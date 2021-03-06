import bleach
import datetime
import feedparser
import html
import json
from markdownify import markdownify
import mechanize
import random
import re
import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import NaturalTimeFormatter
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator


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
SOURCE_TYPE_BLOG = 'B'
SOURCE_TYPE_EXEMPLAR = 'E'
SOURCE_TYPE_CHOICES = (
    (SOURCE_TYPE_MANUAL, 'Manual Announcement'),
    (SOURCE_TYPE_APPS_FORUM, 'JudgeApps Forum Post'),
    (SOURCE_TYPE_BLOG, 'WordPress Blog'),
    (SOURCE_TYPE_EXEMPLAR, 'Exemplar Deadline'),
)
SOURCE_TO_FIELD = {
    SOURCE_TYPE_MANUAL: 'manual',
    SOURCE_TYPE_APPS_FORUM: 'forum',
    SOURCE_TYPE_BLOG: 'blog',
    SOURCE_TYPE_EXEMPLAR: 'exemplar',
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

    order = models.IntegerField(
        default=0,
        help_text="Key to sort by in user-facing views",
    )

    default_source = models.BooleanField(
        default=False,
        help_text="Default sources are automatically added to newly connected "
                  "destinations.",
    )

    @property
    def type_detail(self):
        return self.get_source_type_display()

    @property
    def subclass(self):
        if self.__class__ == MessageSource:
            field = SOURCE_TO_FIELD[self.source_type] + 'source'
            return getattr(self, field)
        else:
            return self

    def get_new_announcements(self, **kwargs):
        # Check for announcements, create Announcement objects.
        raise NotImplementedError()

    def __str__(self):
        return f'MessageSource {self.id} - {self.name}'

    class Meta:
        ordering = ['order']


class ManualSource(MessageSource):
    """
    A manual announcement from the Judge Announcement project. Issued via the
    web interface by an authorized user.
    """

    authorized_users = models.ManyToManyField(
        User,
        null=True, blank=True,
    )
    public_source = models.BooleanField(
        default=False,
        help_text="Allow any user to send to this source, for example, "
                  "for a testing source.",
    )

    def get_new_announcements(self, **kwargs):
        # Do nothing, Announcements for this one are created directly in the
        # database.
        return

    def save(self, *args, **kwargs):
        self.source_type = SOURCE_TYPE_MANUAL
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ManualSource {self.id} - {self.name}'


FORUMSOURCE_TYPE_FORUM_TOPICS = 'FT'
FORUMSOURCE_TYPE_FORUM_POSTS = 'FP'
FORUMSOURCE_TYPE_TOPIC_POSTS = 'TP'
FORUMSOURCE_TYPE_CHOICES = (
    (FORUMSOURCE_TYPE_FORUM_TOPICS, 'New Topics in this Forum'),
    (FORUMSOURCE_TYPE_FORUM_POSTS, 'New Posts in this Forum'),
    (FORUMSOURCE_TYPE_TOPIC_POSTS, 'New Posts in this Topic'),
)

class ForumSource(MessageSource):
    """
    A forum post from a specific JudgeApps forum.
    """

    source_id = models.IntegerField()
    forumsource_type = models.CharField(
        max_length=2,
        choices=FORUMSOURCE_TYPE_CHOICES,
        default=FORUMSOURCE_TYPE_FORUM_TOPICS,
    )
    polling_interval = models.IntegerField(
        default=10,
        help_text="Polling interval in minutes",
    )
    last_polled = models.DateTimeField(
        null=True, blank=True,
        help_text="Last successful poll",
    )

    @property
    def type_detail(self):
        return self.get_source_type_display() + ' - ' +\
               self.get_forumsource_type_display()

    @property
    def feed_url(self):
        if self.forumsource_type == FORUMSOURCE_TYPE_FORUM_TOPICS:
            return settings.JUDGEAPPS_BASE_URL +\
                f'/forum/feed/forum/{self.source_id}/latest_topics/'
        if self.forumsource_type == FORUMSOURCE_TYPE_FORUM_POSTS:
            return settings.JUDGEAPPS_BASE_URL +\
                f'/forum/feed/forum/{self.source_id}/latest_posts/'
        if self.forumsource_type == FORUMSOURCE_TYPE_TOPIC_POSTS:
            return settings.JUDGEAPPS_BASE_URL +\
                f'/forum/feed/topic/{self.source_id}/latest_posts/'

    def get_new_announcements(self, sync=False, **kwargs):
        if not sync and\
           self.last_polled and\
           timezone.now() <= self.last_polled +\
                             datetime.timedelta(minutes=self.polling_interval):
            # Already polled within the interval, don't poll again yet.
            return

        # TODO: Find a way to do this only when needed and store the cookies in
        # redis or something
        br = mechanize.Browser()
        br.set_handle_robots(False)
        br.open(settings.JUDGEAPPS_BASE_URL + '/accounts/login/')
        br.select_form(nr=0)
        br["username"] = settings.JUDGEAPPS_USERNAME
        br["password"] = settings.JUDGEAPPS_PASSWORD
        br.submit()
        res2 = br.open(self.feed_url)

        d = feedparser.parse(res2.read())

        for entry in d.entries:
            if ForumAnnouncement.objects.filter(url=entry.link, source=self):
                continue
            entry_datetime = datetime.datetime.strptime(
                entry.published,
                "%Y-%m-%dT%H:%M:%S%z",
            )
            if entry_datetime < self.created_at:
                continue
            text = bleach.clean(entry.summary, tags=['a'])
            text = html.unescape(text)
            text = markdownify(text)
            announcement = ForumAnnouncement(
                source=self,
                headline=entry.title,
                text=text,
                url=entry.link,
                author_name=entry.author,
                author_url=entry.author_detail.href,
                post_datetime=entry_datetime,
            )
            announcement.save()
        self.last_polled = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        self.source_type = SOURCE_TYPE_APPS_FORUM
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ForumSource {self.id} - {self.name} (JA source {self.source_id})'


class BlogSource(MessageSource):
    """
    A blog post from a specific Judge Blog.
    """

    feed_url = models.URLField(
        help_text="Path to the Judge Blogs feed URL to use, for example, "
                  "https://blogs.magicjudges.org/judgeapps/feed/",
    )

    polling_interval = models.IntegerField(
        default=10,
        help_text="Polling interval in minutes",
    )
    last_polled = models.DateTimeField(
        null=True, blank=True,
        help_text="Last successful poll",
    )

    def get_new_announcements(self, sync=False, **kwargs):
        if not sync and\
           self.last_polled and\
           timezone.now() <= self.last_polled +\
                             datetime.timedelta(minutes=self.polling_interval):
            # Already polled within the interval, don't poll again yet.
            return

        # TODO: Find a way to do this only when needed and store the cookies in
        # redis or something
        d = feedparser.parse(self.feed_url)

        for entry in d.entries:
            if BlogAnnouncement.objects.filter(url=entry.link, source=self):
                continue
            entry_datetime = datetime.datetime.strptime(
                entry.published,
                "%a, %d %b %Y %H:%M:%S %z",
            )
            if entry_datetime < self.created_at:
                continue
            text = bleach.clean(entry.content[0].value, tags=['a'])
            text = html.unescape(text)
            text = markdownify(text)
            res = requests.get(entry.link)
            res.raise_for_status()
            match = re.search('<html lang="(.+?)"', res.text)
            if not match:
                raise Exception("Can't find language code for blog post.")
            announcement = BlogAnnouncement(
                source=self,
                headline=entry.title,
                text=text,
                url=entry.link,
                author_name=entry.author,
                post_datetime=entry_datetime,
                language_tag=match.group(1),
            )
            announcement.save()
        self.last_polled = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        self.source_type = SOURCE_TYPE_BLOG
        super().save(*args, **kwargs)

    def __str__(self):
        return f'BlogSource {self.id} - {self.name}'


class ExemplarSource(MessageSource):
    """
    Announcements about an upcoming Exemplar deadline
    """

    current_wave_id = models.IntegerField(
        help_text="JudgeApps ID of the current exemplar wave",
    )
    current_wave_name = models.CharField(
        max_length=64,
        help_text="Name of the current exemplar wave",
    )
    current_wave_deadline = models.DateTimeField(
        help_text="Deadline of the current exemplar wave",
    )
    last_reminder = models.IntegerField(
        default=99,
        help_text="What was the last reminder that was sent? (number of days "
                  "prior to deadline) Used to track what announcement to send "
                  "next.",
    )

    polling_interval = models.IntegerField(
        default=10,
        help_text="Polling interval in minutes",
    )
    last_polled = models.DateTimeField(
        null=True, blank=True,
        help_text="Last successful poll",
    )

    def get_new_announcements(self, sync=False, **kwargs):
        # if not sync and\
        #    self.last_polled and\
        #    timezone.now() <= self.last_polled +\
        #                      datetime.timedelta(minutes=self.polling_interval):
        # TODO: Update the current wave info from JudgeApps

        announcement_days = (14, 7, 3)

        announcements_due = [d for d in announcement_days
                             if d < self.last_reminder
                             and timezone.now() + datetime.timedelta(days=d) >
                                 self.current_wave_deadline]
        if announcements_due:
            announcement_to_send = min(announcements_due)
            announcement = ExemplarAnnouncement(
                source=self,
                days_out=announcement_to_send,
                wave_id=self.current_wave_id,
                wave_name=self.current_wave_name,
                wave_deadline=self.current_wave_deadline,
            )
            announcement.save()
            self.last_reminder = announcement_to_send
            self.save()

    def save(self, *args, **kwargs):
        self.source_type = SOURCE_TYPE_EXEMPLAR
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ExemplarSource {self.id} - {self.name}'


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

    language_tags = models.CharField(
        default='en-US', max_length=200,
        help_text="Language codes to send to this destination. Only affects "
                  "announcements that are generally translated, like Judge "
                  "Blogs. Defaults to English. Select multiple languages "
                  "using commas, like 'en-US,de-DE'.",
    )

    @property
    def subclass(self):
        if self.__class__ == Destination:
            field = DESTINATION_TO_FIELD[self.destination_type] + 'destination'
            return getattr(self, field)
        else:
            return self

    def maybe_add_default_sources(self):
        routes = SourceRouting.objects.filter(destination=self)
        if not routes:
            for source in MessageSource.objects.filter(default_source=True):
                route, created = SourceRouting.objects.get_or_create(
                    destination=self,
                    source=source,
                )
                if created:
                    route.save()



    def get_absolute_url(self):
        return reverse('destination_detail', kwargs={'pk': self.id})

    # Method to check whether an announcement should go to this destination.
    # Currently checks language settings, however, more things (quiet hours?)
    # could be checked here in the future.
    def wants(self, announcement):
        if announcement.subclass.get_language_tag():
            if announcement.subclass.get_language_tag() not in self.language_tags:
                return False
        return True

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


class AdMessageManager(models.Manager):
    def random(self):
        return random.choice(self.filter(live=True))


class AdMessage(models.Model):
    """
    Simple class stores a string of markdown-formatted text in the database for
    use in each shared announcement. Contains short messages like "Developed on
    GitHub. Pull requests welcome!". One of these is chosen at random and added
    to the context section of each shared announcement.
    """

    text = models.TextField()

    live = models.BooleanField(default=True)

    objects = AdMessageManager()

    def __str__(self):
        return f'AdMessage {self.id} - {self.text}'


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

    def get_language_tag(self):
        return None

    @property
    def subclass(self):
        if self.__class__ == Announcement:
            field = SOURCE_TO_FIELD[self.announcement_type] + 'announcement'
            return getattr(self, field)
        else:
            return self

    @property
    def truncated_text(self):
        text = Truncator(self.text).words(25, html=True)
        text = ">" + text
        text = re.sub("\n", "\n>", text)
        return text

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
            if self.text:
                data.append({
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f"{self.text}",
                    },
                })
        else:
            if self.text:
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
                },
                {
                    'type': 'mrkdwn',
                    'text': AdMessage.objects.random().text,
                }
            ]
        })
        return data

    def save(self, *args, **kwargs):
        self.announcement_type = SOURCE_TYPE_MANUAL
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ManualAnnouncement {self.id}'


