import datetime
import logging

from django.core.management.base import BaseCommand
from django.db.models import Max
from pythorhead.types import LanguageType

from fediverser.apps.core.models import (
    LemmyInstance,
    LemmyMirroredComment,
    LemmyMirroredPost,
    RedditAccount,
    RedditSubmission,
    RedditToLemmyCommunity,
)

logger = logging.getLogger(__name__)


LEMMY_CLIENTS = {}


def make_lemmy_client(reddit_account: RedditAccount):
    global LEMMY_CLIENTS

    if reddit_account.username in LEMMY_CLIENTS:
        return LEMMY_CLIENTS[reddit_account.username]

    lemmy_mirror = LemmyInstance.get_reddit_mirror()

    lemmy_client = lemmy_mirror._get_client()
    lemmy_client.log_in(reddit_account.username, reddit_account.password)
    LEMMY_CLIENTS[reddit_account.username] = lemmy_client

    return lemmy_client


def make_mirror_comment(reddit_comment, lemmy_community, mirrored_post, lemmy_parent_id=None):
    lemmy_client = make_lemmy_client[reddit_comment.author]
    community_id = lemmy_client.discover_community(lemmy_community.fqdn)
    try:
        language = LanguageType[reddit_comment.language_code.upper()]
    except (KeyError, ValueError):
        language = LanguageType.Undefined

    params = dict(
        post_id=mirrored_post.lemmy_post_id,
        community_id=community_id,
        content=reddit_comment.body,
        language_id=language.value,
        parent_id=lemmy_parent_id,
    )

    lemmy_comment = lemmy_client.comment.create(**params)
    mirrored_comment = LemmyMirroredComment.objects.create(
        lemmy_mirrored_post=mirrored_post,
        reddit_comment=reddit_comment,
        lemmy_comment_id=lemmy_comment["id"],
    )

    for reply in reddit_comment.children.all():
        make_mirror_comment(
            reddit_comment, lemmy_community, mirrored_post, lemmy_parent_id=lemmy_comment["id"]
        )

    return mirrored_comment


class Command(BaseCommand):
    help = "Take new posts from all tracked subreddits and posts to related lemmy communities"

    def handle(self, *args, **options):
        NOW = datetime.datetime.now()
        EPOCH = NOW - datetime.timedelta(hours=12)

        last_run = (
            LemmyMirroredPost.objects.aggregate(latest=Max("created")).get("latest") or EPOCH
        )

        reddit_posts = RedditSubmission.objects.filter(created__gte=last_run).select_related(
            "author"
        )

        for reddit_post in reddit_posts:
            for lemmy_community in RedditToLemmyCommunity(subreddit=reddit_post.subreddit):
                mirrored_post = LemmyMirroredPost.objects.filter(
                    reddit_submission=reddit_post, lemmy_community=lemmy_community
                ).first()
                if mirrored_post is None:
                    lemmy_client = make_lemmy_client[reddit_post.author]
                    community_id = lemmy_client.discover_community(lemmy_community.fqdn)
                    try:
                        language = LanguageType[reddit_post.language_code.upper()]
                    except (KeyError, ValueError):
                        language = LanguageType.Undefined

                    params = dict(
                        community_id=community_id,
                        name=reddit_post.title,
                        nsfw=reddit_post.over_18,
                        language_id=language.value,
                    )
                    if reddit_post.is_self_post:
                        params["body"] = reddit_post.selftext
                    else:
                        params["url"] = reddit_post.url

                    lemmy_post = lemmy_client.post.create(**params)
                    mirrored_post = LemmyMirroredPost.objects.create(
                        reddit_submission=reddit_post,
                        lemmy_post_id=lemmy_post["id"],
                        lemmy_community=lemmy_community,
                    )
                for reddit_comment in reddit_post.comments.filter(parent=None).select_related(
                    "author"
                ):
                    mirrored_comment = mirrored_post.comments.filter(
                        reddit_comment=reddit_comment
                    ).first()

                    if mirrored_comment is None:
                        mirrored_comment = make_mirror_comment(
                            reddit_comment, lemmy_community, mirrored_post
                        )
