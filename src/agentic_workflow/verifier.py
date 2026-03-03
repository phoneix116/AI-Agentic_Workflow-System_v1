from __future__ import annotations

from typing import Any


def verify_goal(goal: str, memory: list[dict[str, Any]], iteration: int, max_iterations: int) -> dict[str, Any]:
    """Phase 1 verifier with loop-stop safeguards."""
    if iteration >= max_iterations:
        return {
            "goal_achieved": False,
            "status": "failed",
            "final_answer": "Stopped after reaching max iterations.",
        }

    if len(memory) >= 2:
        last_output = str(memory[-1].get("result", {}).get("output", "")).strip()
        answer = last_output or f"Completed Phase 1 reasoning loop for goal: {goal}"
        return {
            "goal_achieved": True,
            "status": "complete",
            "final_answer": answer,
        }

    return {
        "goal_achieved": False,
        "status": "running",
        "final_answer": "",
    }
