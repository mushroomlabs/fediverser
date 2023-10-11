from unittest.mock import patch

from django.test import TestCase

from fediverser.apps.core import factories
from fediverser.apps.core.choices import AutomaticSubmissionPolicies
from fediverser.apps.core.models import LemmyCommunity, LemmyInstance, RedditSubmission


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

    @patch.object(LemmyCommunity, "mirroring", None)
    @patch.object(LemmyInstance, "mirroring", None)
    def test_can_check_self_posts(self):
        poster = factories.RedditToLemmyCommunityFactory(
            automatic_submission_policy=AutomaticSubmissionPolicies.SELF_POST_ONLY
        )

        with patch.object(RedditSubmission, "post_to_lemmy", return_value=None):
            submission = factories.SelfPostFactory(subreddit=poster.subreddit)
            self.assertTrue(poster.lemmy_community.can_accept_automatic_submission(submission))
