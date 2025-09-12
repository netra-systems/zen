#!/usr/bin/env python3
"""
Iterative test-fix loop script that runs tests and fixes failures in a loop.
"""

import subprocess
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

class TestFixLoop:
    def __init__(self, iterations: int = 100):
        self.iterations = iterations
        self.results_file = project_root / f"test_fix_results_{int(time.time())}.json"
        self.results = []
        self.current_iteration = 0
        
    def run_tests(self) -> Tuple[bool, List[str], str]:
        """Run smoke, unit, and critical tests."""
        cmd = [
            sys.executable,
            str(project_root / "unified_test_runner.py"),
            "--level", "smoke",
            "--level", "unit", 
            "--level", "critical",
            "--no-coverage",
            "--fast-fail",
            "--json-report"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=300  # 5 minute timeout
            )
            
            # Parse output to find failures
            failures = []
            output_lines = result.stdout.split('\n')
            
            for line in output_lines:
                if 'FAILED' in line or 'ERROR' in line:
                    failures.append(line.strip())
            
            success = result.returncode == 0
            return success, failures[:10], result.stdout  # Limit to 10 failures
            
        except subprocess.TimeoutExpired:
            return False, ["Test execution timed out"], "Timeout"
        except Exception as e:
            return False, [f"Test execution error: {str(e)}"], str(e)
    
    def get_first_failing_test(self, failures: List[str]) -> Optional[str]:
        """Extract the first failing test from the failures list."""
        if not failures:
            return None
            
        for failure in failures:
            # Extract test path from failure message
            if '::' in failure:
                parts = failure.split('::')
                if len(parts) >= 2:
                    # Get the file path part
                    test_path = parts[0].strip()
                    if 'tests/' in test_path:
                        return test_path
        
        return failures[0] if failures else None
    
    def save_results(self):
        """Save results to JSON file."""
        with open(self.results_file, 'w') as f:
            json.dump({
                'total_iterations': self.current_iteration,
                'results': self.results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
    
    def run_iteration(self) -> Dict:
        """Run a single iteration of test-fix loop."""
        self.current_iteration += 1
        iteration_result = {
            'iteration': self.current_iteration,
            'timestamp': datetime.now().isoformat(),
            'tests_passed': False,
            'failures_found': [],
            'fix_attempted': False,
            'fix_command': None
        }
        
        print(f"\n{'='*60}")
        print(f"ITERATION {self.current_iteration}/{self.iterations}")
        print(f"{'='*60}")
        
        # Step 1: Run tests
        print("\nStep 1: Running smoke, unit, and critical tests...")
        success, failures, output = self.run_tests()
        
        iteration_result['tests_passed'] = success
        iteration_result['failures_found'] = failures[:5]  # Store first 5 failures
        
        if success:
            print(" PASS:  All tests passed!")
            iteration_result['status'] = 'all_passed'
        else:
            print(f" FAIL:  Found {len(failures)} failing tests")
            
            # Step 2: Fix one failing test
            first_failure = self.get_first_failing_test(failures)
            if first_failure:
                print(f"\nStep 2: Attempting to fix: {first_failure}")
                iteration_result['fix_attempted'] = True
                iteration_result['target_test'] = first_failure
                
                # Create the fix command for the subagent
                fix_cmd = f"Fix the failing test: {first_failure}"
                iteration_result['fix_command'] = fix_cmd
                iteration_result['status'] = 'fix_delegated'
                
                print(f"Delegating fix to subagent: {fix_cmd}")
            else:
                iteration_result['status'] = 'no_specific_test_found'
        
        self.results.append(iteration_result)
        self.save_results()
        
        return iteration_result
    
    def run(self):
        """Run the full loop."""
        print(f"Starting {self.iterations} iteration test-fix loop")
        print(f"Results will be saved to: {self.results_file}")
        
        for i in range(self.iterations):
            result = self.run_iteration()
            
            # If all tests pass, we could stop early
            if result['tests_passed']:
                print(f"\n CELEBRATION:  All tests passing after {self.current_iteration} iterations!")
                if input("Continue anyway? (y/n): ").lower() != 'y':
                    break
            
            # Small delay between iterations
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"COMPLETED {self.current_iteration} ITERATIONS")
        print(f"Results saved to: {self.results_file}")
        
        # Print summary
        passed_iterations = sum(1 for r in self.results if r['tests_passed'])
        print(f"\nSummary:")
        print(f"  Total iterations: {self.current_iteration}")
        print(f"  Iterations with all tests passing: {passed_iterations}")
        print(f"  Iterations with failures: {self.current_iteration - passed_iterations}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run iterative test-fix loop")
    parser.add_argument("--iterations", type=int, default=100, help="Number of iterations")
    args = parser.parse_args()
    
    loop = TestFixLoop(iterations=args.iterations)
    loop.run()