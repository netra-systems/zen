#!/usr/bin/env python3
"""
Fast Auth Service Test Runner
Optimizes auth service startup for E2E testing by setting appropriate environment variables.
"""
import os
import subprocess
import sys
from pathlib import Path


def set_fast_auth_environment():
    """Set environment variables for fast auth service testing"""
    os.environ.update({
        "AUTH_FAST_TEST_MODE": "true",
        "ENVIRONMENT": "test", 
        "AUTH_SERVICE_ENABLED": "true",
        "SQL_ECHO": "false",
        "JWT_SECRET": "test-secret-key-for-testing-only",
        "AUTH_CACHE_TTL_SECONDS": "60",  # Shorter cache for testing
    })

def main():
    """Run tests with optimized auth service configuration"""
    set_fast_auth_environment()
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Default test command if none provided
    if len(sys.argv) < 2:
        test_command = [
            "python", "-m", "pytest", 
            "app/tests/auth_integration/",
            "-v", "--tb=short"
        ]
    else:
        # Use provided command
        test_command = sys.argv[1:]
    
    print("🚀 Running tests with optimized auth service configuration...")
    print(f"Command: {' '.join(test_command)}")
    print("Environment:")
    for key, value in sorted(os.environ.items()):
        if "AUTH" in key or key in ["ENVIRONMENT", "JWT_SECRET"]:
            display_value = "***" if "SECRET" in key else value
            print(f"  {key}={display_value}")
    
    print("\n" + "="*50)
    
    # Run the test command
    result = subprocess.run(test_command)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())