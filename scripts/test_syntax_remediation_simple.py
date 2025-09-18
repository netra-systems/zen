#!/usr/bin/env python3
"""
Test Syntax Remediation Tool - Simple Version
============================================

Automated fixing for common syntax errors in Python test files.
Handles the 321 identified syntax errors in the netra-apex test suite.
"""

import ast
import os
import sys
import glob
import re
import shutil
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

def analyze_all_test_files(root_dir="."):
    """Analyze all test files for syntax errors."""
    print("Analyzing syntax errors across test files...")

    test_files = glob.glob(os.path.join(root_dir, 'tests/**/*.py'), recursive=True)
    syntax_errors = []
    error_patterns = defaultdict(list)

    print(f"Found {len(test_files)} test files to analyze")

    for i, file_path in enumerate(test_files):
        if i % 500 == 0:
            print(f"  Processed {i}/{len(test_files)} files...")

        rel_path = os.path.relpath(file_path, root_dir)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            syntax_errors.append((rel_path, str(e), e.lineno if hasattr(e, 'lineno') else None))
            categorize_error(error_patterns, rel_path, str(e))
        except Exception as e:
            syntax_errors.append((rel_path, f'Parse error: {str(e)}', None))
            error_patterns['parse_error'].append(rel_path)

    print(f"\nAnalysis complete: {len(syntax_errors)} files with syntax errors")
    print_error_summary(error_patterns)

    return syntax_errors, dict(error_patterns)

def categorize_error(error_patterns, file_path, error_msg):
    """Categorize error by pattern for targeted fixing."""
    error_lower = error_msg.lower()

    if 'expected an indented block' in error_lower:
        error_patterns['indentation'].append(file_path)
    elif 'unexpected indent' in error_lower:
        error_patterns['unexpected_indent'].append(file_path)
    elif 'unterminated string' in error_lower or 'eol while scanning string' in error_lower:
        error_patterns['unterminated_string'].append(file_path)
    elif 'invalid syntax' in error_lower and any(bracket in error_lower for bracket in ['[', ']', '{', '}', '(', ')']):
        error_patterns['bracket_mismatch'].append(file_path)
    else:
        error_patterns['other'].append(file_path)

def print_error_summary(error_patterns):
    """Print summary of error patterns found."""
    print("\nError Pattern Summary:")
    total_files = sum(len(files) for files in error_patterns.values())

    for pattern, files in sorted(error_patterns.items(), key=lambda x: len(x[1]), reverse=True):
        percentage = (len(files) / total_files * 100) if total_files > 0 else 0
        print(f"  {pattern:20}: {len(files):3} files ({percentage:5.1f}%)")

        # Show critical mission files if any
        critical_files = [f for f in files if 'mission_critical' in f]
        if critical_files:
            print(f"    CRITICAL mission files: {len(critical_files)}")
            for cf in critical_files[:3]:
                print(f"      - {cf}")
            if len(critical_files) > 3:
                print(f"      ... and {len(critical_files) - 3} more")

def fix_indentation_errors(root_dir, file_paths):
    """Fix files with indentation errors."""
    print(f"Fixing indentation errors in {len(file_paths)} files...")
    fixed = []

    for file_path in file_paths:
        full_path = os.path.join(root_dir, file_path)
        if fix_indentation_single_file(full_path):
            fixed.append(file_path)
            print(f"  Fixed: {file_path}")
        else:
            print(f"  FAILED: {file_path}")

    return fixed

