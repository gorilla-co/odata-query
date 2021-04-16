DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "odata-query",
    }
}
DEBUG = True
INSTALLED_APPS = ["tests.integration.django.apps.ODataQueryConfig"]
