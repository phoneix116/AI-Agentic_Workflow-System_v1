from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from tools import get_tool_specs, run_tool


def _looks_like_calculation(text: str) -> bool:
    lowered = text.lower()
    has_math_words = any(
        token in lowered
        for token in ["calculate", "compute", "solve", "plus", "minus", "times", "divided", "multiply", "subtract", "add"]
    )
    has_operator_expression = bool(re.search(r"\d+\s*[\+\-\*\/\^%]\s*\d+", text))
    is_standalone_expression = bool(re.fullmatch(r"\s*[\d\s\+\-\*\/\(\)\.\%\^]+\s*", text))
    return has_math_words or has_operator_expression or is_standalone_expression


def _looks_like_search_request(text: str) -> bool:
    lowered = text.lower()
    search_intent_keywords = [
        "search",
        "find",
        "research",
        "latest",
        "news",
        "weather",
        "internet",
        "lookup",
        "look up",
        "current",
        "today",
        "headline",
        "price",
        "top",
        "best",
    ]
    return any(word in lowered for word in search_intent_keywords)


def _looks_like_file_request(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ["read", "file", ".py", ".md", ".txt", ".json", ".csv", ".yaml", ".yml"])


def _looks_like_python_request(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ["python", "code", "script", "parse", "transform"])


