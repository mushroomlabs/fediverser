from rest_framework.test import APIClient

from fediverser.apps.core import factories
from fediverser.apps.core.settings import app_settings

from .common import BaseTestCase


class APITestCase(BaseTestCase):
    def setUp(self):
        self.client = APIClient()


class SubredditAPITestCase(APITestCase):
    def test_can_list_subreddits_with_recommendations(self):
        subreddit = factories.RedditCommunityFactory()
        community = factories.CommunityFactory()
        factories.RedditToCommunityRecommendationFactory(subreddit=subreddit, community=community)

        response = self.client.get("/api/subreddits")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        subreddit_data = response.data[0]
        recommendations = subreddit_data["recommended_communities"]
        self.assertEqual(len(recommendations), 1)


class ChangeFeedAPITestCase(APITestCase):

    def test_can_get_connected_account_entry(self):
        feed_entry = factories.ConnectedRedditAccountEntryFactory(
            published_by__portal_url=app_settings.Portal.url
        )
        feed_entry.merge()
        response = self.client.get("/api/changes")
        self.assertEqual(response.status_code, 200)


__all__ = (
    "SubredditAPITestCase",
    "ChangeFeedAPITestCase",
)
