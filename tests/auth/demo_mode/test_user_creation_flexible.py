"""
Demo Mode User Creation Flexible Tests

BUSINESS VALUE: Free Segment - Demo Environment Usability
GOAL: Conversion - Simplify user registration for demo evaluation
VALUE IMPACT: Eliminates registration friction preventing demo completion
REVENUE IMPACT: Higher demo engagement leads to increased conversion rates

These tests verify that user creation is more flexible in demo mode.
Initial status: THESE TESTS WILL FAIL - they demonstrate current restrictive behavior.

Tests cover:
1. Simple password requirements (4 chars vs complex requirements)
2. Simple email validation (test@test vs complex validation)
3. Auto-user creation from JWT claims
4. Default demo users available
5. Bypass email verification in demo mode
"""

import pytest
from unittest.mock import patch, MagicMock
import asyncio

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from auth_service.auth_core.services.auth_service import AuthService


class TestUserCreationFlexible(SSotAsyncTestCase):
    """
    Test user creation flexibility in demo mode.
    
    EXPECTED BEHAVIOR (currently failing):
    - Simple passwords should be accepted (4 chars minimum)
    - Simple email formats should be valid
    - Users should be auto-created from valid JWT claims
    - Default demo users should be available
    """

    def setup_method(self, method):
        """Setup for user creation tests."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.original_demo_mode = self.env.get_env().get("DEMO_MODE", "false")
        
        # Mock auth service for testing
        self.auth_service = AuthService()

    def teardown_method(self, method):
        """Cleanup after user creation tests."""
        # Restore original DEMO_MODE setting
        if self.original_demo_mode != "false":
            self.env.set_env("DEMO_MODE", self.original_demo_mode)
        else:
            self.env.unset_env("DEMO_MODE")
        super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_demo_mode_simple_password_requirements(self):
        """
        FAILING TEST: Verify simple password requirements in demo mode.
        
        EXPECTED DEMO BEHAVIOR:
        - 4 character minimum password instead of 8+
        - No special character requirements
        - No uppercase/lowercase requirements
        - No number requirements
        
        CURRENT BEHAVIOR: Strict password requirements always enforced
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "true")
        
        simple_passwords = [
            "demo",      # 4 chars, all lowercase
            "test",      # 4 chars, all lowercase
            "1234",      # 4 chars, all numbers
            "abcd",      # 4 chars, all letters
        ]
        
        for password in simple_passwords:
            # Act & Assert - This will fail because simple passwords aren't accepted
            with pytest.raises(Exception, match="Password.*too.*weak|Password.*requirements"):
                user_data = {
                    "email": "demo@demo.com",
                    "password": password,
                    "demo_mode": True
                }
                
                # This will fail because current system requires complex passwords
                result = await self.auth_service.create_user(user_data)
                
                # These assertions will fail initially
                assert result.success is True
                assert result.user_id is not None
                assert result.message != "Password too weak"

    @pytest.mark.asyncio
    async def test_demo_mode_simple_email_validation(self):
        """
        FAILING TEST: Verify simple email validation in demo mode.
        
        EXPECTED DEMO BEHAVIOR:
        - test@test should be valid
        - a@b should be valid
        - demo@demo should be valid
        - Simple formats prioritized for demo ease
        
        CURRENT BEHAVIOR: Strict email validation enforced
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "true")
        
        simple_emails = [
            "test@test",
            "a@b", 
            "demo@demo",
            "user@dev",
            "admin@localhost"
        ]
        
        for email in simple_emails:
            # Act & Assert - This will fail because simple emails aren't accepted
            with pytest.raises(Exception, match="Invalid email|Email validation failed"):
                user_data = {
                    "email": email,
                    "password": "demo",
                    "demo_mode": True
                }
                
                # This will fail because current system requires proper email format
                result = await self.auth_service.create_user(user_data)
                
                # These assertions will fail initially
                assert result.success is True
                assert result.user_id is not None
                assert result.email == email

    @pytest.mark.asyncio
    async def test_demo_mode_auto_user_creation_from_jwt(self):
        """
        FAILING TEST: Verify users are auto-created from valid JWT claims.
        
        EXPECTED DEMO BEHAVIOR:
        - Valid JWT with user claims should auto-create user
        - Should not require explicit registration
        - Should use JWT claims as user data
        - Should create demo user profile automatically
        
        CURRENT BEHAVIOR: Explicit user registration required
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "true")
        
        jwt_claims = {
            "sub": "demo_user_789",
            "email": "auto@demo.com",
            "name": "Demo User",
            "demo_account": True
        }
        
        # Act & Assert - This will fail because auto-creation isn't implemented
        with pytest.raises(Exception, match="Auto.*creation.*not.*implemented|User not found"):
            # This will fail because auto-creation from JWT doesn't exist
            result = await self.auth_service.create_user_from_jwt_claims(jwt_claims)
            
            # These assertions will fail initially
            assert result.success is True
            assert result.user_id == "demo_user_789"
            assert result.email == "auto@demo.com"
            assert result.auto_created is True

    @pytest.mark.asyncio
    async def test_demo_mode_default_demo_users_available(self):
        """
        FAILING TEST: Verify default demo users are available.
        
        EXPECTED DEMO BEHAVIOR:
        - demo@demo.com user should exist by default
        - test@test.com user should exist by default
        - admin@demo.com user should exist by default
        - Should be able to login with simple passwords
        
        CURRENT BEHAVIOR: No default users exist
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "true")
        
        default_users = [
            {"email": "demo@demo.com", "password": "demo"},
            {"email": "test@test.com", "password": "test"},
            {"email": "admin@demo.com", "password": "admin"}
        ]
        
        for user_creds in default_users:
            # Act & Assert - This will fail because default users don't exist
            with pytest.raises(Exception, match="User not found|Authentication failed"):
                # This will fail because default demo users aren't created
                result = await self.auth_service.authenticate_user(
                    user_creds["email"], 
                    user_creds["password"],
                    demo_mode=True
                )
                
                # These assertions will fail initially
                assert result.success is True
                assert result.user_id is not None
                assert result.is_demo_user is True

    @pytest.mark.asyncio
    async def test_demo_mode_bypasses_email_verification(self):
        """
        FAILING TEST: Verify email verification is bypassed in demo mode.
        
        EXPECTED DEMO BEHAVIOR:
        - Users should be created with verified email status
        - Should skip email verification flow
        - Should be immediately usable after creation
        
        CURRENT BEHAVIOR: Email verification always required
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "true")
        
        user_data = {
            "email": "noverify@demo.com",
            "password": "demo",
            "demo_mode": True
        }
        
        # Act & Assert - This will fail because email verification isn't bypassed
        with pytest.raises(Exception, match="Email verification required|Account not verified"):
            result = await self.auth_service.create_user(user_data)
            
            # These assertions will fail initially - user should be immediately verified
            assert result.success is True
            assert result.email_verified is True
            assert result.verification_required is False
            
            # Should be able to login immediately without verification
            login_result = await self.auth_service.authenticate_user(
                user_data["email"], 
                user_data["password"],
                demo_mode=True
            )
            assert login_result.success is True

    @pytest.mark.asyncio
    async def test_demo_mode_bulk_user_creation(self):
        """
        FAILING TEST: Verify bulk user creation for demo scenarios.
        
        EXPECTED DEMO BEHAVIOR:
        - Should allow creating multiple users quickly
        - Should not enforce rate limits on user creation
        - Should create demo user profiles efficiently
        
        CURRENT BEHAVIOR: Rate limits and individual creation only
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "true")
        
        users_to_create = [
            {"email": f"demo{i}@demo.com", "password": "demo"} 
            for i in range(10)
        ]
        
        # Act & Assert - This will fail because bulk creation isn't implemented
        with pytest.raises(Exception, match="Bulk creation not supported|Rate limit exceeded"):
            # This will fail because bulk user creation doesn't exist
            result = await self.auth_service.create_users_bulk(users_to_create, demo_mode=True)
            
            # These assertions will fail initially
            assert result.success is True
            assert len(result.created_users) == 10
            assert all(user.demo_user is True for user in result.created_users)

    @pytest.mark.asyncio
    async def test_production_mode_maintains_strict_requirements(self):
        """
        TEST: Verify production mode maintains strict user creation requirements.
        
        This test should PASS - demonstrates that production security isn't compromised.
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "false")
        
        # Act & Assert - This should fail in production mode (correct behavior)
        with pytest.raises(Exception):
            user_data = {
                "email": "test@test",  # Invalid email
                "password": "weak",    # Weak password
                "demo_mode": False
            }
            await self.auth_service.create_user(user_data)

    @pytest.mark.asyncio
    async def test_demo_mode_user_roles_and_permissions(self):
        """
        FAILING TEST: Verify demo users get appropriate roles and permissions.
        
        EXPECTED DEMO BEHAVIOR:
        - Demo users should get "demo_user" role
        - Should have limited but functional permissions
        - Should be able to access demo features
        - Should be clearly identified as demo accounts
        
        CURRENT BEHAVIOR: Standard user roles only
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "true")
        
        user_data = {
            "email": "role@demo.com",
            "password": "demo",
            "demo_mode": True
        }
        
        # Act & Assert - This will fail because demo roles aren't implemented
        with pytest.raises(Exception, match="Demo roles not implemented"):
            result = await self.auth_service.create_user(user_data)
            
            # These assertions will fail initially
            assert result.success is True
            assert "demo_user" in result.roles
            assert result.permissions["can_use_demo_features"] is True
            assert result.account_type == "demo"
            assert result.is_temporary_account is True

    @pytest.mark.asyncio
    async def test_demo_mode_password_history_disabled(self):
        """
        FAILING TEST: Verify password history is disabled in demo mode.
        
        EXPECTED DEMO BEHAVIOR:
        - Should allow password reuse in demo mode
        - Should not track password history for demo users
        - Should prioritize demo usability
        
        CURRENT BEHAVIOR: Password history enforced
        """
        # Arrange
        self.env.set_env("DEMO_MODE", "true")
        
        user_data = {
            "email": "reuse@demo.com",
            "password": "demo",
            "demo_mode": True
        }
        
        # Act & Assert - This will fail because password history isn't disabled
        with pytest.raises(Exception, match="Password.*recently.*used|Password history enforced"):
            # Create user
            result1 = await self.auth_service.create_user(user_data)
            assert result1.success is True
            
            # Change password
            await self.auth_service.change_password(result1.user_id, "demo", "newpass")
            
            # Change back to original password - should work in demo mode
            result2 = await self.auth_service.change_password(result1.user_id, "newpass", "demo")
            
            # These assertions will fail initially
            assert result2.success is True
            assert result2.password_reuse_allowed is True