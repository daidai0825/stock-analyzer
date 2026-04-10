"""Pydantic schemas for authentication and user management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for registering a new user account."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    """Payload for logging in — accepts either email or username as ``username``."""

    username: str  # accepts email or username
    password: str


class UserResponse(BaseModel):
    """Public representation of a user returned from the API."""

    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT access token returned after a successful authentication."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data decoded from a JWT payload."""

    user_id: int | None = None
