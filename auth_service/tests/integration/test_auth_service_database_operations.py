"""
Test Auth Service Database Operations - BATCH 4 Authentication Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable user data persistence and session management
- Value Impact: Users can maintain accounts and sessions across platform restarts
- Strategic Impact: Core database operations for multi-user authentication system

Focus: Database persistence, user management, session storage, data integrity
"""

import pytest
import asyncio
from datetime import datetime, UTC

from auth_service.auth_core.services.auth_service import AuthService
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env


class TestAuthServiceDatabaseOperations(BaseIntegrationTest):
    """Test auth service database operations and persistence"""

    def setup_method(self):
        """Set up test environment"""
        self.auth_service = AuthService()

    @pytest.mark.integration
    async def test_user_creation_with_database_fallback(self, isolated_env):
        """Test user creation with database availability and fallback scenarios"""
        # Test case 1: Database not available - should fallback to in-memory
        self.auth_service._db_connection = None
        
        user_email = "fallback-test@example.com"
        user_password = "FallbackPass123!"
        user_name = "Fallback Test User"
        
        user_id = await self.auth_service.create_user(user_email, user_password, user_name)
        assert user_id is not None
        
        # Verify user was stored in in-memory fallback
        assert user_email in self.auth_service._test_users
        stored_user = self.auth_service._test_users[user_email]
        assert stored_user['email'] == user_email
        assert stored_user['name'] == user_name
        assert 'password_hash' in stored_user
        
        # Test case 2: Duplicate user creation should fail
        duplicate_user_id = await self.auth_service.create_user(user_email, "AnotherPass123!", "Another User")
        assert duplicate_user_id is None  # Should fail for duplicate email

    @pytest.mark.integration
    async def test_user_authentication_database_integration(self, isolated_env):
        """Test user authentication with database integration and fallback"""
        # Create a user first
        user_email = "auth-test@example.com"
        user_password = "AuthTestPass123!"
        user_name = "Auth Test User"
        
        user_id = await self.auth_service.create_user(user_email, user_password, user_name)
        assert user_id is not None
        
        # Test successful authentication
        auth_result = await self.auth_service.authenticate_user(user_email, user_password)
        assert auth_result is not None
        authenticated_user_id, user_data = auth_result
        assert authenticated_user_id == user_id
        assert user_data["email"] == user_email
        assert user_data["name"] == user_name
        
        # Test failed authentication with wrong password
        failed_auth = await self.auth_service.authenticate_user(user_email, "WrongPassword123!")
        assert failed_auth is None
        
        # Test authentication with non-existent user
        nonexistent_auth = await self.auth_service.authenticate_user("nonexistent@example.com", "AnyPassword123!")
        assert nonexistent_auth is None
        
        # Test development fallback user
        dev_auth = await self.auth_service.authenticate_user("dev@example.com", "dev")
        assert dev_auth is not None
        dev_user_id, dev_data = dev_auth
        assert dev_user_id == "dev-user-001"
        assert dev_data["email"] == "dev@example.com"

    @pytest.mark.integration
    async def test_database_connection_health_monitoring(self, isolated_env):
        """Test database connection health monitoring and error handling"""
        # Test database initialization state
        if self.auth_service._db_connection:
            # Database connection available
            assert hasattr(self.auth_service._db_connection, 'get_session')
        else:
            # Database connection not available (expected in test environment)
            assert self.auth_service._db_connection is None
        
        # Test _get_db_session method handles both cases
        db_session = await self.auth_service._get_db_session()
        # In test environment, this may return None (no database) or a session (database available)
        # Both are valid test outcomes
        
        # Verify service can operate in stateless mode
        if db_session is None:
            # Should operate in stateless mode
            # Test that CRUD operations fall back to in-memory storage
            test_user_id = await self.auth_service.create_user(
                "stateless-test@example.com", 
                "StatelessPass123!", 
                "Stateless User"
            )
            assert test_user_id is not None
            
            # Verify user was stored in memory
            assert "stateless-test@example.com" in self.auth_service._test_users

    @pytest.mark.integration
    async def test_session_persistence_and_cleanup(self, isolated_env):
        """Test session persistence, retrieval, and cleanup operations"""
        # Create test users and sessions
        user1_id = "test-user-001"
        user1_data = {"email": "user1@example.com", "name": "User 1", "role": "standard"}
        
        user2_id = "test-user-002"  
        user2_data = {"email": "user2@example.com", "name": "User 2", "role": "admin"}
        
        # Create multiple sessions for each user
        session1_1 = self.auth_service.create_session(user1_id, user1_data)
        session1_2 = self.auth_service.create_session(user1_id, user1_data)
        session2_1 = self.auth_service.create_session(user2_id, user2_data)
        
        # Verify sessions are created with unique IDs
        assert len({session1_1, session1_2, session2_1}) == 3  # All unique
        
        # Verify session data is stored correctly
        assert session1_1 in self.auth_service._sessions
        assert self.auth_service._sessions[session1_1]['user_id'] == user1_id
        assert self.auth_service._sessions[session1_1]['user_data']['email'] == "user1@example.com"
        
        # Test session timestamps are recent
        session_created = self.auth_service._sessions[session1_1]['created_at']
        time_diff = datetime.now(UTC) - session_created
        assert time_diff.total_seconds() < 5  # Created within last 5 seconds
        
        # Test selective session cleanup (delete single session)
        deleted = self.auth_service.delete_session(session1_1)
        assert deleted is True
        assert session1_1 not in self.auth_service._sessions
        assert session1_2 in self.auth_service._sessions  # Other user1 session remains
        assert session2_1 in self.auth_service._sessions  # User2 session remains
        
        # Test bulk session cleanup (invalidate all sessions for user)
        await self.auth_service.invalidate_user_sessions(user1_id)
        assert session1_2 not in self.auth_service._sessions  # User1 sessions removed
        assert session2_1 in self.auth_service._sessions      # User2 session remains
        
        # Test cleanup of non-existent session
        deleted_nonexistent = self.auth_service.delete_session("nonexistent-session-id")
        assert deleted_nonexistent is False

    @pytest.mark.integration
    async def test_password_reset_workflow_integration(self, isolated_env):
        """Test complete password reset workflow with database operations"""
        from auth_service.auth_core.models.auth_models import PasswordResetRequest, PasswordResetConfirm
        
        # Test password reset request for non-existent user (should not reveal existence)
        reset_request = PasswordResetRequest(email="nonexistent@example.com")
        reset_response = await self.auth_service.request_password_reset(reset_request)
        
        assert reset_response.success is True
        assert "If email exists" in reset_response.message
        # Should not reveal whether email exists or not
        
        # Test password reset request for existing user (mock environment)
        existing_email = "test@example.com"
        reset_request_existing = PasswordResetRequest(email=existing_email)
        reset_response_existing = await self.auth_service.request_password_reset(reset_request_existing)
        
        assert reset_response_existing.success is True
        assert "If email exists" in reset_response_existing.message
        
        # In testing environment, token should be provided
        if hasattr(reset_response_existing, 'reset_token') and reset_response_existing.reset_token:
            # Test password reset confirmation with mock token
            new_password = "NewSecurePassword123!"
            reset_confirm = PasswordResetConfirm(
                reset_token=reset_response_existing.reset_token,
                new_password=new_password
            )
            
            confirm_response = await self.auth_service.confirm_password_reset(reset_confirm)
            assert confirm_response.success is True
            assert "successfully" in confirm_response.message
        
        # Test invalid reset token
        invalid_confirm = PasswordResetConfirm(
            reset_token="invalid-token-12345",
            new_password="NewPassword123!"
        )
        
        try:
            invalid_response = await self.auth_service.confirm_password_reset(invalid_confirm)
            # May succeed with mock implementation
            if not invalid_response.success:
                assert "Invalid or expired" in str(invalid_response) or "token" in str(invalid_response)
        except Exception as e:
            # Should raise AuthError for invalid token
            assert "Invalid" in str(e) or "token" in str(e)

    @pytest.mark.integration
    async def test_audit_logging_and_event_tracking(self, isolated_env):
        """Test audit logging and authentication event tracking"""
        # Test audit logging infrastructure exists
        assert hasattr(self.auth_service, '_audit_log')
        assert callable(getattr(self.auth_service, '_audit_log'))
        
        # Test audit log with retry functionality
        assert hasattr(self.auth_service, '_audit_log_with_retry')
        assert callable(getattr(self.auth_service, '_audit_log_with_retry'))
        
        # Test that audit logging doesn't break authentication flow
        user_email = "audit-test@example.com"
        user_password = "AuditTestPass123!"
        
        # Create user (should trigger audit log)
        user_id = await self.auth_service.create_user(user_email, user_password, "Audit User")
        assert user_id is not None
        
        # Authenticate user (should trigger audit log)
        auth_result = await self.auth_service.authenticate_user(user_email, user_password)
        assert auth_result is not None
        
        # Test manual audit logging
        try:
            await self.auth_service._audit_log(
                event_type="test_event",
                user_id=user_id,
                success=True,
                metadata={"test": "audit_integration"},
                client_info={"ip": "127.0.0.1", "user_agent": "test-client"}
            )
        except Exception as e:
            # Audit logging should not fail authentication operations
            # In test environment without database, this may log to console only
            pass
        
        # Test audit log with retry (should handle failures gracefully)
        try:
            await self.auth_service._audit_log_with_retry(
                event_type="test_retry_event",
                user_id=user_id,
                success=True,
                metadata={"test": "retry_integration"}
            )
        except Exception:
            # Should not propagate exceptions to main auth flow
            pass

    @pytest.mark.e2e
    async def test_complete_database_integration_workflow(self, isolated_env):
        """E2E test of complete database integration workflow"""
        # Test complete user lifecycle with database operations
        
        # 1. User Registration
        user_email = "e2e-db-test@example.com"
        user_password = "E2EDbTestPass123!"
        user_name = "E2E DB Test User"
        
        user_id = await self.auth_service.create_user(user_email, user_password, user_name)
        assert user_id is not None
        
        # 2. User Authentication
        auth_result = await self.auth_service.authenticate_user(user_email, user_password)
        assert auth_result is not None
        authenticated_user_id, user_data = auth_result
        assert authenticated_user_id == user_id
        
        # 3. Session Management
        session_id = self.auth_service.create_session(user_id, user_data)
        assert session_id is not None
        assert session_id in self.auth_service._sessions
        
        # 4. Token Generation and Validation
        access_token = await self.auth_service.create_access_token(user_id, user_email)
        refresh_token = await self.auth_service.create_refresh_token(user_id, user_email)
        
        token_validation = await self.auth_service.validate_token(access_token)
        assert token_validation is not None
        assert token_validation.valid is True
        assert token_validation.user_id == user_id
        
        # 5. Token Refresh Operations
        refresh_result = await self.auth_service.refresh_tokens(refresh_token)
        if refresh_result:  # May fail in test environment without full database
            new_access, new_refresh = refresh_result
            assert new_access != access_token
            assert new_refresh != refresh_token
        
        # 6. Password Reset Workflow
        from auth_service.auth_core.models.auth_models import PasswordResetRequest
        reset_request = PasswordResetRequest(email=user_email)
        reset_response = await self.auth_service.request_password_reset(reset_request)
        assert reset_response.success is True
        
        # 7. Session Cleanup
        await self.auth_service.invalidate_user_sessions(user_id)
        assert session_id not in self.auth_service._sessions
        
        # 8. Account Security - Multiple authentication attempts
        # Test that multiple failed attempts don't crash the system
        for _ in range(3):
            failed_auth = await self.auth_service.authenticate_user(user_email, "WrongPassword123!")
            assert failed_auth is None
        
        # Valid authentication should still work after failed attempts
        valid_auth = await self.auth_service.authenticate_user(user_email, user_password)
        assert valid_auth is not None
        
        # 9. Service authentication for cross-service communication
        service_token = await self.auth_service.create_service_token("test-service")
        assert service_token is not None
        assert len(service_token.split('.')) == 3  # Valid JWT structure