def fix_indentation_single_file(file_path):
    """Fix indentation errors in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        fixed_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check for control structures that need indented blocks
            if (stripped.endswith(':') and
                any(stripped.startswith(keyword) for keyword in
                    ['if ', 'for ', 'while ', 'def ', 'class ', 'try:', 'except', 'else:', 'elif ', 'finally:', 'with ', 'async def '])):

                fixed_lines.append(line)

                # Check next line for proper indentation
                if i + 1 < len(lines):
                    next_line = lines[i + 1]

                    # If next line is not indented and not empty/comment
                    if (next_line.strip() and
                        not next_line.strip().startswith('#') and
                        not next_line.startswith('    ') and
                        not next_line.startswith('\t')):

                        # Calculate proper indentation
                        current_indent = len(line) - len(line.lstrip())
                        proper_indent = ' ' * (current_indent + 4)

                        # Fix the indentation
                        next_line = proper_indent + next_line.lstrip()
                        lines[i + 1] = next_line
            else:
                fixed_lines.append(line)

        # Write fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        # Verify fix worked
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)

        return True

    except Exception as e:
        print(f"    Error fixing {file_path}: {e}")
        return False

def fix_unexpected_indent_errors(root_dir, file_paths):
    """Fix files with unexpected indent errors."""
    print(f"Fixing unexpected indent errors in {len(file_paths)} files...")
    fixed = []

    for file_path in file_paths:
        full_path = os.path.join(root_dir, file_path)
        if fix_unexpected_indent_single_file(full_path):
            fixed.append(file_path)
            print(f"  Fixed: {file_path}")
        else:
            print(f"  FAILED: {file_path}")

    return fixed

def fix_unexpected_indent_single_file(file_path):
    """Fix unexpected indent errors in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        fixed_lines = []
        for i, line in enumerate(lines):
            # Handle unexpected indents - simple approach
            if line.strip() and i > 0:
                prev_line = lines[i-1].strip()
                current_indent = len(line) - len(line.lstrip())

                # If previous line doesn't end with colon but current line is indented
                if not prev_line.endswith(':') and current_indent > 0 and not prev_line.startswith('"""') and not prev_line.startswith("'''"):
                    # Check if this is actually a comment that should be indented
                    if not line.strip().startswith('#'):
                        # Remove unexpected indentation
                        fixed_lines.append(line.lstrip())
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        # Write fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

        # Verify fix worked
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)

        return True

    except Exception as e:
        print(f"    Error fixing {file_path}: {e}")
        return False

def fix_unterminated_string_errors(root_dir, file_paths):
    """Fix files with unterminated string literal errors."""
    print(f"Fixing unterminated string errors in {len(file_paths)} files...")
    fixed = []

    for file_path in file_paths:
        full_path = os.path.join(root_dir, file_path)
        if fix_unterminated_string_single_file(full_path):
            fixed.append(file_path)
            print(f"  Fixed: {file_path}")
        else:
            print(f"  FAILED: {file_path}")

    return fixed

def fix_unterminated_string_single_file(file_path):
    """Fix unterminated string literals in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Common patterns for unterminated strings
        original_content = content

        # Fix missing closing quotes at end of lines
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Look for unterminated strings
            if '"' in line and line.count('"') % 2 == 1:
                # Odd number of quotes - likely unterminated
                line = line + '"'
            elif "'" in line and line.count("'") % 2 == 1 and '"""' not in line and "'''" not in line:
                # Odd number of single quotes - likely unterminated
                line = line + "'"

            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # Only write if we made changes
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # Verify fix worked
        ast.parse(content)
        return True

    except Exception as e:
        print(f"    Error fixing {file_path}: {e}")
        return False

def fix_bracket_mismatch_errors(root_dir, file_paths):
    """Fix files with bracket/parenthesis mismatch errors."""
    print(f"Fixing bracket mismatch errors in {len(file_paths)} files...")
    fixed = []

    for file_path in file_paths:
        full_path = os.path.join(root_dir, file_path)
        if fix_bracket_mismatch_single_file(full_path):
            fixed.append(file_path)
            print(f"  Fixed: {file_path}")
        else:
            print(f"  FAILED: {file_path}")

    return fixed

