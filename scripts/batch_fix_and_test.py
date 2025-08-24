#!/usr/bin/env python3
"""Batch fix known test issues and run test iterations."""

import subprocess
import sys
import re
from pathlib import Path
import json
import time

class TestFixRunner:
    def __init__(self):
        self.iterations_completed = 0
        self.tests_passed = 0
        self.fixes_applied = 0
        self.results = []
        
    def fix_known_issues(self):
        """Fix all known syntax issues in test files."""
        fixes = [
            # Fix duplicate imports
            {
                'pattern': r'from unittest\.mock import.*MagicMock.*MagicMock',
                'replacement': 'from unittest.mock import AsyncMock, MagicMock, Mock, patch',
                'description': 'duplicate MagicMock import'
            },
            # Fix decorator spacing
            {
                'pattern': r'(@pytest\.mark\.\w+)\s*\n\s*\n\s*(async def)',
                'replacement': r'\1\n    \2',
                'description': 'decorator spacing'
            },
            # Fix another decorator pattern
            {
                'pattern': r'(@pytest\.mark\.\w+)\s*\n\s*\n\s*(def)',
                'replacement': r'\1\n    \2',
                'description': 'decorator spacing for sync functions'
            }
        ]
        
        test_files = list(Path('netra_backend/tests').rglob('*.py'))
        test_files.extend(list(Path('auth_service/tests').rglob('*.py')))
        test_files.extend(list(Path('tests/e2e').rglob('*.py')))
        
        for test_file in test_files:
            try:
                content = test_file.read_text()
                original = content
                
                for fix in fixes:
                    if re.search(fix['pattern'], content):
                        content = re.sub(fix['pattern'], fix['replacement'], content)
                        
                if content != original:
                    test_file.write_text(content)
                    self.fixes_applied += 1
                    print(f"Fixed {test_file.name}")
                    
            except Exception as e:
                print(f"Error processing {test_file}: {e}")
    
    def run_test_iteration(self, iteration):
        """Run one test iteration."""
        print(f"\nIteration {iteration}/100")
        
        try:
            # Run with simple smoke tests first
            result = subprocess.run(
                [sys.executable, "unified_test_runner.py", "--category", "smoke", "--no-coverage", "--fast-fail"],
                capture_output=True,
                text=True,
                timeout=20,
                cwd=Path(__file__).parent.parent
            )
            
            success = result.returncode == 0
            
            self.results.append({
                'iteration': iteration,
                'success': success,
                'timestamp': time.time()
            })
            
            if success:
                self.tests_passed += 1
                print(f"[PASS] Iteration {iteration}")
            else:
                print(f"[FAIL] Iteration {iteration}")
                
            return success
            
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] Iteration {iteration}")
            return False
        except Exception as e:
            print(f"[ERROR] Iteration {iteration}: {e}")
            return False
    
    def run_all_iterations(self):
        """Run all 100 iterations."""
        print("Starting 100 test iterations...")
        
        # First apply known fixes
        print("\nApplying known fixes...")
        self.fix_known_issues()
        print(f"Applied {self.fixes_applied} fixes")
        
        # Run iterations
        for i in range(1, 101):
            self.run_test_iteration(i)
            self.iterations_completed = i
            
            # Progress report every 10 iterations
            if i % 10 == 0:
                self.print_progress()
        
        self.print_final_summary()
    
    def print_progress(self):
        """Print progress summary."""
        print(f"\n=== Progress: {self.iterations_completed}/100 ===")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {self.tests_passed/self.iterations_completed*100:.1f}%")
    
    def print_final_summary(self):
        """Print final summary."""
        print("\n" + "="*50)
        print("FINAL SUMMARY")
        print("="*50)
        print(f"Total Iterations: {self.iterations_completed}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.iterations_completed - self.tests_passed}")
        print(f"Success Rate: {self.tests_passed/self.iterations_completed*100:.1f}%")
        print(f"Fixes Applied: {self.fixes_applied}")
        
        # Save results to file
        results_file = Path('test_results_100_iterations.json')
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'iterations': self.iterations_completed,
                    'passed': self.tests_passed,
                    'failed': self.iterations_completed - self.tests_passed,
                    'fixes_applied': self.fixes_applied,
                    'success_rate': self.tests_passed/self.iterations_completed*100
                },
                'details': self.results
            }, f, indent=2)
        print(f"\nResults saved to: {results_file}")

if __name__ == "__main__":
    runner = TestFixRunner()
    runner.run_all_iterations()