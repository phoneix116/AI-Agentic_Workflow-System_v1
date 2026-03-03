# Agentic AI Workflow System – Build Plan

## Goal
Build a reasoning-based AI system that:
- Breaks complex tasks into steps
- Selects appropriate tools
- Executes tools
- Stores memory
- Verifies goal completion
- Iterates if necessary

This is NOT a chatbot.
This is an autonomous reasoning + tool-using system.

---

# Phase 1 – Core Agent Loop (Day 1–2)

## Deliverables
- Basic LangGraph workflow
- Planner node
- Executor node
- Verifier node
- Memory state management

## Core Loop Logic

Pseudo-flow:

while not goal_achieved:
    plan = planner(goal, memory)
    tool_call = decide_tool(plan)
    result = execute(tool_call)
    memory.append(result)
    goal_achieved = verifier(memory)

## Implementation
- Use LangGraph StateGraph
- Define AgentState:
    - goal
    - plan
    - tool_result
    - memory
    - status

---

# Phase 2 – Tool Layer (Day 3–4)

## Tools to Implement

1. Web Search Tool
2. Python Execution Tool
3. File Reader Tool
4. Calculator Tool

Each tool must:
- Accept structured arguments
- Return structured JSON
- Handle errors gracefully

---

# Phase 3 – Planning Layer (Day 5–6)

## Planner Responsibilities
- Break goal into atomic steps
- Select tool per step
- Avoid hallucinated tools
- Think step-by-step

Use structured output format:

{
  "step": "...",
  "tool": "...",
  "input": "..."
}

---

# Phase 4 – Memory + Reflection (Day 7–8)

Add:
- Reflection node
- Retry logic
- Goal completion verification

Reflection questions:
- Did last action move toward goal?
- Is more information needed?
- Is the task complete?

---

# Phase 5 – API + Deployment (Day 9–10)

- Wrap system with FastAPI
- Add endpoint:
    POST /run-agent
- Dockerize
- Add logging
- Add basic observability

---

# MVP Success Criteria

- Handles multi-step reasoning
- Uses at least 3 tools correctly
- Stores intermediate memory
- Self-corrects at least once
- Returns structured final output
