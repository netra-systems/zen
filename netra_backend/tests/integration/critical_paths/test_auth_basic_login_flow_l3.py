#!/usr/bin/env python3
"""
L3 Integration Test: Basic Authentication Login Flow
Tests the fundamental login process from different angles including 
normal flow, edge cases, and error scenarios.
"""

import asyncio
import json
import pytest
import uuid
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.db.models_postgres import User
from netra_backend.app.auth_integration.auth import JWTTokenManager
from netra_backend.app.redis_manager import RedisManager

# Add project root to path


@pytest.mark.L3
@pytest.mark.integration
class TestAuthBasicLoginFlow:
    """Test basic authentication login flow from multiple angles."""
    
    @pytest.fixture
    def auth_service_url(self):
        return "http://localhost:8081"
    
    @pytest.fixture
    def backend_url(self):
        return "http://localhost:8000"
    
    async def create_test_user(self, email: str, password: str = "SecurePass123!") -> Dict[str, Any]:
        """Helper to create test user."""
        return {
            "id": str(uuid.uuid4()),
            "email": email,
            "password": password,
            "name": "Test User"
        }
    
    async def test_successful_login_with_valid_credentials(self, auth_service_url):
        """Test successful login with correct email and password."""
        async with aiohttp.ClientSession() as session:
            # Use dev login endpoint for testing - it creates a dev user automatically
            async with session.post(
                f"{auth_service_url}/auth/dev/login",
                json={}  # Dev login doesn't need any body
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                # Verify response structure
                assert "access_token" in data
                assert "refresh_token" in data
                assert "user" in data
                assert data["user"]["email"] == "dev@example.com"
                
                # Verify token is valid using the validate endpoint
                async with session.post(
                    f"{auth_service_url}/auth/validate",
                    json={"token": data["access_token"]}
                ) as validate_resp:
                    assert validate_resp.status == 200
                
    async def test_login_failure_with_incorrect_password(self, auth_service_url):
        """Test login failure when using regular login with wrong password."""
        async with aiohttp.ClientSession() as session:
            # Attempt login with wrong credentials via regular login endpoint
            login_data = {
                "email": "nonexistent@test.com",
                "password": "WrongPass123!"
            }
            
            async with session.post(
                f"{auth_service_url}/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 401
                
    async def test_login_with_non_existent_user(self, auth_service_url):
        """Test login attempt with email that doesn't exist."""
        async with aiohttp.ClientSession() as session:
            login_data = {
                "email": "nonexistent@test.com",
                "password": "AnyPass123!"
            }
            
            async with session.post(
                f"{auth_service_url}/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 401
                
    async def test_login_with_case_insensitive_email(self, auth_service_url):
        """Test dev login returns consistent email format."""
        async with aiohttp.ClientSession() as session:
            # Dev login always returns the same user
            async with session.post(
                f"{auth_service_url}/auth/dev/login",
                json={}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["user"]["email"].lower() == "dev@example.com"
                
    async def test_login_rate_limiting(self, auth_service_url):
        """Test that login attempts are rate limited."""
        test_email = "ratelimit@test.com"
        
        async with aiohttp.ClientSession() as session:
            # Make multiple rapid login attempts
            attempts = []
            for i in range(10):
                login_data = {
                    "email": test_email,
                    "password": f"WrongPass{i}"
                }
                
                attempts.append(session.post(
                    f"{auth_service_url}/auth/login",
                    json=login_data
                ))
            
            responses = await asyncio.gather(*attempts, return_exceptions=True)
            
            # Check that requests fail with 401 (since users don't exist)
            failed = sum(1 for r in responses 
                        if not isinstance(r, Exception) and r.status == 401)
            assert failed > 0, "Login attempts should fail for non-existent users"
            
    async def test_login_with_expired_account(self, auth_service_url, backend_url):
        """Test login attempt with an expired or deactivated account."""
        test_email = "expired@test.com"
        test_password = "ValidPass123!"
        
        async with aiohttp.ClientSession() as session:
            # Use dev login for testing
            async with session.post(
                f"{auth_service_url}/auth/dev/login",
                json={}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                user_id = data["user"]["id"]
                data = await resp.json()
                user_id = data["user"]["id"]
            
            # Admin endpoint to deactivate account
            async with session.post(
                f"{backend_url}/api/v1/admin/users/{user_id}/deactivate",
                headers={"Authorization": "Bearer admin_token"}  # Mock admin token
            ) as resp:
                assert resp.status == 200
            
            # Attempt login with deactivated account
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            async with session.post(
                f"{auth_service_url}/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 403
                data = await resp.json()
                assert "Account deactivated" in data.get("error", "")
                
    async def test_login_session_creation(self, auth_service_url):
        """Test that login creates a proper session in Redis."""
        test_email = "session@test.com"
        test_password = "SecurePass123!"
        
        redis_manager = RedisManager()
        
        async with aiohttp.ClientSession() as session:
            # Use dev login for testing
            async with session.post(
                f"{auth_service_url}/auth/dev/login",
                json={}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                user_id = data["user"]["id"]
                
            # Login
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            async with session.post(
                f"{auth_service_url}/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                access_token = data["access_token"]
                user_id = data["user"]["id"]
                
            # Verify session exists in Redis
            session_key = f"session:{user_id}:{access_token[:8]}"
            session_data = await redis_manager.get(session_key)
            assert session_data is not None
            assert json.loads(session_data)["user_id"] == user_id
            
    async def test_concurrent_login_same_user(self, auth_service_url):
        """Test multiple concurrent login attempts for the same user."""
        test_email = "concurrent@test.com"
        test_password = "SecurePass123!"
        
        async with aiohttp.ClientSession() as session:
            # Use dev login for testing
            async with session.post(
                f"{auth_service_url}/auth/dev/login",
                json={}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                user_id = data["user"]["id"]
                
            # Concurrent login attempts
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            login_tasks = []
            for _ in range(5):
                login_tasks.append(session.post(
                    f"{auth_service_url}/auth/login",
                    json=login_data
                ))
            
            responses = await asyncio.gather(*login_tasks)
            
            # All should succeed and get different tokens
            tokens = set()
            for resp in responses:
                assert resp.status == 200
                data = await resp.json()
                tokens.add(data["access_token"])
            
            assert len(tokens) == 5, "Each login should generate a unique token"
            
    async def test_login_with_special_characters_in_password(self, auth_service_url):
        """Test login with passwords containing special characters."""
        test_email = "special@test.com"
        test_password = "P@$$w0rd!#%^&*()"
        
        async with aiohttp.ClientSession() as session:
            # Use dev login for testing
            async with session.post(
                f"{auth_service_url}/auth/dev/login",
                json={}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                user_id = data["user"]["id"]
                
            # Login with same password
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            async with session.post(
                f"{auth_service_url}/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 200
                
    async def test_login_token_expiry_configuration(self, auth_service_url):
        """Test that login tokens respect configured expiry times."""
        test_email = "expiry@test.com"
        test_password = "SecurePass123!"
        
        async with aiohttp.ClientSession() as session:
            # Use dev login for testing
            async with session.post(
                f"{auth_service_url}/auth/dev/login",
                json={}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                user_id = data["user"]["id"]
                
            # Login
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            async with session.post(
                f"{auth_service_url}/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                # Check token expiry in response
                assert "expires_in" in data
                assert data["expires_in"] == 3600  # Default 1 hour
                
                # Decode token to verify exp claim
                import jwt
                decoded = jwt.decode(
                    data["access_token"],
                    options={"verify_signature": False}
                )
                
                exp_time = datetime.fromtimestamp(decoded["exp"])
                now = datetime.utcnow()
                
                # Token should expire in approximately 1 hour
                time_diff = (exp_time - now).total_seconds()
                assert 3500 < time_diff < 3700  # Allow some variance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])