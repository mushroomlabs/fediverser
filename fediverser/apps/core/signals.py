from django.dispatch import Signal

redditor_migrated = Signal(["reddit_username", "activitypub_actor"])
