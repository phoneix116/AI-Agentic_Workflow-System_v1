from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import pathlib
import traceback
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


def _http_get_json(url: str) -> dict[str, Any]:
    request = Request(url=url, method="GET")
    with urlopen(request, timeout=20) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def web_search(query: str, max_results: int = 5, serpapi_api_key: str | None = None) -> dict[str, Any]:
    api_key = serpapi_api_key or os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {
            "ok": False,
            "error": "Missing SERPAPI_API_KEY. Set it in your environment.",
            "results": [],
        }

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": max_results,
    }
    url = f"https://serpapi.com/search.json?{urlencode(params)}"

    try:
        data = _http_get_json(url)
        organic_results = data.get("organic_results", [])[:max_results]
        reduced = [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in organic_results
        ]
        return {"ok": True, "query": query, "results": reduced}
    except (HTTPError, URLError, TimeoutError) as exc:
        return {"ok": False, "error": f"web_search failed: {exc}", "results": []}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON from SerpAPI: {exc}", "results": []}


def _eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_ast(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left**right
    raise ValueError("Expression contains unsupported syntax.")


def calculator(expression: str) -> dict[str, Any]:
    try:
        parsed = ast.parse(expression, mode="eval")
        value = _eval_ast(parsed)
        rounded = int(value) if value.is_integer() else value
        return {"ok": True, "expression": expression, "result": rounded}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"calculator failed: {exc}"}


def python_execute(code: str) -> dict[str, Any]:
    safe_builtins = {
        "print": print,
        "len": len,
        "range": range,
        "sum": sum,
        "min": min,
        "max": max,
        "sorted": sorted,
        "enumerate": enumerate,
    }
    globals_scope = {"__builtins__": safe_builtins}
    locals_scope: dict[str, Any] = {}
    stdout = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout):
            exec(compile(code, "<python_execute>", "exec"), globals_scope, locals_scope)
        safe_locals = {key: repr(value) for key, value in locals_scope.items() if not key.startswith("__")}
        return {
            "ok": True,
            "stdout": stdout.getvalue(),
            "locals": safe_locals,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"python_execute failed: {exc}",
            "traceback": traceback.format_exc(),
            "stdout": stdout.getvalue(),
        }


def file_reader(path: str, file_root: str = ".", max_chars: int = 12000) -> dict[str, Any]:
    try:
        root = pathlib.Path(file_root).resolve()
        target = (root / path).resolve()
        if not str(target).startswith(str(root)):
            return {"ok": False, "error": "Path escapes file_root."}
        if not target.exists() or not target.is_file():
            return {"ok": False, "error": f"File not found: {path}"}

        content = target.read_text(encoding="utf-8", errors="replace")
        truncated = content[:max_chars]
        return {
            "ok": True,
            "path": str(target),
            "content": truncated,
            "truncated": len(content) > len(truncated),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"file_reader failed: {exc}"}


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="web_search",
        description="Searches the web via SerpAPI and returns top organic results.",
        input_schema={"query": "string", "max_results": "integer (optional)"},
    ),
    ToolSpec(
        name="calculator",
        description="Evaluates arithmetic expressions safely.",
        input_schema={"expression": "string"},
    ),
    ToolSpec(
        name="python_execute",
        description="Executes short Python code with restricted builtins.",
        input_schema={"code": "string"},
    ),
    ToolSpec(
        name="file_reader",
        description="Reads a file within file_root.",
        input_schema={"path": "string", "max_chars": "integer (optional)"},
    ),
]


TOOL_FUNCTIONS: dict[str, Callable[..., dict[str, Any]]] = {
    "web_search": web_search,
    "calculator": calculator,
    "python_execute": python_execute,
    "file_reader": file_reader,
}


def get_tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
        }
        for spec in TOOL_SPECS
    ]


def run_tool(tool_name: str, tool_input: dict[str, Any] | None = None, file_root: str = ".") -> dict[str, Any]:
    payload = tool_input or {}

    if tool_name not in TOOL_FUNCTIONS:
        return {"ok": False, "error": f"Unknown tool: {tool_name}"}

    if tool_name == "web_search":
        return web_search(
            query=str(payload.get("query", "")),
            max_results=int(payload.get("max_results", 5)),
        )
    if tool_name == "calculator":
        return calculator(expression=str(payload.get("expression", "")))
    if tool_name == "python_execute":
        return python_execute(code=str(payload.get("code", "")))
    if tool_name == "file_reader":
        return file_reader(
            path=str(payload.get("path", "")),
            file_root=file_root,
            max_chars=int(payload.get("max_chars", 12000)),
        )

    return {"ok": False, "error": f"No dispatcher for tool: {tool_name}"}