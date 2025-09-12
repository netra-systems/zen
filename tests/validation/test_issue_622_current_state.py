#!/usr/bin/env python3
"""Validation Test for Issue #622: Reproduce Current Failing State

This test reproduces the EXACT failing behavior reported in Issue #622
to confirm the problem exists and validate any fix.

13 E2E tests are failing because they call create_authenticated_test_user()
but the method is actually named create_authenticated_user().
"""

import pytest
import asyncio
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

def test_reproduce_issue_622_failing_method_call():
    """Reproduce the exact AttributeError from Issue #622."""
    
    # This is the exact pattern that's failing in 13 E2E tests
    auth_helper = E2EAuthHelper()
    user_id = "test_user_123"
    
    # This should fail with AttributeError
    with pytest.raises(AttributeError) as exc_info:
        # This is the failing call from test_complete_chat_business_value_flow.py line 332
        asyncio.run(auth_helper.create_authenticated_test_user(user_id))
    
    # Verify it's the expected error
    error_message = str(exc_info.value)
    assert "create_authenticated_test_user" in error_message
    assert "E2EAuthHelper" in error_message or "object has no attribute" in error_message
    
    print(f"✅ Successfully reproduced Issue #622 error: {error_message}")

def test_working_method_exists():
    """Confirm the actual working method exists."""
    
    auth_helper = E2EAuthHelper()
    
    # The actual method that exists
    assert hasattr(auth_helper, 'create_authenticated_user')
    method = getattr(auth_helper, 'create_authenticated_user')
    assert callable(method)
    assert asyncio.iscoroutinefunction(method)
    
    print("✅ Confirmed create_authenticated_user method exists and is callable")

def test_missing_method_confirmed():
    """Confirm the missing method doesn't exist."""
    
    auth_helper = E2EAuthHelper()
    
    # This is what's missing and causing the failures
    missing_method_exists = hasattr(auth_helper, 'create_authenticated_test_user')
    
    if missing_method_exists:
        pytest.fail("Method create_authenticated_test_user exists - Issue #622 may already be fixed")
    
    print("✅ Confirmed create_authenticated_test_user method is missing (expected for Issue #622)")

if __name__ == "__main__":
    # Run the validation tests
    pytest.main([__file__, "-v"])