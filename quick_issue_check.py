#!/usr/bin/env python3
"""Quick check for common test collection issues"""

import subprocess
import sys
import random
from pathlib import Path

def test_single_file(file_path):
    """Test if a single file can be collected"""
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            '--collect-only', str(file_path), '--tb=short', '-q'
        ], capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            # Extract key error info
            if 'ModuleNotFoundError' in result.stderr:
                error_lines = [line for line in result.stderr.split('\n') if 'ModuleNotFoundError' in line]
                return {'success': False, 'error_type': 'import', 'error': error_lines[0][:150] if error_lines else 'Unknown import error'}
            elif 'ImportError' in result.stderr:
                error_lines = [line for line in result.stderr.split('\n') if 'ImportError' in line]
                return {'success': False, 'error_type': 'import', 'error': error_lines[0][:150] if error_lines else 'Unknown import error'}
            elif 'SyntaxError' in result.stderr:
                return {'success': False, 'error_type': 'syntax', 'error': 'Syntax error'}
            else:
                return {'success': False, 'error_type': 'other', 'error': result.stderr[:200]}

        test_count = result.stdout.count('::test_')
        return {'success': True, 'test_count': test_count}

    except subprocess.TimeoutExpired:
        return {'success': False, 'error_type': 'timeout', 'error': 'Collection timeout'}
    except Exception as e:
        return {'success': False, 'error_type': 'exception', 'error': str(e)[:100]}

def main():
    # Find test files (excluding venv/backups)
    test_files = []
    for pattern in ['**/test_*.py']:
        for file in Path('.').glob(pattern):
            if 'venv' not in str(file) and 'backup' not in str(file):
                test_files.append(file)

    print(f"Found {len(test_files)} test files")

    # Sample 30 files from different directories
    sample_files = random.sample(test_files, min(30, len(test_files)))

    print(f"Testing sample of {len(sample_files)} files...")

    # Test each file
    results = []
    for i, file_path in enumerate(sample_files):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(sample_files)}")

        result = test_single_file(file_path)
        result['file'] = str(file_path)
        results.append(result)

    # Analyze results
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\nResults:")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Success rate: {len(successful) / len(results) * 100:.1f}%")

    # Categorize failures
    if failed:
        error_types = {}
        for failure in failed:
            error_type = failure['error_type']
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(failure)

        print(f"\nFailure types:")
        for error_type, failures in error_types.items():
            print(f"  {error_type}: {len(failures)} files")

        print(f"\nFirst few failures:")
        for failure in failed[:5]:
            print(f"  {failure['file']}: {failure['error_type']} - {failure['error']}")

    # Success stats
    if successful:
        total_tests = sum(r.get('test_count', 0) for r in successful)
        print(f"\nTotal tests in successful files: {total_tests}")

if __name__ == "__main__":
    main()