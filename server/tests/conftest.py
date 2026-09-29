"""Shared fixtures: one container (sample data load) per test session."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataplatform.api.main import create_app
from dataplatform.config import AppConfig
from dataplatform.container import Container, build_container
from dataplatform.domain.models import PlatformSettings
from dataplatform.services.agent_service import AGENT_IDS


@pytest.fixture(scope="session")
def config() -> AppConfig:
    return AppConfig(_env_file=None, log_level="WARNING", query_timeout_seconds=5)


@pytest.fixture(scope="session")
def container(config: AppConfig) -> Container:
    return build_container(config)


@pytest.fixture(scope="session")
def app(config: AppConfig, container: Container) -> FastAPI:
    return create_app(config, container)


@pytest.fixture(scope="session")
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, base_url="http://localhost:8000") as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_settings(container: Container) -> Iterator[None]:
    yield
    container.settings.update(PlatformSettings(agents_enabled=dict.fromkeys(AGENT_IDS, True)))
