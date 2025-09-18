#!/usr/bin/env python3
"""Direct test runner to execute agent and e2e tests for staging."""

import subprocess
import sys
import os
from pathlib import Path

# Set up the project root
PROJECT_ROOT = Path(__file__).parent.absolute()
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

def run_test(test_path, test_name):
    """Run a specific test and capture output."""
    cmd = [sys.executable, '-m', 'pytest', test_path, '-v', '--tb=short']
    
    print(f"\n{'='*60}")
    print(f"RUNNING: {test_name}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print(f"Return code: {result.returncode}")
        print(f"\nSTDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")
            
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("Test timed out after 5 minutes")
        return False, "", "Timeout"
    except Exception as e:
        print(f"Error running test: {e}")
        return False, "", str(e)

def main():
    """Main test runner."""
    print("NETRA APEX TEST EXECUTION")
    print("=" * 60)
    
    # Define tests to run
    tests = [
        ("netra_backend/tests/agents/test_supervisor_basic.py", "Basic Supervisor Agent Test"),
        ("netra_backend/tests/agents/test_base_agent_initialization.py", "Base Agent Initialization Test"),
        ("tests/e2e/staging/test_golden_path_staging.py", "Golden Path Staging E2E Test"),
        ("tests/e2e/gcp_staging/test_unified_test_runner_gcp_staging.py", "GCP Staging Test"),
    ]
    
    results = []
    
    for test_path, test_name in tests:
        if os.path.exists(test_path):
            success, stdout, stderr = run_test(test_path, test_name)
            results.append((test_name, test_path, success, stdout, stderr))
        else:
            print(f"SKIPPING {test_name}: File not found at {test_path}")
            results.append((test_name, test_path, False, "", "File not found"))
    
    # Summary
    print("\n" + "="*60)
    print("TEST EXECUTION SUMMARY")
    print("="*60)
    
    for test_name, test_path, success, stdout, stderr in results:
        status = "PASSED" if success else "FAILED"
        print(f"{test_name}: {status}")
        
        if not success and stderr:
            print(f"  Error: {stderr[:200]}...")
    
    # Detailed results
    print("\n" + "="*60)
    print("DETAILED RESULTS")
    print("="*60)
    
    for test_name, test_path, success, stdout, stderr in results:
        print(f"\n{test_name} ({test_path}):")
        print(f"Status: {'PASSED' if success else 'FAILED'}")
        
        if stdout:
            print("Output:")
            print(stdout[:1000] + ("..." if len(stdout) > 1000 else ""))
        
        if stderr:
            print("Errors:")
            print(stderr[:1000] + ("..." if len(stderr) > 1000 else ""))

if __name__ == "__main__":
    main()