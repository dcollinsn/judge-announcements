import datetime
import json
import requests
from urllib.parse import quote_plus
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.signing import Signer
from django.utils import timezone
from django.views.generic import TemplateView
from announcements import jobs, models


class HomepageView(TemplateView):
    template_name = 'announcements/homepage.html'


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

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['destination'] = self.destination

        return context
