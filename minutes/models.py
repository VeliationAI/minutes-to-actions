"""Structured output for meeting minutes extraction."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Priority = Literal["high", "medium", "low"]


class Decision(BaseModel):
    text: str = Field(..., min_length=1)
    context: str = ""


class ActionItem(BaseModel):
    task: str = Field(..., min_length=1)
    owner: str = "Unassigned"
    due: str = ""
    priority: Priority = "medium"


class MinutesResult(BaseModel):
    summary: str = ""
    attendees: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    source: Literal["llm", "heuristic"] = "heuristic"

    def to_markdown(self) -> str:
        lines: list[str] = ["# Minutes to Actions", ""]
        if self.summary:
            lines += ["## Summary", self.summary, ""]
        if self.attendees:
            lines += ["## Attendees", ", ".join(self.attendees), ""]
        if self.decisions:
            lines.append("## Decisions")
            for i, d in enumerate(self.decisions, 1):
                extra = f" — _{d.context}_" if d.context else ""
                lines.append(f"{i}. {d.text}{extra}")
            lines.append("")
        if self.action_items:
            lines.append("## Action items")
            for item in self.action_items:
                due = f" · due {item.due}" if item.due else ""
                lines.append(
                    f"- [ ] **{item.owner}**: {item.task} "
                    f"({item.priority}{due})"
                )
            lines.append("")
        if self.open_questions:
            lines.append("## Open questions")
            for q in self.open_questions:
                lines.append(f"- {q}")
            lines.append("")
        lines.append(f"_Extracted via {self.source}_")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
