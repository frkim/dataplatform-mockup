"""Start a real platform server (REST + MCP + A2A) on a free local port for the whole session."""

import socket
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
import uvicorn
from dataplatform.api.main import create_app
from dataplatform.config import AppConfig
from dataplatform.container import Container, build_container
from dataplatform.domain.models import PlatformSettings
from dataplatform.services.agent_service import AGENT_IDS


@dataclass(frozen=True)
class Platform:
    base_url: str
    container: Container


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


@pytest.fixture(scope="session")
def platform() -> Iterator[Platform]:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    config = AppConfig(_env_file=None, public_base_url=base_url, log_level="WARNING")
    container = build_container(config)
    server = uvicorn.Server(
        uvicorn.Config(create_app(config, container), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("platform server did not start")
        time.sleep(0.05)
    yield Platform(base_url, container)
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(autouse=True)
def _reset_settings(platform: Platform) -> Iterator[None]:
    yield
    platform.container.settings.update(PlatformSettings(agents_enabled=dict.fromkeys(AGENT_IDS, True)))
