import bcrypt
import jwt
import pyotp
from Crypto.PublicKey import RSA
from django.conf import settings
from django.utils import timezone
from pythorhead import Lemmy

from . import models

# Normally, I'd just keep all business logic along with the models,
# but given that the models from this application are not managed by
# Django, I am going to treat them as a more tradititional "data
# object" only and let this services module as the place to
# access/interact with Lemmy


LEMMY_CLIENTS = {}


class LemmyClientRateLimited(Exception):
    pass


class LemmyProxyUserNotConfigured(Exception):
    pass


def generate_rsa_keypair(keysize: int = 2048):
    key = RSA.generate(keysize)
    public_key_pem = key.publickey().export_key().decode()
    private_key_pem = key.export_key().decode()

    return (private_key_pem, public_key_pem)


def get_hashed_password(cleartext: str | None) -> str:
    if cleartext is None:
        return LocalUserProxy.UNUSABLE_PASSWORD

    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(cleartext.encode(), salt=salt)
    return hashed_bytes.decode()


class InstanceProxy(models.Instance):
    def unbot(self, username):
        models.Person.objects.filter(name=username, instance=self).update(bot_account=False)

    def register(self, username, password=None, as_bot=True):
        private_key, public_key = generate_rsa_keypair()

        person, _ = models.Person.objects.get_or_create(
            name=username,
            instance=self,
            defaults={
                "actor_id": f"https://{self.domain}/u/{username}",
                "inbox_url": f"https://{self.domain}/u/{username}/inbox",
                "shared_inbox_url": f"https://{self.domain}/inbox",
                "private_key": private_key,
                "public_key": public_key,
                "published": timezone.now(),
                "last_refreshed_at": timezone.now(),
                "local": True,
                "bot_account": as_bot,
                "deleted": False,
                "banned": False,
            },
        )

        local_user, created = LocalUserProxy.objects.get_or_create(
            person=person,
            defaults={
                "password_encrypted": get_hashed_password(password),
                "accepted_application": True,
            },
        )

        if created:
            models.LocalUserVoteDisplayMode.objects.create(local_user=local_user)

        return local_user

    @classmethod
    def get_connected_instance(cls):
        return cls.objects.get(domain=settings.CONNECTED_LEMMY_INSTANCE_DOMAIN)

    class Meta:
        proxy = True


class CommunityProxy(models.Community):
    class Meta:
        proxy = True


class LocalUserProxy(models.LocalUser):
    UNUSABLE_PASSWORD = "!"

    @property
    def is_bot(self):
        return self.person.bot_account

    def __str__(self):
        return self.person.name

    def check_password(self, cleartext):
        if self.password_encrypted == self.UNUSABLE_PASSWORD:
            return False
        return bcrypt.checkpw(cleartext.encode(), self.password_encrypted.encode())

    def check_totp(self, code):
        if not bool(self.totp_2fa_secret):
            return False

        totp = pyotp.TOTP(self.totp_2fa_secret)
        return totp.verify(code)

    def make_login_token(self):
        token = models.LoginToken.objects.filter(user=self).first()

        if token:
            return token

        now = timezone.now()
        claims = {
            "sub": str(self.id),
            "iss": settings.CONNECTED_LEMMY_INSTANCE_DOMAIN,
            "iat": int(now.timestamp()),
        }

        key = models.Secret.objects.values_list("jwt_secret", flat=True).first()
        login_token = jwt.encode(claims, key, algorithm="HS256")

        return models.LoginToken.objects.create(user=self, token=login_token, published=now)

    def make_lemmy_client(self):
        global LEMMY_CLIENTS

        username = self.person.name

        if username in LEMMY_CLIENTS:
            return LEMMY_CLIENTS[username]

        domain = settings.CONNECTED_LEMMY_INSTANCE_DOMAIN

        lemmy_client = Lemmy(f"https://{domain}", raise_exceptions=True)
        login_token = self.make_login_token()
        lemmy_client._requestor._auth.token = login_token.token
        LEMMY_CLIENTS[username] = lemmy_client

        return lemmy_client

    @classmethod
    def get_mirror_user(cls, username):
        try:
            mirror_instance = InstanceProxy.objects.get(
                domain=settings.CONNECTED_LEMMY_INSTANCE_DOMAIN
            )
        except InstanceProxy.DoesNotExist:
            raise ValueError("Could not find Lemmy instance")

        return cls.objects.filter(
            person__name=username, person__instance=mirror_instance
        ).first() or mirror_instance.register(username, as_bot=True)

    @classmethod
    def get_fediverser_bot(cls):
        username = settings.FEDIVERSER_BOT_USERNAME
        password = settings.FEDIVERSER_BOT_PASSWORD

        try:
            assert username is not None, "Proxy user is not properly configured"
            assert password is not None, "Proxy user does not have a password"
        except AssertionError as exc:
            raise LemmyProxyUserNotConfigured(str(exc))

        try:
            mirror_instance = InstanceProxy.objects.get(
                domain=settings.CONNECTED_LEMMY_INSTANCE_DOMAIN
            )
        except InstanceProxy.DoesNotExist:
            raise LemmyProxyUserNotConfigured("Lemmy Mirror instance is not properly configured")

        proxy_user = cls.objects.filter(
            person__name=username, person__instance=mirror_instance
        ).first()

        if proxy_user is not None:
            return proxy_user

        return mirror_instance.register(username, password=password, as_bot=True)

    class Meta:
        proxy = True
