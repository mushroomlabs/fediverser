from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse


class FediverserSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        return reverse("fediverser-core:portal-home")
