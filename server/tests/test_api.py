"""REST API v1 contract: pagination, problem+json errors, security headers, settings."""

import pytest
from fastapi.testclient import TestClient

PROBLEM_KEYS = {"type", "title", "status", "detail", "instance", "traceId"}


def should_report_live_and_ready_when_started(client: TestClient) -> None:
    # Act
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    # Assert
    assert live.json() == {"status": "ok"}
    assert ready.json() == {"status": "ready"}


def should_describe_platform_when_requested(client: TestClient) -> None:
    # Act
    body = client.get("/api/v1/platform").json()

    # Assert
    assert body["endpoints"] == {
        "rest": "http://localhost:8000/api/v1",
        "mcp": "http://localhost:8000/mcp",
        "a2a": "http://localhost:8000/a2a",
        "openapi": "http://localhost:8000/openapi.json",
    }
    assert body["stats"]["tables"] == 17


def should_return_page_shape_when_listing_collections(client: TestClient) -> None:
    # Act
    body = client.get("/api/v1/catalogs/retail/schemas/sales/tables", params={"pageSize": 2, "page": 2}).json()

    # Assert
    assert set(body) == {"items", "total", "page", "pageSize"}
    assert body["total"] == 5
    assert body["page"] == 2
    assert len(body["items"]) == 2
    assert {"schema", "fullName", "rowCount", "columnCount"} <= set(body["items"][0])


def should_filter_and_sort_rows_when_browsing(client: TestClient) -> None:
    # Act
    response = client.get(
        "/api/v1/catalogs/retail/schemas/sales/tables/stores/rows",
        params={"filter[region]": "North", "sort": "store_id", "order": "desc", "pageSize": 100},
    )

    # Assert
    rows = response.json()["items"]
    assert response.status_code == 200
    assert rows
    assert all(r["region"] == "North" for r in rows)
    assert [r["store_id"] for r in rows] == sorted((r["store_id"] for r in rows), reverse=True)


def should_describe_columns_when_getting_table(client: TestClient) -> None:
    # Act
    body = client.get("/api/v1/catalogs/manufacturing/schemas/production/tables/machines").json()

    # Assert
    assert body["fullName"] == "manufacturing.production.machines"
    assert any(c["name"] == "machine_id" for c in body["columns"])


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/api/v1/catalogs?pageSize=101", 400),
        ("/api/v1/catalogs?page=0", 400),
        ("/api/v1/catalogs?sort=drop%20table", 400),
        ("/api/v1/catalogs?filter[name][evil]=x", 400),
        ("/api/v1/catalogs/retail/schemas/sales/tables/orders/rows?sort=nope", 400),
        ("/api/v1/catalogs/nope/schemas", 404),
        ("/api/v1/catalogs/retail/schemas/sales/tables/nope", 404),
        ("/api/v1/agents/nobody", 404),
        ("/api/v1/unknown", 404),
    ],
)
def should_return_problem_details_when_request_fails(client: TestClient, path: str, status: int) -> None:
    # Act
    response = client.get(path)

    # Assert
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert set(body) >= PROBLEM_KEYS
    assert body["traceId"] == response.headers["x-correlation-id"]


def should_add_security_headers_when_responding(client: TestClient) -> None:
    # Act
    response = client.get("/api/v1/catalogs")

    # Assert
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "max-age" in response.headers["strict-transport-security"]


def should_echo_correlation_id_when_client_sends_one(client: TestClient) -> None:
    # Act
    response = client.get("/health/live", headers={"X-Correlation-ID": "abc-123"})

    # Assert
    assert response.headers["x-correlation-id"] == "abc-123"


def should_allow_only_configured_origin_when_cors_preflight(client: TestClient) -> None:
    # Arrange
    headers = {"Access-Control-Request-Method": "GET"}

    # Act
    allowed = client.options("/api/v1/catalogs", headers={**headers, "Origin": "http://localhost:3000"})
    denied = client.options("/api/v1/catalogs", headers={**headers, "Origin": "https://evil.example"})

    # Assert
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers


