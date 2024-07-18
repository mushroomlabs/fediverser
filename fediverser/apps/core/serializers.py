from rest_framework import serializers

from . import models


class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Instance
        fields = read_only_fields = ("domain", "software")


class FediversedInstanceSerializer(serializers.ModelSerializer):
    instance = InstanceSerializer()

    class Meta:
        model = models.FediversedInstance
        fields = read_only_fields = (
            "instance",
            "portal_url",
            "allows_reddit_mirrored_content",
            "allows_reddit_signup",
            "accepts_community_requests",
        )


class CommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Community
        fields = ("name", "instance", "category", "url", "fqdn")


class RedditCommunitySerializer(serializers.ModelSerializer):
    recommended_communities = CommunitySerializer(many=True, read_only=True)
    candidate_communities = CommunitySerializer(many=True, read_only=True)
    status_display = serializers.SerializerMethodField()
    category = serializers.CharField(source="category.name", read_only=True)

    def get_status_display(self, obj):
        return obj.get_status_display()

    class Meta:
        model = models.RedditCommunity
        read_only_fields = fields = (
            "id",
            "name",
            "description",
            "category",
            "locked",
            "status",
            "status_display",
            "over18",
            "full_reddit_url",
            "recommended_communities",
            "candidate_communities",
        )


class CommunityRequestSerializer(serializers.ModelSerializer):
    instance = serializers.CharField(source="instance.domain", read_only=True)
    subreddit = serializers.CharField(source="subreddit.name", read_only=True)
    description = serializers.CharField(source="subreddit.original_description", read_only=True)
    banner_image_url = serializers.URLField(source="subreddit.banner_image_url", read_only=True)
    header_image_url = serializers.URLField(source="subreddit.header_image_url", read_only=True)
    logo_image_url = serializers.URLField(source="subreddit.logo_image_url", read_only=True)

    class Meta:
        model = models.CommunityRequest
        fields = read_only_fields = (
            "instance",
            "subreddit",
            "description",
            "banner_image_url",
            "header_image_url",
            "logo_image_url",
        )


class NodeInfoSerializer(serializers.Serializer):
    url = serializers.URLField()
    registration_methods = serializers.ListField(child=serializers.CharField())
    lemmy = FediversedInstanceSerializer()
