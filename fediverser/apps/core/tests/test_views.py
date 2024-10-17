from django.test import Client
from django.urls import resolve

from fediverser.apps.core import factories

from .common import BaseTestCase


class CommunityViewTestCase(BaseTestCase):
    def setUp(self):
        self.community = factories.CommunityFactory()
        self.client = Client()

    def test_can_resolve_url(self):
        resolver = resolve(f"/communities/{self.community.fqdn}")
        self.assertEqual(resolver.view_name, "fediverser-core:community-detail")

    def test_anonymous_user_can_see_community_page(self):
        url = f"/communities/{self.community.fqdn}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class SignupViewTestCase(BaseTestCase):
    def test_anonymous_user_can_see_page(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 200)


__all__ = ("CommunityViewTestCase", "SignupViewTestCase")
