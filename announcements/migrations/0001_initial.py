# Generated by Django 2.1.7 on 2019-03-02 07:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('headline', models.TextField(blank=True, null=True)),
                ('text', models.TextField(blank=True, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('announcement_type', models.CharField(choices=[('M', 'Manual Announcement'), ('F', 'JudgeApps Forum Post')], default='', max_length=1)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Destination',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=80)),
                ('destination_type', models.CharField(choices=[('S', 'Slack (Incoming Webhook)')], default='', max_length=1)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sent', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MessageSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=80)),
                ('description', models.TextField()),
                ('source_type', models.CharField(choices=[('M', 'Manual Announcement'), ('F', 'JudgeApps Forum Post')], default='', max_length=1)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SourceRouting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ForumSource',
            fields=[
                ('messagesource_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='announcements.MessageSource')),
                ('forum_id', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
            bases=('announcements.messagesource',),
        ),
        migrations.CreateModel(
            name='ManualAnnouncement',
            fields=[
                ('announcement_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='announcements.Announcement')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=('announcements.announcement',),
        ),
        migrations.CreateModel(
            name='ManualSource',
            fields=[
                ('messagesource_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='announcements.MessageSource')),
                ('authorized_users', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=('announcements.messagesource',),
        ),
        migrations.CreateModel(
            name='SlackDestination',
            fields=[
                ('destination_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='announcements.Destination')),
                ('webhook', models.CharField(max_length=160)),
            ],
            options={
                'abstract': False,
            },
            bases=('announcements.destination',),
        ),
        migrations.AddField(
            model_name='sourcerouting',
            name='destination',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='announcements.Destination'),
        ),
        migrations.AddField(
            model_name='sourcerouting',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='announcements.MessageSource'),
        ),
        migrations.AddField(
            model_name='message',
            name='announcement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='announcements.Announcement'),
        ),
        migrations.AddField(
            model_name='message',
            name='source_routing',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='announcements.SourceRouting'),
        ),
        migrations.AddField(
            model_name='destination',
            name='admins',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='destination',
            name='message_types',
            field=models.ManyToManyField(through='announcements.SourceRouting', to='announcements.MessageSource'),
        ),
        migrations.AddField(
            model_name='announcement',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='announcements.MessageSource'),
        ),
    ]
