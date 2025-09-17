#!/usr/bin/env python3
"""
Syntax Error Scanner for Test Infrastructure Crisis
Scans all Python test files for syntax errors and categorizes them.
"""

import ast
import os
import py_compile
import tempfile
from collections import defaultdict
from pathlib import Path
import traceback
import json

class TestSyntaxScanner:
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir)
        self.errors = defaultdict(list)
        self.error_categories = defaultdict(int)
        self.total_files_scanned = 0
        self.files_with_errors = 0

    def find_test_files(self):
        """Find all Python test files in the project, excluding backups."""
        # Focus on current test directories, exclude backups
        test_dirs = [
            "tests",
            "netra_backend/tests",
            "auth_service/tests",
            "test_framework/tests"
        ]

        test_files = set()
        for test_dir in test_dirs:
            test_dir_path = self.root_dir / test_dir
            if test_dir_path.exists():
                # Get all .py files in test directories
                for py_file in test_dir_path.rglob("*.py"):
                    # Skip files in backup directories
                    if "backup" not in str(py_file).lower() and "__pycache__" not in str(py_file):
                        test_files.add(py_file)

        return sorted(test_files)

    def categorize_error(self, error_msg, file_path):
        """Categorize the type of syntax error."""
        error_lower = str(error_msg).lower()

        if "indentationerror" in error_lower or "expected an indented block" in error_lower:
            return "IndentationError"
        elif "untemp" in error_lower or "eol while scanning" in error_lower or "unterminated" in error_lower:
            return "UnterminatedString"
        elif "invalid syntax" in error_lower:
            return "SyntaxError"
        elif "unexpected indent" in error_lower:
            return "IndentationError"
        elif "unmatched" in error_lower or "closing parenthesis" in error_lower:
            return "UnmatchedParentheses"
        elif "import" in error_lower and ("invalid" in error_lower or "error" in error_lower):
            return "ImportError"
        elif "encoding" in error_lower:
            return "EncodingError"
        else:
            return "OtherSyntaxError"

    def check_file_syntax(self, file_path):
        """Check a single file for syntax errors using multiple methods."""
        errors = []

        try:
            # Method 1: Try to read and parse with AST
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                ast.parse(content, filename=str(file_path))
            except SyntaxError as e:
                error_type = self.categorize_error(str(e), file_path)
                errors.append({
                    'method': 'ast.parse',
                    'error_type': error_type,
                    'error': str(e),
                    'line': getattr(e, 'lineno', None),
                    'column': getattr(e, 'offset', None),
                    'text': getattr(e, 'text', None)
                })
            except Exception as e:
                error_type = self.categorize_error(str(e), file_path)
                errors.append({
                    'method': 'ast.parse',
                    'error_type': error_type,
                    'error': str(e),
                    'line': None,
                    'column': None,
                    'text': None
                })

        except UnicodeDecodeError as e:
            errors.append({
                'method': 'file_read',
                'error_type': 'EncodingError',
                'error': str(e),
                'line': None,
                'column': None,
                'text': None
            })
        except Exception as e:
            errors.append({
                'method': 'file_read',
                'error_type': 'FileReadError',
                'error': str(e),
                'line': None,
                'column': None,
                'text': None
            })

        # Method 2: Try py_compile if AST parsing succeeded
        if not errors:
            try:
                with tempfile.NamedTemporaryFile(suffix='.pyc', delete=True) as tmp:
                    py_compile.compile(str(file_path), tmp.name, doraise=True)
            except py_compile.PyCompileError as e:
                error_type = self.categorize_error(str(e), file_path)
                errors.append({
                    'method': 'py_compile',
                    'error_type': error_type,
                    'error': str(e),
                    'line': None,
                    'column': None,
                    'text': None
                })
            except Exception as e:
                error_type = self.categorize_error(str(e), file_path)
                errors.append({
                    'method': 'py_compile',
                    'error_type': error_type,
                    'error': str(e),
                    'line': None,
                    'column': None,
                    'text': None
                })

        return errors

    def scan_all_files(self):
        """Scan all test files for syntax errors."""
        test_files = self.find_test_files()

        print(f"Found {len(test_files)} test files to scan...")

        for file_path in test_files:
            self.total_files_scanned += 1

            # Skip __pycache__ and .pyc files
            if "__pycache__" in str(file_path) or file_path.suffix == ".pyc":
                continue

            print(f"Scanning: {file_path}")

            file_errors = self.check_file_syntax(file_path)

            if file_errors:
                self.files_with_errors += 1
                self.errors[str(file_path)] = file_errors

                for error in file_errors:
                    self.error_categories[error['error_type']] += 1

    def prioritize_files(self):
        """Prioritize files for fixing based on criticality."""
        critical_patterns = [
            "mission_critical",
            "websocket_agent_events",
            "agent_message",
            "websocket_infrastructure",
            "integration",
            "test_websocket",
            "test_agent"
        ]

        high_priority = []
        medium_priority = []
        low_priority = []

        for file_path in self.errors.keys():
            file_lower = file_path.lower()

            is_critical = any(pattern in file_lower for pattern in critical_patterns)

            if is_critical:
                high_priority.append(file_path)
            elif "test_" in file_lower or "/tests/" in file_lower:
                medium_priority.append(file_path)
            else:
                low_priority.append(file_path)

        return {
            'high_priority': sorted(high_priority),
            'medium_priority': sorted(medium_priority),
            'low_priority': sorted(low_priority)
        }

    def generate_report(self):
        """Generate comprehensive error report."""
        priorities = self.prioritize_files()

        report = {
            'summary': {
                'total_files_scanned': self.total_files_scanned,
                'files_with_errors': self.files_with_errors,
                'error_free_files': self.total_files_scanned - self.files_with_errors,
                'error_categories': dict(self.error_categories)
            },
            'priorities': priorities,
            'detailed_errors': dict(self.errors)
        }

        return report

    def print_summary(self):
        """Print a summary of findings."""
        print("\n" + "="*80)
        print("SYNTAX ERROR SCAN RESULTS")
        print("="*80)

        print(f"Total files scanned: {self.total_files_scanned}")
        print(f"Files with errors: {self.files_with_errors}")
        print(f"Error-free files: {self.total_files_scanned - self.files_with_errors}")

        print(f"\nError Categories:")
        for category, count in sorted(self.error_categories.items()):
            print(f"  {category}: {count}")

        priorities = self.prioritize_files()

        print(f"\nPriority Breakdown:")
        print(f"  High Priority (Critical): {len(priorities['high_priority'])}")
        print(f"  Medium Priority (Tests): {len(priorities['medium_priority'])}")
        print(f"  Low Priority (Other): {len(priorities['low_priority'])}")

        if priorities['high_priority']:
            print(f"\nCRITICAL FILES TO FIX FIRST:")
            for file_path in priorities['high_priority'][:10]:  # Show first 10
                errors = self.errors[file_path]
                error_types = [e['error_type'] for e in errors]
                print(f"  {file_path}")
                print(f"    Errors: {', '.join(set(error_types))}")

    def save_detailed_report(self, output_file):
        """Save detailed report to JSON file."""
        report = self.generate_report()

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\nDetailed report saved to: {output_file}")

def main():
    """Main function to run the syntax scanner."""
    scanner = TestSyntaxScanner()

    print("Starting comprehensive test file syntax scan...")
    scanner.scan_all_files()

    scanner.print_summary()

    # Save detailed report
    report_file = "test_syntax_errors_report.json"
    scanner.save_detailed_report(report_file)

    return scanner

if __name__ == "__main__":
    scanner = main()