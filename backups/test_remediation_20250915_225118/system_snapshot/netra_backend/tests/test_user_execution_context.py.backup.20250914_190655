"""
Test Suite for UserExecutionContext

This module provides comprehensive tests for the UserExecutionContext class
to ensure proper validation and fail-fast behavior for invalid context values.

Business Value: Validates that our critical security validation works correctly
to prevent data leakage and ensure proper request isolation.
"""

import pytest
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import IsolatedEnvironment


class TestUserExecutionContextValidation:
    """Test class for UserExecutionContext validation logic."""
    
    def test_valid_context_creation(self):
        """Test that valid context values are accepted."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890", 
            run_id="run_abcdef",
            request_id="req_xyz123"
        )
        
        assert context.user_id == "user_12345"
        assert context.thread_id == "thread_67890"
        assert context.run_id == "run_abcdef"
        assert context.request_id == "req_xyz123"
    
    def test_user_id_none_validation(self):
        """Test that None user_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be None"):
            UserExecutionContext(
                user_id=None,
                thread_id="thread_67890",
                run_id="run_abcdef", 
                request_id="req_xyz123"
            )
    
    def test_user_id_empty_validation(self):
        """Test that empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be empty"):
            UserExecutionContext(
                user_id="",
                thread_id="thread_67890",
                run_id="run_abcdef",
                request_id="req_xyz123"
            )
    
    def test_user_id_none_string_validation(self):
        """Test that 'None' string as user_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be the string 'None'"):
            UserExecutionContext(
                user_id="None",
                thread_id="thread_67890",
                run_id="run_abcdef",
                request_id="req_xyz123"
            )
    
    def test_thread_id_none_validation(self):
        """Test that None thread_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.thread_id cannot be None"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id=None,
                run_id="run_abcdef",
                request_id="req_xyz123"
            )
    
    def test_thread_id_empty_validation(self):
        """Test that empty thread_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.thread_id cannot be empty"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="",
                run_id="run_abcdef",
                request_id="req_xyz123"
            )
    
    def test_run_id_none_validation(self):
        """Test that None run_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.run_id cannot be None"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id=None,
                request_id="req_xyz123"
            )
    
    def test_run_id_empty_validation(self):
        """Test that empty run_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.run_id cannot be empty"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id="",
                request_id="req_xyz123"
            )
    
    def test_run_id_registry_validation(self):
        """Test that 'registry' as run_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.run_id cannot be 'registry'"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id="registry",
                request_id="req_xyz123"
            )
    
    def test_request_id_none_validation(self):
        """Test that None request_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.request_id cannot be None"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id="run_abcdef",
                request_id=None
            )
    
    def test_request_id_empty_validation(self):
        """Test that empty request_id raises ValueError."""
        with pytest.raises(ValueError, match="UserExecutionContext.request_id cannot be empty"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id="run_abcdef",
                request_id=""
            )


class TestUserExecutionContextMethods:
    """Test class for UserExecutionContext utility methods."""
    
    def test_to_dict_method(self):
        """Test that to_dict returns correct dictionary representation."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef",
            request_id="req_xyz123"
        )
        
        result = context.to_dict()
        expected = {
            "user_id": "user_12345",
            "thread_id": "thread_67890",
            "run_id": "run_abcdef",
            "request_id": "req_xyz123"
        }
        
        assert result == expected
    
    def test_str_method_truncates_user_id(self):
        """Test that __str__ truncates long user_id for security."""
        context = UserExecutionContext(
            user_id="user_very_long_id_12345",
            thread_id="thread_67890",
            run_id="run_abcdef", 
            request_id="req_xyz123"
        )
        
        str_result = str(context)
        assert "user_ver..." in str_result
        assert "thread_id=thread_67890" in str_result
        assert "run_id=run_abcdef" in str_result
        assert "request_id=req_xyz123" in str_result
    
    def test_str_method_short_user_id(self):
        """Test that __str__ doesn't truncate short user_id."""
        context = UserExecutionContext(
            user_id="user123",
            thread_id="thread_67890",
            run_id="run_abcdef",
            request_id="req_xyz123"
        )
        
        str_result = str(context)
        assert "user_id=user123" in str_result
        assert "..." not in str_result
    
    def test_repr_method(self):
        """Test that __repr__ returns detailed representation."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef",
            request_id="req_xyz123"
        )
        
        repr_result = repr(context)
        expected = "UserExecutionContext(user_id='user_12345', thread_id='thread_67890', run_id='run_abcdef', request_id='req_xyz123')"
        assert repr_result == expected


class TestUserExecutionContextEdgeCases:
    """Test class for edge cases and security scenarios."""
    
    def test_multiple_validation_failures(self):
        """Test that first validation failure is caught even when multiple fields are invalid."""
        # Should fail on user_id validation first
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be None"):
            UserExecutionContext(
                user_id=None,
                thread_id=None,  # This would also fail but shouldn't be reached
                run_id="registry",  # This would also fail but shouldn't be reached
                request_id=""  # This would also fail but shouldn't be reached  
            )
    
    def test_whitespace_only_values(self):
        """Test that whitespace-only values are accepted (business decision)."""
        # Note: The current implementation only checks for None and empty string
        # Whitespace-only strings are considered valid as per business requirements
        context = UserExecutionContext(
            user_id="   ",  # Whitespace only - valid
            thread_id=" \t ",  # Whitespace only - valid
            run_id=" \n ",  # Whitespace only - valid
            request_id="  "  # Whitespace only - valid
        )
        
        # Should not raise an exception
        assert context.user_id == "   "
        assert context.thread_id == " \t "
        assert context.run_id == " \n "
        assert context.request_id == "  "
    
    def test_special_characters_in_values(self):
        """Test that special characters are handled properly."""
        context = UserExecutionContext(
            user_id="user@domain.com",
            thread_id="thread-with-dashes_and_underscores.123",
            run_id="run:with:colons/and/slashes",
            request_id="req#with$special%chars&symbols"
        )
        
        # Should not raise an exception
        assert context.user_id == "user@domain.com"
        assert context.thread_id == "thread-with-dashes_and_underscores.123"
        assert context.run_id == "run:with:colons/and/slashes"
        assert context.request_id == "req#with$special%chars&symbols"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])