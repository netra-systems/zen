#!/usr/bin/env python
"""Run tests and get summary of failures"""

import sys
import os
sys.path.insert(0, '.')
os.environ["TESTING"] = "1"

import pytest

# Run tests and capture results
print("Running all backend tests...")
result = pytest.main([
    'app/tests',
    '--tb=no',
    '-q',
    '--no-header',
    '--co'  # Collect only to check for import errors
])

if result != 0:
    print(f"\nCollection failed with exit code: {result}")
    print("Running tests with collection errors skipped...")

# Now run the actual tests
result = pytest.main([
    'app/tests',
    '--tb=no',
    '-q',
    '--no-header',
    '--json-report',
    '--json-report-file=test_results.json'
])

# Read results from JSON report
import json
try:
    with open('.pytest_cache/test_results.json', 'r') as f:
        data = json.load(f)
        summary = data.get('summary', {})
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total tests: {summary.get('total', 0)}")
        print(f"Passed: {summary.get('passed', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Errors: {summary.get('error', 0)}")
        print(f"Skipped: {summary.get('skipped', 0)}")
        
        if summary.get('failed', 0) > 0:
            print("\nFailed tests:")
            for test in data.get('tests', []):
                if test.get('outcome') == 'failed':
                    print(f"  - {test.get('nodeid')}")
                    
except FileNotFoundError:
    print("\nNo JSON report found. Test summary:")
    print(f"Exit code: {result}")
    if result == 0:
        print("All tests passed!")
    elif result == 1:
        print("Some tests failed.")
    elif result == 2:
        print("Test execution was interrupted.")
    elif result == 3:
        print("Internal error during test execution.")
    elif result == 4:
        print("Pytest command line usage error.")
    elif result == 5:
        print("No tests were collected.")

sys.exit(result)