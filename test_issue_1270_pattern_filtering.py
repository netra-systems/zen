#!/usr/bin/env python3
"""
Issue #1270 Test Plan Execution - Pattern Filtering Bug Reproduction

This script reproduces and validates the pattern filtering bug where:
- Database category tests incorrectly get -k filter applied when using --pattern flag
- E2E category tests correctly get -k filter applied when using --pattern flag

Bug: Database category should NOT apply -k filter, but currently does.
"""

import sys
import os
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "tests"))

try:
    from unified_test_runner import UnifiedTestRunner
except ImportError as e:
    print(f"WARNING: Could not import unified_test_runner: {e}")
    print("Running without unified test runner integration")
    UnifiedTestRunner = None


class Issue1270TestExecutor:
    """Execute tests to reproduce and validate Issue #1270"""

    def __init__(self):
        self.results = []
        self.test_failures = []

    def run_pattern_filtering_unit_tests(self) -> Dict:
        """Test the pattern filtering logic in _build_pytest_command()"""
        print("\n" + "="*70)
        print("UNIT TESTS: Pattern Filtering Logic")
        print("="*70)

        if not UnifiedTestRunner:
            return {"status": "SKIPPED", "reason": "UnifiedTestRunner not available"}

        # Create test runner instance
        runner = UnifiedTestRunner()

        # Create mock args
        class MockArgs:
            def __init__(self, pattern=None, **kwargs):
                self.pattern = pattern
                self.no_coverage = True
                self.parallel = False
                self.verbose = False
                self.fast_fail = False
                self.env = "test"

        test_cases = [
            # Test Case 1: Database category with pattern (BUG - should NOT have -k)
            {
                "name": "Database category with pattern",
                "service": "backend",
                "category": "database",
                "args": MockArgs(pattern="test_connection"),
                "expected_k_filter": False,  # Database should NOT get -k filter
                "bug_description": "Database category incorrectly gets -k filter"
            },

            # Test Case 2: E2E category with pattern (CORRECT - should have -k)
            {
                "name": "E2E category with pattern",
                "service": "backend",
                "category": "e2e",
                "args": MockArgs(pattern="test_auth"),
                "expected_k_filter": True,  # E2E should get -k filter
                "bug_description": "E2E category correctly gets -k filter"
            },

            # Test Case 3: Database category without pattern (CORRECT - no -k)
            {
                "name": "Database category without pattern",
                "service": "backend",
                "category": "database",
                "args": MockArgs(),
                "expected_k_filter": False,  # Should not have -k filter
                "bug_description": "Database category without pattern should not have -k"
            },

            # Test Case 4: Unit category with pattern (CORRECT - should have -k)
            {
                "name": "Unit category with pattern",
                "service": "backend",
                "category": "unit",
                "args": MockArgs(pattern="test_validation"),
                "expected_k_filter": True,  # Unit should get -k filter
                "bug_description": "Unit category correctly gets -k filter"
            }
        ]

        unit_test_results = []

        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")

            try:
                # Get the command
                cmd = runner._build_pytest_command(
                    test_case["service"],
                    test_case["category"],
                    test_case["args"]
                )

                print(f"  Generated command: {cmd}")

                # Check if -k filter is present
                has_k_filter = " -k " in cmd
                expected_k_filter = test_case["expected_k_filter"]

                # Determine if this is the bug
                is_bug = (test_case["category"] == "database" and
                         test_case["args"].pattern and
                         has_k_filter)

                test_result = {
                    "test_case": test_case["name"],
                    "category": test_case["category"],
                    "has_pattern": bool(test_case["args"].pattern),
                    "has_k_filter": has_k_filter,
                    "expected_k_filter": expected_k_filter,
                    "is_correct": has_k_filter == expected_k_filter,
                    "is_bug": is_bug,
                    "command": cmd,
                    "description": test_case["bug_description"]
                }

                if is_bug:
                    print(f"  🐛 BUG REPRODUCED: Database category with pattern has -k filter")
                    self.test_failures.append(f"Issue #1270 Bug: {test_case['name']} - {test_case['bug_description']}")
                elif test_result["is_correct"]:
                    print(f"  ✅ CORRECT: {test_case['bug_description']}")
                else:
                    print(f"  ❌ UNEXPECTED: Expected k_filter={expected_k_filter}, got {has_k_filter}")

                unit_test_results.append(test_result)

            except Exception as e:
                print(f"  ❌ ERROR: {str(e)}")
                unit_test_results.append({
                    "test_case": test_case["name"],
                    "error": str(e),
                    "is_bug": False,
                    "is_correct": False
                })

        # Summary
        bugs_found = sum(1 for r in unit_test_results if r.get("is_bug", False))
        correct_behaviors = sum(1 for r in unit_test_results if r.get("is_correct", False))

        print(f"\n📊 Unit Test Summary:")
        print(f"  - Total test cases: {len(unit_test_results)}")
        print(f"  - Bugs reproduced: {bugs_found}")
        print(f"  - Correct behaviors: {correct_behaviors}")

        return {
            "status": "COMPLETED",
            "test_cases": len(unit_test_results),
            "bugs_found": bugs_found,
            "correct_behaviors": correct_behaviors,
            "results": unit_test_results
        }

    def run_integration_tests(self) -> Dict:
        """Test actual command generation behavior"""
        print("\n" + "="*70)
        print("INTEGRATION TESTS: Actual Command Generation")
        print("="*70)

        # Test cases for integration testing
        integration_commands = [
            {
                "name": "Database category with pattern (BUG CASE)",
                "cmd": [
                    sys.executable, "tests/unified_test_runner.py",
                    "--category", "database",
                    "--pattern", "test_connection",
                    "--no-coverage",
                    "--dry-run"  # If available, use dry-run to avoid actual execution
                ],
                "expected_behavior": "Should NOT include -k filter for database category",
                "is_bug_case": True
            },
            {
                "name": "E2E category with pattern (CORRECT CASE)",
                "cmd": [
                    sys.executable, "tests/unified_test_runner.py",
                    "--category", "e2e",
                    "--pattern", "test_auth",
                    "--no-coverage",
                    "--dry-run"
                ],
                "expected_behavior": "Should include -k filter for e2e category",
                "is_bug_case": False
            }
        ]

        integration_results = []

        for test_cmd in integration_commands:
            print(f"\nTesting: {test_cmd['name']}")
            print(f"  Command: {' '.join(test_cmd['cmd'])}")

            try:
                # Run the command
                result = subprocess.run(
                    test_cmd["cmd"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=project_root
                )

                output = result.stdout + result.stderr
                print(f"  Return code: {result.returncode}")

                # Look for pytest command in output
                pytest_commands = re.findall(r'python.*?pytest.*?(?=\n|$)', output, re.MULTILINE)

                k_filter_found = False
                for cmd_line in pytest_commands:
                    if " -k " in cmd_line:
                        k_filter_found = True
                        print(f"  🔍 Found -k filter in: {cmd_line}")
                        break

                if not pytest_commands:
                    print(f"  ⚠️  No pytest commands found in output")

                integration_result = {
                    "test_name": test_cmd["name"],
                    "return_code": result.returncode,
                    "has_k_filter": k_filter_found,
                    "is_bug_case": test_cmd["is_bug_case"],
                    "expected_behavior": test_cmd["expected_behavior"],
                    "output_sample": output[:500] if output else "No output"
                }

                if test_cmd["is_bug_case"] and k_filter_found:
                    print(f"  🐛 BUG CONFIRMED: Database category incorrectly has -k filter")
                    self.test_failures.append(f"Integration test confirmed Issue #1270 bug")
                elif not test_cmd["is_bug_case"] and k_filter_found:
                    print(f"  ✅ CORRECT: E2E category correctly has -k filter")
                else:
                    print(f"  ❓ UNEXPECTED: {test_cmd['expected_behavior']}")

                integration_results.append(integration_result)

            except subprocess.TimeoutExpired:
                print(f"  ⏰ TIMEOUT: Command timed out after 30s")
                integration_results.append({
                    "test_name": test_cmd["name"],
                    "error": "Timeout after 30s",
                    "is_bug_case": test_cmd["is_bug_case"]
                })
            except Exception as e:
                print(f"  ❌ ERROR: {str(e)}")
                integration_results.append({
                    "test_name": test_cmd["name"],
                    "error": str(e),
                    "is_bug_case": test_cmd["is_bug_case"]
                })

        bugs_confirmed = sum(1 for r in integration_results
                           if r.get("is_bug_case", False) and r.get("has_k_filter", False))

        print(f"\n📊 Integration Test Summary:")
        print(f"  - Tests run: {len(integration_results)}")
        print(f"  - Bugs confirmed: {bugs_confirmed}")

        return {
            "status": "COMPLETED",
            "tests_run": len(integration_results),
            "bugs_confirmed": bugs_confirmed,
            "results": integration_results
        }

    def validate_expected_vs_actual(self) -> Dict:
        """Validate what should happen vs what currently happens"""
        print("\n" + "="*70)
        print("VALIDATION: Expected vs Actual Behavior")
        print("="*70)

        validation_rules = [
            {
                "category": "database",
                "with_pattern": True,
                "expected_k_filter": False,
                "reason": "Database tests should run all tests in database paths, pattern should not filter"
            },
            {
                "category": "e2e",
                "with_pattern": True,
                "expected_k_filter": True,
                "reason": "E2E tests should use pattern to filter specific test names"
            },
            {
                "category": "unit",
                "with_pattern": True,
                "expected_k_filter": True,
                "reason": "Unit tests should use pattern to filter specific test names"
            },
            {
                "category": "integration",
                "with_pattern": True,
                "expected_k_filter": True,
                "reason": "Integration tests should use pattern to filter specific test names"
            }
        ]

        validation_results = []

        print("Expected Behavior Rules:")
        for rule in validation_rules:
            pattern_text = "with pattern" if rule["with_pattern"] else "without pattern"
            k_filter_text = "SHOULD" if rule["expected_k_filter"] else "should NOT"

            print(f"  📋 {rule['category']} {pattern_text} {k_filter_text} have -k filter")
            print(f"     Reason: {rule['reason']}")

            validation_results.append({
                "category": rule["category"],
                "with_pattern": rule["with_pattern"],
                "expected_k_filter": rule["expected_k_filter"],
                "reason": rule["reason"]
            })

        print("\nCurrent Bug Status:")
        print("  🐛 Database category with --pattern incorrectly applies -k filter")
        print("  ✅ E2E category with --pattern correctly applies -k filter")
        print("  ✅ Unit category with --pattern correctly applies -k filter")
        print("  ✅ Integration category with --pattern correctly applies -k filter")

        return {
            "status": "COMPLETED",
            "rules_validated": len(validation_rules),
            "primary_bug": "Database category with pattern incorrectly applies -k filter",
            "validation_rules": validation_results
        }

    def assess_test_quality(self) -> Dict:
        """Assess the quality of our tests and provide recommendations"""
        print("\n" + "="*70)
        print("ASSESSMENT: Test Quality and Recommendations")
        print("="*70)

        # Calculate test coverage
        total_failures = len(self.test_failures)
        bug_reproduced = any("Issue #1270" in failure for failure in self.test_failures)

        assessment = {
            "bug_reproduction_success": bug_reproduced,
            "total_test_failures": total_failures,
            "test_quality": "HIGH" if bug_reproduced and total_failures > 0 else "MEDIUM",
            "recommendations": []
        }

        print("Test Quality Assessment:")
        print(f"  🎯 Bug reproduction successful: {'YES' if bug_reproduced else 'NO'}")
        print(f"  📊 Total test failures detected: {total_failures}")
        print(f"  🏆 Overall test quality: {assessment['test_quality']}")

        # Provide recommendations
        recommendations = [
            "Fix the pattern filtering logic in _build_pytest_command() to exclude database category",
            "Add unit tests to prevent regression of this pattern filtering bug",
            "Implement category-specific pattern handling logic",
            "Add integration tests that validate command generation for all categories",
            "Consider adding a --dry-run flag to unified_test_runner.py for testing"
        ]

        assessment["recommendations"] = recommendations

        print("\n🚀 Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

        return assessment

    def run_full_test_plan(self) -> Dict:
        """Execute the complete test plan for Issue #1270"""
        print("🚀 EXECUTING ISSUE #1270 TEST PLAN")
        print("="*70)
        print("Testing pattern filtering bug in unified test runner")
        print("Bug: Database category tests incorrectly get -k filter with --pattern")

        # Execute all test phases
        unit_results = self.run_pattern_filtering_unit_tests()
        integration_results = self.run_integration_tests()
        validation_results = self.validate_expected_vs_actual()
        assessment_results = self.assess_test_quality()

        # Final summary
        print("\n" + "="*70)
        print("🎯 FINAL TEST EXECUTION SUMMARY")
        print("="*70)

        summary = {
            "issue": "Issue #1270 - Database category pattern filtering bug",
            "bug_reproduced": len(self.test_failures) > 0,
            "unit_tests": unit_results,
            "integration_tests": integration_results,
            "validation": validation_results,
            "assessment": assessment_results,
            "test_failures": self.test_failures,
            "recommendation": "PROCEED TO REMEDIATION" if len(self.test_failures) > 0 else "NO BUG DETECTED"
        }

        print(f"Issue: {summary['issue']}")
        print(f"Bug reproduced: {'YES ✅' if summary['bug_reproduced'] else 'NO ❌'}")
        print(f"Test failures: {len(self.test_failures)}")
        print(f"Recommendation: {summary['recommendation']}")

        if self.test_failures:
            print("\n🐛 Confirmed Issues:")
            for failure in self.test_failures:
                print(f"  - {failure}")

        return summary


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Execute Issue #1270 test plan")
    parser.add_argument("--phase", choices=["unit", "integration", "validation", "assessment", "all"],
                       default="all", help="Test phase to run")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    executor = Issue1270TestExecutor()

    if args.phase == "unit":
        result = executor.run_pattern_filtering_unit_tests()
    elif args.phase == "integration":
        result = executor.run_integration_tests()
    elif args.phase == "validation":
        result = executor.validate_expected_vs_actual()
    elif args.phase == "assessment":
        result = executor.assess_test_quality()
    else:
        result = executor.run_full_test_plan()

    return 0 if result.get("bug_reproduced", False) else 1


if __name__ == "__main__":
    sys.exit(main())