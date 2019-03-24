from announcements import models
from django.contrib import admin


admin.site.register(models.ManualSource)
admin.site.register(models.ForumSource)
admin.site.register(models.SlackDestination)
admin.site.register(models.SourceRouting)
admin.site.register(models.ManualAnnouncement)
admin.site.register(models.ForumAnnouncement)
admin.site.register(models.Message)
admin.site.register(models.AdMessage)
