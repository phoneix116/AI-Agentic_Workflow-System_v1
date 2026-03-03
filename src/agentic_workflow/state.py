from __future__ import annotations

from typing import Any, Literal, TypedDict


class ToolResult(TypedDict):
    status: Literal["success", "error"]
    output: str
    metadata: dict[str, Any]


class AgentState(TypedDict):
    goal: str
    plan: dict[str, Any]
    tool_result: ToolResult | None
    memory: list[dict[str, Any]]
    status: Literal["running", "complete", "failed"]
    iteration: int
    max_iterations: int
    goal_achieved: bool
    final_answer: str
