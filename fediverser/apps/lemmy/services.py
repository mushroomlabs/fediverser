import bcrypt
import jwt
import pyotp
from django.conf import settings
from django.utils import timezone

from . import models

# Normally, I'd just keep all business logic along with the models,
# but given that the models from this application are not managed by
# Django, I am going to treat them as a more tradititional "data
# pbject" only and let this services module as the place to
# access/interact with Lemmy.


class LocalUserProxy(models.LocalUser):
    def __str__(self):
        return self.person.name

    def check_password(self, cleartext):
        return bcrypt.checkpw(cleartext.encode(), self.password_encrypted.encode())

    def check_totp(self, code):
        if not bool(self.totp_2fa_secret):
            return False

        totp = pyotp.TOTP(self.totp_2fa_secret)
        return totp.verify(code)

    def make_login_token(self):
        now = timezone.now()
        claims = {
            "sub": str(self.id),
            "iss": settings.LEMMY_MIRROR_INSTANCE_DOMAIN,
            "iat": int(now.timestamp()),
        }

        key = models.Secret.objects.values_list("jwt_secret", flat=True).first()
        login_token = jwt.encode(claims, key, algorithm="HS256")

        return models.LoginToken.objects.create(user=self, token=login_token, published=now)

    class Meta:
        proxy = True
