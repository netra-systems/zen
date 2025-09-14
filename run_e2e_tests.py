#!/usr/bin/env python3
"""
E2E Test Runner for Issue #872 - Agent Testing
Runs newly created E2E tests and captures detailed results
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Set staging environment
os.environ['ENVIRONMENT'] = 'staging'
os.environ['TESTING_ENVIRONMENT'] = 'staging'

class E2ETestRunner:
    def __init__(self):
        self.results = {
            'start_time': datetime.now().isoformat(),
            'environment': 'staging',
            'tests': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0
            }
        }
        
        # Define test files to run
        self.test_files = [
            {
                'name': 'Agent Tool Integration',
                'file': 'tests/e2e/tools/test_agent_tool_integration_comprehensive.py',
                'class': 'TestAgentToolIntegrationComprehensive',
                'method': 'test_all_tool_types_execution'
            },
            {
                'name': 'Agent Resilience Recovery',
                'file': 'tests/e2e/resilience/test_agent_failure_recovery_comprehensive.py',
                'class': 'TestAgentFailureRecoveryComprehensive',
                'method': 'test_agent_crash_recovery'
            },
            {
                'name': 'Agent Concurrent Load',
                'file': 'tests/e2e/performance/test_agent_concurrent_execution_load.py',
                'class': 'TestAgentConcurrentExecutionLoad',
                'method': 'test_memory_usage_under_concurrent_load'  # Smaller test
            }
        ]
    
    def run_single_test(self, test_info: Dict[str, str]) -> Dict[str, Any]:
        """Run a single test and capture results"""
        test_path = f"{test_info['file']}::{test_info['class']}::{test_info['method']}"
        
        print(f"\n{'='*60}")
        print(f"Running: {test_info['name']}")
        print(f"Path: {test_path}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Run pytest with detailed output
            result = subprocess.run([
                sys.executable, '-m', 'pytest',
                test_path,
                '-v',
                '--tb=short',
                '--no-header',
                '--disable-warnings',
                '-x',  # Stop on first failure
                '--capture=no'  # Show output immediately
            ], 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            test_result = {
                'name': test_info['name'],
                'file': test_info['file'],
                'method': test_info['method'],
                'execution_time': execution_time,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'status': 'PASSED' if result.returncode == 0 else 'FAILED'
            }
            
            # Print results
            print(f"\nResult: {test_result['status']}")
            print(f"Execution Time: {execution_time:.2f}s")
            
            if result.stdout:
                print(f"\nSTDOUT:\n{result.stdout}")
            
            if result.stderr:
                print(f"\nSTDERR:\n{result.stderr}")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return {
                'name': test_info['name'],
                'file': test_info['file'],
                'method': test_info['method'],
                'execution_time': execution_time,
                'return_code': -1,
                'stdout': '',
                'stderr': 'Test timed out after 5 minutes',
                'status': 'TIMEOUT'
            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'name': test_info['name'],
                'file': test_info['file'],
                'method': test_info['method'],
                'execution_time': execution_time,
                'return_code': -2,
                'stdout': '',
                'stderr': str(e),
                'status': 'ERROR'
            }
    
    def run_all_tests(self):
        """Run all E2E tests and capture results"""
        print("Starting E2E Test Execution for Issue #872")
        print(f"Environment: {os.environ.get('ENVIRONMENT', 'not_set')}")
        print(f"Total tests to run: {len(self.test_files)}")
        
        for test_info in self.test_files:
            test_result = self.run_single_test(test_info)
            self.results['tests'].append(test_result)
            
            # Update summary
            self.results['summary']['total'] += 1
            if test_result['status'] == 'PASSED':
                self.results['summary']['passed'] += 1
            elif test_result['status'] == 'FAILED':
                self.results['summary']['failed'] += 1
            else:
                self.results['summary']['errors'] += 1
        
        self.results['end_time'] = datetime.now().isoformat()
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
    
    def print_summary(self):
        """Print test execution summary"""
        print("\n" + "="*80)
        print("E2E TEST EXECUTION SUMMARY - Issue #872")
        print("="*80)
        
        summary = self.results['summary']
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        
        if summary['total'] > 0:
            success_rate = (summary['passed'] / summary['total']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print(f"\nStart Time: {self.results['start_time']}")
        print(f"End Time: {self.results['end_time']}")
        
        # Print individual test results
        print(f"\nINDIVIDUAL TEST RESULTS:")
        print("-" * 80)
        
        for test in self.results['tests']:
            status_icon = "✅" if test['status'] == 'PASSED' else "❌"
            print(f"{status_icon} {test['name']}: {test['status']} ({test['execution_time']:.2f}s)")
            
            if test['status'] != 'PASSED':
                print(f"   Error: {test['stderr'][:100]}...")
        
        print("="*80)
    
    def save_results(self):
        """Save results to JSON file"""
        filename = f"e2e_test_results_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed results saved to: {filename}")

if __name__ == "__main__":
    runner = E2ETestRunner()
    runner.run_all_tests()