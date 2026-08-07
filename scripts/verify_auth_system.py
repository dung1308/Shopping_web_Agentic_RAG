"""
scripts/verify_auth_system.py — Lightweight diagnostic test script to verify JWT authentication and RBAC role authorization.
"""

import sys
import os
import asyncio
import httpx
from fastapi import FastAPI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api.routers import auth, admin
from backend.db.session import init_db

# Create isolated test app
test_app = FastAPI(title="Auth Test App")
test_app.include_router(auth.router, prefix="/api/auth")
test_app.include_router(admin.router, prefix="/api/admin")

async def run_auth_verification():
    print("\n========================================================================")
    print(" 🔐 MALL AGENTIC RAG — AUTHENTICATION & RBAC ROLE VERIFICATION")
    print("========================================================================\n")

    try:
        await init_db()
    except Exception as e:
        print(f"⚠️ Note: DB init skipped ({e})")

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # 1. Signup test (New Shopper)
        print("1️⃣ Testing Account Signup (POST /api/auth/signup)...")
        signup_resp = await client.post(
            "/api/auth/signup",
            json={
                "email": "newuser_test@example.com",
                "password": "Password123!",
                "full_name": "Test Shopper User",
                "role": "shopper",
            },
        )
        print(f"   Status: {signup_resp.status_code}")
        if signup_resp.status_code == 200:
            token = signup_resp.json()["access_token"]
            print(f"   ✅ Signup successful! JWT token generated: {token[:20]}...")
        else:
            print(f"   ℹ️ Note: {signup_resp.json().get('detail')}")

        # 2. Login test for Demo Admin
        print("\n2️⃣ Testing Demo Admin Login (POST /api/auth/login)...")
        login_admin = await client.post(
            "/api/auth/login",
            json={"email": "admin@mallrag.com", "password": "admin123"},
        )
        print(f"   Status: {login_admin.status_code}")
        assert login_admin.status_code == 200
        admin_data = login_admin.json()
        admin_token = admin_data["access_token"]
        print(f"   ✅ Admin Login successful! Role: '{admin_data['user']['role']}'")

        # 3. Login test for Demo Store Manager (Middle Role)
        print("\n3️⃣ Testing Demo Store Manager Login (POST /api/auth/login)...")
        login_mgr = await client.post(
            "/api/auth/login",
            json={"email": "manager@nike.com", "password": "manager123"},
        )
        assert login_mgr.status_code == 200
        mgr_data = login_mgr.json()
        mgr_token = mgr_data["access_token"]
        print(f"   ✅ Store Manager Login successful! Role: '{mgr_data['user']['role']}'")

        # 4. Login test for Demo Data Auditor (Middle Role)
        print("\n4️⃣ Testing Demo Data Auditor Login (POST /api/auth/login)...")
        login_auditor = await client.post(
            "/api/auth/login",
            json={"email": "auditor@mallrag.com", "password": "auditor123"},
        )
        assert login_auditor.status_code == 200
        auditor_data = login_auditor.json()
        auditor_token = auditor_data["access_token"]
        print(f"   ✅ Data Auditor Login successful! Role: '{auditor_data['user']['role']}'")

        # 5. Login test for Demo Shopper / Guest
        print("\n5️⃣ Testing Demo Shopper Login (POST /api/auth/login)...")
        login_shopper = await client.post(
            "/api/auth/login",
            json={"email": "shopper@gmail.com", "password": "shopper123"},
        )
        assert login_shopper.status_code == 200
        shopper_data = login_shopper.json()
        shopper_token = shopper_data["access_token"]
        print(f"   ✅ Shopper Login successful! Role: '{shopper_data['user']['role']}'")

        # 6. Profile test (GET /api/auth/me)
        print("\n6️⃣ Testing Protected Profile Endpoint (GET /api/auth/me)...")
        me_resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        print(f"   Status: {me_resp.status_code}, Body: {me_resp.text}")
        assert me_resp.status_code == 200
        print(f"   ✅ Profile retrieved: {me_resp.json()}")

        # 7. RBAC Permission Enforcements on /api/admin/jobs
        print("\n7️⃣ Testing Role-Based Access Control (RBAC) on Protected Route (/api/admin/jobs)...")
        
        # Test Unauthenticated
        no_token_resp = await client.get("/api/admin/jobs")
        print(f"   • Unauthenticated Access: HTTP {no_token_resp.status_code} (Expected 401)")
        assert no_token_resp.status_code == 401

        # Test Shopper Token (Forbidden)
        shopper_access_resp = await client.get(
            "/api/admin/jobs",
            headers={"Authorization": f"Bearer {shopper_token}"},
        )
        print(f"   • Shopper / Guest Access: HTTP {shopper_access_resp.status_code} (Expected 403 Forbidden)")
        assert shopper_access_resp.status_code == 403

        # Test Store Manager Token (Allowed)
        mgr_access_resp = await client.get(
            "/api/admin/jobs",
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        print(f"   • Store Manager Access: HTTP {mgr_access_resp.status_code} (Expected 200)")
        assert mgr_access_resp.status_code == 200

        # Test Data Auditor Token (Allowed)
        auditor_access_resp = await client.get(
            "/api/admin/jobs",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )
        print(f"   • Data Auditor Access: HTTP {auditor_access_resp.status_code} (Expected 200)")
        assert auditor_access_resp.status_code == 200

        # Test System Admin Token (Allowed)
        admin_access_resp = await client.get(
            "/api/admin/jobs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        print(f"   • System Admin Access: HTTP {admin_access_resp.status_code} (Expected 200)")
        assert admin_access_resp.status_code == 200

    print("\n🎉 ALL AUTHENTICATION & RBAC TESTS PASSED SUCCESSFULLY!\n")

if __name__ == "__main__":
    asyncio.run(run_auth_verification())
