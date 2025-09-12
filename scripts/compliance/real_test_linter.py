#!/usr/bin/env python3
"""Real Test Requirements Linter

Integrates into development workflow to enforce real test requirements.
Can be used as pre-commit hook, CI check, or standalone validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity, Risk Reduction
- Value Impact: Prevents test anti-patterns from entering codebase
- Strategic Impact: Maintains test reliability and system integrity

Usage:
  python scripts/compliance/real_test_linter.py [--fix] [--strict] [file1 file2 ...]
  
Options:
  --fix     Attempt to automatically fix violations
  --strict  Fail on any violations (for CI)
  --files   Specific files to check (default: all project test files)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set

# Import our existing validators
from project_test_validator import ProjectTestValidator, TestViolation
from test_fixer import TestFixer


class RealTestLinter:
    """Main linter class integrating validation and fixing"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.validator = ProjectTestValidator(root_path)
        self.fixer = TestFixer(root_path)
        
    def lint_files(self, file_paths: Optional[List[str]] = None,
                  fix: bool = False, strict: bool = False) -> int:
        """Lint specified files or all test files"""
        
        if file_paths:
            # Validate specific files
            violations = self._validate_specific_files(file_paths)
        else:
            # Validate all project test files
            violations = self.validator.validate_project_tests()
        
        # Filter out minor violations if not in strict mode
        if not strict:
            violations = [v for v in violations if v.severity != "minor"]
        
        # Print results
        self._print_results(violations, fix)
        
        # Attempt fixes if requested
        if fix and violations:
            fixed_count = self._attempt_fixes(violations)
            print(f"\nFixed {fixed_count} violations automatically.")
            
            # Re-validate after fixes
            if file_paths:
                remaining_violations = self._validate_specific_files(file_paths)
            else:
                remaining_violations = self.validator.validate_project_tests()
                
            remaining_violations = [v for v in remaining_violations if v.severity != "minor"]
            
            if remaining_violations:
                print(f"\n{len(remaining_violations)} violations remain after auto-fix:")
                self._print_results(remaining_violations, False)
        
        # Return exit code
        critical_violations = [v for v in violations if v.severity == "critical"]
        if strict and violations:
            return len(violations)  # Fail on any violations in strict mode
        else:
            return len(critical_violations)  # Only fail on critical violations normally
    
    def _validate_specific_files(self, file_paths: List[str]) -> List[TestViolation]:
        """Validate only the specified files"""
        violations = []
        
        for file_path in file_paths:
            path = Path(file_path)
            if path.exists() and self.validator._is_test_file(path):
                # Temporarily set up validator for single file
                original_violations = self.validator.violations
                self.validator.violations = []
                
                self.validator._validate_file(path)
                violations.extend(self.validator.violations)
                
                self.validator.violations = original_violations
        
        return violations
    
    def _print_results(self, violations: List[TestViolation], show_fix_suggestions: bool):
        """Print validation results"""
        if not violations:
            print(" PASS:  All test files comply with real test requirements!")
            return
        
        # Group by severity
        by_severity = {"critical": [], "major": [], "minor": []}
        for v in violations:
            by_severity[v.severity].append(v)
        
        critical_count = len(by_severity["critical"])
        major_count = len(by_severity["major"])
        minor_count = len(by_severity["minor"])
        
        print(f"\n FAIL:  Found {len(violations)} test requirement violations:")
        if critical_count > 0:
            print(f"   [U+1F534] {critical_count} CRITICAL (must fix)")
        if major_count > 0:
            print(f"   [U+1F7E1] {major_count} MAJOR (should fix)")
        if minor_count > 0:
            print(f"   [U+1F7E2] {minor_count} MINOR (nice to fix)")
        
        # Show top violations by type
        by_type = {}
        for v in violations:
            if v.violation_type not in by_type:
                by_type[v.violation_type] = []
            by_type[v.violation_type].append(v)
        
        print(f"\nTop violations by type:")
        for violation_type, type_violations in sorted(by_type.items(), 
                                                     key=lambda x: len(x[1]), 
                                                     reverse=True)[:5]:
            type_name = violation_type.replace('_', ' ').title()
            print(f"  {type_name}: {len(type_violations)} files")
            
            # Show examples
            for v in type_violations[:3]:
                severity_icon = {"critical": "[U+1F534]", "major": "[U+1F7E1]", "minor": "[U+1F7E2]"}[v.severity]
                print(f"    {severity_icon} {v.file_path}:{v.line_number}")
        
        if show_fix_suggestions:
            print(f"\n IDEA:  Suggested fixes:")
            print(f"  [U+2022] Run with --fix to attempt automatic fixes")
            print(f"  [U+2022] For file_size violations: Split large test files into focused modules")
            print(f"  [U+2022] For function_size violations: Extract helper methods")
            print(f"  [U+2022] For excessive_mocking violations: Use real components where possible")
            print(f"  [U+2022] For mock_component violations: Replace with real component instantiation")
    
    def _attempt_fixes(self, violations: List[TestViolation]) -> int:
        """Attempt to automatically fix violations"""
        fixed_count = 0
        
        for violation in violations:
            try:
                if violation.violation_type == "mock_component_function":
                    if self.fixer.fix_mock_component_function(violation.file_path, 
                                                            violation.line_number):
                        fixed_count += 1
                        print(f"[U+2713] Fixed mock component function in {violation.file_path}")
                
                elif violation.violation_type == "excessive_mocking":
                    if self.fixer.reduce_mocking_in_integration_test(violation.file_path):
                        fixed_count += 1
                        print(f"[U+2713] Reduced mocking in {violation.file_path}")
                
                # File size and function size violations require manual intervention
                # but we can provide specific guidance
                elif violation.violation_type == "file_size":
                    print(f" WARNING:  Manual fix needed: Split {violation.file_path} (too large)")
                
                elif violation.violation_type == "function_size":
                    print(f" WARNING:  Manual fix needed: Extract helpers in {violation.file_path}:{violation.line_number}")
            
            except Exception as e:
                print(f" FAIL:  Failed to fix {violation.violation_type} in {violation.file_path}: {e}")
        
        return fixed_count
    
    def generate_fix_report(self) -> str:
        """Generate comprehensive fix report for manual intervention"""
        violations = self.validator.validate_project_tests()
        
        if not violations:
            return "All tests comply with requirements!"
        
        fix_plan = self.fixer.generate_fix_plan(violations)
        
        report = ["# Real Test Requirements Fix Plan", ""]
        
        if fix_plan["immediate_fixes"]:
            report.extend(["## Immediate Fixes (Can be automated)", ""])
            for fix in fix_plan["immediate_fixes"]:
                report.append(f"- [ ] {fix}")
            report.append("")
        
        if fix_plan["file_splits"]:
            report.extend(["## File Splits Required", ""])
            report.append("These files exceed 450-line limit and should be split:")
            for split in fix_plan["file_splits"]:
                report.append(f"- [ ] {split}")
            report.append("")
        
        if fix_plan["function_refactors"]:
            report.extend(["## Function Refactoring Required", ""])
            report.append("These functions exceed 25-line limit and need helper extraction:")
            for refactor in fix_plan["function_refactors"][:20]:  # Show top 20
                report.append(f"- [ ] {refactor}")
            if len(fix_plan["function_refactors"]) > 20:
                report.append(f"... and {len(fix_plan['function_refactors']) - 20} more")
            report.append("")
        
        if fix_plan["mock_reductions"]:
            report.extend(["## Mock Reduction Required", ""])
            report.append("These integration tests use excessive mocking:")
            for reduction in fix_plan["mock_reductions"]:
                report.append(f"- [ ] {reduction}")
            report.append("")
        
        return '\n'.join(report)
    
    def check_git_diff(self) -> int:
        """Check only files changed in current git diff"""
        try:
            # Get changed files from git
            result = subprocess.run(['git', 'diff', '--name-only', 'HEAD'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print("Not in a git repository or git not available")
                return 1
            
            changed_files = result.stdout.strip().split('\n')
            test_files = [f for f in changed_files 
                         if f.endswith('.py') and ('test_' in f or '_test' in f)]
            
            if not test_files:
                print("No test files changed")
                return 0
            
            print(f"Checking {len(test_files)} changed test files...")
            return self.lint_files(test_files, fix=False, strict=True)
            
        except Exception as e:
            print(f"Error checking git diff: {e}")
            return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Lint test files for real test requirements compliance"
    )
    parser.add_argument('--fix', action='store_true', 
                       help='Attempt to automatically fix violations')
    parser.add_argument('--strict', action='store_true',
                       help='Fail on any violations (for CI)')
    parser.add_argument('--git-diff', action='store_true',
                       help='Only check files changed in git diff')
    parser.add_argument('--report', action='store_true',
                       help='Generate comprehensive fix report')
    parser.add_argument('files', nargs='*',
                       help='Specific files to check (default: all test files)')
    
    args = parser.parse_args()
    
    linter = RealTestLinter()
    
    if args.report:
        print(linter.generate_fix_report())
        return 0
    
    if args.git_diff:
        return linter.check_git_diff()
    
    return linter.lint_files(
        file_paths=args.files if args.files else None,
        fix=args.fix,
        strict=args.strict
    )


if __name__ == "__main__":
    sys.exit(main())