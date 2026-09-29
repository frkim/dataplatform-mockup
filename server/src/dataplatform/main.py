"""Command-line entry point: ``uv run dataplatform``."""

import uvicorn

from dataplatform.api.main import create_app
from dataplatform.config import get_config


def main() -> None:
    """Start the HTTP server (REST + MCP + A2A)."""
    config = get_config()
    uvicorn.run(create_app(config), host=config.host, port=config.port, log_config=None, proxy_headers=True)


if __name__ == "__main__":
    main()
