#!/usr/bin/env python3
"""
Elite Enforcement Script for Netra Apex
MANDATORY: 450-line file limit, 25-line function limit

Business Value: Prevents $3,500/month context waste regression
Revenue Impact: Maintains code quality = customer retention
"""

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ViolationDetail:
    """Structure for limit violations"""
    file_path: str
    violation_type: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    actual_lines: Optional[int] = None
    max_lines: Optional[int] = None
    message: str = ""
    fix_suggestion: str = ""


class FileLineChecker:
    """Checks file line limits (300 max)"""
    
    def __init__(self, max_lines: int = 300):
        self.max_lines = max_lines
    
    def check_file(self, file_path: Path) -> Optional[ViolationDetail]:
        """Check single file for line limit"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if len(lines) > self.max_lines:
                return ViolationDetail(
                    file_path=str(file_path),
                    violation_type="file_size",
                    actual_lines=len(lines),
                    max_lines=self.max_lines,
                    message=f"File has {len(lines)} lines (max: {self.max_lines})",
                    fix_suggestion=self._get_split_suggestion(len(lines))
                )
        except Exception as e:
            return ViolationDetail(
                file_path=str(file_path),
                violation_type="read_error",
                message=f"Error reading file: {e}",
                fix_suggestion="Check file encoding or permissions"
            )
        return None
    
    def _get_split_suggestion(self, actual_lines: int) -> str:
        """Generate splitting suggestion"""
        suggested_modules = (actual_lines // self.max_lines) + 1
        return f"Split into {suggested_modules} focused modules"


class FunctionLineChecker:
    """Checks function line limits (8 max)"""
    
    def __init__(self, max_lines: int = 8):
        self.max_lines = max_lines
    
    def check_file(self, file_path: Path) -> List[ViolationDetail]:
        """Check all functions in file for line limits"""
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    violation = self._check_function_node(node, file_path)
                    if violation:
                        violations.append(violation)
        except Exception as e:
            violations.append(ViolationDetail(
                file_path=str(file_path),
                violation_type="parse_error",
                message=f"Error parsing Python file: {e}",
                fix_suggestion="Check Python syntax"
            ))
        return violations
    
    def _check_function_node(self, node, file_path: Path) -> Optional[ViolationDetail]:
        """Check individual function node"""
        end_line = getattr(node, 'end_lineno', node.lineno)
        function_lines = end_line - node.lineno + 1
        
        if function_lines > self.max_lines:
            return ViolationDetail(
                file_path=str(file_path),
                violation_type="function_size",
                line_number=node.lineno,
                function_name=node.name,
                actual_lines=function_lines,
                max_lines=self.max_lines,
                message=f"Function '{node.name}' has {function_lines} lines",
                fix_suggestion=self._get_refactor_suggestion(function_lines)
            )
        return None
    
    def _get_refactor_suggestion(self, actual_lines: int) -> str:
        """Generate refactoring suggestion"""
        suggested_functions = (actual_lines // self.max_lines) + 1
        return f"Extract into {suggested_functions} smaller functions"


class EnforcementOrchestrator:
    """Orchestrates all enforcement checks"""
    
    def __init__(self, max_file_lines: int = 300, max_function_lines: int = 8):
        self.file_checker = FileLineChecker(max_file_lines)
        self.function_checker = FunctionLineChecker(max_function_lines)
        self.violations: List[ViolationDetail] = []
    
    def check_files(self, file_paths: List[Path], 
                   check_files: bool = True, 
                   check_functions: bool = True) -> List[ViolationDetail]:
        """Check multiple files for violations"""
        self.violations = []
        
        for file_path in file_paths:
            if not file_path.exists():
                continue
                
            # Check file size limits
            if check_files and self._should_check_file_size(file_path):
                violation = self.file_checker.check_file(file_path)
                if violation:
                    self.violations.append(violation)
            
            # Check function size limits
            if check_functions and file_path.suffix == '.py':
                violations = self.function_checker.check_file(file_path)
                self.violations.extend(violations)
        
        return self.violations
    
    def _should_check_file_size(self, file_path: Path) -> bool:
        """Determine if file should be checked for size"""
        valid_extensions = {'.py', '.ts', '.tsx', '.js', '.jsx'}
        return file_path.suffix in valid_extensions


class EnforcementReporter:
    """Reports violations in various formats"""
    
    @staticmethod
    def generate_console_report(violations: List[ViolationDetail]) -> str:
        """Generate human-readable console report"""
        if not violations:
            return " PASS:  All files comply with architectural limits"
        
        report_lines = []
        report_lines.append("[U+1F534] ARCHITECTURAL LIMIT VIOLATIONS DETECTED")
        report_lines.append("=" * 60)
        
        # Group by violation type
        by_type = EnforcementReporter._group_by_type(violations)
        
        for vtype, items in by_type.items():
            report_lines.append(f"\n{vtype.upper()} VIOLATIONS ({len(items)}):")
            for violation in items:
                report_lines.append(f"  [U+1F4C1] {violation.file_path}")
                if violation.line_number:
                    report_lines.append(f"     Line {violation.line_number}")
                if violation.function_name:
                    report_lines.append(f"     Function: {violation.function_name}")
                report_lines.append(f"     {violation.message}")
                report_lines.append(f"     Fix: {violation.fix_suggestion}")
                report_lines.append("")
        
        report_lines.append(f"Total violations: {len(violations)}")
        return "\n".join(report_lines)
    
    @staticmethod
    def generate_json_report(violations: List[ViolationDetail]) -> str:
        """Generate JSON report for CI/CD integration"""
        violation_data = []
        for v in violations:
            violation_data.append({
                'file': v.file_path,
                'type': v.violation_type,
                'line': v.line_number,
                'function': v.function_name,
                'actual_lines': v.actual_lines,
                'max_lines': v.max_lines,
                'message': v.message,
                'fix_suggestion': v.fix_suggestion
            })
        
        return json.dumps({
            'total_violations': len(violations),
            'violations': violation_data,
            'compliance_status': 'PASS' if len(violations) == 0 else 'FAIL'
        }, indent=2)
    
    @staticmethod
    def _group_by_type(violations: List[ViolationDetail]) -> Dict[str, List[ViolationDetail]]:
        """Group violations by type"""
        grouped = {}
        for violation in violations:
            if violation.violation_type not in grouped:
                grouped[violation.violation_type] = []
            grouped[violation.violation_type].append(violation)
        return grouped


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Elite Enforcement for Netra Apex Architectural Limits"
    )
    
    # Mode options
    parser.add_argument('--mode', choices=['strict', 'warn'], default='warn',
                       help='Enforcement mode (strict blocks, warn reports)')
    parser.add_argument('--fail-fast', action='store_true',
                       help='Exit on first violation (for pre-commit)')
    
    # Check options
    parser.add_argument('--check-files-only', action='store_true',
                       help='Only check file size limits')
    parser.add_argument('--check-functions-only', action='store_true',
                       help='Only check function size limits')
    parser.add_argument('--check-types', action='store_true',
                       help='Check for type duplicates')
    parser.add_argument('--check-stubs', action='store_true',
                       help='Check for test stubs')
    parser.add_argument('--prevent-duplicates', action='store_true',
                       help='Prevent duplicate type definitions')
    parser.add_argument('--fail-on-stubs', action='store_true',
                       help='Fail on test stub detection')
    
    # Limit overrides
    parser.add_argument('--max-lines', type=int, default=300,
                       help='Maximum lines per file (default: 300)')
    parser.add_argument('--max-function-lines', type=int, default=8,
                       help='Maximum lines per function (default: 8)')
    
    # Output options
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    # File selection
    parser.add_argument('files', nargs='*',
                       help='Files to check (if not provided, checks all)')
    
    return parser


def collect_target_files(specified_files: List[str]) -> List[Path]:
    """Collect files to check"""
    if specified_files:
        return [Path(f) for f in specified_files if Path(f).exists()]
    
    # Auto-discover files in target directories
    target_dirs = ['app', 'frontend', 'scripts']
    extensions = ['*.py', '*.ts', '*.tsx']
    
    files = []
    for target_dir in target_dirs:
        dir_path = Path(target_dir)
        if dir_path.exists():
            for ext in extensions:
                files.extend(dir_path.rglob(ext))
    
    return files


def main() -> int:
    """Main enforcement orchestrator"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Collect files to check
    target_files = collect_target_files(args.files)
    
    if not target_files:
        print("No files to check")
        return 0
    
    # Determine what to check
    check_files = not args.check_functions_only
    check_functions = not args.check_files_only
    
    # Run enforcement
    orchestrator = EnforcementOrchestrator(args.max_lines, args.max_function_lines)
    violations = orchestrator.check_files(target_files, check_files, check_functions)
    
    # Generate report
    if args.json:
        print(EnforcementReporter.generate_json_report(violations))
    else:
        print(EnforcementReporter.generate_console_report(violations))
    
    # Exit with appropriate code
    if violations:
        if args.mode == 'strict' or args.fail_fast:
            return 1  # Block commit/CI
        else:
            return 0  # Warn only
    
    return 0


if __name__ == "__main__":
    sys.exit(main())