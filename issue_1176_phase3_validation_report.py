#!/usr/bin/env python3
"""
Issue #1176 Phase 3 Validation Report Generator
===============================================

This script performs Phase 3 validation for Issue #1176 by analyzing:
1. Anti-recursive fixes in the test runner
2. Test infrastructure health
3. Critical component import status
4. Documentation alignment with fixes
5. Infrastructure validation readiness

This validation runs WITHOUT requiring external command execution,
focusing on static analysis and import validation.
"""

import sys
import os
from pathlib import Path
import ast
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class Issue1176Phase3Validator:
    """Validates Issue #1176 Phase 3 fixes and infrastructure health."""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.validation_results = {}
        self.critical_issues = []
        self.validated_fixes = []

    def validate_anti_recursive_fixes(self) -> Dict[str, Any]:
        """Validate that anti-recursive fixes are in place in the test runner."""
        print("🔍 Validating anti-recursive fixes in unified test runner...")

        test_runner_path = self.project_root / "tests" / "unified_test_runner.py"

        if not test_runner_path.exists():
            return {
                "status": "CRITICAL_FAILURE",
                "issue": "Unified test runner not found",
                "path": str(test_runner_path)
            }

        try:
            with open(test_runner_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for the critical fix: total_tests_run == 0 validation
            zero_tests_check = "total_tests_run == 0" in content
            failure_message = "No tests were executed - this indicates infrastructure failure" in content
            exit_code_fix = "return 1  # No tests run is a failure" in content

            # Check for fast collection fix
            fast_collection_fix = "Fast collection mode discovered tests but did NOT execute them" in content

            fixes_present = {
                "zero_tests_validation": zero_tests_check,
                "failure_error_message": failure_message,
                "exit_code_fix": exit_code_fix,
                "fast_collection_fix": fast_collection_fix
            }

            all_fixes_present = all(fixes_present.values())

            return {
                "status": "VALIDATED" if all_fixes_present else "INCOMPLETE",
                "fixes_present": fixes_present,
                "all_critical_fixes": all_fixes_present,
                "file_analyzed": str(test_runner_path)
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "file": str(test_runner_path)
            }

    def validate_anti_recursive_test_exists(self) -> Dict[str, Any]:
        """Validate that the anti-recursive validation test exists and is comprehensive."""
        print("🔍 Validating anti-recursive test file exists...")

        test_file_path = self.project_root / "tests" / "critical" / "test_issue_1176_anti_recursive_validation.py"

        if not test_file_path.exists():
            return {
                "status": "MISSING",
                "issue": "Anti-recursive validation test file not found",
                "expected_path": str(test_file_path)
            }

        try:
            with open(test_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for critical test methods
            required_tests = [
                "test_fast_collection_mode_must_fail_with_no_execution",
                "test_zero_tests_executed_must_fail",
                "test_recursive_pattern_detection",
                "test_truth_before_documentation_principle",
                "test_false_success_pattern_detection"
            ]

            tests_present = {}
            for test_name in required_tests:
                tests_present[test_name] = test_name in content

            all_tests_present = all(tests_present.values())

            return {
                "status": "VALIDATED" if all_tests_present else "INCOMPLETE",
                "tests_present": tests_present,
                "all_required_tests": all_tests_present,
                "file_size": len(content),
                "file_path": str(test_file_path)
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "file": str(test_file_path)
            }

    def validate_documentation_alignment(self) -> Dict[str, Any]:
        """Validate that documentation reflects the current crisis state correctly."""
        print("🔍 Validating documentation alignment with crisis state...")

        status_file = self.project_root / "reports" / "MASTER_WIP_STATUS.md"

        if not status_file.exists():
            return {
                "status": "MISSING",
                "issue": "MASTER_WIP_STATUS.md not found",
                "path": str(status_file)
            }

        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for truth-before-documentation indicators
            truth_indicators = [
                "UNVALIDATED",
                "NEEDS VERIFICATION",
                "CLAIMS NEED VERIFICATION",
                "❌ CRITICAL",
                "⚠️",
                "Phase 1 fix applied",
                "Issue #1176"
            ]

            indicators_present = {}
            for indicator in truth_indicators:
                indicators_present[indicator] = indicator in content

            # Check for specific Phase 1 completion claim
            phase1_complete = "Issue #1176 PHASE 1 COMPLETE" in content
            phase3_pending = "Phase 3: Infrastructure Validation" in content and "⚠️" in content

            return {
                "status": "ALIGNED" if phase1_complete and phase3_pending else "MISALIGNED",
                "truth_indicators": indicators_present,
                "phase1_documented": phase1_complete,
                "phase3_marked_pending": phase3_pending,
                "file_path": str(status_file)
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "file": str(status_file)
            }

    def validate_critical_imports(self) -> Dict[str, Any]:
        """Validate that critical system imports work (without execution)."""
        print("🔍 Validating critical system imports...")

        import_tests = [
            ("unified_test_runner", "tests.unified_test_runner", "UnifiedTestRunner"),
            ("test_framework", "test_framework.ssot.base_test_case", "SSotBaseTestCase"),
            ("websocket_manager", "netra_backend.app.websocket_core.manager", None),
            ("auth_integration", "netra_backend.app.auth_integration.auth", None),
            ("isolated_environment", "shared.isolated_environment", "IsolatedEnvironment"),
        ]

        import_results = {}

        for test_name, module_path, class_name in import_tests:
            try:
                # Attempt to import the module
                __import__(module_path)

                if class_name:
                    # Try to import the specific class
                    module = sys.modules[module_path]
                    getattr(module, class_name)

                import_results[test_name] = {
                    "status": "SUCCESS",
                    "module": module_path,
                    "class": class_name
                }

            except ImportError as e:
                import_results[test_name] = {
                    "status": "IMPORT_ERROR",
                    "error": str(e),
                    "module": module_path
                }
            except AttributeError as e:
                import_results[test_name] = {
                    "status": "CLASS_NOT_FOUND",
                    "error": str(e),
                    "module": module_path,
                    "class": class_name
                }
            except Exception as e:
                import_results[test_name] = {
                    "status": "UNEXPECTED_ERROR",
                    "error": str(e),
                    "module": module_path
                }

        successful_imports = sum(1 for result in import_results.values() if result["status"] == "SUCCESS")
        total_imports = len(import_tests)

        return {
            "status": "HEALTHY" if successful_imports == total_imports else "DEGRADED",
            "successful_imports": successful_imports,
            "total_imports": total_imports,
            "success_rate": successful_imports / total_imports * 100,
            "import_details": import_results
        }

    def validate_test_infrastructure_structure(self) -> Dict[str, Any]:
        """Validate test infrastructure directory structure and key files."""
        print("🔍 Validating test infrastructure structure...")

        required_paths = [
            "tests/unified_test_runner.py",
            "tests/mission_critical/",
            "test_framework/ssot/",
            "test_framework/ssot/base_test_case.py",
            "test_framework/unified_docker_manager.py"
        ]

        structure_results = {}

        for path_str in required_paths:
            path = self.project_root / path_str
            if path.is_file():
                structure_results[path_str] = {
                    "status": "EXISTS",
                    "type": "file",
                    "size": path.stat().st_size
                }
            elif path.is_dir():
                structure_results[path_str] = {
                    "status": "EXISTS",
                    "type": "directory",
                    "file_count": len(list(path.glob("*.py")))
                }
            else:
                structure_results[path_str] = {
                    "status": "MISSING",
                    "type": "unknown"
                }

        missing_paths = [path for path, result in structure_results.items() if result["status"] == "MISSING"]

        return {
            "status": "COMPLETE" if not missing_paths else "INCOMPLETE",
            "missing_paths": missing_paths,
            "structure_details": structure_results
        }

    def analyze_test_execution_patterns(self) -> Dict[str, Any]:
        """Analyze test execution patterns in the codebase."""
        print("🔍 Analyzing test execution patterns...")

        # Look for direct pytest usage that bypasses the unified runner
        problematic_patterns = []

        # Check for direct pytest calls in scripts
        for script_path in self.project_root.glob("**/*.py"):
            if "backup" in str(script_path) or ".git" in str(script_path):
                continue

            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for direct pytest execution
                if re.search(r'subprocess.*pytest|os\.system.*pytest|pytest\.main', content):
                    problematic_patterns.append({
                        "file": str(script_path.relative_to(self.project_root)),
                        "issue": "Direct pytest execution found",
                        "pattern": "bypasses_unified_runner"
                    })

                # Look for potential 0-test success patterns
                if re.search(r'return\s+0.*# No tests|sys\.exit\(0\).*# No tests', content):
                    problematic_patterns.append({
                        "file": str(script_path.relative_to(self.project_root)),
                        "issue": "Potential false success pattern",
                        "pattern": "false_success_risk"
                    })

            except (UnicodeDecodeError, PermissionError):
                continue  # Skip binary or inaccessible files

        return {
            "status": "CLEAN" if not problematic_patterns else "ISSUES_FOUND",
            "problematic_patterns": problematic_patterns,
            "pattern_count": len(problematic_patterns)
        }

    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        print("\n" + "="*60)
        print("🚀 ISSUE #1176 PHASE 3 VALIDATION REPORT")
        print("="*60)

        # Run all validations
        validations = {
            "anti_recursive_fixes": self.validate_anti_recursive_fixes(),
            "anti_recursive_test": self.validate_anti_recursive_test_exists(),
            "documentation_alignment": self.validate_documentation_alignment(),
            "critical_imports": self.validate_critical_imports(),
            "infrastructure_structure": self.validate_test_infrastructure_structure(),
            "execution_patterns": self.analyze_test_execution_patterns()
        }

        # Analyze overall status
        critical_failures = []
        warnings = []
        successes = []

        for validation_name, result in validations.items():
            status = result.get("status", "UNKNOWN")

            if status in ["CRITICAL_FAILURE", "ERROR", "MISSING"]:
                critical_failures.append(validation_name)
            elif status in ["INCOMPLETE", "DEGRADED", "ISSUES_FOUND", "MISALIGNED"]:
                warnings.append(validation_name)
            else:
                successes.append(validation_name)

        overall_status = "CRITICAL" if critical_failures else ("WARNING" if warnings else "SUCCESS")

        # Generate summary
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "phase": "Issue #1176 Phase 3 Validation",
            "summary": {
                "critical_failures": len(critical_failures),
                "warnings": len(warnings),
                "successes": len(successes),
                "total_validations": len(validations)
            },
            "validations": validations,
            "recommendations": self._generate_recommendations(validations, critical_failures, warnings)
        }

        return report

    def _generate_recommendations(self, validations: Dict, critical_failures: List, warnings: List) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        if critical_failures:
            recommendations.append("🚨 CRITICAL: Address critical failures before proceeding with Phase 3")

        if warnings:
            recommendations.append("⚠️  WARNING: Resolve warnings to ensure complete validation")

        # Specific recommendations based on results
        if "anti_recursive_fixes" in critical_failures:
            recommendations.append("• Fix anti-recursive logic in unified_test_runner.py")

        if "critical_imports" in warnings:
            import_result = validations["critical_imports"]
            if import_result["success_rate"] < 100:
                recommendations.append(f"• Fix import issues ({import_result['success_rate']:.1f}% success rate)")

        if "execution_patterns" in warnings:
            pattern_result = validations["execution_patterns"]
            if pattern_result["pattern_count"] > 0:
                recommendations.append(f"• Address {pattern_result['pattern_count']} problematic test execution patterns")

        if not critical_failures and not warnings:
            recommendations.append("✅ Phase 3 validation complete - proceed to test execution")

        return recommendations

    def print_report(self, report: Dict[str, Any]):
        """Print formatted validation report."""
        print(f"\n📊 VALIDATION SUMMARY")
        print(f"Overall Status: {report['overall_status']}")
        print(f"Critical Failures: {report['summary']['critical_failures']}")
        print(f"Warnings: {report['summary']['warnings']}")
        print(f"Successes: {report['summary']['successes']}")

        print(f"\n📋 DETAILED RESULTS:")
        for name, result in report['validations'].items():
            status = result.get('status', 'UNKNOWN')
            icon = "✅" if status in ["VALIDATED", "SUCCESS", "HEALTHY", "COMPLETE", "CLEAN", "ALIGNED"] else ("⚠️" if status in ["INCOMPLETE", "DEGRADED", "ISSUES_FOUND", "MISALIGNED"] else "❌")
            print(f"{icon} {name}: {status}")

        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"   {rec}")

        return report['overall_status'] == "SUCCESS"

def main():
    """Main validation function."""
    validator = Issue1176Phase3Validator()
    report = validator.generate_validation_report()
    success = validator.print_report(report)

    print(f"\n" + "="*60)
    if success:
        print("🎉 PHASE 3 VALIDATION PASSED - Infrastructure validation ready")
        return 0
    else:
        print("⚠️  PHASE 3 VALIDATION INCOMPLETE - Address issues before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())