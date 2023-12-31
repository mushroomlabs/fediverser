# Generated by Django 4.2.6 on 2023-10-11 08:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_redditcomment_marked_as_spam_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="reddittolemmycommunity",
            name="automatic_comment_policy",
            field=models.TextField(
                choices=[
                    ("Disabled", "Comment threads will not be mirrored"),
                    ("Link Only", "Mirror comment threads for external links"),
                    ("Self Only", "Mirror comment threads for self-posts"),
                    ("Full", "Mirror all comment threads"),
                ],
                default="Disabled",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="reddittolemmycommunity",
            name="automatic_submission_limit",
            field=models.SmallIntegerField(
                blank=True, help_text="Limit of maximum automatic submissions per 24h", null=True
            ),
        ),
        migrations.AddField(
            model_name="reddittolemmycommunity",
            name="automatic_submission_policy",
            field=models.TextField(
                choices=[
                    ("Disabled", "No automatic submission allowed"),
                    ("Link Only", "Only external links"),
                    ("Self Only", "Only self-posts"),
                    ("Full", "All submissions"),
                ],
                default="Disabled",
                max_length=16,
            ),
        ),
    ]
