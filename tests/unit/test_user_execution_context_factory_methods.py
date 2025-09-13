"""
Unit Tests for Issue #674: UserExecutionContext Factory Method Validation

Test Plan: Validate UserExecutionContext factory methods and fix create_for_user() errors.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: System Stability & Multi-user Support  
- Value Impact: Fixes critical test infrastructure blocking multi-user validation
- Strategic Impact: Enables $500K+ ARR validation for concurrent user functionality

CRITICAL: This test validates the root cause fix for Issue #674 where 80+ test files
call UserExecutionContext.create_for_user() but this method doesn't exist.
"""

import pytest
from typing import Any, Dict, Optional
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUserExecutionContextFactoryMethods:
    """Test suite validating UserExecutionContext factory methods for Issue #674."""
    
    def test_create_for_user_method_does_not_exist(self):
        """
        ISSUE #674 ROOT CAUSE: Confirm create_for_user method doesn't exist.
        
        This test documents the root cause - 80+ test files call a non-existent method.
        """
        assert not hasattr(UserExecutionContext, 'create_for_user'), \
            "create_for_user method should not exist - this is the root cause of Issue #674"
    
    def test_from_request_method_exists(self):
        """
        Verify from_request method exists as replacement for create_for_user.
        
        This is the correct factory method that should be used instead.
        """
        assert hasattr(UserExecutionContext, 'from_request'), \
            "from_request method should exist as replacement for create_for_user"
    
    def test_from_request_method_signature_compatibility(self):
        """
        Test that from_request method has compatible signature with expected create_for_user usage.
        
        Validates that the fix (replacing create_for_user with from_request) will work.
        """
        # Test with the same parameters used in failing tests
        context = UserExecutionContext.from_request(
            user_id="test_user_674",
            thread_id="test_thread_674", 
            run_id="test_run_674"
        )
        
        # Verify context was created successfully
        assert context is not None, "UserExecutionContext should be created successfully"
        assert context.user_id == "test_user_674", "Context should have correct user_id"
        assert context.thread_id == "test_thread_674", "Context should have correct thread_id"
        assert context.run_id == "test_run_674", "Context should have correct run_id"
    
    def test_from_request_with_optional_parameters(self):
        """
        Test from_request with optional parameters to ensure full compatibility.
        
        Validates that the method works with both required and optional parameters.
        """
        context = UserExecutionContext.from_request(
            user_id="test_user_optional",
            thread_id="test_thread_optional",
            run_id="test_run_optional",
            request_id="custom_request_id",
            websocket_client_id="ws_client_123"
        )
        
        assert context is not None
        assert context.user_id == "test_user_optional"
        assert context.thread_id == "test_thread_optional"
        assert context.run_id == "test_run_optional"
    
    def test_available_factory_methods_comprehensive(self):
        """
        Document all available factory methods for Issue #674 resolution.
        
        This helps developers understand what methods ARE available.
        """
        available_methods = [
            'from_request',                    # Primary replacement for create_for_user
            'from_websocket_request',          # For WebSocket-specific contexts
            'from_fastapi_request',            # For FastAPI request contexts
            'from_agent_execution_context',    # For agent execution scenarios
            'from_request_supervisor'          # For supervisor-level contexts
        ]
        
        for method_name in available_methods:
            assert hasattr(UserExecutionContext, method_name), \
                f"Expected factory method {method_name} should exist"
    
    def test_context_creation_produces_valid_objects(self):
        """
        Test that created contexts are valid and functional.
        
        Ensures that the fix doesn't just avoid errors but creates working contexts.
        """
        context = UserExecutionContext.from_request(
            user_id="validation_user",
            thread_id="validation_thread",
            run_id="validation_run"
        )
        
        # Test that context has expected attributes and methods
        assert hasattr(context, 'user_id'), "Context should have user_id attribute"
        assert hasattr(context, 'thread_id'), "Context should have thread_id attribute"  
        assert hasattr(context, 'run_id'), "Context should have run_id attribute"
        assert hasattr(context, 'get_scoped_key'), "Context should have get_scoped_key method"
        
        # Test that context key can be generated
        context_key = context.get_scoped_key("test_component")
        assert context_key is not None, "Context should generate valid context key"
        assert isinstance(context_key, str), "Context key should be string"
    
    def test_multiple_context_isolation(self):
        """
        Test that multiple contexts are properly isolated (addresses concurrency concern).
        
        This validates that the fix enables proper multi-user isolation testing.
        """
        contexts = []
        
        # Create multiple contexts (simulating concurrent users)
        for i in range(3):
            context = UserExecutionContext.from_request(
                user_id=f"concurrent_user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}"
            )
            contexts.append(context)
        
        # Verify contexts are properly isolated
        user_ids = [ctx.user_id for ctx in contexts]
        thread_ids = [ctx.thread_id for ctx in contexts]
        run_ids = [ctx.run_id for ctx in contexts]
        
        # All should be unique
        assert len(set(user_ids)) == 3, "All contexts should have unique user_ids"
        assert len(set(thread_ids)) == 3, "All contexts should have unique thread_ids"
        assert len(set(run_ids)) == 3, "All contexts should have unique run_ids"
        
        # Context keys should be unique
        context_keys = [ctx.get_scoped_key("test_component") for ctx in contexts]
        assert len(set(context_keys)) == 3, "All contexts should have unique context keys"
    
    def test_error_handling_with_invalid_parameters(self):
        """
        Test error handling to ensure robust behavior.
        
        Validates that the replacement method handles edge cases properly.
        """
        # Test with None parameters (should fail appropriately)
        with pytest.raises((ValueError, TypeError)):
            UserExecutionContext.from_request(
                user_id=None,  # Invalid
                thread_id="valid_thread",
                run_id="valid_run"
            )
        
        # Test with empty string parameters  
        from netra_backend.app.services.user_execution_context import InvalidContextError
        with pytest.raises(InvalidContextError):
            UserExecutionContext.from_request(
                user_id="",  # Invalid empty string
                thread_id="valid_thread", 
                run_id="valid_run"
            )
    
    def test_fix_pattern_validation(self):
        """
        Validate the exact fix pattern that will be applied across 80+ files.
        
        This test simulates the exact replacement pattern for Issue #674.
        """
        # Original failing pattern (method doesn't exist)
        assert not hasattr(UserExecutionContext, 'create_for_user')
        
        # Fixed pattern (method exists and works)
        fixed_context = UserExecutionContext.from_request(
            user_id="test_user",      # Same parameter name
            thread_id="test_thread",  # Same parameter name  
            run_id="test_run"         # Same parameter name
        )
        
        # Verify the fix produces a working context
        assert fixed_context is not None
        assert fixed_context.user_id == "test_user"
        assert fixed_context.thread_id == "test_thread" 
        assert fixed_context.run_id == "test_run"
        
        # Verify context is functional
        assert fixed_context.get_scoped_key("test_component") is not None
    
    def test_issue_674_specific_test_case(self):
        """
        Test the exact scenario from the failing test in Issue #674.
        
        This replicates the create_user_context() method from:
        tests/e2e/golden_path/test_complete_golden_path_e2e_staging.py:96
        """
        # Simulate the fixed create_user_context method
        def create_user_context_fixed() -> UserExecutionContext:
            """Fixed version of create_user_context from failing test."""
            return UserExecutionContext.from_request(  # ✅ FIXED: was create_for_user
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run"
            )
        
        # Test that the fixed method works
        context = create_user_context_fixed()
        
        # Verify it creates a valid context
        assert context is not None
        assert isinstance(context, UserExecutionContext)
        assert context.user_id == "test_user"
        assert context.thread_id == "test_thread"
        assert context.run_id == "test_run"
        
        # Verify context is ready for use in concurrency tests
        assert context.get_scoped_key("test_component") is not None