def should_run_query_and_record_history_when_sql_is_valid(client: TestClient) -> None:
    # Act
    result = client.post(
        "/api/v1/query",
        json={"sql": "SELECT count(*) AS n FROM retail.sales.customers", "maxRows": 10},
        headers={"X-Query-Source": "ui"},
    ).json()
    history = client.get("/api/v1/queries", params={"filter[source]": "ui", "pageSize": 1}).json()

    # Assert
    assert result["rows"] == [{"n": 3000}]
    assert result["columns"] == [{"name": "n", "type": "BIGINT"}]
    assert history["items"][0]["id"] == result["queryId"]
    assert history["items"][0]["status"] == "succeeded"


def should_reject_query_when_statement_writes(client: TestClient) -> None:
    # Act
    response = client.post("/api/v1/query", json={"sql": "DROP TABLE retail.sales.orders"})

    # Assert
    assert response.status_code == 400
    assert response.json()["title"] == "Query failed"


def should_cap_rows_when_settings_limit_is_lower(client: TestClient) -> None:
    # Arrange
    settings = client.get("/api/v1/settings").json()
    client.put("/api/v1/settings", json={**settings, "maxQueryRows": 5})

    # Act
    result = client.post("/api/v1/query", json={"sql": "SELECT * FROM retail.sales.orders", "maxRows": 50}).json()

    # Assert
    assert result["rowCount"] == 5
    assert result["truncated"] is True


def should_use_default_page_size_from_settings_when_not_given(client: TestClient) -> None:
    # Arrange
    settings = client.get("/api/v1/settings").json()
    client.put("/api/v1/settings", json={**settings, "defaultPageSize": 3})

    # Act
    body = client.get("/api/v1/catalogs/retail/schemas/sales/tables/orders/rows").json()

    # Assert
    assert body["pageSize"] == 3
    assert len(body["items"]) == 3


def should_reject_settings_when_values_invalid(client: TestClient) -> None:
    # Arrange
    settings = client.get("/api/v1/settings").json()

    # Act
    too_big = client.put("/api/v1/settings", json={**settings, "defaultPageSize": 1000})
    unknown_agent = client.put("/api/v1/settings", json={**settings, "agentsEnabled": {"ghost": True}})

    # Assert
    assert too_big.status_code == 400
    assert unknown_agent.status_code == 400


def should_list_agents_with_card_urls_when_requested(client: TestClient) -> None:
    # Act
    body = client.get("/api/v1/agents", params={"sort": "name"}).json()

    # Assert
    assert body["total"] == 4
    assert all(a["a2aCardUrl"].endswith("/.well-known/agent-card.json") for a in body["items"])


def should_answer_question_when_agent_invoked(client: TestClient) -> None:
    # Act
    body = client.post(
        "/api/v1/agents/data-analyst/invoke", json={"message": "Which machines need maintenance?"}
    ).json()

    # Assert
    assert body["skillId"] == "quality-maintenance/maintenance-due"
    assert body["rows"]


def should_return_conflict_when_invoking_disabled_agent(client: TestClient) -> None:
    # Arrange
    settings = client.get("/api/v1/settings").json()
    client.put("/api/v1/settings", json={**settings, "agentsEnabled": {"supply-chain": False}})

    # Act
    response = client.post("/api/v1/agents/supply-chain/invoke", json={"message": "open purchase orders"})

    # Assert
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize(("flag", "path"), [("mcpEnabled", "/mcp"), ("a2aEnabled", "/a2a/data-analyst")])
def should_return_service_unavailable_when_protocol_disabled(client: TestClient, flag: str, path: str) -> None:
    # Arrange
    settings = client.get("/api/v1/settings").json()
    client.put("/api/v1/settings", json={**settings, flag: False})

    # Act
    response = client.post(path, json={})

    # Assert
    assert response.status_code == 503
    assert response.json()["title"] == "Protocol disabled"


def should_publish_openapi_when_requested(client: TestClient) -> None:
    # Act
    spec = client.get("/openapi.json").json()

    # Assert
    assert "/api/v1/catalogs/{catalog}/schemas/{schema}/tables/{table}/rows" in spec["paths"]
