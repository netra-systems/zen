#!/usr/bin/env python3
"""
SSOT Remediation Validation Suite

Comprehensive validation scripts for each phase of SSOT remediation.
Ensures Golden Path protection and system stability throughout remediation process.

Business Value: Platform/Internal - $500K+ ARR Protection
Priority: CRITICAL - Prevents regression during SSOT compliance improvements
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import IsolatedEnvironment
from shared.windows_encoding import setup_windows_encoding

# Setup Windows encoding
setup_windows_encoding()


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    details: str
    duration: float
    error_message: Optional[str] = None


@dataclass
class PhaseValidationReport:
    """Comprehensive validation report for a phase."""
    phase_name: str
    start_time: datetime
    end_time: datetime
    overall_success: bool
    checks: List[ValidationResult]
    compliance_score: float
    golden_path_status: bool
    recommendations: List[str]


class SSotRemediationValidator:
    """Comprehensive validation for SSOT remediation phases."""

    def __init__(self):
        """Initialize validator with project context."""
        self.project_root = PROJECT_ROOT
        self.env = IsolatedEnvironment()
        self.validation_reports_dir = self.project_root / "reports" / "ssot_remediation" / "validation"
        self.validation_reports_dir.mkdir(parents=True, exist_ok=True)

    def run_command(self, command: List[str], timeout: int = 300) -> Tuple[bool, str, str]:
        """Run command with timeout and capture output."""
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def validate_golden_path_functionality(self) -> ValidationResult:
        """CRITICAL: Validate Golden Path functionality is preserved."""
        start_time = time.time()

        # Test WebSocket agent events (core Golden Path functionality)
        success, stdout, stderr = self.run_command([
            "python", "tests/mission_critical/test_websocket_agent_events_suite.py"
        ])

        duration = time.time() - start_time

        if success:
            return ValidationResult(
                check_name="Golden Path WebSocket Events",
                passed=True,
                details="All WebSocket agent events working correctly",
                duration=duration
            )
        else:
            return ValidationResult(
                check_name="Golden Path WebSocket Events",
                passed=False,
                details="Golden Path WebSocket events failed",
                duration=duration,
                error_message=f"STDOUT: {stdout}\nSTDERR: {stderr}"
            )

    def validate_ssot_compliance_score(self) -> ValidationResult:
        """Validate current SSOT compliance score."""
        start_time = time.time()

        success, stdout, stderr = self.run_command([
            "python", "scripts/check_architecture_compliance.py"
        ])

        duration = time.time() - start_time

        if success:
            # Extract compliance score from output
            compliance_score = self._extract_compliance_score(stdout)

            return ValidationResult(
                check_name="SSOT Compliance Score",
                passed=compliance_score >= 98.0,
                details=f"Current compliance: {compliance_score}%",
                duration=duration
            )
        else:
            return ValidationResult(
                check_name="SSOT Compliance Score",
                passed=False,
                details="Failed to check compliance score",
                duration=duration,
                error_message=f"STDOUT: {stdout}\nSTDERR: {stderr}"
            )

    def validate_production_system_integrity(self) -> ValidationResult:
        """Ensure production systems remain 100% compliant."""
        start_time = time.time()

        success, stdout, stderr = self.run_command([
            "python", "scripts/check_architecture_compliance.py", "--production-only"
        ])

        duration = time.time() - start_time

        if success:
            # Check for any production violations
            if "0 violations" in stdout or "100.0% compliant" in stdout:
                return ValidationResult(
                    check_name="Production System Integrity",
                    passed=True,
                    details="Production systems maintain 100% SSOT compliance",
                    duration=duration
                )

        return ValidationResult(
            check_name="Production System Integrity",
            passed=False,
            details="Production system compliance issues detected",
            duration=duration,
            error_message=f"STDOUT: {stdout}\nSTDERR: {stderr}"
        )

    def validate_critical_business_flows(self) -> ValidationResult:
        """Validate critical business flows remain operational."""
        start_time = time.time()

        critical_tests = [
            "tests/e2e/test_auth_backend_desynchronization.py",
            "tests/integration/test_authenticated_chat_workflow_comprehensive.py"
        ]

        all_passed = True
        test_results = []

        for test in critical_tests:
            test_path = self.project_root / test
            if test_path.exists():
                success, stdout, stderr = self.run_command(["python", str(test_path)])
                test_results.append(f"{test}: {'PASS' if success else 'FAIL'}")
                if not success:
                    all_passed = False
            else:
                test_results.append(f"{test}: SKIP (not found)")

        duration = time.time() - start_time

        return ValidationResult(
            check_name="Critical Business Flows",
            passed=all_passed,
            details="; ".join(test_results),
            duration=duration
        )

    def validate_test_infrastructure_health(self) -> ValidationResult:
        """Validate test infrastructure remains healthy after changes."""
        start_time = time.time()

        success, stdout, stderr = self.run_command([
            "python", "tests/unified_test_runner.py",
            "--categories", "mission_critical", "integration",
            "--fast-fail", "--timeout", "300"
        ])

        duration = time.time() - start_time

        return ValidationResult(
            check_name="Test Infrastructure Health",
            passed=success,
            details="Mission critical and integration tests status",
            duration=duration,
            error_message=stderr if not success else None
        )

    def validate_mock_consolidation(self) -> ValidationResult:
        """Validate mock consolidation was successful."""
        start_time = time.time()

        # Check for remaining duplicate mock implementations
        duplicate_mocks = []

        for py_file in self.project_root.rglob("tests/**/*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for mock class definitions (should be consolidated)
                import re
                mock_classes = re.findall(r'class (Mock\w+).*:', content)

                if mock_classes:
                    duplicate_mocks.extend([f"{mock} in {py_file.name}" for mock in mock_classes])

            except Exception:
                continue

        duration = time.time() - start_time

        if len(duplicate_mocks) == 0:
            return ValidationResult(
                check_name="Mock Consolidation",
                passed=True,
                details="All duplicate mock implementations successfully consolidated",
                duration=duration
            )
        else:
            return ValidationResult(
                check_name="Mock Consolidation",
                passed=False,
                details=f"Found {len(duplicate_mocks)} remaining duplicate mocks",
                duration=duration,
                error_message="; ".join(duplicate_mocks[:10])  # Limit to first 10
            )

    def validate_import_standardization(self) -> ValidationResult:
        """Validate import path standardization was successful."""
        start_time = time.time()

        # Check for remaining try/except import patterns
        legacy_imports = []

        for py_file in self.project_root.rglob("tests/**/*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for try/except import patterns
                import re
                if re.search(r'try:\s*import.*except.*import', content, re.DOTALL):
                    legacy_imports.append(str(py_file))

            except Exception:
                continue

        duration = time.time() - start_time

        return ValidationResult(
            check_name="Import Standardization",
            passed=len(legacy_imports) == 0,
            details=f"Legacy import patterns remaining: {len(legacy_imports)}",
            duration=duration,
            error_message="; ".join(legacy_imports[:5]) if legacy_imports else None
        )

    def validate_environment_access_consistency(self) -> ValidationResult:
        """Validate environment access standardization."""
        start_time = time.time()

        # Check for remaining direct os.environ access
        direct_environ_access = []

        test_framework_path = self.project_root / "test_framework"

        if test_framework_path.exists():
            for py_file in test_framework_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Look for direct os.environ access
                    if "os.environ" in content and "IsolatedEnvironment" not in content:
                        direct_environ_access.append(str(py_file))

                except Exception:
                    continue

        duration = time.time() - start_time

        return ValidationResult(
            check_name="Environment Access Consistency",
            passed=len(direct_environ_access) == 0,
            details=f"Direct os.environ access remaining: {len(direct_environ_access)}",
            duration=duration,
            error_message="; ".join(direct_environ_access) if direct_environ_access else None
        )

    def _extract_compliance_score(self, compliance_output: str) -> float:
        """Extract compliance score from compliance check output."""
        import re

        # Look for compliance score pattern
        score_match = re.search(r'Compliance Score:\s*(\d+\.?\d*)%', compliance_output)
        if score_match:
            return float(score_match.group(1))

        # Alternative pattern
        score_match = re.search(r'(\d+\.?\d*)%\s*compliant', compliance_output)
        if score_match:
            return float(score_match.group(1))

        return 0.0

    def run_phase_validation(self, phase_name: str, validation_checks: List[str]) -> PhaseValidationReport:
        """Run comprehensive validation for a specific phase."""
        start_time = datetime.now()

        print(f"\n🔍 RUNNING {phase_name.upper()} VALIDATION")
        print("=" * 60)

        results = []
        overall_success = True

        # Define check mapping
        check_methods = {
            "golden_path": self.validate_golden_path_functionality,
            "compliance_score": self.validate_ssot_compliance_score,
            "production_integrity": self.validate_production_system_integrity,
            "business_flows": self.validate_critical_business_flows,
            "test_infrastructure": self.validate_test_infrastructure_health,
            "mock_consolidation": self.validate_mock_consolidation,
            "import_standardization": self.validate_import_standardization,
            "environment_consistency": self.validate_environment_access_consistency
        }

        # Run requested validation checks
        for check_name in validation_checks:
            if check_name in check_methods:
                print(f"\n⏳ Running {check_name.replace('_', ' ').title()} validation...")

                try:
                    result = check_methods[check_name]()
                    results.append(result)

                    status = "✅ PASS" if result.passed else "❌ FAIL"
                    print(f"{status} - {result.details} ({result.duration:.2f}s)")

                    if not result.passed:
                        overall_success = False
                        if result.error_message:
                            print(f"   Error: {result.error_message[:200]}...")

                except Exception as e:
                    error_result = ValidationResult(
                        check_name=check_name,
                        passed=False,
                        details="Validation check failed with exception",
                        duration=0.0,
                        error_message=str(e)
                    )
                    results.append(error_result)
                    overall_success = False
                    print(f"❌ FAIL - Exception during validation: {str(e)[:100]}...")

        end_time = datetime.now()

        # Extract compliance score for report
        compliance_score = 0.0
        golden_path_status = False

        for result in results:
            if result.check_name == "SSOT Compliance Score" and result.passed:
                compliance_score = self._extract_compliance_score(result.details)
            if result.check_name == "Golden Path WebSocket Events":
                golden_path_status = result.passed

        # Generate recommendations
        recommendations = []
        if not overall_success:
            recommendations.append("Address all failed validation checks before proceeding")
        if compliance_score < 99.0:
            recommendations.append("Continue remediation to achieve >99% compliance")
        if not golden_path_status:
            recommendations.append("CRITICAL: Restore Golden Path functionality immediately")

        report = PhaseValidationReport(
            phase_name=phase_name,
            start_time=start_time,
            end_time=end_time,
            overall_success=overall_success,
            checks=results,
            compliance_score=compliance_score,
            golden_path_status=golden_path_status,
            recommendations=recommendations
        )

        # Save report
        self._save_validation_report(report)

        # Print summary
        print(f"\n📊 {phase_name.upper()} VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Overall Success: {'✅ PASS' if overall_success else '❌ FAIL'}")
        print(f"Golden Path Status: {'✅ OPERATIONAL' if golden_path_status else '❌ COMPROMISED'}")
        print(f"Compliance Score: {compliance_score:.1f}%")
        print(f"Checks Passed: {sum(1 for r in results if r.passed)}/{len(results)}")

        if recommendations:
            print(f"\n📋 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"  • {rec}")

        return report

    def _save_validation_report(self, report: PhaseValidationReport):
        """Save validation report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.validation_reports_dir / f"{report.phase_name}_validation_{timestamp}.json"

        # Convert report to JSON-serializable format
        report_data = {
            "phase_name": report.phase_name,
            "start_time": report.start_time.isoformat(),
            "end_time": report.end_time.isoformat(),
            "overall_success": report.overall_success,
            "compliance_score": report.compliance_score,
            "golden_path_status": report.golden_path_status,
            "recommendations": report.recommendations,
            "checks": [
                {
                    "check_name": check.check_name,
                    "passed": check.passed,
                    "details": check.details,
                    "duration": check.duration,
                    "error_message": check.error_message
                }
                for check in report.checks
            ]
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📄 Validation report saved: {report_file}")


def main():
    """Main entry point for validation suite."""
    if len(sys.argv) < 2:
        print("Usage: python validation_suite.py <phase> [checks...]")
        print("Phases: phase1, phase2, phase3, full")
        print("Example: python validation_suite.py phase1 golden_path compliance_score production_integrity")
        sys.exit(1)

    phase = sys.argv[1]
    custom_checks = sys.argv[2:] if len(sys.argv) > 2 else None

    validator = SSotRemediationValidator()

    # Define standard check sets for each phase
    phase_check_sets = {
        "phase1": ["golden_path", "compliance_score", "production_integrity"],
        "phase2": ["golden_path", "compliance_score", "production_integrity", "mock_consolidation",
                  "import_standardization", "environment_consistency"],
        "phase3": ["golden_path", "compliance_score", "production_integrity", "business_flows",
                  "test_infrastructure"],
        "full": ["golden_path", "compliance_score", "production_integrity", "business_flows",
                "test_infrastructure", "mock_consolidation", "import_standardization",
                "environment_consistency"]
    }

    checks = custom_checks if custom_checks else phase_check_sets.get(phase, ["golden_path"])

    report = validator.run_phase_validation(phase, checks)

    # Exit with appropriate code
    sys.exit(0 if report.overall_success else 1)


if __name__ == "__main__":
    main()