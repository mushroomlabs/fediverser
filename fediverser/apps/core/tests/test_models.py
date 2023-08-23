from django.test import TestCase

from fediverser.apps.core import factories


class LemmyInstanceTestCase(TestCase):
    def setUp(self):
        self.instance = factories.LemmyInstanceFactory(domain="test.example.com")

    def test_domain_is_created(self):
        self.assertEqual(self.instance.domain, "test.example.com")
