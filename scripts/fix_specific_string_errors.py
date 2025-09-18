#!/usr/bin/env python3
"""
Targeted script to fix specific unterminated string patterns in test files.
"""

import ast
import os
import re
import shutil
from pathlib import Path

class TargetedStringFixer:
    def __init__(self, dry_run=True, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

    def fix_specific_patterns(self, content: str) -> str:
        """Fix specific unterminated string patterns."""
        lines = content.split('\n')
        modified = False

        for i, line in enumerate(lines):
            original_line = line

            # Pattern 1: Fix missing opening quote in docstrings
            if re.match(r'^\s*""[^"].*$', line):
                line = re.sub(r'^(\s*)""([^"].*)$', r'\1"""\2', line)

            # Pattern 2: Fix missing closing quote in return values
            if re.search(r'return_value="[^"]*\)$', line):
                line = re.sub(r'return_value="([^"]*)\)$', r'return_value="\1")', line)

            # Pattern 3: Fix missing closing quotes in variable assignments
            if re.search(r'=\s*"[^"]*\]"?$', line):
                line = re.sub(r'=\s*"([^"]*)\]"?$', r'= "\1"]"', line)

            # Pattern 4: Fix malformed JSON strings
            if re.search(r'json=\{[^}]*$', line) and not line.strip().endswith('}'):
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('"'):
                    line = line + '{'

            # Pattern 5: Fix missing closing quotes in assert messages
            if re.search(r'assert.*"[^"]*$', line) and not line.strip().endswith('"'):
                line = line + '"'

            # Pattern 6: Fix missing quotes in dictionary access
            if re.search(r'"[^"]*\s+in\s+[^"]*"?$', line):
                line = re.sub(r'"([^"]*)\s+in\s+([^"]*)"?$', r'"\1" in \2', line)

            # Pattern 7: Fix missing closing quotes in headers
            if 'headers=' in line and re.search(r'"[^"]*\}[^"]*$', line):
                line = re.sub(r'"([^"]*\})[^"]*$', r'"\1"', line)

            if line != original_line:
                lines[i] = line
                modified = True
                if self.verbose:
                    print(f"Fixed line {i+1}: '{original_line.strip()}' -> '{line.strip()}'")

        return '\n'.join(lines) if modified else content

    def fix_file(self, file_path: str) -> bool:
        """Fix a single file."""
        self.files_processed += 1

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            if self.verbose:
                print(f"ERROR: Cannot read {file_path}: {e}")
            return False

        # Check if file already has valid syntax
        try:
            ast.parse(original_content)
            return False  # No fix needed
        except SyntaxError as e:
            if 'unterminated string literal' not in str(e).lower() and 'EOL while scanning string literal' not in str(e):
                return False  # Not an unterminated string error

        # Apply fixes
        fixed_content = self.fix_specific_patterns(original_content)

        if fixed_content == original_content:
            return False  # No changes made

        # Validate the fix
        try:
            ast.parse(fixed_content)
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False

        if syntax_valid:
            if not self.dry_run:
                # Backup original file
                shutil.copy2(file_path, file_path + '.backup')

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

            if self.verbose:
                print(f"FIXED: {file_path}")

            self.files_fixed += 1
            self.fixes_applied += 1
            return True
        else:
            if self.verbose:
                print(f"WARNING: Fixes would break syntax in {file_path}, skipping")
            return False

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Fix specific unterminated string errors')
    parser.add_argument('--directory', '-d', default='.', help='Directory to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    fixer = TargetedStringFixer(dry_run=args.dry_run, verbose=args.verbose)

    print(f"Fixing specific unterminated string errors in {args.directory}")
    print(f"Dry run: {args.dry_run}")
    print("-" * 50)

    # Process test files with unterminated string errors
    files_processed = 0
    files_fixed = 0

    for root, dirs, files in os.walk(args.directory):
        # Skip backup directories
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.venv', 'backup']):
            continue

        for file in files:
            if file.endswith('.py') and file.startswith('test_'):
                file_path = os.path.join(root, file)
                files_processed += 1

                if fixer.fix_file(file_path):
                    files_fixed += 1

    print(f"\nResults:")
    print(f"Files processed: {files_processed}")
    print(f"Files fixed: {files_fixed}")
    print(f"Total fixes applied: {fixer.fixes_applied}")

    if args.dry_run:
        print("\nThis was a dry run. Use without --dry-run to apply fixes.")

if __name__ == "__main__":
    main()