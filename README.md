# Agentic AI Workflow (Groq + 5 Agents)

A production-style agentic workflow with:
- **Planner Agent** (task decomposition)
- **Router Agent** (tool selection)
- **Executor Agent** (tool execution + chat)
- **Memory Agent** (session memory)
- **Evaluator Agent** (final quality check)

Includes a FastAPI backend, streaming chat endpoint, and a web chat UI showing a linear execution trace.

## Features

- Groq SDK integration (`groq` Python package)
- Tooling: `web_search`, `calculator`, `python_execute`, `file_reader`
- General conversation + tool-driven tasks
- Session memory retention with automatic pruning:
  - Keeps at most **15 user messages** in memory
  - Oldest user message is dropped when limit is exceeded
- SSE streaming for real-time plan/route/execution/evaluation events

## Project Structure

- `agent_nodes.py` — all 5 agents + Groq client
- `tools.py` — tool implementations and dispatch
- `workflow.py` — orchestration engine
- `api_server.py` — FastAPI app (`/chat`, `/chat/stream`, `/health`, `/health/groq`)
- `chat_ui.html` — frontend chat interface
- `run_api.sh` — startup script (loads `.env`, auto-port handling)

## Prerequisites

- Python 3.11+ (tested in venv)
- Groq API key
- SerpAPI key (for web search tool)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn groq
```

Create `.env` in repo root:

```env
GROQ_API_KEY=your_groq_key
SERPAPI_API_KEY=your_serpapi_key

HOST=127.0.0.1
PORT=8003

PLANNER_MODEL=llama-3.3-70b-versatile
ROUTER_MODEL=llama-3.1-8b-instant
EXECUTOR_MODEL=llama-3.1-8b-instant
EVALUATOR_MODEL=llama-3.3-70b-versatile
```

## Run

```bash
./run_api.sh
```

Open:
- UI: `http://127.0.0.1:8003/`
- Health: `http://127.0.0.1:8003/health`
- Groq diagnostic: `http://127.0.0.1:8003/health/groq`

## API

### POST `/chat`

Request:

```json
{
  "message": "my name is cyril",
  "max_iterations": 6,
  "file_root": ".",
  "session_id": "optional-session-id"
}
```

Response includes:
- `final_answer`
- `plan`
- `task_results`
- `memory`
- `session_id`

### GET `/chat/stream`

Query params:
- `message`
- `max_iterations`
- `file_root`
- `session_id` (optional but recommended for memory continuity)

Returns SSE events: `session`, `plan`, `route`, `execution`, `evaluation`, `final`.

## Session Memory

- Memory is stored server-side per `session_id`
- Frontend stores `session_id` in browser local storage
- Name recall example:
  1. `my name is cyril`
  2. `what's my name?` → `Your name is cyril.`

## Quick Test

```bash
curl -sS -X POST http://127.0.0.1:8003/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello","max_iterations":6,"file_root":"."}'
```

```bash
curl -N -sS "http://127.0.0.1:8003/chat/stream?message=calculate%2023-43&max_iterations=8&file_root=." | head -n 20
```
