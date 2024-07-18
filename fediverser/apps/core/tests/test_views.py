import pytest
from django.test import Client, TestCase
from django.urls import resolve

from fediverser.apps.core import factories


@pytest.mark.django_db(transaction=True)
class BaseTestCase(TestCase):
    pass


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


__all__ = ("CommunityViewTestCase",)
