"""FastAPI dependency providers for services and infrastructure.

All service singletons are instantiated once at module load time so they
share their internal state (e.g. HTTP connection pools) across requests.
The ``get_*`` functions are intended to be used with ``Depends()`` in route
handlers.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheManager
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenData
from app.services.alert_evaluator import AlertEvaluator
from app.services.backtester import Backtester
from app.services.data_fetcher import StockDataFetcher
from app.services.screener import StockScreener
from app.services.stock_scorer import StockScorer
from app.services.technical_analysis import TechnicalAnalyzer
from app.services.valuation import ValuationAnalyzer

# ---------------------------------------------------------------------------
# Singleton service instances (created once, reused across requests)
# ---------------------------------------------------------------------------

_cache = CacheManager(settings.redis_url)
_fetcher = StockDataFetcher()
_analyzer = TechnicalAnalyzer()


# ---------------------------------------------------------------------------
# Dependency provider functions
# ---------------------------------------------------------------------------


def get_cache() -> CacheManager:
    """Return the shared CacheManager instance."""
    return _cache


def get_fetcher() -> StockDataFetcher:
    """Return the shared StockDataFetcher instance."""
    return _fetcher


def get_analyzer() -> TechnicalAnalyzer:
    """Return the shared TechnicalAnalyzer instance."""
    return _analyzer


def get_screener() -> StockScreener:
    """Return a StockScreener wired to the shared analyzer and fetcher."""
    return StockScreener(_analyzer, _fetcher)


def get_backtester() -> Backtester:
    """Return a Backtester wired to the shared analyzer and fetcher."""
    return Backtester(_analyzer, _fetcher)


def get_valuation() -> ValuationAnalyzer:
    """Return a ValuationAnalyzer wired to the shared fetcher."""
    return ValuationAnalyzer(_fetcher)


def get_alert_evaluator() -> AlertEvaluator:
    """Return an AlertEvaluator wired to the shared analyzer and fetcher."""
    return AlertEvaluator(_fetcher, _analyzer)


def get_scorer() -> StockScorer:
    """Return a StockScorer instance."""
    return StockScorer()


# ---------------------------------------------------------------------------
# OAuth2 scheme — expects a Bearer token in the Authorization header
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"detail": "Could not validate credentials.", "code": "INVALID_TOKEN"},
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the JWT and return the corresponding User from the database.

    Raises:
        HTTPException: 401 when the token is missing, expired, or malformed,
            and when the embedded user no longer exists.
    """
    payload = decode_access_token(token)
    if payload is None:
        raise _credentials_exception

    raw_sub = payload.get("sub")
    try:
        token_data = TokenData(user_id=int(raw_sub) if raw_sub is not None else None)
    except (ValueError, TypeError):
        raise _credentials_exception
    if token_data.user_id is None:
        raise _credentials_exception

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise _credentials_exception

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Verify the resolved user account is active.

    Raises:
        HTTPException: 403 when the account has been deactivated.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "User account is inactive.", "code": "INACTIVE_USER"},
        )
    return user
