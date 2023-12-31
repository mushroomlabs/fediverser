# Generated by Django 4.2.4 on 2023-09-11 01:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_lemmycommunityinvitetemplate_lemmycommunityinvite"),
    ]

    operations = [
        migrations.AddField(
            model_name="redditaccount",
            name="marked_as_spammer",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="redditaccount",
            name="rejected_invite",
            field=models.BooleanField(default=False),
        ),
    ]
