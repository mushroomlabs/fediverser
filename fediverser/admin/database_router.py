class InternalRouter:
    """
    A router to control all database operations except the one from the lemmy db
    """

    route_app_labels = {"lemmy"}

    def db_for_read(self, model, **hints):
        """
        Attempts to read auth and contenttypes models go to auth_db.
        """
        if model._meta.app_label in self.route_app_labels:
            return "lemmy"
        return "default"

    def db_for_write(self, model, **hints):
        """
        Attempts to write auth and contenttypes models go to auth_db.
        """
        if model._meta.app_label in self.route_app_labels:
            return "lemmy"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the auth or contenttypes apps is
        involved.
        """
        return self.db_for_write(obj1) == self.db_for_write(obj2)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return app_label not in self.route_app_labels
