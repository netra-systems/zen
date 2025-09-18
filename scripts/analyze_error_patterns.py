#!/usr/bin/env python3
"""
Analyze remaining syntax error patterns to guide targeted fixes.
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path


def analyze_syntax_errors():
    """Analyze syntax errors and categorize them."""
    error_patterns = defaultdict(list)
    test_dir = Path("tests")

    for py_file in test_dir.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to parse the file
            try:
                ast.parse(content)
            except SyntaxError as e:
                error_type = categorize_error(str(e))
                error_patterns[error_type].append((str(py_file), e.lineno, str(e)))
        except Exception as e:
            error_patterns["File Read Error"].append((str(py_file), 0, str(e)))

    return error_patterns


def categorize_error(error_msg):
    """Categorize syntax errors by type."""
    if "unterminated string literal" in error_msg:
        return "Unterminated String Literal"
    elif "unterminated triple-quoted string literal" in error_msg:
        return "Unterminated Triple-Quoted String"
    elif "invalid syntax" in error_msg:
        return "Invalid Syntax"
    elif "closing parenthesis" in error_msg and "does not match" in error_msg:
        return "Mismatched Brackets/Parentheses"
    elif "invalid decimal literal" in error_msg:
        return "Invalid Decimal Literal"
    elif "unexpected EOF" in error_msg:
        return "Unexpected EOF"
    elif "expected" in error_msg:
        return "Expected Token Missing"
    else:
        return "Other Syntax Error"


def main():
    print("Analyzing remaining syntax error patterns...")
    error_patterns = analyze_syntax_errors()

    print(f"\nERROR PATTERN ANALYSIS:")
    print("=" * 50)

    total_errors = sum(len(files) for files in error_patterns.values())
    print(f"Total files with errors: {total_errors}")
    print()

    # Sort by frequency
    for pattern, files in sorted(error_patterns.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{pattern}: {len(files)} files")
        if len(files) <= 5:  # Show all if few
            for file_path, line_no, error in files[:5]:
                print(f"  - {file_path}:{line_no} - {error}")
        else:  # Show top 5
            for file_path, line_no, error in files[:5]:
                print(f"  - {file_path}:{line_no} - {error}")
            print(f"  ... and {len(files) - 5} more")
        print()


if __name__ == "__main__":
    main()