import urllib.request as req
from pathlib import Path
from zipfile import ZipFile

import pytest
from django.core import management


@pytest.fixture(scope="session")
def django_db():
    management.call_command("migrate", "--run-syncdb", "--database", "geo")


@pytest.fixture(scope="session")
def world_borders_dataset(data_dir: Path):
    target_dir = data_dir / "world_borders"

    if target_dir.exists():
        return target_dir

    filename_zip = target_dir.with_suffix(".zip")

    if not filename_zip.exists():
        breakpoint()
        opener = req.build_opener()
        opener.addheaders = [("Accept", "application/zip")]
        req.install_opener(opener)
        req.urlretrieve(
            "https://thematicmapping.org/downloads/TM_WORLD_BORDERS-0.3.zip",
            filename_zip,
        )
        assert filename_zip.exists()

    with ZipFile(filename_zip, "r") as z:
        z.extractall(target_dir)

    return target_dir
