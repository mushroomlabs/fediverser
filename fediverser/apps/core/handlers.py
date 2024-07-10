import logging

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.socialaccount.signals import pre_social_login, social_account_updated
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from fediverser.apps.lemmy.services import InstanceProxy, LocalUserProxy

from .models.accounts import UserAccount
from .models.mirroring import LemmyMirroredPost
from .models.reddit import RedditAccount, RedditCommunity, make_reddit_user_client
from .tasks import post_mirror_disclosure, subscribe_to_community

logger = logging.getLogger(__name__)
User = get_user_model()


REDDIT_PROVIDER = "reddit"


@receiver(post_save, sender=LemmyMirroredPost)
def on_mirrored_post_created_schedule_disclosure_post(sender, **kw):
    if kw["created"] and not kw["raw"]:
        mirrored_post = kw["instance"]
        post_mirror_disclosure.delay(mirrored_post.id)


@receiver(post_save, sender=SocialAccount)
def on_reddit_user_login_attempt_lemmy_(sender, **kw):
    social_account = kw["instance"]

    if kw["created"] and social_account.provider == REDDIT_PROVIDER:
        reddit_username = social_account.extra_data["name"]

        reddit_account, new_redditor = RedditAccount.objects.get_or_create(
            username=reddit_username
        )

        try:
            user_account, _ = UserAccount.objects.get_or_create(
                reddit_account=reddit_account, user=social_account.user
            )
        except IntegrityError:
            logger.warning("User already is associated with different reddit account")
            return

        if user_account.lemmy_local_user is not None:
            logger.info("User is already connected on Lemmy")
            return

        homonym = LocalUserProxy.objects.filter(person__name__iexact=reddit_username).first()

        if homonym is None:
            lemmy_instance = InstanceProxy.get_connected_instance()
            lemmy_instance.register(reddit_username, as_bot=False)
            user_account.lemmy_local_username = reddit_username
            user_account.save()

        elif homonym.is_bot:
            lemmy_instance = InstanceProxy.get_connected_instance()
            lemmy_instance.unbot(reddit_username)
            user_account.lemmy_local_username = reddit_username
            user_account.save()
        else:
            logger.info("Not creating account on Lemmy because username is taken")


@receiver(pre_social_login)
def on_reddit_token_provider_get_subreddits(sender, **kw):
    social_login = kw["sociallogin"]

    social_account = social_login.account
    social_token = social_login.token
    social_application = SocialApp.objects.filter(provider=REDDIT_PROVIDER).first()

    if social_application is not None:
        reddit = make_reddit_user_client(
            social_application=social_application, refresh_token=social_token.token_secret
        )

        reddit_username = social_account.extra_data["name"]
        subreddit_names = [s.display_name for s in reddit.user.subreddits()]
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


@receiver(m2m_changed, sender=RedditAccount.subreddits.through)
def on_subreddit_added_subscribe_to_corresponding_community(sender, **kw):
    action = kw["action"]

    if action == "post_add" and not kw["reverse"]:
        reddit_account = kw["instance"]
        lemmy_user = LocalUserProxy.get_mirror_user(reddit_account.username)
        for subreddit_id in kw["pk_set"]:
            subreddit = RedditCommunity.objects.filter(id=subreddit_id).first()
            if not subreddit:
                continue
            for recommendation in subreddit.recommendations.all():
                subscribe_to_community.delay(lemmy_user.id, recommendation.community.id)
