#!/usr/bin/env python3
import subprocess
import json

def count_tests(path):
    """Count tests in a given path."""
    try:
        result = subprocess.run(['python3', '-m', 'pytest', path, '--collect-only', '-q'], 
                               capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            test_count = len([line for line in result.stdout.split('\n') if '.py::' in line])
            return test_count, "success"
        else:
            return 0, f"collection_failed: {result.stderr[:200]}"
    except Exception as e:
        return 0, f"error: {str(e)[:200]}"

def run_tests(path):
    """Run tests and measure success rate."""
    try:
        result = subprocess.run(['python3', '-m', 'pytest', path, '-x', '--tb=no', '-q'], 
                               capture_output=True, text=True, timeout=120)
        lines = result.stdout.split('\n')
        
        # Parse results
        for line in lines:
            if 'failed' in line and 'passed' in line:
                # Extract numbers
                parts = line.split()
                passed = failed = 0
                for i, part in enumerate(parts):
                    if 'failed' in part:
                        try:
                            failed = int(parts[i-1])
                        except:
                            pass
                    elif 'passed' in part:
                        try:
                            passed = int(parts[i-1])
                        except:
                            pass
                total = passed + failed
                if total > 0:
                    success_rate = passed / total * 100
                    return passed, failed, total, success_rate, "completed"
                    
        return 0, 0, 0, 0, f"parse_failed: {result.stdout[-200:]}"
    except Exception as e:
        return 0, 0, 0, 0, f"error: {str(e)[:200]}"

# Test different paths
test_paths = [
    'tests/mission_critical/',
    'shared/tests/',
    'auth_service/tests/unit/',
]

print("=== TEST INFRASTRUCTURE VALIDATION ===")
print()

for path in test_paths:
    print(f"Path: {path}")
    count, count_status = count_tests(path)
    print(f"  Tests Found: {count} ({count_status})")
    
    if count > 0:
        passed, failed, total, success_rate, status = run_tests(path)
        print(f"  Execution: {passed} passed, {failed} failed, {total} total")
        print(f"  Success Rate: {success_rate:.1f}% ({status})")
    
    print()