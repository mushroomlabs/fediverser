from django.db.models import Q
from rest_framework import serializers

from .services import LocalUserProxy


class LemmyLoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField(write_only=True)
    totp_2fa_token = serializers.CharField(required=False, write_only=True)
    password = serializers.CharField(write_only=True)
    jwt = serializers.CharField(read_only=True)
    registration_created = serializers.BooleanField(read_only=True)
    verify_email_sent = serializers.BooleanField(read_only=True)

    def validate(self, attrs):
        try:
            username_q = Q(person__name=attrs["username_or_email"])
            email_q = Q(email=attrs["username_or_email"])
            local_user = LocalUserProxy.objects.select_related("person").get(username_q | email_q)
            attrs["local_user"] = local_user
            otp_code = attrs.get("totp_2fa_token")

            if local_user.totp_2fa_enabled and not otp_code:
                raise serializers.ValidationError("missing_totp_token")

            if local_user.totp_2fa_enabled and otp_code:
                assert local_user.check_totp(otp_code), "incorrect_login"
            assert local_user.check_password(attrs["password"]), "incorrect_login"
        except LocalUserProxy.DoesNotExist:
            raise serializers.ValidationError("incorrect_login")
        except AssertionError as exc:
            raise serializers.ValidationError(str(exc))
        return attrs

    def create(self, validated_data):
        local_user = validated_data["local_user"]
        login_token = local_user.make_login_token()
        return {
            "jwt": login_token.token,
            "registration_created": False,
            "verify_email_sent": False,
        }
