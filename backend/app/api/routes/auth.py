"""Authentication API routes.

Endpoints
---------
POST   /api/v1/auth/register   — register a new user account
POST   /api/v1/auth/login      — authenticate and receive a JWT
GET    /api/v1/auth/me         — return the authenticated user's profile
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account.

    Checks that both the email address and the username are not already taken
    before persisting the new user.  The password is stored as a bcrypt hash
    — the plain-text value is never written to the database.

    Raises:
        HTTPException: 409 when the email or username already exists.
    """
    # Check for duplicate email or username in a single round-trip.
    result = await db.execute(
        select(User).where(
            or_(User.email == user_in.email, User.username == user_in.username)
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        if existing.email == user_in.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "Email is already registered.", "code": "EMAIL_TAKEN"},
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Username is already taken.", "code": "USERNAME_TAKEN"},
        )

    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("New user registered: id=%s username=%s", user.id, user.username)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    The ``username`` field accepts either the account username or email
    address so callers only need one field.

    Raises:
        HTTPException: 401 when the credentials are incorrect.
    """
    # Accept email or username in the ``username`` field.
    result = await db.execute(
        select(User).where(
            or_(User.username == user_in.username, User.email == user_in.username)
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Incorrect username or password.", "code": "INVALID_CREDENTIALS"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "User account is inactive.", "code": "INACTIVE_USER"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info("User authenticated: id=%s username=%s", user.id, user.username)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)
