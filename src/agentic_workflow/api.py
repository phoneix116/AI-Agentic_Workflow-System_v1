from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .workflow import run_agent_goal


class RunAgentRequest(BaseModel):
    goal: str = Field(..., min_length=3)
    max_iterations: int = Field(default=8, ge=1, le=20)


app = FastAPI(title="Agentic AI Workflow - Phase 1", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run-agent")
def run_agent(payload: RunAgentRequest) -> dict:
    return run_agent_goal(goal=payload.goal, max_iterations=payload.max_iterations)
