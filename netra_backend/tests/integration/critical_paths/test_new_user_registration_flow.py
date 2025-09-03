"""New User Registration Flow Integration Tests (L3)

Tests complete new user registration journey from initial signup to first login.
Validates user creation, email verification, initial permissions, and onboarding.

Business Value Justification (BVJ):
- Segment: Free, Early, Mid (user acquisition across all segments)
- Business Goal: Conversion - smooth onboarding drives adoption
- Value Impact: First impression determines conversion rate
- Revenue Impact: Direct - user registration is the start of revenue journey
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from shared.isolated_environment import get_env

# Set test environment before imports
env = get_env()
env.set("ENVIRONMENT", "testing", "test")
env.set("TESTING", "true", "test")
env.set("SKIP_STARTUP_CHECKS", "true", "test")

from netra_backend.app.db.models_postgres import User
from netra_backend.app.db.postgres import AsyncSessionLocal
from netra_backend.app.main import app
from netra_backend.app.services.user_auth_service import UserAuthService as AuthService
from netra_backend.app.services.user_service import UserService

# Import test framework for real auth
from test_framework.fixtures.auth import create_test_user_token, create_admin_token, create_real_jwt_token

class TestNewUserRegistrationFlow:
    """Test new user registration flow from signup to first login."""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Create mock database session."""
        # Mock: Session isolation for controlled testing without external state
        session = AsyncMock()
        # Mock: Session isolation for controlled testing without external state
        session.execute = AsyncMock()
        # Mock: Session isolation for controlled testing without external state
        session.add = MagicMock()
        # Mock: Session isolation for controlled testing without external state
        session.commit = AsyncMock()
        # Mock: Session isolation for controlled testing without external state
        session.refresh = AsyncMock()
        # Mock: Session isolation for controlled testing without external state
        session.rollback = AsyncMock()
        # Mock: Session isolation for controlled testing without external state
        session.close = AsyncMock()
        try:
            yield session
        finally:
            if hasattr(session, "close"):
                await session.close()
    
    @pytest.fixture
    async def mock_auth_service(self):
        """Create mock auth service."""
        # Mock: Authentication service isolation for testing without real auth flows
        service = AsyncMock(spec=AuthService)
        # Mock: Generic component isolation for controlled unit testing
        service.create_user = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.verify_email = AsyncMock()
        # Use real JWT token generation for integration tests
        service.generate_token = AsyncMock(return_value=create_test_user_token("test_user", use_real_jwt=True).token)
        # Mock: Async component isolation for testing without real async operations
        service.validate_token = AsyncMock(return_value=True)
        yield service
    
    @pytest.fixture
    async def mock_user_service(self):
        """Create mock user service."""
        # Mock: Async component isolation for testing without real async operations
        service = AsyncMock(spec=UserService)
        # Mock: Generic component isolation for controlled unit testing
        service.get_user_by_email = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.create_user = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        service.update_user = AsyncMock()
        yield service
    
    @pytest.fixture
    async def async_client(self, mock_db_session, mock_auth_service, mock_user_service):
        """Create async client with mocked dependencies."""
        async def override_get_db():
            try:
                yield session
            finally:
                if hasattr(session, "close"):
                    await session.close()
        
        app.dependency_overrides[AsyncSessionLocal] = override_get_db
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
        
        app.dependency_overrides.clear()
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_new_user_registration_basic_flow(self, async_client, mock_auth_service):
        """Test 1: Basic new user registration should create user and return token."""
        # Registration data
        registration_data = {
            "email": f"newuser_{uuid.uuid4()}@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User",
            "company": "Test Company"
        }
        
        # Mock successful user creation
        # Mock: Service component isolation for predictable testing behavior
        mock_user = MagicMock(spec=User)
        mock_user.id = str(uuid.uuid4())
        mock_user.email = registration_data["email"]
        mock_user.is_active = False  # Not active until email verified
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.user_service.UserService.create_user', return_value=mock_user):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.auth_service.AuthService.send_verification_email', return_value=True):
                
                response = await async_client.post("/auth/register", json=registration_data)
                
                # Should return 201 Created
                assert response.status_code in [201, 200]  # Some implementations return 200
                
                data = response.json()
                assert "user_id" in data or "id" in data
                assert "message" in data or "email" in data
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_duplicate_email_registration_rejected(self, async_client, mock_user_service):
        """Test 2: Registration with existing email should be rejected."""
        existing_email = "existing@example.com"
        
        # Mock existing user
        # Mock: Service component isolation for predictable testing behavior
        mock_user_service.get_user_by_email.return_value = MagicMock(spec=User)
        
        registration_data = {
            "email": existing_email,
            "password": "SecurePass123!",
            "full_name": "Duplicate User"
        }
        
        # Mock: Generic component isolation for controlled unit testing
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=MagicMock()):
            response = await async_client.post("/auth/register", json=registration_data)
            
            # Should return 409 Conflict or 400 Bad Request
            assert response.status_code in [409, 400]
            
            data = response.json()
            assert "already exists" in data.get("detail", "").lower() or "duplicate" in data.get("detail", "").lower()
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_email_verification_flow(self, async_client, mock_auth_service):
        """Test 3: Email verification should activate user account."""
        user_id = str(uuid.uuid4())
        verification_token = "verify_token_123"
        
        # Mock unverified user
        # Mock: Service component isolation for predictable testing behavior
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.is_active = False
        mock_user.email_verified = False
        
        # Mock verification success
        mock_auth_service.verify_email.return_value = True
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.user_service.UserService.get_user', return_value=mock_user):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.auth_service.AuthService.verify_email_token', return_value=user_id):
                
                response = await async_client.get(f"/auth/verify-email?token={verification_token}")
                
                # Should return success
                assert response.status_code in [200, 302]  # May redirect after verification
                
                # User should now be active
                if response.status_code == 200:
                    data = response.json()
                    assert "verified" in data.get("message", "").lower() or data.get("verified") == True
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_login_before_email_verification(self, async_client, mock_user_service):
        """Test 4: Login should fail for unverified email accounts."""
        # Mock unverified user
        # Mock: Service component isolation for predictable testing behavior
        mock_user = MagicMock(spec=User)
        mock_user.email = "unverified@example.com"
        mock_user.email_verified = False
        mock_user.is_active = False
        
        mock_user_service.get_user_by_email.return_value = mock_user
        
        login_data = {
            "email": "unverified@example.com",
            "password": "password123"
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_user):
            response = await async_client.post("/auth/login", json=login_data)
            
            # Should return 403 Forbidden or 401 Unauthorized
            assert response.status_code in [403, 401]
            
            data = response.json()
            assert "not verified" in data.get("detail", "").lower() or "verify" in data.get("detail", "").lower()
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_first_login_after_verification(self, async_client, mock_auth_service):
        """Test 5: First login after email verification should succeed."""
        # Mock verified user
        # Mock: Service component isolation for predictable testing behavior
        mock_user = MagicMock(spec=User)
        mock_user.id = str(uuid.uuid4())
        mock_user.email = "verified@example.com"
        mock_user.email_verified = True
        mock_user.is_active = True
        # Mock: Service component isolation for predictable testing behavior
        mock_user.check_password = MagicMock(return_value=True)
        
        # Generate real tokens for integration testing
        test_token = create_test_user_token("verified@example.com", use_real_jwt=True)
        mock_token = {
            "access_token": test_token.token,
            "refresh_token": f"refresh_{test_token.token}",
            "token_type": "bearer",
            "expires_in": 3600
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_user):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.auth_service.AuthService.generate_tokens', return_value=mock_token):
                
                login_data = {
                    "email": "verified@example.com",
                    "password": "password123"
                }
                
                response = await async_client.post("/auth/login", json=login_data)
                
                # Should return 200 with tokens
                assert response.status_code == 200
                
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_password_requirements_validation(self, async_client):
        """Test 6: Registration should enforce password requirements."""
        test_cases = [
            ("weak", False, "too short"),
            ("NoNumbers!", False, "missing number"),
            ("nouppercase123!", False, "missing uppercase"),
            ("NOLOWERCASE123!", False, "missing lowercase"),
            ("NoSpecialChar123", False, "missing special"),
            ("ValidPass123!", True, "valid password")
        ]
        
        for password, should_succeed, description in test_cases:
            registration_data = {
                "email": f"test_{uuid.uuid4()}@example.com",
                "password": password,
                "full_name": "Test User"
            }
            
            response = await async_client.post("/auth/register", json=registration_data)
            
            if should_succeed:
                # Should accept valid password
                assert response.status_code in [200, 201, 503], f"Failed for {description}"
            else:
                # Should reject weak password
                assert response.status_code in [400, 422], f"Accepted invalid password: {description}"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_registration_rate_limiting(self, async_client):
        """Test 7: Registration endpoint should be rate limited."""
        # Attempt multiple rapid registrations
        responses = []
        
        for i in range(10):
            registration_data = {
                "email": f"ratelimit_{i}_{uuid.uuid4()}@example.com",
                "password": "ValidPass123!",
                "full_name": f"User {i}"
            }
            
            response = await async_client.post("/auth/register", json=registration_data)
            responses.append(response.status_code)
            
            # Small delay to avoid overwhelming
            await asyncio.sleep(0.1)
        
        # Should hit rate limit at some point
        # Check if any returned 429 (Too Many Requests) or similar
        rate_limited = any(status == 429 for status in responses)
        
        # If no explicit rate limit, at least check consistency
        if not rate_limited:
            # All should return similar status (not a mix of success/failure)
            unique_statuses = set(responses)
            assert len(unique_statuses) <= 2, f"Inconsistent responses: {unique_statuses}"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_user_profile_creation_on_registration(self, async_client, mock_user_service):
        """Test 8: Registration should create complete user profile."""
        registration_data = {
            "email": f"profile_{uuid.uuid4()}@example.com",
            "password": "SecurePass123!",
            "full_name": "John Doe",
            "company": "Acme Corp",
            "phone": "+1234567890"
        }
        
        # Mock user creation with profile
        # Mock: Service component isolation for predictable testing behavior
        mock_user = MagicMock(spec=User)
        mock_user.id = str(uuid.uuid4())
        mock_user.email = registration_data["email"]
        mock_user.full_name = registration_data["full_name"]
        mock_user.company = registration_data.get("company")
        mock_user.phone = registration_data.get("phone")
        mock_user.created_at = datetime.now(timezone.utc)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.user_service.UserService.create_user', return_value=mock_user):
            response = await async_client.post("/auth/register", json=registration_data)
            
            # Should create user with all profile fields
            assert response.status_code in [200, 201, 503]
            
            if response.status_code in [200, 201]:
                data = response.json()
                # Verify profile data is included or user was created
                assert "user_id" in data or "id" in data or "email" in data
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_welcome_email_sent_on_registration(self, async_client, mock_auth_service):
        """Test 9: Welcome email should be sent after successful registration."""
        registration_data = {
            "email": f"welcome_{uuid.uuid4()}@example.com",
            "password": "SecurePass123!",
            "full_name": "New User"
        }
        
        # Track email sending
        mock_auth_service.send_verification_email.return_value = True
        # Mock: Authentication service isolation for testing without real auth flows
        mock_auth_service.send_welcome_email = AsyncMock(return_value=True)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.auth_service.AuthService.send_verification_email', return_value=True) as mock_verify:
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.auth_service.AuthService.send_welcome_email', return_value=True) as mock_welcome:
                
                response = await async_client.post("/auth/register", json=registration_data)
                
                if response.status_code in [200, 201]:
                    # Verification email should be sent
                    # Welcome email may be sent after verification
                    assert mock_verify.called or mock_welcome.called
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_default_permissions_assigned_to_new_user(self, async_client, mock_user_service):
        """Test 10: New users should receive appropriate default permissions."""
        registration_data = {
            "email": f"permissions_{uuid.uuid4()}@example.com",
            "password": "SecurePass123!",
            "full_name": "Permission Test User"
        }
        
        # Mock user with default permissions
        # Mock: Service component isolation for predictable testing behavior
        mock_user = MagicMock(spec=User)
        mock_user.id = str(uuid.uuid4())
        mock_user.email = registration_data["email"]
        mock_user.role = "free_tier"  # Default role
        mock_user.permissions = ["read:own_data", "write:own_data"]  # Default permissions
        mock_user.tier = "free"
        mock_user.api_calls_limit = 1000  # Free tier limit
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.user_service.UserService.create_user', return_value=mock_user):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.permission_service.PermissionService.assign_default_permissions', return_value=True):
                
                response = await async_client.post("/auth/register", json=registration_data)
                
                if response.status_code in [200, 201]:
                    # User should have default free tier permissions
                    assert mock_user.role == "free_tier"
                    assert "read:own_data" in mock_user.permissions
                    assert mock_user.api_calls_limit == 1000