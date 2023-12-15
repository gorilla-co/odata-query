from django.apps import AppConfig


class ODataQueryConfig(AppConfig):
    name = "tests.integration.django"
    verbose_name = "OData Query Django test app"
    default = True


class DbRouter:
    """
    Ensure that GeoDjango models go to the SpatiaLite database, while other
    models use the default SQLite database.
    """

    GEO_APP = "django_geo"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.GEO_APP:
            return "geo"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.GEO_APP:
            return "geo"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._meta.app_label == obj2._meta.app_label

    def allow_migrate(self, db: str, app_label: str, model_name=None, **hints):
        if app_label != self.GEO_APP and db == "default":
            return True
        if app_label == self.GEO_APP and db == "geo":
            return True
        return False
