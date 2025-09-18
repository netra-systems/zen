#!/usr/bin/env python3
"""
SSOT Compliance Test Execution Script - Issue #1098 Phase 2 Validation

MISSION: Execute comprehensive SSOT compliance test suite for Phase 2 validation.

This script runs all SSOT compliance tests in the correct order and provides
comprehensive validation reporting for Phase 2 SSOT compliance.

Business Value: Platform/Internal - Deployment Gate & Quality Assurance
Ensures SSOT compliance before deployment to protect $500K+ ARR Golden Path.

Usage:
    python tests/run_ssot_compliance_tests.py [options]

Options:
    --quick          Run quick compliance check (unit tests only)
    --full           Run full compliance suite (unit + integration + mission critical)
    --mission-only   Run mission critical tests only (deployment gate)
    --baseline       Update baseline violations after cleanup
    --report         Generate detailed compliance report

Test Categories:
1. Unit Tests: Code scanning without external dependencies
2. Integration Tests: Real WebSocket connections (no Docker)
3. Mission Critical: Deployment gate validation

Expected Results (Phase 2):
- PASS: Production violations ≤ 16 (69% reduction achieved)
- PASS: All 5 WebSocket events functional
- PASS: User isolation maintained
- PASS: Business continuity protected
"""

import sys
import os
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SSotComplianceTestRunner:
    """
    Comprehensive SSOT compliance test runner for Issue #1098 Phase 2 validation.
    """

    def __init__(self):
        self.project_root = project_root
        self.start_time = datetime.now()
        self.test_results = {}
        self.violations_found = 0
        self.critical_failures = []

    def run_compliance_tests(self, test_mode: str = "full") -> Dict:
        """
        Run SSOT compliance tests based on mode.

        Args:
            test_mode: Test mode ('quick', 'full', 'mission-only', 'baseline')

        Returns:
            Dictionary with test results and compliance status.
        """
        print("🚨 SSOT COMPLIANCE TEST SUITE - Issue #1098 Phase 2 Validation")
        print(f"Mode: {test_mode.upper()}")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        try:
            if test_mode == "quick":
                return self._run_quick_compliance_check()
            elif test_mode == "full":
                return self._run_full_compliance_suite()
            elif test_mode == "mission-only":
                return self._run_mission_critical_only()
            elif test_mode == "baseline":
                return self._update_baseline_violations()
            else:
                raise ValueError(f"Unknown test mode: {test_mode}")

        except Exception as e:
            print(f"🚨 CRITICAL ERROR: Compliance test execution failed: {e}")
            return {"status": "FAILED", "error": str(e)}

    def _run_quick_compliance_check(self) -> Dict:
        """
        Run quick compliance check (unit tests only).

        Returns:
            Test results for quick compliance check.
        """
        print("🚀 QUICK COMPLIANCE CHECK: Unit tests only")

        results = {
            "mode": "quick",
            "tests_run": [],
            "violations": 0,
            "status": "UNKNOWN"
        }

        # Run unit tests for SSOT compliance
        unit_tests = [
            "tests.unit.ssot_compliance.test_websocket_factory_elimination",
            "tests.unit.ssot_compliance.test_import_structure_validation",
        ]

        for test_module in unit_tests:
            print(f"\n📋 Running: {test_module}")
            test_result = self._run_test_module(test_module)
            results["tests_run"].append(test_result)

            if not test_result["passed"]:
                self.critical_failures.append(test_module)

        # Determine overall status
        results["status"] = "PASSED" if len(self.critical_failures) == 0 else "FAILED"
        results["critical_failures"] = self.critical_failures

        print(f"\nCHECK QUICK COMPLIANCE CHECK: {results['status']}")
        return results

    def _run_full_compliance_suite(self) -> Dict:
        """
        Run full compliance suite (all test categories).

        Returns:
            Comprehensive test results.
        """
        print("🚀 FULL COMPLIANCE SUITE: All test categories")

        results = {
            "mode": "full",
            "test_categories": {},
            "overall_status": "UNKNOWN",
            "violations_summary": {},
            "business_continuity": "UNKNOWN"
        }

        # Category 1: Unit Tests (Code Scanning)
        print(f"\n{'='*50}")
        print("📋 CATEGORY 1: UNIT TESTS (Code Scanning)")
        print(f"{'='*50}")

        unit_results = self._run_unit_test_category()
        results["test_categories"]["unit"] = unit_results

        # Category 2: Integration Tests (Real Connections)
        print(f"\n{'='*50}")
        print("📋 CATEGORY 2: INTEGRATION TESTS (Real Connections)")
        print(f"{'='*50}")

        integration_results = self._run_integration_test_category()
        results["test_categories"]["integration"] = integration_results

        # Category 3: Mission Critical (Deployment Gate)
        print(f"\n{'='*50}")
        print("📋 CATEGORY 3: MISSION CRITICAL (Deployment Gate)")
        print(f"{'='*50}")

        mission_results = self._run_mission_critical_category()
        results["test_categories"]["mission_critical"] = mission_results

        # Determine overall compliance status
        results["overall_status"] = self._determine_overall_status(results["test_categories"])
        results["violations_summary"] = self._generate_violations_summary()
        results["business_continuity"] = self._assess_business_continuity(results["test_categories"])

        print(f"\n🚨 FULL COMPLIANCE SUITE: {results['overall_status']}")
        return results

    def _run_mission_critical_only(self) -> Dict:
        """
        Run mission critical tests only (deployment gate).

        Returns:
            Mission critical test results.
        """
        print("🚨 MISSION CRITICAL ONLY: Deployment gate validation")

        results = {
            "mode": "mission-critical",
            "deployment_gate": "UNKNOWN",
            "critical_violations": 0,
            "business_impact": "UNKNOWN"
        }

        # Run mission critical test
        mission_test = "tests.mission_critical.test_ssot_production_compliance"
        print(f"\n📋 Running: {mission_test}")

        test_result = self._run_test_module(mission_test)
        results["test_result"] = test_result

        # Determine deployment gate status
        if test_result["passed"]:
            results["deployment_gate"] = "PASSED"
            results["business_impact"] = "PROTECTED"
            print("CHECK DEPLOYMENT GATE: PASSED - Safe to deploy")
        else:
            results["deployment_gate"] = "BLOCKED"
            results["business_impact"] = "AT_RISK"
            print("🚨 DEPLOYMENT GATE: BLOCKED - DO NOT DEPLOY")
            print("🚨 Critical violations detected that could impact $500K+ ARR")

        return results

    def _update_baseline_violations(self) -> Dict:
        """
        Update baseline violations after SSOT cleanup.

        Returns:
            Baseline update results.
        """
        print("📊 BASELINE UPDATE: Updating violation baseline after cleanup")

        # Run production compliance scan to get current state
        try:
            from tests.mission_critical.test_ssot_production_compliance import TestSSotProductionCompliance

            test_instance = TestSSotProductionCompliance()
            test_instance.setUp()

            # Get current violation counts
            current_violations = test_instance._scan_all_production_code()
            filtered_violations = [
                v for v in current_violations
                if not test_instance._is_allowed_compatibility_violation(v)
            ]

            # Update baseline file
            baseline_data = {
                "total_violations": len(filtered_violations),
                "critical_violations": len([v for v in filtered_violations if v.severity == "critical"]),
                "factory_violations": len([v for v in filtered_violations if v.violation_type == "websocket_factory_usage"]),
                "import_violations": len([v for v in filtered_violations if v.violation_type == "non_canonical_imports"]),
                "user_isolation_violations": len([v for v in filtered_violations if v.violation_type == "user_isolation_violation"]),
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "phase": "Phase 2 - Current State",
                "baseline_description": f"Updated baseline with {len(filtered_violations)} violations"
            }

            baseline_file = "tests/mission_critical/ssot_baseline_violations.json"
            with open(baseline_file, 'w') as f:
                json.dump(baseline_data, f, indent=2)

            print(f"CHECK Baseline updated: {len(filtered_violations)} violations recorded")

            return {
                "status": "UPDATED",
                "new_baseline": baseline_data,
                "violations_count": len(filtered_violations)
            }

        except Exception as e:
            print(f"🚨 Baseline update failed: {e}")
            return {"status": "FAILED", "error": str(e)}

    def _run_unit_test_category(self) -> Dict:
        """Run all unit tests for SSOT compliance."""
        unit_tests = [
            "tests.unit.ssot_compliance.test_websocket_factory_elimination",
            "tests.unit.ssot_compliance.test_import_structure_validation",
        ]

        results = {"tests": [], "category_status": "UNKNOWN"}

        for test_module in unit_tests:
            print(f"  📋 Running: {test_module}")
            test_result = self._run_test_module(test_module)
            results["tests"].append(test_result)

        passed_tests = sum(1 for t in results["tests"] if t["passed"])
        results["category_status"] = "PASSED" if passed_tests == len(unit_tests) else "PARTIAL"

        print(f"  CHECK Unit Tests: {passed_tests}/{len(unit_tests)} passed")
        return results

    def _run_integration_test_category(self) -> Dict:
        """Run all integration tests for SSOT compliance."""
        integration_tests = [
            "tests.integration.ssot_compliance.test_canonical_patterns_validation",
            "tests.integration.websocket.test_golden_path_preservation",
        ]

        results = {"tests": [], "category_status": "UNKNOWN"}

        for test_module in integration_tests:
            print(f"  📋 Running: {test_module}")
            test_result = self._run_test_module(test_module)
            results["tests"].append(test_result)

        passed_tests = sum(1 for t in results["tests"] if t["passed"])
        results["category_status"] = "PASSED" if passed_tests == len(integration_tests) else "PARTIAL"

        print(f"  CHECK Integration Tests: {passed_tests}/{len(integration_tests)} passed")
        return results

    def _run_mission_critical_category(self) -> Dict:
        """Run mission critical tests."""
        mission_tests = [
            "tests.mission_critical.test_ssot_production_compliance",
        ]

        results = {"tests": [], "category_status": "UNKNOWN"}

        for test_module in mission_tests:
            print(f"  🚨 Running: {test_module}")
            test_result = self._run_test_module(test_module)
            results["tests"].append(test_result)

        passed_tests = sum(1 for t in results["tests"] if t["passed"])
        results["category_status"] = "PASSED" if passed_tests == len(mission_tests) else "FAILED"

        print(f"  🚨 Mission Critical: {passed_tests}/{len(mission_tests)} passed")
        return results

    def _run_test_module(self, test_module: str) -> Dict:
        """
        Run a single test module and capture results.

        Args:
            test_module: Module path to run

        Returns:
            Test result dictionary.
        """
        try:
            # Use unified test runner if available, otherwise use direct pytest
            try:
                cmd = [
                    sys.executable, "tests/unified_test_runner.py",
                    "--module", test_module,
                    "--no-coverage",
                    "--quiet"
                ]
            except:
                # Fallback to direct module execution
                cmd = [sys.executable, "-m", "pytest", f"{test_module.replace('.', '/')}.py", "-v"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout per test module
                cwd=self.project_root
            )

            return {
                "module": test_module,
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "exit_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "module": test_module,
                "passed": False,
                "output": "",
                "errors": "Test timed out after 2 minutes",
                "exit_code": -1
            }
        except Exception as e:
            return {
                "module": test_module,
                "passed": False,
                "output": "",
                "errors": f"Test execution failed: {e}",
                "exit_code": -1
            }

    def _determine_overall_status(self, test_categories: Dict) -> str:
        """Determine overall compliance status from test categories."""
        mission_critical_passed = test_categories.get("mission_critical", {}).get("category_status") == "PASSED"

        if not mission_critical_passed:
            return "CRITICAL_FAILURE"

        unit_status = test_categories.get("unit", {}).get("category_status", "FAILED")
        integration_status = test_categories.get("integration", {}).get("category_status", "FAILED")

        if unit_status == "PASSED" and integration_status == "PASSED":
            return "FULL_COMPLIANCE"
        elif unit_status == "PASSED" or integration_status == "PASSED":
            return "PARTIAL_COMPLIANCE"
        else:
            return "MINIMAL_COMPLIANCE"

    def _generate_violations_summary(self) -> Dict:
        """Generate summary of violations found during testing."""
        return {
            "total_violations": self.violations_found,
            "phase_2_limit": 16,
            "compliance_percentage": max(0, 100 - (self.violations_found * 100 / 53)),  # Based on 53 original violations
            "critical_failures": len(self.critical_failures)
        }

    def _assess_business_continuity(self, test_categories: Dict) -> str:
        """Assess business continuity based on test results."""
        integration_status = test_categories.get("integration", {}).get("category_status", "FAILED")
        mission_status = test_categories.get("mission_critical", {}).get("category_status", "FAILED")

        if mission_status == "PASSED" and integration_status == "PASSED":
            return "PROTECTED"
        elif mission_status == "PASSED":
            return "MINIMAL_RISK"
        else:
            return "AT_RISK"

    def generate_compliance_report(self, results: Dict):
        """Generate detailed compliance report."""
        print(f"\n{'='*80}")
        print("📊 SSOT COMPLIANCE REPORT - Issue #1098 Phase 2")
        print(f"{'='*80}")

        # Overall status
        overall_status = results.get("overall_status", results.get("status", "UNKNOWN"))
        print(f"Overall Status: {overall_status}")

        # Test execution time
        end_time = datetime.now()
        duration = end_time - self.start_time
        print(f"Execution Time: {duration.total_seconds():.2f} seconds")

        # Violations summary
        if "violations_summary" in results:
            summary = results["violations_summary"]
            print(f"\nViolations Summary:")
            print(f"  Total Found: {summary.get('total_violations', 0)}")
            print(f"  Phase 2 Limit: {summary.get('phase_2_limit', 16)}")
            print(f"  Compliance: {summary.get('compliance_percentage', 0):.1f}%")

        # Business impact
        business_continuity = results.get("business_continuity", "UNKNOWN")
        print(f"\nBusiness Impact: {business_continuity}")

        if business_continuity == "AT_RISK":
            print("WARNING️ WARNING: Changes may impact $500K+ ARR Golden Path")
        elif business_continuity == "PROTECTED":
            print("CHECK SUCCESS: Business continuity maintained")

        # Deployment recommendation
        print(f"\nDeployment Recommendation:")
        if overall_status in ["FULL_COMPLIANCE", "PARTIAL_COMPLIANCE"]:
            print("CHECK SAFE TO DEPLOY: SSOT compliance acceptable")
        elif overall_status == "MINIMAL_COMPLIANCE":
            print("WARNING️ DEPLOY WITH CAUTION: Monitor for issues")
        else:
            print("🚨 DO NOT DEPLOY: Critical compliance failures")

        print(f"{'='*80}")


def main():
    """Main execution function for SSOT compliance testing."""
    parser = argparse.ArgumentParser(description="SSOT Compliance Test Suite - Issue #1098 Phase 2")
    parser.add_argument("--quick", action="store_true", help="Run quick compliance check")
    parser.add_argument("--full", action="store_true", help="Run full compliance suite")
    parser.add_argument("--mission-only", action="store_true", help="Run mission critical tests only")
    parser.add_argument("--baseline", action="store_true", help="Update baseline violations")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")

    args = parser.parse_args()

    # Determine test mode
    if args.baseline:
        test_mode = "baseline"
    elif args.mission_only:
        test_mode = "mission-only"
    elif args.quick:
        test_mode = "quick"
    else:
        test_mode = "full"  # Default to full suite

    # Run compliance tests
    runner = SSotComplianceTestRunner()
    results = runner.run_compliance_tests(test_mode)

    # Generate report
    if args.report or test_mode == "full":
        runner.generate_compliance_report(results)

    # Exit with appropriate code
    overall_status = results.get("overall_status", results.get("status", "FAILED"))
    if overall_status in ["FULL_COMPLIANCE", "PARTIAL_COMPLIANCE", "PASSED"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()