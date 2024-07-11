import os
import uuid

from django.db import models
from django.utils.deconstruct import deconstructible
from model_utils import Choices
from tree_queries.models import TreeNode

AP_CLIENT_REQUEST_HEADERS = {"Accept": "application/ld+json"}

COMMUNITY_STATUSES = Choices(
    ("active", "Active"),
    ("inactive", "Inactive (Lingering community or Infrequent Content posted)"),
    ("abandoned", "Abandoned"),
    ("closed", "Closed"),
)

INSTANCE_STATUSES = Choices(
    ("active", "Active"),
    ("abandoned", "Abandoned"),
    ("closed", "Closed"),
)

AP_SERVER_SOFTWARE = Choices(
    ("lemmy", "Lemmy"),
    ("kbin", "Kbin"),
    ("mbin", "Mbin"),
    ("mastodon", "Mastodon"),
)


@deconstructible
class UserUpload:
    def __init__(self, root_folder):
        self.root_folder = root_folder

    def __call__(self, instance, filename):
        return os.path.join(self.root_folder, str(uuid.uuid1()), filename)


class Category(TreeNode):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(null=True, blank=True)

    @property
    def full_name(self):
        return " : ".join([str(n.name) for n in self.ancestors(include_self=True)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
