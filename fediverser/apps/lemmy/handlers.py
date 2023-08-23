import logging

import bcrypt
from Crypto.PublicKey import RSA
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from fediverser.apps.core.models import RedditAccount

from . import models

logger = logging.getLogger(__name__)


def generate_rsa_keypair(keysize: int = 2048):
    key = RSA.generate(keysize)
    public_key_pem = key.publickey().export_key().decode()
    private_key_pem = key.export_key().decode()

    return (private_key_pem, public_key_pem)


def get_hashed_password(cleartext: str) -> str:
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(cleartext.encode(), salt=salt)
    return hashed_bytes.decode()


@receiver(post_save, sender=RedditAccount)
def on_reddit_account_created_make_mirror(sender, **kw):
    lemmy_mirror_domain = settings.LEMMY_MIRROR_INSTANCE_DOMAIN
    if kw["created"] and not kw["raw"]:
        try:
            assert lemmy_mirror_domain is not None, "No instance set as reddit mirror"
            reddit_account = kw["instance"]
            lemmy_mirror = models.Instance.objects.get(domain=lemmy_mirror_domain)
            username = reddit_account.username
            private_key, public_key = generate_rsa_keypair()

            person, _ = models.Person.objects.get_or_create(
                name=reddit_account.username,
                instance=lemmy_mirror,
                defaults={
                    "actor_id": f"https://{lemmy_mirror.domain}/u/{username}",
                    "inbox_url": f"https://{lemmy_mirror.domain}/u/{username}/inbox",
                    "shared_inbox_url": f"https://{lemmy_mirror.domain}/inbox",
                    "private_key": private_key,
                    "public_key": public_key,
                    "published": timezone.now(),
                    "last_refreshed_at": timezone.now(),
                    "local": True,
                    "bot_account": True,
                    "deleted": False,
                    "banned": False,
                    "admin": False,
                },
            )
            local_user, _ = models.LocalUser.objects.update_or_create(
                person=person,
                defaults={
                    "password_encrypted": get_hashed_password(reddit_account.password),
                    "accepted_application": True,
                },
            )

        except models.Instance.DoesNotExist:
            logger.exception("Can not find mirror instance on Lemmy")
        except AssertionError as exc:
            logger.warning(str(exc))
