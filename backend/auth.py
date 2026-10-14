
import os
import httpx
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

# Require credentials to be checked explicitly
security = HTTPBearer(auto_error=False)

CLERK_ISSUER_URL = os.getenv("CLERK_ISSUER_URL", "").rstrip("/")


async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:

    # Reject requests without a Bearer token
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Fail closed if Clerk is not configured
    if not CLERK_ISSUER_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is not configured"
        )

    token = credentials.credentials

    try:
        # Fetch Clerk's public signing keys
        jwks_url = f"{CLERK_ISSUER_URL}/.well-known/jwks.json"

        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=5.0)
            response.raise_for_status()
            jwks = response.json()

        # Read the token header to identify its signing key
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = None

        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        # Reject tokens whose signing key cannot be found
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to verify Clerk token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Verify the signature, algorithm, and issuer
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER_URL,
            options={"verify_aud": False}
        )

        # Ensure the token identifies a user
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        return payload

    except HTTPException:
        raise

    except Exception as e:
        # Avoid returning internal verification details to clients
        print(f"Clerk token verification failed: {type(e).__name__}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Clerk token",
            headers={"WWW-Authenticate": "Bearer"}
        )
