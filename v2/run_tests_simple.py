#!/usr/bin/env python
"""Run tests and get summary"""

import sys
import os
sys.path.insert(0, '.')
os.environ["TESTING"] = "1"

import pytest

# Run tests with minimal output
print("Running all backend tests...")
result = pytest.main([
    'app/tests',
    '--tb=no',
    '-q',
    '--no-header'
])

print(f"\n\nFinal exit code: {result}")
if result == 0:
    print("✓ All tests passed!")
elif result == 1:
    print("✗ Some tests failed.")
    print("\nTo see which tests failed, run:")
    print("  python -c \"import sys; sys.path.insert(0, '.'); import pytest; pytest.main(['app/tests', '-v', '--tb=short'])\"")
elif result == 2:
    print("✗ Test execution was interrupted.")
elif result == 3:
    print("✗ Internal error during test execution.")
elif result == 4:
    print("✗ Pytest command line usage error.")
elif result == 5:
    print("✗ No tests were collected.")

sys.exit(result)