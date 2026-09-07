"""
Shared FastAPI dependencies for authentication and tenant context.

CRITICAL RULE (see SECURITY.md / system spec section 10):
Tenant context is derived ONLY from the verified JWT, never from a
path parameter, query parameter, or request body supplied by the client.
Every module's router/service must use TenantContext.tenant_id as the
sole source of tenant scoping for database queries.
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import TokenPayloadError, decode_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TenantContext:
    user_id: UUID
    tenant_id: UUID
    role: str


def get_current_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TenantContext:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Missing bearer token"}},
        )

    try:
        payload = decode_token(credentials.credentials)
    except TokenPayloadError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Token is invalid or expired"}},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN_TYPE", "message": "Access token required"}},
        )

    try:
        return TenantContext(
            user_id=UUID(payload["sub"]),
            tenant_id=UUID(payload["tenant_id"]),
            role=payload["role"],
        )
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "MALFORMED_TOKEN", "message": "Token claims are malformed"}},
        )


def require_roles(*allowed_roles: str):
    """
    Dependency factory for RBAC checks at the router level.

    Usage:
        @router.post(..., dependencies=[Depends(require_roles("OWNER", "ADMIN"))])
    """

    def _check(ctx: TenantContext = Depends(get_current_context)) -> TenantContext:
        if ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Role '{ctx.role}' is not permitted to perform this action",
                    }
                },
            )
        return ctx

    return _check
