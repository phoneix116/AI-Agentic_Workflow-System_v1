"""User profile endpoints for personalization and assistant context."""

from __future__ import annotations

import re
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import TokenPayload, get_current_user
from app.db.config import get_db
from app.db.models import User, Email
from app.schemas.common import ApiResponse
from app.schemas.user_profile import UserProfileData, UserProfileResponse, UserProfileUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])

PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "me.com",
    "proton.me",
    "protonmail.com",
    "aol.com",
}


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


def _extract_email_address(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", raw_value)
    return match.group(1).lower() if match else None


def _extract_display_name(raw_value: str | None) -> str | None:
    if not raw_value:
        return None

    candidate = raw_value
    if "<" in raw_value:
        candidate = raw_value.split("<", 1)[0]

    candidate = candidate.strip().strip('"').strip("'")
    if not candidate or "@" in candidate:
        return None

    normalized = " ".join(part.capitalize() for part in candidate.split())
    return normalized or None


def _infer_role_from_text(text: str) -> str | None:
    if not text:
        return None

    lowered = text.lower()
    role_patterns = [
        (r"\b(product manager|pm|product lead)\b", "Product Manager"),
        (r"\b(engineer|developer|software engineer|backend engineer|frontend engineer|full[- ]stack)\b", "Software Engineer"),
        (r"\b(manager|team lead|lead|director|vp|head of)\b", "Manager"),
        (r"\b(founder|co[- ]founder|ceo|cto|owner)\b", "Founder"),
        (r"\b(designer|ux|ui|product designer)\b", "Designer"),
        (r"\b(sales|account executive|business development|bdr)\b", "Sales"),
        (r"\b(marketing|growth|content strategist)\b", "Marketing"),
        (r"\b(recruiter|talent|human resources|hr)\b", "Recruiter"),
    ]

    for pattern, role in role_patterns:
        if re.search(pattern, lowered):
            return role
    return None


def _derive_profile_from_mail(user: User, db: Session) -> dict[str, str]:
    recent_emails = (
        db.query(Email)
        .filter(Email.user_id == user.id)
        .order_by(Email.received_at.desc())
        .limit(80)
        .all()
    )

    if not recent_emails:
        return {}

    user_email = (user.email or "").lower()
    domain_counts: Counter[str] = Counter()
    name_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()

    for email in recent_emails:
        sender_raw = email.sender or ""
        sender_email = _extract_email_address(sender_raw)
        sender_name = _extract_display_name(sender_raw)

        if sender_email == user_email and sender_name:
            name_counts[sender_name] += 2

        recipients = email.recipients if isinstance(email.recipients, list) else []
        recipient_emails = [_extract_email_address(str(entry)) for entry in recipients]

        for recipient in recipients:
            recipient_email = _extract_email_address(str(recipient))
            recipient_name = _extract_display_name(str(recipient))
            if recipient_email == user_email and recipient_name:
                name_counts[recipient_name] += 1

        for address in [sender_email, *recipient_emails]:
            if not address or address == user_email or "@" not in address:
                continue

            domain = address.split("@", 1)[1]
            if domain in PERSONAL_EMAIL_DOMAINS:
                continue
            domain_counts[domain] += 1

        if sender_email == user_email:
            role_signal_text = f"{email.subject or ''}\n{(email.body or '')[:1200]}"
            role = _infer_role_from_text(role_signal_text)
            if role:
                role_counts[role] += 1

    derived: dict[str, str] = {}
    if name_counts:
        derived["name"] = name_counts.most_common(1)[0][0]

    if domain_counts:
        top_domain = domain_counts.most_common(1)[0][0]
        guessed_org = _guess_organization_from_email(f"user@{top_domain}")
        if guessed_org:
            derived["organization"] = guessed_org

    if role_counts:
        derived["role"] = role_counts.most_common(1)[0][0]

    return derived


def _build_profile(user: User, db: Session | None = None) -> UserProfileData:
    preferences = dict(user.preferences or {})
    profile = dict(preferences.get("assistant_profile") or {})
    derived_from_mail = _derive_profile_from_mail(user, db) if db else {}

    resolved_name = user.name
    if resolved_name in {"User", "OAuth User"}:
        resolved_name = derived_from_mail.get("name") or resolved_name

    return UserProfileData(
        user_id=user.id,
        email=user.email,
        name=resolved_name,
        timezone=user.timezone,
        language=profile.get("language") or preferences.get("language") or "en",
        organization=(
            profile.get("organization")
            or derived_from_mail.get("organization")
            or _guess_organization_from_email(user.email)
        ),
        role=profile.get("role") or derived_from_mail.get("role"),
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
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Return profile fields used by user tab and assistant personalization."""
    return UserProfileResponse(profile=_build_profile(current_user, db))


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
        data={"profile": _build_profile(current_user, db).model_dump()},
    )
