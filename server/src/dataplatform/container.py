"""Composition root: builds the engine and services once per process."""

from dataclasses import dataclass

from dataplatform.config import AppConfig
from dataplatform.infrastructure.engine import Engine
from dataplatform.infrastructure.sample_data import generate_sample_data
from dataplatform.services.agent_service import AGENT_IDS, AgentService, load_vocabulary
from dataplatform.services.catalog_service import CatalogService
from dataplatform.services.query_service import QueryHistory, QueryService
from dataplatform.services.settings_service import SettingsService


@dataclass(frozen=True)
class Container:
    """Application services."""

    config: AppConfig
    engine: Engine
    settings: SettingsService
    catalog: CatalogService
    queries: QueryService
    agents: AgentService


def build_container(config: AppConfig) -> Container:
    """Load the sample data and wire the services."""
    engine = Engine(
        generate_sample_data(config.data_seed), memory_limit=config.engine_memory_limit, threads=config.engine_threads
    )
    settings = SettingsService(AGENT_IDS)
    queries = QueryService(
        engine, settings, QueryHistory(config.query_history_size), timeout_seconds=config.query_timeout_seconds
    )
    return Container(
        config=config,
        engine=engine,
        settings=settings,
        catalog=CatalogService(engine, settings, timeout_seconds=config.query_timeout_seconds),
        queries=queries,
        agents=AgentService(queries, settings, load_vocabulary(engine), public_base_url=config.public_base_url),
    )
