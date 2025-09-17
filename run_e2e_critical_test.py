#!/usr/bin/env python3
"""
Script to run critical e2e tests and capture output
"""
import subprocess
import sys
import os

def run_critical_e2e_tests():
    """Run critical e2e tests with staging environment"""
    print("Setting up environment for staging...")
    
    # Set environment variables for staging
    env = os.environ.copy()
    env['ENVIRONMENT'] = 'staging'
    env['TEST_TARGET'] = 'staging'
    env['TEST_ENVIRONMENT'] = 'staging'
    
    print("Running critical e2e tests...")
    
    try:
        # Try unified test runner first
        result = subprocess.run([
            sys.executable, 'tests/unified_test_runner.py', 
            '--category', 'e2e', 
            '--fast-fail', 
            '--no-coverage'
        ], env=env, capture_output=True, text=True, timeout=300)
        
        print("=== UNIFIED TEST RUNNER OUTPUT ===")
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
    except Exception as e:
        print(f"Unified test runner failed: {e}")
        
        # Fallback to direct pytest
        print("\nTrying direct pytest...")
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                'tests/e2e/critical/', 
                '-v', '--tb=short', '-x'
            ], env=env, capture_output=True, text=True, timeout=300)
            
            print("=== DIRECT PYTEST OUTPUT ===")
            print("STDOUT:")
            print(result.stdout)
            print("\nSTDERR:")
            print(result.stderr)
            print(f"\nReturn code: {result.returncode}")
            
        except Exception as e2:
            print(f"Direct pytest also failed: {e2}")

if __name__ == "__main__":
    run_critical_e2e_tests()