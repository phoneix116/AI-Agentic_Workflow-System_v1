from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse

from workflow import AgenticWorkflow, WorkflowConfig


def load_env_file(file_path: str = ".env") -> None:
    env_path = Path(file_path)
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()
app = FastAPI(title="5-Agent Workflow API", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent
SESSION_STORE: dict[str, dict[str, Any]] = {}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    max_iterations: int = Field(default=8, ge=1, le=20)
    file_root: str = Field(default=".")
    session_id: str | None = Field(default=None)


def _classify_groq_http_status(status_code: int) -> str:
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "model_or_endpoint_not_found"
    if status_code == 429:
        return "rate_limited"
    if 500 <= status_code <= 599:
        return "provider_server_error"
    return "http_error"


def run_groq_diagnostic(model: str | None = None) -> dict[str, Any]:
    api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    selected_model = model or os.getenv("ROUTER_MODEL") or "llama-3.1-8b-instant"

    if not api_key:
        return {
            "ok": False,
            "status": "missing_api_key",
            "model": selected_model,
            "message": "GROQ_API_KEY is not set.",
        }

    try:
        from groq import Groq
    except ImportError:
        return {
            "ok": False,
            "status": "sdk_not_installed",
            "model": selected_model,
            "message": "Groq SDK is not installed. Install with: pip install groq",
        }

    client = Groq(api_key=api_key)

    try:
        completion = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are a healthcheck endpoint."},
                {"role": "user", "content": "Reply with OK."},
            ],
            temperature=0,
            max_completion_tokens=8,
            top_p=1,
            stream=False,
            stop=None,
        )
        choices = getattr(completion, "choices", None) or []
        content = ""
        if choices:
            message = getattr(choices[0], "message", None)
            content = str(getattr(message, "content", "") or "")

        return {
            "ok": True,
            "status": "ok",
            "model": selected_model,
            "provider_http_status": 200,
            "response_preview": content[:120],
        }
    except Exception as exc:  # noqa: BLE001
        status_code = getattr(exc, "status_code", None)
        if status_code is not None:
            return {
                "ok": False,
                "status": _classify_groq_http_status(int(status_code)),
                "model": selected_model,
                "provider_http_status": int(status_code),
                "message": str(exc),
            }
        error_text = str(exc)
        if "timed out" in error_text.lower():
            status = "timeout"
        elif "network" in error_text.lower() or "connection" in error_text.lower():
            status = "network_error"
        else:
            status = "unexpected_error"
        return {
            "ok": False,
            "status": status,
            "model": selected_model,
            "message": error_text,
        }


@app.get("/", response_class=HTMLResponse)
def chat_ui() -> HTMLResponse:
    ui_path = BASE_DIR / "chat_ui.html"
    if not ui_path.exists():
        return HTMLResponse("<h1>chat_ui.html not found</h1>", status_code=404)
    return HTMLResponse(ui_path.read_text(encoding="utf-8", errors="replace"))


@app.get("/chat-ui", response_class=HTMLResponse)
def chat_ui_alias() -> HTMLResponse:
    return chat_ui()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "groq_key_present": bool(os.getenv("GROQ_API_KEY")),
        "serpapi_key_present": bool(os.getenv("SERPAPI_API_KEY")),
    }


@app.get("/health/groq")
def health_groq(model: str | None = None) -> JSONResponse:
    diagnostic = run_groq_diagnostic(model=model)
    status_code = 200 if diagnostic.get("ok") else 503
    return JSONResponse(content=diagnostic, status_code=status_code)


@app.post("/chat")
def chat(request: ChatRequest) -> JSONResponse:
    session_id = request.session_id or str(uuid4())
    initial_memory = SESSION_STORE.get(session_id, {})

    workflow = AgenticWorkflow(
        WorkflowConfig(max_iterations=request.max_iterations, file_root=request.file_root)
    )
    result = workflow.run(request.message, initial_memory=initial_memory)
    SESSION_STORE[session_id] = result.get("memory", {}) if isinstance(result, dict) else {}
    result["session_id"] = session_id
    return JSONResponse(content=result)


@app.get("/chat/stream")
def chat_stream(
    message: str,
    max_iterations: int = 8,
    file_root: str = ".",
    session_id: str | None = None,
) -> StreamingResponse:
    def event_stream():
        active_session_id = session_id or str(uuid4())
        initial_memory = SESSION_STORE.get(active_session_id, {})
        yield f"data: {json.dumps({'type': 'session', 'session_id': active_session_id}, ensure_ascii=False)}\n\n"

        workflow = AgenticWorkflow(WorkflowConfig(max_iterations=max_iterations, file_root=file_root))
        try:
            for event in workflow.run_stream(message, initial_memory=initial_memory):
                if event.get("type") == "final":
                    result = event.get("result")
                    if isinstance(result, dict):
                        SESSION_STORE[active_session_id] = result.get("memory", {})
                        result["session_id"] = active_session_id
                        event = {"type": "final", "result": result}
                payload = json.dumps(event, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except Exception as exc:  # noqa: BLE001
            payload = json.dumps({"type": "error", "error": str(exc)}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
