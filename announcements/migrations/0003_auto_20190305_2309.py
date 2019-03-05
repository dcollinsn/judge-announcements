# Generated by Django 2.1.7 on 2019-03-05 23:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0002_auto_20190302_2353'),
    ]

    operations = [
        migrations.CreateModel(
            name='ForumAnnouncement',
            fields=[
                ('announcement_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='announcements.Announcement')),
                ('author_name', models.TextField()),
                ('author_url', models.TextField()),
                ('post_datetime', models.DateTimeField()),
            ],
            options={
                'abstract': False,
            },
            bases=('announcements.announcement',),
        ),
        migrations.RenameField(
            model_name='forumsource',
            old_name='forum_id',
            new_name='source_id',
        ),
        migrations.AddField(
            model_name='forumsource',
            name='forumsource_type',
            field=models.CharField(choices=[('FT', 'New Topics in this Forum'), ('FP', 'New Posts in this Forum'), ('TP', 'New Posts in this Topic')], default='FT', max_length=2),
        ),
        migrations.AddField(
            model_name='forumsource',
            name='last_polled',
            field=models.DateTimeField(blank=True, help_text='Last successful poll', null=True),
        ),
        migrations.AddField(
            model_name='forumsource',
            name='polling_interval',
            field=models.IntegerField(default=10, help_text='Polling interval in minutes'),
        ),
    ]