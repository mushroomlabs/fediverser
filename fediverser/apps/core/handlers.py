import logging

from allauth.account.signals import user_signed_up
from allauth.socialaccount.models import SocialAccount, SocialToken
from allauth.socialaccount.providers.reddit.provider import RedditProvider
from allauth.socialaccount.signals import pre_social_login, social_account_updated
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from fediverser.apps.lemmy.services import InstanceProxy, LocalUserProxy

from . import tasks
from .models.accounts import UserAccount
from .models.activitypub import Instance, Person
from .models.feeds import Entry, Feed
from .models.mapping import RedditToCommunityRecommendation
from .models.mirroring import LemmyMirroredPost
from .models.network import (
    ConnectedRedditAccount,
    ConnectedRedditAccountEntry,
    FediversedInstance,
    RedditToCommunityRecommendationEntry,
)
from .models.reddit import (
    RedditAccount,
    RedditCommunity,
    RedditSubmission,
    make_reddit_client,
    make_reddit_user_client,
)
from .settings import app_settings
from .signals import redditor_migrated

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(user_signed_up)
def on_user_signed_up_create_user_account(sender, **kw):
    user = kw["user"]
    UserAccount.objects.get_or_create(user=user)


@receiver(post_save, sender=LemmyMirroredPost)
def on_mirrored_post_created_schedule_disclosure_post(sender, **kw):
    if kw["created"] and not kw["raw"]:
        mirrored_post = kw["instance"]
        tasks.post_mirror_disclosure.delay(mirrored_post.id)


@receiver(post_save, sender=SocialAccount)
def on_reddit_user_login_setup_accounts(sender, **kw):
    if not app_settings.provides_automatic_lemmy_onboarding:
        logger.info("Skip lemmy user registration")
        return

    social_account = kw["instance"]
    reddit_username = social_account.extra_data["name"]

    if kw["created"] and social_account.provider == RedditProvider.id:
        user_account, _ = UserAccount.objects.get_or_create(user=social_account.user)
        if user_account.lemmy_local_user is not None:
            logger.info("User is already connected on Lemmy")
            return

        homonym = LocalUserProxy.objects.filter(person__name__iexact=reddit_username).first()

        if homonym is not None and not homonym.is_bot:
            logger.info("Not creating account on Lemmy because username is taken")

        lemmy_instance = InstanceProxy.get_connected_instance()

        if homonym is None:
            lemmy_instance.register(reddit_username, as_bot=False)

        if homonym.is_bot:
            lemmy_instance.unbot(reddit_username)

        user_account.lemmy_local_username = reddit_username
        user_account.save()

        instance, _ = Instance.objects.get_or_create(domain=lemmy_instance.domain)
        person, _ = Person.objects.get_or_create(instance=instance, name=reddit_username)

        redditor_migrated.send_robust(
            sender=RedditAccount, reddit_username=reddit_username, activitypub_actor=person
        )


@receiver(pre_social_login)
def on_reddit_token_provider_get_subreddits(sender, **kw):
    social_login = kw["sociallogin"]

    social_account = social_login.account
    social_token = social_login.token
    social_application = app_settings.reddit_social_application

    reddit = make_reddit_user_client(
        social_application=social_application, refresh_token=social_token.token_secret
    )

    reddit_username = social_account.extra_data["name"]
    subreddit_names = [
        s.display_name for s in reddit.user.subreddits() if not s.display_name.startswith("u_")
    ]
    reddit_account, _ = RedditAccount.objects.get_or_create(username=reddit_username)

    for subreddit_name in subreddit_names:
        try:
            subreddit = RedditCommunity.objects.get(name__iexact=subreddit_name)
        except RedditCommunity.DoesNotExist:
            subreddit = RedditCommunity.objects.create(name=subreddit_name)
        reddit_account.subreddits.add(subreddit)


@receiver(social_account_updated)
def on_reddit_account_updated_save_access_token(sender, **kw):
    social_login = kw["sociallogin"]
    new_token = social_login.token
    SocialToken.objects.update_or_create(
        account=social_login.account,
        app=new_token.app,
        defaults={
            "token": new_token.token,
            "token_secret": new_token.token_secret,
            "expires_at": new_token.expires_at,
        },
    )


@receiver(m2m_changed, sender=UserAccount.tracked_subreddits.through)
def on_subreddit_added_create_rss_feed(sender, **kw):
    action = kw["action"]
    if action == "post_add" and not kw["reverse"]:
        for subreddit_id in kw["pk_set"]:
            subreddit = RedditCommunity.objects.filter(id=subreddit_id).first()
            if not subreddit:
                continue
            feed_url = f"https://reddit.com/r/{subreddit.name}/hot.rss"
            tasks.fetch_feed.delay(feed_url)


@receiver(m2m_changed, sender=RedditAccount.subreddits.through)
def on_subreddit_added_subscribe_to_corresponding_community(sender, **kw):
    if not settings.FEDIVERSER_ENABLE_LEMMY_INTEGRATION:
        return

    action = kw["action"]
    if action == "post_add" and not kw["reverse"]:
        reddit_account = kw["instance"]
        lemmy_user = LocalUserProxy.get_mirror_user(reddit_account.username)
        for subreddit_id in kw["pk_set"]:
            subreddit = RedditCommunity.objects.filter(id=subreddit_id).first()
            if not subreddit:
                continue
            for recommendation in subreddit.recommendations.all():
                tasks.subscribe_to_community.delay(lemmy_user.id, recommendation.community.id)


@receiver(post_save, sender=Feed)
def on_feed_created_fetch_entries(sender, **kw):
    if kw["created"]:
        feed = kw["instance"]
        tasks.fetch_feed.delay(feed_url=feed.url)


@receiver(post_save, sender=Entry)
def on_reddit_feed_entry_get_submission(sender, **kw):
    entry = kw["instance"]

    if kw["created"] and entry.reddit_submission_id:
        reddit_name = entry.subreddit_name

        subreddit = RedditCommunity.objects.filter(
            name__iexact=reddit_name
        ).first() or RedditCommunity.fetch(reddit_name)

        client = make_reddit_client()
        post = client.submission(entry.reddit_submission_id)
        RedditSubmission.make(subreddit=subreddit, post=post)


@receiver(post_save, sender=RedditToCommunityRecommendation)
def on_recommendation_created_publish_change_feed_entry(sender, **kw):
    if kw["created"]:
        recommendation = kw["instance"]
        RedditToCommunityRecommendationEntry.objects.create(
            published_by=FediversedInstance.current(),
            subreddit=recommendation.subreddit,
            community=recommendation.community,
        )


@receiver(post_save, sender=Instance)
def on_instance_created_get_extra_information(sender, **kw):
    if kw["created"]:
        instance = kw["instance"]
        tasks.get_instance_details.delay(instance.domain)


@receiver(redditor_migrated)
def on_migrated_reddit_account_publish_entry(sender, **kw):
    our_instance = FediversedInstance.current()
    reddit_username = kw["reddit_username"]
    actor = kw["activitypub_actor"]

    reddit_account, _ = RedditAccount.objects.get_or_create(username=reddit_username)

    ConnectedRedditAccount.objects.create(reddit_account=reddit_account, actor=actor)
    ConnectedRedditAccountEntry.objects.create(
        published_by=our_instance, reddit_account=reddit_account, actor=actor
    )
