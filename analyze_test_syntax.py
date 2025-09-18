#!/usr/bin/env python3
"""
Test file syntax analysis script for P0 crisis investigation
"""
import ast
import os
import glob
from pathlib import Path
from collections import defaultdict
import traceback

def categorize_test_file(filepath):
    """Categorize test file by business priority"""
    filepath_lower = filepath.lower()

    # WebSocket tests (90% platform value)
    if any(term in filepath_lower for term in ['websocket', 'ws_', 'socket', 'events']):
        return "websocket"

    # Agent tests (15% coverage crisis)
    if any(term in filepath_lower for term in ['agent', 'supervisor', 'orchestrat', 'execution']):
        return "agent"

    # Auth tests (Golden Path critical)
    if any(term in filepath_lower for term in ['auth', 'login', 'jwt', 'token', 'session']):
        return "auth"

    # Integration tests
    if any(term in filepath_lower for term in ['integration', 'e2e', 'end_to_end']):
        return "integration"

    # Mission critical
    if 'mission_critical' in filepath_lower or 'critical' in filepath_lower:
        return "mission_critical"

    # Unit tests (default)
    return "unit"

def analyze_syntax_error(filepath):
    """Analyze the type of syntax error in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            ast.parse(content)
            return None, None  # No error
        except SyntaxError as e:
            error_type = "unknown"

            # Categorize error types
            if "unterminated string literal" in str(e).lower():
                error_type = "unterminated_string"
            elif "unterminated f-string" in str(e).lower():
                error_type = "unterminated_fstring"
            elif "unexpected indent" in str(e).lower() or "unindent" in str(e).lower():
                error_type = "indentation"
            elif "invalid syntax" in str(e).lower():
                error_type = "invalid_syntax"
            else:
                error_type = "other_syntax"

            return error_type, f"Line {e.lineno}: {e.msg}"

    except Exception as e:
        return "file_error", str(e)

def main():
    base_path = Path(".")

    # Find all test files
    test_patterns = [
        "**/test*.py",
        "**/*test.py",
        "**/tests/**/*.py"
    ]

    test_files = set()
    for pattern in test_patterns:
        test_files.update(glob.glob(str(base_path / pattern), recursive=True))

    print(f"Found {len(test_files)} test files")

    # Analysis results
    results = {
        'by_category': defaultdict(list),
        'by_error_type': defaultdict(list),
        'error_details': {},
        'clean_files': []
    }

    # Analyze each file
    for i, filepath in enumerate(sorted(test_files)):
        if i % 100 == 0:
            print(f"Analyzed {i}/{len(test_files)} files...")

        category = categorize_test_file(filepath)
        error_type, error_msg = analyze_syntax_error(filepath)

        results['by_category'][category].append(filepath)

        if error_type:
            results['by_error_type'][error_type].append(filepath)
            results['error_details'][filepath] = error_msg
        else:
            results['clean_files'].append(filepath)

    # Print summary
    print("\n" + "="*80)
    print("BUSINESS PRIORITY CATEGORIZATION")
    print("="*80)

    for category, files in sorted(results['by_category'].items()):
        error_count = sum(1 for f in files if f in results['error_details'])
        print(f"{category.upper()}: {len(files)} files ({error_count} with errors)")

    print("\n" + "="*80)
    print("ERROR TYPE BREAKDOWN")
    print("="*80)

    total_errors = len(results['error_details'])
    for error_type, files in sorted(results['by_error_type'].items()):
        percentage = (len(files) / total_errors * 100) if total_errors > 0 else 0
        print(f"{error_type}: {len(files)} files ({percentage:.1f}%)")

    print(f"\nClean files: {len(results['clean_files'])}")
    print(f"Files with errors: {total_errors}")
    print(f"Total files: {len(test_files)}")

    # Sample errors for each category
    print("\n" + "="*80)
    print("SAMPLE ERRORS BY BUSINESS PRIORITY")
    print("="*80)

    for category in ['websocket', 'agent', 'auth', 'mission_critical']:
        files_in_category = results['by_category'][category]
        error_files = [f for f in files_in_category if f in results['error_details']]

        if error_files:
            print(f"\n{category.upper()} - Sample errors:")
            for filepath in error_files[:3]:  # Show first 3 errors
                print(f"  {filepath}")
                print(f"    Error: {results['error_details'][filepath]}")

    # Sample errors by type
    print("\n" + "="*80)
    print("SAMPLE ERRORS BY TYPE")
    print("="*80)

    for error_type in ['unterminated_string', 'unterminated_fstring', 'indentation']:
        if error_type in results['by_error_type']:
            files = results['by_error_type'][error_type]
            print(f"\n{error_type.upper()} - Sample files:")
            for filepath in files[:3]:
                print(f"  {filepath}")
                print(f"    Error: {results['error_details'][filepath]}")

if __name__ == "__main__":
    main()