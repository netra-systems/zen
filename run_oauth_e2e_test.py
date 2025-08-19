#!/usr/bin/env python3
"""
OAuth E2E Test Runner - For running the real OAuth Google flow test

Usage:
    python run_oauth_e2e_test.py

This script runs the critical E2E OAuth test that validates:
- Real OAuth flow with Google provider simulation
- Token exchange across Auth and Backend services
- Profile sync and dashboard loading
- Chat history retrieval

Business Value: $100K MRR - Enterprise SSO requirement
"""

import subprocess
import sys
import os


def run_oauth_e2e_test():
    """Run the OAuth E2E test with proper configuration."""
    
    print("🚀 Running OAuth E2E Test - Critical for $100K MRR Enterprise customers")
    print("=" * 70)
    
    # Set up environment
    os.environ["PYTEST_CURRENT_TEST"] = "oauth_e2e"
    
    # Test command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unified/e2e/test_real_oauth_google_flow.py",
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--disable-warnings",
        "-m", "e2e and oauth"  # Run only OAuth E2E tests
    ]
    
    try:
        print(f"📋 Command: {' '.join(cmd)}")
        print("⏳ Starting OAuth E2E test execution...")
        print("-" * 50)
        
        # Run the test
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 70)
            print("✅ OAuth E2E Test: SUCCESS")
            print("✅ $100K MRR Enterprise OAuth flow: PROTECTED")
            print("✅ Enterprise SSO requirements: VALIDATED")
        else:
            print("\n" + "=" * 70)
            print("❌ OAuth E2E Test: FAILED")
            print("⚠️  $100K MRR at risk - OAuth integration issues detected")
            print("🔧 Review test output above for specific failures")
            
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n🛑 Test execution cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test execution error: {e}")
        return 1


def run_oauth_performance_test():
    """Run only the OAuth performance validation."""
    
    print("⚡ Running OAuth Performance Test - <5 second requirement")
    print("=" * 70)
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unified/e2e/test_real_oauth_google_flow.py::test_oauth_flow_performance_target",
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ OAuth Performance Test: SUCCESS - <5s requirement met")
        else:
            print("\n❌ OAuth Performance Test: FAILED - Performance issues detected")
            
        return result.returncode
        
    except Exception as e:
        print(f"\n❌ Performance test error: {e}")
        return 1


def run_oauth_security_test():
    """Run only the OAuth security validation."""
    
    print("🔒 Running OAuth Security Test - Token validation across services")
    print("=" * 70)
    
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/unified/e2e/test_real_oauth_google_flow.py::test_oauth_token_security",
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ OAuth Security Test: SUCCESS - Enterprise security validated")
        else:
            print("\n❌ OAuth Security Test: FAILED - Security vulnerabilities detected")
            
        return result.returncode
        
    except Exception as e:
        print(f"\n❌ Security test error: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "performance":
            exit_code = run_oauth_performance_test()
        elif test_type == "security":
            exit_code = run_oauth_security_test()
        elif test_type == "full":
            exit_code = run_oauth_e2e_test()
        else:
            print("Usage: python run_oauth_e2e_test.py [full|performance|security]")
            print("  full        - Run complete OAuth E2E test suite (default)")
            print("  performance - Run only performance validation (<5s)")
            print("  security    - Run only security validation") 
            exit_code = 1
    else:
        # Default: run full OAuth E2E test
        exit_code = run_oauth_e2e_test()
    
    sys.exit(exit_code)