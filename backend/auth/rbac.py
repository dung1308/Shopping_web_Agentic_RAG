"""
backend/auth/rbac.py — Role-Based Access Control (RBAC) FastAPI dependencies.
"""

from typing import Any, Callable, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import decode_access_token
from backend.db.session import get_db
from backend.db.models import User, UserRole

security_bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Extracts and validates JWT token from Bearer header or Request object.
    Returns authenticated user dict payload.
    """
    token = credentials.credentials if (credentials and credentials.credentials) else None
    if not token:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization") or ""
        if auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
        email = payload.get("sub") or payload.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
        
        # Verify user in DB if available
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        
        if user:
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")
            return {
                "user_id": str(user.user_id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "store_id": str(user.store_id) if user.store_id else None,
            }
        
        # Fallback payload if DB user record not found (for dev/demo tokens)
        return {
            "user_id": payload.get("user_id", "demo-user"),
            "email": email,
            "full_name": payload.get("full_name", email.split("@")[0]),
            "role": payload.get("role", UserRole.shopper.value),
            "store_id": payload.get("store_id"),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict[str, Any]]:
    """Returns authenticated user if token present, or None for guest/unauthenticated user."""
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


def require_roles(*allowed_roles: str) -> Callable:
    """
    Dependency factory to enforce role-based authorization.
    Example: Depends(require_roles("admin", "data_auditor"))
    """
    async def role_checker(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        user_role = current_user.get("role", "").lower()
        allowed_normalized = [r.lower() for r in allowed_roles]
        
        # Admin super-user bypass
        if user_role == UserRole.admin.value or user_role in allowed_normalized:
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Required role in {allowed_roles}. Current role: '{user_role}'.",
        )

    return role_checker
