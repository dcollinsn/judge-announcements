import datetime
import json
import requests
from urllib.parse import quote_plus
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.signing import Signer
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from announcements import jobs, models, forms


class StatusView(UserPassesTestMixin, TemplateView):
    template_name = 'announcements/status.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fetch_job'] = jobs.AnnouncementFetchJob()
        context['router_job'] = jobs.MessageRouterJob()
        context['delivery_job'] = jobs.MessageDeliveryJob()
        return context


class DestinationList(LoginRequiredMixin, ListView):
    model = models.Destination
    template_name = 'announcements/destination_list.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(admins=self.request.user)
        return queryset


class DestinationDetail(LoginRequiredMixin, DetailView):
    model = models.Destination
    template_name = 'announcements/destination_detail.html'
    context_object_name = 'destination'

    def get_object(self, **kwargs):
        object = super().get_object(**kwargs)
        object = object.subclass
        if not self.request.user.is_superuser and\
           self.request.user not in object.admins.all():
            raise PermissionDenied
        return object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_sources'] = models.MessageSource.objects.all()
        context['selected_sources'] = [o.subclass for o in self.object.message_types.all()]
        return context

    def post(self, *args, **kwargs):
        self.object = self.get_object()

        # Process POST data
        current_sources = [o.subclass for o in self.object.message_types.all()]
        selected_source_ids = []
        for key in self.request.POST:
            if key.startswith('ms_'):
                id_str = key[3:]
                try:
                    selected_source_ids.append(int(id_str))
                except ValueError:
                    pass
        selected_sources = [
            o.subclass for o in
            models.MessageSource.objects.filter(id__in=selected_source_ids)]

        for current_source in current_sources:
            if current_source not in selected_sources:
                models.SourceRouting.objects.get(
                    destination=self.object,
                    source=current_source,
                ).delete()

        for selected_source in selected_sources:
            if selected_source not in current_sources:
                models.SourceRouting(
                    destination=self.object,
                    source=selected_source,
                ).save()

        # Proceed with rendering the view normally
        return HttpResponseRedirect(reverse('destination_list'))


class CreateAnnouncementView(LoginRequiredMixin, CreateView):
    template_name = 'announcements/announcement_create.html'
    model = models.ManualAnnouncement
    form_class = forms.ManualAnnouncementForm
    success_url = reverse_lazy('create_announcement_success')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class CreateAnnouncementSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'announcements/announcement_create_success.html'


class SlackConnectView(LoginRequiredMixin, TemplateView):
    template_name = 'announcements/slack_connect.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # Oauth2.0 allows us to send a "state" parameter which is used to
        # protect against CSRF attacks. I don't know if there's a real attack
        # scenario here, but we might as well use it. We'll use django signing
        # to sign the user ID and current timestamp.
        string_to_sign = str(request.user.id) + ':' + timezone.now().strftime("%Y-%m-%dT%H:%M:%S%z")
        signer = Signer()
        context['state'] = quote_plus(signer.sign(string_to_sign))

        # Data for the slack URL
        context['client_id'] = settings.SLACK_CLIENT_ID
        if request.is_secure():
            context['redirect_uri'] = 'https://'
        else:
            context['redirect_uri'] = 'http://'
        context['redirect_uri'] = context['redirect_uri'] +\
            request.get_host() + '/slack/callback/'

        return context

class SlackCallbackView(LoginRequiredMixin, TemplateView):
    template_name = 'announcements/slack_callback.html'

    def get(self, request, *args, **kwargs):
        # We need to do some stuff with the GET parameters

        if request.GET.get('error'):
            raise PermissionDenied()

        state = request.GET.get('state')
        signer = Signer()
        signed_string = signer.unsign(state)

        try:
            user_id_str, timezone_now_str = signed_string.split(':', 1)
            user_id = int(user_id_str)
            timezone_now = datetime.datetime.strptime(
                timezone_now_str,
                "%Y-%m-%dT%H:%M:%S%z",
            )
        except ValueError:
            raise PermissionDenied()

        if user_id != request.user.id or\
           timezone.now() < timezone_now or\
           timezone.now() > timezone_now + datetime.timedelta(minutes=10):
            raise PermissionDenied()

        if request.is_secure():
            redirect_uri = 'https://'
        else:
            redirect_uri = 'http://'
        redirect_uri = redirect_uri +\
            request.get_host() + '/slack/callback/'

        response = requests.get(
            'https://slack.com/api/oauth.access',
            params={
                'client_id': settings.SLACK_CLIENT_ID,
                'client_secret': settings.SLACK_CLIENT_SECRET,
                'code': request.GET.get('code'),
                'redirect_uri': redirect_uri,
            },
        )

        response.raise_for_status()

        json_data = json.loads(response.text)
        destination, created = models.SlackDestination.objects.get_or_create(
            team_id=json_data['team_id'],
            channel_id=json_data['incoming_webhook']['channel_id'],
            defaults={
                'name': json_data['team_name'] + ': ' +
                        json_data['incoming_webhook']['channel'],
            },
        )
        # Use the newer webhook, in case it changed
        destination.webhook = json_data['incoming_webhook']['url']
        destination.admins.add(request.user)
        destination.save()
        self.destination = destination

        # Add default sources if this was just created
        destination.maybe_add_default_sources()

        messages.success(
            request,
            f"Your new destination, {destination.name}, was successfully "
            f"added! The next step is to choose what types of messages you "
            f"want to receive. In the future, you can get to this page "
            f"from the left sidebar, by clicking 'Configure Notification "
            f"Settings'.",
        )

        return HttpResponseRedirect(reverse(
            'destination_detail',
            kwargs={'pk': destination.id},
        ))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['destination'] = self.destination

        return context
