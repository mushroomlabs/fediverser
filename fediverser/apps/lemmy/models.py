from django.db import models

from . import choices


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
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "admin_purge_comment"


class AdminPurgeCommunity(models.Model):
    admin_person = models.ForeignKey("Person", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "admin_purge_community"


class AdminPurgePerson(models.Model):
    admin_person = models.ForeignKey("Person", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "admin_purge_person"


class AdminPurgePost(models.Model):
    admin_person = models.ForeignKey("Person", models.DO_NOTHING)
    community = models.ForeignKey("Community", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "admin_purge_post"


class CaptchaAnswer(models.Model):
    uuid = models.UUIDField(primary_key=True)
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
    path = models.TextField()
    distinguished = models.BooleanField()
    language = models.ForeignKey("Language", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "comment"


class CommentAggregates(models.Model):
    comment = models.OneToOneField(Comment, models.DO_NOTHING, primary_key=True)
    score = models.BigIntegerField()
    upvotes = models.BigIntegerField()
    downvotes = models.BigIntegerField()
    published = models.DateTimeField()
    child_count = models.IntegerField()
    hot_rank = models.FloatField()
    controversy_rank = models.FloatField()

    class Meta:
        managed = False
        db_table = "comment_aggregates"


class CommentLike(models.Model):
    person = models.OneToOneField("Person", models.DO_NOTHING, primary_key=True)
    comment = models.ForeignKey(Comment, models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    score = models.SmallIntegerField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "comment_like"
        unique_together = (("person", "comment"),)


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
    person = models.OneToOneField("Person", models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "comment_saved"
        unique_together = (("person", "comment"),)


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
    followers_url = models.CharField(unique=True, max_length=255, blank=True, null=True)
    inbox_url = models.CharField(max_length=255)
    shared_inbox_url = models.CharField(max_length=255, blank=True, null=True)
    hidden = models.BooleanField()
    posting_restricted_to_mods = models.BooleanField()
    instance = models.ForeignKey("Instance", models.DO_NOTHING)
    moderators_url = models.CharField(unique=True, max_length=255, blank=True, null=True)
    featured_url = models.CharField(unique=True, max_length=255, blank=True, null=True)
    visibility = models.TextField()

    class Meta:
        managed = False
        db_table = "community"


class CommunityAggregates(models.Model):
    community = models.OneToOneField(Community, models.DO_NOTHING, primary_key=True)
    subscribers = models.BigIntegerField()
    posts = models.BigIntegerField()
    comments = models.BigIntegerField()
    published = models.DateTimeField()
    users_active_day = models.BigIntegerField()
    users_active_week = models.BigIntegerField()
    users_active_month = models.BigIntegerField()
    users_active_half_year = models.BigIntegerField()
    hot_rank = models.FloatField()
    subscribers_local = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = "community_aggregates"


class CommunityBlock(models.Model):
    person = models.OneToOneField("Person", models.DO_NOTHING, primary_key=True)
    community = models.ForeignKey(Community, models.DO_NOTHING)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "community_block"
        unique_together = (("person", "community"),)


class CommunityFollower(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    person = models.OneToOneField("Person", models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()
    pending = models.BooleanField()

    class Meta:
        managed = False
        db_table = "community_follower"
        unique_together = (("person", "community"),)


class CommunityLanguage(models.Model):
    community = models.OneToOneField(Community, models.DO_NOTHING, primary_key=True)
    language = models.ForeignKey("Language", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "community_language"
        unique_together = (("community", "language"),)


class CommunityModerator(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    person = models.OneToOneField("Person", models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "community_moderator"
        unique_together = (("person", "community"),)


class CommunityPersonBan(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    person = models.OneToOneField("Person", models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()
    expires = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "community_person_ban"
        unique_together = (("person", "community"),)


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
    custom_emoji = models.OneToOneField(CustomEmoji, models.DO_NOTHING, primary_key=True)
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
    instance = models.OneToOneField("Instance", models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "federation_allowlist"


class FederationBlocklist(models.Model):
    instance = models.OneToOneField("Instance", models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "federation_blocklist"


class FederationQueueState(models.Model):
    instance = models.OneToOneField("Instance", models.DO_NOTHING, primary_key=True)
    last_successful_id = models.BigIntegerField(blank=True, null=True)
    fail_count = models.IntegerField()
    last_retry = models.DateTimeField(blank=True, null=True)
    last_successful_published_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "federation_queue_state"


class ImageUpload(models.Model):
    local_user = models.ForeignKey("LocalUser", models.DO_NOTHING)
    pictrs_alias = models.TextField(primary_key=True)
    pictrs_delete_token = models.TextField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "image_upload"


class Instance(models.Model):
    domain = models.CharField(unique=True, max_length=255)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)
    software = models.CharField(max_length=255, blank=True, null=True)
    version = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.domain

    class Meta:
        managed = False
        db_table = "instance"


class InstanceBlock(models.Model):
    person = models.OneToOneField("Person", models.DO_NOTHING, primary_key=True)
    instance = models.ForeignKey(Instance, models.DO_NOTHING)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "instance_block"
        unique_together = (("person", "instance"),)


class Language(models.Model):
    code = models.CharField(max_length=3)
    name = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        managed = False
        db_table = "language"


class LocalImage(models.Model):
    local_user = models.ForeignKey("LocalUser", models.DO_NOTHING, blank=True, null=True)
    pictrs_alias = models.TextField(primary_key=True)
    pictrs_delete_token = models.TextField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "local_image"


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
    default_post_listing_type = models.TextField()
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
    registration_mode = models.TextField()
    reports_email_admins = models.BooleanField()
    federation_signed_fetch = models.BooleanField()
    default_post_listing_mode = models.TextField()
    default_sort_type = models.TextField()

    class Meta:
        managed = False
        db_table = "local_site"


class LocalSiteRateLimit(models.Model):
    local_site = models.OneToOneField(LocalSite, models.DO_NOTHING, primary_key=True)
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
    import_user_settings = models.IntegerField()
    import_user_settings_per_second = models.IntegerField()

    class Meta:
        managed = False
        db_table = "local_site_rate_limit"


class LocalSiteUrlBlocklist(models.Model):
    url = models.TextField(unique=True)
    published = models.DateTimeField()
    updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "local_site_url_blocklist"


class LocalUser(models.Model):
    person = models.OneToOneField("Person", models.DO_NOTHING)
    password_encrypted = models.TextField()
    email = models.TextField(unique=True, blank=True, null=True)
    show_nsfw = models.BooleanField(default=False)
    theme = models.TextField(default="browser")
    default_sort_type = models.CharField(
        max_length=30,
        choices=choices.SortOrderTypes.choices,
        default=choices.SortOrderTypes.ACTIVE,
    )
    default_listing_type = models.CharField(
        max_length=30,
        choices=choices.ListingTypes.choices,
        default=choices.ListingTypes.LOCAL,
    )
    interface_language = models.CharField(max_length=20, default="browser")
    show_avatars = models.BooleanField(default=True)
    send_notifications_to_email = models.BooleanField(default=False)
    show_scores = models.BooleanField(default=True)
    show_bot_accounts = models.BooleanField(default=True)
    show_read_posts = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    accepted_application = models.BooleanField(default=False)
    totp_2fa_secret = models.TextField(blank=True, null=True)
    open_links_in_new_tab = models.BooleanField(default=False)
    blur_nsfw = models.BooleanField(default=True)
    auto_expand = models.BooleanField(default=False)
    infinite_scroll_enabled = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    post_listing_mode = models.CharField(
        max_length=30,
        choices=choices.PostListingModes.choices,
        default=choices.PostListingModes.LIST,
    )
    totp_2fa_enabled = models.BooleanField(default=False)
    enable_keyboard_navigation = models.BooleanField(default=False)
    enable_animated_images = models.BooleanField(default=True)
    collapse_bot_comments = models.BooleanField(default=False)

    def __str__(self):
        return self.person.name

    class Meta:
        managed = False
        db_table = "local_user"


class LocalUserLanguage(models.Model):
    local_user = models.OneToOneField(LocalUser, models.DO_NOTHING, primary_key=True)
    language = models.ForeignKey(Language, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "local_user_language"
        unique_together = (("local_user", "language"),)


class LocalUserVoteDisplayMode(models.Model):
    local_user = models.OneToOneField(LocalUser, models.DO_NOTHING, primary_key=True)
    score = models.BooleanField(default=False)
    upvotes = models.BooleanField(default=True)
    downvotes = models.BooleanField(default=True)
    upvote_percentage = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "local_user_vote_display_mode"


class LoginToken(models.Model):
    token = models.TextField(primary_key=True)
    user = models.ForeignKey(LocalUser, models.DO_NOTHING)
    published = models.DateTimeField()
    ip = models.TextField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "login_token"


class ModAdd(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    other_person = models.ForeignKey(
        "Person", models.DO_NOTHING, related_name="modadd_other_person_set"
    )
    removed = models.BooleanField()
    when_field = models.DateTimeField(db_column="when_")

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
    when_field = models.DateTimeField(db_column="when_")

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
    when_field = models.DateTimeField(db_column="when_")

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
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "mod_ban_from_community"


class ModFeaturePost(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    featured = models.BooleanField()
    when_field = models.DateTimeField(db_column="when_")
    is_featured_community = models.BooleanField()

    class Meta:
        managed = False
        db_table = "mod_feature_post"


class ModHideCommunity(models.Model):
    community = models.ForeignKey(Community, models.DO_NOTHING)
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    when_field = models.DateTimeField(db_column="when_")
    reason = models.TextField(blank=True, null=True)
    hidden = models.BooleanField()

    class Meta:
        managed = False
        db_table = "mod_hide_community"


class ModLockPost(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    locked = models.BooleanField()
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "mod_lock_post"


class ModRemoveComment(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    comment = models.ForeignKey(Comment, models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    removed = models.BooleanField()
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "mod_remove_comment"


class ModRemoveCommunity(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    community = models.ForeignKey(Community, models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    removed = models.BooleanField()
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "mod_remove_community"


class ModRemovePost(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    post = models.ForeignKey("Post", models.DO_NOTHING)
    reason = models.TextField(blank=True, null=True)
    removed = models.BooleanField()
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "mod_remove_post"


class ModTransferCommunity(models.Model):
    mod_person = models.ForeignKey("Person", models.DO_NOTHING)
    other_person = models.ForeignKey(
        "Person", models.DO_NOTHING, related_name="modtransfercommunity_other_person_set"
    )
    community = models.ForeignKey(Community, models.DO_NOTHING)
    when_field = models.DateTimeField(db_column="when_")

    class Meta:
        managed = False
        db_table = "mod_transfer_community"


class PasswordResetRequest(models.Model):
    token = models.TextField()
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
    inbox_url = models.CharField(max_length=255)
    shared_inbox_url = models.CharField(max_length=255, blank=True, null=True)
    matrix_user_id = models.TextField(blank=True, null=True)
    bot_account = models.BooleanField()
    ban_expires = models.DateTimeField(blank=True, null=True)
    instance = models.ForeignKey(Instance, models.DO_NOTHING)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = "person"


class PersonAggregates(models.Model):
    person = models.OneToOneField(Person, models.DO_NOTHING, primary_key=True)
    post_count = models.BigIntegerField()
    post_score = models.BigIntegerField()
    comment_count = models.BigIntegerField()
    comment_score = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = "person_aggregates"


class PersonBan(models.Model):
    person = models.OneToOneField(Person, models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "person_ban"


class PersonBlock(models.Model):
    person = models.OneToOneField(Person, models.DO_NOTHING, primary_key=True)
    target = models.ForeignKey(Person, models.DO_NOTHING, related_name="personblock_target_set")
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "person_block"
        unique_together = (("person", "target"),)


class PersonFollower(models.Model):
    person = models.ForeignKey(Person, models.DO_NOTHING)
    follower = models.OneToOneField(
        Person, models.DO_NOTHING, primary_key=True, related_name="personfollower_follower_set"
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
    person = models.OneToOneField(Person, models.DO_NOTHING, primary_key=True)
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
    url_content_type = models.TextField(blank=True, null=True)
    alt_text = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "post"


class PostAggregates(models.Model):
    post = models.OneToOneField(Post, models.DO_NOTHING, primary_key=True)
    comments = models.BigIntegerField()
    score = models.BigIntegerField()
    upvotes = models.BigIntegerField()
    downvotes = models.BigIntegerField()
    published = models.DateTimeField()
    newest_comment_time_necro = models.DateTimeField()
    newest_comment_time = models.DateTimeField()
    featured_community = models.BooleanField()
    featured_local = models.BooleanField()
    hot_rank = models.FloatField()
    hot_rank_active = models.FloatField()
    community = models.ForeignKey(Community, models.DO_NOTHING)
    creator = models.ForeignKey(Person, models.DO_NOTHING)
    controversy_rank = models.FloatField()
    instance = models.ForeignKey(Instance, models.DO_NOTHING)
    scaled_rank = models.FloatField()

    class Meta:
        managed = False
        db_table = "post_aggregates"


class PostHide(models.Model):
    post = models.ForeignKey(Post, models.DO_NOTHING)
    person = models.OneToOneField(Person, models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "post_hide"
        unique_together = (("person", "post"),)


class PostLike(models.Model):
    post = models.ForeignKey(Post, models.DO_NOTHING)
    person = models.OneToOneField(Person, models.DO_NOTHING, primary_key=True)
    score = models.SmallIntegerField()
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "post_like"
        unique_together = (("person", "post"),)


class PostRead(models.Model):
    post = models.ForeignKey(Post, models.DO_NOTHING)
    person = models.OneToOneField(Person, models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "post_read"
        unique_together = (("person", "post"),)


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
    person = models.OneToOneField(Person, models.DO_NOTHING, primary_key=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "post_saved"
        unique_together = (("person", "post"),)


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
    ap_id = models.TextField(primary_key=True)
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


class RemoteImage(models.Model):
    link = models.TextField(unique=True)
    published = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "remote_image"


class Secret(models.Model):
    jwt_secret = models.CharField()

    class Meta:
        managed = False
        db_table = "secret"


class SentActivity(models.Model):
    id = models.BigAutoField(primary_key=True)
    ap_id = models.TextField(unique=True)
    data = models.TextField()
    sensitive = models.BooleanField()
    published = models.DateTimeField()
    send_inboxes = models.TextField()
    send_community_followers_of = models.IntegerField(blank=True, null=True)
    send_all_instances = models.BooleanField()
    actor_type = models.TextField()
    actor_apub_id = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "sent_activity"


class Site(models.Model):
    name = models.CharField(max_length=20)
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
    content_warning = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "site"


class SiteAggregates(models.Model):
    site = models.OneToOneField(Site, models.DO_NOTHING, primary_key=True)
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
    site = models.OneToOneField(Site, models.DO_NOTHING, primary_key=True)
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
