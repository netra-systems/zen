#!/usr/bin/env python3
"""
Async Test Pattern Validation Script

Prevents async test decorator gaps by automatically scanning for async test methods
missing @pytest.mark.asyncio decorators.

Business Value Justification (BVJ):
- Segment: Platform Development
- Business Goal: Development Velocity - Prevent async test failures that block CI/CD
- Value Impact: Automated validation prevents 94.7% → 100% test pass rate issues
- Strategic Impact: Maintains development team productivity and system reliability

Usage:
    python scripts/validate_async_test_patterns.py
    python scripts/validate_async_test_patterns.py --fix
    python scripts/validate_async_test_patterns.py --dir netra_backend/tests/unit
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import ast

class AsyncTestValidator:
    """Validates and fixes async test method decorator patterns."""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(".")
        self.violations = []

    def find_async_test_violations(self, file_path: Path) -> List[Dict]:
        """Find async test methods missing @pytest.mark.asyncio decorator."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Parse with AST for accuracy
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('test_'):
                    # Check if @pytest.mark.asyncio decorator is present
                    has_asyncio_decorator = any(
                        isinstance(d, ast.Attribute) and
                        isinstance(d.value, ast.Attribute) and
                        getattr(d.value.value, 'id', None) == 'pytest' and
                        d.value.attr == 'mark' and
                        d.attr == 'asyncio'
                        for d in node.decorator_list
                    ) or any(
                        isinstance(d, ast.Name) and
                        d.id == 'asyncio'  # Handle @asyncio shorthand
                        for d in node.decorator_list
                    )

                    if not has_asyncio_decorator:
                        violations.append({
                            'file': str(file_path),
                            'function': node.name,
                            'line': node.lineno,
                            'content': lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ''
                        })

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return []

        return violations

    def scan_directory(self, directory: Path = None) -> List[Dict]:
        """Scan directory for async test violations."""
        if directory is None:
            directory = self.base_dir

        all_violations = []

        # Find all test files
        test_files = list(directory.rglob("test_*.py"))
        test_files.extend(directory.rglob("*_test.py"))

        for test_file in test_files:
            violations = self.find_async_test_violations(test_file)
            all_violations.extend(violations)

        return all_violations

    def fix_violations(self, violations: List[Dict]) -> int:
        """Fix violations by adding missing decorators."""
        files_fixed = set()

        for violation in violations:
            file_path = Path(violation['file'])

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                line_idx = violation['line'] - 1  # Convert to 0-based index

                if line_idx < len(lines):
                    # Find the indentation level
                    current_line = lines[line_idx]
                    indent = len(current_line) - len(current_line.lstrip())

                    # Insert @pytest.mark.asyncio decorator
                    decorator_line = ' ' * indent + '@pytest.mark.asyncio\n'
                    lines.insert(line_idx, decorator_line)

                    # Write back to file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)

                    files_fixed.add(str(file_path))
                    print(f"Fixed: {violation['function']} in {file_path}")

            except Exception as e:
                print(f"Error fixing {file_path}: {e}")

        return len(files_fixed)

    def validate_import_exists(self, file_path: Path) -> bool:
        """Check if pytest import exists in file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'import pytest' in content
        except:
            return False

def main():
    parser = argparse.ArgumentParser(description='Validate async test patterns')
    parser.add_argument('--fix', action='store_true', help='Fix violations automatically')
    parser.add_argument('--dir', type=str, help='Directory to scan (default: current)')
    parser.add_argument('--file', type=str, help='Specific file to check')
    args = parser.parse_args()

    validator = AsyncTestValidator(args.dir)

    if args.file:
        # Check specific file
        violations = validator.find_async_test_violations(Path(args.file))
    else:
        # Scan directory
        violations = validator.scan_directory()

    if not violations:
        print("[SUCCESS] No async test pattern violations found!")
        return 0

    print(f"[WARNING] Found {len(violations)} async test violations:")
    print()

    for violation in violations:
        print(f"File: {violation['file']}")
        print(f"Function: {violation['function']} (line {violation['line']})")
        print(f"Content: {violation['content']}")
        print()

    if args.fix:
        print("Fixing violations...")
        files_fixed = validator.fix_violations(violations)
        print(f"[SUCCESS] Fixed {len(violations)} violations in {files_fixed} files")
        return 0
    else:
        print("Use --fix to automatically add missing decorators")
        return 1

if __name__ == "__main__":
    sys.exit(main())