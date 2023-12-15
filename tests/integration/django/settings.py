from pathlib import Path

DB_DIR = Path(__file__).parent / "db"
DB_DIR.mkdir(exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DB_DIR / "odata-query"),
    },
    "geo": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": str(DB_DIR / "odata-query-geo"),
    },
}
DATABASE_ROUTERS = ["tests.integration.django.apps.DbRouter"]
DEBUG = True
INSTALLED_APPS = [
    "tests.integration.django.apps.ODataQueryConfig",
    # GEO:
    "django.contrib.gis",
    "tests.integration.django_geo.apps.ODataQueryConfig",
]
