import random
import string

import factory
import factory.fuzzy
from django.db.models import signals
from django.template.defaultfilters import slugify

from .models.activitypub import Community, Instance, Person
from .models.mapping import RedditToCommunityRecommendation
from .models.mirroring import RedditMirrorStrategy
from .models.network import ConnectedRedditAccount, ConnectedRedditAccountEntry, FediversedInstance
from .models.reddit import RedditAccount, RedditCommunity, RedditSubmission

BASE36_ALPHABET = string.digits + string.ascii_lowercase


class InstanceFactory(factory.django.DjangoModelFactory):
    domain = factory.Sequence(lambda n: f"{n:03}.example.com")

    class Meta:
        model = Instance


class CommunityFactory(factory.django.DjangoModelFactory):
    instance = factory.SubFactory(InstanceFactory)
    name = factory.Sequence(lambda n: f"community-{n:03}")

    class Meta:
        model = Community


class RedditCommunityFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"test-subreddit-{n:03}")

    class Meta:
        model = RedditCommunity


class RedditToCommunityRecommendationFactory(factory.django.DjangoModelFactory):
    subreddit = factory.SubFactory(RedditCommunityFactory)
    community = factory.SubFactory(CommunityFactory)

    class Meta:
        model = RedditToCommunityRecommendation


class RedditMirrorStrategyFactory(factory.django.DjangoModelFactory):
    subreddit = factory.SubFactory(RedditCommunityFactory)
    community = factory.SubFactory(CommunityFactory)

    class Meta:
        model = RedditMirrorStrategy


@factory.django.mute_signals(signals.post_save)
class RedditAccountFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"reddit-user-{n:04}")

    class Meta:
        model = RedditAccount


class RedditSubmissionFactory(factory.django.DjangoModelFactory):
    id = factory.LazyFunction(lambda: "".join([random.choice(BASE36_ALPHABET) for _ in range(7)]))
    subreddit = factory.SubFactory(RedditCommunityFactory)
    author = factory.SubFactory(RedditAccountFactory)
    title = factory.fuzzy.FuzzyText(length=40)
    url = factory.Sequence(lambda n: f"https://test-{n:03}.example.com")

    class Meta:
        model = RedditSubmission


class SelfPostFactory(RedditSubmissionFactory):
    url = factory.LazyAttribute(
        lambda o: f"https://reddit.com/r/{o.subreddit.name}/comments/{o.id}/{slugify(o.title)}"
    )
    selftext = "This is just a self-post."
    selftext_html = '<div class="md"><p>This is just a self-post.</p></div>'

    class Meta:
        model = RedditSubmission


class FediversedInstanceFactory(factory.django.DjangoModelFactory):
    portal_url = factory.Sequence(lambda n: f"https://portal-{n:03d}.fediverser.example.com")

    class Meta:
        model = FediversedInstance


class ActorFactory(factory.django.DjangoModelFactory):
    instance = factory.SubFactory(InstanceFactory)
    name = factory.Sequence(lambda n: f"actor-{n:03}")
    url = factory.LazyAttribute(lambda obj: f"https://{obj.instance.domain}/u/{obj.name}")

    class Meta:
        model = Person


class ConnectedRedditAccountFactory(factory.django.DjangoModelFactory):
    reddit_account = factory.SubFactory(RedditAccountFactory)
    actor = factory.SubFactory(ActorFactory)

    class Meta:
        model = ConnectedRedditAccount


class ConnectedRedditAccountEntryFactory(factory.django.DjangoModelFactory):
    reddit_account = factory.SubFactory(RedditAccountFactory)
    actor = factory.SubFactory(ActorFactory)
    published_by = factory.SubFactory(FediversedInstanceFactory)

    class Meta:
        model = ConnectedRedditAccountEntry
