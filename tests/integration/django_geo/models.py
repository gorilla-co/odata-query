# https://docs.djangoproject.com/en/4.2/ref/contrib/gis/tutorial/#geographic-models

from django.core.exceptions import ImproperlyConfigured
from django.db import models

# This file needs to be importable even without Geo system libraries installed.
# Tests using these libraries will be skipped using pytest.skip
try:
    from django.contrib.gis.db.models import MultiPolygonField
except (ImportError, ImproperlyConfigured):
    MultiPolygonField = models.CharField


class WorldBorder(models.Model):
    # Regular Django fields corresponding to the attributes in the
    # world borders shapefile.
    name = models.CharField(max_length=50)
    area = models.IntegerField()
    pop2005 = models.IntegerField("Population 2005")
    fips = models.CharField("FIPS Code", max_length=2, null=True)
    iso2 = models.CharField("2 Digit ISO", max_length=2)
    iso3 = models.CharField("3 Digit ISO", max_length=3)
    un = models.IntegerField("United Nations Code")
    region = models.IntegerField("Region Code")
    subregion = models.IntegerField("Sub-Region Code")
    lon = models.FloatField()
    lat = models.FloatField()

    # GeoDjango-specific: a geometry field (MultiPolygonField)
    mpoly = MultiPolygonField()

    def __str__(self):
        return self.name
