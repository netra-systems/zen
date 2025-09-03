#!/usr/bin/env python3
"""Test script to verify auth endpoints are correctly configured."""

import asyncio
from httpx import AsyncClient, ASGITransport
from netra_backend.app.main import app


async def test_auth_endpoints():
    """Test that auth endpoints return expected status codes."""
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test /auth/login endpoint (compat router)
        response = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        print(f"/auth/login status: {response.status_code}")
        assert response.status_code != 404, "/auth/login returned 404 - endpoint not found!"
        
        # Test /auth/register endpoint (compat router)
        response = await client.post("/auth/register", json={
            "email": "newuser@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        })
        print(f"/auth/register status: {response.status_code}")
        assert response.status_code != 404, "/auth/register returned 404 - endpoint not found!"
        
        # Test /api/v1/auth/login endpoint (main router)
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com", 
            "password": "wrongpassword"
        })
        print(f"/api/v1/auth/login status: {response.status_code}")
        assert response.status_code != 404, "/api/v1/auth/login returned 404 - endpoint not found!"
        
        # Test /api/v1/auth/register endpoint (main router)
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser2@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        })
        print(f"/api/v1/auth/register status: {response.status_code}")
        assert response.status_code != 404, "/api/v1/auth/register returned 404 - endpoint not found!"
        
        # Test WebSocket endpoint exists
        # Note: Can't test WebSocket fully with httpx, just check it's not 404
        response = await client.get("/ws")
        print(f"/ws GET status: {response.status_code}")
        # WebSocket endpoints typically return 400 or 426 for non-WebSocket requests
        assert response.status_code in [400, 426], f"/ws returned unexpected status: {response.status_code}"
        
    print("\n✅ All auth endpoints are correctly configured (no 404 errors)!")


if __name__ == "__main__":
    asyncio.run(test_auth_endpoints())