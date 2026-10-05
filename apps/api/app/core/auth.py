import httpx
import jwt
from app.core.config import settings
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWKS_URL = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
JWT_ISSUER = f"{settings.supabase_url}/auth/v1"
JWT_ALGORITHMS = ["ES256"]

def get_jwks() -> dict:
    response = httpx.get(JWKS_URL)
    response.raise_for_status()
    return response.json()

def verify_access_token(token: str) -> dict:
    signing_key = jwt.PyJWKClient(JWKS_URL).get_signing_key_from_jwt(token)

    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=JWT_ALGORITHMS,
        issuer=JWT_ISSUER,
        audience="authenticated",
    )
    return payload

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return verify_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )