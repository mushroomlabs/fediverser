# Generated by Django 4.2.13 on 2024-07-17 23:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_person_useraccount_lemmy_account"),
    ]

    operations = [
        migrations.AddField(
            model_name="fediversedinstance",
            name="creates_reddit_mirror_bots",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="fediversedinstance",
            name="portal_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
