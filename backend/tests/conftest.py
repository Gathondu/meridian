"""Pytest fixtures."""

import pytest
from starlette.testclient import TestClient

from meridian_api.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
