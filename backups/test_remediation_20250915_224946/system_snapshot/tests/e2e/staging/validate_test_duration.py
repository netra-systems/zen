#!/usr/bin/env python
"""
Test Duration Validator
Ensures tests are making real network calls by checking execution time
"""

import json
import sys
from pathlib import Path


def validate_test_durations(json_report_path: str, min_duration: float = 0.01):
    """Validate that tests take real time to execute"""
    
    with open(json_report_path) as f:
        data = json.load(f)
    
    tests = data.get('tests', [])
    fake_tests = []
    
    for test in tests:
        duration = test.get('duration', 0)
        if duration < min_duration:
            fake_tests.append({
                'name': test.get('nodeid', 'unknown'),
                'duration': duration
            })
    
    if fake_tests:
        print("[!] FAKE TESTS DETECTED!")
        print(f"   {len(fake_tests)} tests completed in < {min_duration}s")
        print("   These tests are NOT making real network calls!")
        print("\nFake tests:")
        for test in fake_tests[:10]:  # Show first 10
            print(f"   - {test['name']}: {test['duration']:.3f}s")
        
        return 1  # Exit with error
    
    print("[OK] All tests have realistic durations")
    return 0


if __name__ == "__main__":
    import sys
    report_path = sys.argv[1] if len(sys.argv) > 1 else "test_results.json"
    sys.exit(validate_test_durations(report_path))
