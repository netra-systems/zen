#!/usr/bin/env python3
"""
Quick test runner for the JWT critical tests

This script demonstrates that the new test file uses real services
and doesn't rely on mocks or simulations.
"""
import sys
import subprocess
import os
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

def main():
    """Run the critical JWT authentication tests"""
    
    # Set up the environment
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    print("[U+1F680] Running Critical JWT Authentication Tests")
    print("=" * 60)
    print("This test uses REAL services - NO MOCKS!")
    print("- Starts real auth service on port 8081")
    print("- Starts real backend service on port 8200") 
    print("- Makes real HTTP calls for JWT token generation")
    print("- Tests real token validation across services")
    print("- Tests real WebSocket authentication")
    print("=" * 60)
    
    # Run the tests
    test_file = "tests/e2e/critical/test_auth_jwt_critical.py"
    
    try:
        # Run pytest with verbose output
        cmd = [
            sys.executable, "-m", "pytest", 
            test_file,
            "-v",
            "--tb=short",
            "-s",  # Don't capture output
            "--no-header"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        print()
        
        result = subprocess.run(cmd, cwd=project_root)
        
        if result.returncode == 0:
            print()
            print(" PASS:  All JWT authentication tests passed!")
            print(" PASS:  Real services are working correctly!")
        else:
            print()
            print(" FAIL:  Some tests failed - check output above")
            
    except Exception as e:
        print(f" FAIL:  Error running tests: {e}")
        return 1
        
    return result.returncode if 'result' in locals() else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)