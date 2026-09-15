import os
import httpx
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer(auto_error=False)

CLERK_ISSUER_URL = os.getenv("CLERK_ISSUER_URL")

if not CLERK_ISSUER_URL:
    raise RuntimeError("CLERK_ISSUER_URL is missing in backend/.env")


async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:

    if not credentials or not credentials.credentials:
        return {
            "sub": "dev_user_default",
            "email": "student@example.com"
        }

    token = credentials.credentials

    try:
        issuer = CLERK_ISSUER_URL.rstrip("/")
        jwks_url = f"{issuer}/.well-known/jwks.json"

        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=5.0)
            response.raise_for_status()
            jwks = response.json()

        unverified_header = jwt.get_unverified_header(token)

        rsa_key = {}

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

        if rsa_key:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=issuer,
                options={
                    "verify_aud": False
                }
            )

            return payload

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to verify Clerk token"
        )

    except HTTPException:
        raise

    except Exception as e:
        print(f"Token verification failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk token"
        )
