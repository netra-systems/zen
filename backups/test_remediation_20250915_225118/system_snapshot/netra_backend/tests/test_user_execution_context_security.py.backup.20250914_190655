"""
Security Demonstration Tests for UserExecutionContext

This module demonstrates how UserExecutionContext prevents common security 
vulnerabilities related to placeholder values and improper context initialization.

These tests show real-world scenarios where invalid context could lead to 
data leakage between users or system failures.
"""

import pytest
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import IsolatedEnvironment


class TestUserExecutionContextSecurity:
    """Security demonstration tests for UserExecutionContext."""
    
    def test_prevents_none_user_id_data_leakage(self):
        """
        Demonstrate how the class prevents data leakage from None user_id.
        
        In a real system, a None user_id could cause:
        - Database queries returning all users' data
        - Cache keys being malformed leading to cross-user data access
        - Authorization checks failing open
        """
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(
                user_id=None,
                thread_id="thread_123",
                run_id="run_456",
                request_id="req_789"
            )
        
        assert "user isolation" in str(exc_info.value).lower()
        
    def test_prevents_placeholder_user_id_confusion(self):
        """
        Demonstrate how the class prevents confusion from string "None" user_id.
        
        In a real system, a "None" string user_id could cause:
        - All "None" users being treated as the same user
        - Cache collisions between different requests
        - Audit logs showing "None" instead of actual user IDs
        """
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(
                user_id="None",  # String "None" is a common placeholder mistake
                thread_id="thread_123", 
                run_id="run_456",
                request_id="req_789"
            )
        
        assert "placeholder value" in str(exc_info.value).lower()
        
    def test_prevents_registry_run_id_system_confusion(self):
        """
        Demonstrate how the class prevents system confusion from "registry" run_id.
        
        In a real system, a "registry" run_id could cause:
        - Conflicts with system registry operations
        - Agent execution being misrouted to registry operations
        - Resource cleanup targeting the wrong execution context
        """
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(
                user_id="user_123",
                thread_id="thread_456",
                run_id="registry",  # "registry" is a system placeholder
                request_id="req_789"
            )
        
        assert "placeholder value" in str(exc_info.value).lower()
        assert "registry" in str(exc_info.value).lower()
        
    def test_prevents_empty_context_fields(self):
        """
        Demonstrate how the class prevents empty context fields.
        
        Empty context fields could cause:
        - Database constraints violations
        - Malformed cache keys
        - Broken request tracing and debugging
        """
        # Test empty thread_id
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(
                user_id="user_123",
                thread_id="",  # Empty thread_id
                run_id="run_456",
                request_id="req_789"
            )
        assert "conversation tracking" in str(exc_info.value).lower()
        
        # Test empty request_id
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(
                user_id="user_123",
                thread_id="thread_456",
                run_id="run_789",
                request_id=""  # Empty request_id
            )
        assert "request tracking" in str(exc_info.value).lower()
        
    def test_valid_context_enables_secure_operations(self):
        """
        Demonstrate how valid context enables secure operations.
        
        This shows what a properly initialized context looks like and
        how it can be safely used for system operations.
        """
        context = UserExecutionContext(
            user_id="user_secure_123",
            thread_id="thread_conv_456", 
            run_id="run_exec_789",
            request_id="req_api_012"
        )
        
        # These operations would be safe with this context
        assert context.user_id.startswith("user_")
        assert context.thread_id.startswith("thread_")
        assert context.run_id.startswith("run_")
        assert context.request_id.startswith("req_")
        
        # Context can be safely converted to dict for logging/tracing
        context_dict = context.to_dict()
        assert all(key in context_dict for key in ["user_id", "thread_id", "run_id", "request_id"])
        assert all(isinstance(value, str) and value.strip() for value in context_dict.values())
        
    def test_secure_string_representation_for_logging(self):
        """
        Demonstrate secure string representation that protects user privacy in logs.
        
        The __str__ method truncates user_id to prevent full user IDs from
        appearing in logs while still providing useful debugging information.
        """
        context = UserExecutionContext(
            user_id="user_very_long_sensitive_id_12345",
            thread_id="thread_456",
            run_id="run_789", 
            request_id="req_012"
        )
        
        str_repr = str(context)
        
        # User ID should be truncated for security
        assert "user_ver..." in str_repr
        assert "user_very_long_sensitive_id_12345" not in str_repr
        
        # Other fields should be visible for debugging
        assert "thread_456" in str_repr
        assert "run_789" in str_repr 
        assert "req_012" in str_repr
        
    def test_fail_fast_behavior_prevents_silent_failures(self):
        """
        Demonstrate that the class fails fast on invalid input rather than
        allowing silent failures that could cause security issues later.
        
        Fail-fast behavior is critical for security because it prevents
        invalid context from propagating through the system and causing
        subtle security vulnerabilities.
        """
        # All of these should fail immediately, not later in the system
        invalid_contexts = [
            {"user_id": None, "thread_id": "t", "run_id": "r", "request_id": "req"},
            {"user_id": "", "thread_id": "t", "run_id": "r", "request_id": "req"},
            {"user_id": "None", "thread_id": "t", "run_id": "r", "request_id": "req"},
            {"user_id": "u", "thread_id": None, "run_id": "r", "request_id": "req"},
            {"user_id": "u", "thread_id": "", "run_id": "r", "request_id": "req"},
            {"user_id": "u", "thread_id": "t", "run_id": None, "request_id": "req"},
            {"user_id": "u", "thread_id": "t", "run_id": "", "request_id": "req"},
            {"user_id": "u", "thread_id": "t", "run_id": "registry", "request_id": "req"},
            {"user_id": "u", "thread_id": "t", "run_id": "r", "request_id": None},
            {"user_id": "u", "thread_id": "t", "run_id": "r", "request_id": ""},
        ]
        
        for invalid_context in invalid_contexts:
            with pytest.raises(ValueError):
                UserExecutionContext(**invalid_context)
                
        # This confirms that each invalid context fails fast at construction time
        # rather than failing later when used in system operations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])