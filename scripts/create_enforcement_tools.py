#!/usr/bin/env python3
"""
Comprehensive Enforcement Tools for Netra Codebase
Creates production-ready tools that enforce CLAUDE.md architectural rules:
- 450-line file limit
- 25-line function limit
- No test stubs in production code
- No duplicate type definitions

These tools are designed for CI/CD integration and large codebase analysis.
"""

import argparse
import ast
import json
import os
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union


@dataclass
class ViolationReport:
    """Structured violation report"""
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
class ComplianceReport:
    """Complete compliance report"""
    total_violations: int
    compliance_score: float
    timestamp: str
    violations_by_type: Dict[str, int]
    violations: List[ViolationReport]
    summary: Dict[str, Union[int, str]]


class ProgressTracker:
    """Progress tracking for large codebases"""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
    
    def update(self, increment: int = 1):
        """Update progress"""
        self.current += increment
        if self.current % 10 == 0 or self.current == self.total:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed if elapsed > 0 else 0
            percent = (self.current / self.total) * 100
            print(f"\r{self.description}: {self.current}/{self.total} "
                  f"({percent:.1f}%) - {rate:.1f} files/sec", end="")
        
        if self.current == self.total:
            print()  # New line when complete


class EnforcementEngine:
    """Core enforcement engine with configurable thresholds"""
    
    def __init__(self, 
                 root_path: str = ".",
                 max_file_lines: int = 300,
                 max_function_lines: int = 8,
                 exclude_patterns: Optional[List[str]] = None,
                 include_patterns: Optional[List[str]] = None):
        
        self.root_path = Path(root_path)
        self.max_file_lines = max_file_lines
        self.max_function_lines = max_function_lines
        
        # Default exclude patterns for performance
        self.exclude_patterns = exclude_patterns or [
            '__pycache__', 'node_modules', '.git', 'migrations',
            'test_reports', 'docs', '.pytest_cache', 'venv',
            'htmlcov', 'coverage', '.coverage', 'dist', 'build'
        ]
        
        # Default include patterns
        self.include_patterns = include_patterns or [
            'app/**/*.py', 'frontend/**/*.ts', 'frontend/**/*.tsx',
            'scripts/**/*.py', 'tests/**/*.py'
        ]
        
        self.violations: List[ViolationReport] = []

    def should_skip_file(self, file_path: str) -> bool:
        """Determine if file should be skipped"""
        return any(pattern in file_path for pattern in self.exclude_patterns)

    def get_all_files(self) -> List[Path]:
        """Get all files to check with progress tracking"""
        files = []
        
        for pattern in self.include_patterns:
            pattern_files = list(self.root_path.glob(pattern))
            files.extend([f for f in pattern_files 
                         if f.is_file() and not self.should_skip_file(str(f))])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in files:
            if str(f) not in seen:
                seen.add(str(f))
                unique_files.append(f)
        
        return unique_files

    def check_file_size_violations(self, files: List[Path]) -> List[ViolationReport]:
        """Check files for size violations with progress tracking"""
        violations = []
        progress = ProgressTracker(len(files), "Checking file sizes")
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    
                if lines > self.max_file_lines:
                    violations.append(ViolationReport(
                        file_path=str(file_path.relative_to(self.root_path)),
                        violation_type="file_size",
                        severity="high",
                        actual_value=lines,
                        expected_value=self.max_file_lines,
                        description=f"File exceeds {self.max_file_lines} line limit",
                        fix_suggestion=f"Split file into {(lines // self.max_file_lines) + 1} modules with single responsibilities"
                    ))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
            
            progress.update()
        
        return violations

    def analyze_function_complexity(self, file_path: Path) -> List[ViolationReport]:
        """Analyze a single Python file for function complexity"""
        violations = []
        
        if not file_path.suffix == '.py':
            return violations
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lines = self._count_function_lines(node)
                    if lines > self.max_function_lines:
                        violations.append(ViolationReport(
                            file_path=str(file_path.relative_to(self.root_path)),
                            violation_type="function_complexity",
                            severity="medium",
                            line_number=node.lineno,
                            function_name=node.name,
                            actual_value=lines,
                            expected_value=self.max_function_lines,
                            description=f"Function '{node.name}' exceeds {self.max_function_lines} line limit",
                            fix_suggestion=f"Split function into {(lines // self.max_function_lines) + 1} smaller functions with single responsibilities"
                        ))
        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return violations

    def check_function_complexity_violations(self, files: List[Path]) -> List[ViolationReport]:
        """Check all Python files for function complexity violations"""
        python_files = [f for f in files if f.suffix == '.py']
        progress = ProgressTracker(len(python_files), "Analyzing function complexity")
        
        all_violations = []
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(self.analyze_function_complexity, f): f 
                for f in python_files
            }
            
            for future in as_completed(future_to_file):
                violations = future.result()
                all_violations.extend(violations)
                progress.update()
        
        return all_violations

    def find_duplicate_types(self, files: List[Path]) -> List[ViolationReport]:
        """Find duplicate type definitions across the codebase"""
        type_definitions = defaultdict(list)
        violations = []
        
        progress = ProgressTracker(len(files), "Scanning for duplicate types")
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Python classes
                if file_path.suffix == '.py':
                    for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                        type_name = match.group(1)
                        type_definitions[type_name].append(str(file_path.relative_to(self.root_path)))
                
                # TypeScript interfaces and types
                elif file_path.suffix in ['.ts', '.tsx']:
                    for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
                        type_name = match.group(1)
                        type_definitions[type_name].append(str(file_path.relative_to(self.root_path)))
            
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
            
            progress.update()
        
        # Create violations for duplicates
        for type_name, files_list in type_definitions.items():
            if len(files_list) > 1:
                violations.append(ViolationReport(
                    file_path=", ".join(files_list[:3]) + ("..." if len(files_list) > 3 else ""),
                    violation_type="duplicate_types",
                    severity="medium",
                    description=f"Type '{type_name}' defined in {len(files_list)} files",
                    fix_suggestion=f"Consolidate '{type_name}' into single source of truth in shared types file"
                ))
        
        return violations

    def detect_test_stubs(self, files: List[Path]) -> List[ViolationReport]:
        """Detect test stubs in production code"""
        # Enhanced suspicious patterns
        stub_patterns = [
            (r'# Mock implementation', 'Mock implementation comment'),
            (r'# Test stub', 'Test stub comment'),  
            (r'# TODO.*implement', 'TODO implementation comment'),
            (r'""".*test implementation.*"""', 'Test implementation docstring'),
            (r'""".*for testing.*"""', 'For testing docstring'),
            (r'""".*placeholder.*"""', 'Placeholder docstring'),
            (r'return \[{"id": "1"', 'Hardcoded test data return'),
            (r'return {"test": "data"}', 'Test data return'),
            (r'return {"status": "ok"}', 'Static status return'),
            (r'def \w+\(\*args, \*\*kwargs\).*?return {', 'Args/kwargs with static return'),
            (r'raise NotImplementedError', 'Not implemented error'),
            (r'pass\s*#.*stub', 'Explicit stub comment'),
        ]
        
        violations = []
        python_files = [f for f in files if f.suffix == '.py' and 'test' not in str(f)]
        progress = ProgressTracker(len(python_files), "Detecting test stubs")
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern, description in stub_patterns:
                    matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
                    for match in matches:
                        line_number = content[:match.start()].count('\n') + 1
                        violations.append(ViolationReport(
                            file_path=str(file_path.relative_to(self.root_path)),
                            violation_type="test_stub",
                            severity="high",
                            line_number=line_number,
                            description=f"Test stub detected: {description}",
                            fix_suggestion="Replace with production implementation or remove if not needed"
                        ))
                        break  # Only report first match per file to avoid spam
            
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
            
            progress.update()
        
        return violations

    def _count_function_lines(self, node) -> int:
        """Count actual code lines in function (excluding docstrings and comments)"""
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

    def run_all_checks(self) -> ComplianceReport:
        """Run all enforcement checks and generate comprehensive report"""
        print("Starting comprehensive architecture enforcement check...")
        print(f"Target directory: {self.root_path}")
        print(f"Thresholds: {self.max_file_lines} lines/file, {self.max_function_lines} lines/function")
        print("-" * 80)
        
        # Get all files to check
        files = self.get_all_files()
        print(f"Found {len(files)} files to check")
        
        all_violations = []
        
        # Run all checks
        all_violations.extend(self.check_file_size_violations(files))
        all_violations.extend(self.check_function_complexity_violations(files))
        all_violations.extend(self.find_duplicate_types(files))
        all_violations.extend(self.detect_test_stubs(files))
        
        # Generate summary
        violations_by_type = defaultdict(int)
        for violation in all_violations:
            violations_by_type[violation.violation_type] += 1
        
        total_violations = len(all_violations)
        total_files = len(files)
        compliance_score = max(0, (total_files - total_violations) / total_files * 100) if total_files > 0 else 100
        
        report = ComplianceReport(
            total_violations=total_violations,
            compliance_score=compliance_score,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            violations_by_type=dict(violations_by_type),
            violations=all_violations,
            summary={
                "total_files_checked": total_files,
                "files_with_violations": len(set(v.file_path for v in all_violations)),
                "compliance_score": compliance_score,
                "max_file_lines": self.max_file_lines,
                "max_function_lines": self.max_function_lines
            }
        )
        
        return report


