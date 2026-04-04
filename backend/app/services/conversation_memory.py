"""Conversation memory persistence, caching, and retrieval helpers."""

from __future__ import annotations

import json
import logging
import importlib
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.cache.config import get_redis
from app.core.config import settings
from app.db.models import ConversationTurn, User
from app.repositories.repositories import (
    ConversationSessionRepository,
    ConversationTurnRepository,
    UserRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class RuntimeConversationContext:
    """Conversation context assembled for prompt personalization."""

    recent_turns: list[dict[str, Any]]
    semantic_memories: list[dict[str, Any]]
    last_message: Optional[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "recent_turns": self.recent_turns,
            "semantic_memories": self.semantic_memories,
            "last_message": self.last_message,
        }


class ConversationMemoryService:
    """Handles durable conversation storage and context retrieval."""

    _last_cleanup_at: Optional[datetime] = None

    def __init__(self, db: Session):
        self.db = db
        self._sessions = ConversationSessionRepository(db)
        self._turns = ConversationTurnRepository(db)
        self._users = UserRepository(db)

    @staticmethod
    def _recent_cache_key(user_id: str, session_id: str) -> str:
        return f"ctx:user:{user_id}:session:{session_id}:recent"

    @staticmethod
    def _profile_cache_key(user_id: str) -> str:
        return f"cache:user:{user_id}:profile"

    def get_runtime_context(
        self,
        *,
        user_id: str,
        session_id: str,
        query: str,
        recent_limit: Optional[int] = None,
        semantic_top_k: Optional[int] = None,
    ) -> RuntimeConversationContext:
        """Return recent + semantic context with Redis read-through fallback."""
        recent_limit = recent_limit or settings.conversation_history_window
        semantic_top_k = semantic_top_k or settings.conversation_semantic_top_k

        recent_turns = self._get_recent_turns_cached(
            user_id=user_id,
            session_id=session_id,
            limit=recent_limit,
        )
        semantic_memories = self._get_semantic_memories(
            user_id=user_id,
            query=query,
            top_k=semantic_top_k,
        )

        last_message = None
        for item in reversed(recent_turns):
            if item.get("role") == ConversationTurn.Role.USER.value:
                last_message = item
                break

        return RuntimeConversationContext(
            recent_turns=recent_turns,
            semantic_memories=semantic_memories,
            last_message=last_message,
        )

    def persist_turn_pair(
        self,
        *,
        user: User,
        session_id: str,
        user_message: str,
        assistant_message: str,
        trace_id: Optional[str],
        tool_results: Optional[list[dict[str, Any]]] = None,
        approval_id: Optional[str] = None,
    ) -> None:
        """Persist one user turn and one assistant turn, then refresh cache/indexes."""
        session = self._sessions.get_or_create(user_id=user.id, session_id=session_id)

        user_turn = self._turns.add_turn(
            user_id=user.id,
            conversation_session_id=session.id,
            session_id=session_id,
            role=ConversationTurn.Role.USER,
            content=user_message,
            metadata_json={"source": "chat_api"},
            trace_id=trace_id,
        )

        assistant_summary = self._summarize_assistant_reply(assistant_message)
        assistant_turn = self._turns.add_turn(
            user_id=user.id,
            conversation_session_id=session.id,
            session_id=session_id,
            role=ConversationTurn.Role.ASSISTANT,
            content=assistant_message,
            assistant_summary=assistant_summary,
            metadata_json={
                "tool_results": tool_results or [],
                "approval_id": approval_id,
                "source": "chat_api",
            },
            trace_id=trace_id,
        )

        session.last_activity_at = datetime.utcnow()

        # Keep last-message pointers in preferences for backward compatibility
        # when DB schema migrations have not been applied yet.
        preferences = dict(user.preferences or {})
        conversation_meta = dict(preferences.get("conversation_meta") or {})
        conversation_meta["last_session_id"] = session_id
        conversation_meta["last_user_message_at"] = (
            (user_turn.created_at or datetime.utcnow()).isoformat()
        )
        conversation_meta["last_turn_id"] = assistant_turn.id
        preferences["conversation_meta"] = conversation_meta
        user.preferences = preferences

        self.db.add(session)
        self.db.add(user)
        self.db.commit()

        self._refresh_recent_cache(user_id=user.id, session_id=session_id)
        self._invalidate_profile_cache(user_id=user.id)
        self._index_turn_for_semantic_search(
            user_id=user.id,
            session_id=session_id,
            turn_id=user_turn.id,
            content=user_turn.content,
            summary=assistant_summary,
            created_at=user_turn.created_at or datetime.utcnow(),
        )
        self._cleanup_expired_if_due()

    def get_history(
        self,
        *,
        user_id: str,
        session_id: Optional[str],
        skip: int,
        limit: int,
    ) -> tuple[list[ConversationTurn], int]:
        """Return chat history plus total row count."""
        try:
            if session_id:
                rows = self._turns.get_user_turns_for_session(
                    user_id=user_id,
                    session_id=session_id,
                    skip=skip,
                    limit=limit,
                )
                total = self._turns.count_user_turns(user_id=user_id, session_id=session_id)
                return rows, total

            rows = self._turns.get_user_turns(user_id=user_id, skip=skip, limit=limit)
            total = self._turns.count_user_turns(user_id=user_id)
            return rows, total
        except Exception:
            self.db.rollback()
            logger.warning("conversation_memory.get_history_fallback", exc_info=True)
            return [], 0

    def _get_recent_turns_cached(self, *, user_id: str, session_id: str, limit: int) -> list[dict[str, Any]]:
        redis_client = get_redis()
        cache_key = self._recent_cache_key(user_id=user_id, session_id=session_id)

        try:
            cached = redis_client.get(cache_key)
            if cached:
                parsed = json.loads(cached)
                if isinstance(parsed, list):
                    return parsed[:limit]
        except Exception:
            logger.warning("conversation_memory.cache_read_failed", exc_info=True)

        try:
            rows = self._turns.get_recent_for_session(user_id=user_id, session_id=session_id, limit=limit)
        except Exception:
            self.db.rollback()
            logger.warning("conversation_memory.recent_turns_db_fallback", exc_info=True)
            return []
        payload = [self._serialize_turn(row) for row in rows]

        try:
            redis_client.setex(cache_key, settings.conversation_cache_ttl_seconds, json.dumps(payload, default=str))
        except Exception:
            logger.warning("conversation_memory.cache_write_failed", exc_info=True)

        return payload

    def _refresh_recent_cache(self, *, user_id: str, session_id: str) -> None:
        try:
            rows = self._turns.get_recent_for_session(
                user_id=user_id,
                session_id=session_id,
                limit=max(20, settings.conversation_history_window),
            )
        except Exception:
            self.db.rollback()
            logger.warning("conversation_memory.refresh_recent_cache_db_failed", exc_info=True)
            return
        payload = [self._serialize_turn(row) for row in rows]
        redis_client = get_redis()
        cache_key = self._recent_cache_key(user_id=user_id, session_id=session_id)
        try:
            redis_client.setex(cache_key, settings.conversation_cache_ttl_seconds, json.dumps(payload, default=str))
        except Exception:
            logger.warning("conversation_memory.refresh_cache_failed", exc_info=True)

    def _invalidate_profile_cache(self, *, user_id: str) -> None:
        try:
            get_redis().delete(self._profile_cache_key(user_id))
        except Exception:
            logger.warning("conversation_memory.invalidate_profile_cache_failed", exc_info=True)

    def _get_semantic_memories(self, *, user_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        if not query.strip():
            return []

        elastic_memories = self._search_elasticsearch(user_id=user_id, query=query, top_k=top_k)
        try:
            corpus = self._turns.get_recent_user_turns(user_id=user_id, limit=200)
        except Exception:
            self.db.rollback()
            logger.warning("conversation_memory.semantic_corpus_fallback", exc_info=True)
            return []

        lexical_memories = self._rank_by_token_overlap(query=query, turns=corpus, top_k=max(top_k * 3, 10))
        vector_memories: list[dict[str, Any]] = []
        if settings.conversation_vector_enabled:
            vector_memories = self._rank_by_vector_similarity(query=query, turns=corpus, top_k=max(top_k * 3, 10))

        return self._merge_hybrid_results(
            top_k=top_k,
            primary=elastic_memories,
            lexical=lexical_memories,
            vector=vector_memories,
        )

    def _search_elasticsearch(self, *, user_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        Elasticsearch = self._resolve_elasticsearch_client()
        if Elasticsearch is None:
            return []

        try:
            client = Elasticsearch(settings.elasticsearch_url)
            body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"user_id": user_id}},
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["content^2", "summary"],
                                }
                            },
                        ]
                    }
                },
            }
            response = client.search(index=settings.elasticsearch_index_conversation, body=body)
            hits = response.get("hits", {}).get("hits", [])
            results: list[dict[str, Any]] = []
            for hit in hits:
                source = hit.get("_source") or {}
                results.append(
                    {
                        "turn_id": source.get("turn_id"),
                        "session_id": source.get("session_id"),
                        "content": source.get("content"),
                        "summary": source.get("summary"),
                        "score": float(hit.get("_score") or 0.0),
                        "created_at": source.get("created_at"),
                    }
                )
            return results
        except Exception:
            logger.warning("conversation_memory.elasticsearch_search_failed", exc_info=True)
            return []

    def _index_turn_for_semantic_search(
        self,
        *,
        user_id: str,
        session_id: str,
        turn_id: str,
        content: str,
        summary: str,
        created_at: datetime,
    ) -> None:
        Elasticsearch = self._resolve_elasticsearch_client()
        if Elasticsearch is None:
            return

        try:
            client = Elasticsearch(settings.elasticsearch_url)
            doc = {
                "turn_id": turn_id,
                "user_id": user_id,
                "session_id": session_id,
                "content": content,
                "summary": summary,
                "created_at": created_at.isoformat(),
            }
            client.index(index=settings.elasticsearch_index_conversation, id=turn_id, document=doc, refresh=False)
        except Exception:
            logger.warning("conversation_memory.elasticsearch_index_failed", exc_info=True)

    @staticmethod
    def _rank_by_token_overlap(query: str, turns: list[ConversationTurn], top_k: int) -> list[dict[str, Any]]:
        tokens = ConversationMemoryService._tokenize(query)
        if not tokens:
            return []

        scored: list[tuple[int, ConversationTurn]] = []
        for turn in turns:
            overlap = len(tokens.intersection(ConversationMemoryService._tokenize(turn.content or "")))
            if overlap > 0:
                scored.append((overlap, turn))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, turn in scored[:top_k]:
            results.append(
                {
                    "turn_id": turn.id,
                    "session_id": turn.session_id,
                    "content": turn.content,
                    "summary": turn.assistant_summary,
                    "score": float(score),
                    "created_at": turn.created_at.isoformat() if turn.created_at else None,
                }
            )
        return results

    @staticmethod
    def _embed_text(text: str, *, dimensions: int) -> list[float]:
        if dimensions <= 0:
            return []

        vector = [0.0] * dimensions
        normalized = (text or "").lower()
        tokens = re.findall(r"[a-z0-9]+", normalized)

        for token in tokens:
            if len(token) < 2:
                continue
            for idx in range(len(token) - 1):
                gram = token[idx : idx + 2]
                bucket = hash(gram) % dimensions
                vector[bucket] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        return float(sum(a * b for a, b in zip(vec_a, vec_b)))

    def _rank_by_vector_similarity(self, query: str, turns: list[ConversationTurn], top_k: int) -> list[dict[str, Any]]:
        dimensions = max(8, int(settings.conversation_vector_dim))
        query_vector = self._embed_text(query, dimensions=dimensions)
        if not any(query_vector):
            return []

        scored: list[tuple[float, ConversationTurn]] = []
        for turn in turns:
            turn_vector = self._embed_text(turn.content or "", dimensions=dimensions)
            similarity = self._cosine_similarity(query_vector, turn_vector)
            if similarity > 0:
                scored.append((similarity, turn))

        scored.sort(key=lambda item: item[0], reverse=True)

        results: list[dict[str, Any]] = []
        for similarity, turn in scored[:top_k]:
            results.append(
                {
                    "turn_id": turn.id,
                    "session_id": turn.session_id,
                    "content": turn.content,
                    "summary": turn.assistant_summary,
                    "score": float(similarity),
                    "created_at": turn.created_at.isoformat() if turn.created_at else None,
                    "source": "vector",
                }
            )
        return results

    @staticmethod
    def _merge_hybrid_results(
        *,
        top_k: int,
        primary: list[dict[str, Any]],
        lexical: list[dict[str, Any]],
        vector: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        lexical_weight = min(max(float(settings.conversation_hybrid_weight_lexical), 0.0), 1.0)
        vector_weight = min(max(float(settings.conversation_hybrid_weight_vector), 0.0), 1.0)
        if lexical_weight == 0 and vector_weight == 0:
            lexical_weight = 1.0

        combined: dict[str, dict[str, Any]] = {}

        for item in primary or []:
            key = str(item.get("turn_id") or "")
            if not key:
                continue
            enriched = dict(item)
            enriched["hybrid_score"] = float(item.get("score") or 0.0) * 1.1
            enriched["source"] = enriched.get("source") or "elasticsearch"
            combined[key] = enriched

        for item in lexical or []:
            key = str(item.get("turn_id") or "")
            if not key:
                continue
            lexical_score = float(item.get("score") or 0.0)
            if key not in combined:
                combined[key] = dict(item)
                combined[key]["source"] = combined[key].get("source") or "lexical"
                combined[key]["hybrid_score"] = lexical_score * lexical_weight
                continue
            combined[key]["hybrid_score"] = float(combined[key].get("hybrid_score") or 0.0) + (lexical_score * lexical_weight)

        for item in vector or []:
            key = str(item.get("turn_id") or "")
            if not key:
                continue
            vector_score = float(item.get("score") or 0.0)
            if key not in combined:
                combined[key] = dict(item)
                combined[key]["source"] = combined[key].get("source") or "vector"
                combined[key]["hybrid_score"] = vector_score * vector_weight
                continue
            combined[key]["hybrid_score"] = float(combined[key].get("hybrid_score") or 0.0) + (vector_score * vector_weight)

        ranked = sorted(combined.values(), key=lambda item: float(item.get("hybrid_score") or 0.0), reverse=True)
        output: list[dict[str, Any]] = []
        for item in ranked[:top_k]:
            normalized = dict(item)
            if "score" not in normalized:
                normalized["score"] = float(normalized.get("hybrid_score") or 0.0)
            output.append(normalized)
        return output

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {t for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(t) > 2}

    @staticmethod
    def _summarize_assistant_reply(message: str, max_chars: int = 240) -> str:
        text = (message or "").strip()
        if not text:
            return ""
        collapsed = " ".join(text.split())
        if len(collapsed) <= max_chars:
            return collapsed
        return f"{collapsed[:max_chars].rstrip()}..."

    @staticmethod
    def _serialize_turn(turn: ConversationTurn) -> dict[str, Any]:
        return {
            "id": turn.id,
            "session_id": turn.session_id,
            "role": turn.role.value if hasattr(turn.role, "value") else str(turn.role),
            "content": turn.content,
            "assistant_summary": turn.assistant_summary,
            "trace_id": turn.trace_id,
            "created_at": turn.created_at.isoformat() if turn.created_at else None,
        }

    def _cleanup_expired_if_due(self) -> None:
        now = datetime.utcnow()
        if self.__class__._last_cleanup_at and (
            now - self.__class__._last_cleanup_at
        ).total_seconds() < settings.conversation_cleanup_interval_seconds:
            return

        cutoff = now - timedelta(days=settings.conversation_retention_days)
        try:
            deleted = self._turns.prune_before(cutoff=cutoff)
            self.db.commit()
            self.__class__._last_cleanup_at = now
            if deleted:
                logger.info("conversation_memory.retention_cleanup", extra={"deleted": deleted})
        except Exception:
            self.db.rollback()
            logger.warning("conversation_memory.retention_cleanup_failed", exc_info=True)

    @staticmethod
    def _resolve_elasticsearch_client() -> Any:
        """Resolve Elasticsearch client class dynamically to keep runtime optional."""
        try:
            module = importlib.import_module("elasticsearch")
            return getattr(module, "Elasticsearch")
        except Exception:
            return None