def fix_bracket_mismatch_single_file(file_path):
    """Fix bracket mismatch errors in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Common bracket mismatch patterns
        fixes = [
            # [ ) should be [ ]
            (r'\[\s*\)', '[]'),
            # { ) should be { }
            (r'\{\s*\)', '{}'),
            # ( ] should be ( )
            (r'\(\s*\]', '()'),
            # ( } should be ( )
            (r'\(\s*\}', '()'),
            # [ } should be [ ]
            (r'\[\s*\}', '[]'),
            # { ] should be { }
            (r'\{\s*\]', '{}'),
        ]

        original_content = content
        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content)

        # Only write if we made changes
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # Verify fix worked
        ast.parse(content)
        return True

    except Exception as e:
        print(f"    Error fixing {file_path}: {e}")
        return False

def create_backup(root_dir, file_paths):
    """Create backup of files before fixing."""
    backup_dir = os.path.join(root_dir, "backups", f"syntax_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    print(f"Creating backup in {backup_dir}")

    for file_path in file_paths:
        full_path = os.path.join(root_dir, file_path)
        if os.path.exists(full_path):
            backup_path = os.path.join(backup_dir, file_path)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(full_path, backup_path)

    return backup_dir

def prioritize_files(patterns):
    """Prioritize files for fixing based on business impact."""

    priority_files = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    }

    for pattern_name, files in patterns.items():
        for file_path in files:
            if 'mission_critical' in file_path:
                priority_files['critical'].append((pattern_name, file_path))
            elif any(keyword in file_path for keyword in ['e2e', 'integration', 'websocket']):
                priority_files['high'].append((pattern_name, file_path))
            elif any(keyword in file_path for keyword in ['agent', 'auth', 'database']):
                priority_files['medium'].append((pattern_name, file_path))
            else:
                priority_files['low'].append((pattern_name, file_path))

    return priority_files

def main():
    parser = argparse.ArgumentParser(description="Test Syntax Remediation Tool")
    parser.add_argument("--analyze", action="store_true", help="Analyze syntax errors only")
    parser.add_argument("--fix-all", action="store_true", help="Fix all syntax errors")
    parser.add_argument("--fix-pattern", choices=["indentation", "unexpected_indent", "unterminated_string", "bracket_mismatch"],
                       help="Fix specific error pattern")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup")
    parser.add_argument("--root-dir", default=".", help="Root directory to scan")

    args = parser.parse_args()

    if not any([args.analyze, args.fix_all, args.fix_pattern]):
        # Default to analysis
        args.analyze = True

    root_dir = args.root_dir

    if args.analyze:
        analyze_all_test_files(root_dir)
        return

    # Get current state
    errors, patterns = analyze_all_test_files(root_dir)

    if not patterns:
        print("No syntax errors found!")
        return

    # Show prioritization
    priority_files = prioritize_files(patterns)
    print("\nFile Priority Breakdown:")
    for priority, file_list in priority_files.items():
        print(f"  {priority.upper()}: {len(file_list)} files")

    if args.fix_all:
        # Create backup
        if not args.no_backup:
            all_files = []
            for files in patterns.values():
                all_files.extend(files)
            backup_dir = create_backup(root_dir, list(set(all_files)))

        results = {}

        # Fix patterns in priority order
        fix_functions = {
            'indentation': fix_indentation_errors,
            'unexpected_indent': fix_unexpected_indent_errors,
            'unterminated_string': fix_unterminated_string_errors,
            'bracket_mismatch': fix_bracket_mismatch_errors,
        }

        for pattern_name in ['indentation', 'unexpected_indent', 'unterminated_string', 'bracket_mismatch']:
            if pattern_name in patterns:
                print(f"\nProcessing {pattern_name} errors...")
                fixed_files = fix_functions[pattern_name](root_dir, patterns[pattern_name])
                results[pattern_name] = fixed_files

        # Handle remaining files
        if 'other' in patterns:
            print(f"\n{len(patterns['other'])} files with 'other' pattern errors need manual review:")
            for file_path in patterns['other'][:10]:
                print(f"  - {file_path}")
            if len(patterns['other']) > 10:
                print(f"  ... and {len(patterns['other']) - 10} more")

        # Final validation
        print("\nValidating fixes...")
        final_errors, final_patterns = analyze_all_test_files(root_dir)

        total_fixed = sum(len(files) for files in results.values())
        print(f"\nSUMMARY:")
        print(f"  Files originally with errors: {len(errors)}")
        print(f"  Files fixed: {total_fixed}")
        print(f"  Files still with errors: {len(final_errors)}")

    elif args.fix_pattern:
        if args.fix_pattern in patterns:
            if not args.no_backup:
                backup_dir = create_backup(root_dir, patterns[args.fix_pattern])

            fix_functions = {
                'indentation': fix_indentation_errors,
                'unexpected_indent': fix_unexpected_indent_errors,
                'unterminated_string': fix_unterminated_string_errors,
                'bracket_mismatch': fix_bracket_mismatch_errors,
            }

            fixed = fix_functions[args.fix_pattern](root_dir, patterns[args.fix_pattern])
            print(f"Fixed {len(fixed)} files with {args.fix_pattern} errors")
        else:
            print(f"No files found with {args.fix_pattern} pattern")

if __name__ == "__main__":
    main()