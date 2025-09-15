#!/usr/bin/env python3
"""
Test script to verify Issue #1234 authentication fix works in practice.
Simulates the auth failure scenario that was causing 403 instead of 401.
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from netra_backend.app.core.unified_error_handler import _unified_error_handler
from netra_backend.app.schemas.shared_types import ErrorContext
from fastapi import HTTPException

async def test_auth_failure_scenario():
    """Test that auth failures now return 401 instead of 403"""
    
    print("Testing Issue #1234 Fix - Authentication Failure Scenario")
    print("=" * 60)
    
    # Create a context for the test
    context = ErrorContext(
        trace_id=str(uuid4()),
        operation="chat_api_auth",
        timestamp=datetime.now(timezone.utc)
    )
    
    # Simulate the auth failure that was returning 403
    auth_error = HTTPException(status_code=401, detail="Invalid or expired JWT token")
    
    print(f"Simulating auth failure: {auth_error.detail}")
    
    # Handle the error through the unified error handler
    result = await _unified_error_handler.handle_error(auth_error, context)
    
    # Check the HTTP status code that would be returned
    if hasattr(result, 'error_code'):
        http_status = _unified_error_handler.get_http_status_code(result.error_code)
        print(f"Error code: {result.error_code}")
        print(f"HTTP status: {http_status}")
        
        if http_status == 401:
            print("✅ SUCCESS: Auth failure correctly returns 401 (Unauthorized)")
            print("✅ Chat API authentication should now work properly!")
            return True
        elif http_status == 403:
            print("❌ FAILED: Auth failure still returns 403 (Forbidden)")
            return False
        else:
            print(f"❌ UNEXPECTED: Auth failure returns {http_status}")
            return False
    else:
        print("❌ ERROR: Could not determine error code from result")
        return False

async def test_different_auth_scenarios():
    """Test various auth failure scenarios"""
    
    print("\nTesting different auth failure scenarios:")
    print("-" * 40)
    
    scenarios = [
        ("Invalid JWT token", HTTPException(status_code=401, detail="Invalid JWT token")),
        ("Expired JWT token", HTTPException(status_code=401, detail="Expired JWT token")),
        ("Missing JWT token", HTTPException(status_code=401, detail="Missing authorization header")),
        ("Malformed JWT token", HTTPException(status_code=401, detail="Malformed authorization header")),
    ]
    
    all_passed = True
    
    for scenario_name, error in scenarios:
        context = ErrorContext(
            trace_id=str(uuid4()),
            operation=f"test_{scenario_name.lower().replace(' ', '_')}",
            timestamp=datetime.now(timezone.utc)
        )
        
        result = await _unified_error_handler.handle_error(error, context)
        
        if hasattr(result, 'error_code'):
            http_status = _unified_error_handler.get_http_status_code(result.error_code)
            status_icon = "✅" if http_status == 401 else "❌"
            print(f"{status_icon} {scenario_name}: HTTP {http_status}")
            
            if http_status != 401:
                all_passed = False
        else:
            print(f"❌ {scenario_name}: Could not determine status code")
            all_passed = False
    
    return all_passed

async def main():
    """Main test function"""
    
    # Test the main auth failure scenario
    main_test_passed = await test_auth_failure_scenario()
    
    # Test different auth scenarios
    scenarios_passed = await test_different_auth_scenarios()
    
    print("\n" + "=" * 60)
    if main_test_passed and scenarios_passed:
        print("🎉 ALL TESTS PASSED!")
        print("Issue #1234 has been successfully resolved.")
        print("Chat API authentication should now work correctly.")
        print("Authentication failures will properly return HTTP 401 instead of 403.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Issue #1234 may not be fully resolved.")
        if not main_test_passed:
            print("- Main auth failure test failed")
        if not scenarios_passed:
            print("- Some auth scenario tests failed")

if __name__ == "__main__":
    asyncio.run(main())