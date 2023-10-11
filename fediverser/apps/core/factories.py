import random
import string

import factory
import factory.fuzzy
from django.db.models import signals
from django.template.defaultfilters import slugify

from . import models

BASE36_ALPHABET = string.digits + string.ascii_lowercase


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


@factory.django.mute_signals(signals.post_save)
class RedditAccountFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: "reddit-user-{n:04}")

    class Meta:
        model = models.RedditAccount


class RedditSubmissionFactory(factory.django.DjangoModelFactory):
    id = factory.LazyFunction(lambda: "".join([random.choice(BASE36_ALPHABET) for _ in range(7)]))
    subreddit = factory.SubFactory(RedditCommunityFactory)
    author = factory.SubFactory(RedditAccountFactory)
    title = factory.fuzzy.FuzzyText(length=40)
    url = factory.Sequence(lambda n: "https://test-{n:03}.example.com")

    class Meta:
        model = models.RedditSubmission


class SelfPostFactory(RedditSubmissionFactory):
    url = factory.LazyAttribute(
        lambda o: f"https://reddit.com/r/{o.subreddit.name}/comments/{o.id}/{slugify(o.title)}"
    )
    selftext = "This is just a self-post."
    selftext_html = '<div class="md"><p>This is just a self-post.</p></div>'

    class Meta:
        model = models.RedditSubmission
