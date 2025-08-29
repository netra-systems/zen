#!/usr/bin/env python3
"""
Process A: Continuous E2E Agent Test Runner with Fail-Fast
Continuously runs e2e agent real LLM tests with fail-fast settings.
Tracks failures and spawns Process B agents for analysis and recommendations.
"""

import asyncio
import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
MAX_CONCURRENT_ANALYSIS_AGENTS = 3
TEST_COMMAND_BASE = [
    "python", "unified_test_runner.py",
    "--category", "agent",
    "--real-llm",
    "--fast-fail",
    "--env", "test"
]

FAILURE_REPORT_PATH = Path("test_failure_report.md")
FAILED_TESTS_CACHE = Path(".failed_tests_cache.json")


class TestFailureTracker:
    """Tracks failed tests across runs."""
    
    def __init__(self):
        self.failed_tests: Set[str] = set()
        self.load_cache()
        
    def load_cache(self):
        """Load previously failed tests from cache."""
        if FAILED_TESTS_CACHE.exists():
            try:
                with open(FAILED_TESTS_CACHE, 'r') as f:
                    data = json.load(f)
                    self.failed_tests = set(data.get('failed_tests', []))
                    print(f"Loaded {len(self.failed_tests)} known failed tests from cache")
            except Exception as e:
                print(f"Warning: Could not load failed tests cache: {e}")
                
    def save_cache(self):
        """Save failed tests to cache."""
        try:
            with open(FAILED_TESTS_CACHE, 'w') as f:
                json.dump({
                    'failed_tests': list(self.failed_tests),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save failed tests cache: {e}")
            
    def add_failure(self, test_name: str):
        """Add a test to the failure list."""
        self.failed_tests.add(test_name)
        self.save_cache()
        
    def remove_analyzed(self, test_name: str):
        """Remove an analyzed test from the failure list."""
        self.failed_tests.discard(test_name)
        self.save_cache()
        
    def get_skip_args(self) -> List[str]:
        """Get command line arguments to skip known failed tests."""
        if not self.failed_tests:
            return []
        # Create skip pattern for pytest
        skip_pattern = " or ".join(f"not {test}" for test in self.failed_tests)
        return ["-k", skip_pattern]


class ProcessBManager:
    """Manages Process B agents for analyzing failures and providing recommendations."""
    
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_ANALYSIS_AGENTS):
        self.max_concurrent = max_concurrent
        self.active_agents: Dict[str, subprocess.Popen] = {}
        self.completed_analyses: List[str] = []
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.lock = threading.Lock()
        
    def spawn_analysis_agent(self, test_name: str, failure_info: Dict) -> Optional[subprocess.Popen]:
        """Spawn a Process B agent to analyze a specific test failure and provide recommendations."""
        with self.lock:
            if len(self.active_agents) >= self.max_concurrent:
                print(f"At concurrency limit ({self.max_concurrent}), waiting to spawn agent for {test_name}")
                return None
                
        # Create analysis script for this specific failure
        analysis_script = self._create_analysis_script(test_name, failure_info)
        
        # Spawn the analysis agent
        try:
            process = subprocess.Popen(
                ["python", analysis_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            with self.lock:
                self.active_agents[test_name] = process
                
            print(f"Spawned Process B agent for {test_name} (PID: {process.pid})")
            return process
            
        except Exception as e:
            print(f"Error spawning analysis agent for {test_name}: {e}")
            return None
            
    def _create_analysis_script(self, test_name: str, failure_info: Dict) -> str:
        """Create a Python script for the analysis agent."""
        script_path = Path(f"temp_analysis_agent_{test_name.replace('::', '_')}.py")
        
        script_content = f'''#!/usr/bin/env python3
"""Auto-generated analysis agent for test: {test_name}"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_failure_analyzer import TestFailureAnalyzer

def main():
    analyzer = TestFailureAnalyzer(
        test_name="{test_name}",
        failure_info={json.dumps(failure_info, indent=2)},
        report_path="{FAILURE_REPORT_PATH}"
    )
    
    success = analyzer.analyze()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)
            
        return str(script_path)
        
    def wait_for_available_slot(self, timeout: int = 60) -> bool:
        """Wait for an available slot to spawn a new agent."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self.lock:
                # Check for completed agents
                completed = []
                for test_name, process in self.active_agents.items():
                    if process.poll() is not None:
                        completed.append(test_name)
                        
                # Remove completed agents
                for test_name in completed:
                    del self.active_agents[test_name]
                    self.completed_analyses.append(test_name)
                    print(f"Process B agent for {test_name} completed")
                    
                if len(self.active_agents) < self.max_concurrent:
                    return True
                    
            time.sleep(1)
            
        return False
        
    def shutdown(self):
        """Shutdown all active agents."""
        with self.lock:
            for test_name, process in self.active_agents.items():
                print(f"Terminating Process B agent for {test_name}")
                process.terminate()
                
        self.executor.shutdown(wait=True)


class ContinuousTestRunner:
    """Main controller for Process A."""
    
    def __init__(self):
        self.tracker = TestFailureTracker()
        self.process_b_manager = ProcessBManager()
        self.all_failures: Dict[str, Dict] = {}
        self.iteration_count = 0
        
    def run_tests(self, skip_known_failures: bool = True) -> Tuple[bool, List[Dict]]:
        """Run the e2e agent tests and return results."""
        cmd = TEST_COMMAND_BASE.copy()
        
        if skip_known_failures and self.tracker.failed_tests:
            skip_args = self.tracker.get_skip_args()
            if skip_args:
                cmd.extend(skip_args)
                print(f"Skipping {len(self.tracker.failed_tests)} known failed tests")
                
        print(f"\nIteration {self.iteration_count + 1}: Running tests...")
        print(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            # Parse test results
            failures = self._parse_test_output(result.stdout, result.stderr)
            
            if result.returncode == 0:
                print(f"All tests passed! (Iteration {self.iteration_count + 1})")
                return True, []
            else:
                print(f"Found {len(failures)} test failures")
                return False, failures
                
        except subprocess.TimeoutExpired:
            print("Test run timed out after 10 minutes")
            return False, []
        except Exception as e:
            print(f"Error running tests: {e}")
            return False, []
            
    def _parse_test_output(self, stdout: str, stderr: str) -> List[Dict]:
        """Parse test output to extract failure information."""
        failures = []
        
        # Simple parsing - look for FAILED markers
        lines = (stdout + stderr).split('\n')
        
        for i, line in enumerate(lines):
            if 'FAILED' in line:
                # Extract test name and error
                test_name = self._extract_test_name(line)
                if test_name:
                    # Look for error details in surrounding lines
                    error_details = self._extract_error_details(lines, i)
                    
                    failures.append({
                        'test_name': test_name,
                        'error_line': line,
                        'error_details': error_details,
                        'timestamp': datetime.now().isoformat()
                    })
                    
        return failures
        
    def _extract_test_name(self, line: str) -> Optional[str]:
        """Extract test name from a failure line."""
        # Pattern: test_file.py::TestClass::test_method
        import re
        match = re.search(r'(test_\w+\.py(::\w+)*)', line)
        if match:
            return match.group(1)
        return None
        
    def _extract_error_details(self, lines: List[str], failure_index: int) -> str:
        """Extract error details around the failure line."""
        start = max(0, failure_index - 10)
        end = min(len(lines), failure_index + 20)
        return '\n'.join(lines[start:end])
        
    def process_failures(self, failures: List[Dict]):
        """Process test failures by spawning analysis agents."""
        for failure in failures:
            test_name = failure['test_name']
            
            # Track this failure
            self.tracker.add_failure(test_name)
            self.all_failures[test_name] = failure
            
            # Try to spawn an analysis agent
            if self.process_b_manager.wait_for_available_slot(timeout=30):
                self.process_b_manager.spawn_analysis_agent(test_name, failure)
            else:
                print(f"Could not spawn analysis agent for {test_name} - queue full")
                
    def update_report(self):
        """Update the unified failure report."""
        report_content = f"""# E2E Agent Test Failure Report
Generated: {datetime.now().isoformat()}
Iteration: {self.iteration_count}

## Summary
- Total unique failures found: {len(self.all_failures)}
- Known failed tests: {len(self.tracker.failed_tests)}
- Analysis agents spawned: {len(self.process_b_manager.active_agents) + len(self.process_b_manager.completed_analyses)}
- Analyses completed: {len(self.process_b_manager.completed_analyses)}

## Current Status

### Active Analysis Agents ({len(self.process_b_manager.active_agents)})
"""
        
        for test_name in self.process_b_manager.active_agents:
            report_content += f"- {test_name} (in progress)\n"
            
        report_content += f"\n### Completed Analyses ({len(self.process_b_manager.completed_analyses)})\n"
        for test_name in self.process_b_manager.completed_analyses:
            report_content += f"- {test_name} ✓\n"
            
        report_content += f"\n### Known Failed Tests ({len(self.tracker.failed_tests)})\n"
        for test_name in sorted(self.tracker.failed_tests):
            failure = self.all_failures.get(test_name, {})
            report_content += f"\n#### {test_name}\n"
            report_content += f"- First seen: {failure.get('timestamp', 'Unknown')}\n"
            if 'error_details' in failure:
                report_content += f"```\n{failure['error_details'][:500]}\n```\n"
                
        # Write report
        with open(FAILURE_REPORT_PATH, 'w') as f:
            f.write(report_content)
            
        print(f"Updated failure report: {FAILURE_REPORT_PATH}")
        
    async def run_continuous(self):
        """Main continuous test loop."""
        print("Starting continuous E2E agent test runner...")
        print(f"Max concurrent analysis agents: {MAX_CONCURRENT_ANALYSIS_AGENTS}")
        print(f"Failure report: {FAILURE_REPORT_PATH}")
        
        while True:
            self.iteration_count += 1
            
            # Run tests
            all_passed, failures = self.run_tests(skip_known_failures=True)
            
            if all_passed and not self.tracker.failed_tests:
                print("\n🎉 SUCCESS! All tests are passing!")
                self.update_report()
                break
                
            # Process new failures
            if failures:
                print(f"\nProcessing {len(failures)} new failures...")
                self.process_failures(failures)
                
            # Update report
            self.update_report()
            
            # Wait a bit before next iteration
            print("\nWaiting 30 seconds before next test run...")
            await asyncio.sleep(30)
            
        # Cleanup
        print("\nShutting down...")
        self.process_b_manager.shutdown()


def main():
    """Main entry point."""
    runner = ContinuousTestRunner()
    
    try:
        asyncio.run(runner.run_continuous())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        runner.process_b_manager.shutdown()
    except Exception as e:
        print(f"Error: {e}")
        runner.process_b_manager.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()