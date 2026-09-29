"""FastAPI dependencies."""

from typing import Annotated, Literal

from fastapi import Depends, Query, Request

from dataplatform.container import Container
from dataplatform.services.list_options import ListOptions, parse_filters


def get_container(request: Request) -> Container:
    """Return the application container."""
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def list_options(
    request: Request,
    container: ContainerDep,
    page: Annotated[int, Query(ge=1, le=100_000, description="1-based page number.")] = 1,
    page_size: Annotated[
        int | None,
        Query(alias="pageSize", ge=1, le=100, description="Items per page (default from settings, max 100)."),
    ] = None,
    sort: Annotated[str | None, Query(max_length=64, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")] = None,
    order: Annotated[Literal["asc", "desc"], Query()] = "asc",
    q: Annotated[str | None, Query(max_length=100, description="Global search across text columns.")] = None,
) -> ListOptions:
    """Parse ``page``, ``pageSize``, ``sort``, ``order``, ``q`` and ``filter[col][op]`` parameters."""
    return ListOptions(
        page=page,
        page_size=page_size or container.settings.get().default_page_size,
        sort=sort,
        order=order,
        q=q.strip() or None if q else None,
        filters=parse_filters(request.query_params.multi_items()),
    )


ListOptionsDep = Annotated[ListOptions, Depends(list_options)]
