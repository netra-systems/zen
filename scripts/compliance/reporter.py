#!/usr/bin/env python3
"""
Compliance report generator.
Generates human-readable reports for architecture compliance violations.
"""

from typing import List, Dict, Tuple

from .core import Violation, ComplianceResults


class ComplianceReporter:
    """Generates compliance reports"""
    
    def __init__(self, max_file_lines: int, max_function_lines: int):
        self.max_file_lines = max_file_lines
        self.max_function_lines = max_function_lines
    
    def generate_report(self, results: ComplianceResults) -> str:
        """Generate full compliance report"""
        self._print_report_header()
        self._print_all_violation_sections(results)
        return self._generate_final_summary(results)
    
    def _print_report_header(self) -> None:
        """Print report header"""
        print("\n" + "="*80)
        print("ARCHITECTURE COMPLIANCE REPORT")
        print("="*80)
    
    def _print_all_violation_sections(self, results: ComplianceResults) -> None:
        """Print all violation report sections"""
        self._report_file_size_violations(results)
        self._report_function_complexity_violations(results)
        self._report_duplicate_type_violations(results)
        self._report_test_stub_violations(results)
    
    def _report_file_size_violations(self, results: ComplianceResults) -> None:
        """Report file size violations"""
        print(f"\n[FILE SIZE VIOLATIONS] (>{self.max_file_lines} lines)")
        print("-" * 40)
        file_violations = self._get_violations_by_type(results, "file_size")
        self._print_file_violations(file_violations)
    
    def _get_violations_by_type(self, results: ComplianceResults, violation_type: str) -> List[Violation]:
        """Get violations filtered by type"""
        return [v for v in results.violations if v.violation_type == violation_type]
    
    def _print_file_violations(self, file_violations: List[Violation]) -> None:
        """Print file violation details"""
        if file_violations:
            self._print_violation_list(file_violations, 10, "lines")
            print(f"\n  Total violations: {len(file_violations)}")
        else:
            print("  [PASS] No violations found")
    
    def _print_violation_list(self, violations: List[Violation], limit: int, suffix: str) -> None:
        """Print a limited list of violations"""
        for violation in violations[:limit]:
            print(f"  {violation.actual_value:4d} {suffix}: {violation.file_path}")
        self._print_truncation_message(violations, limit)
    
    def _print_truncation_message(self, violations: List[Violation], limit: int) -> None:
        """Print truncation message if needed"""
        if len(violations) > limit:
            print(f"  ... and {len(violations)-limit} more files")
    
    def _report_function_complexity_violations(self, results: ComplianceResults) -> None:
        """Report function complexity violations"""
        print(f"\n[FUNCTION COMPLEXITY VIOLATIONS] (>{self.max_function_lines} lines)")
        print("-" * 40)
        func_violations = self._get_violations_by_type(results, "function_complexity")
        func_errors, func_warnings = self._categorize_function_violations(func_violations)
        self._print_function_violations(func_errors, func_warnings)
    
    def _categorize_function_violations(self, func_violations: List[Violation]) -> Tuple[List[Violation], List[Violation]]:
        """Categorize function violations by severity"""
        func_errors = [v for v in func_violations if v.severity == "medium"]
        func_warnings = [v for v in func_violations if v.severity == "low"]
        return func_errors, func_warnings
    
    def _print_function_violations(self, func_errors: List[Violation], func_warnings: List[Violation]) -> None:
        """Print function violation details"""
        if func_errors:
            self._print_function_error_list(func_errors)
        if func_warnings:
            self._print_function_warning_list(func_warnings)
        self._print_function_summary(func_errors, func_warnings)
    
    def _print_function_error_list(self, func_errors: List[Violation]) -> None:
        """Print function error violations"""
        print("  VIOLATIONS (must fix):")
        for violation in func_errors[:5]:
            print(f"    {violation.actual_value:3d} lines: {violation.function_name}() in {violation.file_path}")
        self._print_error_truncation(func_errors)
    
    def _print_error_truncation(self, func_errors: List[Violation]) -> None:
        """Print error truncation message if needed"""
        if len(func_errors) > 5:
            print(f"    ... and {len(func_errors)-5} more violations")
    
    def _print_function_warning_list(self, func_warnings: List[Violation]) -> None:
        """Print function warning violations"""
        print("\n  WARNINGS (example/demo files):")
        for violation in func_warnings[:5]:
            print(f"    {violation.actual_value:3d} lines: {violation.function_name}() in {violation.file_path}")
        self._print_warning_truncation(func_warnings)
    
    def _print_warning_truncation(self, func_warnings: List[Violation]) -> None:
        """Print warning truncation message if needed"""
        if len(func_warnings) > 5:
            print(f"    ... and {len(func_warnings)-5} more warnings")
    
    def _print_function_summary(self, func_errors: List[Violation], func_warnings: List[Violation]) -> None:
        """Print function violation summary"""
        if func_errors or func_warnings:
            print(f"\n  Total: {len(func_errors)} violations, {len(func_warnings)} warnings")
        else:
            print("  [PASS] No violations found")
    
    def _report_duplicate_type_violations(self, results: ComplianceResults) -> None:
        """Report duplicate type violations"""
        print("\n[DUPLICATE TYPE DEFINITIONS]")
        print("-" * 40)
        duplicate_violations = self._get_violations_by_type(results, "duplicate_types")
        self._print_duplicate_violations(duplicate_violations)
    
    def _print_duplicate_violations(self, duplicate_violations: List[Violation]) -> None:
        """Print duplicate type violation details"""
        if duplicate_violations:
            self._print_duplicate_list(duplicate_violations)
            print(f"\n  Total duplicate types: {len(duplicate_violations)}")
        else:
            print("  [PASS] No duplicates found")
    
    def _print_duplicate_list(self, duplicate_violations: List[Violation]) -> None:
        """Print duplicate violation list"""
        for violation in duplicate_violations[:10]:
            print(f"  {violation.description}")
            print(f"    Files: {violation.file_path}")
        self._print_duplicate_truncation(duplicate_violations)
    
    def _print_duplicate_truncation(self, duplicate_violations: List[Violation]) -> None:
        """Print duplicate truncation message if needed"""
        if len(duplicate_violations) > 10:
            print(f"\n  ... and {len(duplicate_violations)-10} more duplicate types")
    
    def _report_test_stub_violations(self, results: ComplianceResults) -> None:
        """Report test stub violations"""
        print("\n[TEST STUBS IN PRODUCTION]")
        print("-" * 40)
        test_stub_violations = self._get_violations_by_type(results, "test_stub")
        self._print_test_stub_violations(test_stub_violations)
    
    def _print_test_stub_violations(self, test_stub_violations: List[Violation]) -> None:
        """Print test stub violation details"""
        if test_stub_violations:
            self._print_test_stub_list(test_stub_violations)
            print(f"\n  Total suspicious files: {len(test_stub_violations)}")
        else:
            print("  [PASS] No test stubs found")
    
    def _print_test_stub_list(self, test_stub_violations: List[Violation]) -> None:
        """Print test stub violation list"""
        for violation in test_stub_violations[:10]:
            line_info = f" (line {violation.line_number})" if violation.line_number else ""
            print(f"  {violation.file_path}{line_info}: {violation.description}")
        self._print_stub_truncation(test_stub_violations)
    
    def _print_stub_truncation(self, test_stub_violations: List[Violation]) -> None:
        """Print stub truncation message if needed"""
        if len(test_stub_violations) > 10:
            print(f"  ... and {len(test_stub_violations)-10} more files")
    
    def _generate_final_summary(self, results: ComplianceResults) -> str:
        """Generate final compliance summary"""
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        actual_violations, total_warnings = self._count_violations(results)
        return self._determine_compliance_status(results, actual_violations, total_warnings)
    
    def _count_violations(self, results: ComplianceResults) -> Tuple[int, int]:
        """Count actual violations vs warnings"""
        actual_violations = len([v for v in results.violations if v.severity in ["high", "medium"]])
        total_warnings = len([v for v in results.violations if v.severity == "low"])
        return actual_violations, total_warnings
    
    def _determine_compliance_status(self, results: ComplianceResults, 
                                   actual_violations: int, total_warnings: int) -> str:
        """Determine final compliance status"""
        if actual_violations == 0:
            return self._handle_pass_status(total_warnings)
        else:
            return self._handle_fail_status(results, actual_violations, total_warnings)
    
    def _handle_pass_status(self, total_warnings: int) -> str:
        """Handle pass status with optional warnings"""
        if total_warnings > 0:
            print(f"[PASS WITH WARNINGS] No critical violations, but {total_warnings} warnings in example/demo files")
        else:
            print("[PASS] FULL COMPLIANCE - All architectural rules satisfied!")
        return "PASS"
    
    def _handle_fail_status(self, results: ComplianceResults, 
                          actual_violations: int, total_warnings: int) -> str:
        """Handle fail status with remediation actions"""
        self._print_fail_summary(results, actual_violations, total_warnings)
        self._print_required_actions(results)
        print("\nRefer to ALIGNMENT_ACTION_PLAN.md for remediation steps")
        return "FAIL"
    
    def _print_fail_summary(self, results: ComplianceResults, 
                          actual_violations: int, total_warnings: int) -> None:
        """Print failure summary details"""
        print(f"[FAIL] VIOLATIONS FOUND: {actual_violations} issues requiring fixes")
        if total_warnings > 0:
            print(f"       WARNINGS: {total_warnings} issues in example/demo files")
        print(f"Compliance Score: {results.compliance_score:.1f}%")
    
    def _print_required_actions(self, results: ComplianceResults) -> None:
        """Print required remediation actions"""
        print("\nRequired Actions:")
        violations_by_type = self._get_violation_counts_by_type(results)
        self._print_action_items(violations_by_type)
    
    def _print_action_items(self, violations_by_type: Dict[str, int]) -> None:
        """Print individual action items"""
        if violations_by_type["file_size"] > 0:
            print(f"  - Split {violations_by_type['file_size']} oversized files")
        if violations_by_type["function_errors"] > 0:
            print(f"  - Refactor {violations_by_type['function_errors']} complex functions")
        if violations_by_type["duplicate_types"] > 0:
            print(f"  - Deduplicate {violations_by_type['duplicate_types']} type definitions")
        if violations_by_type["test_stub"] > 0:
            print(f"  - Remove {violations_by_type['test_stub']} test stubs from production")
    
    def _get_violation_counts_by_type(self, results: ComplianceResults) -> Dict[str, int]:
        """Get violation counts by type"""
        file_violations = self._get_violations_by_type(results, "file_size")
        func_violations = self._get_violations_by_type(results, "function_complexity")
        func_errors = [v for v in func_violations if v.severity == "medium"]
        duplicate_violations = self._get_violations_by_type(results, "duplicate_types")
        test_stub_violations = self._get_violations_by_type(results, "test_stub")
        return {
            "file_size": len(file_violations),
            "function_errors": len(func_errors),
            "duplicate_types": len(duplicate_violations),
            "test_stub": len(test_stub_violations)
        }