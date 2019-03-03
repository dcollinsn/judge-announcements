from announcements.models import MessageSource, Announcement, Message


def fetch_announcements():
    for source in MessageSource.objects.all():
        source.subclass.get_new_announcements()


def route_announcements():
    """
    For now, just create the Messages straight away using the configured
    Routings. However, in the future, we might delay on creating some Messages,
    or do some other special stuff, in order to support use cases like a "quiet
    hours" setting for certain destinations.

    TODO: Maybe also need a filter to not keep checking old Announcements.
    """
    for announcement in Announcement.objects.all():
        source = announcement.source
        configured_routings = source.sourcerouting_set.all()
        created_messages = announcement.message_set.all()
        created_routings = [m.source_routing for m in created_messages]
        for routing in configured_routings:
            if routing not in created_routings:
                if announcement.created_at >= routing.created_at:
                    message = Message(
                        source_routing=routing,
                        announcement=announcement,
                    )
                    message.save()


def deliver_messages():
    for message in Message.objects.filter(sent=False):
        message.deliver()
