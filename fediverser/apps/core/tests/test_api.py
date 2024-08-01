from rest_framework.test import APIClient

from fediverser.apps.core import factories
from fediverser.apps.core.settings import app_settings

from .common import BaseTestCase


class ChangeFeedAPITestCase(BaseTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_can_get_connected_account_entry(self):
        feed_entry = factories.ConnectedRedditAccountEntryFactory(
            published_by__portal_url=app_settings.Portal.url
        )
        feed_entry.merge()
        response = self.client.get("/api/changes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


__all__ = ("ChangeFeedAPITestCase",)
