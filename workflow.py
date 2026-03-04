from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from typing import Any

from agent_nodes import EvaluatorAgent, ExecutorAgent, GroqClient, MemoryAgent, PlannerAgent, RouterAgent


@dataclass
class WorkflowConfig:
    max_iterations: int = 8
    file_root: str = "."
    planner_model: str = os.getenv("PLANNER_MODEL", "llama-3.3-70b-versatile")
    router_model: str = os.getenv("ROUTER_MODEL", "llama-3.1-8b-instant")
    executor_model: str = os.getenv("EXECUTOR_MODEL", "llama-3.1-8b-instant")
    evaluator_model: str = os.getenv("EVALUATOR_MODEL", "llama-3.3-70b-versatile")


class AgenticWorkflow:
    def __init__(self, config: WorkflowConfig) -> None:
        self.config = config
        groq = GroqClient()
        self.planner = PlannerAgent(groq=groq, model=config.planner_model)
        self.router = RouterAgent(groq=groq, model=config.router_model)
        self.executor = ExecutorAgent(groq=groq, model=config.executor_model)
        self.memory = MemoryAgent()
        self.evaluator = EvaluatorAgent(groq=groq, model=config.evaluator_model)

    @staticmethod
    def _extract_user_profile_updates(message: str) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        name_match = re.search(r"\bmy name is\s+([a-zA-Z][a-zA-Z\-\s']{0,40})", message, flags=re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip().split()[0]
            updates["name"] = name
        return updates

    @staticmethod
    def _prune_chat_history_by_user_limit(
        chat_history: list[dict[str, Any]] | Any,
        max_user_messages: int = 15,
    ) -> list[dict[str, Any]]:
        if not isinstance(chat_history, list):
            return []

        trimmed: list[dict[str, Any]] = [item for item in chat_history if isinstance(item, dict)]
        user_count = sum(1 for item in trimmed if item.get("role") == "user")

        while user_count > max_user_messages:
            oldest_user_index = next(
                (index for index, item in enumerate(trimmed) if item.get("role") == "user"),
                None,
            )
            if oldest_user_index is None:
                break
            trimmed.pop(oldest_user_index)
            user_count -= 1

        if len(trimmed) > 80:
            trimmed = trimmed[-80:]

        return trimmed

    def run_stream(self, user_goal: str, initial_memory: dict[str, Any] | None = None):
        self.memory.load_snapshot(initial_memory)

        chat_history = self.memory.read("chat_history", [])
        if not isinstance(chat_history, list):
            chat_history = []
        chat_history.append({"role": "user", "content": user_goal})
        chat_history = self._prune_chat_history_by_user_limit(chat_history, max_user_messages=15)
        self.memory.write("chat_history", chat_history)

        user_profile = self.memory.read("user_profile", {})
        if not isinstance(user_profile, dict):
            user_profile = {}
        user_profile_updates = self._extract_user_profile_updates(user_goal)
        if user_profile_updates:
            user_profile.update(user_profile_updates)
            self.memory.write("user_profile", user_profile)

        plan = self.planner.plan(user_goal=user_goal, memory=self.memory.snapshot())
        if not plan:
            plan = [user_goal]

        yield {"type": "plan", "plan": plan}

        task_results: list[dict[str, Any]] = []

        for index, task in enumerate(plan[: self.config.max_iterations], start=1):
            route = self.router.route(task=task, memory=self.memory.snapshot())
            yield {"type": "route", "task_index": index, "task": task, "route": route}

            execution = self.executor.execute(
                task=task,
                route=route,
                file_root=self.config.file_root,
                memory=self.memory.snapshot(),
            )
            task_results.append(execution)
            yield {"type": "execution", "task_index": index, "execution": execution}

            self.memory.append("task_history", execution)
            self.memory.write(f"task_{index}", execution)

        final_answer = self.executor.synthesize_final_answer(
            user_goal=user_goal,
            task_results=task_results,
            memory=self.memory.snapshot(),
        )

        evaluation = self.evaluator.evaluate(
            user_goal=user_goal,
            plan=plan,
            task_results=task_results,
            final_answer=final_answer,
        )
        yield {"type": "evaluation", "evaluation": evaluation}

        if evaluation.get("status") == "retry":
            final_answer = self.executor.synthesize_final_answer(
                user_goal=f"{user_goal}\nEvaluator feedback: {evaluation.get('reason', '')}",
                task_results=task_results,
                memory=self.memory.snapshot(),
            )
            evaluation = self.evaluator.evaluate(
                user_goal=user_goal,
                plan=plan,
                task_results=task_results,
                final_answer=final_answer,
            )
            yield {"type": "evaluation", "evaluation": evaluation, "retry": True}

        updated_chat_history = self.memory.read("chat_history", [])
        if not isinstance(updated_chat_history, list):
            updated_chat_history = []
        updated_chat_history.append({"role": "assistant", "content": final_answer})
        updated_chat_history = self._prune_chat_history_by_user_limit(updated_chat_history, max_user_messages=15)
        self.memory.write("chat_history", updated_chat_history)

        result = {
            "goal": user_goal,
            "plan": plan,
            "task_results": task_results,
            "memory": self.memory.snapshot(),
            "evaluation": evaluation,
            "final_answer": final_answer,
        }
        yield {"type": "final", "result": result}

    def run(self, user_goal: str, initial_memory: dict[str, Any] | None = None) -> dict[str, Any]:
        final: dict[str, Any] | None = None
        for event in self.run_stream(user_goal, initial_memory=initial_memory):
            if event.get("type") == "final":
                payload = event.get("result")
                if isinstance(payload, dict):
                    final = payload

        if final is None:
            raise RuntimeError("Workflow did not produce final output.")
        return final


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="5-Agent workflow with Groq + tools")
    parser.add_argument("--goal", required=True, help="User goal to process")
    parser.add_argument("--max-iterations", type=int, default=8, help="Maximum tasks to execute")
    parser.add_argument("--file-root", default=".", help="Root path for file_reader tool")
    parser.add_argument("--json", action="store_true", help="Print full JSON output")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = WorkflowConfig(max_iterations=args.max_iterations, file_root=args.file_root)
    workflow = AgenticWorkflow(config)
    result = workflow.run(args.goal)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("\n=== PLAN ===")
    for idx, task in enumerate(result["plan"], start=1):
        print(f"{idx}. {task}")

    print("\n=== FINAL ANSWER ===")
    print(result["final_answer"])

    print("\n=== EVALUATION ===")
    print(json.dumps(result["evaluation"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()