"""A2A agent cards and JSON-RPC ``SendMessage``."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dataplatform.services.agent_service import AGENT_IDS

A2A_HEADERS = {"A2A-Version": "1.0"}


def _send(client: TestClient, agent_id: str, text: str) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "SendMessage",
        "params": {
            "message": {"messageId": uuid.uuid4().hex, "role": "ROLE_USER", "parts": [{"text": text}]},
            "configuration": {"returnImmediately": False},
        },
    }
    response = client.post(f"/a2a/{agent_id}", json=payload, headers=A2A_HEADERS)
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.parametrize("agent_id", AGENT_IDS)
def should_publish_agent_card_when_requested(client: TestClient, agent_id: str) -> None:
    # Act
    card = client.get(f"/a2a/{agent_id}/.well-known/agent-card.json").json()

    # Assert
    assert card["supportedInterfaces"][0]["url"] == f"http://localhost:8000/a2a/{agent_id}"
    assert card["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
    assert card["skills"]


def should_serve_data_analyst_card_when_root_well_known_requested(client: TestClient) -> None:
    # Act
    card = client.get("/.well-known/agent-card.json").json()

    # Assert
    assert card["name"] == "Data Analyst Agent"


def should_complete_task_with_artifact_when_message_sent(client: TestClient) -> None:
    # Act
    body = _send(client, "supply-chain", "Which suppliers are most often late?")

    # Assert
    task = body["result"]["task"]
    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    parts = task["artifacts"][0]["parts"]
    assert parts[0]["mediaType"] == "text/markdown"
    assert parts[1]["data"]["skillId"] == "supplier-performance"
    assert parts[1]["data"]["rows"]


def should_fail_task_when_agent_disabled(client: TestClient) -> None:
    # Arrange
    settings = client.get("/api/v1/settings").json()
    client.put("/api/v1/settings", json={**settings, "agentsEnabled": {"quality-maintenance": False}})

    # Act
    body = _send(client, "quality-maintenance", "Which machines need maintenance?")

    # Assert
    task = body["result"]["task"]
    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert "disabled" in task["status"]["message"]["parts"][0]["text"]
