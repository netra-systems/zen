#!/usr/bin/env python3
"""
Simple standalone test to verify UnifiedAuthenticationService + UserExecutionContext integration.

This bypasses the problematic test infrastructure to focus on core functionality.
"""

import asyncio
import sys
import os
import uuid
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_basic_auth_integration():
    """Test basic authentication and context creation."""
    
    try:
        # Test 1: Import the required modules
        print("Testing imports...")
        
        from netra_backend.app.services.unified_authentication_service import (
            get_unified_auth_service,
            AuthResult,
            AuthenticationContext,
            AuthenticationMethod,
            UnifiedAuthenticationService
        )
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.clients.auth_client_core import validate_jwt_format
        
        print("PASS: Imports successful")
        
        # Test 2: Create authentication service
        print("Testing authentication service creation...")
        auth_service = get_unified_auth_service()
        assert auth_service is not None, "Auth service should be created"
        print("PASS: Authentication service created")
        
        # Test 3: Test JWT format validation
        print("Testing JWT format validation...")
        
        # Valid JWT format (dummy)
        valid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        assert validate_jwt_format(valid_jwt) == True, "Valid JWT should pass format check"
        
        # Invalid JWT formats
        invalid_jwts = ["", "invalid", "header.payload", None]
        for invalid_jwt in invalid_jwts:
            assert validate_jwt_format(invalid_jwt) == False, f"Invalid JWT should fail: {invalid_jwt}"
        
        print("PASS: JWT format validation working")
        
        # Test 4: Test authentication with invalid token (should fail gracefully)
        print("Testing authentication with invalid token...")
        auth_result = await auth_service.authenticate_token(
            token="invalid.jwt.token",
            context=AuthenticationContext.REST_API,
            method=AuthenticationMethod.JWT_TOKEN
        )
        assert auth_result.success == False, "Invalid token should fail authentication"
        print("PASS: Invalid authentication handled correctly")
        
        # Test 5: Test UserExecutionContext creation
        print("Testing UserExecutionContext creation...")
        
        test_user_id = str(uuid.uuid4())
        test_thread_id = str(uuid.uuid4())
        test_run_id = str(uuid.uuid4())
        
        context = UserExecutionContext.from_request(
            user_id=test_user_id,
            thread_id=test_thread_id,
            run_id=test_run_id
        )
        
        assert context.user_id == test_user_id, "User ID should match"
        assert context.thread_id == test_thread_id, "Thread ID should match"
        assert context.run_id == test_run_id, "Run ID should match"
        assert context.request_id is not None, "Request ID should be generated"
        assert context.created_at is not None, "Created timestamp should be set"
        
        print("PASS: UserExecutionContext creation working")
        
        # Test 6: Test context serialization
        print("Testing context serialization...")
        
        context_dict = context.to_dict()
        assert context_dict['user_id'] == test_user_id, "Serialized user ID should match"
        assert context_dict['thread_id'] == test_thread_id, "Serialized thread ID should match"
        assert context_dict['run_id'] == test_run_id, "Serialized run ID should match"
        
        print("PASS: Context serialization working")
        
        # Test 7: Test child context creation
        print("Testing child context creation...")
        
        child_context = context.create_child_context(
            operation_name="test_operation",
            additional_agent_context={"test": "value"}
        )
        
        assert child_context.user_id == context.user_id, "Child should inherit user ID"
        assert child_context.thread_id == context.thread_id, "Child should inherit thread ID"
        assert child_context.request_id != context.request_id, "Child should have different request ID"
        assert child_context.parent_request_id == context.request_id, "Child should track parent"
        assert child_context.operation_depth == context.operation_depth + 1, "Child should be one level deeper"
        
        print("PASS: Child context creation working")
        
        # Test 8: Test concurrent contexts (isolation)
        print("Testing concurrent context isolation...")
        
        async def create_isolated_context(index: int):
            """Create an isolated context for testing."""
            return UserExecutionContext.from_request(
                user_id=f"user_{index}_{uuid.uuid4()}",
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
        
        # Create 3 concurrent contexts
        concurrent_tasks = [
            asyncio.create_task(create_isolated_context(i))
            for i in range(3)
        ]
        
        concurrent_contexts = await asyncio.gather(*concurrent_tasks)
        
        # Verify complete isolation
        user_ids = {ctx.user_id for ctx in concurrent_contexts}
        thread_ids = {ctx.thread_id for ctx in concurrent_contexts}
        run_ids = {ctx.run_id for ctx in concurrent_contexts}
        request_ids = {ctx.request_id for ctx in concurrent_contexts}
        
        assert len(user_ids) == 3, "All user IDs should be unique"
        assert len(thread_ids) == 3, "All thread IDs should be unique"
        assert len(run_ids) == 3, "All run IDs should be unique"
        assert len(request_ids) == 3, "All request IDs should be unique"
        
        print("PASS: Concurrent context isolation working")
        
        print("\n*** ALL TESTS PASSED! Basic auth + context integration is working! ***")
        return True
        
    except Exception as e:
        print(f"\n*** TEST FAILED: {e} ***")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_basic_auth_integration())
    sys.exit(0 if result else 1)