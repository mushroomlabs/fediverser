from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication

from .models import LocalUser

User = get_user_model()


class LemmyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get("jwt")
        local_user = (
            LocalUser.objects.filter(logintoken__token=token).select_related("person").first()
        )
        user = (
            local_user
            and User.objects.filter(account__lemmy_local_username=local_user.person.name).first()
            or AnonymousUser()
        )
        return (user, None)
