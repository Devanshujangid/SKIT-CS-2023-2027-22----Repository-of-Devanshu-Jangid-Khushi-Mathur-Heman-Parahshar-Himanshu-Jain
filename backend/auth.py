import asyncio
import logging
import os
import time

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

CLERK_ISSUER_URL = os.getenv("CLERK_ISSUER_URL", "").rstrip("/")
logger.info("Clerk issuer configured: %s", bool(CLERK_ISSUER_URL))
JWKS_TTL_SECONDS = 3600
JWKS_TIMEOUT_SECONDS = 5.0

_jwks_cache: dict | None = None
_jwks_expires_at = 0.0
_jwks_lock = asyncio.Lock()


async def get_clerk_jwks(force_refresh: bool = False) -> dict:
    """Fetch Clerk's JWKS only when the cache expires or a refresh is needed."""
    global _jwks_cache, _jwks_expires_at

    if not CLERK_ISSUER_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is not configured",
        )

    async with _jwks_lock:
        cache_valid = (
            _jwks_cache is not None
            and time.monotonic() < _jwks_expires_at
        )

        if cache_valid and not force_refresh:
            return _jwks_cache

        jwks_url = f"{CLERK_ISSUER_URL}/.well-known/jwks.json"

        try:
            async with httpx.AsyncClient(
                timeout=JWKS_TIMEOUT_SECONDS
            ) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                jwks = response.json()

            if not isinstance(jwks.get("keys"), list):
                raise ValueError("Invalid JWKS response")

            _jwks_cache = jwks
            _jwks_expires_at = time.monotonic() + JWKS_TTL_SECONDS
            return jwks

        except (httpx.HTTPError, ValueError) as exc:
            logger.exception("Failed to fetch Clerk JWKS")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable",
            ) from exc


async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> dict:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not CLERK_ISSUER_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is not configured",
        )

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        if not kid or header.get("alg") != "RS256":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Clerk token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jwks = await get_clerk_jwks()

        key_data = next(
            (key for key in jwks["keys"] if key.get("kid") == kid),
            None,
        )

        # Refresh once if Clerk has rotated the signing key.
        if key_data is None:
            jwks = await get_clerk_jwks(force_refresh=True)
            key_data = next(
                (key for key in jwks["keys"] if key.get("kid") == kid),
                None,
            )

        if key_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to verify Clerk token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        public_key = jwt.PyJWK.from_dict(key_data).key

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER_URL,
            options={"verify_aud": False},
        )

        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        return payload

    except HTTPException:
        raise

    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        logger.warning(
            "Clerk token verification failed: %s",
            type(exc).__name__,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Clerk token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc