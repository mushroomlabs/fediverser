from allauth.account.forms import PasswordField
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .services import InstanceProxy
from .settings import app_settings


class SignupForm(forms.Form):
    username = forms.CharField(
        label=_("Username"),
        min_length=3,
        widget=forms.TextInput(attrs={"placeholder": _("Username"), "autocomplete": "username"}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "type": "email",
                "placeholder": _("Email address"),
                "autocomplete": "email",
            }
        ),
    )
    password = PasswordField(
        min_length=10,
        max_length=60,
        label=_("Password"),
        autocomplete="new-password",
        help_text="",
    )

    def clean(self):
        if not app_settings.integration_enabled:
            raise ValidationError("Lemmy Integration is not enabled")
        instance = InstanceProxy.get_connected_instance()

        if instance is None:
            raise ValidationError("Could not get Lemmy instance")

        username = self.cleaned_data["username"]

        if instance.person_set.filter(name__iexact=username).exists():
            raise ValidationError(f"Username {username} already taken")

        return self.cleaned_data

    def signup(self):
        instance = InstanceProxy.get_connected_instance()
        local_user = instance.register(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            as_bot=False,
        )
        return local_user


class SetPasswordForm(forms.Form):
    password1 = PasswordField(
        min_length=10,
        max_length=60,
        label=_("Password"),
        autocomplete="new-password",
        help_text="Password must have between 10 and 60 characters",
    )

    password2 = PasswordField(
        min_length=10,
        max_length=60,
        label=_("Password"),
        autocomplete="new-password",
        help_text="Repeat password",
    )

    def clean(self):
        if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
            raise ValidationError("Passwords do not match")
        return self.cleaned_data
