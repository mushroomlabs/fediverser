from django.test import TestCase

from fediverser.apps.core import factories
from fediverser.apps.core.choices import AutomaticSubmissionPolicies


class LemmyInstanceTestCase(TestCase):
    def setUp(self):
        self.instance = factories.LemmyInstanceFactory(domain="test.example.com")

    def test_domain_is_created(self):
        self.assertEqual(self.instance.domain, "test.example.com")


class RedditToLemmyCommunityTestCase(TestCase):
    def test_can_make_automatic_submission_policies(self):
        poster = factories.RedditToLemmyCommunityFactory(
            automatic_submission_policy=AutomaticSubmissionPolicies.FULL
        )
        self.assertTrue(poster.accepts_automatic_submissions)

    def test_can_make_self_post_only_policy(self):
        poster = factories.RedditToLemmyCommunityFactory(
            automatic_submission_policy=AutomaticSubmissionPolicies.SELF_POST_ONLY
        )
        self.assertTrue(poster.accepts_self_posts)
        self.assertFalse(poster.accepts_link_posts)
