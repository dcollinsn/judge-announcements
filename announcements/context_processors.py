from announcements import models


def access_control(request):
    user = request.user
    context = {}
    if models.ManualSource.objects.filter(authorized_users=user):
        context['can_send_manual_announcements'] = True

    return context
