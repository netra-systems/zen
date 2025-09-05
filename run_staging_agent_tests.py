#!/usr/bin/env python
"""Run top 5 critical agent E2E tests against staging environment"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set staging environment variables
os.environ['ENVIRONMENT'] = 'staging'
os.environ['TEST_MODE'] = 'real'
os.environ['USE_REAL_SERVICES'] = 'true'
os.environ['USE_REAL_LLM'] = 'true'
os.environ['SKIP_MOCKS'] = 'true'
os.environ['STAGING_AUTH_URL'] = 'https://api.staging.netrasystems.ai'
os.environ['STAGING_BACKEND_URL'] = 'https://api.staging.netrasystems.ai'
os.environ['STAGING_WEBSOCKET_URL'] = 'wss://api.staging.netrasystems.ai/ws'

# Top 5 critical agent E2E tests based on business value
CRITICAL_TESTS = [
    "tests/e2e/test_critical_agent_chat_flow.py",
    "tests/e2e/test_websocket_agent_events_e2e.py", 
    "tests/e2e/test_agent_pipeline_critical.py",
    "tests/e2e/test_multi_agent_orchestration_e2e.py",
    "tests/e2e/test_critical_websocket_agent_events.py"
]

def run_test(test_path):
    """Run a single test file against staging"""
    print(f"\n{'='*60}")
    print(f"Running: {test_path}")
    print('='*60)
    
    cmd = [
        sys.executable,
        "tests/unified_test_runner.py",
        "--env", "staging",
        "--real-llm",
        "--category", "e2e",
        "--pattern", Path(test_path).stem,
        "--no-coverage",
        "--fast-fail"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300  # 5 minute timeout per test
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: Test {test_path} exceeded 5 minute limit")
        return False
    except Exception as e:
        print(f"ERROR running test: {e}")
        return False

def main():
    """Run all critical agent tests"""
    print("\n" + "="*60)
    print("RUNNING TOP 5 CRITICAL AGENT E2E TESTS AGAINST STAGING")
    print("="*60)
    
    results = {}
    
    for test_path in CRITICAL_TESTS:
        # Check if test file exists
        full_path = PROJECT_ROOT / test_path
        if not full_path.exists():
            print(f"WARNING: Test file not found: {test_path}")
            results[test_path] = "NOT_FOUND"
            continue
            
        success = run_test(test_path)
        results[test_path] = "PASSED" if success else "FAILED"
    
    # Print summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for test, status in results.items():
        test_name = Path(test).stem
        status_symbol = "[PASS]" if status == "PASSED" else "[FAIL]" if status == "FAILED" else "[WARN]"
        print(f"{status_symbol} {test_name}: {status}")
    
    # Overall result
    passed = sum(1 for s in results.values() if s == "PASSED")
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] ALL CRITICAL TESTS PASSED!")
        return 0
    else:
        print("[ERROR] SOME TESTS FAILED - STAGING DEPLOYMENT MAY BE BROKEN")
        return 1

if __name__ == "__main__":
    sys.exit(main())