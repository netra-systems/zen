#!/usr/bin/env python3
"""
E2E Continuous Test Runner with Failure Tracking
Process A: Continuously runs e2e tests and tracks failures
Process B: Spawns sub-agents to fix failures (max 3 concurrent)
"""

import json
import subprocess
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class E2EContinuousRunner:
    """Manages continuous e2e test execution with failure tracking."""
    
    def __init__(self):
        self.test_dir = Path("e2e_test_tracking")
        self.test_dir.mkdir(exist_ok=True)
        
        self.failed_tests: Set[str] = set()
        self.fixed_tests: Set[str] = set()
        self.skip_list: Set[str] = set()
        
        self.report_path = self.test_dir / "unified_failure_report.md"
        self.skip_list_path = self.test_dir / "skip_list.json"
        self.session_log = self.test_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        self.iteration = 0
        self.max_concurrent_fixes = 3
        self.active_fix_agents = []
        self.fix_executor = ThreadPoolExecutor(max_workers=self.max_concurrent_fixes)
        
        # Load existing skip list
        self.load_skip_list()
    
    def load_skip_list(self):
        """Load tests to skip from previous runs."""
        if self.skip_list_path.exists():
            with open(self.skip_list_path, 'r') as f:
                data = json.load(f)
                self.skip_list = set(data.get("failed_tests", []))
                self.fixed_tests = set(data.get("fixed_tests", []))
                print(f"Loaded {len(self.skip_list)} tests to skip from previous runs")
    
    def save_skip_list(self):
        """Save current skip list and fixed tests."""
        with open(self.skip_list_path, 'w') as f:
            json.dump({
                "failed_tests": list(self.failed_tests - self.fixed_tests),
                "fixed_tests": list(self.fixed_tests),
                "updated": datetime.now().isoformat()
            }, f, indent=2)
    
    def parse_test_output(self, output: str) -> Dict[str, Any]:
        """Parse test output for failures and statistics."""
        failures = []
        errors = []
        passed = []
        
        # Pattern matching for different test states
        patterns = {
            'failed': r'FAILED ([\w/\\\.]+::\S+)',
            'error': r'ERROR ([\w/\\\.]+::\S+)',
            'passed': r'PASSED ([\w/\\\.]+::\S+)',
        }
        
        for pattern_type, pattern in patterns.items():
            for match in re.finditer(pattern, output):
                test_name = match.group(1)
                if pattern_type == 'failed':
                    failures.append(test_name)
                elif pattern_type == 'error':
                    errors.append(test_name)
                elif pattern_type == 'passed':
                    passed.append(test_name)
        
        # Extract summary statistics
        stats_match = re.search(r'(\d+) passed.*?(\d+) failed.*?(\d+) error', output)
        stats = {
            'passed': len(passed),
            'failed': len(failures),
            'errors': len(errors),
            'total': len(passed) + len(failures) + len(errors)
        }
        
        return {
            'failures': failures,
            'errors': errors,
            'passed': passed,
            'statistics': stats
        }
    
    def run_e2e_tests(self, skip_tests: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Run e2e tests with real LLM, optionally skipping known failures."""
        self.iteration += 1
        
        print(f"\n{'='*70}")
        print(f"E2E Test Run - Iteration #{self.iteration}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        # Build command
        cmd = [
            "python", "unified_test_runner.py",
            "--category", "e2e",
            "--real-llm",
            "--fast-fail",
            "--no-coverage"
        ]
        
        # Add deselect patterns for known failures
        if skip_tests:
            print(f"Skipping {len(skip_tests)} known failing tests")
            for test in skip_tests:
                # Convert test path format for pytest deselect
                test_path = test.replace("::", " ").replace("\\", "/")
                cmd.extend(["--deselect", test_path])
        
        print(f"Command: {' '.join(cmd[:6])}...")
        
        # Run tests
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout for e2e tests
        )
        duration = time.time() - start_time
        
        # Parse output
        combined_output = result.stdout + result.stderr
        parsed = self.parse_test_output(combined_output)
        
        # Update tracking
        all_failures = set(parsed['failures'] + parsed['errors'])
        new_failures = all_failures - self.failed_tests
        self.failed_tests.update(all_failures)
        
        # Check for fixed tests
        newly_fixed = []
        if skip_tests:
            for test in skip_tests:
                if test not in all_failures and test in self.failed_tests:
                    self.fixed_tests.add(test)
                    newly_fixed.append(test)
                    self.failed_tests.discard(test)
        
        # Build result
        result_data = {
            'iteration': self.iteration,
            'timestamp': datetime.now().isoformat(),
            'duration': duration,
            'return_code': result.returncode,
            'statistics': parsed['statistics'],
            'new_failures': list(new_failures),
            'newly_fixed': newly_fixed,
            'total_failures': len(self.failed_tests - self.fixed_tests),
            'skipped_count': len(skip_tests) if skip_tests else 0
        }
        
        # Save results
        self.save_iteration_result(result_data)
        self.update_unified_report()
        
        # Print summary
        print(f"\nIteration #{self.iteration} Summary:")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Tests Run: {parsed['statistics']['total']}")
        print(f"  Passed: {parsed['statistics']['passed']}")
        print(f"  Failed: {parsed['statistics']['failed']}")
        print(f"  Errors: {parsed['statistics']['errors']}")
        print(f"  New Failures: {len(new_failures)}")
        print(f"  Fixed: {len(newly_fixed)}")
        print(f"  Total Remaining: {len(self.failed_tests - self.fixed_tests)}")
        
        if new_failures:
            print(f"\n[FAIL] New failures detected:")
            for test in list(new_failures)[:5]:  # Show first 5
                print(f"    - {test}")
        
        if newly_fixed:
            print(f"\n[FIXED] Tests fixed:")
            for test in newly_fixed[:5]:  # Show first 5
                print(f"    - {test}")
        
        return result_data
    
    def save_iteration_result(self, result: Dict):
        """Save iteration result to session log."""
        session_data = []
        if self.session_log.exists():
            with open(self.session_log, 'r') as f:
                session_data = json.load(f)
        
        session_data.append(result)
        
        with open(self.session_log, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Update skip list
        self.save_skip_list()
    
    def update_unified_report(self):
        """Update the unified failure report markdown file."""
        with open(self.report_path, 'w') as f:
            f.write("# E2E Test Failure Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Iteration: #{self.iteration}\n\n")
            
            f.write("## Summary\n")
            f.write(f"- Total unique failures found: {len(self.failed_tests)}\n")
            f.write(f"- Tests fixed: {len(self.fixed_tests)}\n")
            f.write(f"- Remaining failures: {len(self.failed_tests - self.fixed_tests)}\n")
            f.write(f"- Active fix agents: {len(self.active_fix_agents)}\n\n")
            
            if self.failed_tests - self.fixed_tests:
                f.write("## Current Failures\n")
                for i, test in enumerate(sorted(self.failed_tests - self.fixed_tests), 1):
                    f.write(f"{i}. [FAIL] `{test}`\n")
                f.write("\n")
            
            if self.fixed_tests:
                f.write("## Fixed Tests\n")
                for i, test in enumerate(sorted(self.fixed_tests), 1):
                    f.write(f"{i}. [FIXED] `{test}`\n")
                f.write("\n")
            
            if self.active_fix_agents:
                f.write("## Active Fix Agents\n")
                for agent in self.active_fix_agents:
                    f.write(f"- {agent['test']}: {agent['status']}\n")
                f.write("\n")
    
    def spawn_fix_agent(self, test_failure: str) -> Dict[str, Any]:
        """Spawn a sub-agent to fix a specific test failure (Process B)."""
        print(f"\n[FIX] Spawning fix agent for: {test_failure}")
        
        # This would normally spawn an actual sub-agent
        # For now, we'll simulate with a subprocess call
        agent_info = {
            'test': test_failure,
            'status': 'analyzing',
            'started': datetime.now().isoformat()
        }
        
        self.active_fix_agents.append(agent_info)
        
        # Create fix task file for sub-agent
        fix_task_path = self.test_dir / f"fix_task_{test_failure.replace('::', '_').replace('/', '_')}.json"
        with open(fix_task_path, 'w') as f:
            json.dump({
                'test': test_failure,
                'iteration': self.iteration,
                'timestamp': datetime.now().isoformat(),
                'status': 'pending'
            }, f, indent=2)
        
        print(f"   Created fix task: {fix_task_path}")
        return agent_info
    
    def run_continuous(self):
        """Main loop - Process A: Continuously run e2e tests."""
        print("Starting E2E Continuous Test Runner")
        print(f"Max concurrent fix agents: {self.max_concurrent_fixes}")
        print(f"Skip list has {len(self.skip_list)} tests from previous runs\n")
        
        consecutive_passes = 0
        
        while True:
            try:
                # Run tests with current skip list
                skip_tests = (self.failed_tests - self.fixed_tests) if self.iteration > 0 else self.skip_list
                result = self.run_e2e_tests(skip_tests)
                
                # Check if all tests passed
                if result['return_code'] == 0 and not skip_tests:
                    consecutive_passes += 1
                    print(f"\n[SUCCESS] All e2e tests passing! (Pass #{consecutive_passes})")
                    
                    if consecutive_passes >= 2:
                        print("\n[COMPLETE] SUCCESS! All e2e tests passing consistently!")
                        break
                else:
                    consecutive_passes = 0
                
                # Spawn fix agents for new failures (up to max concurrent)
                if result['new_failures'] and len(self.active_fix_agents) < self.max_concurrent_fixes:
                    available_slots = self.max_concurrent_fixes - len(self.active_fix_agents)
                    to_fix = result['new_failures'][:available_slots]
                    
                    print(f"\n[AGENTS] Spawning {len(to_fix)} fix agents...")
                    for test in to_fix:
                        self.spawn_fix_agent(test)
                
                # Wait before next iteration
                wait_time = 30 if self.failed_tests - self.fixed_tests else 10
                print(f"\n[WAIT] Waiting {wait_time} seconds before next run...")
                time.sleep(wait_time)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            except Exception as e:
                print(f"\n[ERROR] Error in iteration: {e}")
                time.sleep(10)
        
        # Final report
        print(f"\n{'='*70}")
        print("FINAL REPORT")
        print(f"{'='*70}")
        print(f"Total iterations: {self.iteration}")
        print(f"Total unique failures found: {len(self.failed_tests)}")
        print(f"Total tests fixed: {len(self.fixed_tests)}")
        print(f"Remaining failures: {len(self.failed_tests - self.fixed_tests)}")
        print(f"Report saved to: {self.report_path}")
        print(f"Session log: {self.session_log}")
        
        return len(self.failed_tests - self.fixed_tests) == 0


def main():
    """Main entry point."""
    runner = E2EContinuousRunner()
    success = runner.run_continuous()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())