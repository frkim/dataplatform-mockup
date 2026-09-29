"""Liveness and readiness probes."""

from fastapi import APIRouter

from dataplatform.api.deps import ContainerDep

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", summary="Liveness probe")
def live() -> dict[str, str]:
    """The process is running."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
def ready(container: ContainerDep) -> dict[str, str]:
    """The data engine answers queries."""
    container.engine.row_count("retail.sales.stores")
    return {"status": "ready"}
