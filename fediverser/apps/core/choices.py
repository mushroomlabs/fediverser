from django.db.models import TextChoices
from model_utils import Choices


class AutomaticSubmissionPolicies(TextChoices):
    NONE = ("Disabled", "No automatic submission allowed")
    LINK_ONLY = ("Link Only", "Only external links")
    SELF_POST_ONLY = ("Self Only", "Only self-posts")
    FULL = ("Full", "All submissions")


class AutomaticCommentPolicies(TextChoices):
    NONE = ("Disabled", "Comment threads will not be mirrored")
    LINK_ONLY = ("Link Only", "Mirror comment threads for external links")
    SELF_POST_ONLY = ("Self Only", "Mirror comment threads for self-posts")
    FULL = ("Full", "Mirror all comment threads")


SOURCE_CONTENT_STATUSES = Choices("retrieved", "accepted", "rejected", "failed", "mirrored")
