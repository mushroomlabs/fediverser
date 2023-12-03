import logging

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.socialaccount.signals import pre_social_login, social_account_updated
from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import LemmyMirroredPost, RedditAccount, RedditCommunity, make_reddit_user_client
from .tasks import clone_redditor, post_mirror_disclosure, subscribe_to_lemmy_community

logger = logging.getLogger(__name__)
User = get_user_model()


REDDIT_PROVIDER = "reddit"


@receiver(post_save, sender=LemmyMirroredPost)
def on_mirrored_post_created_schedule_disclosure_post(sender, **kw):
    if kw["created"] and not kw["raw"]:
        mirrored_post = kw["instance"]
        post_mirror_disclosure.delay(mirrored_post.id)


@receiver(post_save, sender=RedditAccount)
def on_reddit_account_created_make_mirror(sender, **kw):
    if kw["created"] and not kw["raw"]:
        reddit_account = kw["instance"]
        if reddit_account.controller is None:
            clone_redditor.delay(reddit_account.username, as_bot=True)


@receiver(post_save, sender=SocialAccount)
def on_reddit_user_connected_account_update_reddit_account(sender, **kw):
    social_account = kw["instance"]

    if social_account.provider == REDDIT_PROVIDER:
        reddit_username = social_account.extra_data["name"]

        reddit_account, created = RedditAccount.objects.update_or_create(
            username=reddit_username, defaults={"controller": social_account.user}
        )

        if created:
            reddit_account.register_mirror(as_bot=False)
        else:
            reddit_account.unbot_mirror()


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
def on_subreddit_added_subscribe_to_corresponding_lemmy_community(sender, **kw):
    action = kw["action"]

    if action == "post_add" and not kw["reverse"]:
        reddit_account = kw["instance"]
        if not reddit_account.is_initial_password_in_use:
            logger.warning("Account is taken over by owner, can not do anything on their behalf")
            return

        for subreddit_id in kw["pk_set"]:
            subreddit = RedditCommunity.objects.filter(id=subreddit_id).first()
            if not subreddit:
                continue
            for mapping in subreddit.reddittolemmycommunity_set.all():
                subscribe_to_lemmy_community.delay(
                    reddit_account.username, mapping.lemmy_community.id
                )
