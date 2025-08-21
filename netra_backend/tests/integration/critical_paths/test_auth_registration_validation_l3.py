#!/usr/bin/env python3
"""
L3 Integration Test: User Registration and Validation
Tests comprehensive user registration flows including validation, 
duplicate handling, and edge cases.
"""

import asyncio
import json
import pytest
from typing import Dict, Any
import aiohttp
from datetime import datetime
import re

from test_framework.test_patterns import L3IntegrationTest
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.db.models_postgres import User
from netra_backend.app.core.redis_client import RedisManager

# Add project root to path


class TestAuthRegistrationValidation(L3IntegrationTest):
    """Test user registration and validation from multiple angles."""
    
    async def test_successful_registration_flow(self):
        """Test complete successful registration flow."""
        async with aiohttp.ClientSession() as session:
            register_data = {
                "email": "newuser@test.com",
                "password": "SecurePass123!",
                "name": "New User",
                "company": "Test Corp"
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 201
                data = await resp.json()
                
                # Verify response structure
                assert "user" in data
                assert "access_token" in data
                assert "refresh_token" in data
                
                # Verify user data
                user = data["user"]
                assert user["email"] == register_data["email"].lower()
                assert user["name"] == register_data["name"]
                assert "id" in user
                assert "created_at" in user
                
    async def test_registration_email_validation(self):
        """Test email validation during registration."""
        async with aiohttp.ClientSession() as session:
            # Test invalid email formats
            invalid_emails = [
                "notanemail",
                "@test.com",
                "user@",
                "user@.com",
                "user..test@example.com",
                "user@example..com"
            ]
            
            for email in invalid_emails:
                register_data = {
                    "email": email,
                    "password": "SecurePass123!",
                    "name": "Test User"
                }
                
                async with session.post(
                    f"{self.auth_service_url}/auth/register",
                    json=register_data
                ) as resp:
                    assert resp.status == 400
                    data = await resp.json()
                    assert "Invalid email format" in data.get("error", "")
                    
    async def test_registration_password_requirements(self):
        """Test password strength requirements."""
        async with aiohttp.ClientSession() as session:
            # Test weak passwords
            weak_passwords = [
                "short",  # Too short
                "nouppercase123!",  # No uppercase
                "NOLOWERCASE123!",  # No lowercase
                "NoNumbers!",  # No numbers
                "NoSpecialChar123",  # No special characters
                "        ",  # Just spaces
            ]
            
            for i, password in enumerate(weak_passwords):
                register_data = {
                    "email": f"weak{i}@test.com",
                    "password": password,
                    "name": "Test User"
                }
                
                async with session.post(
                    f"{self.auth_service_url}/auth/register",
                    json=register_data
                ) as resp:
                    assert resp.status == 400
                    data = await resp.json()
                    assert "password" in data.get("error", "").lower()
                    
    async def test_registration_duplicate_email(self):
        """Test registration with already existing email."""
        async with aiohttp.ClientSession() as session:
            email = "duplicate@test.com"
            
            # First registration
            register_data = {
                "email": email,
                "password": "SecurePass123!",
                "name": "First User"
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 201
                
            # Second registration with same email
            register_data["name"] = "Second User"
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 409
                data = await resp.json()
                assert "already exists" in data.get("error", "").lower()
                
    async def test_registration_case_insensitive_email(self):
        """Test that email registration is case-insensitive."""
        async with aiohttp.ClientSession() as session:
            # Register with lowercase
            register_data = {
                "email": "casetest@test.com",
                "password": "SecurePass123!",
                "name": "First User"
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 201
                
            # Try to register with uppercase
            register_data = {
                "email": "CASETEST@TEST.COM",
                "password": "SecurePass123!",
                "name": "Second User"
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 409  # Should fail as duplicate
                
    async def test_registration_with_sql_injection_attempts(self):
        """Test that registration is safe from SQL injection."""
        async with aiohttp.ClientSession() as session:
            sql_injection_attempts = [
                "test'; DROP TABLE users; --",
                "test' OR '1'='1",
                "admin'--",
                "test\"; DROP TABLE users; --"
            ]
            
            for i, injection in enumerate(sql_injection_attempts):
                register_data = {
                    "email": f"sql{i}@test.com",
                    "password": "SecurePass123!",
                    "name": injection
                }
                
                async with session.post(
                    f"{self.auth_service_url}/auth/register",
                    json=register_data
                ) as resp:
                    # Should either succeed safely or fail validation
                    assert resp.status in [201, 400]
                    
                    if resp.status == 201:
                        # Verify data was stored safely
                        data = await resp.json()
                        assert data["user"]["name"] == injection
                        
    async def test_registration_field_length_limits(self):
        """Test field length validation during registration."""
        async with aiohttp.ClientSession() as session:
            # Test overly long fields
            register_data = {
                "email": "a" * 250 + "@test.com",  # Very long email
                "password": "SecurePass123!",
                "name": "Test User"
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 400
                data = await resp.json()
                assert "too long" in data.get("error", "").lower()
                
            # Test overly long name
            register_data = {
                "email": "longname@test.com",
                "password": "SecurePass123!",
                "name": "A" * 500  # Very long name
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 400
                
    async def test_registration_creates_user_profile(self):
        """Test that registration creates associated user profile."""
        async with aiohttp.ClientSession() as session:
            register_data = {
                "email": "profile@test.com",
                "password": "SecurePass123!",
                "name": "Profile User",
                "company": "Test Company"
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 201
                data = await resp.json()
                user_id = data["user"]["id"]
                access_token = data["access_token"]
                
            # Fetch user profile
            async with session.get(
                f"{self.backend_url}/api/v1/users/{user_id}/profile",
                headers={"Authorization": f"Bearer {access_token}"}
            ) as resp:
                assert resp.status == 200
                profile = await resp.json()
                
                assert profile["email"] == register_data["email"].lower()
                assert profile["name"] == register_data["name"]
                assert profile["company"] == register_data["company"]
                
    async def test_registration_email_verification_flow(self):
        """Test email verification requirement after registration."""
        async with aiohttp.ClientSession() as session:
            register_data = {
                "email": "verify@test.com",
                "password": "SecurePass123!",
                "name": "Verify User"
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/register",
                json=register_data
            ) as resp:
                assert resp.status == 201
                data = await resp.json()
                
                # Check if verification is required
                user = data["user"]
                assert "email_verified" in user
                assert user["email_verified"] is False
                
                # Check verification email was queued
                redis_manager = RedisManager()
                email_queue_key = "email:queue:verification"
                queue_data = await redis_manager.lpop(email_queue_key)
                
                if queue_data:
                    email_task = json.loads(queue_data)
                    assert email_task["to"] == register_data["email"].lower()
                    assert email_task["type"] == "verification"
                    
    async def test_concurrent_registration_same_email(self):
        """Test concurrent registration attempts with same email."""
        async with aiohttp.ClientSession() as session:
            email = "concurrent@test.com"
            
            # Create multiple registration tasks
            tasks = []
            for i in range(5):
                register_data = {
                    "email": email,
                    "password": "SecurePass123!",
                    "name": f"User {i}"
                }
                
                tasks.append(session.post(
                    f"{self.auth_service_url}/auth/register",
                    json=register_data
                ))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Only one should succeed
            success_count = sum(
                1 for r in responses 
                if not isinstance(r, Exception) and r.status == 201
            )
            assert success_count == 1, "Only one registration should succeed"
            
            # Others should get conflict error
            conflict_count = sum(
                1 for r in responses 
                if not isinstance(r, Exception) and r.status == 409
            )
            assert conflict_count == 4, "Other registrations should conflict"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])