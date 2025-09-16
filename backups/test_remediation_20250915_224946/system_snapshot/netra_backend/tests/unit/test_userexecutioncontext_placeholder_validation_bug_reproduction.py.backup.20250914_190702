"""
Bug Reproduction Test for UserExecutionContext Placeholder Validation

This test reproduces the critical bug where legitimate test user IDs are 
incorrectly flagged as placeholder patterns, causing integration tests to fail.

Location: netra_backend/app/services/user_execution_context.py:194
Error: InvalidContextError: Field 'user_id' appears to contain placeholder pattern: 'test_user_81dc9607'

Business Value: Platform/Internal - Critical bug blocking integration test pipeline
"""

import pytest
import uuid
import time
from unittest.mock import patch

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    InvalidContextError
)
from shared.isolated_environment import IsolatedEnvironment


class TestUserExecutionContextPlaceholderValidationBug:
    """Test suite to reproduce and verify fix for placeholder validation bug."""
    
    def test_bug_reproduction_test_user_pattern_rejected_in_all_environments(self):
        """
        AFTER FIX: Test user IDs with 'test_user_' pattern are now allowed in test environments.
        
        This shows the bug was fixed - before the fix this would fail, now it passes.
        """
        # This is the exact pattern that was causing integration test failures
        test_user_id = "test_user_81dc9607"
        
        # After fix: This should NOT raise InvalidContextError in real test environment
        context = UserExecutionContext(
            user_id=test_user_id,
            thread_id="thread_test_123",
            run_id="run_test_456", 
            request_id="req_test_789"
        )
        assert context.user_id == test_user_id
    
    def test_production_should_reject_test_user_patterns(self):
        """
        SECURITY TEST: Production environments should still reject test user patterns.
        
        This should PASS both before and after the fix.
        """
        # Mock the instance methods by patching through the module path used in user_execution_context.py
        with patch('netra_backend.app.services.user_execution_context.IsolatedEnvironment') as mock_env_class:
            # Configure the mock instance
            mock_env_instance = mock_env_class.return_value
            mock_env_instance.is_test.return_value = False
            mock_env_instance.get_environment_name.return_value = "production"
            
            with pytest.raises(InvalidContextError, match="placeholder pattern"):
                UserExecutionContext(
                    user_id="test_user_fail",  # < 20 chars to trigger validation  
                    thread_id="thread_123",
                    run_id="run_456", 
                    request_id="req_789"
                )
    
    def test_test_environment_should_allow_test_user_patterns_after_fix(self):
        """
        EXPECTED BEHAVIOR AFTER FIX: Test environments should allow test_user_ patterns.
        
        This should FAIL before the fix and PASS after the fix.
        """
        with patch('netra_backend.app.services.user_execution_context.IsolatedEnvironment') as mock_env_class:
            # Configure the mock instance for test environment
            mock_env_instance = mock_env_class.return_value
            mock_env_instance.is_test.return_value = True
            mock_env_instance.get_environment_name.return_value = "test"
            
            # After fix, this should NOT raise InvalidContextError
            context = UserExecutionContext(
                user_id="test_user_81dc9607",
                thread_id="thread_test_123",
                run_id="run_test_456", 
                request_id="req_test_789"
            )
            assert context.user_id == "test_user_81dc9607"
    
    def test_common_test_user_id_patterns_should_work_in_test_env(self):
        """
        Test various test user ID patterns found in the codebase.
        
        These are all legitimate patterns used throughout the test suite.
        """
        test_patterns = [
            f"test_user_{uuid.uuid4().hex[:8]}",  # UUID-based pattern
            f"test_user_{int(time.time())}",      # Timestamp-based pattern
            f"test_user_{hash('test@example.com') % 10000}",  # Hash-based pattern
            "test_user_81dc9607",                 # Specific failing pattern
            "backend_test_user_12345",            # Backend service pattern
            "memory_test_user_1",                 # Memory test pattern
            "load_test_user_42"                   # Load test pattern
        ]
        
        with patch('netra_backend.app.services.user_execution_context.IsolatedEnvironment') as mock_env_class:
            # Configure the mock instance for test environment
            mock_env_instance = mock_env_class.return_value
            mock_env_instance.is_test.return_value = True
            mock_env_instance.get_environment_name.return_value = "test"
            
            for test_user_id in test_patterns:
                # After fix, none of these should raise InvalidContextError
                context = UserExecutionContext(
                    user_id=test_user_id,
                    thread_id=f"thread_{test_user_id}",
                    run_id=f"run_{test_user_id}",
                    request_id=f"req_{test_user_id}"
                )
                assert context.user_id == test_user_id
    
    def test_non_test_patterns_work_in_all_environments(self):
        """
        REGRESSION TEST: Non-test patterns should work in all environments.
        
        This should PASS both before and after the fix.
        """
        legitimate_user_ids = [
            "user_12345",
            "actual_user_67890", 
            "production_user_abc123",
            "real_user_xyz789"
        ]
        
        for env_name, is_test_val in [("production", False), ("test", True), ("development", False)]:
            with patch('netra_backend.app.services.user_execution_context.IsolatedEnvironment') as mock_env_class:
                # Configure the mock instance
                mock_env_instance = mock_env_class.return_value
                mock_env_instance.is_test.return_value = is_test_val
                mock_env_instance.get_environment_name.return_value = env_name
                
                for user_id in legitimate_user_ids:
                    context = UserExecutionContext(
                        user_id=user_id,
                        thread_id="thread_123",
                        run_id="run_456", 
                        request_id="req_789"
                    )
                    assert context.user_id == user_id
    
    def test_other_forbidden_patterns_still_rejected_in_test_env(self):
        """
        SECURITY TEST: Other dangerous patterns should still be rejected even in test environments.
        
        This should PASS both before and after the fix.
        """
        dangerous_patterns = [
            "placeholder_user",  # matches "placeholder_"
            "default_user",      # matches "default_"
            "temp_user",         # matches "temp_"
            "example_user",      # matches "example_"
            "mock_user"          # matches "mock_"
            # Note: removed "dummy_user" - it doesn't match any forbidden pattern, only exact value "dummy"
        ]
        
        with patch('netra_backend.app.services.user_execution_context.IsolatedEnvironment') as mock_env_class:
            # Configure the mock instance for test environment
            mock_env_instance = mock_env_class.return_value
            mock_env_instance.is_test.return_value = True
            mock_env_instance.get_environment_name.return_value = "test"
            
            for dangerous_id in dangerous_patterns:
                with pytest.raises(InvalidContextError):
                    UserExecutionContext(
                        user_id=dangerous_id,
                        thread_id="thread_123",
                        run_id="run_456",
                        request_id="req_789"
                    )
    
    def test_exact_forbidden_values_still_rejected_in_test_env(self):
        """
        SECURITY TEST: Exact forbidden values should still be rejected in test environments.
        
        This should PASS both before and after the fix.
        """
        forbidden_exact_values = [
            "test",  # Exact "test" should still be forbidden
            "demo",
            "sample", 
            "template",
            "placeholder",
            "default"
        ]
        
        with patch('netra_backend.app.services.user_execution_context.IsolatedEnvironment') as mock_env_class:
            # Configure the mock instance for test environment
            mock_env_instance = mock_env_class.return_value
            mock_env_instance.is_test.return_value = True
            mock_env_instance.get_environment_name.return_value = "test"
            
            for forbidden_value in forbidden_exact_values:
                with pytest.raises(InvalidContextError):
                    UserExecutionContext(
                        user_id=forbidden_value,
                        thread_id="thread_123", 
                        run_id="run_456",
                        request_id="req_789"
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])