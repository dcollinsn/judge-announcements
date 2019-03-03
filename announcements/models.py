import json
import requests

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class CreatedUpdatedMixin(models.Model):
    """
    Model Mixin adding an auto_now and auto_now_add field.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


SOURCE_TYPE_MANUAL = 'M'
SOURCE_TYPE_APPS_FORUM = 'F'
SOURCE_TYPE_CHOICES = (
    (SOURCE_TYPE_MANUAL, 'Manual Announcement'),
    (SOURCE_TYPE_APPS_FORUM, 'JudgeApps Forum Post'),
)
SOURCE_TO_FIELD = {
    SOURCE_TYPE_MANUAL: 'manual',
    SOURCE_TYPE_APPS_FORUM: 'forum',
}


class MessageSource(CreatedUpdatedMixin, models.Model):
    """
    Base class representing a possible source of announcements. Each subclass
    implements logic to check the source for new announcements and create
    Message objects. Each subclass also contains fields that are used to store
    configuration data such as URLs and API keys for the source.
    """

    name = models.CharField(max_length=80)
    description = models.TextField()

    source_type = models.CharField(
        max_length=1,
        choices=SOURCE_TYPE_CHOICES,
        default='',
    )

    @property
    def subclass(self):
        if self.__class__ == MessageSource:
            field = SOURCE_TO_FIELD[self.source_type] + 'source'
            return getattr(self, field)
        else:
            return self

    def get_new_announcements(self):
        # Check for announcements, create Announcement objects.
        raise NotImplementedError()

    def __str__(self):
        return f'MessageSource {self.id} - {self.name}'


class ManualSource(MessageSource):
    """
    A manual announcement from the Judge Announcement project. Issued via the
    web interface by an authorized user.
    """

    authorized_users = models.ManyToManyField(User)

    def get_new_announcements(self):
        # Do nothing, Announcements for this one are created directly in the
        # database.
        return

    def save(self, *args, **kwargs):
        self.source_type = SOURCE_TYPE_MANUAL
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ManualSource {self.id} - {self.name}'


class ForumSource(MessageSource):
    """
    A forum post from a specific JudgeApps forum.
    """

    forum_id = models.IntegerField()

    def save(self, *args, **kwargs):
        self.source_type = SOURCE_TYPE_APPS_FORUM
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ForumSource {self.id} - {self.name} (JA forum {self.forum_id})'


class SourceRouting(CreatedUpdatedMixin, models.Model):
    """
    For now, just a through class to link a Destination to the Sources that it
    subscribes to. In the future, we may add more fields like "active hours" so
    that regions can configure not to get notifications in the middle of their
    night.
    """

    destination = models.ForeignKey('Destination', on_delete=models.CASCADE)
    source = models.ForeignKey(MessageSource, on_delete=models.CASCADE)

    def __str__(self):
        return f'Routing {self.id} - "{self.source.subclass}" to ' +\
               f'"{self.destination.subclass}"'


DESTINATION_TYPE_SLACK = 'S'
DESTINATION_TYPE_CHOICES = (
    (DESTINATION_TYPE_SLACK, 'Slack (Incoming Webhook)'),
)
DESTINATION_TO_FIELD = {
    DESTINATION_TYPE_SLACK: 'slack',
}


class Destination(CreatedUpdatedMixin, models.Model):
    """
    Base class representing a place where announcements can be sent. Each
    subclass contains configuration fields such as URLs and API keys, each
    subclass also implements logic to send a message and verify delivery.
    """

    name = models.CharField(max_length=80)
    admins = models.ManyToManyField(User)
    message_types = models.ManyToManyField(
        MessageSource,
        through=SourceRouting,
    )

    destination_type = models.CharField(
        max_length=1,
        choices=DESTINATION_TYPE_CHOICES,
        default='',
    )

    @property
    def subclass(self):
        if self.__class__ == Destination:
            field = DESTINATION_TO_FIELD[self.destination_type] + 'destination'
            return getattr(self, field)
        else:
            return self

    def deliver(self, message):
        raise NotImplementedError()

    def __str__(self):
        return f'Destination {self.id} - {self.name}'


class SlackDestination(Destination):
    team_id = models.CharField(max_length=32)
    channel_id = models.CharField(max_length=32)
    webhook = models.CharField(max_length=160)

    def deliver(self, message):
        slack_data = message.announcement.subclass.get_slack_data()
        slack_data = {'blocks': slack_data}
        response = requests.post(
            self.webhook,
            data=json.dumps(slack_data),
            headers={'Content-Type': 'application/json'},
        )
        if response.status_code == 200:
            message.sent = True
            message.sent_at = timezone.now()
            message.save()
        else:
            response.raise_for_status()
            # TODO: Logging
            # TODO: Backoff?
            return

    def save(self, *args, **kwargs):
        self.destination_type = DESTINATION_TYPE_SLACK
        super().save(*args, **kwargs)

    def __str__(self):
        return f'SlackDestination {self.id} - {self.name}'


class Announcement(CreatedUpdatedMixin, models.Model):
    """
    Base class representing an individual announcement. Each subclass contains
    the data fields appropriate to that type of announcement, so that the text
    of the announcement can be prepared as it is about to be delivered, taking
    into account any relevant locale settings.
    """

    # TODO: This is a VERY TEMPORARY implementation of this thing. We ACTUALLY
    # want to handle anything from plain text to Blog posts to Forum posts and
    # more. So instead of a simple text and url field, we're actually going to
    # want to have something like a template engine.

    source = models.ForeignKey(MessageSource, on_delete=models.CASCADE)
    headline = models.TextField(null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    url = models.TextField(null=True, blank=True)

    # Types exactly correspond to source types, so use the same enum
    announcement_type = models.CharField(
        max_length=1,
        choices=SOURCE_TYPE_CHOICES,
        default='',
    )

    @property
    def subclass(self):
        if self.__class__ == Announcement:
            field = SOURCE_TO_FIELD[self.announcement_type] + 'announcement'
            return getattr(self, field)
        else:
            return self

    def get_slack_data(self):
        raise NotImplementedError()

    def __str__(self):
        return f'Announcement {self.id}'


class ManualAnnouncement(Announcement):
    """
    Announcement that was entered manually by a user.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def get_slack_data(self):
        data = []
        if self.headline:
            data.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*{self.source.name}: {self.headline}*",
                },
            })
            data.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"{self.text}",
                },
            })
        else:
            data.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*{self.source.name}*: {self.text}",
                },
            })
        if self.url:
            data.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"{self.url}",
                },
            })
        data.append({
            'type': 'context',
            'elements': [
                {
                    'type': 'mrkdwn',
                    'text': f"Submitted on {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC) by {self.user.get_full_name()}",
                }
            ]
        })
        return data

    def save(self, *args, **kwargs):
        self.announcement_type = SOURCE_TYPE_MANUAL
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ManualAnnouncement {self.id}'


class Message(CreatedUpdatedMixin, models.Model):
    """
    Class representing an individual announcement going to an individual
    SourceRouting. (Destination + configuration data.)
    """
    source_routing = models.ForeignKey(SourceRouting, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    def deliver(self):
        self.source_routing.destination.subclass.deliver(self)

    def __str__(self):
        return f'Message {self.id} - {self.announcement.subclass} ' +\
               f'to {self.source_routing.destination.subclass}'
