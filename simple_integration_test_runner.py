#!/usr/bin/env python3
"""
Simple Integration Test Runner for Golden Path functionality
Focuses on running integration tests without Docker dependencies
"""

import sys
import os
import subprocess
from pathlib import Path

# Set up the project path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def run_test_file(test_file_path):
    """Run a single test file and capture results"""
    try:
        cmd = [sys.executable, "-m", "pytest", str(test_file_path), "-v", "--tb=short", "--maxfail=3"]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=PROJECT_ROOT
        )
        
        return {
            'file': test_file_path,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            'file': test_file_path,
            'returncode': -1,
            'stdout': '',
            'stderr': 'Test timed out after 5 minutes'
        }
    except Exception as e:
        return {
            'file': test_file_path,
            'returncode': -1,
            'stdout': '',
            'stderr': f'Error running test: {str(e)}'
        }

def find_golden_path_integration_tests():
    """Find integration tests related to golden path functionality"""
    integration_dir = PROJECT_ROOT / "tests" / "integration"
    golden_path_tests = []
    
    # Look for files with 'golden' in the name
    for test_file in integration_dir.rglob("*golden*.py"):
        if test_file.is_file() and not test_file.name.startswith("__"):
            golden_path_tests.append(test_file)
    
    # Also include some key WebSocket integration tests
    websocket_tests = [
        integration_dir / "websocket" / "test_golden_path_preservation.py",
        integration_dir / "test_websocket_ssot_golden_path.py",
    ]
    
    for test_file in websocket_tests:
        if test_file.exists() and test_file not in golden_path_tests:
            golden_path_tests.append(test_file)
    
    return golden_path_tests

def main():
    """Main test runner"""
    print("Simple Integration Test Runner for Golden Path")
    print("=" * 50)
    
    # Find golden path integration tests
    test_files = find_golden_path_integration_tests()
    
    if not test_files:
        print("No golden path integration tests found!")
        return 1
    
    print(f"Found {len(test_files)} golden path integration tests:")
    for test_file in test_files:
        print(f"  - {test_file.relative_to(PROJECT_ROOT)}")
    
    print("\nRunning tests...")
    print("-" * 30)
    
    results = []
    passed = 0
    failed = 0
    
    for test_file in test_files:
        print(f"\nRunning: {test_file.name}")
        result = run_test_file(test_file)
        results.append(result)
        
        if result['returncode'] == 0:
            print("✅ PASSED")
            passed += 1
        else:
            print("❌ FAILED")
            failed += 1
            if result['stderr']:
                print(f"Error: {result['stderr'][:200]}...")
    
    # Summary
    print("\n" + "=" * 50)
    print("GOLDEN PATH INTEGRATION TEST SUMMARY")
    print("=" * 50)
    print(f"Total tests: {len(test_files)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for result in results:
            if result['returncode'] != 0:
                print(f"  - {Path(result['file']).name}")
                if result['stderr']:
                    print(f"    Error: {result['stderr'][:100]}...")
    
    return 1 if failed > 0 else 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)