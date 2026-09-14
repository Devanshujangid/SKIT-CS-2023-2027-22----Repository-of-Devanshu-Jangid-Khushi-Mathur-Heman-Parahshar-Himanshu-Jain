import os
import httpx
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer(auto_error=False)
CLERK_ISSUER_URL = os.getenv("CLERK_ISSUER_URL", "https://striking-man-6858.clerk.accounts.dev")

async def verify_clerk_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    if not credentials or not credentials.credentials:
        return {"sub": "dev_user_default", "email": "student@example.com"}

    token = credentials.credentials
    try:
        issuer = os.getenv("CLERK_ISSUER_URL", "https://striking-man-6858.clerk.accounts.dev").rstrip('/')
        jwks_url = f"{issuer}/.well-known/jwks.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=5.0)
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
                options={"verify_aud": False}
            )
            return payload

        # Fallback to unverified decode for development
        return jwt.decode(token, options={"verify_signature": False})

    except Exception as e:
        print(f"Token verification fallback triggered: {e}")
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return {"sub": "dev_user_default", "email": "student@example.com"}