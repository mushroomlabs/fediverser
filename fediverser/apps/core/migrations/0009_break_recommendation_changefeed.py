# Generated by Django 4.2.13 on 2024-07-19 23:46

from django.db import migrations


def split_recommendation_feed_entries(apps, schema_editor):
    RedditToCommunityRecommendationEntry = apps.get_model(
        "core", "RedditToCommunityRecommendationEntry"
    )

    for entry in RedditToCommunityRecommendationEntry.objects.all():
        entry.subreddit = entry.recommendation.subreddit
        entry.community = entry.recommendation.community
        entry.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_add_url"),
    ]

    operations = [
        migrations.RunPython(
            split_recommendation_feed_entries, reverse_code=migrations.RunPython.noop
        ),
    ]