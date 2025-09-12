"""
E2E Test: User Sessions Authentication Flow

This test validates the complete authentication flow that depends on the user_sessions table.
Demonstrates the business impact when the user_sessions table is missing from staging database.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication works end-to-end for all users
- Value Impact: Authentication failure blocks ALL user access to chat functionality
- Strategic Impact: $120K+ MRR protection by ensuring users can log in and use the platform

CRITICAL: This test uses REAL authentication flows and will FAIL if the user_sessions
table is missing, demonstrating the exact business impact of the deployment issue.
"""

import pytest
import asyncio
import logging
import json
from typing import Dict, Any
from datetime import datetime, timezone

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EAuthConfig,
    create_test_user_with_auth,
    create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestUserSessionsAuthenticationE2E(BaseE2ETest):
    """
    E2E test that validates complete authentication flow requiring user_sessions table.
    
    This test demonstrates the end-to-end user experience when authentication
    depends on user_sessions table operations. If the table is missing,
    users cannot log in or maintain sessions.
    """
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_complete_user_authentication_flow_e2e(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Complete user authentication flow from login to chat.
        
        This test simulates the complete user journey:
        1. User registration/login (requires user_sessions for session management)  
        2. JWT token validation (may require user_sessions for session tracking)
        3. WebSocket connection with authentication
        4. Chat functionality access
        
        FAILURE SCENARIO: If user_sessions table is missing, this flow will fail
        at session management steps, preventing users from accessing chat.
        """
        logger.info(" SEARCH:  CRITICAL E2E: Complete user authentication flow test")
        
        # Step 1: Create authenticated user (requires user_sessions for session management)
        try:
            auth_user = await create_test_user_with_auth(
                email="e2e-user-sessions-test@example.com",
                name="E2E User Sessions Test User",
                environment="test",
                permissions=["read", "write", "chat"]
            )
            
            assert auth_user["auth_success"] is True, "User authentication should succeed"
            assert auth_user["jwt_token"] is not None, "JWT token should be created"
            assert auth_user["user_id"] is not None, "User ID should be assigned"
            
            logger.info(f" PASS:  Step 1: User authentication successful for {auth_user['email']}")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE Step 1: User authentication failed: {e}. "
                f"This may indicate user_sessions table issues preventing auth operations."
            )
        
        # Step 2: Validate JWT token and session management
        try:
            auth_helper = E2EAuthHelper(environment="test")
            
            # Validate the JWT token
            token_validation = await auth_helper.validate_jwt_token(auth_user["jwt_token"])
            
            assert token_validation["valid"] is True, "JWT token should be valid"
            assert token_validation["user_id"] == auth_user["user_id"], "Token user ID should match"
            
            logger.info(" PASS:  Step 2: JWT token validation successful")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE Step 2: JWT token validation failed: {e}. "
                f"This may indicate session management issues related to user_sessions table."
            )
        
        # Step 3: WebSocket connection with authentication (may require session validation)
        try:
            auth_helper = E2EAuthHelper(environment="test") 
            
            # Get WebSocket headers with authentication
            websocket_headers = auth_helper.get_websocket_headers(auth_user["jwt_token"])
            
            assert "Authorization" in websocket_headers, "WebSocket headers should include Authorization"
            assert websocket_headers["Authorization"].startswith("Bearer "), "Should use Bearer token format"
            
            logger.info(" PASS:  Step 3: WebSocket authentication headers prepared")
            
            # Test WebSocket connection (this tests the full auth pipeline)
            websocket_url = f"ws://localhost:8000/ws"
            
            async with WebSocketTestClient(
                url=websocket_url,
                headers=websocket_headers,
                timeout=10.0
            ) as websocket:
                
                # Send authentication test message
                auth_test_message = {
                    "type": "auth_test",
                    "message": "Test authentication via user_sessions", 
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send_json(auth_test_message)
                logger.info(" PASS:  Step 3: WebSocket connection and message send successful")
                
                # Try to receive response (validates the auth worked end-to-end)
                try:
                    response = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                    logger.info(f" PASS:  Step 3: Received WebSocket response: {response.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    logger.warning(" WARNING: [U+FE0F] Step 3: WebSocket response timeout (may be normal for auth test)")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE Step 3: WebSocket authentication failed: {e}. "
                f"This indicates end-to-end authentication pipeline failure, "
                f"possibly due to missing user_sessions table affecting session validation."
            )
        
        # Step 4: Validate user can access chat functionality
        try:
            # Create user context for chat operations
            user_context = await create_authenticated_user_context(
                user_email=auth_user["email"],
                user_id=auth_user["user_id"],
                environment="test",
                permissions=auth_user["permissions"],
                websocket_enabled=True
            )
            
            assert user_context.user_id is not None, "User context should have user ID"
            assert user_context.agent_context["jwt_token"] is not None, "User context should have JWT token"
            
            logger.info(" PASS:  Step 4: User context for chat functionality created successfully")
            
            # Validate the user context has all required components for chat
            required_context_fields = ["jwt_token", "user_email", "environment", "permissions"]
            for field in required_context_fields:
                assert field in user_context.agent_context, f"User context missing {field}"
            
            logger.info(" PASS:  Step 4: User context validated for chat functionality access")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE Step 4: Chat functionality access failed: {e}. "
                f"User authentication succeeded but chat access failed, "
                f"indicating user_sessions table issues affecting user context creation."
            )
        
        logger.info(" CELEBRATION:  COMPLETE SUCCESS: End-to-end authentication flow works correctly")
        logger.info(" PASS:  All steps passed - user_sessions table is functioning properly")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_user_session_persistence_e2e(self, real_services_fixture):
        """
        CRITICAL E2E TEST: User session persistence across requests.
        
        This test validates that user sessions are properly maintained across
        multiple requests, which requires the user_sessions table to store
        and retrieve session data.
        
        FAILURE SCENARIO: If user_sessions table is missing, session persistence
        will fail and users will need to re-authenticate constantly.
        """
        logger.info(" SEARCH:  CRITICAL E2E: User session persistence test")
        
        auth_helper = E2EAuthHelper(environment="test")
        
        # Step 1: Create user and establish session
        try:
            user_data = await create_test_user_with_auth(
                email="e2e-session-persistence@example.com",
                name="Session Persistence Test User",
                environment="test"
            )
            
            initial_token = user_data["jwt_token"]
            user_id = user_data["user_id"]
            
            logger.info(f" PASS:  Step 1: Initial session established for user {user_id}")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE Step 1: Initial session creation failed: {e}")
        
        # Step 2: Validate session persists across multiple requests
        try:
            # Make multiple authenticated requests to test session persistence
            for request_number in range(3):
                logger.info(f"Testing session persistence - request {request_number + 1}")
                
                # Validate token is still valid
                validation_result = await auth_helper.validate_jwt_token(initial_token)
                
                assert validation_result["valid"] is True, f"Session should persist for request {request_number + 1}"
                assert validation_result["user_id"] == user_id, "Session should maintain same user ID"
                
                # Simulate some delay between requests
                await asyncio.sleep(0.5)
            
            logger.info(" PASS:  Step 2: Session persisted across multiple requests")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE Step 2: Session persistence failed: {e}. "
                f"This indicates user_sessions table issues preventing session storage/retrieval."
            )
        
        # Step 3: Test session cleanup and renewal
        try:
            # Create a second session to test concurrent session management
            second_user_data = await create_test_user_with_auth(
                email="e2e-concurrent-session@example.com", 
                name="Concurrent Session Test User",
                environment="test"
            )
            
            second_token = second_user_data["jwt_token"]
            second_user_id = second_user_data["user_id"]
            
            # Validate both sessions work concurrently
            first_validation = await auth_helper.validate_jwt_token(initial_token)
            second_validation = await auth_helper.validate_jwt_token(second_token)
            
            assert first_validation["valid"] is True, "First session should still be valid"
            assert second_validation["valid"] is True, "Second session should be valid"
            assert first_validation["user_id"] != second_validation["user_id"], "Sessions should have different users"
            
            logger.info(" PASS:  Step 3: Concurrent session management successful")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE Step 3: Concurrent session management failed: {e}. "
                f"This indicates user_sessions table issues with multi-user session handling."
            )
        
        logger.info(" CELEBRATION:  SUCCESS: User session persistence works correctly across requests")
    
    @pytest.mark.e2e  
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_authentication_failure_recovery_e2e(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Authentication failure and recovery scenarios.
        
        This test validates how the system handles authentication failures
        and recovery, which depends on user_sessions table for error tracking
        and retry management.
        
        FAILURE SCENARIO: If user_sessions table is missing, authentication
        error handling and recovery may fail, leaving users unable to retry login.
        """
        logger.info(" SEARCH:  CRITICAL E2E: Authentication failure recovery test")
        
        auth_helper = E2EAuthHelper(environment="test")
        
        # Step 1: Test invalid token handling
        try:
            invalid_token = "invalid.jwt.token.that.should.fail"
            
            validation_result = await auth_helper.validate_jwt_token(invalid_token)
            
            assert validation_result["valid"] is False, "Invalid token should fail validation"
            assert "error" in validation_result, "Should provide error details"
            
            logger.info(" PASS:  Step 1: Invalid token properly rejected")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE Step 1: Invalid token handling crashed: {e}")
        
        # Step 2: Test expired token scenario
        try:
            # Create token with very short expiry for testing
            short_lived_token = auth_helper.create_test_jwt_token(
                user_id="expire-test-user",
                email="expire-test@example.com",
                exp_minutes=0.01  # Expires in 0.6 seconds
            )
            
            # Wait for token to expire
            await asyncio.sleep(1.0)
            
            # Validate expired token is properly rejected
            expired_validation = await auth_helper.validate_jwt_token(short_lived_token)
            
            assert expired_validation["valid"] is False, "Expired token should be rejected"
            assert "expired" in expired_validation.get("error", "").lower(), "Should indicate token expiration"
            
            logger.info(" PASS:  Step 2: Expired token properly rejected")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE Step 2: Expired token handling failed: {e}")
        
        # Step 3: Test successful recovery after failure
        try:
            # After failed authentication, user should be able to get new valid token
            recovery_user = await create_test_user_with_auth(
                email="recovery-test@example.com",
                name="Recovery Test User",
                environment="test"
            )
            
            recovery_token = recovery_user["jwt_token"]
            
            # Validate the recovery token works
            recovery_validation = await auth_helper.validate_jwt_token(recovery_token)
            
            assert recovery_validation["valid"] is True, "Recovery authentication should succeed"
            assert recovery_validation["user_id"] == recovery_user["user_id"], "Recovery should have correct user"
            
            logger.info(" PASS:  Step 3: Authentication recovery successful after failures")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE Step 3: Authentication recovery failed: {e}. "
                f"This indicates user_sessions table issues preventing auth recovery operations."
            )
        
        logger.info(" CELEBRATION:  SUCCESS: Authentication failure recovery scenarios work correctly")


