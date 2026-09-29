"""A2A access to the platform agents with the official ``a2a-sdk`` client."""

from dataclasses import dataclass, field
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_data_parts, get_message_text, new_text_message
from a2a.types import AgentCard, Role, SendMessageRequest, Task, TaskState

from dataplatform_client.mcp_client import PlatformError


@dataclass(frozen=True)
class AgentAnswer:
    """The outcome of an A2A task."""

    agent: str
    state: str
    markdown: str
    data: dict[str, Any] = field(default_factory=dict)


def _answer_from_task(agent: str, task: Task) -> AgentAnswer:
    state = TaskState.Name(task.status.state)
    if task.status.state != TaskState.TASK_STATE_COMPLETED:
        reason = get_message_text(task.status.message) if task.status.HasField("message") else state
        raise PlatformError(f"{agent}: task ended in {state}: {reason}")
    markdown = "\n".join(get_artifact_text(a) for a in task.artifacts)
    data = next((d for a in task.artifacts for d in get_data_parts(a.parts) if isinstance(d, dict)), {})
    return AgentAnswer(agent=agent, state=state, markdown=markdown, data=data)


class PlatformA2AClient:
    """Talks to the agents published at ``{base_url}/a2a/{agent_id}``."""

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        """Prepare a client for the platform at ``base_url``."""
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def agent_url(self, agent_id: str) -> str:
        """A2A endpoint of an agent (its card lives under ``/.well-known/agent-card.json``)."""
        return f"{self._base_url}/a2a/{agent_id}"

    async def get_card(self, agent_id: str) -> AgentCard:
        """Resolve an agent card."""
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            return await A2ACardResolver(httpx_client=http, base_url=self.agent_url(agent_id)).get_agent_card()

    async def ask(self, agent_id: str, question: str) -> AgentAnswer:
        """Send one message and wait for the completed task.

        Raises:
            PlatformError: The task failed (for example, the agent is disabled).

        """
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            card = await A2ACardResolver(httpx_client=http, base_url=self.agent_url(agent_id)).get_agent_card()
            client = await create_client(card, client_config=ClientConfig(streaming=False, httpx_client=http))
            request = SendMessageRequest(message=new_text_message(question, role=Role.ROLE_USER))
            try:
                async for event in client.send_message(request):
                    if event.HasField("task"):
                        return _answer_from_task(card.name, event.task)
                    if event.HasField("message"):
                        return AgentAnswer(card.name, "message", get_message_text(event.message))
            finally:
                await client.close()
        raise PlatformError(f"{agent_id}: no response")
