import datetime

from django.db import migrations
from django.utils import timezone

from fediverser.apps.core.choices import SOURCE_CONTENT_STATUSES


def mark_mirrored_migrations(apps, schema_editor):
    RedditComment = apps.get_model("core", "RedditComment")
    NOW = timezone.now()

    unprocessed_comments = RedditComment.objects.filter(status=SOURCE_CONTENT_STATUSES.retrieved)

    unprocessed_comments.filter(created__lte=NOW - datetime.timedelta(hours=12)).update(
        status=SOURCE_CONTENT_STATUSES.rejected
    )

    unprocessed_comments.filter(lemmy_mirrored_comments__isnull=False).update(
        status=SOURCE_CONTENT_STATUSES.mirrored
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_redditcomment_status_redditcomment_status_changed"),
    ]

    operations = [
        migrations.RunPython(mark_mirrored_migrations, reverse_code=migrations.RunPython.noop),
    ]
