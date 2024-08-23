from django.dispatch import Signal

redditor_migrated = Signal(["reddit_username", "activitypub_actor"])
instance_closed = Signal(["instance"])
instance_abandoned = Signal(["instance"])
