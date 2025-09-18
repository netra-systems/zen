#!/usr/bin/env python3
"""
P0 CRITICAL: Automated Test File Syntax Error Repair Tool
Fixes systematic syntax errors in test files that prevent collection and execution.
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import argparse

class TestFileSyntaxRepair:
    """Repairs common syntax errors in test files."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.fixed_files = []
        self.failed_files = []
        self.error_patterns = {
            'unterminated_string': 0,
            'misplaced_quotes': 0,
            'malformed_fstring': 0,
            'indentation': 0,
            'other': 0
        }

    def check_syntax(self, filepath: Path) -> Tuple[bool, str]:
        """Check if a file has syntax errors."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            compile(content, str(filepath), 'exec')
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def fix_unterminated_strings(self, content: str) -> str:
        """Fix common unterminated string patterns."""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Pattern 1: String with extra colon at end like "agent_started":"
            if re.search(r'"[^"]+":"$', line):
                line = re.sub(r'":"$', '"', line)
                self.error_patterns['unterminated_string'] += 1

            # Pattern 2: Quotes in middle of words like conf"iguration
            if re.search(r'\w"\w', line):
                line = re.sub(r'(\w)"(\w)', r'\1\2', line)
                self.error_patterns['misplaced_quotes'] += 1

            # Pattern 3: Missing opening quote in f-strings like fWarning:
            if re.search(r'print\(f[A-Z]', line):
                line = re.sub(r'print\(f([A-Z])', r'print(f"\1', line)
                self.error_patterns['malformed_fstring'] += 1

            # Pattern 4: Malformed f-strings missing quotes
            if re.search(r'f"[^"]*\{[^}]+\}[^"]*",', line):
                # Check for missing closing quote
                if line.count('"') % 2 != 0:
                    line = line.rstrip(',') + '",'
                    self.error_patterns['malformed_fstring'] += 1

            # Pattern 5: Lists with malformed strings like [agent_completed, f"inal_report]
            if re.search(r'\[.*f"[^"]+\]', line):
                # Fix split f-strings
                line = re.sub(r'f"(\w+)', r'"f\1"', line)
                self.error_patterns['malformed_fstring'] += 1

            # Pattern 6: Fix unterminated strings in comparisons
            if re.search(r'!= "[^"]+":"', line):
                line = re.sub(r'":"$', '"', line)
                self.error_patterns['unterminated_string'] += 1

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_file(self, filepath: Path) -> bool:
        """Attempt to fix syntax errors in a single file."""
        is_valid, error = self.check_syntax(filepath)
        if is_valid:
            return True

        print(f"Fixing {filepath}: {error}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Apply fixes
            fixed_content = self.fix_unterminated_strings(content)

            # Verify the fix
            try:
                compile(fixed_content, str(filepath), 'exec')

                if not self.dry_run:
                    # Backup original
                    backup_path = filepath.with_suffix('.py.backup')
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    # Write fixed content
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)

                self.fixed_files.append(filepath)
                print(f"  [FIXED] {filepath}")
                return True

            except SyntaxError as e:
                self.failed_files.append((filepath, str(e)))
                print(f"  [FAILED] Could not auto-fix {filepath}: {e}")
                return False

        except Exception as e:
            self.failed_files.append((filepath, str(e)))
            print(f"  [ERROR] Error processing {filepath}: {e}")
            return False

    def scan_and_fix(self, root_dir: str, pattern: str = "**/test_*.py") -> Dict:
        """Scan directory for test files with syntax errors and fix them."""
        root_path = Path(root_dir)
        test_files = list(root_path.glob(pattern))

        print(f"Scanning {len(test_files)} test files for syntax errors...")

        error_files = []
        for filepath in test_files:
            is_valid, error = self.check_syntax(filepath)
            if not is_valid:
                error_files.append(filepath)

        print(f"Found {len(error_files)} files with syntax errors")

        if error_files:
            print("\nAttempting to fix errors...")
            for filepath in error_files:
                self.fix_file(filepath)

        return {
            'total_scanned': len(test_files),
            'errors_found': len(error_files),
            'fixed': len(self.fixed_files),
            'failed': len(self.failed_files),
            'error_patterns': self.error_patterns
        }

    def prioritize_critical_files(self, root_dir: str) -> None:
        """Fix critical test files first (WebSocket, agent, auth)."""
        critical_patterns = [
            "**/test_*websocket*.py",
            "**/test_*agent*.py",
            "**/test_*auth*.py",
            "**/mission_critical/*.py"
        ]

        print("Fixing CRITICAL test files first (WebSocket, Agent, Auth)...")
        for pattern in critical_patterns:
            self.scan_and_fix(root_dir, pattern)

def main():
    parser = argparse.ArgumentParser(description='Repair syntax errors in test files')
    parser.add_argument('--root', default='.', help='Root directory to scan')
    parser.add_argument('--apply', action='store_true', help='Actually apply fixes (default is dry-run)')
    parser.add_argument('--critical', action='store_true', help='Fix critical files first')

    args = parser.parse_args()

    repair = TestFileSyntaxRepair(dry_run=not args.apply)

    if args.critical:
        repair.prioritize_critical_files(args.root)
    else:
        results = repair.scan_and_fix(args.root)

        print("\n=== Repair Summary ===")
        print(f"Total files scanned: {results['total_scanned']}")
        print(f"Files with errors: {results['errors_found']}")
        print(f"Files fixed: {results['fixed']}")
        print(f"Files failed: {results['failed']}")
        print("\n=== Error Pattern Summary ===")
        for pattern, count in results['error_patterns'].items():
            if count > 0:
                print(f"  {pattern}: {count}")

        if repair.failed_files:
            print("\n=== Failed Files (Need Manual Fix) ===")
            for filepath, error in repair.failed_files[:10]:
                print(f"  {filepath}: {error}")

        if not args.apply:
            print("\n⚠️  DRY RUN MODE - No files were actually modified")
            print("Run with --apply to actually fix the files")

if __name__ == '__main__':
    main()