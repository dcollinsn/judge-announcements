# Generated by Django 2.1.7 on 2019-03-27 06:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0005_messagesource_order'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlogAnnouncement',
            fields=[
                ('announcement_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='announcements.Announcement')),
                ('language_tag', models.CharField(max_length=10)),
                ('author_name', models.TextField()),
                ('post_datetime', models.DateTimeField()),
            ],
            options={
                'abstract': False,
            },
            bases=('announcements.announcement',),
        ),
        migrations.CreateModel(
            name='BlogSource',
            fields=[
                ('messagesource_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='announcements.MessageSource')),
                ('feed_url', models.URLField(help_text='Path to the Judge Blogs feed URL to use, for example, https://blogs.magicjudges.org/judgeapps/feed/')),
                ('polling_interval', models.IntegerField(default=10, help_text='Polling interval in minutes')),
                ('last_polled', models.DateTimeField(blank=True, help_text='Last successful poll', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('announcements.messagesource',),
        ),
        migrations.AlterModelOptions(
            name='messagesource',
            options={'ordering': ['order']},
        ),
        migrations.AddField(
            model_name='destination',
            name='language_tags',
            field=models.CharField(default='en-US', help_text="Language codes to send to this destination. Only affects announcements that are generally translated, like Judge Blogs. Defaults to English. Select multiple languages using commas, like 'en-US,de-DE'.", max_length=200),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='announcement_type',
            field=models.CharField(choices=[('M', 'Manual Announcement'), ('F', 'JudgeApps Forum Post'), ('B', 'MagicJudges Blog')], default='', max_length=1),
        ),
        migrations.AlterField(
            model_name='messagesource',
            name='source_type',
            field=models.CharField(choices=[('M', 'Manual Announcement'), ('F', 'JudgeApps Forum Post'), ('B', 'MagicJudges Blog')], default='', max_length=1),
        ),
    ]
