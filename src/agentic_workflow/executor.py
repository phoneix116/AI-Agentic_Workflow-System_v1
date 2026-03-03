from __future__ import annotations

from typing import Any

from .state import ToolResult


def execute_plan(plan: dict[str, Any], goal: str, memory: list[dict[str, Any]]) -> ToolResult:
    """Phase 1 executor.

    Real external tools are added in Phase 2. Here we keep a structured execution contract.
    """
    if plan.get("input") == "summarize_memory":
        summary = " | ".join(
            str(item.get("result", {}).get("output", ""))
            for item in memory
            if isinstance(item, dict) and item.get("result")
        ).strip()
        output = summary or f"Goal analyzed in Phase 1 loop: {goal}"
    else:
        output = f"Prepared execution context for goal: {goal}"

    return {
        "status": "success",
        "output": output,
        "metadata": {
            "executed_tool": str(plan.get("tool", "")),
            "phase": "phase-1-core-loop",
        },
    }
