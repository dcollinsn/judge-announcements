from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView
from announcements import jobs


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
