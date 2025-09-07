"""
Auth Registration and Login Flow Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable seamless user onboarding and authentication for platform access
- Value Impact: New users can register and existing users can log in to access chat features
- Strategic Impact: Core user acquisition and retention mechanism - without working auth, no users can access the platform

CRITICAL: These tests use REAL PostgreSQL and Redis services (no mocks).
Tests validate complete registration/login flows with real database persistence.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import hashlib
import secrets
import bcrypt

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.config import AuthConfig
from auth_service.services.user_service import UserService
from auth_service.services.redis_service import RedisService
from auth_service.services.jwt_service import JWTService
from auth_service.services.password_service import PasswordService
from auth_service.database import get_database
from auth_service.models import User


class TestRegistrationLoginIntegration(BaseIntegrationTest):
    """Integration tests for user registration and login flows with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real services."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real auth service configuration
        self.auth_config = AuthConfig()
        
        # Real service instances
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.jwt_service = JWTService(self.auth_config)
        self.password_service = PasswordService()
        
        # Real database connection
        self.db = get_database()
        self.user_service = UserService(self.auth_config, self.db, self.password_service)
        
        # Test user data templates
        self.test_user_template = {
            "name": "Registration Test User",
            "password": "SecureTestPassword123!",
            "timezone": "UTC",
            "preferences": {
                "notifications": True,
                "theme": "light"
            }
        }
        
        self.created_user_emails = []  # Track for cleanup
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services."""
        try:
            # Clean test users from database
            for email in self.created_user_emails:
                try:
                    user = await self.user_service.get_user_by_email(email)
                    if user:
                        await self.user_service.delete_user(user.id)
                except Exception as e:
                    self.logger.warning(f"Could not delete test user {email}: {e}")
            
            # Clean Redis data
            test_keys = await self.redis_service.keys("*registration-test*")
            if test_keys:
                await self.redis_service.delete(*test_keys)
                
            login_keys = await self.redis_service.keys("*login-test*")
            if login_keys:
                await self.redis_service.delete(*login_keys)
                
            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    def generate_unique_email(self, prefix: str = "registration-test") -> str:
        """Generate unique email for testing."""
        timestamp = int(time.time())
        random_suffix = secrets.token_hex(4)
        email = f"{prefix}-{timestamp}-{random_suffix}@example.com"
        self.created_user_emails.append(email)
        return email
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_registration_complete_flow(self):
        """
        Test complete user registration flow with real database persistence.
        
        BVJ: New users must be able to register to access chat features and drive user acquisition.
        """
        # Generate unique test email
        test_email = self.generate_unique_email("reg-complete")
        
        registration_data = {
            "email": test_email,
            "name": self.test_user_template["name"],
            "password": self.test_user_template["password"],
            "timezone": self.test_user_template["timezone"],
            "preferences": self.test_user_template["preferences"]
        }
        
        # Step 1: Register new user
        created_user = await self.user_service.create_user(**registration_data)
        
        assert created_user is not None
        assert created_user.email == test_email
        assert created_user.name == registration_data["name"]
        assert created_user.timezone == registration_data["timezone"]
        assert created_user.id is not None
        assert created_user.created_at is not None
        assert created_user.updated_at is not None
        
        # Verify password was hashed (not stored in plain text)
        assert created_user.password_hash != registration_data["password"]
        assert len(created_user.password_hash) > 50  # Bcrypt hashes are long
        
        # Step 2: Verify user exists in database
        retrieved_user = await self.user_service.get_user_by_email(test_email)
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email
        assert retrieved_user.name == created_user.name
        
        # Step 3: Verify password verification works
        password_valid = await self.user_service.verify_password(
            retrieved_user.id,
            registration_data["password"]
        )
        assert password_valid is True
        
        # Step 4: Verify wrong password is rejected
        wrong_password_valid = await self.user_service.verify_password(
            retrieved_user.id,
            "WrongPassword123!"
        )
        assert wrong_password_valid is False
        
        # Step 5: Create authentication token for registered user
        access_token = await self.jwt_service.create_access_token(
            user_id=str(created_user.id),
            email=created_user.email,
            permissions=["read", "write"]
        )
        
        assert access_token is not None
        assert len(access_token) > 100  # JWT tokens are long
        
        # Step 6: Store session in Redis
        session_key = f"session:registration-test-{created_user.id}"
        session_data = {
            "user_id": str(created_user.id),
            "email": created_user.email,
            "name": created_user.name,
            "access_token": access_token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "registration_completed": True
        }
        
        await self.redis_service.set(
            session_key,
            json.dumps(session_data),
            ex=3600  # 1 hour
        )
        
        # Verify session storage
        stored_session = await self.redis_service.get(session_key)
        assert stored_session is not None
        
        retrieved_session = json.loads(stored_session)
        assert retrieved_session["user_id"] == str(created_user.id)
        assert retrieved_session["email"] == created_user.email
        assert retrieved_session["registration_completed"] is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_login_complete_flow(self):
        """
        Test complete user login flow for existing users.
        
        BVJ: Existing users must be able to log in to access their chat history and continue conversations.
        """
        # Step 1: Create existing user (simulate prior registration)
        test_email = self.generate_unique_email("login-test")
        
        registration_data = {
            "email": test_email,
            "name": "Login Test User",
            "password": "ExistingUserPassword123!",
            "timezone": "America/New_York"
        }
        
        existing_user = await self.user_service.create_user(**registration_data)
        assert existing_user is not None
        
        # Step 2: Login with correct credentials
        login_result = await self.user_service.authenticate_user(
            email=test_email,
            password=registration_data["password"]
        )
        
        assert login_result is not None
        assert "user" in login_result
        assert "access_token" in login_result
        
        authenticated_user = login_result["user"]
        access_token = login_result["access_token"]
        
        # Verify authenticated user data
        assert authenticated_user.id == existing_user.id
        assert authenticated_user.email == existing_user.email
        assert authenticated_user.name == existing_user.name
        
        # Verify token is valid JWT
        assert access_token is not None
        assert len(access_token) > 100
        assert access_token.count('.') == 2  # JWT structure
        
        # Step 3: Validate token using JWT service
        token_valid = await self.jwt_service.validate_token(access_token)
        assert token_valid is True
        
        # Step 4: Create login session in Redis
        login_session_key = f"session:login-test-{existing_user.id}"
        login_session_data = {
            "user_id": str(existing_user.id),
            "email": existing_user.email,
            "name": existing_user.name,
            "access_token": access_token,
            "login_method": "email_password",
            "last_login": datetime.now(timezone.utc).isoformat(),
            "ip_address": "127.0.0.1",
            "user_agent": "integration-test-client"
        }
        
        await self.redis_service.set(
            login_session_key,
            json.dumps(login_session_data),
            ex=7200  # 2 hours
        )
        
        # Verify session creation
        stored_login_session = await self.redis_service.get(login_session_key)
        assert stored_login_session is not None
        
        session_data = json.loads(stored_login_session)
        assert session_data["user_id"] == str(existing_user.id)
        assert session_data["login_method"] == "email_password"
        assert "last_login" in session_data
        
        # Step 5: Test session-based authentication
        # Simulate subsequent request using session
        user_from_session = await self.user_service.get_user_by_id(
            int(session_data["user_id"])
        )
        assert user_from_session is not None
        assert user_from_session.email == existing_user.email
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_login_with_invalid_credentials(self):
        """
        Test login failure with invalid credentials.
        
        BVJ: Protects user accounts by rejecting invalid login attempts.
        """
        # Create test user
        test_email = self.generate_unique_email("invalid-creds")
        
        registration_data = {
            "email": test_email,
            "name": "Invalid Creds Test User",
            "password": "ValidPassword123!"
        }
        
        existing_user = await self.user_service.create_user(**registration_data)
        
        # Test 1: Wrong password
        with pytest.raises(Exception, match="Invalid credentials"):
            await self.user_service.authenticate_user(
                email=test_email,
                password="WrongPassword123!"
            )
        
        # Test 2: Non-existent email
        with pytest.raises(Exception, match="User not found"):
            await self.user_service.authenticate_user(
                email="nonexistent@example.com",
                password="SomePassword123!"
            )
        
        # Test 3: Empty password
        with pytest.raises(Exception):
            await self.user_service.authenticate_user(
                email=test_email,
                password=""
            )
        
        # Test 4: Empty email
        with pytest.raises(Exception):
            await self.user_service.authenticate_user(
                email="",
                password=registration_data["password"]
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_duplicate_registration_prevention(self):
        """
        Test prevention of duplicate user registrations.
        
        BVJ: Ensures data integrity and prevents account conflicts.
        """
        test_email = self.generate_unique_email("duplicate-test")
        
        registration_data = {
            "email": test_email,
            "name": "First Registration",
            "password": "FirstPassword123!"
        }
        
        # First registration should succeed
        first_user = await self.user_service.create_user(**registration_data)
        assert first_user is not None
        assert first_user.email == test_email
        
        # Second registration with same email should fail
        duplicate_data = {
            "email": test_email,  # Same email
            "name": "Second Registration",
            "password": "SecondPassword123!"
        }
        
        with pytest.raises(Exception, match="User with email .* already exists"):
            await self.user_service.create_user(**duplicate_data)
        
        # Verify only one user exists with that email
        users_with_email = await self.user_service.get_user_by_email(test_email)
        assert users_with_email is not None
        assert users_with_email.name == "First Registration"  # Original user preserved
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_password_strength_validation(self):
        """
        Test password strength validation during registration.
        
        BVJ: Ensures user accounts have secure passwords to protect platform integrity.
        """
        test_email = self.generate_unique_email("password-strength")
        
        # Test cases for password validation
        weak_passwords = [
            "123",                    # Too short
            "password",               # No numbers/symbols
            "PASSWORD123",            # No lowercase
            "password123",            # No uppercase
            "Password",               # No numbers
            "   ",                    # Only spaces
            "",                       # Empty
        ]
        
        for weak_password in weak_passwords:
            with pytest.raises(Exception, match="Password does not meet security requirements"):
                await self.user_service.create_user(
                    email=test_email,
                    name="Weak Password Test",
                    password=weak_password
                )
        
        # Strong password should work
        strong_password_data = {
            "email": test_email,
            "name": "Strong Password User",
            "password": "StrongPassword123!"
        }
        
        user_with_strong_password = await self.user_service.create_user(**strong_password_data)
        assert user_with_strong_password is not None
        assert user_with_strong_password.email == test_email
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_registrations(self):
        """
        Test concurrent user registrations for multi-user system validation.
        
        BVJ: Ensures system can handle multiple simultaneous registrations without conflicts.
        """
        concurrent_users = 5
        
        async def register_user(user_index: int):
            """Register a single user concurrently."""
            test_email = self.generate_unique_email(f"concurrent-{user_index}")
            
            registration_data = {
                "email": test_email,
                "name": f"Concurrent User {user_index}",
                "password": f"ConcurrentPassword{user_index}123!",
                "timezone": "UTC"
            }
            
            try:
                user = await self.user_service.create_user(**registration_data)
                
                # Authenticate immediately after registration
                login_result = await self.user_service.authenticate_user(
                    email=test_email,
                    password=registration_data["password"]
                )
                
                return {
                    "user_index": user_index,
                    "user": user,
                    "login_result": login_result,
                    "success": True
                }
            except Exception as e:
                return {
                    "user_index": user_index,
                    "error": str(e),
                    "success": False
                }
        
        # Execute concurrent registrations
        tasks = [register_user(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all registrations succeeded
        successful_registrations = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        failed_registrations = [r for r in results if isinstance(r, Exception) or not r.get("success")]
        
        assert len(successful_registrations) == concurrent_users
        assert len(failed_registrations) == 0
        
        # Verify each user is unique and properly stored
        for result in successful_registrations:
            user = result["user"]
            login_result = result["login_result"]
            
            assert user is not None
            assert user.id is not None
            assert user.email.startswith(f"concurrent-{result['user_index']}")
            
            assert login_result is not None
            assert "access_token" in login_result
            assert login_result["access_token"] is not None
            
            # Verify user exists in database
            db_user = await self.user_service.get_user_by_email(user.email)
            assert db_user is not None
            assert db_user.id == user.id
        
        # Verify all users have unique IDs and emails
        user_ids = [r["user"].id for r in successful_registrations]
        user_emails = [r["user"].email for r in successful_registrations]
        
        assert len(set(user_ids)) == concurrent_users
        assert len(set(user_emails)) == concurrent_users
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_profile_update_after_registration(self):
        """
        Test user profile updates after initial registration.
        
        BVJ: Allows users to maintain and update their profile information for better personalization.
        """
        # Create initial user
        test_email = self.generate_unique_email("profile-update")
        
        initial_data = {
            "email": test_email,
            "name": "Initial Name",
            "password": "InitialPassword123!",
            "timezone": "UTC"
        }
        
        created_user = await self.user_service.create_user(**initial_data)
        
        # Update user profile
        update_data = {
            "name": "Updated Name",
            "timezone": "America/Los_Angeles",
            "preferences": {
                "notifications": False,
                "theme": "dark",
                "language": "en"
            }
        }
        
        updated_user = await self.user_service.update_user_profile(
            user_id=created_user.id,
            **update_data
        )
        
        assert updated_user is not None
        assert updated_user.name == update_data["name"]
        assert updated_user.timezone == update_data["timezone"]
        
        # Verify changes persisted in database
        db_user = await self.user_service.get_user_by_id(created_user.id)
        assert db_user.name == update_data["name"]
        assert db_user.timezone == update_data["timezone"]
        
        # Verify email and password unchanged
        assert db_user.email == initial_data["email"]
        
        password_still_valid = await self.user_service.verify_password(
            db_user.id,
            initial_data["password"]
        )
        assert password_still_valid is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_password_change_flow(self):
        """
        Test password change functionality for existing users.
        
        BVJ: Enables users to update passwords for security and account recovery.
        """
        # Create user with initial password
        test_email = self.generate_unique_email("password-change")
        
        initial_data = {
            "email": test_email,
            "name": "Password Change User",
            "password": "OldPassword123!"
        }
        
        user = await self.user_service.create_user(**initial_data)
        
        # Verify initial password works
        initial_login = await self.user_service.authenticate_user(
            email=test_email,
            password="OldPassword123!"
        )
        assert initial_login is not None
        
        # Change password
        new_password = "NewSecurePassword456!"
        
        await self.user_service.update_password(
            user_id=user.id,
            old_password="OldPassword123!",
            new_password=new_password
        )
        
        # Verify old password no longer works
        with pytest.raises(Exception, match="Invalid credentials"):
            await self.user_service.authenticate_user(
                email=test_email,
                password="OldPassword123!"  # Old password
            )
        
        # Verify new password works
        new_login = await self.user_service.authenticate_user(
            email=test_email,
            password=new_password
        )
        assert new_login is not None
        assert "access_token" in new_login
        
        # Invalidate existing sessions in Redis (security best practice)
        session_pattern = f"session:*{user.id}*"
        old_sessions = await self.redis_service.keys(session_pattern)
        if old_sessions:
            await self.redis_service.delete(*old_sessions)
        
        # Create new session with updated credentials
        new_session_key = f"session:password-change-{user.id}"
        new_session_data = {
            "user_id": str(user.id),
            "email": user.email,
            "access_token": new_login["access_token"],
            "password_changed_at": datetime.now(timezone.utc).isoformat(),
            "security_event": "password_changed"
        }
        
        await self.redis_service.set(
            new_session_key,
            json.dumps(new_session_data),
            ex=3600
        )
        
        # Verify new session
        stored_new_session = await self.redis_service.get(new_session_key)
        assert stored_new_session is not None
        
        session_data = json.loads(stored_new_session)
        assert session_data["security_event"] == "password_changed"
        assert "password_changed_at" in session_data
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_cleanup_on_logout(self):
        """
        Test session cleanup when user logs out.
        
        BVJ: Ensures proper session management and security by cleaning up user sessions.
        """
        # Create and login user
        test_email = self.generate_unique_email("logout-test")
        
        registration_data = {
            "email": test_email,
            "name": "Logout Test User",
            "password": "LogoutPassword123!"
        }
        
        user = await self.user_service.create_user(**registration_data)
        login_result = await self.user_service.authenticate_user(
            email=test_email,
            password=registration_data["password"]
        )
        
        # Create multiple sessions for the user
        session_keys = []
        for i in range(3):
            session_key = f"session:logout-test-{user.id}-{i}"
            session_data = {
                "user_id": str(user.id),
                "email": user.email,
                "access_token": login_result["access_token"],
                "session_index": i,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_service.set(
                session_key,
                json.dumps(session_data),
                ex=3600
            )
            session_keys.append(session_key)
        
        # Verify sessions exist
        for session_key in session_keys:
            session_exists = await self.redis_service.get(session_key)
            assert session_exists is not None
        
        # Perform logout (cleanup all user sessions)
        await self.user_service.logout_user(user.id)
        
        # Verify all sessions are cleaned up
        for session_key in session_keys:
            session_after_logout = await self.redis_service.get(session_key)
            assert session_after_logout is None
        
        # Verify user can still login again (logout doesn't affect user account)
        new_login = await self.user_service.authenticate_user(
            email=test_email,
            password=registration_data["password"]
        )
        assert new_login is not None
        assert "access_token" in new_login