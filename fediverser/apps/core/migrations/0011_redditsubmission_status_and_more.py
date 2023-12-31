# Generated by Django 4.2.6 on 2023-10-16 17:34

from django.db import migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_alter_lemmymirroredpost_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="redditsubmission",
            name="status",
            field=model_utils.fields.StatusField(
                choices=[
                    ("retrieved", "retrieved"),
                    ("rejected", "rejected"),
                    ("failed", "failed"),
                    ("mirrored", "mirrored"),
                ],
                default="retrieved",
                max_length=100,
                no_check_for_status=True,
                verbose_name="status",
            ),
        ),
        migrations.AddField(
            model_name="redditsubmission",
            name="status_changed",
            field=model_utils.fields.MonitorField(
                default=django.utils.timezone.now, monitor="status", verbose_name="status changed"
            ),
        ),
    ]
