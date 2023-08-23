import factory
import factory.fuzzy

from . import models


class LemmyInstanceFactory(factory.django.DjangoModelFactory):
    domain = factory.Sequence(lambda n: f"{n:03}.example.com")

    class Meta:
        model = models.LemmyInstance
