"""Ad-hoc SQL execution and query history."""

import logging
import threading
import time
from collections import deque
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from dataplatform.domain.errors import QueryError
from dataplatform.domain.models import Page, QueryHistoryEntry, QueryResult, QuerySource, ResultColumn
from dataplatform.infrastructure.engine import Engine
from dataplatform.services.list_options import ListOptions, paginate_in_memory
from dataplatform.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_HISTORY_FIELDS = {
    "id": lambda e: e.id,
    "sql": lambda e: e.sql,
    "source": lambda e: e.source,
    "status": lambda e: e.status,
    "rowCount": lambda e: e.row_count,
    "durationMs": lambda e: e.duration_ms,
    "startedAt": lambda e: e.started_at,
    "error": lambda e: e.error,
}


class QueryHistory:
    """Bounded, thread-safe, most-recent-first query log."""

    def __init__(self, size: int) -> None:
        self._entries: deque[QueryHistoryEntry] = deque(maxlen=size)
        self._lock = threading.Lock()

    def add(self, entry: QueryHistoryEntry) -> None:
        """Record an entry."""
        with self._lock:
            self._entries.appendleft(entry)

    def list(self, options: ListOptions) -> Page[QueryHistoryEntry]:
        """Page through the history (default order: most recent first)."""
        with self._lock:
            snapshot = list(self._entries)
        return paginate_in_memory(snapshot, options, fields=_HISTORY_FIELDS, search_fields=("sql", "error", "source"))


class QueryService:
    """Runs read-only SQL on behalf of the UI, API clients, MCP clients and agents."""

    def __init__(
        self, engine: Engine, settings: SettingsService, history: QueryHistory, *, timeout_seconds: float
    ) -> None:
        self._engine = engine
        self._settings = settings
        self._history = history
        self._timeout = timeout_seconds

    @property
    def history(self) -> QueryHistory:
        """The query history."""
        return self._history

    def run(
        self,
        sql: str,
        *,
        source: QuerySource,
        max_rows: int | None = None,
        parameters: Sequence[Any] | None = None,
    ) -> QueryResult:
        """Execute a read-only statement and record it in the history.

        Args:
            sql: A single ``SELECT`` statement.
            source: Which surface issued the query.
            max_rows: Requested row cap, bounded by the ``maxQueryRows`` setting.
            parameters: Positional ``?`` parameters.

        Raises:
            QueryError: The statement is rejected, fails, or times out.
        """
        settings = self._settings.get()
        limit = min(max_rows or settings.max_query_rows, settings.max_query_rows)
        query_id = uuid4().hex
        started_at = datetime.now(UTC)
        start = time.perf_counter()
        self._settings.simulate_latency()
        try:
            raw = self._engine.execute(sql, parameters, max_rows=limit, timeout_seconds=self._timeout)
        except QueryError as exc:
            duration = _elapsed_ms(start)
            self._history.add(
                QueryHistoryEntry(
                    id=query_id, sql=sql, source=source, status="failed", row_count=0,
                    duration_ms=duration, error=exc.detail, started_at=started_at,
                )
            )
            logger.info("query failed", extra={"event": "query.failed", "query_id": query_id, "source": source})
            raise
        duration = _elapsed_ms(start)
        self._history.add(
            QueryHistoryEntry(
                id=query_id, sql=sql, source=source, status="succeeded", row_count=len(raw.rows),
                duration_ms=duration, started_at=started_at,
            )
        )
        logger.info(
            "query succeeded",
            extra={"event": "query.succeeded", "query_id": query_id, "source": source, "rows": len(raw.rows)},
        )
        return QueryResult(
            query_id=query_id,
            columns=[ResultColumn(name=n, type=t) for n, t in raw.columns],
            rows=raw.rows,
            row_count=len(raw.rows),
            truncated=raw.truncated,
            duration_ms=duration,
        )


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
