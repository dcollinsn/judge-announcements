from django.db.models import Q
from announcements import models


def access_control(request):
    user = request.user
    context = {}
    if user.is_authenticated and\
       models.ManualSource.objects.filter(Q(public_source=True) |
                                          Q(authorized_users=user)):
        context['can_send_manual_announcements'] = True

    return context
