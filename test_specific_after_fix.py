#!/usr/bin/env python3
"""
Test specific test files after the fix to ensure functionality is preserved.
"""
import subprocess
import sys

def test_specific_file(filepath):
    """Test a specific file."""
    print(f"Testing {filepath}...")

    result = subprocess.run([
        sys.executable, '-m', 'pytest',
        filepath, '-v', '--tb=short'
    ], capture_output=True, text=True, timeout=60)

    print(f"  Exit code: {result.returncode}")

    if result.returncode == 0:
        stdout_lines = result.stdout.strip().split('\n')
        collected_line = [l for l in stdout_lines if 'collected' in l.lower()]
        if collected_line:
            print(f"  {collected_line[0]}")
        passed_line = [l for l in stdout_lines if 'passed' in l and '=' in l]
        if passed_line:
            print(f"  {passed_line[0]}")
        else:
            print("  Status: Tests collected but no execution summary found")
    else:
        print(f"  Error: {result.stderr[:200]}...")

    return result.returncode == 0

def main():
    """Test several files to ensure functionality."""

    test_files = [
        'netra_backend/tests/test_agent_response_serialization.py',
        'netra_backend/tests/test_basic_health_endpoint.py',
        'netra_backend/tests/unit/websocket/test_message_queue_resilience.py'
    ]

    print("Testing functionality of renamed test classes...")
    print("=" * 60)

    results = []
    for filepath in test_files:
        success = test_specific_file(filepath)
        results.append((filepath, success))
        print()

    print("Summary:")
    print("-" * 30)
    for filepath, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} {filepath}")

if __name__ == "__main__":
    main()