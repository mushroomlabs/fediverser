import factory
import factory.fuzzy

from . import models


class LemmyInstanceFactory(factory.django.DjangoModelFactory):
    domain = factory.Sequence(lambda n: f"{n:03}.example.com")

    class Meta:
        model = models.LemmyInstance


class LemmyCommunityFactory(factory.django.DjangoModelFactory):
    instance = factory.SubFactory(LemmyInstanceFactory)
    name = factory.Sequence(lambda n: f"community-{n:03}")

    class Meta:
        model = models.LemmyCommunity


class RedditCommunityFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"test-subreddit-{n:03}")

    class Meta:
        model = models.RedditCommunity


class RedditToLemmyCommunityFactory(factory.django.DjangoModelFactory):
    subreddit = factory.SubFactory(RedditCommunityFactory)
    lemmy_community = factory.SubFactory(LemmyCommunityFactory)

    class Meta:
        model = models.RedditToLemmyCommunity
