#!/usr/bin/env python3
"""
Test Violations Reporter - Focus specifically on test file and function violations
Generates detailed reports with splitting suggestions for test limit violations.
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add the compliance directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from core import ComplianceConfig, Violation
from test_limits_checker import TestLimitsChecker


class TestViolationsReporter:
    """Reports specifically on test file and function violations"""
    
    def __init__(self, root_path: str = "."):
        self.config = ComplianceConfig(root_path)
        self.checker = TestLimitsChecker(self.config)
    
    def generate_report(self) -> None:
        """Generate comprehensive test violations report"""
        violations = self.checker.check_test_limits()
        suggestions = self.checker.generate_splitting_suggestions(violations)
        
        # Separate file and function violations
        file_violations = [v for v in violations if v.violation_type == "test_file_size"]
        function_violations = [v for v in violations if v.violation_type == "test_function_complexity"]
        
        print("=" * 80)
        print("TEST LIMITS VIOLATIONS REPORT")
        print("=" * 80)
        
        self._print_summary(file_violations, function_violations)
        self._print_file_violations(file_violations)
        self._print_function_violations(function_violations)
        self._print_splitting_suggestions(suggestions)
        
        print("\n" + "=" * 80)
        print("COMPLIANCE ANALYSIS")
        print("=" * 80)
        
        total_test_files = self._count_total_test_files()
        compliant_files = total_test_files - len(set(v.file_path for v in violations))
        compliance_rate = (compliant_files / total_test_files * 100) if total_test_files > 0 else 100
        
        print(f"Total Test Files: {total_test_files}")
        print(f"Files with Violations: {len(set(v.file_path for v in violations))}")
        print(f"Compliant Files: {compliant_files}")
        print(f"Compliance Rate: {compliance_rate:.1f}%")
        print("\nRECOMMENDATION:")
        if compliance_rate < 50:
            print("[CRITICAL] Majority of test files violate limits. Consider systematic refactoring.")
        elif compliance_rate < 80:
            print("[WARNING] Significant test limit violations. Prioritize cleanup.")
        else:
            print("[GOOD] Most test files comply. Address remaining violations.")
    
    def _print_summary(self, file_violations: List[Violation], function_violations: List[Violation]) -> None:
        """Print summary statistics"""
        print(f"\nSUMMARY:")
        print(f"Test File Size Violations (>300 lines): {len(file_violations)}")
        print(f"Test Function Violations (>8 lines): {len(function_violations)}")
        print(f"Total Test Violations: {len(file_violations) + len(function_violations)}")
    
    def _print_file_violations(self, violations: List[Violation]) -> None:
        """Print test file size violations"""
        if not violations:
            print("\nNo test file size violations found!")
            return
        
        print(f"\nTEST FILE SIZE VIOLATIONS ({len(violations)} files)")
        print("-" * 60)
        
        # Sort by size descending
        sorted_violations = sorted(violations, key=lambda x: x.actual_value, reverse=True)
        
        for i, violation in enumerate(sorted_violations[:15], 1):  # Show top 15
            excess = violation.actual_value - violation.expected_value
            print(f"{i:2d}. {violation.actual_value:4d} lines (+{excess:3d}) {violation.file_path}")
        
        if len(sorted_violations) > 15:
            print(f"    ... and {len(sorted_violations) - 15} more files")
    
    def _print_function_violations(self, violations: List[Violation]) -> None:
        """Print test function violations"""
        if not violations:
            print("\nNo test function violations found!")
            return
        
        print(f"\nTEST FUNCTION VIOLATIONS ({len(violations)} functions)")
        print("-" * 60)
        
        # Group by file for better organization
        by_file = {}
        for violation in violations:
            if violation.file_path not in by_file:
                by_file[violation.file_path] = []
            by_file[violation.file_path].append(violation)
        
        # Show files with most violations first
        sorted_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)
        
        shown_files = 0
        shown_functions = 0
        max_files = 10
        max_functions_per_file = 5
        
        for file_path, file_violations in sorted_files:
            if shown_files >= max_files:
                break
            
            print(f"\n{file_path} ({len(file_violations)} violations)")
            
            # Sort functions by line count descending
            sorted_funcs = sorted(file_violations, key=lambda x: x.actual_value, reverse=True)
            
            for violation in sorted_funcs[:max_functions_per_file]:
                excess = violation.actual_value - violation.expected_value
                print(f"    {violation.function_name}() - {violation.actual_value} lines (+{excess})")
                shown_functions += 1
            
            if len(sorted_funcs) > max_functions_per_file:
                print(f"    ... and {len(sorted_funcs) - max_functions_per_file} more functions")
            
            shown_files += 1
        
        if len(sorted_files) > max_files:
            remaining_files = len(sorted_files) - max_files
            remaining_violations = sum(len(violations) for _, violations in sorted_files[max_files:])
            print(f"\n    ... and {remaining_violations} more violations in {remaining_files} more files")
    
    def _print_splitting_suggestions(self, suggestions: Dict[str, List[str]]) -> None:
        """Print automated splitting suggestions"""
        if not suggestions:
            print("\nNo splitting suggestions needed!")
            return
        
        print(f"\nAUTOMATED SPLITTING SUGGESTIONS ({len(suggestions)} items)")
        print("=" * 60)
        
        # Show top suggestions
        for i, (identifier, suggestion_list) in enumerate(suggestions.items(), 1):
            if i > 8:  # Limit to top 8 suggestions
                print(f"\n... and {len(suggestions) - 8} more suggestions")
                break
            
            print(f"\n{i}. {identifier}")
            print("-" * 40)
            for suggestion in suggestion_list:
                print(f"   {suggestion}")
    
    def _count_total_test_files(self) -> int:
        """Count total test files in the project"""
        test_files = self.checker._find_test_files()
        return len(test_files)


def main():
    """Main entry point for test violations reporter"""
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."
    
    reporter = TestViolationsReporter(root_path)
    reporter.generate_report()


if __name__ == "__main__":
    main()