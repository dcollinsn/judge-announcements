# Generated by Django 2.2rc1 on 2019-04-05 18:46

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0007_auto_20190328_1621'),
    ]

    operations = [
        migrations.AddField(
            model_name='manualsource',
            name='public_source',
            field=models.BooleanField(default=False, help_text='Allow any user to send to this source, for example, for a testing source.'),
        ),
        migrations.AlterField(
            model_name='manualsource',
            name='authorized_users',
            field=models.ManyToManyField(blank=True, null=True, to=settings.AUTH_USER_MODEL),
        ),
    ]
