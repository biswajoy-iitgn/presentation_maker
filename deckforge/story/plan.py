"""The plan: every reasoning step from brief to slides as a typed, inspectable artefact.

Brief -> Problem -> Issue tree -> Analyses (framework + message type + dataset) -> Storyline -> Slides.
A planner model fills this schema stage by stage (planner.py). The renderer never invents content:
it only draws what the plan and the data say.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from deckforge.viz.select import MessageType


class Problem(BaseModel):
    key_question: str
    decision_maker: str
    success_criteria: list[str]
    scope: str


class Issue(BaseModel):
    id: str
    question: str
    hypothesis: str = ""
    children: list["Issue"] = Field(default_factory=list)


class Analysis(BaseModel):
    id: str
    issue: str                  # issue id this analysis answers
    framework: str              # FRAMEWORK_LIBRARY id, e.g. F051
    name: str
    message_type: MessageType
    dataset: str                # key in the data file
    data_status: Literal["provided", "research", "dummy"]
    why: str = ""               # why this framework answers the question


class Point(BaseModel):
    """A commentary point, optionally anchored to an exhibit element by a numbered marker, or led by an icon."""
    lead: str
    text: str
    target: str | int | None = None
    icon: str | None = None


class Kpi(BaseModel):
    value: str
    caption: str


class Slide(BaseModel):
    id: str
    archetype: Literal["cover", "agenda", "exec_summary", "exhibit", "decisions"]
    title: str
    subtitle: str | None = None
    section: int | None = None
    analysis: str | None = None
    exhibit: str = "auto"
    exhibit_title: str | None = None
    exhibit_unit: str | None = None
    emphasis: list[str | int] = Field(default_factory=list)
    commentary_head: str | None = None
    points: list[Point] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)      # exec summary and decision rows
    kpis: list[Kpi] = Field(default_factory=list)       # big-number sidebar instead of commentary
    header: Literal["auto", "rule", "band"] = "auto"
    sticker: str | None = None
    source: str = ""
    notes: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    brief_id: str
    produced_by: str
    audience: str = "board"
    family: str = "meridian"
    problem: Problem
    issue_tree: Issue
    governing_thought: str
    situation: str
    complication: str
    resolution: str
    sections: list[str]
    analyses: list[Analysis]
    slides: list[Slide]

    def analysis(self, aid: str) -> Analysis:
        return next(a for a in self.analyses if a.id == aid)


TOKEN = re.compile(r"\{([a-z0-9_]+)\}")


def resolve(template: str, facts: dict) -> str:
    """Fill {fact} tokens. Unknown tokens raise, so a title can never ship with a hole."""
    return TOKEN.sub(lambda m: str(facts[m.group(1)]), template)


def untracked_numbers(template: str, allowed: set[str]) -> list[str]:
    """Digits typed into a template rather than computed: allowed only for fiscal labels or brief facts."""
    bare = TOKEN.sub("", template)
    found = re.findall(r"(?<![A-Za-z0-9])\d[\d,.]*", bare)
    return [n for n in found if n not in allowed]