class ForumAnnouncement(Announcement):
    """
    Announcement that was retrieved from the JudgeApps forums.
    """
    author_name = models.TextField()
    author_url = models.TextField()
    post_datetime = models.DateTimeField()

    def get_slack_data(self):
        data = []
        source = self.source.subclass
        if source.forumsource_type == FORUMSOURCE_TYPE_FORUM_TOPICS:
            data.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*{source.name} - New Thread: {self.headline}*",
                },
            })
        else:
            data.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*{source.name} - New Post in {self.headline}*",
                },
            })
        data.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"Posted by: <{self.author_url}|{self.author_name}>",
            },
        })
        data.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"{self.truncated_text}",
            },
        })
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
                    'text': f"Posted to the JudgeApps forum on {self.post_datetime.strftime('%Y-%m-%d %H:%M:%S')} (UTC)",
                },
                {
                    'type': 'mrkdwn',
                    'text': AdMessage.objects.random().text,
                }
            ]
        })
        return data

    def save(self, *args, **kwargs):
        self.announcement_type = SOURCE_TYPE_APPS_FORUM
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ForumAnnouncement {self.id}'


class BlogAnnouncement(Announcement):
    """
    Announcement that was retrieved from the MagicJudges Blogs.
    """
    language_tag = models.CharField(max_length=10)
    author_name = models.TextField()
    post_datetime = models.DateTimeField()

    def get_language_tag(self):
        return self.language_tag

    def get_slack_data(self):
        data = []
        source = self.source.subclass
        data.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"*{source.name} - New Blog Post in {self.headline}*",
            },
        })
        data.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"Posted by: {self.author_name}",
            },
        })
        data.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"{self.truncated_text}",
            },
        })
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
                    'text': f"Posted to the MagicJudges Blogs on {self.post_datetime.strftime('%Y-%m-%d %H:%M:%S')} (UTC)",
                },
                {
                    'type': 'mrkdwn',
                    'text': AdMessage.objects.random().text,
                }
            ]
        })
        return data

    def save(self, *args, **kwargs):
        self.announcement_type = SOURCE_TYPE_BLOG
        super().save(*args, **kwargs)

    def __str__(self):
        return f'BlogAnnouncement {self.id}'


