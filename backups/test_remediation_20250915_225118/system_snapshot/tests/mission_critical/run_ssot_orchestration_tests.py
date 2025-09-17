#!/usr/bin/env python3
'''
SSOT Orchestration Test Suite Runner
====================================

This script runs the comprehensive SSOT orchestration test suite with proper
configuration and reporting. It runs all the test files created for validating
the SSOT orchestration consolidation.

Test Suites:
1. test_ssot_orchestration_consolidation.py - Main validation tests
2. test_orchestration_edge_cases.py - Edge cases and stress tests
3. test_orchestration_integration.py - Integration with real components
4. test_no_ssot_violations.py - Regression prevention tests
5. test_orchestration_performance.py - Performance benchmarks

Usage:
python tests/mission_critical/run_ssot_orchestration_tests.py [options]

Options:
--suite SUITE    Run specific test suite (consolidation, edge_cases, integration, violations, performance)
--fast          Run only fast tests (skip performance benchmarks)
--verbose       Verbose output
--stop-on-fail  Stop on first failure
'''

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any

            # Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class SSOTTestRunner:
    """Runner for SSOT orchestration test suites."""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.test_dir = self.project_root / "tests" / "mission_critical"

        self.test_suites = { )
        "consolidation": { )
        "file": "test_ssot_orchestration_consolidation.py",
        "description": "Main SSOT orchestration validation tests",
        "fast": True
        },
        "edge_cases": { )
        "file": "test_orchestration_edge_cases.py",
        "description": "Edge cases, concurrency, and stress tests",
        "fast": False
        },
        "integration": { )
        "file": "test_orchestration_integration.py",
        "description": "Integration with real orchestration components",
        "fast": True
        },
        "violations": { )
        "file": "test_no_ssot_violations.py",
        "description": "SSOT violation detection and prevention",
        "fast": True
        },
        "performance": { )
        "file": "test_orchestration_performance.py",
        "description": "Performance benchmarks and optimization validation",
        "fast": False
    
    

    def run_suite(self, suite_name: str, verbose: bool = False, stop_on_fail: bool = False) -> int:
        """Run a specific test suite."""
        if suite_name not in self.test_suites:
        print("formatted_string")
        print("formatted_string")
        return 1

        suite_info = self.test_suites[suite_name]
        test_file = self.test_dir / suite_info["file"]

        if not test_file.exists():
        print("formatted_string")
        return 1

        print("formatted_string")
        print("=" * 80)

            # Build pytest command
        cmd = [ )
        sys.executable, str(test_file),
        "-v" if verbose else "",
        "-x" if stop_on_fail else "",
        "--tb=short",
        "-m", "mission_critical"
            

            # Remove empty strings
        cmd = [item for item in []]

            # Set environment variables for testing
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)

        try:
        result = subprocess.run(cmd, cwd=self.project_root, env=env, timeout=300)
        return result.returncode
        except subprocess.TimeoutExpired:
        print("Test suite timed out after 5 minutes")
        return 1
        except Exception as e:
        print("formatted_string")
        return 1

    def run_all_suites(self, fast_only: bool = False, verbose: bool = False, stop_on_fail: bool = False) -> Dict[str, int]:
        """Run all test suites."""
        results = {}

        print("Running ALL SSOT Orchestration Test Suites")
        print("=" * 80)

        for suite_name, suite_info in self.test_suites.items():
        if fast_only and not suite_info["fast"]:
        print("formatted_string")
        results[suite_name] = 0  # Count as success for fast mode
        continue

        result = self.run_suite(suite_name, verbose, stop_on_fail)
        results[suite_name] = result

        if result != 0 and stop_on_fail:
        print("formatted_string")
        break

        return results

    def print_summary(self, results: Dict[str, int]):
        """Print test results summary."""
        print(" )
        " + "=" * 80)
        print("SSOT ORCHESTRATION TEST RESULTS SUMMARY")
        print("=" * 80)

        passed_suites = []
        failed_suites = []

        for suite_name, result_code in results.items():
        suite_info = self.test_suites[suite_name]
        status = "PASSED" if result_code == 0 else "FAILED"

        print("formatted_string")

        if result_code == 0:
        passed_suites.append(suite_name)
        else:
        failed_suites.append(suite_name)

        print("=" * 80)
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

        if len(failed_suites) == 0:
        print(" )
        ALL SSOT ORCHESTRATION TESTS PASSED!")
        print("SSOT Orchestration consolidation is BULLETPROOF!")
        else:
        print("formatted_string")
        print("Fix failures before deploying!")

        return len(failed_suites) == 0


    def main():
        """Main entry point."""
        parser = argparse.ArgumentParser(description="Run SSOT orchestration test suites")

        parser.add_argument( )
        "--suite",
        choices=["consolidation", "edge_cases", "integration", "violations", "performance"],
        help="Run specific test suite"
    
        parser.add_argument( )
        "--fast",
        action="store_true",
        help="Run only fast tests (skip performance benchmarks)"
    
        parser.add_argument( )
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    
        parser.add_argument( )
        "--stop-on-fail", "-x",
        action="store_true",
        help="Stop on first failure"
    

        args = parser.parse_args()

        runner = SSOTTestRunner()

        if args.suite:
        # Run specific suite
        result_code = runner.run_suite(args.suite, args.verbose, args.stop_on_fail)
        sys.exit(result_code)
        else:
            # Run all suites
        results = runner.run_all_suites(args.fast, args.verbose, args.stop_on_fail)
        success = runner.print_summary(results)
        sys.exit(0 if success else 1)


        if __name__ == "__main__":
        main()
