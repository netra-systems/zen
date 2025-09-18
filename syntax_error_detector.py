#!/usr/bin/env python3
"""
Syntax Error Detection and Repair Script for Test Infrastructure
Issue #837 - Emergency Test File Syntax Repair

This script identifies Python files with syntax errors and categorizes the error types
to enable automated repair.
"""

import ast
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import traceback
import shutil
from datetime import datetime


class SyntaxErrorDetector:
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.errors = []
        self.error_patterns = {
            "mismatched_parentheses": [],
            "unterminated_strings": [],
            "indentation_errors": [],
            "invalid_syntax": [],
            "encoding_errors": [],
            "other": []
        }

    def find_test_files(self) -> List[Path]:
        """Find all Python test files in the project."""
        test_patterns = [
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**/*.py",
            "**/conftest*.py"
        ]

        test_files = []
        for pattern in test_patterns:
            test_files.extend(self.root_dir.glob(pattern))

        # Remove duplicates and ensure they're Python files
        unique_files = []
        seen = set()
        for file in test_files:
            if file.suffix == '.py' and str(file) not in seen:
                unique_files.append(file)
                seen.add(str(file))

        return unique_files

    def check_syntax_ast(self, file_path: Path) -> Optional[Dict]:
        """Check syntax using AST parsing."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to parse with AST
            ast.parse(content, filename=str(file_path))
            return None  # No syntax error

        except SyntaxError as e:
            return {
                "file": str(file_path),
                "error_type": "syntax_error",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text
            }
        except UnicodeDecodeError as e:
            return {
                "file": str(file_path),
                "error_type": "encoding_error",
                "message": str(e),
                "line": None,
                "offset": None,
                "text": None
            }
        except Exception as e:
            return {
                "file": str(file_path),
                "error_type": "other_error",
                "message": str(e),
                "line": None,
                "offset": None,
                "text": None
            }

    def check_syntax_compile(self, file_path: Path) -> Optional[Dict]:
        """Check syntax using compile() - alternative check."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            compile(content, str(file_path), 'exec')
            return None  # No syntax error

        except SyntaxError as e:
            return {
                "file": str(file_path),
                "error_type": "compile_syntax_error",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text
            }
        except Exception as e:
            return {
                "file": str(file_path),
                "error_type": "compile_other_error",
                "message": str(e),
                "line": None,
                "offset": None,
                "text": None
            }

    def categorize_error(self, error_info: Dict) -> str:
        """Categorize the error type for targeted repair."""
        message = error_info.get("message", "").lower()

        if "unmatched" in message or "parenthes" in message or "bracket" in message:
            return "mismatched_parentheses"
        elif "unterminated" in message or "eol while scanning" in message:
            return "unterminated_strings"
        elif "indentation" in message or "indent" in message:
            return "indentation_errors"
        elif "encoding" in error_info.get("error_type", ""):
            return "encoding_errors"
        else:
            return "invalid_syntax"

    def analyze_files(self) -> Dict:
        """Analyze all test files for syntax errors."""
        test_files = self.find_test_files()

        print(f"Found {len(test_files)} test files to analyze...")

        total_errors = 0
        for i, file_path in enumerate(test_files):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(test_files)} files analyzed")

            # Try AST parsing first
            error = self.check_syntax_ast(file_path)
            if error is None:
                # Try compile as backup
                error = self.check_syntax_compile(file_path)

            if error is not None:
                category = self.categorize_error(error)
                error["category"] = category
                self.errors.append(error)
                self.error_patterns[category].append(error)
                total_errors += 1

                print(f"SYNTAX ERROR: {file_path}")
                print(f"  Category: {category}")
                print(f"  Message: {error['message']}")
                print(f"  Line: {error.get('line', 'Unknown')}")
                print()

        print(f"Analysis complete. Found {total_errors} files with syntax errors.")
        return self.generate_report()

    def generate_report(self) -> Dict:
        """Generate a comprehensive report of findings."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_files_analyzed": len(self.find_test_files()),
            "total_syntax_errors": len(self.errors),
            "error_breakdown": {
                category: len(errors) for category, errors in self.error_patterns.items()
            },
            "detailed_errors": self.errors,
            "error_patterns": self.error_patterns
        }

        return report

    def save_report(self, filename: str = "syntax_error_report.json"):
        """Save the analysis report to a JSON file."""
        report = self.generate_report()

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Report saved to {filename}")
        return report


def main():
    """Main execution function."""
    print("Starting syntax error detection for test infrastructure...")
    print("=" * 60)

    detector = SyntaxErrorDetector()
    report = detector.analyze_files()

    # Save the report
    detector.save_report("syntax_error_analysis_report.json")

    # Print summary
    print("\n" + "=" * 60)
    print("SYNTAX ERROR ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total files analyzed: {report['total_files_analyzed']}")
    print(f"Files with syntax errors: {report['total_syntax_errors']}")
    print(f"Error breakdown:")
    for category, count in report['error_breakdown'].items():
        if count > 0:
            print(f"  {category}: {count} files")

    if report['total_syntax_errors'] > 0:
        print(f"\nNext step: Run syntax_error_repair.py to fix these errors")
        return 1
    else:
        print(f"\nNo syntax errors found! Test infrastructure is clean.")
        return 0


if __name__ == "__main__":
    exit(main())