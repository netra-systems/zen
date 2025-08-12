#!/usr/bin/env python
"""Simple test runner that actually works"""

import os
import sys
import subprocess
import json
from pathlib import Path
import time

# Set testing environment
os.environ.update({
    "TESTING": "1",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "SECRET_KEY": "test-secret-key",
    "JWT_SECRET_KEY": "test-jwt-secret",
    "REDIS_URL": "redis://localhost:6379/1",
    "CLICKHOUSE_URL": "clickhouse://localhost:9000/test",
    "ANTHROPIC_API_KEY": "test-key",
    "ENVIRONMENT": "testing",
    "LOG_LEVEL": "ERROR",
    "FERNET_KEY": "cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao=",
    "ENCRYPTION_KEY": "test-encryption-key-32-chars-long"
})

def run_tests(test_path: str, max_time: int = 30) -> dict:
    """Run tests with timeout protection"""
    print(f"\nRunning: {test_path}")
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=no",
        "--no-header",
        "--no-summary",
        "-q",
        "--disable-warnings",
        "-p", "no:cacheprovider",
        "-p", "no:warnings",
        "--asyncio-mode=auto"
    ]
    
    try:
        start = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max_time,
            cwd=str(Path(__file__).parent)
        )
        duration = time.time() - start
        
        # Parse output
        lines = result.stdout.split('\n')
        passed = 0
        failed = 0
        errors = 0
        
        for line in lines:
            if 'passed' in line.lower():
                try:
                    passed = int(line.split()[0])
                except:
                    pass
            if 'failed' in line.lower():
                try:
                    failed = int(line.split()[0])
                except:
                    pass
            if 'error' in line.lower():
                try:
                    errors = int(line.split()[0])
                except:
                    pass
        
        # If no summary found, check exit code
        if passed == 0 and failed == 0 and errors == 0:
            if result.returncode == 0:
                passed = 1  # Assume at least one test passed
            else:
                failed = 1  # Assume at least one test failed
        
        return {
            "path": test_path,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "duration": duration,
            "exit_code": result.returncode,
            "output": result.stdout[:500]  # First 500 chars
        }
        
    except subprocess.TimeoutExpired:
        return {
            "path": test_path,
            "failed": 1,
            "errors": 0,
            "passed": 0,
            "duration": max_time,
            "exit_code": -1,
            "output": f"TIMEOUT after {max_time}s"
        }
    except Exception as e:
        return {
            "path": test_path,
            "failed": 0,
            "errors": 1,
            "passed": 0,
            "duration": 0,
            "exit_code": -2,
            "output": str(e)
        }

def main():
    """Run key test files to assess current state"""
    print("=" * 60)
    print("SIMPLE TEST RUNNER - Quick Assessment")
    print("=" * 60)
    
    # Priority test files
    test_files = [
        # Core functionality
        "app/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error",
        "app/tests/core/test_config_manager.py::TestConfigManager::test_initialization",
        
        # Critical services  
        "app/tests/services/test_security_service.py::TestSecurityService::test_verify_password",
        
        # Routes
        "app/tests/routes/test_health_route.py::test_live_endpoint",
        
        # System
        "tests/test_system_startup.py::TestSystemStartup::test_configuration_loading",
    ]
    
    results = []
    total_passed = 0
    total_failed = 0
    total_errors = 0
    
    for test_file in test_files:
        # Check if file exists
        file_path = test_file.split("::")[0]
        if not Path(file_path).exists():
            print(f"  [SKIP] {test_file} - File not found")
            continue
            
        result = run_tests(test_file, max_time=10)
        results.append(result)
        
        total_passed += result["passed"]
        total_failed += result["failed"]
        total_errors += result["errors"]
        
        status = "PASS" if result["exit_code"] == 0 else "FAIL"
        print(f"  [{status}] {test_file.split('::')[-1] if '::' in test_file else Path(test_file).name}")
        if result["exit_code"] != 0:
            print(f"       {result['output'][:100]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Errors: {total_errors}")
    
    # Save results
    with open("simple_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: simple_test_results.json")
    
    if total_failed + total_errors > 0:
        print(f"\n[FAILED] {total_failed + total_errors} tests need attention")
        return 1
    else:
        print("\n[SUCCESS] All tests passing!")
        return 0

if __name__ == "__main__":
    sys.exit(main())