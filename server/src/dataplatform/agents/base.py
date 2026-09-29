"""Agent building blocks: skills, the execution context, and the base agent."""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from dataplatform.agents.nlp import score
from dataplatform.domain.models import AgentReply, AgentSkillInfo, QueryResult


@dataclass(frozen=True)
class Vocabulary:
    """Known data values that agents can recognise in a question."""

    regions: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    loyalty_tiers: tuple[str, ...] = ()
    plants: dict[str, str] = field(default_factory=dict)
    """Plant name, city or country (lower-case) -> plant_id."""
    years: tuple[int, ...] = ()


@dataclass
class AgentContext:
    """Everything a skill needs to answer: a SQL runner and the data vocabulary."""

    run_sql: Callable[[str], QueryResult]
    vocabulary: Vocabulary


SkillHandler = Callable[[str, AgentContext], AgentReply]


@dataclass(frozen=True)
class Skill:
    """A capability of an agent, selected by regex patterns over the user message."""

    id: str
    name: str
    description: str
    examples: tuple[str, ...]
    patterns: tuple[re.Pattern[str], ...]
    handler: SkillHandler

    def info(self) -> AgentSkillInfo:
        """Public description of the skill."""
        return AgentSkillInfo(id=self.id, name=self.name, description=self.description, examples=list(self.examples))


def patterns(*expressions: str) -> tuple[re.Pattern[str], ...]:
    """Compile case-insensitive patterns."""
    return tuple(re.compile(e, re.IGNORECASE) for e in expressions)


class Agent:
    """A domain agent that routes a message to its best-matching skill."""

    def __init__(self, agent_id: str, name: str, description: str, domain: str, skills: Sequence[Skill]) -> None:
        self.id = agent_id
        self.name = name
        self.description = description
        self.domain = domain
        self.skills = tuple(skills)

    def best_skill(self, message: str) -> tuple[Skill | None, int]:
        """Return the highest-scoring skill (earliest wins ties) and its score."""
        best: Skill | None = None
        best_score = 0
        for skill in self.skills:
            current = score(message, skill.patterns)
            if current > best_score:
                best, best_score = skill, current
        return best, best_score

    def handle(self, message: str, context: AgentContext) -> AgentReply:
        """Answer a message."""
        skill, _ = self.best_skill(message)
        if skill is None:
            return self.help_reply()
        return skill.handler(message, context)

    def help_reply(self) -> AgentReply:
        """Build a reply listing what the agent can do."""
        lines = [f"I'm the **{self.name}**. I didn't recognise a question I can answer. Try one of these:", ""]
        for skill in self.skills:
            lines.append(f'- **{skill.name}** — {skill.description} _e.g. "{skill.examples[0]}"_')
        return AgentReply(agent_id=self.id, skill_id="help", answer="\n".join(lines))


def reply(agent_id: str, skill_id: str, answer: str, sql: str, result: QueryResult) -> AgentReply:
    """Build an ``AgentReply`` from a query result."""
    return AgentReply(
        agent_id=agent_id, skill_id=skill_id, answer=answer, sql=sql, columns=result.columns, rows=result.rows
    )