def _is_general_conversation(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if _looks_like_search_request(stripped):
        return False
    if _looks_like_calculation(stripped):
        return False
    if _looks_like_file_request(stripped):
        return False
    if _looks_like_python_request(stripped):
        return False
    return True


def _extract_json(text: str) -> dict[str, Any] | None:
    candidate = text.strip()

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        try:
            parsed = json.loads(fenced_match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        maybe = text[start : end + 1]
        try:
            parsed = json.loads(maybe)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None

    return None


class GroqClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        if not self.api_key:
            raise RuntimeError("Missing GROQ_API_KEY")

        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("Missing Groq SDK. Install with: pip install groq") from exc

        self._client = Groq(api_key=self.api_key)
        return self._client

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("Missing GROQ_API_KEY")

        client = self._get_client()

        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                top_p=1,
                stream=False,
                stop=None,
            )

            choices = getattr(completion, "choices", None) or []
            if not choices:
                raise RuntimeError("Groq response had no choices")

            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", "") if message is not None else ""
            text = str(content or "").strip()
            if not text:
                raise RuntimeError("Groq response content was empty")
            return text
        except RuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001
            status_code = getattr(exc, "status_code", None)
            if status_code is not None:
                raise RuntimeError(f"Groq API call failed ({status_code}): {exc}") from exc
            raise RuntimeError(f"Groq API call failed: {exc}") from exc


class MemoryAgent:
    def __init__(self) -> None:
        self._state: dict[str, Any] = {}

    def load_snapshot(self, snapshot: dict[str, Any] | None) -> None:
        if isinstance(snapshot, dict):
            self._state = dict(snapshot)
        else:
            self._state = {}

    def write(self, key: str, value: Any) -> None:
        self._state[key] = value

    def append(self, key: str, value: Any) -> None:
        current = self._state.get(key)
        if not isinstance(current, list):
            current = []
        current.append(value)
        self._state[key] = current

    def read(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        return dict(self._state)


@dataclass
class PlannerAgent:
    groq: GroqClient
    model: str = "llama-3.3-70b-versatile"

    def plan(self, user_goal: str, memory: dict[str, Any] | None = None) -> list[str]:
        goal = user_goal.strip()
        if _is_general_conversation(goal):
            return [goal]

        system_prompt = (
            "You are the Planner Agent in a 5-agent system. "
            "Return only valid JSON with this exact shape: {\"tasks\": [\"task1\", \"task2\"]}. "
            "Tasks must be short, atomic, and executable with these capabilities: web search, calculator, python execution, file reading, or llm summarization."
        )
        user_prompt = json.dumps(
            {
                "user_goal": user_goal,
                "memory": memory or {},
                "max_tasks": 6,
            },
            ensure_ascii=False,
        )

        if self.groq.available():
            try:
                response_text = self.groq.chat(system_prompt, user_prompt, model=self.model)
                parsed = _extract_json(response_text)
                tasks = parsed.get("tasks", []) if parsed else []
                cleaned = [str(item).strip() for item in tasks if str(item).strip()]
                if cleaned:
                    return cleaned
            except RuntimeError:
                pass

        return [goal]


@dataclass
class RouterAgent:
    groq: GroqClient
    model: str = "llama-3.1-8b-instant"

    def _fallback_route(self, task: str) -> dict[str, Any]:
        lowered = task.lower()

        if _looks_like_search_request(task):
            return {
                "tool": "web_search",
                "tool_input": {"query": task, "max_results": 5},
                "reason": "Task requires external information.",
            }

        arithmetic_chunks = re.findall(r"[\d\s\+\-\*\/\(\)\.\%\^]+", task)
        expression_candidates = [
            chunk.strip()
            for chunk in arithmetic_chunks
            if re.search(r"\d", chunk) and re.search(r"[\+\-\*\/\^%]", chunk)
        ]
        inferred_expression = max(expression_candidates, key=len) if expression_candidates else ""
        if _looks_like_calculation(task):
            expression = inferred_expression or task.replace("calculate", "").strip()
            expression = expression or "0"
            expression = expression.replace("^", "**")
            return {
                "tool": "calculator",
                "tool_input": {"expression": expression},
                "reason": "Task requests arithmetic computation.",
            }

        if _looks_like_python_request(task):
            return {
                "tool": "python_execute",
                "tool_input": {"code": "print('No code provided to execute')"},
                "reason": "Task looks like code execution/transformation.",
            }

        if _looks_like_file_request(task):
            path_match = re.search(r"([\w./-]+\.(?:py|md|txt|json|csv|yaml|yml))", task)
            candidate = path_match.group(1) if path_match else ""
            return {
                "tool": "file_reader",
                "tool_input": {"path": candidate},
                "reason": "Task asks for file access.",
            }

        return {
            "tool": "llm_chat",
            "tool_input": {"prompt": task},
            "reason": "Default conversational response path.",
        }

    def route(self, task: str, memory: dict[str, Any]) -> dict[str, Any]:
        if _is_general_conversation(task):
            return {
                "tool": "llm_chat",
                "tool_input": {"prompt": task},
                "reason": "Direct conversational request.",
            }

        tool_specs = get_tool_specs()
        tool_specs.append(
            {
                "name": "llm_chat",
                "description": "General conversation and natural-language response generation.",
                "input_schema": {"prompt": "string"},
            }
        )
        system_prompt = (
            "You are the Router Agent. Pick exactly one tool and arguments for this task. "
            "Return only JSON with keys: tool, tool_input, reason."
        )
        user_prompt = json.dumps(
            {
                "task": task,
                "memory": memory,
                "available_tools": tool_specs,
            },
            ensure_ascii=False,
        )

        if self.groq.available():
            try:
                response_text = self.groq.chat(system_prompt, user_prompt, model=self.model)
                parsed = _extract_json(response_text)
                if parsed and parsed.get("tool") in {spec["name"] for spec in tool_specs}:
                    parsed.setdefault("tool_input", {})
                    parsed.setdefault("reason", "")
                    return parsed
            except RuntimeError:
                pass

        return self._fallback_route(task)


@dataclass
class ExecutorAgent:
    groq: GroqClient
    model: str = "llama-3.1-8b-instant"

    def _local_conversation_reply(self, prompt: str, memory: dict[str, Any] | None = None) -> str:
        lowered = prompt.lower().strip()
        memory_state = memory or {}
        user_profile = memory_state.get("user_profile", {}) if isinstance(memory_state, dict) else {}
        remembered_name = str(user_profile.get("name", "")).strip()

        if re.search(r"\b(what('?s| is) my name|do you remember my name)\b", lowered):
            if remembered_name:
                return f"Your name is {remembered_name}."
            return "You haven’t told me your name yet."

        name_match = re.search(r"\bmy name is\s+([a-zA-Z][a-zA-Z\-\s']{0,40})", prompt, flags=re.IGNORECASE)
        if name_match:
            supplied_name = name_match.group(1).strip().split()[0]
            return f"Nice to meet you, {supplied_name}."

        if re.search(r"\b(hi|hello|hey)\b", lowered) or "how are you" in lowered:
            return "Hey! I’m doing well. I can help with general questions, calculations, and web lookups."

        if any(phrase in lowered for phrase in ["what can you do", "help me", "capabilities"]):
            return (
                "I can chat normally, solve math, read local files, run Python snippets, and search the web "
                "for up-to-date info like weather, news, or current events."
            )

        if "moon" in lowered and any(word in lowered for word in ["distance", "far", "earth", "high"]):
            return "The Moon is about 384,400 km (238,855 miles) away from Earth on average."

        if any(word in lowered for word in ["thanks", "thank you"]):
            return "You’re welcome — happy to help."

        if any(word in lowered for word in ["bye", "goodbye"]):
            return "Got it. Talk soon."

        if "?" in prompt:
            return "I can help with that. If you want live data, ask me to search the web and I’ll fetch it."

        return "Understood. Tell me what you want to do next, and I’ll handle it step by step."

    def _run_llm_chat(self, prompt: str, memory: dict[str, Any] | None = None) -> dict[str, Any]:
        memory_state = memory or {}
        user_profile = memory_state.get("user_profile", {}) if isinstance(memory_state, dict) else {}
        chat_history = memory_state.get("chat_history", []) if isinstance(memory_state, dict) else []
        if not isinstance(chat_history, list):
            chat_history = []

        lowered = prompt.lower().strip()
        remembered_name = str(user_profile.get("name", "")).strip()
        intro_name_match = re.search(r"\bmy name is\s+([a-zA-Z][a-zA-Z\-\s']{0,40})", prompt, flags=re.IGNORECASE)
        if intro_name_match:
            introduced_name = intro_name_match.group(1).strip().split()[0]
            return {"ok": True, "response": f"Nice to meet you, {introduced_name}.", "from_memory": True}

        if re.search(r"\b(what('?s| is) my name|do you remember my name)\b", lowered) and remembered_name:
            return {"ok": True, "response": f"Your name is {remembered_name}.", "from_memory": True}

        if self.groq.available():
            try:
                response = self.groq.chat(
                    system_prompt=(
                        "You are a concise, helpful AI assistant. Use the provided memory context when relevant. "
                        "If user profile includes a name and user asks for their name, answer directly."
                    ),
                    user_prompt=json.dumps(
                        {
                            "user_message": prompt,
                            "memory": {
                                "user_profile": user_profile,
                                "recent_chat_history": chat_history[-8:],
                            },
                        },
                        ensure_ascii=False,
                    ),
                    model=self.model,
                    temperature=0.3,
                )
                return {"ok": True, "response": response}
            except RuntimeError as exc:
                fallback = self._local_conversation_reply(prompt, memory=memory_state)
                return {"ok": True, "response": fallback, "fallback": True, "error": str(exc)}

        return {
            "ok": True,
            "response": self._local_conversation_reply(prompt, memory=memory_state),
            "fallback": True,
        }

    def _fallback_final_answer(self, task_results: list[dict[str, Any]]) -> str:
        if not task_results:
            return "I could not produce a result for your request."

        for item in reversed(task_results):
            route = item.get("route", {})
            tool_name = str(route.get("tool", ""))
            tool_output = item.get("tool_output", {})

            if tool_name == "llm_chat" and isinstance(tool_output, dict) and tool_output.get("ok"):
                response = str(tool_output.get("response", "")).strip()
                if response:
                    return response

            if tool_name == "calculator" and isinstance(tool_output, dict) and tool_output.get("ok"):
                return f"The result is {tool_output.get('result')}."

            if tool_name == "web_search" and isinstance(tool_output, dict) and tool_output.get("ok"):
                results = tool_output.get("results", [])
                if isinstance(results, list) and results:
                    lines = ["Here are the top results I found:"]
                    for index, result in enumerate(results[:5], start=1):
                        title = result.get("title", "Untitled")
                        lines.append(f"{index}. {title}")
                    return "\n".join(lines)
                return "I searched the web but did not find clear results."

            if tool_name == "python_execute" and isinstance(tool_output, dict) and tool_output.get("ok"):
                stdout = str(tool_output.get("stdout", "")).strip()
                if stdout:
                    return stdout
                return "Python code ran successfully."

            if tool_name == "file_reader" and isinstance(tool_output, dict) and tool_output.get("ok"):
                content = str(tool_output.get("content", "")).strip()
                if content:
                    preview = content[:500]
                    return preview if len(content) <= 500 else f"{preview}..."

        last_output = task_results[-1].get("tool_output", {})
        if isinstance(last_output, dict) and last_output.get("error"):
            return f"I could not complete the request: {last_output.get('error')}"
        return "I completed the workflow, but I could not generate a clear final answer."

    def execute(
        self,
        task: str,
        route: dict[str, Any],
        file_root: str = ".",
        memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tool = str(route.get("tool", "")).strip()
        tool_input = route.get("tool_input", {})
        if not isinstance(tool_input, dict):
            tool_input = {}

        if tool == "llm_chat":
            output = self._run_llm_chat(prompt=str(tool_input.get("prompt", task)), memory=memory)
        else:
            output = run_tool(tool, tool_input=tool_input, file_root=file_root)
        return {
            "task": task,
            "route": route,
            "tool_output": output,
        }

    def synthesize_final_answer(self, user_goal: str, task_results: list[dict[str, Any]], memory: dict[str, Any]) -> str:
        if task_results:
            last = task_results[-1]
            last_route = last.get("route", {})
            last_tool = str(last_route.get("tool", ""))
            last_output = last.get("tool_output", {})

            if last_tool == "llm_chat" and isinstance(last_output, dict) and last_output.get("ok"):
                response = str(last_output.get("response", "")).strip()
                if response:
                    return response

            if last_tool == "calculator" and isinstance(last_output, dict) and last_output.get("ok"):
                return f"The result is {last_output.get('result')}."

        if self.groq.available():
            try:
                system_prompt = (
                    "You are the final answer writer. Return only the direct answer to the user. "
                    "Do not mention planning, tools, routes, memory, or internal reasoning. "
                    "If multiple results exist, summarize them briefly in user-friendly language."
                )
                user_prompt = json.dumps(
                    {
                        "user_goal": user_goal,
                        "task_results": task_results,
                        "memory": memory,
                    },
                    ensure_ascii=False,
                )
                return self.groq.chat(system_prompt, user_prompt, model=self.model, temperature=0.2)
            except RuntimeError:
                pass

        return self._fallback_final_answer(task_results)


@dataclass
class EvaluatorAgent:
    groq: GroqClient
    model: str = "llama-3.3-70b-versatile"

    def evaluate(self, user_goal: str, plan: list[str], task_results: list[dict[str, Any]], final_answer: str) -> dict[str, Any]:
        system_prompt = (
            "You are the Evaluator Agent. Determine if the final answer satisfies the goal using the task outputs. "
            "Return only JSON: {\"status\": \"pass\"|\"retry\", \"reason\": \"...\"}."
        )
        user_prompt = json.dumps(
            {
                "user_goal": user_goal,
                "plan": plan,
                "task_results": task_results,
                "final_answer": final_answer,
            },
            ensure_ascii=False,
        )

        if self.groq.available():
            try:
                response_text = self.groq.chat(system_prompt, user_prompt, model=self.model)
                parsed = _extract_json(response_text)
                if parsed and parsed.get("status") in {"pass", "retry"}:
                    parsed.setdefault("reason", "")
                    return parsed
            except RuntimeError:
                pass

        if final_answer.strip():
            return {"status": "pass", "reason": "Fallback evaluator accepted non-empty answer."}
        return {"status": "retry", "reason": "Final answer is empty."}