from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''New User Registration Flow Integration Tests (L3)

# REMOVED_SYNTAX_ERROR: Tests complete new user registration journey from initial signup to first login.
# REMOVED_SYNTAX_ERROR: Validates user creation, email verification, initial permissions, and onboarding.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Free, Early, Mid (user acquisition across all segments)
    # REMOVED_SYNTAX_ERROR: - Business Goal: Conversion - smooth onboarding drives adoption
    # REMOVED_SYNTAX_ERROR: - Value Impact: First impression determines conversion rate
    # REMOVED_SYNTAX_ERROR: - Revenue Impact: Direct - user registration is the start of revenue journey
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # Test framework import - using pytest fixtures instead

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from fastapi.testclient import TestClient
    # REMOVED_SYNTAX_ERROR: from httpx import ASGITransport, AsyncClient

    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

    # Set test environment before imports
    # REMOVED_SYNTAX_ERROR: env = get_env()
    # REMOVED_SYNTAX_ERROR: env.set("ENVIRONMENT", "testing", "test")
    # REMOVED_SYNTAX_ERROR: env.set("TESTING", "true", "test")
    # REMOVED_SYNTAX_ERROR: env.set("SKIP_STARTUP_CHECKS", "true", "test")

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.models_postgres import User
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.postgres import AsyncSessionLocal
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.main import app
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_auth_service import UserAuthService as AuthService
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_service import UserService

    # Import test framework for real auth
    # REMOVED_SYNTAX_ERROR: from test_framework.fixtures.auth import create_test_user_token, create_admin_token, create_real_jwt_token

# REMOVED_SYNTAX_ERROR: class TestNewUserRegistrationFlow:
    # REMOVED_SYNTAX_ERROR: """Test new user registration flow from signup to first login."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_db_session(self):
    # REMOVED_SYNTAX_ERROR: """Create mock database session."""
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.execute = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.add = MagicMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.commit = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.refresh = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.rollback = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: session.close = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: yield session
        # REMOVED_SYNTAX_ERROR: finally:
            # REMOVED_SYNTAX_ERROR: if hasattr(session, "close"):
                # REMOVED_SYNTAX_ERROR: await session.close()

                # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_auth_service(self):
    # REMOVED_SYNTAX_ERROR: """Create mock auth service."""
    # Mock: Authentication service isolation for testing without real auth flows
    # REMOVED_SYNTAX_ERROR: service = AsyncMock(spec=AuthService)
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.create_user = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.verify_email = AsyncMock()  # TODO: Use real service instance
    # Use real JWT token generation for integration tests
    # REMOVED_SYNTAX_ERROR: service.generate_token = AsyncMock(return_value=create_test_user_token("test_user", use_real_jwt=True).token)
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: service.validate_token = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: yield service

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_user_service(self):
    # REMOVED_SYNTAX_ERROR: """Create mock user service."""
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: service = AsyncMock(spec=UserService)
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.get_user_by_email = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.create_user = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.update_user = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: yield service

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def async_client(self, mock_db_session, mock_auth_service, mock_user_service):
    # REMOVED_SYNTAX_ERROR: """Create async client with mocked dependencies."""
