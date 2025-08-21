#!/usr/bin/env python3
"""
L3 Integration Test: Password Reset Flow
Tests complete password reset flow including request, validation, and completion.
"""

import asyncio
import json
import pytest
from typing import Dict, Any
import aiohttp
from datetime import datetime, timedelta
import uuid
import hashlib

from test_framework.test_patterns import L3IntegrationTest
from app.core.redis_client import RedisManager
from app.core.auth import TokenManager


class TestAuthPasswordResetFlow(L3IntegrationTest):
    """Test password reset flow from multiple angles."""
    
    async def test_password_reset_request(self):
        """Test requesting a password reset."""
        user_data = await self.create_test_user("reset1@test.com")
        
        async with aiohttp.ClientSession() as session:
            # Request password reset
            reset_data = {"email": user_data["email"]}
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/password-reset/request",
                json=reset_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["message"] == "Password reset email sent"
                
            # Verify reset token in Redis
            redis_manager = RedisManager()
            reset_key = f"password_reset:{user_data['email']}:*"
            reset_tokens = await redis_manager.scan_keys(reset_key)
            assert len(reset_tokens) > 0
            
    async def test_password_reset_with_invalid_email(self):
        """Test password reset with non-existent email."""
        async with aiohttp.ClientSession() as session:
            reset_data = {"email": "nonexistent@test.com"}
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/password-reset/request",
                json=reset_data
            ) as resp:
                # Should still return 200 to prevent email enumeration
                assert resp.status == 200
                data = await resp.json()
                assert "sent" in data["message"].lower()
                
    async def test_password_reset_token_validation(self):
        """Test password reset token validation."""
        user_data = await self.create_test_user("reset2@test.com")
        
        # Generate reset token
        reset_token = str(uuid.uuid4())
        redis_manager = RedisManager()
        
        # Store reset token
        reset_key = f"password_reset:{user_data['email']}:{reset_token}"
        await redis_manager.set(reset_key, user_data["id"], ex=3600)
        
        async with aiohttp.ClientSession() as session:
            # Validate token
            validate_data = {
                "email": user_data["email"],
                "token": reset_token
            }
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/password-reset/validate",
                json=validate_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["valid"] is True
                
    async def test_password_reset_completion(self):
        """Test completing password reset with new password."""
        user_data = await self.create_test_user("reset3@test.com")
        
        # Generate and store reset token
        reset_token = str(uuid.uuid4())
        redis_manager = RedisManager()
        reset_key = f"password_reset:{user_data['email']}:{reset_token}"
        await redis_manager.set(reset_key, user_data["id"], ex=3600)
        
        async with aiohttp.ClientSession() as session:
            # Complete password reset
            new_password = "NewSecurePass123!"
            reset_complete_data = {
                "email": user_data["email"],
                "token": reset_token,
                "new_password": new_password
            }
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/password-reset/complete",
                json=reset_complete_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["message"] == "Password reset successful"
            
            # Verify old password doesn't work
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 401
            
            # Verify new password works
            login_data["password"] = new_password
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 200
                
    async def test_password_reset_token_expiry(self):
        """Test that password reset tokens expire."""
        user_data = await self.create_test_user("reset4@test.com")
        
        # Generate expired token
        reset_token = str(uuid.uuid4())
        redis_manager = RedisManager()
        reset_key = f"password_reset:{user_data['email']}:{reset_token}"
        
        # Set with 1 second expiry
        await redis_manager.set(reset_key, user_data["id"], ex=1)
        await asyncio.sleep(2)
        
        async with aiohttp.ClientSession() as session:
            # Try to use expired token
            reset_complete_data = {
                "email": user_data["email"],
                "token": reset_token,
                "new_password": "NewPass123!"
            }
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/password-reset/complete",
                json=reset_complete_data
            ) as resp:
                assert resp.status == 400
                data = await resp.json()
                assert "expired" in data["error"].lower()
                
    async def test_password_reset_rate_limiting(self):
        """Test rate limiting on password reset requests."""
        email = "ratelimit_reset@test.com"
        
        async with aiohttp.ClientSession() as session:
            # Make multiple reset requests
            tasks = []
            for _ in range(10):
                reset_data = {"email": email}
                tasks.append(session.post(
                    f"{self.auth_service_url}/api/v1/auth/password-reset/request",
                    json=reset_data
                ))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for rate limiting
            rate_limited = sum(
                1 for r in responses 
                if not isinstance(r, Exception) and r.status == 429
            )
            assert rate_limited > 0
            
    async def test_password_reset_invalidates_sessions(self):
        """Test that password reset invalidates all existing sessions."""
        user_data = await self.create_test_user("reset5@test.com")
        
        # Login to create sessions
        tokens = []
        async with aiohttp.ClientSession() as session:
            for _ in range(3):
                login_data = {
                    "email": user_data["email"],
                    "password": user_data["password"]
                }
                
                async with session.post(
                    f"{self.auth_service_url}/api/v1/auth/login",
                    json=login_data
                ) as resp:
                    assert resp.status == 200
                    data = await resp.json()
                    tokens.append(data["access_token"])
            
            # Reset password
            reset_token = str(uuid.uuid4())
            redis_manager = RedisManager()
            reset_key = f"password_reset:{user_data['email']}:{reset_token}"
            await redis_manager.set(reset_key, user_data["id"], ex=3600)
            
            reset_complete_data = {
                "email": user_data["email"],
                "token": reset_token,
                "new_password": "NewSecurePass123!"
            }
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/password-reset/complete",
                json=reset_complete_data
            ) as resp:
                assert resp.status == 200
            
            # Verify all old tokens are invalid
            for token in tokens:
                async with session.get(
                    f"{self.backend_url}/api/v1/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 401
                    
    async def test_password_reset_single_use_token(self):
        """Test that reset tokens can only be used once."""
        user_data = await self.create_test_user("reset6@test.com")
        
        # Generate reset token
        reset_token = str(uuid.uuid4())
        redis_manager = RedisManager()
        reset_key = f"password_reset:{user_data['email']}:{reset_token}"
        await redis_manager.set(reset_key, user_data["id"], ex=3600)
        
        async with aiohttp.ClientSession() as session:
            # First use - should succeed
            reset_complete_data = {
                "email": user_data["email"],
                "token": reset_token,
                "new_password": "FirstNewPass123!"
            }
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/password-reset/complete",
                json=reset_complete_data
            ) as resp:
                assert resp.status == 200
            
            # Second use - should fail
            reset_complete_data["new_password"] = "SecondNewPass123!"
            
            async with session.post(
                f"{self.auth_service_url}/api/v1/auth/password-reset/complete",
                json=reset_complete_data
            ) as resp:
                assert resp.status == 400
                data = await resp.json()
                assert "invalid" in data["error"].lower()
                
    async def test_password_reset_complexity_requirements(self):
        """Test password complexity requirements during reset."""
        user_data = await self.create_test_user("reset7@test.com")
        
        # Generate reset token
        reset_token = str(uuid.uuid4())
        redis_manager = RedisManager()
        reset_key = f"password_reset:{user_data['email']}:{reset_token}"
        await redis_manager.set(reset_key, user_data["id"], ex=3600)
        
        async with aiohttp.ClientSession() as session:
            # Try weak passwords
            weak_passwords = [
                "short",
                "nouppercase123!",
                "NOLOWERCASE123!",
                "NoNumbers!",
                "NoSpecialChar123"
            ]
            
            for password in weak_passwords:
                reset_complete_data = {
                    "email": user_data["email"],
                    "token": reset_token,
                    "new_password": password
                }
                
                async with session.post(
                    f"{self.auth_service_url}/api/v1/auth/password-reset/complete",
                    json=reset_complete_data
                ) as resp:
                    assert resp.status == 400
                    data = await resp.json()
                    assert "password" in data["error"].lower()
                    
    async def test_concurrent_password_reset_requests(self):
        """Test concurrent password reset requests for same user."""
        user_data = await self.create_test_user("reset8@test.com")
        
        async with aiohttp.ClientSession() as session:
            # Make concurrent reset requests
            tasks = []
            for _ in range(5):
                reset_data = {"email": user_data["email"]}
                tasks.append(session.post(
                    f"{self.auth_service_url}/api/v1/auth/password-reset/request",
                    json=reset_data
                ))
            
            responses = await asyncio.gather(*tasks)
            
            # All should succeed or rate limit
            for resp in responses:
                assert resp.status in [200, 429]
            
            # Only one token should be valid
            redis_manager = RedisManager()
            reset_pattern = f"password_reset:{user_data['email']}:*"
            reset_tokens = await redis_manager.scan_keys(reset_pattern)
            
            # Should have at most recent token(s)
            assert len(reset_tokens) <= 2  # Allow for race condition


if __name__ == "__main__":
    pytest.main([__file__, "-v"])