class ExemplarAnnouncement(Announcement):
    """
    Announcement of an upcoming Exemplar deadline
    """
    days_out = models.IntegerField(
        help_text="Nominal number of days out until the wave closes",
    )
    wave_id = models.IntegerField(
        help_text="JudgeApps ID of the exemplar wave in question",
    )
    wave_name = models.CharField(
        max_length=64,
        help_text="Exemplar wave name",
    )
    wave_deadline = models.DateTimeField(
        help_text="Deadline of exemplar wave in question",
    )

    @property
    def time_zone_converter_url(self):
        return "https://www.timeanddate.com/worldclock/converter.html?iso=" +\
               self.wave_deadline.strftime("%Y%m%dT%H%M%S") +\
               "&p1=234&p2=179&p3=136&p4=195&p5=248&p6=240"

    @property
    def apps_exemplar_url(self):
        return "https://apps.magicjudges.org/recognitions/"

    @property
    def timedelta(self):
        return NaturalTimeFormatter.string_for(self.wave_deadline)

    def get_slack_data(self):
        data = []
        source = self.source.subclass
        data.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"*{source.name} - {self.wave_name}*",
            },
        })
        data.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"Closing {self.timedelta}",
            },
        })
        data.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"The Exemplar Program window {self.wave_name} will "
                        f"be closing on <{self.time_zone_converter_url}|" +
                        f"{self.wave_deadline.strftime('%A, %B %-d at %-H:%M %p')}"
                        f" UTC>. Consider taking a moment "
                        f"to enter recognitions now! {self.apps_exemplar_url}",
            },
        })
        data.append({
            'type': 'context',
            'elements': [
                {
                    'type': 'mrkdwn',
                    'text': f"Automatically sent by the Judge Announcements app",
                },
                {
                    'type': 'mrkdwn',
                    'text': AdMessage.objects.random().text,
                }
            ]
        })
        return data

    def save(self, *args, **kwargs):
        self.announcement_type = SOURCE_TYPE_EXEMPLAR
        super().save(*args, **kwargs)

    def __str__(self):
        return f'ExemplarAnnouncement {self.id}'


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
