"""Security utilities for password hashing and JWT token management."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return the bcrypt hash of *password*.

    Args:
        password: Plain-text password to hash.

    Returns:
        Hashed password string suitable for storage.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify *plain* against a previously hashed password.

    Args:
        plain: Plain-text password supplied by the user.
        hashed: Stored bcrypt hash to compare against.

    Returns:
        ``True`` when the password matches, ``False`` otherwise.
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Encode *data* as a signed JWT access token.

    Args:
        data: Payload dictionary to embed in the token.
        expires_delta: Optional lifetime override.  Defaults to
            ``settings.jwt_expire_minutes`` when not provided.

    Returns:
        Signed JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None
        else timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode and verify a JWT access token.

    Args:
        token: JWT string to decode.

    Returns:
        The decoded payload dictionary, or ``None`` when the token is
        invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None
