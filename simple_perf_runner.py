#!/usr/bin/env python3
"""
Simple Performance Test Runner
Runs performance tests without loading the full application stack to avoid import issues.
"""

import sys
import subprocess
import os
from pathlib import Path

def run_performance_tests():
    """Run performance tests with minimal dependencies"""
    
    # Set Python path to include the app directory
    current_dir = Path(__file__).parent
    app_dir = current_dir / "app"
    sys.path.insert(0, str(current_dir))
    sys.path.insert(0, str(app_dir))
    
    # Set environment variables to avoid loading full app
    os.environ['TESTING'] = '1'
    os.environ['SKIP_APP_INIT'] = '1'
    
    performance_test_files = [
        'app/tests/performance/test_benchmark_metrics.py',
        'app/tests/performance/test_database_performance.py',
        'app/tests/performance/test_concurrent_processing.py',
        'app/tests/performance/test_corpus_generation_perf.py',
        'app/tests/performance/test_large_scale_generation.py',
        'app/tests/performance/test_agent_load_stress.py'
    ]
    
    results = []
    
    for test_file in performance_test_files:
        if not os.path.exists(test_file):
            print(f"WARNING: Test file not found: {test_file}")
            continue
            
        print(f"\nRunning {test_file}...")
        
        try:
            # Run pytest with minimal configuration
            cmd = [
                sys.executable, '-m', 'pytest', 
                test_file,
                '--no-cov',
                '--tb=short',
                '-v',
                '--disable-warnings',
                '--no-header',
                '--override-ini', 'python_files=test_*.py',
                '--ignore-glob=*conftest.py',
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout per test file
            )
            
            results.append({
                'file': test_file,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
            if result.returncode == 0:
                print(f"PASSED: {test_file}")
            else:
                print(f"FAILED: {test_file}")
                if result.stdout:
                    print(f"Output: {result.stdout[:500]}...")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}...")
                
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: {test_file}")
            results.append({
                'file': test_file,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Test timed out after 5 minutes'
            })
        except Exception as e:
            print(f"ERROR: {test_file} - {e}")
            results.append({
                'file': test_file,
                'returncode': -2,
                'stdout': '',
                'stderr': str(e)
            })
    
    # Print summary
    print("\n" + "="*80)
    print("PERFORMANCE TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['returncode'] == 0)
    failed = sum(1 for r in results if r['returncode'] != 0)
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFAILED TESTS:")
        for result in results:
            if result['returncode'] != 0:
                print(f"  - {result['file']}")
                if result['stderr']:
                    print(f"    Error: {result['stderr'][:200]}...")
    
    return results

if __name__ == "__main__":
    results = run_performance_tests()
    failed_count = sum(1 for r in results if r['returncode'] != 0)
    sys.exit(failed_count)