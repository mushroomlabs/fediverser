from collections.abc import Mapping

from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer

from .models.activitypub import Community, Instance
from .models.mapping import CommunityRequest
from .models.network import (
    ChangeFeedEntry,
    ConnectedRedditAccountEntry,
    EndorsementEntry,
    FediversedInstance,
    RedditToCommunityRecommendationEntry,
)
from .models.reddit import RedditCommunity


class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instance
        fields = read_only_fields = ("url", "software", "description", "over18")


class InstanceRecommendationSerializer(serializers.ModelSerializer):
    signup_url = serializers.SerializerMethodField()
    score = serializers.FloatField()

    def get_signup_url(self, obj):
        try:
            assert obj.fediverser_configuration.allows_reddit_signup
            return f"{obj.fediverser_configuration.portal_url}/reddit/connect"
        except (AssertionError, AttributeError):
            return f"{obj.url}/signup"

    class Meta:
        model = Instance
        fields = read_only_fields = ("domain", "signup_url", "description", "score")


class FediversedInstanceSerializer(serializers.ModelSerializer):
    instance = InstanceSerializer(read_only=True)

    def validate(self, attrs):
        url = attrs["portal_url"]
        if self.Meta.model.objects.filter(portal_url=url).exists():
            raise serializers.ValidationError(f"{url} is already registered")
        return attrs

    def create(self, validated_data):
        url = validated_data["portal_url"]
        return self.Meta.model.fetch(url)

    class Meta:
        model = FediversedInstance
        fields = (
            "instance",
            "portal_url",
            "allows_reddit_mirrored_content",
            "allows_reddit_signup",
            "accepts_community_requests",
        )
        read_only_fields = (
            "instance",
            "allows_reddit_mirrored_content",
            "allows_reddit_signup",
            "accepts_community_requests",
        )


class CommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Community
        fields = ("name", "instance", "category", "url", "fqdn")


class RedditCommunitySerializer(serializers.ModelSerializer):
    recommended_communities = CommunitySerializer(many=True, read_only=True)
    candidate_communities = CommunitySerializer(many=True, read_only=True)
    status_display = serializers.SerializerMethodField()
    category = serializers.CharField(source="category.name", read_only=True)

    def get_status_display(self, obj):
        return obj.get_status_display()

    class Meta:
        model = RedditCommunity
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
        model = CommunityRequest
        fields = read_only_fields = (
            "instance",
            "subreddit",
            "description",
            "banner_image_url",
            "header_image_url",
            "logo_image_url",
        )


class ChangeFeedEntrySerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="fediverser-core:changefeedentry-detail")
    type = serializers.SerializerMethodField()

    def get_type(self, obj):
        return obj.TYPE

    class Meta:
        model = ChangeFeedEntry
        fields = read_only_fields = ("url", "description", "type", "created")


class ConnectedRedditAccountEntrySerializer(ChangeFeedEntrySerializer):
    reddit_account = serializers.CharField(source="connection.reddit_account.username")
    actor = serializers.CharField(source="connection.actor.url")

    class Meta:
        model = ConnectedRedditAccountEntry
        fields = read_only_fields = ChangeFeedEntrySerializer.Meta.fields + (
            "reddit_account",
            "actor",
        )


class EndorsementEntrySerializer(ChangeFeedEntrySerializer):
    endorser = serializers.CharField(source="endorsement.endorser.portal_url")
    endorsed = serializers.CharField(source="endorsement.endorsed.portal_url")

    class Meta:
        model = ConnectedRedditAccountEntry
        fields = read_only_fields = ChangeFeedEntrySerializer.Meta.fields + (
            "endorser",
            "endorsed",
        )


class RedditToCommunityRecommendationEntrySerializer(ChangeFeedEntrySerializer):
    subreddit = serializers.CharField(source="subreddit.name")
    community = serializers.CharField(source="community.url")

    class Meta:
        model = RedditToCommunityRecommendationEntry
        fields = read_only_fields = ChangeFeedEntrySerializer.Meta.fields + (
            "subreddit",
            "community",
        )


class PolymorphicChangeFeedEntrySerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        ConnectedRedditAccountEntry: ConnectedRedditAccountEntrySerializer,
        EndorsementEntry: EndorsementEntrySerializer,
        RedditToCommunityRecommendationEntry: RedditToCommunityRecommendationEntrySerializer,
    }

    def to_representation(self, instance):
        if isinstance(instance, Mapping):
            resource_type = self._get_resource_type_from_mapping(instance)
            serializer = self._get_serializer_from_resource_type(resource_type)
        else:
            resource_type = self.to_resource_type(instance)
            serializer = self._get_serializer_from_model_or_instance(instance)

        return serializer.to_representation(instance)
