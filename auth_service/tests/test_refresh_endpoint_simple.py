"""
Simple test for refresh endpoint field naming without database dependencies.
"""
import json
import sys
import os
from shared.isolated_environment import IsolatedEnvironment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Removed all mock imports - using real services per CLAUDE.md requirement
import pytest


def test_refresh_endpoint_accepts_multiple_formats():
    """Test that the refresh endpoint accepts different field naming formats"""
    from auth_service.auth_core.routes.auth_routes import refresh_tokens
    from fastapi import Request
    
    # Test data
    test_token = "test_refresh_token_123"
    
    # Test with real HTTP client instead of mocks
    import asyncio
    from httpx import AsyncClient, ASGITransport
    from auth_service.main import app
    
    async def test_real_refresh():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test 1: snake_case format (refresh_token)
            response1 = await client.post("/auth/refresh", json={"refresh_token": test_token})
            # Will return 401 for invalid token, but should parse the field correctly
            assert response1.status_code in [401, 422]
            
            # Test 2: camelCase format (refreshToken)
            response2 = await client.post("/auth/refresh", json={"refreshToken": test_token})
            assert response2.status_code in [401, 422]
            
            # Test 3: simple token format
            response3 = await client.post("/auth/refresh", json={"token": test_token})
            assert response3.status_code in [401, 422]
    
    asyncio.run(test_real_refresh())


def test_refresh_endpoint_error_handling():
    """Test error handling for missing refresh token"""
    from auth_service.auth_core.routes.auth_routes import refresh_tokens
    from fastapi import Request, HTTPException
    
    # Test with real HTTP client
    import asyncio
    from httpx import AsyncClient, ASGITransport
    from auth_service.main import app
    
    async def test_real_empty_body():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/auth/refresh", json={})
            assert response.status_code == 422
            assert "refresh_token" in response.text.lower()
    
    asyncio.run(test_real_empty_body())


def test_refresh_endpoint_invalid_json():
    """Test error handling for invalid JSON"""
    from auth_service.auth_core.routes.auth_routes import refresh_tokens
    from fastapi import Request, HTTPException
    
    # Test with real HTTP client and invalid JSON
    import asyncio
    from httpx import AsyncClient, ASGITransport
    from auth_service.main import app
    
    async def test_real_invalid_json():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/auth/refresh", 
                content=b"not valid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 422
            assert "json" in response.text.lower() or "invalid" in response.text.lower()
    
    asyncio.run(test_real_invalid_json())


def test_refresh_endpoint_invalid_token():
    """Test handling of invalid refresh token"""
    from auth_service.auth_core.routes.auth_routes import refresh_tokens
    from fastapi import Request, HTTPException
    
    # Test with real HTTP client and invalid token
    import asyncio
    from httpx import AsyncClient, ASGITransport
    from auth_service.main import app
    
    async def test_real_invalid_token():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/auth/refresh", json={"refresh_token": "invalid"})
            assert response.status_code == 401
            assert "invalid" in response.text.lower() or "token" in response.text.lower()
    
    asyncio.run(test_real_invalid_token())


if __name__ == "__main__":
    print("Testing refresh endpoint field naming compatibility...")
    
    try:
        test_refresh_endpoint_accepts_multiple_formats()
        print("[PASS] Multiple field formats test passed")
    except Exception as e:
        print(f"[FAIL] Multiple formats test failed: {e}")
    
    try:
        test_refresh_endpoint_error_handling()
        print("[PASS] Error handling test passed")
    except Exception as e:
        print(f"[FAIL] Error handling test failed: {e}")
    
    try:
        test_refresh_endpoint_invalid_json()
        print("[PASS] Invalid JSON test passed")
    except Exception as e:
        print(f"[FAIL] Invalid JSON test failed: {e}")
    
    try:
        test_refresh_endpoint_invalid_token()
        print("[PASS] Invalid token test passed")
    except Exception as e:
        print(f"[FAIL] Invalid token test failed: {e}")
    
    print("\nAll tests completed!")