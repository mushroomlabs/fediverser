import pytest
from django.test import TestCase


@pytest.mark.django_db(transaction=True)
class BaseTestCase(TestCase):
    pass
