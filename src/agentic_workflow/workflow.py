from __future__ import annotations

import importlib
from typing import Any, Literal

from .executor import execute_plan
from .planner import planner
from .state import AgentState
from .verifier import verify_goal


def planner_node(state: AgentState) -> AgentState:
    state["plan"] = planner(goal=state["goal"], memory=state["memory"])
    return state


def executor_node(state: AgentState) -> AgentState:
    result = execute_plan(plan=state["plan"], goal=state["goal"], memory=state["memory"])
    state["tool_result"] = result
    state["memory"].append({
        "iteration": state["iteration"],
        "plan": state["plan"],
        "result": result,
    })
    return state


def verifier_node(state: AgentState) -> AgentState:
    verdict = verify_goal(
        goal=state["goal"],
        memory=state["memory"],
        iteration=state["iteration"],
        max_iterations=state["max_iterations"],
    )
    state["goal_achieved"] = verdict["goal_achieved"]
    state["status"] = verdict["status"]
    state["final_answer"] = verdict["final_answer"]
    state["iteration"] += 1
    return state


def route_after_verifier(state: AgentState) -> Literal["planner", "end"]:
    if state["goal_achieved"] or state["status"] in {"complete", "failed"}:
        return "end"
    return "planner"


def build_workflow():
    graph_module = importlib.import_module("langgraph.graph")
    END = getattr(graph_module, "END")
    START = getattr(graph_module, "START")
    StateGraph = getattr(graph_module, "StateGraph")

    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("verifier", verifier_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "verifier")
    graph.add_conditional_edges("verifier", route_after_verifier, {"planner": "planner", "end": END})

    return graph.compile()


def run_agent_goal(goal: str, max_iterations: int = 8) -> dict[str, Any]:
    app = build_workflow()
    initial_state: AgentState = {
        "goal": goal,
        "plan": {},
        "tool_result": None,
        "memory": [],
        "status": "running",
        "iteration": 0,
        "max_iterations": max_iterations,
        "goal_achieved": False,
        "final_answer": "",
    }
    final_state = app.invoke(initial_state)
    return {
        "goal": final_state["goal"],
        "status": final_state["status"],
        "goal_achieved": final_state["goal_achieved"],
        "iterations": final_state["iteration"],
        "plan": final_state["plan"],
        "tool_result": final_state["tool_result"],
        "memory": final_state["memory"],
        "final_answer": final_state["final_answer"],
    }
