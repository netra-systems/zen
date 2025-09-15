#!/usr/bin/env python3
"""
Test collection performance analysis for Issue #1041.
"""
import subprocess
import time
import sys
import os

def test_collection_performance():
    """Test collection performance on various test directories."""

    test_dirs = [
        'netra_backend/tests/unit/agents',
        'netra_backend/tests/unit/core',
        'netra_backend/tests/unit/services',
        'netra_backend/tests/unit/websocket'
    ]

    results = []

    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            print(f"Directory {test_dir} does not exist, skipping...")
            continue

        print(f"Testing collection on {test_dir}...")
        start_time = time.time()

        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest',
                '--collect-only', '-q', test_dir
            ], capture_output=True, text=True, timeout=45)

            collection_time = time.time() - start_time

            print(f"  Time: {collection_time:.2f}s")
            print(f"  Return code: {result.returncode}")

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                test_count = len([l for l in lines if '::test_' in l or '::Test' in l])
                collected_line = [l for l in lines if 'collected' in l.lower()]
                if collected_line:
                    print(f"  Collection summary: {collected_line[0]}")
                print(f"  Tests found: {test_count}")

                results.append({
                    'directory': test_dir,
                    'time': collection_time,
                    'success': True,
                    'test_count': test_count
                })
            else:
                print(f"  Error: {result.stderr[:300]}...")
                results.append({
                    'directory': test_dir,
                    'time': collection_time,
                    'success': False,
                    'error': result.stderr[:300]
                })

        except subprocess.TimeoutExpired:
            collection_time = time.time() - start_time
            print(f"  TIMEOUT after {collection_time:.2f} seconds!")
            results.append({
                'directory': test_dir,
                'time': collection_time,
                'success': False,
                'timeout': True
            })
        except Exception as e:
            collection_time = time.time() - start_time
            print(f"  Exception: {e}")
            results.append({
                'directory': test_dir,
                'time': collection_time,
                'success': False,
                'exception': str(e)
            })

        print()

    # Summary
    print("=" * 60)
    print("COLLECTION PERFORMANCE SUMMARY")
    print("=" * 60)

    for result in results:
        status = "SUCCESS" if result['success'] else "FAILED"
        print(f"{result['directory']:40} {result['time']:6.2f}s {status}")
        if not result['success']:
            if 'timeout' in result:
                print(f"  -> TIMEOUT")
            elif 'error' in result:
                print(f"  -> ERROR: {result['error'][:100]}...")
            elif 'exception' in result:
                print(f"  -> EXCEPTION: {result['exception']}")

    print()
    avg_time = sum(r['time'] for r in results if r['success']) / len([r for r in results if r['success']])
    print(f"Average successful collection time: {avg_time:.2f}s")

    return results

if __name__ == "__main__":
    test_collection_performance()