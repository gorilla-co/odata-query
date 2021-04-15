import pytest
from django.core import management


@pytest.fixture(scope="session")
def django_db():
    management.call_command("migrate", "--run-syncdb")
