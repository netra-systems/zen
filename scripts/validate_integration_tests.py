#!/usr/bin/env python3
"""
Validate integration test import fixes.
"""

import subprocess
import sys
from pathlib import Path


def test_file_collection(test_files):
    """Test if files can be collected without import errors."""
    success_count = 0
    failed_files = []
    
    for file in test_files:
        try:
            result = subprocess.run([
                'python', '-m', 'pytest', 
                f'netra_backend/tests/integration/{file}', 
                '--collect-only', '-q'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"SUCCESS: {file}")
                success_count += 1
            else:
                print(f"FAILED: {file}")
                if 'ImportError' in result.stderr or 'ModuleNotFoundError' in result.stderr:
                    print(f"  -> Import error detected")
                failed_files.append(file)
                
        except Exception as e:
            print(f"ERROR: {file} - {e}")
            failed_files.append(file)
    
    return success_count, failed_files


def main():
    """Main validation function."""
    # List of files we know had import issues
    test_files = [
        'test_background_jobs_redis_queue.py',
        'test_circuit_breaker_service_failures.py',
        'test_first_time_user_core.py',
        'test_first_time_user_advanced.py',
        'test_first_time_user_experience.py',
        'test_first_time_user_onboarding.py',
        'test_message_flow_auth_core.py',
        'test_message_flow_auth_helpers.py',
        'test_unified_message_flow_core.py',
        'test_unified_message_flow_helpers.py',
        'test_unified_message_flow_fixtures.py'
    ]
    
    print(f"Validating {len(test_files)} integration test files...\n")
    
    success_count, failed_files = test_file_collection(test_files)
    
    print(f"\n=== VALIDATION SUMMARY ===")
    print(f"Total files tested: {len(test_files)}")
    print(f"Successfully collecting: {success_count}")
    print(f"Still failing: {len(failed_files)}")
    
    if failed_files:
        print(f"\nFailed files:")
        for file in failed_files:
            print(f"  - {file}")
    
    success_rate = (success_count / len(test_files)) * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    if success_rate >= 70:
        print("[U+2713] Major import issues resolved!")
        return 0
    else:
        print("[U+2717] More work needed on import issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())