from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def lemmy_mirror_instance():
    return settings.LEMMY_MIRROR_INSTANCE_DOMAIN


@register.filter
def lemmy_mirrored_community_url(lemmy_community):
    return f"https://{settings.LEMMY_MIRROR_INSTANCE_DOMAIN}/c/{lemmy_community.fqdn}"
