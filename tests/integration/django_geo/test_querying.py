from pathlib import Path
from typing import Type

import pytest
from django.core.exceptions import ImproperlyConfigured

from odata_query.django import apply_odata_query

from .models import WorldBorder

try:
    from django.contrib.gis.db import models
    from django.contrib.gis.utils import LayerMapping
except (ImportError, ImproperlyConfigured):
    pytest.skip(allow_module_level=True, reason="Could not load GIS libraries")

# The default spatial reference system for geometry fields is WGS84
# (meaning the SRID is 4326)
SRID = "SRID=4326"


@pytest.fixture(scope="session")
def sample_data_sess(django_db, world_borders_dataset: Path):
    world_mapping = {
        "fips": "FIPS",
        "iso2": "ISO2",
        "iso3": "ISO3",
        "un": "UN",
        "name": "NAME",
        "area": "AREA",
        "pop2005": "POP2005",
        "region": "REGION",
        "subregion": "SUBREGION",
        "lon": "LON",
        "lat": "LAT",
        "mpoly": "MULTIPOLYGON",
    }

    world_shp = world_borders_dataset / "TM_WORLD_BORDERS-0.3.shp"
    lm = LayerMapping(WorldBorder, world_shp, world_mapping, transform=False)
    lm.save(strict=True, verbose=True)
    yield
    WorldBorder.objects.all().delete()


@pytest.mark.parametrize(
    "model, query, exp_results",
    [
        (
            WorldBorder,
            "geo.length(mpoly) gt 1000000",
            154,
        ),
        (
            WorldBorder,
            f"geo.intersects(mpoly, geography'{SRID};Point(-95.3385 29.7245)')",
            1,
        ),
    ],
)
def test_query_with_odata(
    model: Type[models.Model],
    query: str,
    exp_results: int,
    sample_data_sess,
):
    q = apply_odata_query(model.objects, query)
    results = q.all()
    assert len(results) == exp_results
