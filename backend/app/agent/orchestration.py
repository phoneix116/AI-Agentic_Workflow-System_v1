"""Planner -> router -> tools orchestration for chat requests."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import uuid4

from langchain_groq import ChatGroq
from sqlalchemy.orm import Session

from app.agent.state import (
    AgentState,
    InputTriggerType,
    PlannerDecision,
    PlannerOutput,
    ToolExecutionResult,
    ToolRequirement,
    UserInput,
    ResponseContent,
    ActionCard,
    PendingApproval,
    StateBuilder,
)
from app.agent.tools.calendar_tools import create_calendar_tools
from app.agent.tools.email_tools import create_email_tools
from app.agent.tools.planning_tools import create_planning_tools
from app.agent.tools.task_tools import create_task_tools
from app.cache.config import get_redis
from app.core.config import settings
from app.core.logging_config import get_trace_id
from app.core.metrics import metrics_collector
from app.db.models import Approval, User

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Lightweight orchestrator implementing planner, router and tool execution."""

    def __init__(self, db: Session):
        self.db = db
        self._planner_llm = None
        if settings.groq_api_key:
            self._planner_llm = ChatGroq(
                model=settings.groq_planner_model,
                temperature=0,
                api_key=settings.groq_api_key,
            )

    def execute_chat(self, user: User, message: str, session_id: str | None = None) -> AgentState:
        start = perf_counter()
        trace_id = get_trace_id() or str(uuid4())
        state = StateBuilder.create_initial_state(
            user_id=user.id,
            trace_id=trace_id,
            session_id=session_id or str(uuid4()),
            user_input=UserInput(type=InputTriggerType.USER_CHAT, content=message, context={"message_type": "text"}),
        )

        try:
            self._run_planner(state)
            self._run_router(state)
            self._run_tools(state, user)
            self._build_response(state)
            self._persist_state(state)

            state.metadata.end_time = datetime.utcnow()
            state.metadata.execution_time_ms = (perf_counter() - start) * 1000
            metrics_collector.record_agent_step("orchestration.execute_chat", "success", state.metadata.execution_time_ms)
            return state

        except Exception as exc:
            state.metadata.errors.append({"message": str(exc), "timestamp": datetime.utcnow().isoformat()})
            state.metadata.end_time = datetime.utcnow()
            state.metadata.execution_time_ms = (perf_counter() - start) * 1000
            metrics_collector.record_agent_step("orchestration.execute_chat", "error", state.metadata.execution_time_ms)
            logger.error("orchestration.execute_chat.error", extra={"trace_id": trace_id, "user_id": user.id}, exc_info=True)
            state.response = ResponseContent(message="I could not complete that request right now. Please try again.")
            return state

    def _run_planner(self, state: AgentState) -> None:
        if self._run_planner_with_llm(state):
            return

        logger.warning(
            "orchestration.planner.llm_failed_no_fallback",
            extra={"trace_id": state.trace_id, "user_id": state.user_id},
        )
        state.plan = PlannerOutput(
            action_type=PlannerDecision.CHAT_RESPONSE,
            reasoning="Unable to determine intent from LLM. Responding conversationally.",
            tools_required=[],
            requires_approval=False,
            confidence=0.5,
            estimated_duration_seconds=1.0,
        )
        state.current_node = "planner"
        state.metadata.nodes_executed.append("planner")

    def _run_planner_with_llm(self, state: AgentState) -> bool:
        if not self._planner_llm:
            return False

        supported_actions = [decision.value for decision in PlannerDecision]
        supported_tools = [
            "fetch_latest_emails",
            "summarize_inbox",
            "check_urgent_emails",
            "generate_draft_reply",
            "list_tasks",
            "create_task",
            "update_task",
            "move_task",
            "list_free_slots",
            "find_best_slot",
            "create_event",
            "generate_daily_plan",
        ]

        prompt = (
            "You are an expert intent planner for an AI assistant. Your task is to understand the semantic intent "
            "of user messages and determine the best action and tools to execute.\n\n"
            "INTENT UNDERSTANDING (not keyword matching):\n"
            "- User wants to review/send emails: INTENT = email operations\n"
            "- User wants to check calendar/see free slots/schedule meeting: INTENT = calendar operations\n"
            "- User wants to create/update/complete tasks: INTENT = task management\n"
            "- User needs help planning/organizing: INTENT = planning\n"
            "- Otherwise: INTENT = conversational response\n\n"
            "Return ONLY valid JSON with this schema:\n"
            "{\n"
            "  \"action_type\": string (one of the allowed values),\n"
            "  \"reasoning\": string (explain your semantic understanding),\n"
            "  \"requires_approval\": boolean (true if action modifies data),\n"
            "  \"approval_reason\": string|null,\n"
            "  \"confidence\": number (0-1, 1=certain),\n"
            "  \"tools_required\": [{\"tool_name\": string, \"parameters\": object}]\n"
            "}\n\n"
            f"Allowed action_type values: {supported_actions}\n"
            f"Allowed tool_name values: {supported_tools}\n\n"
            "RULES:\n"
            "1. Base decisions on semantic intent, not keywords\n"
            "2. If tools_required is empty, set action_type=chat_response\n"
            "3. Always include a reasoning field explaining what the user is trying to accomplish\n"
            "4. Return valid JSON even if you're unsure - use confidence field\n"
            "5. If message is unclear, use chat_response action\n\n"
            f"User message: {state.user_input.content or ''}"
        )

        try:
            result = self._planner_llm.invoke(prompt)
            raw_content = str(result.content).strip()
            data = self._extract_json(raw_content)

            action_type = str(data.get("action_type", PlannerDecision.CHAT_RESPONSE.value)).lower()
            if action_type not in supported_actions:
                action_type = PlannerDecision.CHAT_RESPONSE.value

            action_enum = PlannerDecision(action_type)
            tools_required: list[ToolRequirement] = []

            for entry in data.get("tools_required", []):
                tool_name = str(entry.get("tool_name", "")).strip()
                if tool_name not in supported_tools:
                    continue
                tools_required.append(
                    ToolRequirement(
                        tool_name=tool_name,
                        parameters=entry.get("parameters") or {},
                    )
                )

            message_text = (state.user_input.content or "").lower()
            likely_actionable = any(
                keyword in message_text
                for keyword in [
                    "email",
                    "emails",
                    "mail",
                    "mails",
                    "inbox",
                    "calendar",
                    "meeting",
                    "schedule",
                    "task",
                    "todo",
                    "plan",
                ]
            )
            if action_enum == PlannerDecision.CHAT_RESPONSE and not tools_required and likely_actionable:
                return False

            state.plan = PlannerOutput(
                action_type=action_enum,
                reasoning=str(data.get("reasoning", "LLM intent classification")),
                tools_required=tools_required,
                requires_approval=bool(data.get("requires_approval", False)),
                approval_reason=data.get("approval_reason"),
                confidence=float(data.get("confidence", 0.75)),
                estimated_duration_seconds=2.0,
            )
            state.current_node = "planner"
            state.metadata.nodes_executed.append("planner")
            return True
        except Exception:
            logger.warning(
                "orchestration.planner.llm_fallback",
                extra={"trace_id": state.trace_id, "user_id": state.user_id},
                exc_info=True,
            )
            return False

    @staticmethod
    def _extract_json(raw_content: str) -> dict[str, Any]:
        if raw_content.startswith("```"):
            lines = raw_content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_content = "\n".join(lines).strip()
        return json.loads(raw_content)


    def _run_router(self, state: AgentState) -> None:
        tool_names = [tool.tool_name for tool in (state.plan.tools_required if state.plan else [])]
        state.router_decision = tool_names
        state.current_node = "router"
        state.metadata.nodes_executed.append("router")

    def _run_tools(self, state: AgentState, user: User) -> None:
        tools = {}
        tools.update(create_email_tools(self.db))
        tools.update(create_task_tools(self.db))
        tools.update(create_calendar_tools(self.db))
        tools.update(create_planning_tools(self.db))

        for requirement in state.plan.tools_required if state.plan else []:
            start = perf_counter()
            tool_name = requirement.tool_name
            params = dict(requirement.parameters)

            if params.get("email_id") == "latest":
                latest_raw = tools["fetch_latest_emails"](user_id=user.id, limit=1)
                latest = self._normalize_tool_result("fetch_latest_emails", latest_raw)
                emails = latest.get("emails", []) if isinstance(latest.get("emails", []), list) else []
                if latest.get("status") != "success" or not emails:
                    result = {"status": "failed", "error": "No recent emails found"}
                    if latest.get("status") != "success" and latest.get("error"):
                        result["error"] = latest.get("error")
                    state.tool_results.append(
                        ToolExecutionResult(
                            tool_name=tool_name,
                            success=False,
                            result=result,
                            error=result.get("error"),
                            execution_time_ms=(perf_counter() - start) * 1000,
                        )
                    )
                    continue
                params["email_id"] = emails[0]["id"]

            try:
                tool_fn = tools.get(tool_name)
                if not tool_fn:
                    result = {"status": "failed", "error": f"Unknown tool: {tool_name}"}
                else:
                    raw_result = tool_fn(user_id=user.id, **params)
                    result = self._normalize_tool_result(tool_name, raw_result)

                success = result.get("status") == "success"
                error_text = result.get("error")
                state.tool_results.append(
                    ToolExecutionResult(
                        tool_name=tool_name,
                        success=success,
                        result=result,
                        error=error_text,
                        execution_time_ms=(perf_counter() - start) * 1000,
                    )
                )

                self._capture_pending_approval(state, user, tool_name, result)

            except Exception as exc:
                state.tool_results.append(
                    ToolExecutionResult(
                        tool_name=tool_name,
                        success=False,
                        result=None,
                        error=str(exc),
                        execution_time_ms=(perf_counter() - start) * 1000,
                    )
                )

        state.current_node = "tools"
        state.metadata.nodes_executed.append("tools")

    @staticmethod
    def _normalize_tool_result(tool_name: str, raw_result: Any) -> dict[str, Any]:
        """Convert tool outputs into a consistent payload shape for downstream handling."""
        if not isinstance(raw_result, dict):
            return {
                "status": "failed",
                "error": f"Unexpected result type from {tool_name}: {type(raw_result).__name__}",
                "raw_result": raw_result,
            }

        result = dict(raw_result)
        status = str(result.get("status", "")).lower()

        if status in {"success", "failed"}:
            return result

        if result.get("success") is True:
            result["status"] = "success"
            return result

        if result.get("error"):
            result["status"] = "failed"
            return result

        result["status"] = "failed"
        result["error"] = result.get("error") or "Tool returned an unrecognized payload"
        return result

    def _capture_pending_approval(self, state: AgentState, user: User, tool_name: str, result: dict) -> None:
        approval_id = result.get("approval_id")
        if not approval_id and result.get("requires_approval") and tool_name == "generate_draft_reply":
            approval_id = self._create_draft_approval(user, result)

        if not approval_id:
            return

        state.pending_approval = PendingApproval(
            approval_id=approval_id,
            action_type=result.get("action_type") or state.plan.action_type.value,
            action_payload=result,
            reason=(state.plan.approval_reason if state.plan else "Approval required"),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            ai_confidence=state.plan.confidence if state.plan else 0.8,
        )
        self._publish_approval_requested(user_id=user.id, approval_id=approval_id, result=result, trace_id=state.trace_id)

    def _create_draft_approval(self, user: User, result: dict) -> str | None:
        draft = result.get("draft") or {}
        if not draft:
            return None

        try:
            approval = Approval(
                user_id=user.id,
                approval_type=Approval.ApprovalType.SEND_EMAIL,
                status=Approval.ApprovalStatus.PENDING,
                action_description=f"Send drafted email to {draft.get('to_recipient', 'recipient')}",
                action_payload=draft,
                ai_reasoning="AI generated an email draft",
                confidence_score=float(draft.get("confidence", 0.8)),
                expires_at=datetime.utcnow() + timedelta(minutes=15),
            )
            self.db.add(approval)
            self.db.commit()
            return approval.id
        except Exception:
            self.db.rollback()
            return None

    def _publish_approval_requested(self, user_id: str, approval_id: str, result: dict, trace_id: str) -> None:
        payload = {
            "type": "approvals:requested",
            "approval_id": approval_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id,
            "data": {
                "approval_id": approval_id,
                "action_type": result.get("action_type", "other"),
                "preview": result.get("event_preview") or result.get("draft") or {},
            },
        }
        try:
            redis_client = get_redis()
            redis_client.publish(f"ws:approvals:{user_id}", json.dumps(payload))
        except Exception:
            logger.warning("orchestration.publish_approval_requested.failed", extra={"trace_id": trace_id, "user_id": user_id})

    def _build_response(self, state: AgentState) -> None:
        if state.pending_approval:
            state.response = ResponseContent(
                message="I prepared this action and it now needs your approval before execution.",
                action_cards=[
                    ActionCard(
                        id=state.pending_approval.approval_id,
                        label="Review approval",
                        action="approve",
                        payload={"approval_id": state.pending_approval.approval_id},
                    )
                ],
                suggested_follow_ups=["Approve this action", "Modify this action", "Reject this action"],
            )
            state.current_node = "awaiting_approval"
            state.metadata.nodes_executed.append("awaiting_approval")
            return

        successful = [item for item in state.tool_results if item.success]
        failed = [item for item in state.tool_results if not item.success]
        if not successful:
            if state.plan and not state.plan.tools_required:
                message = (
                    "I can help with email, calendar, tasks, and day planning. "
                    "Try asking: 'check my mails', 'summarize my inbox', or 'show my tasks'."
                )
            elif failed:
                error_text = " | ".join((item.error or "").lower() for item in failed)
                if (
                    "gmail not connected" in error_text
                    or "no emails found" in error_text
                    or "failed to summarize inbox" in error_text
                ):
                    message = (
                        "I could not access your inbox right now. "
                        "Please connect Gmail (or sync sample data) and try again."
                    )
                elif "calendar not connected" in error_text:
                    message = "I could not access your calendar because Calendar is not connected yet. Please connect Calendar and try again."
                elif "not found" in error_text:
                    message = "I could not find the required data for that request. Please try a more specific prompt."
                else:
                    message = "I could not complete that request yet. Please try again in a moment."
            else:
                message = "I could not complete that request yet. Please try again in a moment."
        else:
            first = successful[0]
            if first.tool_name == "generate_daily_plan":
                summary = (first.result or {}).get("plan", {}).get("summary", {})
                message = (
                    "Here is your plan for today: "
                    f"{summary.get('high_priority_tasks', 0)} high-priority tasks, "
                    f"{summary.get('total_tasks', 0)} total tasks, and "
                    f"{summary.get('urgent_emails', 0)} urgent emails."
                )
            else:
                message = f"Completed using {first.tool_name}."

        state.response = ResponseContent(
            message=message,
            suggested_follow_ups=["What is next on my calendar?", "Show my top tasks", "Summarize urgent emails"],
        )
        state.current_node = "response_generator"
        state.metadata.nodes_executed.append("response_generator")

    def _persist_state(self, state: AgentState) -> None:
        try:
            redis_client = get_redis()
            cache_key = f"state:{state.user_id}:{state.trace_id}"
            redis_client.setex(cache_key, 86400, json.dumps(state.to_redis_dict(), default=str))
        except Exception:
            logger.warning("orchestration.persist_state.failed", extra={"trace_id": state.trace_id, "user_id": state.user_id})
