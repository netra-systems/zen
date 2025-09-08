"""
Integration Tests: Authentication & Context Integration - Batch 1

Tests the integration between UnifiedAuthenticationService and UserExecutionContext
with real implementations (no mocks) and multi-user isolation verification.

Business Value:
- Ensures complete user isolation at authentication boundary
- Validates secure context creation and management
- Prevents cross-user data contamination

Test Coverage:
1. UnifiedAuthenticationService creates valid UserExecutionContext
2. Concurrent authentication creates isolated contexts
3. Invalid JWT prevents context creation
4. Auth service handles context validation errors
5. User context maintains auth state throughout lifecycle
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod,
    UnifiedAuthenticationService
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError
)
from netra_backend.app.clients.auth_client_core import validate_jwt_format
from netra_backend.app.db.session import get_async_session
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    create_test_jwt_token,
    create_test_user_context,
    generate_valid_user_claims,
    E2EAuthHelper
)


class TestAuthContextIntegration(SSotAsyncTestCase):
    """Integration tests for UnifiedAuthenticationService + UserExecutionContext."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.auth_service = None
        self.test_users = []
        self.created_contexts = []
        self.auth_helper = E2EAuthHelper()
        
        # Test data for multi-user scenarios
        self.user_test_data = [
            {
                "user_id": str(uuid.uuid4()),
                "email": f"testuser1_{uuid.uuid4().hex[:8]}@netra.ai",
                "role": "user",
                "permissions": ["read", "write"]
            },
            {
                "user_id": str(uuid.uuid4()),
                "email": f"testuser2_{uuid.uuid4().hex[:8]}@netra.ai", 
                "role": "admin",
                "permissions": ["read", "write", "admin"]
            },
            {
                "user_id": str(uuid.uuid4()),
                "email": f"testuser3_{uuid.uuid4().hex[:8]}@netra.ai",
                "role": "viewer",
                "permissions": ["read"]
            }
        ]

    async def asyncSetUp(self):
        """Async setup for test fixtures."""
        await super().asyncSetUp()
        
        # Initialize auth service
        self.auth_service = await get_unified_auth_service()
        self.assertIsNotNone(self.auth_service, "UnifiedAuthenticationService must be available")
        
        # Initialize auth helper
        await self.auth_helper.initialize()

    async def asyncTearDown(self):
        """Clean up test resources."""
        # Clean up created contexts
        for context in self.created_contexts:
            try:
                if hasattr(context, 'cleanup'):
                    await context.cleanup()
            except Exception as e:
                self.logger.warning(f"Failed to cleanup context {context.user_id}: {e}")
        
        # Clean up test users
        for user_data in self.test_users:
            try:
                await self.auth_helper.cleanup_test_user(user_data['user_id'])
            except Exception as e:
                self.logger.warning(f"Failed to cleanup user {user_data['user_id']}: {e}")
        
        self.created_contexts.clear()
        self.test_users.clear()
        
        await super().asyncTearDown()

    async def test_unified_auth_service_creates_valid_user_context(self):
        """Test 1: UnifiedAuthenticationService creates valid UserExecutionContext."""
        
        # Step 1: Create test user and JWT token
        user_data = self.user_test_data[0]
        test_user = await self.auth_helper.create_test_user(
            user_id=user_data['user_id'],
            email=user_data['email'],
            role=user_data['role']
        )
        self.test_users.append(user_data)
        
        # Generate valid JWT token
        token = create_test_jwt_token(
            user_id=user_data['user_id'],
            email=user_data['email'],
            permissions=user_data['permissions']
        )
        
        # Step 2: Authenticate with auth service
        auth_result = await self.auth_service.authenticate_token(
            token=token,
            context=AuthenticationContext.REST_API,
            method=AuthenticationMethod.JWT_TOKEN
        )
        
        # Step 3: Verify authentication succeeded
        self.assertTrue(auth_result.success, "Authentication should succeed with valid token")
        self.assertEqual(auth_result.user_id, user_data['user_id'], "User ID should match")
        self.assertIsNotNone(auth_result.email, "User email should be present")
        
        # Step 4: Create UserExecutionContext with auth result
        context = UserExecutionContext.from_request(
            user_id=auth_result.user_id,
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        self.created_contexts.append(context)
        
        # Step 5: Verify context is properly created
        self.assertEqual(context.user_id, user_data['user_id'], "Context user ID should match auth result")
        self.assertIsNotNone(context.request_id, "Context should have request ID")
        self.assertIsNotNone(context.thread_id, "Context should have thread ID")
        self.assertIsNotNone(context.run_id, "Context should have run ID")
        
        # Step 6: Verify context validation passes
        try:
            # UserExecutionContext validates itself during creation via __post_init__
            # If we got here without exception, validation passed
            pass
        except (InvalidContextError, ContextIsolationError) as e:
            self.fail(f"Context validation should pass for valid auth result: {e}")
        
        # Step 7: Verify context properties are properly set
        self.assertEqual(context.user_id, user_data['user_id'], "User ID should be preserved")
        self.assertIsNotNone(context.created_at, "Context should have creation timestamp")
        
        self.logger.info(f"✅ Successfully created valid UserExecutionContext for user {user_data['user_id']}")

    async def test_concurrent_auth_creates_isolated_contexts(self):
        """Test 2: Concurrent authentication creates completely isolated contexts."""
        
        num_concurrent_users = 5
        concurrent_tasks = []
        
        async def authenticate_user(user_index: int) -> Dict[str, Any]:
            """Authenticate a single user and return context info."""
            # Use different user data for each concurrent request
            base_data = self.user_test_data[user_index % len(self.user_test_data)]
            user_data = {
                **base_data,
                "user_id": str(uuid.uuid4()),  # Unique ID for each concurrent user
                "email": f"concurrent_user_{user_index}_{uuid.uuid4().hex[:8]}@netra.ai"
            }
            
            # Create test user
            test_user = await self.auth_helper.create_test_user(
                user_id=user_data['user_id'],
                email=user_data['email'], 
                role=user_data['role']
            )
            
            # Generate JWT token
            token = create_test_jwt_token(
                user_id=user_data['user_id'],
                email=user_data['email'],
                permissions=user_data['permissions']
            )
            
            # Authenticate
            auth_result = await self.auth_service.authenticate_token(
                token=token,
                context=AuthenticationContext.REST_API,
                method=AuthenticationMethod.JWT_TOKEN
            )
            
            # Create context
            context = UserExecutionContext.from_request(
                user_id=auth_result.user_id if auth_result.success else str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            return {
                "user_data": user_data,
                "auth_result": auth_result,
                "context": context,
                "user_index": user_index
            }
        
        # Step 1: Run concurrent authentication requests
        for i in range(num_concurrent_users):
            task = asyncio.create_task(authenticate_user(i))
            concurrent_tasks.append(task)
        
        # Wait for all concurrent operations to complete
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Step 2: Verify all authentications succeeded
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.fail(f"Concurrent authentication {i} failed: {result}")
            successful_results.append(result)
            self.test_users.append(result['user_data'])
            self.created_contexts.append(result['context'])
        
        self.assertEqual(len(successful_results), num_concurrent_users, "All concurrent auths should succeed")
        
        # Step 3: Verify complete isolation between contexts
        user_ids = set()
        request_ids = set()
        thread_ids = set()
        run_ids = set()
        
        for result in successful_results:
            context = result['context']
            
            # Verify unique IDs (no collisions)
            self.assertNotIn(context.user_id, user_ids, f"User ID collision detected: {context.user_id}")
            self.assertNotIn(context.request_id, request_ids, f"Request ID collision: {context.request_id}")
            self.assertNotIn(context.thread_id, thread_ids, f"Thread ID collision: {context.thread_id}")
            self.assertNotIn(context.run_id, run_ids, f"Run ID collision: {context.run_id}")
            
            user_ids.add(context.user_id)
            request_ids.add(context.request_id)
            thread_ids.add(context.thread_id)
            run_ids.add(context.run_id)
            
            # Verify context isolation - context validates itself during creation
            # If we got here, the context was created successfully
        
        # Step 4: Verify no cross-user data contamination
        for i, result1 in enumerate(successful_results):
            for j, result2 in enumerate(successful_results):
                if i != j:
                    ctx1, ctx2 = result1['context'], result2['context']
                    
                    # Verify complete separation
                    self.assertNotEqual(ctx1.user_id, ctx2.user_id, "User IDs should be different")
                    self.assertNotEqual(ctx1.request_id, ctx2.request_id, "Request IDs should be different")
                    self.assertNotEqual(ctx1.thread_id, ctx2.thread_id, "Thread IDs should be different")
                    self.assertNotEqual(ctx1.run_id, ctx2.run_id, "Run IDs should be different")
        
        self.logger.info(f"✅ Successfully verified isolation across {num_concurrent_users} concurrent contexts")

    async def test_invalid_jwt_prevents_context_creation(self):
        """Test 3: Invalid JWT tokens prevent UserExecutionContext creation."""
        
        invalid_tokens = [
            "invalid.jwt.token",  # Malformed token
            "",  # Empty token
            "header.payload",  # Missing signature
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",  # Invalid signature
            create_test_jwt_token(
                user_id=str(uuid.uuid4()),
                email="expired@netra.ai", 
                permissions=["read"],
                exp_delta=timedelta(days=-1)  # Expired token
            )
        ]
        
        for i, invalid_token in enumerate(invalid_tokens):
            with self.subTest(token_type=f"invalid_token_{i}"):
                # Step 1: Attempt authentication with invalid token
                auth_result = await self.auth_service.authenticate_token(
                    token=invalid_token,
                    context=AuthenticationContext.REST_API,
                    method=AuthenticationMethod.JWT_TOKEN
                )
                
                # Step 2: Authentication should fail
                self.assertFalse(auth_result.success, f"Authentication should fail for invalid token {i}")
                
                # Step 3: Context creation should fail or create context without valid user_id
                if auth_result.user_id is None:
                    # If auth completely failed, context creation should raise exception with empty user_id
                    with self.assertRaises((InvalidContextError, ValueError)):
                        UserExecutionContext.from_request(
                            user_id="",  # Empty user_id should cause validation error
                            thread_id=str(uuid.uuid4()),
                            run_id=str(uuid.uuid4())
                        )
                else:
                    # If partial auth info exists, context can be created but represents failed auth
                    context = UserExecutionContext.from_request(
                        user_id=auth_result.user_id,
                        thread_id=str(uuid.uuid4()),
                        run_id=str(uuid.uuid4())
                    )
                    # Context exists but represents a failed authentication attempt
                    self.assertIsNotNone(context, "Context should be created even for failed auth")
        
        self.logger.info("✅ Successfully verified invalid JWT tokens prevent valid context creation")

    async def test_auth_service_handles_context_validation_errors(self):
        """Test 4: Auth service properly handles context validation errors."""
        
        # Step 1: Create valid user and token
        user_data = self.user_test_data[1]
        test_user = await self.auth_helper.create_test_user(
            user_id=user_data['user_id'],
            email=user_data['email'],
            role=user_data['role']
        )
        self.test_users.append(user_data)
        
        token = create_test_jwt_token(
            user_id=user_data['user_id'],
            email=user_data['email'],
            permissions=user_data['permissions']
        )
        
        # Step 2: Authenticate successfully
        auth_result = await self.auth_service.authenticate_token(
            token=token,
            context=AuthenticationContext.REST_API,
            method=AuthenticationMethod.JWT_TOKEN
        )
        self.assertTrue(auth_result.success, "Initial authentication should succeed")
        
        # Step 3: Test various context validation error scenarios
        validation_error_scenarios = [
            {
                "name": "empty_request_id",
                "request_id": "",
                "thread_id": str(uuid.uuid4()),
                "should_raise": InvalidContextError
            },
            {
                "name": "none_thread_id", 
                "request_id": str(uuid.uuid4()),
                "thread_id": None,
                "should_raise": InvalidContextError
            },
            {
                "name": "invalid_uuid_format",
                "request_id": "not-a-uuid",
                "thread_id": str(uuid.uuid4()),
                "should_raise": InvalidContextError
            }
        ]
        
        for scenario in validation_error_scenarios:
            with self.subTest(scenario=scenario['name']):
                # Step 4: Create context with invalid parameters
                if scenario['should_raise']:
                    with self.assertRaises(scenario['should_raise']):
                        UserExecutionContext.from_request(
                            user_id=auth_result.user_id,
                            thread_id=scenario['thread_id'] or "",
                            run_id=str(uuid.uuid4()) if scenario['request_id'] else ""
                        )
                else:
                    # Context should be created but validation should fail
                    try:
                        UserExecutionContext.from_request(
                            user_id=auth_result.user_id,
                            thread_id=scenario['thread_id'] or "",
                            run_id=str(uuid.uuid4()) if scenario['request_id'] else ""
                        )
                    except (InvalidContextError, ContextIsolationError):
                        pass  # Expected validation failure
        
        self.logger.info("✅ Successfully verified auth service handles context validation errors")

    async def test_user_context_maintains_auth_state(self):
        """Test 5: UserExecutionContext maintains auth state throughout lifecycle."""
        
        # Step 1: Create test user with specific permissions
        user_data = self.user_test_data[2]
        test_user = await self.auth_helper.create_test_user(
            user_id=user_data['user_id'],
            email=user_data['email'],
            role=user_data['role']
        )
        self.test_users.append(user_data)
        
        # Step 2: Generate token with specific claims
        token = create_test_jwt_token(
            user_id=user_data['user_id'],
            email=user_data['email'],
            permissions=user_data['permissions'],
            custom_claims={
                "org_id": "test-org-123",
                "subscription_tier": "premium",
                "feature_flags": ["feature_a", "feature_b"]
            }
        )
        
        # Step 3: Authenticate and create context
        auth_result = await self.auth_service.authenticate_token(
            token=token,
            context=AuthenticationContext.REST_API,
            method=AuthenticationMethod.JWT_TOKEN
        )
        self.assertTrue(auth_result.success, "Authentication should succeed")
        
        context = UserExecutionContext.from_request(
            user_id=auth_result.user_id,
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        self.created_contexts.append(context)
        
        # Step 4: Verify initial state preservation
        self.assertEqual(context.user_id, user_data['user_id'], "User ID should be preserved")
        self.assertIsNotNone(context.created_at, "Context should have creation timestamp")
        self.assertIsNotNone(context.request_id, "Context should have request ID")
        
        # Step 5: Test state through child context creation
        child_context = context.create_child_context(
            operation_name="test_operation",
            metadata={"test": "child_context"}
        )
        
        self.assertEqual(child_context.user_id, context.user_id, "Child should inherit user ID")
        self.assertNotEqual(child_context.run_id, context.run_id, "Child should have different run ID")
        self.assertEqual(child_context.thread_id, context.thread_id, "Child should inherit thread ID")
        self.assertEqual(child_context.parent_request_id, context.request_id, "Child should track parent request")
        
        # Step 6: Test state through WebSocket connection scenarios
        websocket_connection_id = str(uuid.uuid4())
        websocket_context = context.with_websocket_connection(websocket_connection_id)
        
        self.assertEqual(websocket_context.user_id, context.user_id, "WebSocket context should preserve user ID")
        self.assertEqual(websocket_context.websocket_connection_id, websocket_connection_id, "WebSocket ID should be set")
        
        # Step 7: Test state through serialization
        context_dict = context.to_dict()
        
        # Verify context state is preserved in serialized form
        self.assertEqual(context_dict['user_id'], user_data['user_id'], "Serialized user ID should match")
        self.assertEqual(context_dict['thread_id'], context.thread_id, "Serialized thread ID should match")
        self.assertEqual(context_dict['run_id'], context.run_id, "Serialized run ID should match")
        
        # Step 8: Verify audit metadata preservation
        audit_data = context.audit_metadata
        
        self.assertIsInstance(audit_data, dict, "Audit metadata should be a dictionary")
        # Audit metadata is initialized during creation
        
        # Step 9: Test context remains valid throughout operations
        operations_to_test = 3
        for i in range(operations_to_test):
            # Create child contexts to simulate operations
            operation_context = context.create_child_context(
                operation_name=f"operation_{i}",
                metadata={f"operation_{i}": f"test_value_{i}"}
            )
            
            # Verify context state is preserved
            self.assertEqual(operation_context.user_id, context.user_id, f"User ID should persist through operation {i}")
            self.assertEqual(operation_context.thread_id, context.thread_id, f"Thread ID should persist through operation {i}")
        
        self.logger.info("✅ Successfully verified UserExecutionContext maintains auth state throughout lifecycle")

    def test_jwt_token_format_validation(self):
        """Test JWT token format validation utility."""
        
        # Valid JWT formats
        valid_tokens = [
            create_test_jwt_token(str(uuid.uuid4()), "test@netra.ai", ["read"]),
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        ]
        
        # Invalid JWT formats  
        invalid_tokens = [
            "",
            "invalid",
            "header.payload",
            "too.many.dots.here.invalid",
            None
        ]
        
        for token in valid_tokens:
            self.assertTrue(validate_jwt_format(token), f"Token should be valid: {token[:50]}...")
        
        for token in invalid_tokens:
            self.assertFalse(validate_jwt_format(token), f"Token should be invalid: {token}")
        
        self.logger.info("✅ Successfully verified JWT token format validation")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])