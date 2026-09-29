"""A2A (Agent2Agent protocol 1.0) endpoints for the platform agents.

Every agent is published as an independent A2A agent:

* card: ``/a2a/{agent_id}/.well-known/agent-card.json``
* JSON-RPC endpoint: ``POST /a2a/{agent_id}``

The root ``/.well-known/agent-card.json`` advertises the ``data-analyst`` agent, which routes
questions to the specialist agents.
"""

import logging

import anyio
from a2a.helpers import get_message_text, new_data_part, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import add_a2a_routes_to_fastapi, create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentProvider, AgentSkill, TaskState
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from fastapi import FastAPI

from dataplatform import __version__
from dataplatform.container import Container
from dataplatform.domain.errors import DomainError
from dataplatform.services.agent_service import AGENT_IDS, AgentService

logger = logging.getLogger(__name__)

ROOT_AGENT_ID = "data-analyst"


def build_agent_card(agents: AgentService, agent_id: str, base_url: str) -> AgentCard:
    """Build the A2A agent card of a platform agent."""
    info = agents.info(agent_id)
    return AgentCard(
        name=info.name,
        description=info.description,
        version=__version__,
        provider=AgentProvider(organization="Data Platform Mockup", url=base_url),
        documentation_url=f"{base_url}/docs",
        default_input_modes=["text/plain"],
        default_output_modes=["text/markdown", "application/json"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(protocol_binding="JSONRPC", url=f"{base_url}/a2a/{agent_id}", protocol_version="1.0")
        ],
        skills=[
            AgentSkill(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                tags=[info.domain, agent_id],
                examples=skill.examples,
                input_modes=["text/plain"],
                output_modes=["text/markdown", "application/json"],
            )
            for skill in info.skills
        ],
    )


class PlatformAgentExecutor(AgentExecutor):
    """Bridge between the A2A task lifecycle and a platform agent."""

    def __init__(self, agents: AgentService, agent_id: str) -> None:
        """Bind the executor to one agent."""
        self._agents = agents
        self._agent_id = agent_id

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Answer the user message; publishes a Markdown + JSON artifact or a failed status."""
        if context.message is None:
            raise ValueError("A2A request without a message.")
        task = context.current_task or new_task_from_user_message(context.message)
        if context.current_task is None:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        await updater.start_work(
            new_text_message("Analysing your question…", context_id=task.context_id, task_id=task.id)
        )
        question = get_message_text(context.message).strip()
        try:
            reply = await anyio.to_thread.run_sync(lambda: self._agents.invoke(self._agent_id, question, source="a2a"))
        except DomainError as exc:
            await updater.failed(new_text_message(exc.detail, context_id=task.context_id, task_id=task.id))
            return
        except Exception:
            logger.exception("a2a agent failure", extra={"event": "a2a.error", "agentId": self._agent_id})
            await updater.failed(
                new_text_message("The agent failed unexpectedly.", context_id=task.context_id, task_id=task.id)
            )
            return
        await updater.add_artifact(
            parts=[
                new_text_part(reply.answer, media_type="text/markdown"),
                new_data_part(reply.model_dump(mode="json", by_alias=True), media_type="application/json"),
            ],
            name="answer",
        )
        await updater.complete(new_text_message(reply.answer, context_id=task.context_id, task_id=task.id))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Answers are computed synchronously, so there is nothing to cancel mid-flight."""
        task = context.current_task
        if task is not None:
            await TaskUpdater(event_queue, task.id, task.context_id).update_status(TaskState.TASK_STATE_CANCELED)


def mount_a2a(app: FastAPI, container: Container) -> None:
    """Register the A2A card and JSON-RPC routes of every agent on ``app``."""
    base_url = container.config.public_base_url.rstrip("/")
    for agent_id in AGENT_IDS:
        card = build_agent_card(container.agents, agent_id, base_url)
        handler = DefaultRequestHandler(
            agent_executor=PlatformAgentExecutor(container.agents, agent_id),
            task_store=InMemoryTaskStore(),
            agent_card=card,
        )
        card_routes = create_agent_card_routes(card, card_url=f"/a2a/{agent_id}{AGENT_CARD_WELL_KNOWN_PATH}")
        if agent_id == ROOT_AGENT_ID:
            card_routes += create_agent_card_routes(card, card_url=AGENT_CARD_WELL_KNOWN_PATH)
        add_a2a_routes_to_fastapi(
            app,
            agent_card_routes=card_routes,
            jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url=f"/a2a/{agent_id}"),
        )
