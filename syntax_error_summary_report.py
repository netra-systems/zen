#!/usr/bin/env python3
"""
Syntax Error Summary Report - Final status of test file corruption crisis
"""

import ast
import os
from pathlib import Path
import json

def check_syntax_basic(file_path):
    """Check a single file for syntax errors without fancy output."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content, filename=str(file_path))
        return None  # No error
    except Exception as e:
        return str(e)

def main():
    """Generate comprehensive syntax error report"""

    # Focus on critical test directories
    test_patterns = [
        "tests/e2e/test_websocket*.py",
        "tests/mission_critical/*.py",
        "tests/integration/test_websocket*.py",
        "tests/integration/test_*websocket*.py"
    ]

    root = Path(".")
    all_files = set()

    # Collect all files
    for pattern in test_patterns:
        all_files.update(root.glob(pattern))

    print("P0 TEST INFRASTRUCTURE CRISIS - SYNTAX ERROR SUMMARY")
    print("="*80)
    print(f"Total critical test files scanned: {len(all_files)}")
    print()

    # Categories for error analysis
    error_categories = {
        'unterminated_string': [],
        'invalid_decimal': [],
        'mismatched_brackets': [],
        'invalid_syntax': [],
        'other_errors': [],
        'files_fixed': []
    }

    files_with_errors = 0
    files_working = 0

    for file_path in sorted(all_files):
        if file_path.suffix == '.py' and "__pycache__" not in str(file_path):
            error = check_syntax_basic(file_path)

            if error:
                files_with_errors += 1

                # Categorize the error
                if 'unterminated string literal' in error:
                    error_categories['unterminated_string'].append(str(file_path))
                elif 'invalid decimal literal' in error:
                    error_categories['invalid_decimal'].append(str(file_path))
                elif 'does not match opening' in error or 'closing parenthesis' in error:
                    error_categories['mismatched_brackets'].append(str(file_path))
                elif 'invalid syntax' in error:
                    error_categories['invalid_syntax'].append(str(file_path))
                else:
                    error_categories['other_errors'].append(str(file_path))
            else:
                files_working += 1
                error_categories['files_fixed'].append(str(file_path))

    # Generate summary
    print(f"CRITICAL STATUS:")
    print(f"  Files with syntax errors: {files_with_errors}")
    print(f"  Files working correctly: {files_working}")
    print(f"  Total files processed: {len(all_files)}")
    print()

    success_rate = (files_working / len(all_files)) * 100 if all_files else 0
    print(f"SYNTAX SUCCESS RATE: {success_rate:.1f}%")
    print()

    print("ERROR BREAKDOWN BY CATEGORY:")
    print("-" * 40)
    for category, files in error_categories.items():
        if files and category != 'files_fixed':
            print(f"{category.replace('_', ' ').title()}: {len(files)} files")
            # Show first 3 examples
            for file in files[:3]:
                print(f"  - {file}")
            if len(files) > 3:
                print(f"  ... and {len(files) - 3} more")
            print()

    print("BUSINESS IMPACT ASSESSMENT:")
    print("-" * 40)
    if files_with_errors > 100:
        print("CRITICAL: P0 infrastructure crisis - test collection completely blocked")
        print("Impact: $500K+ ARR at risk - cannot validate Golden Path functionality")
    elif files_with_errors > 50:
        print("HIGH: Major test infrastructure issues - significant coverage gaps")
        print("Impact: Core WebSocket functionality cannot be validated")
    elif files_with_errors > 10:
        print("MEDIUM: Test infrastructure problems - some coverage gaps")
        print("Impact: Limited testing capability for WebSocket events")
    else:
        print("LOW: Minor test infrastructure issues")
        print("Impact: Most critical functionality can be tested")

    print()
    print("RECOMMENDED ACTIONS:")
    print("-" * 40)

    if error_categories['unterminated_string']:
        print(f"1. FIX UNTERMINATED STRINGS ({len(error_categories['unterminated_string'])} files)")
        print("   - Most files start with single quote character")
        print("   - Need to add proper docstring quotes or remove quotes")

    if error_categories['invalid_decimal']:
        print(f"2. FIX INVALID DECIMAL LITERALS ({len(error_categories['invalid_decimal'])} files)")
        print("   - Likely issues with numeric formatting in f-strings")
        print("   - Check variable substitution patterns")

    if error_categories['mismatched_brackets']:
        print(f"3. FIX MISMATCHED BRACKETS ({len(error_categories['mismatched_brackets'])} files)")
        print("   - Parentheses, brackets, braces don't match")
        print("   - Need careful manual review")

    print()
    print("NEXT STEPS:")
    print("1. Focus on fixing unterminated string literal files first (highest impact)")
    print("2. Use manual inspection for complex bracket mismatches")
    print("3. Create targeted fixers for each error category")
    print("4. Re-run syntax validation after each batch of fixes")

    # Output machine-readable summary
    summary = {
        'total_files': len(all_files),
        'files_with_errors': files_with_errors,
        'files_working': files_working,
        'success_rate': success_rate,
        'error_categories': {k: len(v) for k, v in error_categories.items()},
        'most_critical_files': error_categories['unterminated_string'][:10]
    }

    with open('syntax_error_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nDetailed summary written to: syntax_error_summary.json")
    return files_with_errors

if __name__ == "__main__":
    error_count = main()
    exit(1 if error_count > 0 else 0)