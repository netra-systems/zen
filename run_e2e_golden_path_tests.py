#!/usr/bin/env python3
"""
E2E Golden Path Test Execution Script

This script runs the E2E golden path tests without Docker, focusing on
staging environment validation of the core user journey: login → AI response.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment for staging tests
os.environ['TEST_ENV'] = 'staging'
os.environ['ENVIRONMENT'] = 'staging'
os.environ['BYPASS_STAGING_HEALTH_CHECK'] = 'true'
os.environ['PYTHONPATH'] = str(PROJECT_ROOT)

def run_test_file(test_file, test_name=None):
    """Run a specific test file or test method."""
    print(f"\n=== Running: {test_file} ===")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    cmd = [
        'python3', '-m', 'pytest', 
        test_file,
        '-v', '--tb=short', '-x', '--no-header'
    ]
    
    if test_name:
        cmd.append(f'-k {test_name}')
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ
        )
        
        print(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Test exceeded 300 seconds")
        return False, "", "Timeout expired"
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, "", str(e)

def main():
    """Main test execution function."""
    print("🚀 E2E Golden Path Test Execution")
    print("================================")
    print(f"Environment: {os.environ.get('ENVIRONMENT')}")
    print(f"Test Environment: {os.environ.get('TEST_ENV')}")
    print(f"WebSocket URL: wss://api-staging.netrasystems.ai/ws")
    print(f"Bypass Health Check: {os.environ.get('BYPASS_STAGING_HEALTH_CHECK')}")
    
    # Test files to run
    test_files = [
        {
            'file': 'tests/e2e/agent_golden_path/test_agent_golden_path_smoke_tests.py',
            'description': 'Smoke tests for basic golden path functionality'
        },
        {
            'file': 'tests/e2e/test_golden_path_websocket_chat.py', 
            'description': 'WebSocket chat functionality tests'
        },
        {
            'file': 'tests/e2e/agent_golden_path/test_agent_golden_path_comprehensive.py',
            'description': 'Comprehensive golden path user journey tests'
        }
    ]
    
    results = []
    total_start_time = time.time()
    
    for test_info in test_files:
        test_file = test_info['file']
        description = test_info['description']
        
        print(f"\n📋 {description}")
        print(f"📁 File: {test_file}")
        
        start_time = time.time()
        success, stdout, stderr = run_test_file(test_file)
        duration = time.time() - start_time
        
        results.append({
            'file': test_file,
            'description': description,
            'success': success,
            'duration': duration,
            'stdout': stdout,
            'stderr': stderr
        })
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{status} - Duration: {duration:.2f}s")
    
    # Summary report
    total_duration = time.time() - total_start_time
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\n" + "="*60)
    print("📊 E2E Golden Path Test Results Summary")
    print("="*60)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Environment: staging (no Docker)")
    
    print(f"\n📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{i}. {status} {result['file']} ({result['duration']:.2f}s)")
        if not result['success'] and result['stderr']:
            print(f"   Error: {result['stderr'][:200]}...")
    
    # Write detailed results to file
    results_file = PROJECT_ROOT / 'e2e_golden_path_test_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            'summary': {
                'total': total,
                'passed': passed,
                'failed': total - passed,
                'duration': total_duration,
                'environment': 'staging',
                'docker_used': False
            },
            'results': results
        }, f, indent=2)
    
    print(f"\n📝 Detailed results saved to: {results_file}")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)