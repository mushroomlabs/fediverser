class RejectedComment(Exception):
    pass


class RejectedPost(Exception):
    pass


class LemmyClientRateLimited(Exception):
    pass


class LemmyProxyUserNotConfigured(Exception):
    pass
