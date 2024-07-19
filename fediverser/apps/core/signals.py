from django.dispatch import Signal

redditor_migrated = Signal(["reddit_account", "activitypub_actor"])
