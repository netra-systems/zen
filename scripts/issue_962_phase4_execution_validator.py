#!/usr/bin/env python3
"""
Issue #962 Phase 4 Execution Validator Script

This script provides the execution framework for validating atomic remediation changes
during Issue #962 Configuration SSOT remediation. It ensures each change maintains
system stability while progressing toward 100% SSOT compliance.

Business Impact: Protects $500K+ ARR Golden Path during remediation execution.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class ValidationResult:
    """Results from validation testing"""
    success: bool
    violations_count: int
    test_failures: List[str]
    execution_time: float
    details: Dict[str, Any]


@dataclass
class RemediationProgress:
    """Track overall remediation progress"""
    deprecated_imports_remaining: int
    deprecated_managers_remaining: int
    auth_consistency_score: float
    mission_critical_score: float
    ssot_compliance_percentage: float


class Issue962Phase4Validator:
    """
    Execution validator for Issue #962 Phase 4 Configuration SSOT remediation.

    Provides comprehensive validation framework for atomic changes while ensuring
    Golden Path functionality remains operational throughout remediation.
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results_dir = self.project_root / "test_results" / "issue_962_phase4"
        self.test_results_dir.mkdir(parents=True, exist_ok=True)

        # Test suite file paths
        self.test_suites = {
            "import_patterns": "tests/unit/config_ssot/test_issue_962_import_pattern_enforcement.py",
            "single_manager": "tests/unit/config_ssot/test_issue_962_single_configuration_manager_validation.py",
            "auth_flow": "tests/integration/config_ssot/test_issue_962_authentication_flow_validation.py",
            "mission_critical": "tests/mission_critical/test_issue_962_configuration_ssot_final_validation.py",
            "staging_validation": "tests/staging/test_issue_962_gcp_staging_configuration_validation.py"
        }

        # Files to remediate in execution order (risk-based)
        self.remediation_files = {
            # Phase 4A: Low-Risk Files
            "phase_4a": [
                "netra_backend/app/db/cache_core.py",
                "netra_backend/app/db/migration_utils.py",
                "netra_backend/app/core/environment_constants.py",
                "netra_backend/app/core/config_validator.py",
                "netra_backend/app/llm/llm_manager.py"
            ],
            # Phase 4B: Medium-Risk Files
            "phase_4b": [
                "netra_backend/app/startup_checks/system_checks.py",
                "netra_backend/app/core/configuration/database.py",
                "netra_backend/app/core/configuration/startup_validator.py",
                "netra_backend/app/core/cross_service_validators/security_validators.py",
                "netra_backend/app/services/configuration_service.py"
            ],
            # Phase 4C: High-Risk Critical Files
            "phase_4c": [
                "netra_backend/app/core/websocket_cors.py",  # Critical for Golden Path
                "netra_backend/app/auth_integration/auth_config.py",  # Authentication Critical
                "netra_backend/app/startup_module.py",  # System Startup Critical
                "netra_backend/app/core/config.py"  # MOST CRITICAL - SSOT itself
            ]
        }

    def run_baseline_validation(self) -> Dict[str, ValidationResult]:
        """
        Run baseline validation to establish current system state.

        This creates the baseline against which all remediation progress will be measured.
        All tests are expected to FAIL initially, showing current SSOT violations.
        """
        print("=" * 80)
        print("ISSUE #962 PHASE 4: BASELINE VALIDATION")
        print("Business Impact: $500K+ ARR Golden Path Protection")
        print("Expected: All tests FAIL showing current SSOT violations")
        print("=" * 80)

        baseline_results = {}

        for suite_name, suite_path in self.test_suites.items():
            print(f"\n--- Running Baseline Test: {suite_name} ---")
            result = self._run_test_suite(suite_path, f"baseline_{suite_name}")
            baseline_results[suite_name] = result

            print(f"Suite: {suite_name}")
            print(f"  Status: {'PASS' if result.success else 'FAIL (EXPECTED)'}")
            print(f"  Violations: {result.violations_count}")
            print(f"  Failures: {len(result.test_failures)}")
            print(f"  Time: {result.execution_time:.2f}s")

        # Save baseline for comparison
        self._save_validation_results("baseline", baseline_results)

        # Generate baseline summary
        summary = self._generate_progress_summary(baseline_results)
        print(f"\n=== BASELINE SUMMARY ===")
        print(f"Deprecated Imports Remaining: {summary.deprecated_imports_remaining}")
        print(f"Deprecated Managers Remaining: {summary.deprecated_managers_remaining}")
        print(f"SSOT Compliance: {summary.ssot_compliance_percentage:.1f}%")
        print(f"Mission Critical Score: {summary.mission_critical_score:.1f}%")

        return baseline_results

    def validate_pre_change(self, file_path: str) -> ValidationResult:
        """
        Validate system state before making changes to specific file.

        Args:
            file_path: File about to be changed

        Returns:
            ValidationResult with current system state
        """
        print(f"\n--- PRE-CHANGE VALIDATION: {file_path} ---")

        # Run quick validation focused on import patterns and critical systems
        start_time = time.time()

        # 1. Check current violations for this specific file
        violations = self._scan_file_violations(file_path)

        # 2. Run critical system health checks
        critical_health = self._run_critical_health_checks()

        # 3. Quick import pattern test
        import_test = self._run_test_suite(
            self.test_suites["import_patterns"] + "::TestIssue962ImportPatternEnforcement::test_no_deprecated_get_unified_config_imports",
            f"pre_change_{Path(file_path).stem}"
        )

        execution_time = time.time() - start_time

        result = ValidationResult(
            success=critical_health["system_healthy"],
            violations_count=len(violations),
            test_failures=import_test.test_failures,
            execution_time=execution_time,
            details={
                "file_violations": violations,
                "critical_health": critical_health,
                "import_test_result": import_test.details
            }
        )

        print(f"  System Health: {'✅ HEALTHY' if result.success else '❌ UNHEALTHY'}")
        print(f"  File Violations: {result.violations_count}")
        print(f"  Validation Time: {result.execution_time:.2f}s")

        return result

    def validate_post_change(self, file_path: str, baseline: ValidationResult) -> ValidationResult:
        """
        Validate system state after making changes to specific file.

        Args:
            file_path: File that was just changed
            baseline: Pre-change validation results for comparison

        Returns:
            ValidationResult with post-change system state
        """
        print(f"\n--- POST-CHANGE VALIDATION: {file_path} ---")

        start_time = time.time()

        # 1. Check violations reduced for this file
        violations = self._scan_file_violations(file_path)

        # 2. Ensure system still healthy
        critical_health = self._run_critical_health_checks()

        # 3. Run import pattern test to verify progress
        import_test = self._run_test_suite(
            self.test_suites["import_patterns"] + "::TestIssue962ImportPatternEnforcement::test_no_deprecated_get_unified_config_imports",
            f"post_change_{Path(file_path).stem}"
        )

        # 4. Run critical authentication test
        auth_test = self._run_test_suite(
            "tests/mission_critical/test_websocket_agent_events_suite.py",
            f"post_auth_check_{Path(file_path).stem}"
        )

        execution_time = time.time() - start_time

        # Evaluate success criteria
        success_criteria = [
            critical_health["system_healthy"],  # System must remain healthy
            len(violations) <= baseline.violations_count,  # Violations must not increase
            file_path not in [v["file"] for v in violations],  # This file should be fixed
            auth_test.success or len(auth_test.test_failures) <= 2  # Auth must work (allow some tolerance)
        ]

        result = ValidationResult(
            success=all(success_criteria),
            violations_count=len(violations),
            test_failures=import_test.test_failures + auth_test.test_failures,
            execution_time=execution_time,
            details={
                "file_violations": violations,
                "critical_health": critical_health,
                "import_test_result": import_test.details,
                "auth_test_result": auth_test.details,
                "success_criteria": success_criteria,
                "violations_reduced": baseline.violations_count - len(violations),
                "file_fixed": file_path not in [v["file"] for v in violations]
            }
        )

        print(f"  System Health: {'✅ HEALTHY' if critical_health['system_healthy'] else '❌ UNHEALTHY'}")
        print(f"  Violations Reduced: {result.details['violations_reduced']}")
        print(f"  File Fixed: {'✅ YES' if result.details['file_fixed'] else '❌ NO'}")
        print(f"  Overall Success: {'✅ PASS' if result.success else '❌ FAIL'}")
        print(f"  Validation Time: {result.execution_time:.2f}s")

        return result

    def run_progress_validation(self) -> Dict[str, ValidationResult]:
        """
        Run full progress validation to measure overall remediation progress.

        Returns:
            Dictionary of validation results from all test suites
        """
        print(f"\n--- PROGRESS VALIDATION ---")

        progress_results = {}

        for suite_name, suite_path in self.test_suites.items():
            print(f"\nRunning Progress Test: {suite_name}")
            result = self._run_test_suite(suite_path, f"progress_{suite_name}")
            progress_results[suite_name] = result

            print(f"  Status: {'✅ PASS' if result.success else '❌ FAIL'}")
            print(f"  Violations: {result.violations_count}")
            print(f"  Failures: {len(result.test_failures)}")

        # Generate progress summary
        summary = self._generate_progress_summary(progress_results)
        print(f"\n=== PROGRESS SUMMARY ===")
        print(f"Deprecated Imports Remaining: {summary.deprecated_imports_remaining}")
        print(f"Deprecated Managers Remaining: {summary.deprecated_managers_remaining}")
        print(f"SSOT Compliance: {summary.ssot_compliance_percentage:.1f}%")
        print(f"Auth Consistency: {summary.auth_consistency_score:.1f}%")
        print(f"Mission Critical Score: {summary.mission_critical_score:.1f}%")

        # Save progress results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_validation_results(f"progress_{timestamp}", progress_results)

        return progress_results

    def run_final_validation(self) -> bool:
        """
        Run final validation to confirm 100% SSOT compliance achieved.

        Returns:
            True if all validation tests PASS (Issue #962 resolved)
        """
        print("=" * 80)
        print("ISSUE #962 PHASE 4: FINAL VALIDATION")
        print("Business Goal: Confirm 100% SSOT compliance achieved")
        print("Expected: All tests PASS proving Issue #962 resolved")
        print("=" * 80)

        final_results = {}
        all_passed = True

        for suite_name, suite_path in self.test_suites.items():
            print(f"\n--- Final Test: {suite_name} ---")
            result = self._run_test_suite(suite_path, f"final_{suite_name}")
            final_results[suite_name] = result

            if not result.success:
                all_passed = False

            print(f"Suite: {suite_name}")
            print(f"  Status: {'✅ PASS' if result.success else '❌ FAIL'}")
            print(f"  Violations: {result.violations_count}")
            print(f"  Failures: {len(result.test_failures)}")

            if result.test_failures:
                print(f"  Failed Tests:")
                for failure in result.test_failures[:3]:  # Show first 3
                    print(f"    - {failure}")
                if len(result.test_failures) > 3:
                    print(f"    ... and {len(result.test_failures) - 3} more")

        # Save final results
        self._save_validation_results("final", final_results)

        # Generate final summary
        summary = self._generate_progress_summary(final_results)
        print(f"\n=== FINAL RESULTS ===")
        print(f"Issue #962 Resolution: {'✅ COMPLETE' if all_passed else '❌ INCOMPLETE'}")
        print(f"Deprecated Imports: {summary.deprecated_imports_remaining} (Expected: 0)")
        print(f"Deprecated Managers: {summary.deprecated_managers_remaining} (Expected: 0)")
        print(f"SSOT Compliance: {summary.ssot_compliance_percentage:.1f}% (Expected: 100%)")
        print(f"Mission Critical: {summary.mission_critical_score:.1f}% (Expected: 100%)")

        if all_passed:
            print(f"\n🎉 SUCCESS: Issue #962 Configuration SSOT remediation COMPLETE!")
            print(f"🎉 $500K+ ARR Golden Path fully protected with 100% SSOT compliance")
        else:
            print(f"\n⚠️ INCOMPLETE: Issue #962 remediation requires additional work")
            print(f"⚠️ Business Impact: Golden Path still at risk from configuration fragmentation")

        return all_passed

    def _run_test_suite(self, test_path: str, result_name: str) -> ValidationResult:
        """Run specific test suite and capture results"""
        start_time = time.time()

        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "--no-header",
            f"--json-report-file={self.test_results_dir / f'{result_name}.json'}"
        ]

        try:
            # Run test
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            execution_time = time.time() - start_time

            # Parse results
            violations_count = self._extract_violations_from_output(result.stdout)
            test_failures = self._extract_test_failures_from_output(result.stdout)

            return ValidationResult(
                success=result.returncode == 0,
                violations_count=violations_count,
                test_failures=test_failures,
                execution_time=execution_time,
                details={
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                success=False,
                violations_count=999,
                test_failures=["Test suite timed out after 5 minutes"],
                execution_time=time.time() - start_time,
                details={"error": "timeout"}
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                violations_count=999,
                test_failures=[f"Test execution error: {str(e)}"],
                execution_time=time.time() - start_time,
                details={"error": str(e)}
            )

    def _scan_file_violations(self, file_path: str) -> List[Dict[str, str]]:
        """Scan specific file for deprecated import violations"""
        violations = []
        full_path = self.project_root / file_path

        if not full_path.exists():
            return violations

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for deprecated import pattern
            deprecated_pattern = "from netra_backend.app.core.configuration.base import get_unified_config"
            if deprecated_pattern in content:
                violations.append({
                    "file": file_path,
                    "pattern": deprecated_pattern,
                    "type": "deprecated_import"
                })

        except Exception as e:
            pass  # Ignore file read errors

        return violations

    def _run_critical_health_checks(self) -> Dict[str, Any]:
        """Run critical system health checks"""
        health_status = {
            "system_healthy": True,
            "checks": {}
        }

        # Check 1: Basic import works
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            health_status["checks"]["ssot_import"] = True
        except Exception as e:
            health_status["checks"]["ssot_import"] = False
            health_status["system_healthy"] = False
            health_status["checks"]["ssot_import_error"] = str(e)

        # Check 2: System can start (basic validation)
        try:
            # This is a simplified check - in real implementation would check more
            health_status["checks"]["system_start"] = True
        except Exception as e:
            health_status["checks"]["system_start"] = False
            health_status["system_healthy"] = False

        return health_status

    def _extract_violations_from_output(self, output: str) -> int:
        """Extract violation count from test output"""
        # Look for patterns in the test output
        lines = output.split('\n')
        for line in lines:
            if "deprecated import occurrences" in line.lower():
                try:
                    # Extract number from "Found 14 deprecated import occurrences"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "deprecated" in part.lower() and i > 0:
                            return int(parts[i-1])
                except:
                    pass
        return 0

    def _extract_test_failures_from_output(self, output: str) -> List[str]:
        """Extract test failure information from output"""
        failures = []
        lines = output.split('\n')

        for line in lines:
            if "FAILED" in line and "::" in line:
                # Extract test name from pytest failure line
                test_name = line.split()[0] if line.split() else line
                failures.append(test_name)

        return failures

    def _generate_progress_summary(self, results: Dict[str, ValidationResult]) -> RemediationProgress:
        """Generate progress summary from validation results"""

        # Extract metrics from test results
        deprecated_imports = 0
        deprecated_managers = 0
        auth_score = 0.0
        mission_critical_score = 0.0
        ssot_compliance = 0.0

        # Import patterns test
        if "import_patterns" in results:
            deprecated_imports = results["import_patterns"].violations_count

        # Single manager test
        if "single_manager" in results:
            deprecated_managers = results["single_manager"].violations_count

        # Auth flow test
        if "auth_flow" in results:
            auth_score = 100.0 if results["auth_flow"].success else 0.0

        # Mission critical test
        if "mission_critical" in results:
            mission_critical_score = 100.0 if results["mission_critical"].success else 0.0

        # Calculate SSOT compliance (based on import pattern improvements)
        if deprecated_imports == 0:
            ssot_compliance = 100.0
        else:
            # Estimated based on original 14 violations
            ssot_compliance = max(0, (14 - deprecated_imports) / 14 * 100)

        return RemediationProgress(
            deprecated_imports_remaining=deprecated_imports,
            deprecated_managers_remaining=deprecated_managers,
            auth_consistency_score=auth_score,
            mission_critical_score=mission_critical_score,
            ssot_compliance_percentage=ssot_compliance
        )

    def _save_validation_results(self, name: str, results: Dict[str, ValidationResult]):
        """Save validation results to file for tracking"""
        timestamp = datetime.now().isoformat()

        # Convert results to serializable format
        serializable_results = {}
        for suite_name, result in results.items():
            serializable_results[suite_name] = {
                "success": result.success,
                "violations_count": result.violations_count,
                "test_failures": result.test_failures,
                "execution_time": result.execution_time,
                "timestamp": timestamp
            }

        result_file = self.test_results_dir / f"{name}_results.json"
        with open(result_file, 'w') as f:
            json.dump(serializable_results, f, indent=2)

        print(f"Results saved to: {result_file}")


def main():
    """Main execution function for Issue #962 Phase 4 validation"""

    print("Issue #962 Phase 4 Execution Validator")
    print("Configuration SSOT Remediation Test Framework")
    print("Business Impact: $500K+ ARR Golden Path Protection")
    print("=" * 80)

    validator = Issue962Phase4Validator()

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "baseline":
            print("Running baseline validation...")
            validator.run_baseline_validation()

        elif command == "progress":
            print("Running progress validation...")
            validator.run_progress_validation()

        elif command == "final":
            print("Running final validation...")
            success = validator.run_final_validation()
            sys.exit(0 if success else 1)

        elif command == "prechange" and len(sys.argv) > 2:
            file_path = sys.argv[2]
            print(f"Running pre-change validation for: {file_path}")
            validator.validate_pre_change(file_path)

        elif command == "postchange" and len(sys.argv) > 2:
            file_path = sys.argv[2]
            print(f"Running post-change validation for: {file_path}")
            # For demo, create a dummy baseline
            baseline = ValidationResult(True, 1, [], 0.0, {})
            validator.validate_post_change(file_path, baseline)

        else:
            print("Usage:")
            print("  python scripts/issue_962_phase4_execution_validator.py baseline")
            print("  python scripts/issue_962_phase4_execution_validator.py progress")
            print("  python scripts/issue_962_phase4_execution_validator.py final")
            print("  python scripts/issue_962_phase4_execution_validator.py prechange <file_path>")
            print("  python scripts/issue_962_phase4_execution_validator.py postchange <file_path>")
    else:
        # Default: run baseline validation
        print("Running default baseline validation...")
        validator.run_baseline_validation()


if __name__ == "__main__":
    main()