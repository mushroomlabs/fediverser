# Generated by Django 4.2.13 on 2024-07-19 20:43

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_rename_endorsemement_endorsemententry_endorsement_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fediversedinstance",
            name="portal_url",
            field=models.URLField(unique=True),
        ),
    ]
