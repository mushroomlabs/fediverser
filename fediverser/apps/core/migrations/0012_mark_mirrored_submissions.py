import datetime

from django.db import migrations
from django.utils import timezone

from fediverser.apps.core.choices import SOURCE_CONTENT_STATUSES


def mark_mirrored_migrations(apps, schema_editor):
    RedditSubmission = apps.get_model("core", "RedditSubmission")

    NOW = timezone.now()

    unprocessed_submissions = RedditSubmission.objects.filter(
        status=SOURCE_CONTENT_STATUSES.retrieved
    )

    unprocessed_submissions.filter(created__lte=NOW - datetime.timedelta(minutes=30)).update(
        status=SOURCE_CONTENT_STATUSES.rejected
    )

    unprocessed_submissions.filter(lemmy_mirrored_posts__isnull=False).update(
        status=SOURCE_CONTENT_STATUSES.mirrored
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_redditsubmission_status_and_more"),
    ]
    operations = [
        migrations.RunPython(mark_mirrored_migrations, reverse_code=migrations.RunPython.noop),
    ]
