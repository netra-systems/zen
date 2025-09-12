#!/usr/bin/env python3
"""
Simple Staging Timeout Validation - Issue #404

FOCUSED MISSION: Quick validation that staging timeouts are working correctly.
"""

import os
import sys
from unittest.mock import patch

# Add the project root to Python path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from netra_backend.app.core.timeout_configuration import (
    get_websocket_recv_timeout,
    get_agent_execution_timeout,
    validate_timeout_hierarchy,
    get_timeout_hierarchy_info,
    reset_timeout_manager
)

def main():
    """Simple validation of staging timeout configuration."""
    print("=" * 60)
    print("SIMPLE STAGING TIMEOUT VALIDATION - ISSUE #404")
    print("=" * 60)
    
    # Test staging environment
    with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=False):
        reset_timeout_manager()
        
        print("Environment: staging")
        
        # Get timeout values
        websocket_recv = get_websocket_recv_timeout()
        agent_exec = get_agent_execution_timeout()
        hierarchy_valid = validate_timeout_hierarchy()
        hierarchy_info = get_timeout_hierarchy_info()
        
        print(f"WebSocket recv timeout: {websocket_recv}s")
        print(f"Agent execution timeout: {agent_exec}s")
        print(f"Hierarchy valid: {hierarchy_valid}")
        print(f"Hierarchy gap: {hierarchy_info['hierarchy_gap']}s")
        
        # Validate expected values for staging
        expected_websocket = 35
        expected_agent = 30
        min_gap = 5
        
        websocket_ok = websocket_recv == expected_websocket
        agent_ok = agent_exec == expected_agent
        hierarchy_ok = hierarchy_valid and hierarchy_info['hierarchy_gap'] >= min_gap
        
        print("\nValidation Results:")
        print(f"WebSocket timeout (35s expected): {'PASS' if websocket_ok else 'FAIL'}")
        print(f"Agent timeout (30s expected): {'PASS' if agent_ok else 'FAIL'}")
        print(f"Hierarchy (>5s gap expected): {'PASS' if hierarchy_ok else 'FAIL'}")
        
        all_pass = websocket_ok and agent_ok and hierarchy_ok
        
        print("\n" + "=" * 60)
        if all_pass:
            print("RESULT: ALL PASS - Staging timeouts properly configured")
            print("ASSESSMENT: Race condition resolved (35s > 30s hierarchy)")
            print("RECOMMENDATION: Issue #404 appears to be RESOLVED")
            return 0
        else:
            print("RESULT: SOME FAIL - Staging timeout issues detected")
            print("ASSESSMENT: Race condition may still be present")
            print("RECOMMENDATION: Review timeout configuration")
            return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)