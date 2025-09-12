"""
Unit Test: JWT Token Creation Backwards Compatibility (Issue #520)

PURPOSE: Reproduce the exact TypeError from Issue #520 where JWT token creation
fails with "missing 1 required positional argument: 'email'"

This test directly calls create_real_jwt_token with the old calling pattern
to reproduce the breaking change and validate fix approaches.
"""

import pytest
from typing import List

from test_framework.fixtures.auth import create_real_jwt_token


class TestJWTTokenCreationBackwardsCompatibility:
    """Test JWT token creation backwards compatibility issues."""
    
    def test_jwt_creation_missing_email_parameter_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Reproduce the exact TypeError from Issue #520.
        
        This test should FAIL with:
        "create_real_jwt_token() missing 1 required positional argument: 'email'"
        
        This represents the breaking change where existing code calls
        create_real_jwt_token without the newly required email parameter.
        """
        user_id = "test-user-123"
        permissions = ["read", "write", "websocket"]
        
        # This should fail because email parameter is missing
        # Pattern: Old calling code that worked before the change
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            create_real_jwt_token(
                user_id=user_id,
                permissions=permissions,
                expires_in=3600
            )
    
    def test_jwt_creation_with_keyword_args_missing_email_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Test the keyword argument pattern that fails.
        
        This represents frontend tests and other code using keyword arguments
        but missing the required email parameter.
        """
        user_id = "test-user-456"
        permissions = ["read", "write"]
        
        # This should fail because email parameter is missing
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            create_real_jwt_token(
                user_id=user_id,
                permissions=permissions,
                expires_in=7200
            )
    
    def test_jwt_creation_with_positional_args_wrong_order_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Test positional argument pattern that fails.
        
        This represents code that passes arguments positionally but in the
        wrong order or missing the email parameter.
        """
        user_id = "test-user-789"
        permissions = ["admin"]
        
        # This should fail because the third argument should be email, not expires_in
        with pytest.raises(TypeError):
            create_real_jwt_token(user_id, permissions, 1800)  # Missing email
    
    def test_jwt_creation_with_token_type_parameter_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Test the specific pattern from test_reconnection.py.
        
        This reproduces the exact calling pattern that fails in multiple test files.
        """
        user_id = "test-user-reconnection"
        permissions = ["read", "write", "websocket"]
        
        # This pattern from test_reconnection.py should fail
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            create_real_jwt_token(
                user_id=user_id,
                permissions=permissions,
                token_type="access",  # This parameter doesn't exist in function signature
                expires_in=3600
            )


class TestJWTTokenCreationExpectedBehavior:
    """Test what the correct calling pattern should look like after fix."""
    
    def test_jwt_creation_with_required_email_parameter_should_work(self):
        """
        VALIDATION TEST: Test that providing email parameter works correctly.
        
        This test shows the expected behavior after the fix.
        This should PASS and create a valid JWT token.
        """
        user_id = "test-user-valid"
        permissions = ["read", "write", "websocket"]
        email = "test@example.com"
        
        # This should work correctly
        token = create_real_jwt_token(
            user_id=user_id,
            permissions=permissions,
            email=email,
            expires_in=3600
        )
        
        # Basic validation that we got a token-like string
        assert isinstance(token, str)
        assert len(token) > 10  # JWT tokens are much longer
        assert token.count('.') == 2  # JWT format: header.payload.signature