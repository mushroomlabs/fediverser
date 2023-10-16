from django.conf import settings
from django.db import models
from pythorhead import Lemmy


class DieselSchemaMigrations(models.Model):
    version = models.CharField(primary_key=True, max_length=50)
    run_on = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "__diesel_schema_migrations"


class AdminPurgeComment(models.Model):
    admin_person = models.ForeignKey("Person", models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "admin_purge_comment"


class AdminPurgeCommunity(models.Model):
    admin_person = models.ForeignKey("Person", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "admin_purge_community"


class AdminPurgePerson(models.Model):
    admin_person = models.ForeignKey("Person", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "admin_purge_person"


class AdminPurgePost(models.Model):
    admin_person = models.ForeignKey("Person", models.DO_NOTHING)
    community = models.ForeignKey("Community", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "admin_purge_post"


class CaptchaAnswer(models.Model):
    uuid = models.UUIDField(unique=True)
    answer = models.TextField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "captcha_answer"


class Comment(models.Model):
    creator = models.ForeignKey("Person", models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    content = models.TextField()
    removed = models.BooleanField()
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    deleted = models.BooleanField()
    ap_id = models.CharField(unique=True, max_length=255)
    local = models.BooleanField()
    path = models.TextField()  # This field type is a guess.
    distinguished = models.BooleanField()
    language = models.ForeignKey("Language", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "comment"


class CommentAggregates(models.Model):
    comment = models.OneToOneField(Comment, models.DO_NOTHING)
    score = models.BigIntegerField()
    upvotes = models.BigIntegerField()
    downvotes = models.BigIntegerField()
    published = models.DateTimeField()
    child_count = models.IntegerField()
    hot_rank = models.IntegerField()

    class Meta:
        managed = False
        db_table = "comment_aggregates"


class CommentLike(models.Model):
    person = models.ForeignKey("Person", models.DO_NOTHING)
    comment = models.ForeignKey(Comment, models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    score = models.SmallIntegerField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "comment_like"
        unique_together = (("comment", "person"),)


class CommentReply(models.Model):
    recipient = models.ForeignKey("Person", models.DO_NOTHING)
    comment = models.ForeignKey(Comment, models.DO_NOTHING)
    read = models.BooleanField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "comment_reply"
        unique_together = (("recipient", "comment"),)


class CommentReport(models.Model):
    creator = models.ForeignKey("Person", models.DO_NOTHING)
    comment = models.ForeignKey(Comment, models.DO_NOTHING)
    original_comment_text = models.TextField()
    reason = models.TextField()
    resolved = models.BooleanField()
    resolver = models.ForeignKey(
        "Person",
        models.DO_NOTHING,
        related_name="commentreport_resolver_set",
        blank=True,
        null=True,
    )
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "comment_report"
        unique_together = (("comment", "creator"),)


class CommentSaved(models.Model):
    comment = models.ForeignKey(Comment, models.DO_NOTHING)
    person = models.ForeignKey("Person", models.DO_NOTHING)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "comment_saved"
        unique_together = (("comment", "person"),)


class Community(models.Model):
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    removed = models.BooleanField()
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    deleted = models.BooleanField()
    nsfw = models.BooleanField()
    actor_id = models.CharField(unique=True, max_length=255)
    local = models.BooleanField()
    private_key = models.TextField(blank=True, null=True)
    public_key = models.TextField()
    last_refreshed_at = models.DateTimeField()
    icon = models.TextField(blank=True, null=True)
    banner = models.TextField(blank=True, null=True)
    followers_url = models.CharField(unique=True, max_length=255)
    inbox_url = models.CharField(unique=True, max_length=255)
    shared_inbox_url = models.CharField(max_length=255, blank=True, null=True)
    hidden = models.BooleanField()
    posting_restricted_to_mods = models.BooleanField()
    instance = models.ForeignKey("Instance", models.DO_NOTHING)
    moderators_url = models.CharField(unique=True, max_length=255, blank=True, null=True)
    featured_url = models.CharField(unique=True, max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "community"


class CommunityAggregates(models.Model):
    community = models.OneToOneField(Community, models.DO_NOTHING)
    subscribers = models.BigIntegerField()
    posts = models.BigIntegerField()
    comments = models.BigIntegerField()
    published = models.DateTimeField()
    users_active_day = models.BigIntegerField()
    users_active_week = models.BigIntegerField()
    users_active_month = models.BigIntegerField()
    users_active_half_year = models.BigIntegerField()
    hot_rank = models.IntegerField()

    class Meta:
        managed = False
        db_table = "community_aggregates"


class CommunityBlock(models.Model):
    person = models.ForeignKey("Person", models.DO_NOTHING)
    community = models.ForeignKey(Community, models.DO_NOTHING)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "community_block"
        unique_together = (("person", "community"),)


class CommunityFollower(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    person = models.ForeignKey("Person", models.DO_NOTHING)
    published = models.DateTimeField()
    pending = models.BooleanField()

    class Meta:
        managed = False
        db_table = "community_follower"
        unique_together = (("community", "person"),)


class CommunityLanguage(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    language = models.ForeignKey("Language", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "community_language"
        unique_together = (("community", "language"),)


class CommunityModerator(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    person = models.ForeignKey("Person", models.DO_NOTHING)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "community_moderator"
        unique_together = (("community", "person"),)


class CommunityPersonBan(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    person = models.ForeignKey("Person", models.DO_NOTHING)
    published = models.DateTimeField()
    expires = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "community_person_ban"
        unique_together = (("community", "person"),)


class CustomEmoji(models.Model):
    local_site = models.ForeignKey("LocalSite", models.DO_NOTHING)
    shortcode = models.CharField(unique=True, max_length=128)
    image_url = models.TextField(unique=True)
    alt_text = models.TextField()
    category = models.TextField()
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "custom_emoji"


class CustomEmojiKeyword(models.Model):
    custom_emoji = models.ForeignKey(CustomEmoji, models.DO_NOTHING)
    keyword = models.CharField(max_length=128)

    class Meta:
        managed = False
        db_table = "custom_emoji_keyword"
        unique_together = (("custom_emoji", "keyword"),)


class EmailVerification(models.Model):
    local_user = models.ForeignKey("LocalUser", models.DO_NOTHING)
    email = models.TextField()
    verification_token = models.TextField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "email_verification"


class FederationAllowlist(models.Model):
    instance = models.OneToOneField("Instance", models.DO_NOTHING)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "federation_allowlist"


class FederationBlocklist(models.Model):
    instance = models.OneToOneField("Instance", models.DO_NOTHING)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "federation_blocklist"


class Instance(models.Model):
    domain = models.CharField(unique=True, max_length=255)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    software = models.CharField(max_length=255, blank=True, null=True)
    version = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.domain

    def _get_client(self):
        return Lemmy(f"https://{self.domain}", raise_exceptions=True)

    @classmethod
    def get_reddit_mirror(cls):
        return cls.objects.get(domain=settings.LEMMY_MIRROR_INSTANCE_DOMAIN)

    class Meta:
        managed = False
        db_table = "instance"


class Language(models.Model):
    code = models.CharField(max_length=3)
    name = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        managed = False
        db_table = "language"


class LocalSite(models.Model):
    site = models.OneToOneField("Site", models.DO_NOTHING)
    site_setup = models.BooleanField()
    enable_downvotes = models.BooleanField()
    enable_nsfw = models.BooleanField()
    community_creation_admin_only = models.BooleanField()
    require_email_verification = models.BooleanField()
    application_question = models.TextField(blank=True, null=True)
    private_instance = models.BooleanField()
    default_theme = models.TextField()
    default_post_listing_type = models.TextField()  # This field type is a guess.
    legal_information = models.TextField(blank=True, null=True)
    hide_modlog_mod_names = models.BooleanField()
    application_email_admins = models.BooleanField()
    slur_filter_regex = models.TextField(blank=True, null=True)
    actor_name_max_length = models.IntegerField()
    federation_enabled = models.BooleanField()
    captcha_enabled = models.BooleanField()
    captcha_difficulty = models.CharField(max_length=255)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    registration_mode = models.TextField()  # This field type is a guess.
    reports_email_admins = models.BooleanField()

    class Meta:
        managed = False
        db_table = "local_site"


class LocalSiteRateLimit(models.Model):
    local_site = models.OneToOneField(LocalSite, models.DO_NOTHING)
    message = models.IntegerField()
    message_per_second = models.IntegerField()
    post = models.IntegerField()
    post_per_second = models.IntegerField()
    register = models.IntegerField()
    register_per_second = models.IntegerField()
    image = models.IntegerField()
    image_per_second = models.IntegerField()
    comment = models.IntegerField()
    comment_per_second = models.IntegerField()
    search = models.IntegerField()
    search_per_second = models.IntegerField()
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "local_site_rate_limit"


class LocalUser(models.Model):
    person = models.OneToOneField("Person", models.DO_NOTHING)
    password_encrypted = models.TextField()
    email = models.TextField(unique=True, blank=True, null=True)
    show_nsfw = models.BooleanField(default=False)
    theme = models.TextField(default="browser")
    default_sort_type = models.TextField(default="Active")
    default_listing_type = models.TextField(default="Local")
    interface_language = models.CharField(max_length=20)
    show_avatars = models.BooleanField(default=True)
    send_notifications_to_email = models.BooleanField(default=False)
    validator_time = models.DateTimeField(auto_now_add=True)
    show_scores = models.BooleanField(default=False)
    show_bot_accounts = models.BooleanField(default=True)
    show_read_posts = models.BooleanField(default=False)
    show_new_post_notifs = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    accepted_application = models.BooleanField(default=False)
    totp_2fa_secret = models.TextField(blank=True, null=True)
    totp_2fa_url = models.TextField(blank=True, null=True)
    open_links_in_new_tab = models.BooleanField(default=True)
    infinite_scroll_enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.person.name

    class Meta:
        managed = False
        db_table = "local_user"


class LocalUserLanguage(models.Model):
    local_user = models.ForeignKey(LocalUser, models.DO_NOTHING)
    language = models.ForeignKey(Language, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "local_user_language"
        unique_together = (("local_user", "language"),)


class ModAdd(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    other_person = models.ForeignKey(
        "Person", models.DO_NOTHING, related_name="modadd_other_person_set"
    )
    removed = models.BooleanField()
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_add"


class ModAddCommunity(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    other_person = models.ForeignKey(
        "Person", models.DO_NOTHING, related_name="modaddcommunity_other_person_set"
    )
    community = models.ForeignKey(Community, models.DO_NOTHING)
    removed = models.BooleanField()
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_add_community"


class ModBan(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    other_person = models.ForeignKey(
        "Person", models.DO_NOTHING, related_name="modban_other_person_set"
    )
    reason = models.TextField(blank=True, null=True)
    banned = models.BooleanField()
    expires = models.DateTimeField(blank=True, null=True)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_ban"


class ModBanFromCommunity(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    other_person = models.ForeignKey(
        "Person", models.DO_NOTHING, related_name="modbanfromcommunity_other_person_set"
    )
    community = models.ForeignKey(Community, models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    banned = models.BooleanField()
    expires = models.DateTimeField(blank=True, null=True)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_ban_from_community"


class ModFeaturePost(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    featured = models.BooleanField()
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.
    is_featured_community = models.BooleanField()

    class Meta:
        managed = False
        db_table = "mod_feature_post"


class ModHideCommunity(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.
    reason = models.TextField(blank=True, null=True)
    hidden = models.BooleanField()

    class Meta:
        managed = False
        db_table = "mod_hide_community"


class ModLockPost(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    locked = models.BooleanField()
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_lock_post"


class ModRemoveComment(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    comment = models.ForeignKey(Comment, models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    removed = models.BooleanField()
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_remove_comment"


class ModRemoveCommunity(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    community = models.ForeignKey(Community, models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    removed = models.BooleanField()
    expires = models.DateTimeField(blank=True, null=True)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_remove_community"


class ModRemovePost(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    removed = models.BooleanField()
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_remove_post"


class ModTransferCommunity(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    other_person = models.ForeignKey(
        "Person", models.DO_NOTHING, related_name="modtransfercommunity_other_person_set"
    )
    community = models.ForeignKey(Community, models.DO_NOTHING)
    when_field = models.DateTimeField(
        db_column="when_"
    )  # Field renamed because it ended with '_'.

    class Meta:
        managed = False
        db_table = "mod_transfer_community"


class PasswordResetRequest(models.Model):
    token_encrypted = models.TextField()
    published = models.DateTimeField()
    local_user = models.ForeignKey(LocalUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "password_reset_request"


class Person(models.Model):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.TextField(blank=True, null=True)
    banned = models.BooleanField()
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    actor_id = models.CharField(unique=True, max_length=255)
    bio = models.TextField(blank=True, null=True)
    local = models.BooleanField()
    private_key = models.TextField(blank=True, null=True)
    public_key = models.TextField()
    last_refreshed_at = models.DateTimeField()
    banner = models.TextField(blank=True, null=True)
    deleted = models.BooleanField()
    inbox_url = models.CharField(unique=True, max_length=255)
    shared_inbox_url = models.CharField(max_length=255, blank=True, null=True)
    matrix_user_id = models.TextField(blank=True, null=True)
    admin = models.BooleanField()
    bot_account = models.BooleanField()
    ban_expires = models.DateTimeField(blank=True, null=True)
    instance = models.ForeignKey(Instance, models.DO_NOTHING)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = "person"


class PersonAggregates(models.Model):
    person = models.OneToOneField(Person, models.DO_NOTHING)
    post_count = models.BigIntegerField()
    post_score = models.BigIntegerField()
    comment_count = models.BigIntegerField()
    comment_score = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = "person_aggregates"


class PersonBan(models.Model):
    person = models.OneToOneField(Person, models.DO_NOTHING)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "person_ban"


class PersonBlock(models.Model):
    person = models.ForeignKey(Person, models.DO_NOTHING)
    target = models.ForeignKey(Person, models.DO_NOTHING, related_name="personblock_target_set")
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "person_block"
        unique_together = (("person", "target"),)


class PersonFollower(models.Model):
    person = models.ForeignKey(Person, models.DO_NOTHING)
    follower = models.ForeignKey(
        Person, models.DO_NOTHING, related_name="personfollower_follower_set"
    )
    published = models.DateTimeField()
    pending = models.BooleanField()

    class Meta:
        managed = False
        db_table = "person_follower"
        unique_together = (("follower", "person"),)


class PersonMention(models.Model):
    recipient = models.ForeignKey(Person, models.DO_NOTHING)
    comment = models.ForeignKey(Comment, models.DO_NOTHING)
    read = models.BooleanField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "person_mention"
        unique_together = (("recipient", "comment"),)


class PersonPostAggregates(models.Model):
    person = models.ForeignKey(Person, models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    read_comments = models.BigIntegerField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "person_post_aggregates"
        unique_together = (("person", "post"),)


class Post(models.Model):
    name = models.CharField(max_length=200)
    url = models.CharField(max_length=512, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    creator = models.ForeignKey(Person, models.DO_NOTHING)
    community = models.ForeignKey(Community, models.DO_NOTHING)
    removed = models.BooleanField()
    locked = models.BooleanField()
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    deleted = models.BooleanField()
    nsfw = models.BooleanField()
    embed_title = models.TextField(blank=True, null=True)
    embed_description = models.TextField(blank=True, null=True)
    thumbnail_url = models.TextField(blank=True, null=True)
    ap_id = models.CharField(unique=True, max_length=255)
    local = models.BooleanField()
    embed_video_url = models.TextField(blank=True, null=True)
    language = models.ForeignKey(Language, models.DO_NOTHING)
    featured_community = models.BooleanField()
    featured_local = models.BooleanField()

    class Meta:
        managed = False
        db_table = "post"


class PostAggregates(models.Model):
    post = models.OneToOneField(Post, models.DO_NOTHING)
    comments = models.BigIntegerField()
    score = models.BigIntegerField()
    upvotes = models.BigIntegerField()
    downvotes = models.BigIntegerField()
    published = models.DateTimeField()
    newest_comment_time_necro = models.DateTimeField()
    newest_comment_time = models.DateTimeField()
    featured_community = models.BooleanField()
    featured_local = models.BooleanField()
    hot_rank = models.IntegerField()
    hot_rank_active = models.IntegerField()
    community = models.ForeignKey(Community, models.DO_NOTHING)
    creator = models.ForeignKey(Person, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "post_aggregates"


class PostLike(models.Model):
    post = models.ForeignKey(Post, models.DO_NOTHING)
    person = models.ForeignKey(Person, models.DO_NOTHING)
    score = models.SmallIntegerField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "post_like"
        unique_together = (("post", "person"),)


class PostRead(models.Model):
    post = models.ForeignKey(Post, models.DO_NOTHING)
    person = models.ForeignKey(Person, models.DO_NOTHING)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "post_read"
        unique_together = (("post", "person"),)


class PostReport(models.Model):
    creator = models.ForeignKey(Person, models.DO_NOTHING)
    post = models.ForeignKey(Post, models.DO_NOTHING)
    original_post_name = models.CharField(max_length=200)
    original_post_url = models.TextField(blank=True, null=True)
    original_post_body = models.TextField(blank=True, null=True)
    reason = models.TextField()
    resolved = models.BooleanField()
    resolver = models.ForeignKey(
        Person, models.DO_NOTHING, related_name="postreport_resolver_set", blank=True, null=True
    )
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "post_report"
        unique_together = (("post", "creator"),)


class PostSaved(models.Model):
    post = models.ForeignKey(Post, models.DO_NOTHING)
    person = models.ForeignKey(Person, models.DO_NOTHING)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "post_saved"
        unique_together = (("post", "person"),)


class PrivateMessage(models.Model):
    creator = models.ForeignKey(Person, models.DO_NOTHING)
    recipient = models.ForeignKey(
        Person, models.DO_NOTHING, related_name="privatemessage_recipient_set"
    )
    content = models.TextField()
    deleted = models.BooleanField()
    read = models.BooleanField()
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    ap_id = models.CharField(unique=True, max_length=255)
    local = models.BooleanField()

    class Meta:
        managed = False
        db_table = "private_message"


class PrivateMessageReport(models.Model):
    creator = models.ForeignKey(Person, models.DO_NOTHING)
    private_message = models.ForeignKey(PrivateMessage, models.DO_NOTHING)
    original_pm_text = models.TextField()
    reason = models.TextField()
    resolved = models.BooleanField()
    resolver = models.ForeignKey(
        Person,
        models.DO_NOTHING,
        related_name="privatemessagereport_resolver_set",
        blank=True,
        null=True,
    )
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "private_message_report"
        unique_together = (("private_message", "creator"),)


class ReceivedActivity(models.Model):
    id = models.BigAutoField(primary_key=True)
    ap_id = models.TextField(unique=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "received_activity"


class RegistrationApplication(models.Model):
    local_user = models.OneToOneField(LocalUser, models.DO_NOTHING)
    answer = models.TextField()
    admin = models.ForeignKey(Person, models.DO_NOTHING, blank=True, null=True)
    deny_reason = models.TextField(blank=True, null=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "registration_application"


class Secret(models.Model):
    jwt_secret = models.CharField()

    class Meta:
        managed = False
        db_table = "secret"


class SentActivity(models.Model):
    id = models.BigAutoField(primary_key=True)
    ap_id = models.TextField(unique=True)
    data = models.TextField()  # This field type is a guess.
    sensitive = models.BooleanField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "sent_activity"


class Site(models.Model):
    name = models.CharField(unique=True, max_length=20)
    sidebar = models.TextField(blank=True, null=True)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    icon = models.TextField(blank=True, null=True)
    banner = models.TextField(blank=True, null=True)
    description = models.CharField(max_length=150, blank=True, null=True)
    actor_id = models.CharField(unique=True, max_length=255)
    last_refreshed_at = models.DateTimeField()
    inbox_url = models.CharField(max_length=255)
    private_key = models.TextField(blank=True, null=True)
    public_key = models.TextField()
    instance = models.OneToOneField(Instance, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "site"


class SiteAggregates(models.Model):
    site = models.ForeignKey(Site, models.DO_NOTHING)
    users = models.BigIntegerField()
    posts = models.BigIntegerField()
    comments = models.BigIntegerField()
    communities = models.BigIntegerField()
    users_active_day = models.BigIntegerField()
    users_active_week = models.BigIntegerField()
    users_active_month = models.BigIntegerField()
    users_active_half_year = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = "site_aggregates"


class SiteLanguage(models.Model):
    site = models.ForeignKey(Site, models.DO_NOTHING)
    language = models.ForeignKey(Language, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "site_language"
        unique_together = (("site", "language"),)


class Tagline(models.Model):
    local_site = models.ForeignKey(LocalSite, models.DO_NOTHING)
    content = models.TextField()
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "tagline"
