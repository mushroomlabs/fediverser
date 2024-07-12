import pytest
from django.test import TestCase

from fediverser.apps.core import factories
from fediverser.apps.core.choices import AutomaticSubmissionPolicies


@pytest.mark.django_db(transaction=True)
class BaseTestCase(TestCase):
    pass


class LemmyInstanceTestCase(BaseTestCase):
    def setUp(self):
        self.instance = factories.InstanceFactory(domain="test.example.com")

    def test_domain_is_created(self):
        self.assertEqual(self.instance.domain, "test.example.com")


class RedditMirrorStrategyTestCasee(BaseTestCase):
    def test_can_make_automatic_submission_policies(self):
        strategy = factories.RedditMirrorStrategyFactory(
            automatic_submission_policy=AutomaticSubmissionPolicies.FULL
        )
        self.assertTrue(strategy.accepts_automatic_submissions)

    def test_can_make_self_post_only_policy(self):
        strategy = factories.RedditMirrorStrategyFactory(
            automatic_submission_policy=AutomaticSubmissionPolicies.SELF_POST_ONLY
        )
        self.assertTrue(strategy.accepts_self_posts)
        self.assertFalse(strategy.accepts_link_posts)


class RedditSubmissionTestCase(BaseTestCase):
    def test_self_posts_are_not_linked_to_reddit(self):
        post = factories.RedditSubmissionFactory(
            url="https://www.reddit.com/r/testing/comments/17fuc65/this_is_a_test_post/",
            title="This is a test post",
            selftext="And self posts are not linked back",
        )

        self.assertTrue(post.has_self_text)
        self.assertTrue(post.is_self_post)
        self.assertFalse(post.is_link_post)
        self.assertFalse(post.is_cross_post)

        lemmy_post_payload = post.to_lemmy_post_payload()
        self.assertTrue("url" not in lemmy_post_payload)
        self.assertTrue("body" in lemmy_post_payload)
        self.assertEqual(lemmy_post_payload["body"], "And self posts are not linked back")

    def test_link_posts(self):
        post = factories.RedditSubmissionFactory(
            url="https://www.w3.org/Provider/Style/URI",
            title="Cool URIs don't change",
            selftext="A cool URI is one which does not change.",
        )

        self.assertTrue(post.has_self_text)
        self.assertFalse(post.is_self_post)
        self.assertTrue(post.is_link_post)
        self.assertFalse(post.is_cross_post)

        lemmy_post_payload = post.to_lemmy_post_payload()
        self.assertTrue("url" in lemmy_post_payload)
        self.assertTrue("body" in lemmy_post_payload)
        self.assertEqual(lemmy_post_payload["body"], "A cool URI is one which does not change.")


__all__ = ["LemmyInstanceTestCase", "RedditSubmissionTestCase"]
