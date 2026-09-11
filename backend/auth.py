import os
import httpx
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()
CLERK_ISSUER_URL = os.getenv("CLERK_ISSUER_URL")

async def verify_clerk_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    token = credentials.credentials
    try:
        jwks_url = f"{CLERK_ISSUER_URL}/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            jwks = response.json()

        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: Key ID not found"
            )

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER_URL,
            options={"verify_aud": False}
        )
        return payload

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )