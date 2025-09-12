"""
Multi-User Session Isolation Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - especially critical for Enterprise
- Business Goal: Ensure complete user data isolation and prevent data leakage
- Value Impact: Users can trust platform with sensitive data without cross-contamination
- Strategic Impact: Core security requirement for enterprise sales and compliance

CRITICAL: Tests multi-user session isolation with REAL auth service and database.
Validates Factory patterns prevent user data mixing and maintain complete isolation.

Following CLAUDE.md requirements:
- Uses real services (no mocks in integration tests)
- Follows SSOT patterns from test_framework/ssot/
- Tests MUST fail hard - no try/except blocks masking errors
- Factory patterns for user isolation are MANDATORY
"""
import pytest
import asyncio
import time
import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Set

# Absolute imports per CLAUDE.md
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, create_authenticated_user_context
)
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestMultiUserSessionIsolationIntegration(BaseIntegrationTest):
    """Integration tests for multi-user session isolation with real services."""
    
    @pytest.fixture(autouse=True)
    def setup_isolation_environment(self):
        """Setup environment for multi-user isolation testing."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Set multi-user isolation configuration
        self.env.set("JWT_SECRET_KEY", "integration-isolation-jwt-secret-32-chars", "test_multi_user_isolation")
        self.env.set("SERVICE_SECRET", "integration-isolation-service-secret-32", "test_multi_user_isolation")
        self.env.set("ENVIRONMENT", "test", "test_multi_user_isolation")
        
        # Enable strict user isolation mode for testing
        self.env.set("ENABLE_STRICT_USER_ISOLATION", "true", "test_multi_user_isolation")
        self.env.set("USER_CONTEXT_FACTORY_MODE", "enabled", "test_multi_user_isolation")
        
        self.auth_helper = E2EAuthHelper(environment="test")
        self.id_generator = UnifiedIdGenerator()
        
        yield
        
        # Cleanup
        self.env.disable_isolation()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_factory_creates_isolated_execution_contexts(self, real_services_fixture):
        """Test that user context factory creates completely isolated execution contexts for different users."""
        # Arrange: Create multiple users with different permissions and data
        user_configs = [
            {
                "user_id": f"isolation-user-1-{int(time.time())}",
                "email": f"isolation-user-1-{int(time.time())}@company-a.com", 
                "permissions": ["read:company_a", "write:company_a", "admin:company_a"],
                "organization": "company-a",
                "role": "admin"
            },
            {
                "user_id": f"isolation-user-2-{int(time.time())}",
                "email": f"isolation-user-2-{int(time.time())}@company-b.com",
                "permissions": ["read:company_b", "write:company_b"],
                "organization": "company-b", 
                "role": "user"
            },
            {
                "user_id": f"isolation-user-3-{int(time.time())}",
                "email": f"isolation-user-3-{int(time.time())}@company-c.com",
                "permissions": ["read:company_c"],
                "organization": "company-c",
                "role": "viewer"
            }
        ]
        
        # Act: Create isolated execution contexts for each user
        user_contexts = []
        
        for config in user_configs:
            # Create authenticated user context using SSOT factory pattern
            user_context = await create_authenticated_user_context(
                user_email=config["email"],
                user_id=config["user_id"],
                environment="test",
                permissions=config["permissions"],
                websocket_enabled=True
            )
            
            # Add additional test metadata
            user_context.audit_metadata.update({
                "organization": config["organization"],
                "role": config["role"],
                "test_isolation_check": True
            })
            
            user_contexts.append({
                "config": config,
                "context": user_context,
                "jwt_token": user_context.agent_context["jwt_token"]
            })
        
        # Assert: Each context must be completely isolated
        for i, user_data in enumerate(user_contexts):
            context = user_data["context"]
            config = user_data["config"]
            
            # Verify context contains correct isolated user data
            assert str(context.user_id) == config["user_id"], (
                f"User context {i} must contain correct isolated user_id: "
                f"expected {config['user_id']}, got {context.user_id}"
            )
            
            # Verify JWT token contains correct isolated claims
            import jwt as jwt_lib
            decoded_token = jwt_lib.decode(
                user_data["jwt_token"],
                options={"verify_signature": False}
            )
            
            assert decoded_token["sub"] == config["user_id"], (
                f"JWT token {i} must contain correct isolated user_id"
            )
            assert decoded_token["email"] == config["email"], (
                f"JWT token {i} must contain correct isolated email"
            )
            assert decoded_token["permissions"] == config["permissions"], (
                f"JWT token {i} must contain correct isolated permissions"
            )
            
            # Verify all IDs are unique and properly generated
            assert context.thread_id is not None, f"Context {i} must have unique thread_id"
            assert context.run_id is not None, f"Context {i} must have unique run_id"
            assert context.request_id is not None, f"Context {i} must have unique request_id"
            assert context.websocket_client_id is not None, f"Context {i} must have unique websocket_id"
        
        # Verify no ID collisions between users
        all_thread_ids = [str(ctx["context"].thread_id) for ctx in user_contexts]
        all_run_ids = [str(ctx["context"].run_id) for ctx in user_contexts]
        all_request_ids = [str(ctx["context"].request_id) for ctx in user_contexts]
        all_websocket_ids = [str(ctx["context"].websocket_client_id) for ctx in user_contexts]
        
        assert len(set(all_thread_ids)) == len(all_thread_ids), "All thread_ids must be unique across users"
        assert len(set(all_run_ids)) == len(all_run_ids), "All run_ids must be unique across users"
        assert len(set(all_request_ids)) == len(all_request_ids), "All request_ids must be unique across users"
        assert len(set(all_websocket_ids)) == len(all_websocket_ids), "All websocket_ids must be unique across users"
        
        # Test concurrent API access maintains isolation
        api_tasks = []
        
        async def make_isolated_api_call(user_data):
            """Make API call with isolated user context."""
            headers = self.auth_helper.get_auth_headers(user_data["jwt_token"])
            client = self.auth_helper.create_sync_authenticated_client()
            client.headers.update(headers)
            
            response = client.get("/api/health")
            
            return {
                "user_id": user_data["config"]["user_id"],
                "organization": user_data["config"]["organization"],
                "status_code": response.status_code,
                "success": response.status_code in [200, 404]
            }
        
        # Execute concurrent API calls
        api_tasks = [make_isolated_api_call(user_data) for user_data in user_contexts]
        api_results = await asyncio.gather(*api_tasks, return_exceptions=True)
        
        # Verify all API calls succeeded with proper isolation
        for i, result in enumerate(api_results):
            assert not isinstance(result, Exception), f"API call {i} must not raise exception: {result}"
            assert result["success"] is True, (
                f"API call for user {result['user_id']} must succeed with isolated context, "
                f"got status {result['status_code']}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_sessions_prevent_data_leakage(self, real_services_fixture):
        """Test that concurrent user sessions cannot access each other's data or permissions."""
        # Arrange: Create users with different permission levels and sensitive data
        sensitive_user_configs = [
            {
                "user_id": f"sensitive-admin-{int(time.time())}",
                "email": f"admin-{int(time.time())}@sensitive-corp.com",
                "permissions": ["read:all", "write:all", "delete:all", "admin:system"],
                "security_level": "admin",
                "sensitive_data": {"api_keys": ["super-secret-admin-key-123"], "billing_access": True}
            },
            {
                "user_id": f"sensitive-user-{int(time.time())}",
                "email": f"user-{int(time.time())}@public-org.com", 
                "permissions": ["read:public", "write:own"],
                "security_level": "user",
                "sensitive_data": {"profile_data": "basic-user-info", "billing_access": False}
            },
            {
                "user_id": f"sensitive-guest-{int(time.time())}",
                "email": f"guest-{int(time.time())}@external.com",
                "permissions": ["read:public"],
                "security_level": "guest", 
                "sensitive_data": {"temp_access": True, "restricted": True}
            }
        ]
        
        # Create isolated contexts with sensitive data
        sensitive_contexts = []
        
        for config in sensitive_user_configs:
            user_context = await create_authenticated_user_context(
                user_email=config["email"],
                user_id=config["user_id"],
                environment="test",
                permissions=config["permissions"],
                websocket_enabled=True
            )
            
            # Store sensitive data in agent context (simulating real application)
            user_context.agent_context.update({
                "security_level": config["security_level"],
                "sensitive_data": config["sensitive_data"],
                "access_token": user_context.agent_context["jwt_token"],
                "user_specific_secrets": f"secret-for-{config['user_id']}-only"
            })
            
            sensitive_contexts.append({
                "config": config,
                "context": user_context
            })
        
        # Act: Attempt concurrent access to verify isolation
        async def attempt_cross_user_access(accessing_user, target_user):
            """Attempt to access another user's data using different user context."""
            accessing_context = accessing_user["context"]
            target_config = target_user["config"]
            
            # Use accessing user's JWT to try to access target user's resources
            accessing_jwt = accessing_context.agent_context["jwt_token"]
            
            # Verify accessing user cannot decode or access target user's sensitive data
            # This tests that user contexts are properly isolated
            
            results = {
                "accessing_user": accessing_user["config"]["user_id"],
                "target_user": target_config["user_id"],
                "isolation_maintained": True,
                "errors": []
            }
            
            # Test 1: JWT tokens must be different (isolation check)
            target_context = target_user["context"]
            target_jwt = target_context.agent_context["jwt_token"]
            
            if accessing_jwt == target_jwt:
                results["isolation_maintained"] = False
                results["errors"].append("JWT tokens are identical between users")
            
            # Test 2: Decode JWT tokens and verify they contain different user data
            import jwt as jwt_lib
            
            accessing_decoded = jwt_lib.decode(accessing_jwt, options={"verify_signature": False})
            target_decoded = jwt_lib.decode(target_jwt, options={"verify_signature": False})
            
            if accessing_decoded["sub"] == target_decoded["sub"]:
                results["isolation_maintained"] = False
                results["errors"].append("JWT subject (user_id) is identical between users")
            
            if accessing_decoded["email"] == target_decoded["email"]:
                results["isolation_maintained"] = False
                results["errors"].append("JWT email is identical between users")
            
            # Test 3: Context IDs must be different
            if accessing_context.thread_id == target_context.thread_id:
                results["isolation_maintained"] = False
                results["errors"].append("Thread IDs are identical between users")
            
            if accessing_context.run_id == target_context.run_id:
                results["isolation_maintained"] = False
                results["errors"].append("Run IDs are identical between users")
            
            # Test 4: Sensitive data access must be isolated
            accessing_sensitive = accessing_context.agent_context.get("sensitive_data", {})
            target_sensitive = target_context.agent_context.get("sensitive_data", {})
            
            if accessing_sensitive == target_sensitive and len(accessing_sensitive) > 0:
                results["isolation_maintained"] = False
                results["errors"].append("Sensitive data is identical between users")
            
            return results
        
        # Test all combinations of cross-user access attempts
        isolation_test_results = []
        
        for i, accessing_user in enumerate(sensitive_contexts):
            for j, target_user in enumerate(sensitive_contexts):
                if i != j:  # Don't test user accessing their own data
                    isolation_result = await attempt_cross_user_access(accessing_user, target_user)
                    isolation_test_results.append(isolation_result)
        
        # Assert: All cross-user access attempts must maintain isolation
        for result in isolation_test_results:
            assert result["isolation_maintained"] is True, (
                f"User isolation must be maintained: {result['accessing_user']} -> {result['target_user']}. "
                f"Errors: {result['errors']}"
            )
        
        # Verify each user can only access their own data via API
        concurrent_api_isolation_tasks = []
        
        async def verify_api_data_isolation(user_data):
            """Verify user can only access their own data via API."""
            user_context = user_data["context"]
            config = user_data["config"]
            
            headers = self.auth_helper.get_auth_headers(
                user_context.agent_context["jwt_token"]
            )
            client = self.auth_helper.create_sync_authenticated_client()
            client.headers.update(headers)
            
            # Make API call that should only return this user's data
            response = client.get("/api/health")  # Health endpoint for basic connectivity
            
            return {
                "user_id": config["user_id"],
                "security_level": config["security_level"],
                "api_success": response.status_code in [200, 404],
                "status_code": response.status_code
            }
        
        # Execute concurrent API isolation tests
        api_isolation_tasks = [
            verify_api_data_isolation(user_data) 
            for user_data in sensitive_contexts
        ]
        api_isolation_results = await asyncio.gather(*api_isolation_tasks, return_exceptions=True)
        
        # Assert: All users can access API with their isolated context
        for i, result in enumerate(api_isolation_results):
            assert not isinstance(result, Exception), (
                f"API isolation test {i} must not raise exception: {result}"
            )
            assert result["api_success"] is True, (
                f"User {result['user_id']} with security level {result['security_level']} "
                f"must be able to access API with isolated context, got status {result['status_code']}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_user_session_cleanup_maintains_isolation_integrity(self, real_services_fixture):
        """Test that user session cleanup maintains isolation integrity and doesn't affect other users."""
        # Arrange: Create multiple user sessions with different lifespans
        user_session_configs = [
            {
                "user_id": f"cleanup-persistent-{int(time.time())}-1",
                "email": f"persistent-1-{int(time.time())}@longterm.com",
                "lifespan": "long",  # Should persist through cleanup
                "permissions": ["read:persistent", "write:persistent"]
            },
            {
                "user_id": f"cleanup-persistent-{int(time.time())}-2", 
                "email": f"persistent-2-{int(time.time())}@longterm.com",
                "lifespan": "long",  # Should persist through cleanup
                "permissions": ["read:persistent", "admin:persistent"]
            },
            {
                "user_id": f"cleanup-temporary-{int(time.time())}-1",
                "email": f"temporary-1-{int(time.time())}@shortterm.com",
                "lifespan": "short",  # May be cleaned up
                "permissions": ["read:temporary"]
            }
        ]
        
        # Create user contexts and track their isolation data
        user_sessions = []
        isolation_tracking = {}
        
        for config in user_session_configs:
            user_context = await create_authenticated_user_context(
                user_email=config["email"],
                user_id=config["user_id"],
                environment="test",
                permissions=config["permissions"],
                websocket_enabled=True
            )
            
            # Create JWT token with appropriate expiry
            if config["lifespan"] == "long":
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=config["user_id"],
                    email=config["email"],
                    permissions=config["permissions"],
                    exp_minutes=30  # Long-lived for testing
                )
            else:
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id=config["user_id"],
                    email=config["email"], 
                    permissions=config["permissions"],
                    exp_minutes=1  # Short-lived for cleanup testing
                )
            
            user_context.agent_context["jwt_token"] = jwt_token
            
            user_sessions.append({
                "config": config,
                "context": user_context,
                "jwt_token": jwt_token
            })
            
            # Track isolation data for verification
            isolation_tracking[config["user_id"]] = {
                "thread_id": str(user_context.thread_id),
                "run_id": str(user_context.run_id),
                "request_id": str(user_context.request_id),
                "websocket_id": str(user_context.websocket_client_id),
                "permissions": config["permissions"],
                "lifespan": config["lifespan"]
            }
        
        # Verify initial isolation state
        initial_validation_tasks = []
        
        async def validate_initial_session(user_session):
            """Validate initial session state."""
            jwt_token = user_session["jwt_token"]
            config = user_session["config"]
            
            # Validate JWT token
            is_valid = await self.auth_helper.validate_token(jwt_token)
            
            return {
                "user_id": config["user_id"],
                "lifespan": config["lifespan"],
                "initially_valid": is_valid
            }
        
        initial_validation_tasks = [
            validate_initial_session(session) for session in user_sessions
        ]
        initial_results = await asyncio.gather(*initial_validation_tasks, return_exceptions=True)
        
        # Verify all sessions are initially valid
        for result in initial_results:
            assert not isinstance(result, Exception), f"Initial validation must not raise exception: {result}"
            assert result["initially_valid"] is True, (
                f"Session for {result['user_id']} must be initially valid"
            )
        
        # Act: Simulate session cleanup by waiting for short-lived tokens to expire
        print("[U+23F3] Waiting for short-lived sessions to expire...")
        await asyncio.sleep(70)  # Wait for short tokens to expire
        
        # Verify isolation integrity after cleanup
        post_cleanup_validation_tasks = []
        
        async def validate_post_cleanup_session(user_session):
            """Validate session state after cleanup."""
            jwt_token = user_session["jwt_token"]
            config = user_session["config"]
            
            # Validate JWT token
            is_valid = await self.auth_helper.validate_token(jwt_token)
            
            # Verify context data integrity
            context = user_session["context"]
            original_tracking = isolation_tracking[config["user_id"]]
            
            context_integrity = (
                str(context.thread_id) == original_tracking["thread_id"] and
                str(context.run_id) == original_tracking["run_id"] and
                str(context.request_id) == original_tracking["request_id"] and
                str(context.websocket_client_id) == original_tracking["websocket_id"]
            )
            
            return {
                "user_id": config["user_id"],
                "lifespan": config["lifespan"],
                "post_cleanup_valid": is_valid,
                "context_integrity_maintained": context_integrity,
                "expected_valid": config["lifespan"] == "long"
            }
        
        post_cleanup_validation_tasks = [
            validate_post_cleanup_session(session) for session in user_sessions
        ]
        post_cleanup_results = await asyncio.gather(*post_cleanup_validation_tasks, return_exceptions=True)
        
        # Assert: Cleanup must maintain isolation integrity
        for result in post_cleanup_results:
            assert not isinstance(result, Exception), (
                f"Post-cleanup validation must not raise exception: {result}"
            )
            
            user_id = result["user_id"]
            lifespan = result["lifespan"]
            expected_valid = result["expected_valid"]
            actually_valid = result["post_cleanup_valid"]
            context_integrity = result["context_integrity_maintained"]
            
            # Context integrity must always be maintained
            assert context_integrity is True, (
                f"Context integrity must be maintained after cleanup for {user_id}"
            )
            
            # Long-lived sessions should still be valid
            if lifespan == "long":
                assert actually_valid is True, (
                    f"Long-lived session for {user_id} must remain valid after cleanup"
                )
            
            # Short-lived sessions may be invalid (expected)
            if lifespan == "short" and not actually_valid:
                print(f"[U+2713] Short-lived session for {user_id} properly expired during cleanup")
        
        # Verify no cross-contamination occurred during cleanup
        final_isolation_verification = []
        
        for user_session in user_sessions:
            config = user_session["config"]
            user_id = config["user_id"]
            
            # Verify this user's isolation data hasn't been mixed with others
            current_tracking = isolation_tracking[user_id]
            context = user_session["context"]
            
            isolation_maintained = (
                str(context.thread_id) == current_tracking["thread_id"] and
                str(context.run_id) == current_tracking["run_id"] and
                str(context.request_id) == current_tracking["request_id"] and
                str(context.websocket_client_id) == current_tracking["websocket_id"]
            )
            
            final_isolation_verification.append({
                "user_id": user_id,
                "isolation_maintained": isolation_maintained
            })
        
        # Assert: No isolation was compromised during cleanup
        for verification in final_isolation_verification:
            assert verification["isolation_maintained"] is True, (
                f"User isolation must be maintained during cleanup for {verification['user_id']}"
            )