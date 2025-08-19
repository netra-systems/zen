#!/usr/bin/env python3
"""
JWT Token Lifecycle E2E Test Runner

Quick runner for the Token Refresh During Active Session test.
Demonstrates the implemented E2E test functionality.
"""

import subprocess
import sys
import os

def main():
    """Run JWT token lifecycle E2E tests."""
    
    print("🔐 JWT Token Lifecycle E2E Test Runner")
    print("=====================================")
    print()
    
    # Test file path
    test_file = "tests/unified/e2e/test_token_lifecycle.py"
    
    print(f"Running tests from: {test_file}")
    print()
    
    # Test commands
    test_commands = [
        {
            "name": "🚀 Main Token Refresh Test",
            "cmd": [
                "python", "-m", "pytest", 
                f"{test_file}::TestTokenLifecycleE2E::test_token_refresh_during_active_session",
                "-v", "-s"
            ]
        },
        {
            "name": "⚡ Performance Benchmark",
            "cmd": [
                "python", "-m", "pytest",
                f"{test_file}::TestTokenLifecycleE2E::test_token_refresh_performance_benchmark", 
                "-v", "-s"
            ]
        },
        {
            "name": "🔄 Race Condition Test",
            "cmd": [
                "python", "-m", "pytest",
                f"{test_file}::TestTokenLifecycleE2E::test_concurrent_token_refresh_race_conditions",
                "-v", "-s"
            ]
        }
    ]
    
    for test in test_commands:
        print(f"Running: {test['name']}")
        print(f"Command: {' '.join(test['cmd'])}")
        print("-" * 50)
        
        try:
            result = subprocess.run(
                test['cmd'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("✅ PASSED")
            else:
                print("❌ FAILED")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print("⏰ TIMEOUT - Test took longer than 60 seconds")
        except Exception as e:
            print(f"💥 ERROR: {e}")
        
        print()
        print("=" * 50)
        print()

if __name__ == "__main__":
    main()