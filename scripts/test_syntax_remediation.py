#!/usr/bin/env python3
"""
Comprehensive Test Syntax Remediation Tool
==========================================

This script provides automated fixing for common syntax errors in Python test files.
Designed to handle the 321 identified syntax errors in the netra-apex test suite.

Error Patterns Supported:
1. Indentation errors (125 files) - Missing indentation after if/for/while/def/class
2. Unexpected indent errors (6 files) - Extra indentation
3. Unterminated string literals (25 files) - Missing closing quotes
4. Other syntax errors (165 files) - Various parsing issues

Usage:
    python scripts/test_syntax_remediation.py --analyze          # Analyze errors only
    python scripts/test_syntax_remediation.py --fix-all          # Fix all errors
    python scripts/test_syntax_remediation.py --fix-pattern indentation  # Fix specific pattern
    python scripts/test_syntax_remediation.py --fix-file tests/path/to/file.py  # Fix single file
    python scripts/test_syntax_remediation.py --validate         # Validate fixes
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
from pathlib import Path

class TestSyntaxRemediator:
    """Automated syntax error remediation for Python test files."""

    def __init__(self, root_dir: str = None):
        self.root_dir = root_dir or os.getcwd()
        self.backup_dir = os.path.join(self.root_dir, "backups", f"syntax_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.fixed_files = []
        self.failed_fixes = []

        # Error pattern counters
        self.error_patterns = defaultdict(list)
        self.fix_stats = defaultdict(int)

    def analyze_syntax_errors(self) -> Tuple[List[Tuple], Dict]:
        """Analyze all test files for syntax errors and categorize them."""
        print("🔍 Analyzing syntax errors across test files...")

        test_files = glob.glob(os.path.join(self.root_dir, 'tests/**/*.py'), recursive=True)
        syntax_errors = []

        print(f"📊 Found {len(test_files)} test files to analyze")

        for i, file_path in enumerate(test_files):
            if i % 500 == 0:
                print(f"  Processed {i}/{len(test_files)} files...")

            rel_path = os.path.relpath(file_path, self.root_dir)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                syntax_errors.append((rel_path, str(e), e.lineno if hasattr(e, 'lineno') else None))
                self._categorize_error(rel_path, str(e))
            except Exception as e:
                syntax_errors.append((rel_path, f'Parse error: {str(e)}', None))
                self.error_patterns['parse_error'].append(rel_path)

        print(f"\n✅ Analysis complete: {len(syntax_errors)} files with syntax errors")
        self._print_error_summary()

        return syntax_errors, dict(self.error_patterns)

    def _categorize_error(self, file_path: str, error_msg: str):
        """Categorize error by pattern for targeted fixing."""
        error_lower = error_msg.lower()

        if 'expected an indented block' in error_lower:
            self.error_patterns['indentation'].append(file_path)
        elif 'unexpected indent' in error_lower:
            self.error_patterns['unexpected_indent'].append(file_path)
        elif 'unterminated string' in error_lower or 'eol while scanning string' in error_lower:
            self.error_patterns['unterminated_string'].append(file_path)
        elif 'invalid syntax' in error_lower and any(bracket in error_lower for bracket in ['[', ']', '{', '}', '(', ')']):
            self.error_patterns['bracket_mismatch'].append(file_path)
        elif 'invalid decimal literal' in error_lower:
            self.error_patterns['decimal_literal'].append(file_path)
        elif 'invalid character' in error_lower:
            self.error_patterns['invalid_character'].append(file_path)
        else:
            self.error_patterns['other'].append(file_path)

    def _print_error_summary(self):
        """Print summary of error patterns found."""
        print("\n📋 Error Pattern Summary:")
        total_files = sum(len(files) for files in self.error_patterns.values())

        for pattern, files in sorted(self.error_patterns.items(), key=lambda x: len(x[1]), reverse=True):
            percentage = (len(files) / total_files * 100) if total_files > 0 else 0
            print(f"  {pattern:20}: {len(files):3} files ({percentage:5.1f}%)")

            # Show critical mission files if any
            critical_files = [f for f in files if 'mission_critical' in f]
            if critical_files:
                print(f"    🚨 Critical mission files: {len(critical_files)}")
                for cf in critical_files[:3]:
                    print(f"      - {cf}")
                if len(critical_files) > 3:
                    print(f"      ... and {len(critical_files) - 3} more")

    def fix_indentation_errors(self, file_paths: List[str]) -> List[str]:
        """Fix files with indentation errors."""
        print(f"🔧 Fixing indentation errors in {len(file_paths)} files...")
        fixed = []

        for file_path in file_paths:
            full_path = os.path.join(self.root_dir, file_path)
            if self._fix_indentation_single_file(full_path):
                fixed.append(file_path)
                self.fix_stats['indentation'] += 1

        return fixed

    def _fix_indentation_single_file(self, file_path: str) -> bool:
        """Fix indentation errors in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            fixed_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]

                # Check for control structures that need indented blocks
                stripped = line.strip()
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

                i += 1

            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            # Verify fix worked
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)

            return True

        except Exception as e:
            print(f"  ❌ Failed to fix {file_path}: {e}")
            return False

    def fix_unexpected_indent_errors(self, file_paths: List[str]) -> List[str]:
        """Fix files with unexpected indent errors."""
        print(f"🔧 Fixing unexpected indent errors in {len(file_paths)} files...")
        fixed = []

        for file_path in file_paths:
            full_path = os.path.join(self.root_dir, file_path)
            if self._fix_unexpected_indent_single_file(full_path):
                fixed.append(file_path)
                self.fix_stats['unexpected_indent'] += 1

        return fixed

    def _fix_unexpected_indent_single_file(self, file_path: str) -> bool:
        """Fix unexpected indent errors in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            fixed_lines = []
            for i, line in enumerate(lines):
                # Try to detect and fix common unexpected indent issues
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    # Line is properly aligned
                    fixed_lines.append(line)
                elif line.strip() and i > 0:
                    # Check if this line's indentation makes sense
                    prev_line = lines[i-1].strip()
                    current_indent = len(line) - len(line.lstrip())

                    # If previous line doesn't end with colon but current line is indented
                    if not prev_line.endswith(':') and current_indent > 0:
                        # Remove unexpected indentation
                        fixed_lines.append(line.lstrip())
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
            print(f"  ❌ Failed to fix {file_path}: {e}")
            return False

    def fix_unterminated_string_errors(self, file_paths: List[str]) -> List[str]:
        """Fix files with unterminated string literal errors."""
        print(f"🔧 Fixing unterminated string errors in {len(file_paths)} files...")
        fixed = []

        for file_path in file_paths:
            full_path = os.path.join(self.root_dir, file_path)
            if self._fix_unterminated_string_single_file(full_path):
                fixed.append(file_path)
                self.fix_stats['unterminated_string'] += 1

        return fixed

    def _fix_unterminated_string_single_file(self, file_path: str) -> bool:
        """Fix unterminated string literals in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Common patterns for unterminated strings
            fixes = [
                # Missing closing quote at end of line
                (r'("[^"]*?)$', r'\1"'),
                (r"('[^']*?)$", r"\1'"),
                # Missing closing triple quote
                (r'("""[^"]*?)$', r'\1"""'),
                (r"('''[^']*?)$", r"\1'''"),
            ]

            original_content = content
            for pattern, replacement in fixes:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            # Only write if we made changes
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Verify fix worked
            ast.parse(content)
            return True

        except Exception as e:
            print(f"  ❌ Failed to fix {file_path}: {e}")
            return False

    def fix_bracket_mismatch_errors(self, file_paths: List[str]) -> List[str]:
        """Fix files with bracket/parenthesis mismatch errors."""
        print(f"🔧 Fixing bracket mismatch errors in {len(file_paths)} files...")
        fixed = []

        for file_path in file_paths:
            full_path = os.path.join(self.root_dir, file_path)
            if self._fix_bracket_mismatch_single_file(full_path):
                fixed.append(file_path)
                self.fix_stats['bracket_mismatch'] += 1

        return fixed

    def _fix_bracket_mismatch_single_file(self, file_path: str) -> bool:
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
            print(f"  ❌ Failed to fix {file_path}: {e}")
            return False

    def create_backup(self, file_paths: List[str]):
        """Create backup of files before fixing."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

        print(f"💾 Creating backup in {self.backup_dir}")

        for file_path in file_paths:
            full_path = os.path.join(self.root_dir, file_path)
            if os.path.exists(full_path):
                backup_path = os.path.join(self.backup_dir, file_path)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(full_path, backup_path)

    def fix_all_patterns(self, create_backup: bool = True) -> Dict[str, List[str]]:
        """Fix all identified syntax error patterns."""
        print("🚀 Starting comprehensive syntax error remediation...")

        # Analyze errors first
        _, patterns = self.analyze_syntax_errors()

        if not patterns:
            print("✅ No syntax errors found!")
            return {}

        # Create backup if requested
        if create_backup:
            all_files = []
            for files in patterns.values():
                all_files.extend(files)
            self.create_backup(list(set(all_files)))

        results = {}

        # Fix patterns in order of priority
        priority_order = [
            ('indentation', self.fix_indentation_errors),
            ('unexpected_indent', self.fix_unexpected_indent_errors),
            ('unterminated_string', self.fix_unterminated_string_errors),
            ('bracket_mismatch', self.fix_bracket_mismatch_errors),
        ]

        for pattern_name, fix_function in priority_order:
            if pattern_name in patterns:
                print(f"\n🎯 Processing {pattern_name} errors...")
                fixed_files = fix_function(patterns[pattern_name])
                results[pattern_name] = fixed_files

                if fixed_files:
                    print(f"  ✅ Fixed {len(fixed_files)} files")
                else:
                    print(f"  ⚠️  No files were successfully fixed")

        # Handle remaining 'other' pattern files manually
        if 'other' in patterns:
            print(f"\n⚠️  {len(patterns['other'])} files with 'other' pattern errors need manual review:")
            for file_path in patterns['other'][:10]:  # Show first 10
                print(f"    - {file_path}")
            if len(patterns['other']) > 10:
                print(f"    ... and {len(patterns['other']) - 10} more")

        return results

    def validate_fixes(self) -> Tuple[int, int]:
        """Validate that all fixes were successful."""
        print("🔍 Validating syntax fixes...")

        test_files = glob.glob(os.path.join(self.root_dir, 'tests/**/*.py'), recursive=True)
        syntax_errors = 0
        total_files = len(test_files)

        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError:
                syntax_errors += 1

        success_rate = ((total_files - syntax_errors) / total_files * 100) if total_files > 0 else 0

        print(f"📊 Validation Results:")
        print(f"  Total test files: {total_files}")
        print(f"  Files with syntax errors: {syntax_errors}")
        print(f"  Success rate: {success_rate:.1f}%")

        return total_files, syntax_errors

    def generate_report(self, results: Dict[str, List[str]]):
        """Generate detailed remediation report."""
        report_path = os.path.join(self.backup_dir, "remediation_report.md")

        with open(report_path, 'w') as f:
            f.write("# Test Syntax Remediation Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Summary\n\n")
            total_fixed = sum(len(files) for files in results.values())
            f.write(f"- **Total files fixed:** {total_fixed}\n")

            for pattern, files in results.items():
                f.write(f"- **{pattern}:** {len(files)} files\n")

            f.write("\n## Detailed Results\n\n")

            for pattern, files in results.items():
                f.write(f"### {pattern.replace('_', ' ').title()} ({len(files)} files)\n\n")
                for file_path in files:
                    f.write(f"- `{file_path}`\n")
                f.write("\n")

            f.write("## Backup Location\n\n")
            f.write(f"Original files backed up to: `{self.backup_dir}`\n\n")

            f.write("## Next Steps\n\n")
            f.write("1. Run comprehensive test suite to verify fixes\n")
            f.write("2. Review any remaining 'other' pattern errors manually\n")
            f.write("3. Update git commit with atomic syntax fixes\n")

        print(f"📄 Report generated: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Test Syntax Remediation Tool")
    parser.add_argument("--analyze", action="store_true", help="Analyze syntax errors only")
    parser.add_argument("--fix-all", action="store_true", help="Fix all syntax errors")
    parser.add_argument("--fix-pattern", choices=["indentation", "unexpected_indent", "unterminated_string", "bracket_mismatch"],
                       help="Fix specific error pattern")
    parser.add_argument("--fix-file", help="Fix specific file")
    parser.add_argument("--validate", action="store_true", help="Validate syntax of all test files")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup")
    parser.add_argument("--root-dir", default=".", help="Root directory to scan (default: current)")

    args = parser.parse_args()

    if not any([args.analyze, args.fix_all, args.fix_pattern, args.fix_file, args.validate]):
        parser.print_help()
        return

    remediation = TestSyntaxRemediator(args.root_dir)

    if args.analyze:
        remediation.analyze_syntax_errors()

    elif args.validate:
        remediation.validate_fixes()

    elif args.fix_all:
        results = remediation.fix_all_patterns(create_backup=not args.no_backup)
        remediation.generate_report(results)
        remediation.validate_fixes()

    elif args.fix_pattern:
        _, patterns = remediation.analyze_syntax_errors()
        if args.fix_pattern in patterns:
            if not args.no_backup:
                remediation.create_backup(patterns[args.fix_pattern])

            fix_function = getattr(remediation, f"fix_{args.fix_pattern}_errors")
            fixed = fix_function(patterns[args.fix_pattern])
            print(f"✅ Fixed {len(fixed)} files with {args.fix_pattern} errors")
        else:
            print(f"❌ No files found with {args.fix_pattern} pattern")

    elif args.fix_file:
        # Implementation for single file fixing
        pass

if __name__ == "__main__":
    main()