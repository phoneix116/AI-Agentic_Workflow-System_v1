"""User profile endpoints for personalization and assistant context."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import TokenPayload, get_current_user
from app.db.config import get_db
from app.db.models import User
from app.schemas.common import ApiResponse
from app.schemas.user_profile import UserProfileData, UserProfileResponse, UserProfileUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _guess_organization_from_email(email: str) -> str | None:
    if "@" not in email:
        return None

    domain = email.split("@", 1)[1]
    label = domain.split(".", 1)[0]
    cleaned = label.replace("-", " ").replace("_", " ").strip()
    if not cleaned:
        return None
    return " ".join(chunk.capitalize() for chunk in cleaned.split())


def _build_profile(user: User) -> UserProfileData:
    preferences = dict(user.preferences or {})
    profile = dict(preferences.get("assistant_profile") or {})

    return UserProfileData(
        user_id=user.id,
        email=user.email,
        name=user.name,
        timezone=user.timezone,
        language=profile.get("language") or preferences.get("language") or "en",
        organization=profile.get("organization") or _guess_organization_from_email(user.email),
        role=profile.get("role"),
        working_hours_start=profile.get("working_hours_start"),
        working_hours_end=profile.get("working_hours_end"),
        communication_tone=profile.get("communication_tone") or preferences.get("tone"),
        role_context=profile.get("role_context"),
        ai_instructions=profile.get("ai_instructions"),
    )


async def get_current_user_from_db(
    current_token: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == current_token.sub).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user_from_db),
) -> UserProfileResponse:
    """Return profile fields used by user tab and assistant personalization."""
    return UserProfileResponse(profile=_build_profile(current_user))


@router.put("/profile", response_model=ApiResponse)
async def update_user_profile(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """Persist editable profile fields in user row + preferences profile block."""

    preferences = dict(current_user.preferences or {})
    profile = dict(preferences.get("assistant_profile") or {})

    if payload.name is not None:
        current_user.name = payload.name.strip()

    if payload.timezone is not None:
        current_user.timezone = payload.timezone.strip()

    if payload.language is not None:
        language = payload.language.strip().lower()
        profile["language"] = language
        preferences["language"] = language

    if payload.organization is not None:
        profile["organization"] = _normalize_optional_text(payload.organization)

    if payload.role is not None:
        profile["role"] = _normalize_optional_text(payload.role)

    if payload.working_hours_start is not None:
        profile["working_hours_start"] = _normalize_optional_text(payload.working_hours_start)

    if payload.working_hours_end is not None:
        profile["working_hours_end"] = _normalize_optional_text(payload.working_hours_end)

    if payload.communication_tone is not None:
        tone = _normalize_optional_text(payload.communication_tone)
        profile["communication_tone"] = tone
        preferences["tone"] = tone

    if payload.role_context is not None:
        profile["role_context"] = _normalize_optional_text(payload.role_context)

    if payload.ai_instructions is not None:
        profile["ai_instructions"] = _normalize_optional_text(payload.ai_instructions)

    preferences["assistant_profile"] = profile
    current_user.preferences = preferences

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return ApiResponse(
        message="Profile updated",
        data={"profile": _build_profile(current_user).model_dump()},
    )