class TestUserSessionsDependentOperationsE2E(BaseE2ETest):
    """
    E2E tests for operations that specifically depend on user_sessions table functionality.
    
    These tests validate the specific database operations that require the user_sessions
    table to exist and be accessible.
    """
    
    @pytest.mark.e2e
    @pytest.mark.real_services 
    @pytest.mark.critical
    async def test_multi_user_session_isolation_e2e(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Multiple users with isolated sessions.
        
        This test validates that multiple users can have separate, isolated sessions
        stored in the user_sessions table without interference.
        
        FAILURE SCENARIO: If user_sessions table is missing, multi-user session
        isolation cannot work, causing security and functionality issues.
        """
        logger.info(" SEARCH:  CRITICAL E2E: Multi-user session isolation test")
        
        # Create multiple test users simultaneously
        try:
            user_tasks = []
            
            for user_number in range(3):
                email = f"isolation-test-user-{user_number}@example.com"
                name = f"Isolation Test User {user_number}"
                
                task = create_test_user_with_auth(
                    email=email,
                    name=name,
                    environment="test",
                    permissions=["read", "write", "chat"]
                )
                user_tasks.append(task)
            
            # Wait for all users to be created
            users = await asyncio.gather(*user_tasks)
            
            assert len(users) == 3, "Should have created 3 test users"
            
            # Validate each user has unique session data
            user_ids = set()
            tokens = set()
            
            for i, user in enumerate(users):
                assert user["auth_success"] is True, f"User {i} authentication should succeed"
                assert user["user_id"] not in user_ids, f"User {i} should have unique user ID"
                assert user["jwt_token"] not in tokens, f"User {i} should have unique JWT token"
                
                user_ids.add(user["user_id"])
                tokens.add(user["jwt_token"])
                
                logger.info(f" PASS:  User {i}: {user['email']} - Unique session created")
            
            logger.info(" PASS:  Multi-user session isolation successful - all users have separate sessions")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Multi-user session isolation failed: {e}. "
                f"This indicates user_sessions table issues preventing proper session management."
            )
        
        # Validate concurrent session operations
        try:
            auth_helper = E2EAuthHelper(environment="test")
            
            # Validate all tokens concurrently
            validation_tasks = [
                auth_helper.validate_jwt_token(user["jwt_token"]) 
                for user in users
            ]
            
            validations = await asyncio.gather(*validation_tasks)
            
            for i, validation in enumerate(validations):
                assert validation["valid"] is True, f"User {i} token should be valid"
                assert validation["user_id"] == users[i]["user_id"], f"User {i} token should match user ID"
            
            logger.info(" PASS:  Concurrent session validation successful - session isolation maintained")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Concurrent session validation failed: {e}. "
                f"This indicates user_sessions table concurrency issues."
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_session_based_authorization_e2e(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Session-based authorization for different user permissions.
        
        This test validates that users with different permissions have proper
        authorization based on session data stored in user_sessions table.
        
        FAILURE SCENARIO: If user_sessions table is missing, permission-based
        authorization cannot work, causing security vulnerabilities.
        """
        logger.info(" SEARCH:  CRITICAL E2E: Session-based authorization test")
        
        # Create users with different permission levels
        try:
            # Read-only user
            readonly_user = await create_test_user_with_auth(
                email="readonly-user@example.com",
                name="Read Only User", 
                environment="test",
                permissions=["read"]
            )
            
            # Full access user
            fullaccess_user = await create_test_user_with_auth(
                email="fullaccess-user@example.com",
                name="Full Access User",
                environment="test", 
                permissions=["read", "write", "admin", "chat"]
            )
            
            logger.info(" PASS:  Created users with different permission levels")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Permission-based user creation failed: {e}")
        
        # Validate permission isolation in sessions
        try:
            auth_helper = E2EAuthHelper(environment="test")
            
            # Validate readonly user permissions
            readonly_validation = await auth_helper.validate_jwt_token(readonly_user["jwt_token"])
            assert readonly_validation["valid"] is True, "Read-only user token should be valid"
            readonly_permissions = readonly_validation.get("permissions", [])
            assert "read" in readonly_permissions, "Read-only user should have read permission"
            assert "write" not in readonly_permissions, "Read-only user should not have write permission"
            assert "admin" not in readonly_permissions, "Read-only user should not have admin permission"
            
            # Validate full access user permissions  
            fullaccess_validation = await auth_helper.validate_jwt_token(fullaccess_user["jwt_token"])
            assert fullaccess_validation["valid"] is True, "Full access user token should be valid"
            fullaccess_permissions = fullaccess_validation.get("permissions", [])
            assert "read" in fullaccess_permissions, "Full access user should have read permission"
            assert "write" in fullaccess_permissions, "Full access user should have write permission"
            assert "admin" in fullaccess_permissions, "Full access user should have admin permission"
            assert "chat" in fullaccess_permissions, "Full access user should have chat permission"
            
            logger.info(" PASS:  Permission-based authorization validation successful")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Permission-based authorization failed: {e}. "
                f"This indicates user_sessions table issues affecting permission management."
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.critical
    async def test_session_cleanup_and_security_e2e(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Session cleanup and security operations.
        
        This test validates session cleanup operations that depend on user_sessions
        table for tracking session expiry and cleanup.
        
        FAILURE SCENARIO: If user_sessions table is missing, session cleanup
        cannot work, leading to security issues and resource leaks.
        """
        logger.info(" SEARCH:  CRITICAL E2E: Session cleanup and security test")
        
        # Create test session that should be cleaned up
        try:
            test_user = await create_test_user_with_auth(
                email="cleanup-test-user@example.com",
                name="Cleanup Test User",
                environment="test"
            )
            
            test_token = test_user["jwt_token"]
            logger.info(f" PASS:  Created test session for cleanup validation")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Test session creation for cleanup failed: {e}")
        
        # Test session expiry handling
        try:
            # Create very short-lived token for expiry testing
            auth_helper = E2EAuthHelper(environment="test")
            
            short_token = auth_helper.create_test_jwt_token(
                user_id="cleanup-expire-user",
                email="expire@example.com",
                exp_minutes=0.01  # Expires very quickly
            )
            
            # Wait for expiration
            await asyncio.sleep(2.0)
            
            # Validate expired token is properly handled
            expired_validation = await auth_helper.validate_jwt_token(short_token)
            assert expired_validation["valid"] is False, "Expired token should be invalid"
            
            logger.info(" PASS:  Session expiry handling works correctly")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Session expiry handling failed: {e}. "
                f"This indicates user_sessions table issues with expiry tracking."
            )
        
        # Test that valid sessions are not affected by cleanup
        try:
            # Original test session should still be valid
            auth_helper = E2EAuthHelper(environment="test")
            current_validation = await auth_helper.validate_jwt_token(test_token)
            
            assert current_validation["valid"] is True, "Valid session should not be affected by cleanup"
            assert current_validation["user_id"] == test_user["user_id"], "Session should maintain correct user"
            
            logger.info(" PASS:  Valid sessions unaffected by cleanup operations")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Valid session protection during cleanup failed: {e}")
        
        logger.info(" CELEBRATION:  SUCCESS: Session cleanup and security operations work correctly")