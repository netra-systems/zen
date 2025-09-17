#!/usr/bin/env python3
"""Test E2E critical test collection to validate timeout fixes."""

import sys
import subprocess
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_e2e_collection():
    """Test if e2e critical tests can be collected without errors."""
    print("Testing E2E critical test collection...")
    
    # Set staging environment
    os.environ['ENVIRONMENT'] = 'staging'
    
    try:
        # Try pytest collection only (doesn't run tests, just checks if they can be loaded)
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/e2e/critical/test_service_health_critical.py',
            '--collect-only', '--quiet'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ PASS: E2E critical test collection successful")
            print("✅ This suggests timeout configuration is loading correctly")
            print(f"   Collected output: {result.stdout[:200]}...")
            return True
        else:
            print("❌ FAIL: E2E critical test collection failed")
            print(f"   Return code: {result.returncode}")
            print(f"   Stderr: {result.stderr}")
            print(f"   Stdout: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Test collection took too long (>30s)")
        return False
    except Exception as e:
        print(f"❌ ERROR: Collection test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_e2e_collection()
    sys.exit(0 if success else 1)