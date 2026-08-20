import logging
import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from backend.config import settings

logger = logging.getLogger(__name__)

# Try to get Auth0 config from settings, fallback to env
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", getattr(settings, "AUTH0_DOMAIN", ""))
API_AUDIENCE = os.getenv(
    "AUTH0_API_AUDIENCE",
    getattr(settings, "AUTH0_API_AUDIENCE", ""),
)
ALGORITHMS = ["RS256"]

token_auth_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
):
    """
    Validates the Auth0 JWT token using PyJWT.
    """
    token = credentials.credentials
    try:
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
            leeway=60,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token is expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid issuer")
    except Exception as e:
        logger.error(f"Auth0 Validation Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


def require_role(allowed_roles: list):
    """
    Dependency to require specific roles.
    Assumes roles are added to the token under a custom namespace or 'permissions' claim.
    """

    def role_checker(user: dict = Depends(get_current_user)):
        # Check standard permissions
        permissions = user.get("permissions", [])

        # Check custom namespace roles (e.g. from an Auth0 Action)
        roles = user.get("roles", [])
        if not roles:
            roles = user.get("https://stateful-agent.com/roles", [])
        if not roles:
            roles = user.get("https://ai.code.agent/roles", [])
        if not roles:
            roles = user.get(
                "http://schemas.microsoft.com/ws/2008/06/identity/claims/role", []
            )

        user_roles = [r.lower() for r in (permissions + roles)]

        # Allow 'admin' to access anything requested by 'admin', 'manager', etc.
        # Actually, user role mapping:
        # User wants "admin is for manager and user is for developer"
        # So "admin" = manager, "user" = developer

        if not any(role.lower() in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required roles. Required one of: {allowed_roles}",
            )
        return user

    return role_checker
