"""Data Analyst agent: a Genie / Cortex Analyst-like natural-language front door to the catalog.

It answers catalog questions itself (what data exists, table structure, row counts, previews)
and delegates domain questions to the specialist agents.
"""

import re
from collections.abc import Sequence

from dataplatform.agents.base import Agent, AgentContext, Skill, patterns, reply
from dataplatform.agents.nlp import extract_top_n, fmt_number, normalise, sql_literal
from dataplatform.domain.models import AgentReply
from dataplatform.infrastructure.catalog_metadata import TableDef, all_tables

AGENT_ID = "data-analyst"

_OVERVIEW = patterns(
    r"\bwhat (?:data|tables|datasets)\b", r"\bwhich (?:data|tables|datasets)\b", r"\blist (?:all )?(?:the )?tables\b",
    r"\bcatalogs?\b", r"\bdatasets?\b", r"\bavailable\b",
)
_DESCRIBE = patterns(r"\bdescribe\b", r"\bcolumns?\b", r"\bschema of\b", r"\bstructure\b", r"\bfields?\b")
_COUNT = patterns(r"\bhow many\b", r"\bcount\b", r"\bnumber of\b")
_PREVIEW = patterns(r"\bpreview\b", r"\bsample\b", r"\bshow me (?:the |some )?(?:rows|data|records)\b", r"\bfirst \d+ rows\b", r"\brows (?:of|from)\b")
_ANALYTIC = patterns(r"\btop\b", r"\bbest\b", r"\bworst\b", r"\btrend", r"\bby\b", r"\bper\b", r"\bhighest\b", r"\blowest\b")


def _aliases(table: TableDef) -> list[str]:
    spaced = table.name.replace("_", " ")
    singular = spaced[:-1] if spaced.endswith("s") else spaced
    return [table.full_name, f"{table.schema}.{table.name}", table.name, spaced, singular]


_TABLE_ALIASES: list[tuple[str, TableDef]] = sorted(
    ((alias.lower(), t) for t in all_tables() for alias in _aliases(t)), key=lambda pair: len(pair[0]), reverse=True
)


def find_table(message: str) -> TableDef | None:
    """Return the table mentioned in the message (longest alias wins), if any."""
    lowered = normalise(message)
    for alias, table in _TABLE_ALIASES:
        if re.search(rf"(?<![\w.]){re.escape(alias)}(?![\w])", lowered):
            return table
    return None


_FILLER = frozenset(
    "how many count number of do does we you have are there is in the a an total table rows records contain "
    "contains exist exists all our".split()
)


def is_simple_count(message: str, table: TableDef) -> bool:
    """Whether the message only asks for a row count ("how many customers do we have?")."""
    text = re.sub(r"[^\w\s.]", " ", normalise(message))
    for alias in _aliases(table):
        text = re.sub(rf"(?<![\w.]){re.escape(alias.lower())}(?![\w])", " ", text)
    return all(word.strip(".") in _FILLER for word in text.split() if word.strip("."))


def _matches(message: str, compiled: Sequence[re.Pattern[str]]) -> bool:
    return any(p.search(normalise(message)) for p in compiled)


def catalog_overview(message: str, ctx: AgentContext) -> AgentReply:
    """List every table with its row count and description."""
    sql = """SELECT database_name AS catalog, schema_name AS schema, table_name AS "table",
       estimated_size AS row_count, comment AS description
FROM duckdb_tables()
WHERE database_name IN ('manufacturing', 'retail')
ORDER BY 1, 2, 3"""
    result = ctx.run_sql(sql)
    lines = [f"The platform exposes **{len(result.rows)} tables** in 2 catalogs:", ""]
    lines += [
        f"- `{r['catalog']}.{r['schema']}.{r['table']}` — {r['description']} ({fmt_number(r['row_count'])} rows)"
        for r in result.rows
    ]
    return reply(AGENT_ID, "catalog-overview", "\n".join(lines), sql, result)


def describe_table(table: TableDef, ctx: AgentContext) -> AgentReply:
    """Describe the columns of a table."""
    sql = f"""SELECT column_name, data_type, is_nullable, comment AS description
FROM duckdb_columns()
WHERE database_name = {sql_literal(table.catalog)} AND schema_name = {sql_literal(table.schema)}
  AND table_name = {sql_literal(table.name)}
ORDER BY column_index"""
    result = ctx.run_sql(sql)
    lines = [f"**`{table.full_name}`** — {table.description}", ""]
    lines += [f"- `{r['column_name']}` {r['data_type']}: {r['description']}" for r in result.rows]
    return reply(AGENT_ID, "describe-table", "\n".join(lines), sql, result)


def count_rows(table: TableDef, ctx: AgentContext) -> AgentReply:
    """Count the rows of a table."""
    sql = f"SELECT count(*) AS row_count FROM {table.full_name}"
    result = ctx.run_sql(sql)
    count = result.rows[0]["row_count"]
    return reply(AGENT_ID, "count-rows", f"`{table.full_name}` contains **{fmt_number(count)} rows**.", sql, result)


def preview_table(message: str, table: TableDef, ctx: AgentContext) -> AgentReply:
    """Return the first rows of a table."""
    n = extract_top_n(message, default=10, maximum=100)
    number = re.search(r"\b(\d{1,3})\s+rows\b", normalise(message))
    if number:
        n = max(1, min(int(number.group(1)), 100))
    sql = f"SELECT * FROM {table.full_name} LIMIT {n}"
    result = ctx.run_sql(sql)
    answer = f"Here are the first {len(result.rows)} rows of `{table.full_name}` — {table.description}"
    return reply(AGENT_ID, "preview-table", answer, sql, result)


class DataAnalystAgent(Agent):
    """Front-door agent that answers catalog questions and routes domain questions."""

    def __init__(self, specialists: Sequence[Agent]) -> None:
        self._specialists = tuple(specialists)
        super().__init__(
            AGENT_ID,
            "Data Analyst Agent",
            "Your natural-language front door to the platform (like Databricks Genie or Snowflake Cortex Analyst): "
            "explores the catalog, describes tables, counts and previews rows, and routes domain questions to the "
            "sales, supply chain and quality specialists.",
            "cross-domain",
            [
                Skill(
                    "catalog-overview",
                    "Catalog overview",
                    "List the available catalogs, schemas and tables.",
                    ("What data is available?", "List all tables"),
                    _OVERVIEW,
                    catalog_overview,
                ),
                Skill(
                    "describe-table",
                    "Describe table",
                    "Explain the columns of a table.",
                    ("Describe retail.sales.orders", "What columns does the machines table have?"),
                    _DESCRIBE,
                    self._describe,
                ),
                Skill(
                    "count-rows",
                    "Count rows",
                    "Count the rows of a table.",
                    ("How many customers do we have?", "Count the sensor readings"),
                    _COUNT,
                    self._count,
                ),
                Skill(
                    "preview-table",
                    "Preview table",
                    "Show the first rows of a table.",
                    ("Preview 5 rows of work orders", "Show me some data from suppliers"),
                    _PREVIEW,
                    self._preview,
                ),
                Skill(
                    "route-to-specialist",
                    "Ask a specialist",
                    "Routes business questions to the Sales, Supply Chain or Quality & Maintenance agent.",
                    ("What are the top 5 products in Electronics?", "Which machines need maintenance?"),
                    (),
                    self._delegate,
                ),
            ],
        )

    def _describe(self, message: str, ctx: AgentContext) -> AgentReply:
        table = find_table(message)
        return describe_table(table, ctx) if table else catalog_overview(message, ctx)

    def _count(self, message: str, ctx: AgentContext) -> AgentReply:
        table = find_table(message)
        return count_rows(table, ctx) if table else self.help_reply()

    def _preview(self, message: str, ctx: AgentContext) -> AgentReply:
        table = find_table(message)
        return preview_table(message, table, ctx) if table else self.help_reply()

    def _best_specialist(self, message: str) -> tuple[Agent | None, int]:
        best: Agent | None = None
        best_score = 0
        for agent in self._specialists:
            _, current = agent.best_skill(message)
            if current > best_score:
                best, best_score = agent, current
        return best, best_score

    def _delegate(self, message: str, ctx: AgentContext) -> AgentReply:
        specialist, _ = self._best_specialist(message)
        if specialist is None:
            return self.help_reply()
        delegated = specialist.handle(message, ctx)
        return delegated.model_copy(
            update={
                "agent_id": AGENT_ID,
                "skill_id": f"{specialist.id}/{delegated.skill_id}",
                "answer": f"_Routed to the **{specialist.name}**._\n\n{delegated.answer}",
            }
        )

    def handle(self, message: str, context: AgentContext) -> AgentReply:
        """Route: catalog intents first, then specialists, then a table preview, then help."""
        table = find_table(message)
        analytic = _matches(message, _ANALYTIC)
        if table is None and _matches(message, _OVERVIEW):
            return catalog_overview(message, context)
        if table is not None and _matches(message, _DESCRIBE):
            return describe_table(table, context)
        if table is not None and _matches(message, _PREVIEW) and not analytic:
            return preview_table(message, table, context)
        if table is not None and _matches(message, _COUNT) and is_simple_count(message, table):
            return count_rows(table, context)
        specialist, _ = self._best_specialist(message)
        if specialist is not None:
            return self._delegate(message, context)
        if table is not None:
            return preview_table(message, table, context)
        return self.help_reply()
