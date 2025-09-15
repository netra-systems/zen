#!/usr/bin/env python3
"""
Issue #1024 Emergency Syntax Fix Script

CRITICAL: Emergency script to fix the most critical syntax errors blocking
test collection and Golden Path validation.

This script fixes:
1. Unterminated string literals
2. Unexpected indentation errors
3. Malformed code blocks from failed migrations

Focus: Mission critical tests and core infrastructure files only.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple


class EmergencySyntaxFixer:
    """Emergency syntax error fixer for Issue #1024."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.fixes_applied = 0
        self.files_processed = 0

    def fix_critical_syntax_errors(self):
        """Fix critical syntax errors in mission critical files."""
        print("ISSUE #1024 EMERGENCY SYNTAX REPAIR")
        print("="*50)

        # Focus on mission critical directories first
        critical_dirs = [
            self.project_root / "tests" / "mission_critical",
            self.project_root / "netra_backend" / "tests" / "critical"
        ]

        for test_dir in critical_dirs:
            if test_dir.exists():
                print(f"\nProcessing: {test_dir}")
                self._fix_directory(test_dir)

        print(f"\nEMERGENCY REPAIR COMPLETE:")
        print(f"Files processed: {self.files_processed}")
        print(f"Fixes applied: {self.fixes_applied}")

    def _fix_directory(self, directory: Path):
        """Fix syntax errors in a directory."""
        for file_path in directory.glob("*.py"):
            self._fix_file(file_path)

    def _fix_file(self, file_path: Path):
        """Fix syntax errors in a single file."""
        try:
            self.files_processed += 1

            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Check if file has syntax errors
            try:
                ast.parse(original_content)
                # No syntax errors, skip
                return
            except SyntaxError as e:
                print(f"  Fixing: {file_path.name} (Line {e.lineno}: {e.msg})")

            # Apply emergency fixes
            fixed_content = self._apply_emergency_fixes(original_content, file_path)

            # Verify the fix works
            try:
                ast.parse(fixed_content)
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                self.fixes_applied += 1
                print(f"    SUCCESS: Fixed {file_path.name}")
            except SyntaxError as e:
                print(f"    FAILED: Could not fix {file_path.name} - {e.msg}")

        except Exception as e:
            print(f"  ERROR: Could not process {file_path.name}: {e}")

    def _apply_emergency_fixes(self, content: str, file_path: Path) -> str:
        """Apply emergency syntax fixes to content."""
        lines = content.split('\n')
        fixed_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Fix 1: Remove malformed MIGRATED comments that break syntax
            if '# MIGRATED: Use SSOT unified test runner' in line:
                # Skip the next few lines that are part of the malformed block
                while i < len(lines) and (
                    '# MIGRATED:' in lines[i] or
                    '# python tests/unified_test_runner.py' in lines[i] or
                    'pass  # TODO: Replace with appropriate SSOT' in lines[i]
                ):
                    i += 1
                continue

            # Fix 2: Remove stray 'pass' statements that break indentation
            if line.strip() == 'pass  # TODO: Replace with appropriate SSOT test execution':
                i += 1
                continue

            # Fix 3: Fix unterminated string literals
            line = self._fix_unterminated_strings(line)

            # Fix 4: Fix unexpected indentation by normalizing
            line = self._fix_indentation(line, i, lines)

            fixed_lines.append(line)
            i += 1

        return '\n'.join(fixed_lines)

    def _fix_unterminated_strings(self, line: str) -> str:
        """Fix unterminated string literals."""
        # Pattern: if ('some string without closing quote
        if "if ('" in line and line.count("'") % 2 == 1:
            # Add closing quote and complete the condition
            if line.endswith(" and"):
                line = line.replace(" and", "') and")
            elif not line.endswith("'):"):
                line += "')"

        # Pattern: if ("some string without closing quote
        if 'if ("' in line and line.count('"') % 2 == 1:
            if line.endswith(" and"):
                line = line.replace(" and", '") and')
            elif not line.endswith('"):'):
                line += '")'

        return line

    def _fix_indentation(self, line: str, line_idx: int, all_lines: List[str]) -> str:
        """Fix indentation issues."""
        # If this is an unexpected indent, check if it should be dedented
        if line.startswith('    ') and line_idx > 0:
            prev_line = all_lines[line_idx - 1]
            # If previous line is a comment or doesn't end with ':', dedent
            if prev_line.strip().startswith('#') or not prev_line.rstrip().endswith(':'):
                # Check if this looks like it should be at the same level
                if any(keyword in line for keyword in ['if (', 'def ', 'class ', 'for ', 'while ']):
                    # This might be incorrectly indented
                    stripped = line.lstrip()
                    if prev_line.strip() and not prev_line.strip().startswith('#'):
                        # Match the indentation of the previous non-comment line
                        prev_indent = len(prev_line) - len(prev_line.lstrip())
                        return ' ' * prev_indent + stripped

        return line


def main():
    """Run emergency syntax repair."""
    fixer = EmergencySyntaxFixer()
    fixer.fix_critical_syntax_errors()

    print("\n" + "="*50)
    print("EMERGENCY PHASE COMPLETE")
    print("="*50)
    print("Next steps:")
    print("1. Run syntax assessment test to verify fixes")
    print("2. Run mission critical tests to validate functionality")
    print("3. Proceed with pytest.main() violation fixes")


if __name__ == '__main__':
    main()