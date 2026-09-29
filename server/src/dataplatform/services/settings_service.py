"""Runtime platform settings (in memory; they reset when the process restarts)."""

import threading
import time
from collections.abc import Iterable

from dataplatform.domain.errors import InvalidRequestError
from dataplatform.domain.models import PlatformSettings


class SettingsService:
    """Thread-safe holder of the current ``PlatformSettings``."""

    def __init__(self, agent_ids: Iterable[str]) -> None:
        self._agent_ids = tuple(agent_ids)
        self._lock = threading.Lock()
        self._settings = PlatformSettings(agents_enabled=dict.fromkeys(self._agent_ids, True))

    def get(self) -> PlatformSettings:
        """Return a copy of the current settings."""
        with self._lock:
            return self._settings.model_copy(deep=True)

    def update(self, settings: PlatformSettings) -> PlatformSettings:
        """Replace the settings.

        Agents missing from ``agents_enabled`` keep their current state.

        Raises:
            InvalidRequestError: ``agents_enabled`` references an unknown agent.

        """
        unknown = sorted(set(settings.agents_enabled) - set(self._agent_ids))
        if unknown:
            raise InvalidRequestError(f"Unknown agent id(s): {', '.join(unknown)}.")
        with self._lock:
            merged = {**self._settings.agents_enabled, **settings.agents_enabled}
            self._settings = settings.model_copy(update={"agents_enabled": merged}, deep=True)
            return self._settings.model_copy(deep=True)

    def is_agent_enabled(self, agent_id: str) -> bool:
        """Whether an agent is enabled."""
        with self._lock:
            return self._settings.agents_enabled.get(agent_id, False)

    def simulate_latency(self) -> None:
        """Sleep for the configured simulated warehouse latency (blocking; call from a worker thread)."""
        delay = self.get().simulated_latency_ms
        if delay:
            time.sleep(delay / 1000)
