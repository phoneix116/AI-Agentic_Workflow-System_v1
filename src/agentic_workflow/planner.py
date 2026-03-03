from __future__ import annotations

from typing import Any


def planner(goal: str, memory: list[dict[str, Any]]) -> dict[str, Any]:
    """Phase 1 deterministic planner.

    Phase 1 keeps planner simple and structured so it can be replaced by an LLM planner in Phase 3.
    """
    if not memory:
        return {
            "step": "Gather initial context for the goal",
            "tool": "defer_tool_layer",
            "input": goal,
        }

    return {
        "step": "Produce a concise conclusion from collected intermediate outputs",
        "tool": "defer_tool_layer",
        "input": "summarize_memory",
    }