def create_argument_parser():
    """Create and configure argument parser"""
    return argparse.ArgumentParser(
        description="Comprehensive enforcement tools for Netra codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_enforcement_tools.py --path . --output report.json
  python create_enforcement_tools.py --max-file-lines 250 --max-function-lines 6
  python create_enforcement_tools.py --fail-on-violation --threshold 95
        """)


def add_basic_arguments(parser):
    """Add basic command line arguments"""
    parser.add_argument('--path', default='.', help='Root path to check (default: current directory)')
    parser.add_argument('--output', '-o', help='Output JSON report to file')
    parser.add_argument('--max-file-lines', type=int, default=300, help='Maximum lines per file (default: 300)')
    parser.add_argument('--max-function-lines', type=int, default=8, help='Maximum lines per function (default: 8)')


def add_advanced_arguments(parser):
    """Add advanced command line arguments"""
    parser.add_argument('--fail-on-violation', action='store_true', help='Exit with non-zero code on violations')
    parser.add_argument('--threshold', type=float, default=0.0, help='Minimum compliance score (0-100) to pass')
    parser.add_argument('--include-pattern', action='append', help='Include files matching pattern (can be used multiple times)')
    parser.add_argument('--exclude-pattern', action='append', help='Exclude files matching pattern (can be used multiple times)')
    parser.add_argument('--json-only', action='store_true', help='Output only JSON, no human-readable report')


def setup_parser_arguments(parser):
    """Add all command line arguments to parser"""
    add_basic_arguments(parser)
    add_advanced_arguments(parser)


def create_enforcement_engine(args):
    """Create enforcement engine from parsed arguments"""
    return EnforcementEngine(
        root_path=args.path,
        max_file_lines=args.max_file_lines,
        max_function_lines=args.max_function_lines,
        include_patterns=args.include_pattern,
        exclude_patterns=args.exclude_pattern
    )


def print_report_header(report):
    """Print report header information"""
    print("\n" + "="*80)
    print("COMPREHENSIVE ENFORCEMENT REPORT")
    print("="*80)
    print(f"Timestamp: {report.timestamp}")
    print(f"Compliance Score: {report.compliance_score:.1f}%")
    print(f"Total Violations: {report.total_violations}")
    print(f"Files Checked: {report.summary['total_files_checked']}")
    print(f"Files with Violations: {report.summary['files_with_violations']}")


def print_violations_by_type(report):
    """Print violations grouped by type"""
    print("\nVIOLATIONS BY TYPE:")
    print("-" * 40)
    for violation_type, count in report.violations_by_type.items():
        print(f"  {violation_type.replace('_', ' ').title()}: {count}")


def print_violation_details(violation):
    """Print details for a single violation"""
    print(f"  {violation.file_path}")
    print(f"    {violation.description}")
    print(f"    Fix: {violation.fix_suggestion}")
    print()


def print_high_severity_violations(report):
    """Print top high severity violations"""
    high_severity = [v for v in report.violations if v.severity == "high"]
    if high_severity:
        print(f"\nTOP HIGH SEVERITY VIOLATIONS (showing first 10):")
        print("-" * 40)
        for violation in high_severity[:10]:
            print_violation_details(violation)


def generate_console_output(report, json_only):
    """Generate appropriate console output"""
    if json_only:
        print(json.dumps(asdict(report), indent=2))
    else:
        print_report_header(report)
        print_violations_by_type(report)
        print_high_severity_violations(report)


def save_json_report(report, output_path):
    """Save JSON report to specified file"""
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        print(f"\nJSON report saved to: {output_path}")


def handle_exit_logic(args, report):
    """Handle exit code based on violations and thresholds"""
    if args.fail_on_violation and (
        report.total_violations > 0 or 
        report.compliance_score < args.threshold
    ):
        sys.exit(1)
    sys.exit(0)


def main():
    """Main entry point for enforcement tools"""
    parser = create_argument_parser()
    setup_parser_arguments(parser)
    args = parser.parse_args()
    engine = create_enforcement_engine(args)
    report = engine.run_all_checks()
    generate_console_output(report, args.json_only)
    save_json_report(report, args.output)
    handle_exit_logic(args, report)


if __name__ == "__main__":
    main()