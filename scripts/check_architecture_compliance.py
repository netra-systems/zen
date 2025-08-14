#!/usr/bin/env python3
"""
Architecture Compliance Checker
Enforces CLAUDE.md architectural rules:
- 300-line file limit
- 8-line function limit  
- No duplicate types
- No test stubs in production

Enhanced with JSON output, CI/CD integration, and configurable thresholds.
"""

import ast
import glob
import json
import os
import sys
import time
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional, Union
from pathlib import Path

@dataclass
class Violation:
    """Structured violation data"""
    file_path: str
    violation_type: str
    severity: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    actual_value: Optional[int] = None
    expected_value: Optional[int] = None
    description: str = ""
    fix_suggestion: str = ""


@dataclass
class ComplianceResults:
    """Complete compliance results"""
    total_violations: int
    compliance_score: float
    timestamp: str
    violations_by_type: Dict[str, int]
    violations: List[Violation]
    summary: Dict[str, Union[int, str, float]]


class ArchitectureEnforcer:
    """Enforces architectural rules from CLAUDE.md"""
    
    def __init__(self, 
                 root_path: str = ".",
                 max_file_lines: int = 300,
                 max_function_lines: int = 8):
        self.root_path = Path(root_path)
        self.max_file_lines = max_file_lines
        self.max_function_lines = max_function_lines
        self.violations: List[Violation] = []
        
    def check_file_size(self) -> List[Violation]:
        """Check for files exceeding line limit"""
        violations = []
        patterns = ['app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 'scripts/**/*.py']
        
        for pattern in patterns:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if self._should_skip(filepath):
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        if lines > self.max_file_lines:
                            rel_path = str(Path(filepath).relative_to(self.root_path))
                            violations.append(Violation(
                                file_path=rel_path,
                                violation_type="file_size",
                                severity="high",
                                actual_value=lines,
                                expected_value=self.max_file_lines,
                                description=f"File exceeds {self.max_file_lines} line limit",
                                fix_suggestion=f"Split into {(lines // self.max_file_lines) + 1} modules"
                            ))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    
        return sorted(violations, key=lambda x: x.actual_value or 0, reverse=True)
    
    def check_function_complexity(self) -> List[Violation]:
        """Check for functions exceeding line limit"""
        violations = []
        patterns = ['app/**/*.py', 'scripts/**/*.py']
        
        for pattern in patterns:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if self._should_skip(filepath):
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                        
                    rel_path = str(Path(filepath).relative_to(self.root_path))
                    
                    # Check if this is an example/demo file
                    is_example_file = any(x in rel_path.lower() for x in [
                        'example', 'demo', 'sample', 'test_', 'mock', 
                        'example_usage', 'corpus_metrics', 'audit/example'
                    ])
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            lines = self._count_function_lines(node)
                            if lines > self.max_function_lines:
                                # Use lower severity for example files
                                severity = "low" if is_example_file else "medium"
                                description_prefix = "[WARNING]" if is_example_file else "[VIOLATION]"
                                
                                violations.append(Violation(
                                    file_path=rel_path,
                                    violation_type="function_complexity",
                                    severity=severity,
                                    line_number=node.lineno,
                                    function_name=node.name,
                                    actual_value=lines,
                                    expected_value=self.max_function_lines,
                                    description=f"{description_prefix} Function '{node.name}' has {lines} lines (max: {self.max_function_lines})",
                                    fix_suggestion=f"{'Consider splitting' if is_example_file else 'Split'} into {(lines // self.max_function_lines) + 1} smaller functions"
                                ))
                except Exception as e:
                    print(f"Error parsing {filepath}: {e}")
                    
        return sorted(violations, key=lambda x: x.actual_value or 0, reverse=True)
    
    def check_duplicate_types(self) -> List[Violation]:
        """Find duplicate type definitions"""
        type_definitions = defaultdict(list)
        violations = []
        
        # Check Python files
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip(filepath):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    rel_path = str(Path(filepath).relative_to(self.root_path))
                    for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                        type_name = match.group(1)
                        type_definitions[type_name].append(rel_path)
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
        
        # Check TypeScript files
        for pattern in ['frontend/**/*.ts', 'frontend/**/*.tsx']:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if 'node_modules' in filepath:
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        rel_path = str(Path(filepath).relative_to(self.root_path))
                        for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
                            type_name = match.group(1)
                            type_definitions[type_name].append(rel_path)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
        
        # Create violations for duplicates
        for type_name, files in type_definitions.items():
            if len(files) > 1:
                violations.append(Violation(
                    file_path=", ".join(files[:3]) + ("..." if len(files) > 3 else ""),
                    violation_type="duplicate_types",
                    severity="medium",
                    actual_value=len(files),
                    expected_value=1,
                    description=f"Type '{type_name}' defined in {len(files)} files",
                    fix_suggestion=f"Consolidate '{type_name}' into single source of truth"
                ))
        
        return violations
    
    def check_test_stubs(self) -> List[Violation]:
        """Check for test stubs in production code"""
        suspicious_patterns = [
            (r'# Mock implementation', 'Mock implementation comment'),
            (r'# Test stub', 'Test stub comment'),
            (r'# TODO.*implement', 'TODO implementation comment'),
            (r'""".*test implementation.*"""', 'Test implementation docstring'),
            (r'""".*for testing.*"""', 'For testing docstring'),
            (r'""".*placeholder.*"""', 'Placeholder docstring'),
            (r'return \[{"id": "1"', 'Hardcoded test data'),
            (r'return {"test": "data"}', 'Test data return'),
            (r'return {"status": "ok"}', 'Static status return'),
            (r'def \w+\(\*args, \*\*kwargs\).*return {', 'Args/kwargs with static return'),
            (r'raise NotImplementedError', 'Not implemented error'),
        ]
        
        violations = []
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if '__pycache__' in filepath or 'app/tests' in filepath or '/tests/' in filepath:
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    rel_path = str(Path(filepath).relative_to(self.root_path))
                    for pattern, description in suspicious_patterns:
                        matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
                        for match in matches:
                            line_number = content[:match.start()].count('\n') + 1
                            violations.append(Violation(
                                file_path=rel_path,
                                violation_type="test_stub",
                                severity="high",
                                line_number=line_number,
                                description=f"Test stub detected: {description}",
                                fix_suggestion="Replace with production implementation"
                            ))
                            break  # Only report first match per file
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                
        return violations
    
    def _should_skip(self, filepath: str) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '__pycache__',
            'node_modules',
            '.git',
            'migrations',
            'test_reports',
            'docs',
            '.pytest_cache'
        ]
        return any(pattern in filepath for pattern in skip_patterns)
    
    def _count_function_lines(self, node) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        
        # Skip docstring if present
        start_idx = 0
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Constant, ast.Str))):
            start_idx = 1
        
        if start_idx >= len(node.body):
            return 0
            
        # Count lines from first real statement to last
        first_line = node.body[start_idx].lineno
        last_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else node.body[-1].lineno
        return last_line - first_line + 1
    
    def run_all_checks(self) -> ComplianceResults:
        """Run all compliance checks and return structured results"""
        all_violations = []
        
        # Run all checks
        all_violations.extend(self.check_file_size())
        all_violations.extend(self.check_function_complexity())
        all_violations.extend(self.check_duplicate_types())
        all_violations.extend(self.check_test_stubs())
        
        # Calculate summary statistics
        violations_by_type = defaultdict(int)
        for violation in all_violations:
            violations_by_type[violation.violation_type] += 1
        
        total_violations = len(all_violations)
        
        # Calculate compliance score (rough estimate)
        patterns = ['app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 'scripts/**/*.py']
        total_files = 0
        for pattern in patterns:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if not self._should_skip(filepath):
                    total_files += 1
        
        compliance_score = max(0, (total_files - len(set(v.file_path for v in all_violations))) / total_files * 100) if total_files > 0 else 100
        
        return ComplianceResults(
            total_violations=total_violations,
            compliance_score=compliance_score,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            violations_by_type=dict(violations_by_type),
            violations=all_violations,
            summary={
                "total_files_checked": total_files,
                "files_with_violations": len(set(v.file_path for v in all_violations)),
                "max_file_lines": self.max_file_lines,
                "max_function_lines": self.max_function_lines,
                "compliance_score": compliance_score
            }
        )
    
    def generate_report(self) -> str:
        """Generate compliance report"""
        print("\n" + "="*80)
        print("ARCHITECTURE COMPLIANCE REPORT")
        print("="*80)
        
        # Get results using new structured approach
        results = self.run_all_checks()
        
        # File size violations
        print(f"\n[FILE SIZE VIOLATIONS] (>{self.max_file_lines} lines)")
        print("-" * 40)
        file_violations = [v for v in results.violations if v.violation_type == "file_size"]
        if file_violations:
            for violation in file_violations[:10]:
                print(f"  {violation.actual_value:4d} lines: {violation.file_path}")
            if len(file_violations) > 10:
                print(f"  ... and {len(file_violations)-10} more files")
            print(f"\n  Total violations: {len(file_violations)}")
        else:
            print("  [PASS] No violations found")
        
        # Function complexity violations
        print(f"\n[FUNCTION COMPLEXITY VIOLATIONS] (>{self.max_function_lines} lines)")
        print("-" * 40)
        func_violations = [v for v in results.violations if v.violation_type == "function_complexity"]
        
        # Separate violations and warnings based on severity
        func_errors = [v for v in func_violations if v.severity == "medium"]
        func_warnings = [v for v in func_violations if v.severity == "low"]
        
        if func_errors:
            print("  VIOLATIONS (must fix):")
            for violation in func_errors[:5]:
                print(f"    {violation.actual_value:3d} lines: {violation.function_name}() in {violation.file_path}")
            if len(func_errors) > 5:
                print(f"    ... and {len(func_errors)-5} more violations")
        
        if func_warnings:
            print("\n  WARNINGS (example/demo files):")
            for violation in func_warnings[:5]:
                print(f"    {violation.actual_value:3d} lines: {violation.function_name}() in {violation.file_path}")
            if len(func_warnings) > 5:
                print(f"    ... and {len(func_warnings)-5} more warnings")
        
        if func_violations:
            print(f"\n  Total: {len(func_errors)} violations, {len(func_warnings)} warnings")
        else:
            print("  [PASS] No violations found")
        
        # Duplicate types
        print("\n[DUPLICATE TYPE DEFINITIONS]")
        print("-" * 40)
        duplicate_violations = [v for v in results.violations if v.violation_type == "duplicate_types"]
        if duplicate_violations:
            for violation in duplicate_violations[:10]:
                print(f"  {violation.description}")
                print(f"    Files: {violation.file_path}")
            if len(duplicate_violations) > 10:
                print(f"\n  ... and {len(duplicate_violations)-10} more duplicate types")
            print(f"\n  Total duplicate types: {len(duplicate_violations)}")
        else:
            print("  [PASS] No duplicates found")
        
        # Test stubs
        print("\n[TEST STUBS IN PRODUCTION]")
        print("-" * 40)
        test_stub_violations = [v for v in results.violations if v.violation_type == "test_stub"]
        if test_stub_violations:
            for violation in test_stub_violations[:10]:
                line_info = f" (line {violation.line_number})" if violation.line_number else ""
                print(f"  {violation.file_path}{line_info}: {violation.description}")
            if len(test_stub_violations) > 10:
                print(f"  ... and {len(test_stub_violations)-10} more files")
            print(f"\n  Total suspicious files: {len(test_stub_violations)}")
        else:
            print("  [PASS] No test stubs found")
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        # Count only actual violations (not warnings)
        actual_violations = len([v for v in results.violations if v.severity in ["high", "medium"]])
        total_warnings = len([v for v in results.violations if v.severity == "low"])
        
        if actual_violations == 0:
            if total_warnings > 0:
                print(f"[PASS WITH WARNINGS] No critical violations, but {total_warnings} warnings in example/demo files")
            else:
                print("[PASS] FULL COMPLIANCE - All architectural rules satisfied!")
            return "PASS"
        else:
            print(f"[FAIL] VIOLATIONS FOUND: {actual_violations} issues requiring fixes")
            if total_warnings > 0:
                print(f"       WARNINGS: {total_warnings} issues in example/demo files")
            print(f"Compliance Score: {results.compliance_score:.1f}%")
            print("\nRequired Actions:")
            if file_violations:
                print(f"  - Split {len(file_violations)} oversized files")
            if func_errors:
                print(f"  - Refactor {len(func_errors)} complex functions")
            if duplicate_violations:
                print(f"  - Deduplicate {len(duplicate_violations)} type definitions")
            if test_stub_violations:
                print(f"  - Remove {len(test_stub_violations)} test stubs from production")
            
            print("\nRefer to ALIGNMENT_ACTION_PLAN.md for remediation steps")
            return "FAIL"

def main():
    """Main entry point with enhanced CI/CD features"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Check architecture compliance with enhanced CI/CD features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python check_architecture_compliance.py --json-output report.json
  python check_architecture_compliance.py --max-file-lines 250 --threshold 90
  python check_architecture_compliance.py --fail-on-violation --json-only
        """)
    
    parser.add_argument('--path', default='.', help='Root path to check')
    parser.add_argument('--fail-on-violation', action='store_true', 
                       help='Exit with non-zero code on violations')
    parser.add_argument('--max-file-lines', type=int, default=300,
                       help='Maximum lines per file (default: 300)')
    parser.add_argument('--max-function-lines', type=int, default=8,
                       help='Maximum lines per function (default: 8)')
    parser.add_argument('--json-output', help='Output JSON report to file')
    parser.add_argument('--json-only', action='store_true',
                       help='Output only JSON, no human-readable report')
    parser.add_argument('--threshold', type=float, default=0.0,
                       help='Minimum compliance score (0-100) to pass')
    
    args = parser.parse_args()
    
    enforcer = ArchitectureEnforcer(
        root_path=args.path,
        max_file_lines=args.max_file_lines,
        max_function_lines=args.max_function_lines
    )
    
    # Get structured results
    results = enforcer.run_all_checks()
    
    # Output results
    if args.json_only:
        print(json.dumps(asdict(results), indent=2))
    else:
        result_status = enforcer.generate_report()
    
    # Save JSON output if requested
    if args.json_output:
        with open(args.json_output, 'w') as f:
            json.dump(asdict(results), f, indent=2)
        print(f"\nJSON report saved to: {args.json_output}")
    
    # Exit with appropriate code for CI/CD
    if args.fail_on_violation and (
        results.total_violations > 0 or 
        results.compliance_score < args.threshold
    ):
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()