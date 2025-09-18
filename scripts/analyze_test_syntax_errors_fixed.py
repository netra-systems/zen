#!/usr/bin/env python3
"""
Script to analyze syntax errors in test files and categorize them by type and severity.
"""

import os
import ast
import sys
import subprocess
from pathlib import Path
from collections import defaultdict
import re

def find_test_files(root_dir):
    """Find all Python test files in the project."""
    test_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip backup directories
        if 'backup' in root.lower() or '__pycache__' in root:
            continue

        for file in files:
            if file.endswith('.py') and ('test' in root or file.startswith('test_')):
                test_files.append(os.path.join(root, file))
    return test_files

def check_syntax_errors(file_path):
    """Check for syntax errors in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to parse the AST
        ast.parse(content)
        return None, content
    except SyntaxError as e:
        return e, content if 'content' in locals() else None
    except Exception as e:
        return e, None

def categorize_error(error_msg, content):
    """Categorize the type of syntax error."""
    error_str = str(error_msg)

    # Common patterns from the failed formatting
    patterns = {
        'dict_bracket_mismatch': r'{ \)',
        'list_bracket_mismatch': r'\[ \)',
        'missing_colon': r'if\s+.*[^:]\s*$',
        'missing_indent': r'IndentationError',
        'unterminated_string': r'unterminated string',
        'unmatched_parentheses': r"closing parenthesis '\)' does not match opening parenthesis",
        'removed_syntax_marker': r'REMOVED_SYNTAX_ERROR'
    }

    for category, pattern in patterns.items():
        if re.search(pattern, error_str) or (content and re.search(pattern, content)):
            return category

    return 'other'

def prioritize_files(test_files):
    """Prioritize test files by importance."""
    priorities = {
        'mission_critical': [],
        'e2e': [],
        'integration': [],
        'unit': [],
        'other': []
    }

    for file_path in test_files:
        path_lower = file_path.lower()
        if 'mission_critical' in path_lower:
            priorities['mission_critical'].append(file_path)
        elif 'e2e' in path_lower or 'end_to_end' in path_lower:
            priorities['e2e'].append(file_path)
        elif 'integration' in path_lower:
            priorities['integration'].append(file_path)
        elif 'unit' in path_lower:
            priorities['unit'].append(file_path)
        else:
            priorities['other'].append(file_path)

    return priorities

def main():
    """Main analysis function."""
    root_dir = '/c/netra-apex'

    print("ANALYZING Analyzing test file syntax errors...")

    # Find all test files
    test_files = find_test_files(root_dir)
    print(f"Found {len(test_files)} test files")

    # Check syntax errors
    error_count = 0
    error_categories = defaultdict(list)
    priority_errors = defaultdict(int)

    for file_path in test_files:
        error, content = check_syntax_errors(file_path)
        if error:
            error_count += 1
            category = categorize_error(str(error), content)
            error_categories[category].append({
                'file': file_path,
                'error': str(error),
                'line': getattr(error, 'lineno', None)
            })

    # Prioritize files
    priorities = prioritize_files([item['file'] for category in error_categories.values() for item in category])

    print(f"\nSYNTAX SYNTAX ERROR ANALYSIS RESULTS")
    print(f"=" * 50)
    print(f"Total test files: {len(test_files)}")
    print(f"Files with syntax errors: {error_count}")
    print(f"Files without errors: {len(test_files) - error_count}")

    print(f"\nERROR ERROR BREAKDOWN BY CATEGORY:")
    for category, errors in error_categories.items():
        print(f"  {category}: {len(errors)} files")
        # Show first few examples
        for i, error_info in enumerate(errors[:3]):
            rel_path = error_info['file'].replace('/c/netra-apex/', '')
            print(f"    - {rel_path} (line {error_info.get('line', 'unknown')})")
        if len(errors) > 3:
            print(f"    ... and {len(errors) - 3} more files")

    print(f"\nPRIORITY PRIORITY BREAKDOWN:")
    total_priority_errors = 0
    for priority, files in priorities.items():
        error_files = [f for f in files if any(f == item['file'] for category in error_categories.values() for item in category)]
        if error_files:
            total_priority_errors += len(error_files)
            print(f"  {priority}: {len(error_files)} files with errors")
            # Show examples
            for file_path in error_files[:2]:
                rel_path = file_path.replace('/c/netra-apex/', '')
                print(f"    - {rel_path}")

    # Most common error patterns
    print(f"\nMOST MOST COMMON PATTERNS:")
    pattern_counts = defaultdict(int)
    for category, errors in error_categories.items():
        pattern_counts[category] = len(errors)

    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count} files")

    return error_categories, priorities

if __name__ == "__main__":
    main()