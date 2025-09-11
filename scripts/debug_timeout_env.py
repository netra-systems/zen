#!/usr/bin/env python3
"""Debug timeout environment detection."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_environment():
    """Debug environment detection."""
    
    print("Debug Environment Detection")
    print("="*40)
    
    # Test environment variables
    print("Environment variables:")
    print(f"  ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'NOT SET')}")
    print(f"  PYTEST_CURRENT_TEST: {os.environ.get('PYTEST_CURRENT_TEST', 'NOT SET')}")
    print(f"  TESTING: {os.environ.get('TESTING', 'NOT SET')}")
    
    # Test shared isolated environment
    from shared.isolated_environment import get_env
    env = get_env()
    print(f"\nIsolated environment:")
    print(f"  ENVIRONMENT: {env.get('ENVIRONMENT', 'NOT SET')}")
    print(f"  PYTEST_CURRENT_TEST: {env.get('PYTEST_CURRENT_TEST', 'NOT SET')}")
    print(f"  TESTING: {env.get('TESTING', 'NOT SET')}")
    
    # Test timeout manager
    print(f"\nTesting different environments:")
    
    environments = ["staging", "production", "testing", "development"]
    
    for test_env in environments:
        print(f"\n--- Testing {test_env} ---")
        os.environ["ENVIRONMENT"] = test_env
        
        from netra_backend.app.core.timeout_configuration import reset_timeout_manager, get_timeout_hierarchy_info
        reset_timeout_manager()
        
        info = get_timeout_hierarchy_info()
        print(f"  Detected environment: {info['environment']}")
        print(f"  WebSocket timeout: {info['websocket_recv_timeout']}s")
        print(f"  Agent timeout: {info['agent_execution_timeout']}s")
        print(f"  Hierarchy valid: {info['hierarchy_valid']}")

if __name__ == "__main__":
    debug_environment()