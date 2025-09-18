#!/usr/bin/env python3
"""
Automated script to detect and fix unterminated string errors in Python files.
Focuses on test files to improve syntax error count.
"""

import ast
import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict
import argparse

class UnterminatedStringFixer:
    def __init__(self, dry_run=True, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def detect_unterminated_strings(self, content: str) -> List[Tuple[int, str, str]]:
        """Detect unterminated string patterns and suggest fixes."""
        fixes = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line_num = i + 1

            # Pattern 1: Single quote at end of line without closing quote
            if re.search(r"[^'\"]*'[^'\"]*$", line) and not re.search(r"[^'\"]*'[^'\"]*'", line):
                if not line.strip().endswith('\\'):  # Not an escaped quote
                    fixes.append((line_num, line, line + "'"))

            # Pattern 2: Double quote at end of line without closing quote
            elif re.search(r'[^\'\"]*"[^\'\"]*$', line) and not re.search(r'[^\'\"]*"[^\'\"]*"', line):
                if not line.strip().endswith('\\'):  # Not an escaped quote
                    fixes.append((line_num, line, line + '"'))

            # Pattern 3: Unclosed f-string
            elif re.search(r"f'[^']*$", line) or re.search(r'f"[^"]*$', line):
                if line.count("'") % 2 == 1 and "f'" in line:
                    fixes.append((line_num, line, line + "'"))
                elif line.count('"') % 2 == 1 and 'f"' in line:
                    fixes.append((line_num, line, line + '"'))

            # Pattern 4: Triple quote docstrings that are not closed
            elif '"""' in line and line.count('"""') == 1:
                # Look ahead to see if there's a closing triple quote in next few lines
                has_closing = False
                for j in range(i + 1, min(i + 10, len(lines))):
                    if '"""' in lines[j]:
                        has_closing = True
                        break
                if not has_closing and line.strip().endswith('"""'):
                    # This might be a single line docstring missing opening quotes
                    content_before_quotes = line[:line.rfind('"""')]
                    if content_before_quotes.strip() and not content_before_quotes.strip().startswith('"""'):
                        fixes.append((line_num, line, content_before_quotes + '"""' + line[line.rfind('"""') + 3:] + '"""'))

        return fixes

    def apply_fixes(self, file_path: str, fixes: List[Tuple[int, str, str]]) -> bool:
        """Apply fixes to a file."""
        if not fixes:
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            # Apply fixes from bottom to top to maintain line numbers
            for line_num, old_line, new_line in reversed(fixes):
                if line_num <= len(lines) and lines[line_num - 1] == old_line:
                    lines[line_num - 1] = new_line
                    self.fixes_applied += 1

            new_content = '\n'.join(lines)

            # Validate the fix doesn't break syntax
            try:
                ast.parse(new_content)
                syntax_valid = True
            except SyntaxError:
                syntax_valid = False

            if syntax_valid:
                if not self.dry_run:
                    # Backup original file
                    shutil.copy2(file_path, file_path + '.backup')

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                if self.verbose:
                    print(f"FIXED {len(fixes)} issues in {file_path}")
                return True
            else:
                if self.verbose:
                    print(f"WARNING: Fixes would break syntax in {file_path}, skipping")
                return False

        except Exception as e:
            if self.verbose:
                print(f"ERROR processing {file_path}: {e}")
            return False

    def has_syntax_error(self, file_path: str) -> bool:
        """Check if file has syntax errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return False
        except SyntaxError:
            return True
        except Exception:
            return False

    def fix_file(self, file_path: str) -> bool:
        """Fix unterminated strings in a single file."""
        self.files_processed += 1

        if not self.has_syntax_error(file_path):
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            if self.verbose:
                print(f"ERROR: Cannot read {file_path}: {e}")
            return False

        fixes = self.detect_unterminated_strings(content)

        if fixes:
            if self.apply_fixes(file_path, fixes):
                self.files_fixed += 1
                return True

        return False

    def fix_directory(self, directory: str, pattern: str = "test_*.py") -> Dict[str, int]:
        """Fix all matching files in directory."""
        results = {
            'files_processed': 0,
            'files_fixed': 0,
            'fixes_applied': 0
        }

        for root, dirs, files in os.walk(directory):
            # Skip non-relevant directories
            if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.venv']):
                continue

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)

                    # Focus on test files first
                    if pattern == "test_*.py" and not file.startswith('test_'):
                        continue

                    if self.fix_file(file_path):
                        results['files_fixed'] += 1

                    results['files_processed'] += 1

        results['fixes_applied'] = self.fixes_applied
        return results

def main():
    parser = argparse.ArgumentParser(description='Fix unterminated string errors in Python files')
    parser.add_argument('--directory', '-d', default='.', help='Directory to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--pattern', default='test_*.py', help='File pattern to match')

    args = parser.parse_args()

    fixer = UnterminatedStringFixer(dry_run=args.dry_run, verbose=args.verbose)

    print(f"Fixing unterminated string errors in {args.directory}")
    print(f"Pattern: {args.pattern}")
    print(f"Dry run: {args.dry_run}")
    print("-" * 50)

    results = fixer.fix_directory(args.directory, args.pattern)

    print(f"\nResults:")
    print(f"Files processed: {results['files_processed']}")
    print(f"Files fixed: {results['files_fixed']}")
    print(f"Total fixes applied: {results['fixes_applied']}")

    if args.dry_run:
        print("\nThis was a dry run. Use --dry-run=false to apply fixes.")

if __name__ == "__main__":
    main()