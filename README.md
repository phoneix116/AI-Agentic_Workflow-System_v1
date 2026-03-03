# Agentic AI Workflow System

Phase 1 implementation of the core autonomous loop from the project markdown docs.

## Implemented in Phase 1
- Basic LangGraph workflow (`planner -> executor -> verifier -> loop/end`)
- Planner node
- Executor node
- Verifier node
- Agent memory state management

## Files
- `src/agentic_workflow/state.py`
- `src/agentic_workflow/planner.py`
- `src/agentic_workflow/executor.py`
- `src/agentic_workflow/verifier.py`
- `src/agentic_workflow/workflow.py`
- `src/agentic_workflow/api.py`

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.agentic_workflow.main:app --reload
```

## API
- `GET /health`
- `POST /run-agent`

Example payload:
```json
{
  "goal": "Analyze this startup idea and suggest initial competitors",
  "max_iterations": 8
}
```

## Notes
- This is Phase 1 only.
- External tools (web search, Python execution, file reader, calculator) are deferred to Phase 2.
- LLM planning is deferred to Phase 3; planner is intentionally deterministic for now.
