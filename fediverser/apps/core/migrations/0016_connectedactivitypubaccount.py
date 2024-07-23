# Generated by Django 4.2.13 on 2024-07-22 21:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_mergedentry"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConnectedActivityPubAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connected_activitypub_accounts",
                        to="core.useraccount",
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connected_portal_accounts",
                        to="core.person",
                    ),
                ),
            ],
        ),
    ]