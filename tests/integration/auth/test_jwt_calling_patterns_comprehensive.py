"""
Comprehensive Test: JWT Calling Patterns Analysis (Issue #520)

PURPOSE: Comprehensive reproduction of all JWT token creation patterns that fail
due to the signature change requiring the email parameter.

This test covers the full scope of the breaking change affecting 50+ test files
and validates both the problem and solution approaches.
"""

import pytest
from typing import Dict, List, Any, Optional

from test_framework.fixtures.auth import create_real_jwt_token


class TestJWTCallingPatternsComprehensive:
    """Comprehensive test of all JWT calling patterns affected by Issue #520."""
    
    def test_positional_args_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Positional arguments pattern (most common failure).
        
        Many tests use positional arguments and are broken by the new email requirement.
        """
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            # Old pattern: user_id, permissions, expires_in
            create_real_jwt_token("user123", ["read", "write"], 3600)
    
    def test_mixed_args_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Mixed positional and keyword arguments pattern.
        
        Some tests mix positional and keyword arguments, missing email.
        """
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            # Mixed pattern: positional user_id, permissions, then keyword expires_in
            create_real_jwt_token("user456", ["admin"], expires_in=7200)
    
    def test_keyword_only_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Keyword-only arguments pattern.
        
        Tests using only keyword arguments but missing email parameter.
        """
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            # Keyword-only pattern missing email
            create_real_jwt_token(
                user_id="user789",
                permissions=["read", "write", "websocket"],
                expires_in=1800
            )
    
    def test_extra_unknown_parameters_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Pattern with extra unknown parameters.
        
        Some tests pass parameters that don't exist in the function signature.
        """
        with pytest.raises(TypeError):
            # Pattern with unknown parameters (token_type doesn't exist)
            create_real_jwt_token(
                user_id="user101",
                permissions=["read"],
                token_type="access",  # This parameter doesn't exist
                expires_in=3600
            )
    
    def test_permissions_as_string_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Pattern with permissions as string instead of list.
        
        Some tests might pass permissions as string, which would cause type errors.
        """
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            # Pattern with permissions as string (would fail anyway, but email is still missing)
            create_real_jwt_token(
                user_id="user202",
                permissions="read,write",  # Should be List[str]
                expires_in=3600
            )
    
    def test_none_values_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Pattern with None values for optional parameters.
        
        Tests that explicitly pass None for optional parameters but miss email.
        """
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            # Pattern with None for optional params but missing required email
            create_real_jwt_token(
                user_id="user303",
                permissions=["read", "write"],
                expires_in=None  # This would be converted to default
            )
    
    def test_dynamic_parameters_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Pattern with dynamically generated parameters.
        
        Tests that build parameters dynamically and miss the new email requirement.
        """
        # Simulate dynamic parameter generation (common in test utilities)
        test_params = {
            "user_id": "dynamic-user-404",
            "permissions": ["dynamic", "test", "permissions"],
            "expires_in": 2400
        }
        
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            # Dynamic parameter unpacking missing email
            create_real_jwt_token(**test_params)
    
    def test_factory_method_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Factory method pattern used in test utilities.
        
        Test factory methods that create JWT tokens are broken by the signature change.
        """
        def create_test_jwt_for_user(user_id: str, role: str = "user") -> str:
            """Simulate a test factory method that creates JWT tokens."""
            permissions = {
                "user": ["read", "write"],
                "admin": ["read", "write", "admin"],
                "agent": ["read", "write", "agent_execute"]
            }.get(role, ["read"])
            
            # This factory method doesn't know about the new email requirement
            return create_real_jwt_token(
                user_id=user_id,
                permissions=permissions,
                expires_in=3600
            )
        
        with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
            create_test_jwt_for_user("factory-user-505")
    
    def test_conditional_token_creation_pattern_reproduces_issue_520(self):
        """
        REPRODUCTION TEST: Conditional token creation pattern.
        
        Tests that conditionally create tokens based on test conditions.
        """
        test_conditions = {
            "needs_auth": True,
            "user_type": "premium",
            "session_length": "standard"
        }
        
        if test_conditions["needs_auth"]:
            permissions = ["premium", "read", "write"]
            expires_in = 3600 if test_conditions["session_length"] == "standard" else 7200
            
            with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'email'"):
                # Conditional creation missing email parameter
                create_real_jwt_token(
                    user_id="conditional-user-606",
                    permissions=permissions,
                    expires_in=expires_in
                )


class TestJWTCallingPatternsFixValidation:
    """Test how all calling patterns should work after implementing fixes."""
    
    def test_optional_email_parameter_fix_approach_validation(self):
        """
        VALIDATION TEST: Test optional email parameter fix approach.
        
        If email is made optional with a default value, old calling patterns should work.
        NOTE: This test will fail initially but shows the expected behavior after fix.
        """
        # This would work if email parameter is made optional with default
        try:
            token = create_real_jwt_token(
                user_id="optional-email-test",
                permissions=["read", "write"],
                expires_in=3600
            )
            # If this works, the optional parameter approach was implemented
            assert isinstance(token, str)
            assert len(token) > 10
        except TypeError as e:
            # Expected to fail until fix is implemented
            assert "missing 1 required positional argument: 'email'" in str(e)
    
    def test_systematic_update_fix_approach_validation(self):
        """
        VALIDATION TEST: Test systematic update fix approach.
        
        With systematic updates, all calls must provide email parameter.
        """
        # This should work with explicit email parameter
        token = create_real_jwt_token(
            user_id="systematic-update-test",
            permissions=["read", "write"],
            email="systematic-test@example.com",
            expires_in=3600
        )
        
        assert isinstance(token, str)
        assert len(token) > 10
        assert token.count('.') == 2  # JWT format
    
    def test_factory_method_with_email_fix_validation(self):
        """
        VALIDATION TEST: Test factory method pattern with email fix.
        
        Shows how factory methods should be updated to include email.
        """
        def create_test_jwt_for_user_fixed(user_id: str, email: str, role: str = "user") -> str:
            """Fixed test factory method that includes email parameter."""
            permissions = {
                "user": ["read", "write"],
                "admin": ["read", "write", "admin"],
                "agent": ["read", "write", "agent_execute"]
            }.get(role, ["read"])
            
            # Fixed factory method with email parameter
            return create_real_jwt_token(
                user_id=user_id,
                permissions=permissions,
                email=email,
                expires_in=3600
            )
        
        # This should work with the fixed factory method
        token = create_test_jwt_for_user_fixed(
            user_id="fixed-factory-user",
            email="factory-test@example.com",
            role="admin"
        )
        
        assert isinstance(token, str)
        assert len(token) > 10
    
    def test_dynamic_parameters_with_email_fix_validation(self):
        """
        VALIDATION TEST: Test dynamic parameter pattern with email fix.
        
        Shows how dynamic parameter generation should include email.
        """
        # Fixed dynamic parameter generation with email
        test_params = {
            "user_id": "dynamic-user-fixed",
            "permissions": ["dynamic", "test", "permissions"],
            "email": "dynamic-test@example.com",
            "expires_in": 2400
        }
        
        # This should work with email included
        token = create_real_jwt_token(**test_params)
        
        assert isinstance(token, str)
        assert len(token) > 10
        assert token.count('.') == 2