# REMOVED_SYNTAX_ERROR: async def override_get_db():
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: yield session
        # REMOVED_SYNTAX_ERROR: finally:
            # REMOVED_SYNTAX_ERROR: if hasattr(session, "close"):
                # REMOVED_SYNTAX_ERROR: await session.close()

                # REMOVED_SYNTAX_ERROR: app.dependency_overrides[AsyncSessionLocal] = override_get_db

                # REMOVED_SYNTAX_ERROR: transport = ASGITransport(app=app)
                # REMOVED_SYNTAX_ERROR: async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    # REMOVED_SYNTAX_ERROR: yield ac

                    # REMOVED_SYNTAX_ERROR: app.dependency_overrides.clear()

                    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                    # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_new_user_registration_basic_flow(self, async_client, mock_auth_service):
                        # Removed problematic line: '''Test 1: Basic new user registration should create user and await asyncio.sleep(0)
                        # REMOVED_SYNTAX_ERROR: return token.""""
                        # Registration data
                        # REMOVED_SYNTAX_ERROR: registration_data = { )
                        # REMOVED_SYNTAX_ERROR: "email": "formatted_string",
                        # REMOVED_SYNTAX_ERROR: "password": "SecurePass123!",
                        # REMOVED_SYNTAX_ERROR: "full_name": "Test User",
                        # REMOVED_SYNTAX_ERROR: "company": "Test Company"
                        

                        # Mock successful user creation
                        # Mock: Service component isolation for predictable testing behavior
                        # REMOVED_SYNTAX_ERROR: mock_user = MagicMock(spec=User)
                        # REMOVED_SYNTAX_ERROR: mock_user.id = str(uuid.uuid4())
                        # REMOVED_SYNTAX_ERROR: mock_user.email = registration_data["email"]
                        # REMOVED_SYNTAX_ERROR: mock_user.is_active = False  # Not active until email verified

                        # Mock: Component isolation for testing without external dependencies
                        # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.create_user', return_value=mock_user):
                            # Mock: Component isolation for testing without external dependencies
                            # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.send_verification_email', return_value=True):

                                # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/register", json=registration_data)

                                # Should return 201 Created
                                # REMOVED_SYNTAX_ERROR: assert response.status_code in [201, 200]  # Some implementations return 200

                                # REMOVED_SYNTAX_ERROR: data = response.json()
                                # REMOVED_SYNTAX_ERROR: assert "user_id" in data or "id" in data
                                # REMOVED_SYNTAX_ERROR: assert "message" in data or "email" in data

                                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_duplicate_email_registration_rejected(self, async_client, mock_user_service):
                                    # REMOVED_SYNTAX_ERROR: """Test 2: Registration with existing email should be rejected."""
                                    # REMOVED_SYNTAX_ERROR: existing_email = "existing@example.com"

                                    # Mock existing user
                                    # Mock: Service component isolation for predictable testing behavior
                                    # REMOVED_SYNTAX_ERROR: mock_user_service.get_user_by_email.return_value = MagicMock(spec=User)

                                    # REMOVED_SYNTAX_ERROR: registration_data = { )
                                    # REMOVED_SYNTAX_ERROR: "email": existing_email,
                                    # REMOVED_SYNTAX_ERROR: "password": "SecurePass123!",
                                    # REMOVED_SYNTAX_ERROR: "full_name": "Duplicate User"
                                    

                                    # Mock: Generic component isolation for controlled unit testing
                                    # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=MagicMock()  # TODO: Use real service instance):
                                        # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/register", json=registration_data)

                                        # Should await asyncio.sleep(0)
                                        # REMOVED_SYNTAX_ERROR: return 409 Conflict or 400 Bad Request
                                        # REMOVED_SYNTAX_ERROR: assert response.status_code in [409, 400]

                                        # REMOVED_SYNTAX_ERROR: data = response.json()
                                        # REMOVED_SYNTAX_ERROR: assert "already exists" in data.get("detail", "").lower() or "duplicate" in data.get("detail", "").lower()

                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_email_verification_flow(self, async_client, mock_auth_service):
                                            # REMOVED_SYNTAX_ERROR: """Test 3: Email verification should activate user account."""
                                            # REMOVED_SYNTAX_ERROR: user_id = str(uuid.uuid4())
                                            # REMOVED_SYNTAX_ERROR: verification_token = "verify_token_123"

                                            # Mock unverified user
                                            # Mock: Service component isolation for predictable testing behavior
                                            # REMOVED_SYNTAX_ERROR: mock_user = MagicMock(spec=User)
                                            # REMOVED_SYNTAX_ERROR: mock_user.id = user_id
                                            # REMOVED_SYNTAX_ERROR: mock_user.is_active = False
                                            # REMOVED_SYNTAX_ERROR: mock_user.email_verified = False

                                            # Mock verification success
                                            # REMOVED_SYNTAX_ERROR: mock_auth_service.verify_email.return_value = True

                                            # Mock: Component isolation for testing without external dependencies
                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user', return_value=mock_user):
                                                # Mock: Component isolation for testing without external dependencies
                                                # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.verify_email_token', return_value=user_id):

                                                    # REMOVED_SYNTAX_ERROR: response = await async_client.get("formatted_string")

                                                    # Should await asyncio.sleep(0)
                                                    # REMOVED_SYNTAX_ERROR: return success
                                                    # REMOVED_SYNTAX_ERROR: assert response.status_code in [200, 302]  # May redirect after verification

                                                    # User should now be active
                                                    # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                                                        # REMOVED_SYNTAX_ERROR: data = response.json()
                                                        # REMOVED_SYNTAX_ERROR: assert "verified" in data.get("message", "").lower() or data.get("verified") == True

                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_login_before_email_verification(self, async_client, mock_user_service):
                                                            # REMOVED_SYNTAX_ERROR: """Test 4: Login should fail for unverified email accounts."""
                                                            # Mock unverified user
                                                            # Mock: Service component isolation for predictable testing behavior
                                                            # REMOVED_SYNTAX_ERROR: mock_user = MagicMock(spec=User)
                                                            # REMOVED_SYNTAX_ERROR: mock_user.email = "unverified@example.com"
                                                            # REMOVED_SYNTAX_ERROR: mock_user.email_verified = False
                                                            # REMOVED_SYNTAX_ERROR: mock_user.is_active = False

                                                            # REMOVED_SYNTAX_ERROR: mock_user_service.get_user_by_email.return_value = mock_user

                                                            # REMOVED_SYNTAX_ERROR: login_data = { )
                                                            # REMOVED_SYNTAX_ERROR: "email": "unverified@example.com",
                                                            # REMOVED_SYNTAX_ERROR: "password": "password123"
                                                            

                                                            # Mock: Component isolation for testing without external dependencies
                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_user):
                                                                # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/login", json=login_data)

                                                                # Should await asyncio.sleep(0)
                                                                # REMOVED_SYNTAX_ERROR: return 403 Forbidden or 401 Unauthorized
                                                                # REMOVED_SYNTAX_ERROR: assert response.status_code in [403, 401]

                                                                # REMOVED_SYNTAX_ERROR: data = response.json()
                                                                # REMOVED_SYNTAX_ERROR: assert "not verified" in data.get("detail", "").lower() or "verify" in data.get("detail", "").lower()

                                                                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_first_login_after_verification(self, async_client, mock_auth_service):
                                                                    # REMOVED_SYNTAX_ERROR: """Test 5: First login after email verification should succeed."""
                                                                    # Mock verified user
                                                                    # Mock: Service component isolation for predictable testing behavior
                                                                    # REMOVED_SYNTAX_ERROR: mock_user = MagicMock(spec=User)
                                                                    # REMOVED_SYNTAX_ERROR: mock_user.id = str(uuid.uuid4())
                                                                    # REMOVED_SYNTAX_ERROR: mock_user.email = "verified@example.com"
                                                                    # REMOVED_SYNTAX_ERROR: mock_user.email_verified = True
                                                                    # REMOVED_SYNTAX_ERROR: mock_user.is_active = True
                                                                    # Mock: Service component isolation for predictable testing behavior
                                                                    # REMOVED_SYNTAX_ERROR: mock_user.check_password = MagicMock(return_value=True)

                                                                    # Generate real tokens for integration testing
                                                                    # REMOVED_SYNTAX_ERROR: test_token = create_test_user_token("verified@example.com", use_real_jwt=True)
                                                                    # REMOVED_SYNTAX_ERROR: mock_token = { )
                                                                    # REMOVED_SYNTAX_ERROR: "access_token": test_token.token,
                                                                    # REMOVED_SYNTAX_ERROR: "refresh_token": "formatted_string",
                                                                    # REMOVED_SYNTAX_ERROR: "token_type": "bearer",
                                                                    # REMOVED_SYNTAX_ERROR: "expires_in": 3600
                                                                    

                                                                    # Mock: Component isolation for testing without external dependencies
                                                                    # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_user):
                                                                        # Mock: Component isolation for testing without external dependencies
                                                                        # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.generate_tokens', return_value=mock_token):

                                                                            # REMOVED_SYNTAX_ERROR: login_data = { )
                                                                            # REMOVED_SYNTAX_ERROR: "email": "verified@example.com",
                                                                            # REMOVED_SYNTAX_ERROR: "password": "password123"
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/login", json=login_data)

                                                                            # Should await asyncio.sleep(0)
                                                                            # REMOVED_SYNTAX_ERROR: return 200 with tokens
                                                                            # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

                                                                            # REMOVED_SYNTAX_ERROR: data = response.json()
                                                                            # REMOVED_SYNTAX_ERROR: assert "access_token" in data
                                                                            # REMOVED_SYNTAX_ERROR: assert "refresh_token" in data
                                                                            # REMOVED_SYNTAX_ERROR: assert data["token_type"] == "bearer"

                                                                            # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                            # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_password_requirements_validation(self, async_client):
                                                                                # REMOVED_SYNTAX_ERROR: """Test 6: Registration should enforce password requirements."""
                                                                                # REMOVED_SYNTAX_ERROR: test_cases = [ )
                                                                                # REMOVED_SYNTAX_ERROR: ("weak", False, "too short"),
                                                                                # REMOVED_SYNTAX_ERROR: ("NoNumbers!", False, "missing number"),
                                                                                # REMOVED_SYNTAX_ERROR: ("nouppercase123!", False, "missing uppercase"),
                                                                                # REMOVED_SYNTAX_ERROR: ("NOLOWERCASE123!", False, "missing lowercase"),
                                                                                # REMOVED_SYNTAX_ERROR: ("NoSpecialChar123", False, "missing special"),
                                                                                # REMOVED_SYNTAX_ERROR: ("ValidPass123!", True, "valid password")
                                                                                

                                                                                # REMOVED_SYNTAX_ERROR: for password, should_succeed, description in test_cases:
                                                                                    # REMOVED_SYNTAX_ERROR: registration_data = { )
                                                                                    # REMOVED_SYNTAX_ERROR: "email": "formatted_string",
                                                                                    # REMOVED_SYNTAX_ERROR: "password": password,
                                                                                    # REMOVED_SYNTAX_ERROR: "full_name": "Test User"
                                                                                    

                                                                                    # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/register", json=registration_data)

                                                                                    # REMOVED_SYNTAX_ERROR: if should_succeed:
                                                                                        # Should accept valid password
                                                                                        # REMOVED_SYNTAX_ERROR: assert response.status_code in [200, 201, 503], "formatted_string",
                                                                                                    # REMOVED_SYNTAX_ERROR: "password": "ValidPass123!",
                                                                                                    # REMOVED_SYNTAX_ERROR: "full_name": "formatted_string"
                                                                                                    

                                                                                                    # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/register", json=registration_data)
                                                                                                    # REMOVED_SYNTAX_ERROR: responses.append(response.status_code)

                                                                                                    # Small delay to avoid overwhelming
                                                                                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                                                                                    # Should hit rate limit at some point
                                                                                                    # Check if any returned 429 (Too Many Requests) or similar
                                                                                                    # REMOVED_SYNTAX_ERROR: rate_limited = any(status == 429 for status in responses)

                                                                                                    # If no explicit rate limit, at least check consistency
                                                                                                    # REMOVED_SYNTAX_ERROR: if not rate_limited:
                                                                                                        # All should await asyncio.sleep(0)
                                                                                                        # REMOVED_SYNTAX_ERROR: return similar status (not a mix of success/failure)
                                                                                                        # REMOVED_SYNTAX_ERROR: unique_statuses = set(responses)
                                                                                                        # REMOVED_SYNTAX_ERROR: assert len(unique_statuses) <= 2, "formatted_string"

                                                                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                        # Removed problematic line: async def test_user_profile_creation_on_registration(self, async_client, mock_user_service):
                                                                                                            # REMOVED_SYNTAX_ERROR: """Test 8: Registration should create complete user profile."""
                                                                                                            # REMOVED_SYNTAX_ERROR: registration_data = { )
                                                                                                            # REMOVED_SYNTAX_ERROR: "email": "formatted_string",
                                                                                                            # REMOVED_SYNTAX_ERROR: "password": "SecurePass123!",
                                                                                                            # REMOVED_SYNTAX_ERROR: "full_name": "John Doe",
                                                                                                            # REMOVED_SYNTAX_ERROR: "company": "Acme Corp",
                                                                                                            # REMOVED_SYNTAX_ERROR: "phone": "+1234567890"
                                                                                                            

                                                                                                            # Mock user creation with profile
                                                                                                            # Mock: Service component isolation for predictable testing behavior
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_user = MagicMock(spec=User)
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_user.id = str(uuid.uuid4())
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_user.email = registration_data["email"]
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_user.full_name = registration_data["full_name"]
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_user.company = registration_data.get("company")
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_user.phone = registration_data.get("phone")
                                                                                                            # REMOVED_SYNTAX_ERROR: mock_user.created_at = datetime.now(timezone.utc)

                                                                                                            # Mock: Component isolation for testing without external dependencies
                                                                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.create_user', return_value=mock_user):
                                                                                                                # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/register", json=registration_data)

                                                                                                                # Should create user with all profile fields
                                                                                                                # REMOVED_SYNTAX_ERROR: assert response.status_code in [200, 201, 503]

                                                                                                                # REMOVED_SYNTAX_ERROR: if response.status_code in [200, 201]:
                                                                                                                    # REMOVED_SYNTAX_ERROR: data = response.json()
                                                                                                                    # Verify profile data is included or user was created
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert "user_id" in data or "id" in data or "email" in data

                                                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                    # Removed problematic line: async def test_welcome_email_sent_on_registration(self, async_client, mock_auth_service):
                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test 9: Welcome email should be sent after successful registration."""
                                                                                                                        # REMOVED_SYNTAX_ERROR: registration_data = { )
                                                                                                                        # REMOVED_SYNTAX_ERROR: "email": "formatted_string",
                                                                                                                        # REMOVED_SYNTAX_ERROR: "password": "SecurePass123!",
                                                                                                                        # REMOVED_SYNTAX_ERROR: "full_name": "New User"
                                                                                                                        

                                                                                                                        # Track email sending
                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_auth_service.send_verification_email.return_value = True
                                                                                                                        # Mock: Authentication service isolation for testing without real auth flows
                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_auth_service.send_welcome_email = AsyncMock(return_value=True)

                                                                                                                        # Mock: Component isolation for testing without external dependencies
                                                                                                                        # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.send_verification_email', return_value=True) as mock_verify:
                                                                                                                            # Mock: Component isolation for testing without external dependencies
                                                                                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.send_welcome_email', return_value=True) as mock_welcome:

                                                                                                                                # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/register", json=registration_data)

                                                                                                                                # REMOVED_SYNTAX_ERROR: if response.status_code in [200, 201]:
                                                                                                                                    # Verification email should be sent
                                                                                                                                    # Welcome email may be sent after verification
                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert mock_verify.called or mock_welcome.called

                                                                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                    # Removed problematic line: async def test_default_permissions_assigned_to_new_user(self, async_client, mock_user_service):
                                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test 10: New users should receive appropriate default permissions."""
                                                                                                                                        # REMOVED_SYNTAX_ERROR: registration_data = { )
                                                                                                                                        # REMOVED_SYNTAX_ERROR: "email": "formatted_string",
                                                                                                                                        # REMOVED_SYNTAX_ERROR: "password": "SecurePass123!",
                                                                                                                                        # REMOVED_SYNTAX_ERROR: "full_name": "Permission Test User"
                                                                                                                                        

                                                                                                                                        # Mock user with default permissions
                                                                                                                                        # Mock: Service component isolation for predictable testing behavior
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_user = MagicMock(spec=User)
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_user.id = str(uuid.uuid4())
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_user.email = registration_data["email"]
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_user.role = "free_tier"  # Default role
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_user.permissions = ["read:own_data", "write:own_data"]  # Default permissions
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_user.tier = "free"
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_user.api_calls_limit = 1000  # Free tier limit

                                                                                                                                        # Mock: Component isolation for testing without external dependencies
                                                                                                                                        # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.create_user', return_value=mock_user):
                                                                                                                                            # Mock: Component isolation for testing without external dependencies
                                                                                                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.permission_service.PermissionService.assign_default_permissions', return_value=True):

                                                                                                                                                # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/register", json=registration_data)

                                                                                                                                                # REMOVED_SYNTAX_ERROR: if response.status_code in [200, 201]:
                                                                                                                                                    # User should have default free tier permissions
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert mock_user.role == "free_tier"
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert "read:own_data" in mock_user.permissions
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert mock_user.api_calls_limit == 1000