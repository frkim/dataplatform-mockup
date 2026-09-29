"""Agent registry and invocation, shared by the REST API, the MCP tools and the A2A executors."""

import logging

from dataplatform.agents import data_analyst, quality, sales, supply_chain
from dataplatform.agents.base import Agent, AgentContext, Vocabulary
from dataplatform.domain.errors import ConflictError, NotFoundError
from dataplatform.domain.models import AgentInfo, AgentReply, Page, QueryResult, QuerySource
from dataplatform.infrastructure.engine import Engine
from dataplatform.services.list_options import ListOptions, paginate_in_memory
from dataplatform.services.query_service import QueryService
from dataplatform.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

AGENT_IDS: tuple[str, ...] = (data_analyst.AGENT_ID, sales.AGENT_ID, supply_chain.AGENT_ID, quality.AGENT_ID)
_VOCABULARY_TIMEOUT_SECONDS = 30.0


def build_agents() -> dict[str, Agent]:
    """Instantiate every agent, keyed by id (front-door agent first)."""
    specialists = [sales.create_agent(), supply_chain.create_agent(), quality.create_agent()]
    agents: list[Agent] = [data_analyst.DataAnalystAgent(specialists), *specialists]
    return {a.id: a for a in agents}


def load_vocabulary(engine: Engine) -> Vocabulary:
    """Read the values agents recognise in questions (regions, categories, plants...)."""

    def values(sql: str) -> list[str]:
        rows = engine.execute(sql, max_rows=1_000, timeout_seconds=_VOCABULARY_TIMEOUT_SECONDS).rows
        return [str(next(iter(r.values()))) for r in rows]

    plants: dict[str, str] = {}
    for row in engine.execute(
        "SELECT plant_id, name, city, country FROM manufacturing.production.plants",
        max_rows=1_000,
        timeout_seconds=_VOCABULARY_TIMEOUT_SECONDS,
    ).rows:
        for key in (row["plant_id"], row["name"], row["city"], row["country"]):
            plants[str(key).lower()] = str(row["plant_id"])
    years = [
        int(y) for y in values("SELECT DISTINCT CAST(year(order_date) AS VARCHAR) FROM retail.sales.orders ORDER BY 1")
    ]
    return Vocabulary(
        regions=tuple(values("SELECT DISTINCT region FROM retail.sales.stores ORDER BY 1")),
        categories=tuple(values("SELECT DISTINCT category FROM retail.sales.products ORDER BY 1")),
        loyalty_tiers=tuple(values("SELECT DISTINCT loyalty_tier FROM retail.sales.customers ORDER BY 1")),
        plants=plants,
        years=tuple(years),
    )


class AgentService:
    """Lists and invokes agents, honouring the enabled/disabled settings."""

    def __init__(
        self, queries: QueryService, settings: SettingsService, vocabulary: Vocabulary, *, public_base_url: str
    ) -> None:
        self._agents = build_agents()
        self._queries = queries
        self._settings = settings
        self._vocabulary = vocabulary
        self._base_url = public_base_url

    def agent(self, agent_id: str) -> Agent:
        """Return an agent.

        Raises:
            NotFoundError: Unknown agent id.

        """
        found = self._agents.get(agent_id)
        if found is None:
            raise NotFoundError(f"Agent '{agent_id}' does not exist. Known agents: {', '.join(self._agents)}.")
        return found

    def card_url(self, agent_id: str) -> str:
        """Absolute URL of the agent's A2A agent card."""
        return f"{self._base_url}/a2a/{agent_id}/.well-known/agent-card.json"

    def info(self, agent_id: str) -> AgentInfo:
        """Describe an agent."""
        agent = self.agent(agent_id)
        return AgentInfo(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            domain=agent.domain,
            enabled=self._settings.is_agent_enabled(agent.id),
            skills=[s.info() for s in agent.skills],
            a2a_card_url=self.card_url(agent.id),
        )

    def all_info(self) -> list[AgentInfo]:
        """Describe every agent."""
        return [self.info(agent_id) for agent_id in self._agents]

    def list(self, options: ListOptions) -> Page[AgentInfo]:
        """Page through the agents."""
        return paginate_in_memory(
            self.all_info(),
            options,
            fields={
                "id": lambda a: a.id,
                "name": lambda a: a.name,
                "domain": lambda a: a.domain,
                "enabled": lambda a: a.enabled,
                "description": lambda a: a.description,
            },
            search_fields=("id", "name", "domain", "description"),
        )

    def invoke(self, agent_id: str, message: str, *, source: QuerySource) -> AgentReply:
        """Ask an agent a question (blocking: call from a worker thread in async code).

        Raises:
            NotFoundError: Unknown agent id.
            ConflictError: The agent is disabled in the settings.
            QueryError: A generated query failed.

        """
        agent = self.agent(agent_id)
        if not self._settings.is_agent_enabled(agent_id):
            raise ConflictError(f"Agent '{agent_id}' is disabled. Enable it in the platform settings.")

        def run_sql(sql: str) -> QueryResult:
            return self._queries.run(sql, source=source, max_rows=100)

        reply = agent.handle(message, AgentContext(run_sql=run_sql, vocabulary=self._vocabulary))
        logger.info(
            "agent invoked",
            extra={"event": "agent.invoked", "agent_id": agent_id, "skill_id": reply.skill_id, "source": source},
        )
        return reply
