from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Run critical authentication cross-system E2E tests against GCP staging environment
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_staging_environment():
    """Set up environment variables for staging tests"""
    # Set staging environment variables
    staging_env = {
        "BACKEND_URL": "https://netra-backend-staging-pnovr5vsba-uc.a.run.app",
        "AUTH_SERVICE_URL": "https://netra-auth-staging-pnovr5vsba-uc.a.run.app", 
        "TEST_ENV": "staging",
        "USE_REAL_LLM": "true",
        "SERVICE_SECRET": "xNp9hKjT5mQ8w2fE7vR4yU3iO6aS1gL9cB0zZ8tN6wX2eR4vY7uI0pQ3s9dF5gH8",
        "JWT_SECRET_KEY": "rsWwwvq8X6mCSuNv-TMXHDCfb96Xc-Dbay9MZy6EDCU",
        "ENVIRONMENT": "staging",
        "TESTING": "false",  # Don't override with test environment
        "SKIP_STARTUP_CHECKS": "false",
        "AUTH_SERVICE_ENABLED": "true",
        "AUTH_FAST_TEST_MODE": "false",
    }
    
    # Update environment
    for key, value in staging_env.items():
        os.environ[key] = value
        print(f"Set {key}={value}")
    
    return staging_env

def run_critical_auth_tests():
    """Run the critical auth cross-system tests"""
    try:
        # Change to project root
        project_root = Path(__file__).parent
        os.chdir(project_root)
        
        # Setup environment
        setup_staging_environment()
        
        # Run pytest with the specific test file
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/critical/test_auth_cross_system_failures.py",
            "-v", "-s", 
            "--tb=short",
            "--no-header",
            "--capture=no"
        ]
        
        print(f"\nRunning command: {' '.join(cmd)}")
        print(f"Working directory: {os.getcwd()}")
        print("\n" + "="*80)
        print("STARTING CRITICAL AUTH CROSS-SYSTEM E2E TESTS")
        print("="*80)
        
        # Run the tests
        result = subprocess.run(cmd, capture_output=False)
        
        print("\n" + "="*80)
        print(f"TESTS COMPLETED - Exit code: {result.returncode}")
        print("="*80)
        
        return result.returncode
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_critical_auth_tests()
    sys.exit(exit_code)
