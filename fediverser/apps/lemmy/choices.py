from django.db import models


class ActorTypes(models.TextChoices):
    SITE = "site"
    COMMUNITY = "community"
    PERSON = "person"


class CommunityVisibilityTypes(models.TextChoices):
    PUBLIC = "Public"
    LOCAL = "LocalOnly"


class ListingTypes(models.TextChoices):
    ALL = "All"
    LOCAL = "Local"
    SUBSCRIBED = "Subscribed"
    MODERATOR = "ModeratorView"


class PostListingModes(models.TextChoices):
    LIST = "List"
    CARD = "Card"
    SMALLCARD = "SmallCard"


class RegistrationModels(models.TextChoices):
    CLOSED = "Closed"
    REQUIRE_APPLICATION = "RequireApplication"
    OPEN = "Open"


class SortOrderTypes(models.TextChoices):
    ACTIVE = "Active"
    HOT = "Hot"
    NEW = "New"
    OLD = "Old"
    TOP_DAY = "TopDay"
    TOP_WEEK = "TopWeek"
    TOP_MONTH = "TopMonth"
    TOP_YEAR = "TopYear"
    TOP_ALL = "TopAll"
    MOST_COMMENTS = "MostComments"
    NEW_COMMENTS = "NewComments"
    TOP_HOUR = "TopHour"
    TOP_SIXHOUR = "TopSixHour"
    TOP_TWELVEHOUR = "TopTwelveHour"
    TOP_THREEMONTHS = "TopThreeMonths"
    TOP_SIXMONTHS = "TopSixMonths"
    TOP_NINEMONTHS = "TopNineMonths"
    CONTROVERSIAL = "Controversial"
    SCALED = "Scaled"
