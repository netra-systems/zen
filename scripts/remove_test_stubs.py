#!/usr/bin/env python3
"""
Test Stub Detection and Removal Script

This script automatically detects test stubs, mock implementations, and placeholder
code in production files according to the SPEC/no_test_stubs.xml specification.

Usage:
    python scripts/remove_test_stubs.py --scan          # Scan for test stubs
    python scripts/remove_test_stubs.py --fix           # Fix detected stubs
    python scripts/remove_test_stubs.py --report        # Generate detailed report
"""

import argparse
import csv
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TestStubViolation:
    """Represents a test stub violation found in production code."""
    file_path: str
    line_number: int
    violation_type: str
    severity: str
    description: str
    code_snippet: str
    recommended_action: str
    auto_fixable: bool = False


class TestStubDetector:
    """Detects test stubs and mock implementations in production code."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations: List[TestStubViolation] = []
        
        # Pattern definitions based on SPEC/no_test_stubs.xml
        self.patterns = {
            'mock_implementation_comments': [
                r'""".*mock implementation.*"""',
                r'""".*test implementation.*"""',
                r'""".*for testing.*"""',
                r'# Mock implementation',
                r'# Test stub',
                r'# Test implementation',
            ],
            'hardcoded_test_data': [
                r'return\s*\[\s*\{\s*["\']id["\']\s*:\s*["\']1["\']',
                r'return\s*\{\s*["\']test["\']\s*:\s*["\']data["\']\s*\}',
                r'return\s*\{\s*["\']status["\']\s*:\s*["\']ok["\']\s*\}',
                r'\[\s*["\']Part 1["\']\s*,\s*["\']Part 2["\']\s*,\s*["\']Part 3["\']\s*\]',
            ],
            'args_kwargs_stubs': [
                r'async\s+def\s+\w+\(\*args\s*,\s*\*\*kwargs\)\s*:\s*\n.*return\s*\{',
                r'def\s+\w+\(\*args\s*,\s*\*\*kwargs\)\s*:\s*\n.*return\s*\{',
            ],
            'empty_implementations': [
                r'def\s+\w+\([^)]*\)\s*:\s*\n\s*pass\s*$',
                r'async\s+def\s+\w+\([^)]*\)\s*:\s*\n\s*pass\s*$',
                r'def\s+\w+\([^)]*\)\s*:\s*\n\s*\.\.\.\s*$',
                r'async\s+def\s+\w+\([^)]*\)\s*:\s*\n\s*\.\.\.\s*$',
            ],
        }
        
        # Directories to scan (production code only)
        self.scan_dirs = ['app', 'frontend']
        
        # Directories to exclude (test directories)
        self.exclude_dirs = [
            'tests', '__tests__', 'test_', 'testing',
            'node_modules', '.git', '__pycache__',
            'htmlcov', 'coverage', '.pytest_cache'
        ]
        
        # File extensions to scan
        self.scan_extensions = ['.py', '.ts', '.tsx', '.js', '.jsx']

    def should_scan_file(self, file_path: Path) -> bool:
        """Determine if a file should be scanned for test stubs."""
        # Check if file is in a test directory
        path_parts = file_path.parts
        for part in path_parts:
            if any(exclude in part.lower() for exclude in self.exclude_dirs):
                return False
        
        # Check file extension
        if file_path.suffix not in self.scan_extensions:
            return False
        
        # Skip test files by name pattern
        if any(pattern in file_path.name.lower() for pattern in ['test_', '_test', '.test.', 'spec.']):
            return False
        
        return True

    def scan_directory(self, directory: str) -> List[TestStubViolation]:
        """Scan a directory for test stub violations."""
        violations = []
        scan_path = self.project_root / directory
        
        if not scan_path.exists():
            print(f"Directory {scan_path} does not exist, skipping.")
            return violations
        
        for file_path in scan_path.rglob('*'):
            if file_path.is_file() and self.should_scan_file(file_path):
                file_violations = self.scan_file(file_path)
                violations.extend(file_violations)
        
        return violations

    def scan_file(self, file_path: Path) -> List[TestStubViolation]:
        """Scan a single file for test stub violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except (UnicodeDecodeError, IOError) as e:
            print(f"Error reading {file_path}: {e}")
            return violations
        
        # Scan for different types of violations
        violations.extend(self._scan_comments(file_path, lines))
        violations.extend(self._scan_hardcoded_data(file_path, lines))
        violations.extend(self._scan_args_kwargs_stubs(file_path, content))
        violations.extend(self._scan_empty_implementations(file_path, content))
        
        return violations

    def _scan_comments(self, file_path: Path, lines: List[str]) -> List[TestStubViolation]:
        """Scan for test stub comments and docstrings."""
        violations = []
        
        for i, line in enumerate(lines, 1):
            for pattern in self.patterns['mock_implementation_comments']:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(TestStubViolation(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type="mock_implementation_comment",
                        severity="HIGH",
                        description=f"Mock/test implementation comment found: {line.strip()}",
                        code_snippet=line.strip(),
                        recommended_action="Replace with real implementation or move to test directory",
                        auto_fixable=False
                    ))
        
        return violations

    def _scan_hardcoded_data(self, file_path: Path, lines: List[str]) -> List[TestStubViolation]:
        """Scan for hardcoded test data patterns."""
        violations = []
        
        for i, line in enumerate(lines, 1):
            for pattern in self.patterns['hardcoded_test_data']:
                if re.search(pattern, line):
                    # Skip if in health check endpoints (legitimate use)
                    if 'health' in str(file_path).lower() and 'status' in pattern:
                        continue
                    
                    violations.append(TestStubViolation(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type="hardcoded_test_data",
                        severity="MEDIUM",
                        description=f"Hardcoded test data pattern found: {line.strip()}",
                        code_snippet=line.strip(),
                        recommended_action="Replace with real data source or move to test fixtures",
                        auto_fixable=False
                    ))
        
        return violations

    def _scan_args_kwargs_stubs(self, file_path: Path, content: str) -> List[TestStubViolation]:
        """Scan for functions that accept *args, **kwargs and return static data."""
        violations = []
        
        for pattern in self.patterns['args_kwargs_stubs']:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                line_number = content[:match.start()].count('\n') + 1
                
                violations.append(TestStubViolation(
                    file_path=str(file_path),
                    line_number=line_number,
                    violation_type="args_kwargs_stub",
                    severity="HIGH",
                    description="Function accepts *args, **kwargs and returns static data",
                    code_snippet=match.group()[:100] + "..." if len(match.group()) > 100 else match.group(),
                    recommended_action="Replace with proper function signature and real implementation",
                    auto_fixable=False
                ))
        
        return violations

    def _scan_empty_implementations(self, file_path: Path, content: str) -> List[TestStubViolation]:
        """Scan for empty function implementations (pass or ...)."""
        violations = []
        
        # Skip Protocol definitions and abstract classes (legitimate use of ...)
        if 'Protocol' in content or 'ABC' in content or 'abstractmethod' in content:
            return violations
        
        for pattern in self.patterns['empty_implementations']:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                line_number = content[:match.start()].count('\n') + 1
                
                # Check if this is in a Protocol or abstract class context
                before_match = content[:match.start()]
                recent_lines = before_match.split('\n')[-10:]  # Look at recent lines
                
                if any('Protocol' in line or 'ABC' in line or '@abstractmethod' in line 
                       for line in recent_lines):
                    continue
                
                violations.append(TestStubViolation(
                    file_path=str(file_path),
                    line_number=line_number,
                    violation_type="empty_implementation",
                    severity="MEDIUM",
                    description="Empty function implementation found",
                    code_snippet=match.group().strip(),
                    recommended_action="Implement real functionality or remove unused function",
                    auto_fixable=False
                ))
        
        return violations

    def scan_all(self) -> List[TestStubViolation]:
        """Scan all production directories for test stub violations."""
        all_violations = []
        
        for directory in self.scan_dirs:
            print(f"Scanning {directory}/ directory...")
            violations = self.scan_directory(directory)
            all_violations.extend(violations)
            print(f"Found {len(violations)} violations in {directory}/")
        
        self.violations = all_violations
        return all_violations

    def generate_report(self, output_format: str = 'json') -> str:
        """Generate a detailed report of all violations."""
        if not self.violations:
            self.scan_all()
        
        report_data = {
            'scan_timestamp': datetime.now().isoformat(),
            'total_violations': len(self.violations),
            'severity_breakdown': self._get_severity_breakdown(),
            'violation_type_breakdown': self._get_type_breakdown(),
            'files_affected': len(set(v.file_path for v in self.violations)),
            'violations': [asdict(v) for v in self.violations]
        }
        
        if output_format == 'json':
            return json.dumps(report_data, indent=2)
        elif output_format == 'csv':
            return self._generate_csv_report()
        else:
            return self._generate_text_report(report_data)

    def _get_severity_breakdown(self) -> Dict[str, int]:
        """Get breakdown of violations by severity."""
        breakdown = {}
        for violation in self.violations:
            breakdown[violation.severity] = breakdown.get(violation.severity, 0) + 1
        return breakdown

    def _get_type_breakdown(self) -> Dict[str, int]:
        """Get breakdown of violations by type."""
        breakdown = {}
        for violation in self.violations:
            breakdown[violation.violation_type] = breakdown.get(violation.violation_type, 0) + 1
        return breakdown

    def _generate_csv_report(self) -> str:
        """Generate CSV format report."""
        if not self.violations:
            return "file_path,line_number,violation_type,severity,description,recommended_action\n"
        
        output = []
        output.append("file_path,line_number,violation_type,severity,description,recommended_action")
        
        for violation in self.violations:
            output.append(f'"{violation.file_path}",{violation.line_number},'
                         f'"{violation.violation_type}","{violation.severity}",'
                         f'"{violation.description}","{violation.recommended_action}"')
        
        return '\n'.join(output)

    def _generate_text_report(self, report_data: Dict[str, Any]) -> str:
        """Generate human-readable text report."""
        lines = []
        lines.append("=" * 80)
        lines.append("TEST STUB DETECTION REPORT")
        lines.append("=" * 80)
        lines.append(f"Scan Date: {report_data['scan_timestamp']}")
        lines.append(f"Total Violations: {report_data['total_violations']}")
        lines.append(f"Files Affected: {report_data['files_affected']}")
        lines.append("")
        
        lines.append("SEVERITY BREAKDOWN:")
        for severity, count in report_data['severity_breakdown'].items():
            lines.append(f"  {severity}: {count}")
        lines.append("")
        
        lines.append("VIOLATION TYPE BREAKDOWN:")
        for vtype, count in report_data['violation_type_breakdown'].items():
            lines.append(f"  {vtype}: {count}")
        lines.append("")
        
        lines.append("DETAILED VIOLATIONS:")
        lines.append("-" * 80)
        
        for violation in self.violations:
            lines.append(f"File: {violation.file_path}")
            lines.append(f"Line: {violation.line_number}")
            lines.append(f"Type: {violation.violation_type}")
            lines.append(f"Severity: {violation.severity}")
            lines.append(f"Description: {violation.description}")
            lines.append(f"Code: {violation.code_snippet}")
            lines.append(f"Action: {violation.recommended_action}")
            lines.append("-" * 40)
        
        return '\n'.join(lines)

    def save_report(self, filename: str, format: str = 'json') -> None:
        """Save report to file."""
        report_content = self.generate_report(format)
        
        output_path = self.project_root / 'reports' / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"Report saved to {output_path}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Test Stub Detection and Removal Tool')
    parser.add_argument('--scan', action='store_true', help='Scan for test stubs')
    parser.add_argument('--fix', action='store_true', help='Fix detected stubs (not implemented)')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--format', choices=['json', 'csv', 'text'], default='text',
                       help='Report format (default: text)')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    args = parser.parse_args()
    
    detector = TestStubDetector(args.project_root)
    
    if args.scan or args.report:
        print("Scanning for test stubs...")
        violations = detector.scan_all()
        
        print(f"\nScan completed. Found {len(violations)} violations.")
        
        if violations:
            print("\nSummary:")
            severity_breakdown = detector._get_severity_breakdown()
            for severity, count in severity_breakdown.items():
                print(f"  {severity}: {count}")
        
        if args.report:
            if args.output:
                detector.save_report(args.output, args.format)
            else:
                print("\n" + "=" * 80)
                print(detector.generate_report(args.format))
    
    elif args.fix:
        print("Auto-fix functionality not implemented yet.")
        print("Please review violations manually and implement proper solutions.")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()