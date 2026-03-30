"""Schemas for editable user profile and assistant personalization."""

from typing import Optional

from pydantic import BaseModel, Field


class UserProfileData(BaseModel):
    """Normalized user profile payload used by frontend and LLM context."""

    user_id: str
    email: str
    name: str
    timezone: str
    language: str = Field(default="en")
    organization: Optional[str] = None
    role: Optional[str] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    communication_tone: Optional[str] = None
    role_context: Optional[str] = None
    ai_instructions: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Response wrapper for user profile retrieval."""

    profile: UserProfileData


class UserProfileUpdateRequest(BaseModel):
    """Editable profile fields from user tab."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    language: Optional[str] = Field(default=None, min_length=2, max_length=32)
    organization: Optional[str] = Field(default=None, max_length=255)
    role: Optional[str] = Field(default=None, max_length=255)
    working_hours_start: Optional[str] = Field(default=None, max_length=5)
    working_hours_end: Optional[str] = Field(default=None, max_length=5)
    communication_tone: Optional[str] = Field(default=None, max_length=50)
    role_context: Optional[str] = Field(default=None, max_length=2000)
    ai_instructions: Optional[str] = Field(default=None, max_length=2000)
