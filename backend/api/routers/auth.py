"""
backend/api/routers/auth.py — Authentication REST API router (Signup, Login, Profile, Demo Seeding).
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import create_access_token, hash_password, verify_password
from backend.auth.rbac import get_current_user
from backend.db.session import get_db
from backend.db.models import User, UserRole

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=6, example="securePassword123")
    full_name: str = Field(..., example="Jane Doe")
    role: UserRole = Field(UserRole.shopper, example=UserRole.shopper)
    store_id: Optional[UUID] = Field(None, description="Optional associated store ID for Store Managers")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="admin@mallrag.com")
    password: str = Field(..., example="admin123")


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    store_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, summary="Register a new user account")
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Create a new user account and return JWT access token."""
    email_clean = body.email.lower().strip()
    
    # Check duplicate email
    stmt = select(User).where(User.email == email_clean)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{email_clean}' already exists.",
        )

    user = User(
        email=email_clean,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role=body.role,
        store_id=body.store_id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    user_profile = UserProfileResponse(
        user_id=str(user.user_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        store_id=str(user.store_id) if user.store_id else None,
    )

    token = create_access_token({
        "sub": user.email,
        "user_id": str(user.user_id),
        "role": user_profile.role,
        "full_name": user.full_name,
    })

    return TokenResponse(access_token=token, user=user_profile)


@router.post("/login", response_model=TokenResponse, summary="Authenticate with email & password")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Validate credentials and return JWT token."""
    email_clean = body.email.lower().strip()
    
    stmt = select(User).where(User.email == email_clean)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    # Fallback check for demo accounts if DB not yet seeded
    if not user:
        demo_accounts = {
            "admin@mallrag.com": ("admin123", "System Admin", UserRole.admin),
            "manager@nike.com": ("manager123", "Nike Store Manager", UserRole.store_manager),
            "auditor@mallrag.com": ("auditor123", "Data Quality Auditor", UserRole.data_auditor),
            "shopper@gmail.com": ("shopper123", "Smart Shopper", UserRole.shopper),
        }
        if email_clean in demo_accounts:
            pwd, name, role = demo_accounts[email_clean]
            if body.password == pwd:
                user_profile = UserProfileResponse(
                    user_id=f"demo-{role.value}",
                    email=email_clean,
                    full_name=name,
                    role=role.value,
                )
                token = create_access_token({
                    "sub": email_clean,
                    "user_id": user_profile.user_id,
                    "role": role.value,
                    "full_name": name,
                })
                return TokenResponse(access_token=token, user=user_profile)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated.",
        )

    user.last_login_at = datetime.utcnow()
    await db.commit()

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    user_profile = UserProfileResponse(
        user_id=str(user.user_id),
        email=user.email,
        full_name=user.full_name,
        role=role_str,
        store_id=str(user.store_id) if user.store_id else None,
    )

    token = create_access_token({
        "sub": user.email,
        "user_id": str(user.user_id),
        "role": role_str,
        "full_name": user.full_name,
    })

    return TokenResponse(access_token=token, user=user_profile)


@router.get("/me", response_model=UserProfileResponse, summary="Get current logged-in user profile")
async def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserProfileResponse:
    """Return user profile from validated JWT token."""
    return UserProfileResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        store_id=current_user.get("store_id"),
    )


@router.post("/logout", summary="Logout current user session")
async def logout(_current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    """Invalidate session."""
    return {"message": "Successfully logged out"}


@router.post("/seed-demo-users", summary="Seed initial demo accounts for Admin, Store Manager, Auditor, and Shopper")
async def seed_demo_users(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Seed demo accounts into database."""
    demos = [
        ("admin@mallrag.com", "admin123", "System Admin", UserRole.admin),
        ("manager@nike.com", "manager123", "Nike Store Manager", UserRole.store_manager),
        ("auditor@mallrag.com", "auditor123", "Data Quality Auditor", UserRole.data_auditor),
        ("shopper@gmail.com", "shopper123", "Smart Shopper", UserRole.shopper),
    ]
    created = []
    for email, pwd, name, role in demos:
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        if not res.scalar_one_or_none():
            u = User(
                email=email,
                password_hash=hash_password(pwd),
                full_name=name,
                role=role,
                is_active=True,
            )
            db.add(u)
            created.append(email)
    
    await db.commit()
    return {"message": "Demo users seeded successfully", "newly_created": created}
