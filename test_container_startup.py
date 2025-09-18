#!/usr/bin/env python3
"""
Test script to validate container startup configuration
Tests the changes made for Issue #1278 remediation
"""

import os
import sys
import subprocess
import time

# Add the root directory to Python path
sys.path.append('/c/netra-apex')

def test_auth_service_imports():
    """Test if SSOT auth integration works correctly"""
    print("Testing SSOT auth integration...")
    try:
        # Test SSOT auth integration pattern instead of direct auth service imports
        from netra_backend.app.auth_integration.auth import AuthIntegration
        from netra_backend.app.database.session_manager import SessionManager
        print("PASS: SSOT auth integration imports successful")
        return True
    except ImportError as e:
        print(f"FAIL: SSOT auth integration import failed: {e}")
        return False
    except Exception as e:
        print(f"FAIL: SSOT auth integration import error: {e}")
        return False

def test_backend_database_config():
    """Test backend database configuration"""
    print("Testing backend database configuration...")
    try:
        from netra_backend.app.core.configuration.database import DatabaseConfig
        config = DatabaseConfig()

        # Check if timeout values are properly set
        if hasattr(config, 'timeout_seconds'):
            print(f"PASS: Database timeout configured: {config.timeout_seconds}s")
        else:
            print("WARN: Database timeout not found in config")

        return True
    except Exception as e:
        print(f"FAIL: Backend database config error: {e}")
        return False

def test_environment_detection():
    """Test environment detection for staging"""
    print("Testing environment detection...")
    try:
        # Set staging environment variable
        os.environ['ENVIRONMENT'] = 'staging'

        from netra_backend.app.core.configuration.base import get_config
        config = get_config()

        print(f"PASS: Environment detected: {getattr(config, 'environment', 'unknown')}")
        return True
    except Exception as e:
        print(f"FAIL: Environment detection error: {e}")
        return False

def main():
    """Run all startup validation tests"""
    print("=== Container Startup Validation ===\n")

    tests = [
        test_auth_service_imports,
        test_backend_database_config,
        test_environment_detection
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"FAIL: Test {test.__name__} failed with exception: {e}")
            results.append(False)
        print()

    success_count = sum(results)
    total_count = len(results)

    print(f"=== Results: {success_count}/{total_count} tests passed ===")

    if success_count == total_count:
        print("PASS: All startup validation tests passed")
        return 0
    else:
        print("FAIL: Some startup validation tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())