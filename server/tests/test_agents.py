"""Agents answer business questions with the right skill and real data."""

import pytest

from dataplatform.container import Container
from dataplatform.domain.errors import ConflictError, NotFoundError
from dataplatform.domain.models import PlatformSettings
from dataplatform.services.list_options import ListOptions


@pytest.mark.parametrize(
    ("agent_id", "question", "skill_id"),
    [
        ("data-analyst", "What data is available?", "catalog-overview"),
        ("data-analyst", "Describe retail.sales.orders", "describe-table"),
        ("data-analyst", "How many customers do we have?", "count-rows"),
        ("data-analyst", "Preview 5 rows of work orders", "preview-table"),
        ("data-analyst", "What are the top 5 products in Electronics?", "sales-insights/top-products"),
        ("data-analyst", "defect rate by plant", "quality-maintenance/defect-analysis"),
        ("data-analyst", "Which materials are below their reorder point?", "supply-chain/material-shortages"),
        ("sales-insights", "Which stores perform best in the South region?", "store-performance"),
        ("sales-insights", "What is the revenue split by channel?", "channel-mix"),
        ("sales-insights", "How do loyalty tiers compare?", "customer-segments"),
        ("sales-insights", "Category performance in 2026", "category-performance"),
        ("sales-insights", "Show me the monthly revenue trend for 2025", "revenue-trend"),
        ("supply-chain", "Show stock-outs for Toys", "store-low-stock"),
        ("supply-chain", "Which suppliers are most often late?", "supplier-performance"),
        ("supply-chain", "What purchase orders are still open?", "open-purchase-orders"),
        ("quality-maintenance", "What is the production yield per plant?", "production-yield"),
        ("quality-maintenance", "Which machines show sensor anomalies?", "machine-anomalies"),
        ("quality-maintenance", "Which machines need maintenance?", "maintenance-due"),
    ],
)
def should_pick_expected_skill_when_question_matches(
    container: Container, agent_id: str, question: str, skill_id: str
) -> None:
    # Act
    reply = container.agents.invoke(agent_id, question, source="agent")

    # Assert
    assert reply.skill_id == skill_id
    assert reply.answer
    if reply.sql:
        assert reply.rows


def should_apply_filters_when_question_names_region_and_year(container: Container) -> None:
    # Act
    reply = container.agents.invoke("sales-insights", "Top 3 products in the North region in 2025", source="agent")

    # Assert
    assert len(reply.rows) == 3
    assert reply.sql is not None
    assert "'North'" in reply.sql
    assert "2025" in reply.sql


def should_list_skills_when_question_is_not_understood(container: Container) -> None:
    # Act
    reply = container.agents.invoke("supply-chain", "tell me a joke", source="agent")

    # Assert
    assert reply.skill_id == "help"
    assert reply.sql is None


def should_raise_conflict_when_agent_disabled(container: Container) -> None:
    # Arrange
    container.settings.update(PlatformSettings(agents_enabled={"sales-insights": False}))

    # Act / Assert
    with pytest.raises(ConflictError):
        container.agents.invoke("sales-insights", "top products", source="agent")


def should_raise_not_found_when_agent_unknown(container: Container) -> None:
    # Act / Assert
    with pytest.raises(NotFoundError):
        container.agents.invoke("nobody", "hi", source="agent")


def should_record_agent_queries_in_history_when_agent_runs_sql(container: Container) -> None:
    # Act
    reply = container.agents.invoke("quality-maintenance", "Which machines need maintenance?", source="a2a")

    # Assert
    latest = container.queries.history.list(ListOptions())
    assert latest.items[0].sql == reply.sql
    assert latest.items[0].source == "a2a"
