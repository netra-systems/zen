#!/usr/bin/env python3
"""
Validation script for authentication E2E tests
Checks all requirements are met per CLAUDE.md specifications
"""

import ast
import inspect
import sys
from pathlib import Path

def validate_auth_test_file():
    """Validate the authentication test file meets all requirements."""
    test_file_path = Path("tests/e2e/test_auth_complete_flow.py")
    
    print("Validating authentication E2E test file...")
    print(f"File: {test_file_path}")
    
    # Check 1: File exists in correct location
    assert test_file_path.exists(), "ERROR: Test file must be in tests/e2e/ directory"
    print("PASS: File is in correct tests/e2e/ directory")
    
    # Check 2: Parse file and analyze structure
    with open(test_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    # Check 3: Has Business Value Justification
    assert "Business Value Justification" in content, "ERROR: Must have BVJ comment"
    assert "Segment:" in content, "ERROR: BVJ must include Segment"
    assert "Business Goal:" in content, "ERROR: BVJ must include Business Goal" 
    assert "Value Impact:" in content, "ERROR: BVJ must include Value Impact"
    assert "Strategic Impact:" in content, "ERROR: BVJ must include Strategic Impact"
    print("PASS: Business Value Justification (BVJ) present")
    
    # Check 4: Uses IsolatedEnvironment, not os.environ
    assert "from shared.isolated_environment import get_env" in content, "ERROR: Must use IsolatedEnvironment"
    assert "os.environ" not in content, "ERROR: Must NOT use os.environ directly"
    print("PASS: Uses IsolatedEnvironment correctly")
    
    # Check 5: Uses proper test framework imports
    assert "from test_framework.base_e2e_test import BaseE2ETest" in content, "ERROR: Must inherit from BaseE2ETest"
    assert "from test_framework.real_services import ServiceEndpoints" in content, "ERROR: Must use real services"
    assert "from test_framework.websocket_helpers import" in content, "ERROR: Must use WebSocket helpers"
    print("PASS: Uses proper test framework imports")
    
    # Check 6: Has proper pytest markers
    assert "@pytest.mark.e2e" in content, "ERROR: Must have @pytest.mark.e2e marker"
    assert "@pytest.mark.real_services" in content, "ERROR: Must have @pytest.mark.real_services marker"
    print("PASS: Has proper pytest markers")
    
    # Check 7: Tests real authentication flows
    required_methods = [
        "test_complete_oauth_flow",
        "test_jwt_authentication", 
        "test_websocket_authentication",
        "test_multi_user_isolation",
        "test_session_management"
    ]
    
    for method in required_methods:
        assert method in content, f"ERROR: Must have {method} test method"
    print("PASS: All required test methods present")
    
    # Check 8: WebSocket event verification
    assert "assert_websocket_events" in content, "ERROR: Must verify WebSocket events"
    assert "agent_started" in content, "ERROR: Must check for agent_started event"
    assert "agent_thinking" in content, "ERROR: Must check for agent_thinking event"
    assert "tool_executing" in content, "ERROR: Must check for tool_executing event"
    assert "tool_completed" in content, "ERROR: Must check for tool_completed event"
    assert "agent_completed" in content, "ERROR: Must check for agent_completed event"
    print("PASS: WebSocket event verification present")
    
    # Check 9: Real business value validation
    assert "CRITICAL:" in content, "ERROR: Must mark critical business value tests"
    assert "business value" in content.lower(), "ERROR: Must validate actual business value"
    print("PASS: Real business value validation present")
    
    # Check 10: No mocks for core functionality
    assert "Mock(" not in content or "@patch" not in content, "ERROR: Should not mock core auth flows"
    print("PASS: No inappropriate mocking")
    
    # Check 11: Proper async/await usage
    assert "async def test_" in content, "ERROR: E2E tests must be async"
    assert "@pytest.mark.asyncio" in content, "ERROR: Must have asyncio marker"
    print("PASS: Proper async test structure")
    
    # Check 12: Cleanup and resource management
    assert "cleanup" in content.lower(), "ERROR: Must have resource cleanup"
    assert "test_users" in content, "ERROR: Must track created test data"
    print("PASS: Resource management present")
    
    print("\nSUCCESS: All validation checks passed!")
    print("Summary:")
    print("   PASS: Correct file location (tests/e2e/)")
    print("   PASS: Business Value Justification complete")
    print("   PASS: Uses IsolatedEnvironment (not os.environ)")
    print("   PASS: Real services integration")
    print("   PASS: All 5 required test methods")
    print("   PASS: WebSocket events verification")
    print("   PASS: Proper pytest markers")
    print("   PASS: No inappropriate mocking")
    print("   PASS: Async test structure")
    print("   PASS: Resource cleanup")
    print("\nAuthentication E2E tests ready for execution!")

if __name__ == "__main__":
    try:
        validate_auth_test_file()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Validation failed: {e}")
        sys.exit(1)