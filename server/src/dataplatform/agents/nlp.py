"""Lightweight, deterministic natural-language helpers used by the mock agents.

The agents are intentionally rule-based: answers are reproducible and testable, and no model
endpoint or credential is required to run the mockup.
"""

import re
from collections.abc import Iterable, Sequence
from typing import Any

_TOP_N = re.compile(r"\b(?:top|best|worst|bottom|first|last)\s+(\d{1,3})\b|\b(\d{1,3})\s+(?:best|worst|top|most|least)\b")
_YEAR = re.compile(r"\b(20\d{2})\b")
_ASCENDING = re.compile(r"\b(?:worst|lowest|bottom|least|slowest|poorest)\b")


def normalise(text: str) -> str:
    """Lower-case and collapse whitespace."""
    return " ".join(text.lower().split())


def extract_top_n(text: str, *, default: int = 10, maximum: int = 50) -> int:
    """Return N from phrases such as "top 5" or "3 worst", clamped to ``[1, maximum]``."""
    match = _TOP_N.search(normalise(text))
    if not match:
        return default
    value = int(match.group(1) or match.group(2))
    return max(1, min(value, maximum))


def extract_year(text: str, years: Iterable[int]) -> int | None:
    """Return the first year mentioned in ``text`` that exists in ``years``."""
    allowed = set(years)
    return next((int(y) for y in _YEAR.findall(text) if int(y) in allowed), None)


def wants_ascending(text: str) -> bool:
    """Whether the user asks for the worst/lowest items rather than the best."""
    return _ASCENDING.search(normalise(text)) is not None


def extract_value(text: str, candidates: Sequence[str]) -> str | None:
    """Return the longest candidate mentioned in ``text`` as a whole word (case-insensitive)."""
    lowered = normalise(text)
    for candidate in sorted(candidates, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(candidate.lower())}(?!\w)", lowered):
            return candidate
    return None


def sql_literal(value: str | int | float) -> str:
    """Render a value as a SQL literal.

    Only used with values drawn from the data vocabulary or parsed as numbers, never with raw
    user text; single quotes are still escaped as defence in depth.
    """
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float):
        return repr(value)
    return "'" + value.replace("'", "''") + "'"


def fmt_number(value: Any, decimals: int = 0) -> str:
    """Format a number with thousands separators."""
    if value is None:
        return "n/a"
    return f"{float(value):,.{decimals}f}"


def fmt_money(value: Any) -> str:
    """Format an amount in euros."""
    return "n/a" if value is None else f"€{float(value):,.2f}"


def score(text: str, patterns: Sequence[re.Pattern[str]]) -> int:
    """Count how many patterns match ``text``."""
    lowered = normalise(text)
    return sum(1 for p in patterns if p.search(lowered))
