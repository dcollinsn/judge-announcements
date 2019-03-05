import importlib
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import View
from django_q.models import Task, Schedule


class BaseScheduledJob():
    """
    Base class for each of our async job. This class is basically responsible
    for creating the schedule (on first run) and for reporting status
    information (for our status page).
    """
    extra_kwargs = {}

    # Create the Schedule if needed, set up the object
    def __init__(self):
        object, created = Schedule.objects.get_or_create(
            name=self.name,
            func=self.func,
            schedule_type=self.schedule_type,
            defaults={
                'repeats': -1,
            },
            **self.extra_kwargs
        )
        if created:
            Schedule.objects.filter(name=self.name).delete()
            object.save()
        self.object = object
        self.task_id = self.object.task
        try:
            self.task = Task.objects.get(id=self.object.task)
        except Task.DoesNotExist:
            self.task = None
        return

    def run_now(self):
        mod_name, func_name = self.func.rsplit('.',1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        func(sync=True)
#        self.object.next_run = timezone.now()
#        self.object.save()

    def get_last_run(self):
        if self.task:
            return self.task.stopped
        try:
            return Task.objects.filter(group=self.name)[0].stopped
        except IndexError:
            return None

    def get_next_run(self):
        return self.object.next_run

    def queued_now(self):
        if self.object.next_run <= timezone.now():
            return True
        if self.task_id and not self.task:
            return True
        return False


class RunJobMixin(UserPassesTestMixin):
    """
    View mixin to run the selected job immediately.
    """
    success_url = reverse_lazy('site_status')

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        self.object = self.schedule_class()
        self.object.run_now()
        return HttpResponseRedirect(str(self.success_url))


class AnnouncementFetchJob(BaseScheduledJob):
    """
    Step 1 of the pipeline: Iterate over all MessageSources and check for any
    new messages. If we get any, create an Announcement.
    """
    name = 'fetch_announcements'
    func = 'announcements.workers.fetch_announcements'
    schedule_type = Schedule.MINUTES
    extra_kwargs = {
        'minutes': 1,
    }


class MessageRouterJob(BaseScheduledJob):
    """
    Step 2 of the pipeline: Using the configured routing settings, create any
    applicable Messages from Announcements.
    """
    name = 'route_announcements'
    func = 'announcements.workers.route_announcements'
    schedule_type = Schedule.MINUTES
    extra_kwargs = {
        'minutes': 1,
    }


class MessageDeliveryJob(BaseScheduledJob):
    """
    Step 3: Attempt to deliver Messages.
    """
    name = 'deliver_messages'
    func = 'announcements.workers.deliver_messages'
    schedule_type = Schedule.MINUTES
    extra_kwargs = {
        'minutes': 1,
    }


class RunAnnouncementFetchJobNowView(RunJobMixin, View):
    schedule_class = AnnouncementFetchJob


class RunMessageRouterJobNowView(RunJobMixin, View):
    schedule_class = MessageRouterJob


class RunMessageDeliveryJobNowView(RunJobMixin, View):
    schedule_class = MessageDeliveryJob
