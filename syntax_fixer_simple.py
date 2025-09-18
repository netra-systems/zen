#!/usr/bin/env python3
"""
Test File Syntax Error Fixer - P0 Infrastructure Crisis Resolution

MISSION: Fix 339+ syntax errors in test files to restore test infrastructure
PRIORITY: E2E, agent, and mission critical tests first
"""

import ast
import os
import re
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import traceback
from datetime import datetime


class SyntaxFixer:
    def __init__(self, base_dir: str = "C:/netra-apex"):
        self.base_dir = Path(base_dir)
        self.backup_dir = self.base_dir / "backups" / f"syntax_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            'total_processed': 0,
            'fixed_successfully': 0,
            'failed_to_fix': 0,
            'already_valid': 0,
            'patterns_applied': {}
        }

        # Priority patterns for fixing
        self.fix_patterns = [
            # Fix bracket/brace mismatches
            (r'\{\s*\)', '{}', 'bracket_mismatch_brace'),
            (r'\[\s*\)', '[]', 'bracket_mismatch_square'),
            (r'\(\s*\)', '()', 'bracket_mismatch_paren'),

            # Fix malformed imports with ( )
            (r'from\s+([^\s]+)\s+import\s+\(\s*\)', r'from \1 import ()', 'malformed_import_empty'),

            # Fix unterminated strings - common patterns
            (r'print\("([^"]*?)!\)$', r'print("\1!")', 'unterminated_print_string'),
            (r'print\("([^"]*?)$', r'print("\1")', 'unterminated_print_simple'),

            # Fix missing quotes in f-strings and print statements
            (r'print\(f([^"]*?)$', r'print(f"\1")', 'fstring_missing_quote'),
            (r'print\(f([^"]*?)\)$', r'print(f"\1")', 'fstring_missing_quote2'),
            (r'print\(([^"\']*?)\)$', r'print("\1")', 'print_missing_quotes'),

            # Fix decimal literal issues
            (r'(\d+)\.(\d+)\."""', r'\1.\2"""', 'decimal_literal_fix'),

            # Remove syntax error markers
            (r'REMOVED_SYNTAX_ERROR[^\n]*\n?', '', 'remove_error_markers'),

            # Fix missing colons
            (r'^(\s*)(if|elif|else|try|except|finally|for|while|with|def|class)\s+([^:]+)$',
             r'\1\2 \3:', 'missing_colon'),

            # Fix f-string format issues
            (r'print\(f"([^"]*?)\{([^}]*?)\}([^"]*?)"', r'print(f"\1{\2}\3")', 'fstring_fix'),
            (r'f"([^"]*?)([^}])\)$', r'f"\1\2")', 'fstring_termination'),
        ]

    def get_priority_files(self) -> List[Path]:
        """Get priority test files in order of importance."""
        all_files = []
        seen_files = set()

        # Priority 1: E2E agent tests
        for file_path in (self.base_dir / "tests").rglob("*agent*.py"):
            if file_path.is_file() and "e2e" in str(file_path) and file_path not in seen_files:
                all_files.append(file_path)
                seen_files.add(file_path)

        # Priority 2: Mission critical agent tests
        for file_path in (self.base_dir / "tests").rglob("*agent*.py"):
            if file_path.is_file() and "mission_critical" in str(file_path) and file_path not in seen_files:
                all_files.append(file_path)
                seen_files.add(file_path)

        # Priority 3: All E2E tests
        for file_path in (self.base_dir / "tests" / "e2e").rglob("*.py"):
            if file_path.is_file() and file_path not in seen_files:
                all_files.append(file_path)
                seen_files.add(file_path)

        # Priority 4: All mission critical tests
        for file_path in (self.base_dir / "tests" / "mission_critical").rglob("*.py"):
            if file_path.is_file() and file_path not in seen_files:
                all_files.append(file_path)
                seen_files.add(file_path)

        # Priority 5: Other agent tests
        for file_path in (self.base_dir / "tests").rglob("*agent*.py"):
            if file_path.is_file() and file_path not in seen_files:
                all_files.append(file_path)
                seen_files.add(file_path)

        # Priority 6: All other test files
        for file_path in (self.base_dir / "tests").rglob("*.py"):
            if file_path.is_file() and file_path not in seen_files:
                all_files.append(file_path)
                seen_files.add(file_path)

        print(f"Found {len(all_files)} test files to process")
        return all_files

    def backup_file(self, file_path: Path) -> bool:
        """Create backup of original file."""
        try:
            relative_path = file_path.relative_to(self.base_dir)
            backup_file = self.backup_dir / relative_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_file)
            return True
        except Exception as e:
            print(f"Failed to backup {file_path}: {e}")
            return False

    def check_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """Check if Python content has valid syntax."""
        try:
            ast.parse(content)
            return True, None
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Other error: {e}"

    def apply_fixes(self, content: str) -> Tuple[str, List[str]]:
        """Apply all fix patterns to content."""
        fixed_content = content
        applied_patterns = []

        for pattern, replacement, pattern_name in self.fix_patterns:
            try:
                if re.search(pattern, fixed_content, re.MULTILINE):
                    fixed_content = re.sub(pattern, replacement, fixed_content, flags=re.MULTILINE)
                    applied_patterns.append(pattern_name)

                    if pattern_name not in self.stats['patterns_applied']:
                        self.stats['patterns_applied'][pattern_name] = 0
                    self.stats['patterns_applied'][pattern_name] += 1

            except Exception as e:
                print(f"Error applying pattern {pattern_name}: {e}")
                continue

        return fixed_content, applied_patterns

    def advanced_string_fix(self, content: str) -> str:
        """Advanced string literal fixing."""
        lines = content.split('\n')
        fixed_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            fixed_line = line

            # Fix malformed multi-line imports
            if 'from' in line and 'import' in line and '( )' in line:
                # Look for continuation lines
                j = i + 1
                import_items = []
                while j < len(lines) and not lines[j].strip().startswith('from'):
                    if lines[j].strip() and not lines[j].strip().startswith('#'):
                        import_items.append(lines[j].strip().rstrip(','))
                    j += 1

                if import_items:
                    # Reconstruct the import
                    import_base = line.replace('( )', '(').strip()
                    if not import_base.endswith('('):
                        import_base += ' ('

                    fixed_line = import_base
                    for k, item in enumerate(import_items):
                        if k == len(import_items) - 1:
                            fixed_line += f'\n    {item}\n)'
                        else:
                            fixed_line += f'\n    {item},'

                    # Skip the processed lines
                    i = j - 1

            # Fix common unterminated string patterns
            elif '"' in line and line.count('"') % 2 == 1:
                # Odd number of quotes - likely unterminated
                if 'print(' in line and line.strip().endswith('!') and not line.strip().endswith('")'):
                    fixed_line = line + '")'
                elif 'print(f' in line and not line.strip().endswith('")'):
                    fixed_line = line + '")'

            # Fix lines that are just a quote
            elif line.strip() == '"':
                if i > 0 and '"""' in lines[i-1]:
                    fixed_line = '"""'

            fixed_lines.append(fixed_line)
            i += 1

        return '\n'.join(fixed_lines)

    def fix_file(self, file_path: Path) -> Dict[str, any]:
        """Fix syntax errors in a single file."""
        result = {
            'file': str(file_path),
            'success': False,
            'original_valid': False,
            'final_valid': False,
            'patterns_applied': [],
            'error': None
        }

        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()

            # Check if already valid
            is_valid, error = self.check_syntax(original_content)
            result['original_valid'] = is_valid

            if is_valid:
                result['success'] = True
                result['final_valid'] = True
                self.stats['already_valid'] += 1
                return result

            # Backup original file
            if not self.backup_file(file_path):
                result['error'] = "Failed to create backup"
                return result

            # Apply pattern-based fixes
            fixed_content, applied_patterns = self.apply_fixes(original_content)
            result['patterns_applied'] = applied_patterns

            # Apply advanced string fixes
            fixed_content = self.advanced_string_fix(fixed_content)

            # Validate fixed content
            is_valid, error = self.check_syntax(fixed_content)
            result['final_valid'] = is_valid

            if is_valid:
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                result['success'] = True
                self.stats['fixed_successfully'] += 1
                print(f"FIXED: {file_path.name} (patterns: {', '.join(applied_patterns)})")
            else:
                result['error'] = f"Still invalid after fixes: {error}"
                self.stats['failed_to_fix'] += 1
                print(f"FAILED: {file_path.name} - {error}")

        except Exception as e:
            result['error'] = f"Exception: {str(e)}"
            self.stats['failed_to_fix'] += 1
            print(f"ERROR: {file_path.name} - {e}")

        self.stats['total_processed'] += 1
        return result

    def fix_batch(self, max_files: int = 50) -> List[Dict[str, any]]:
        """Fix a batch of priority files."""
        priority_files = self.get_priority_files()
        files_to_process = priority_files[:max_files]

        print(f"\nStarting syntax fix batch: {len(files_to_process)} files")
        print(f"Backup directory: {self.backup_dir}")
        print("="*60)

        results = []
        for i, file_path in enumerate(files_to_process, 1):
            print(f"[{i}/{len(files_to_process)}] Processing: {file_path.name}")
            result = self.fix_file(file_path)
            results.append(result)

            if i % 10 == 0:
                print(f"Progress: {self.stats['fixed_successfully']} fixed, {self.stats['failed_to_fix']} failed")

        return results

    def print_final_report(self, results: List[Dict[str, any]]):
        """Print comprehensive final report."""
        print("\n" + "="*60)
        print("SYNTAX FIXING FINAL REPORT")
        print("="*60)

        print(f"STATISTICS:")
        print(f"   Total processed: {self.stats['total_processed']}")
        print(f"   Fixed successfully: {self.stats['fixed_successfully']}")
        print(f"   Already valid: {self.stats['already_valid']}")
        print(f"   Failed to fix: {self.stats['failed_to_fix']}")

        if self.stats['patterns_applied']:
            print(f"\nPATTERNS APPLIED:")
            for pattern, count in sorted(self.stats['patterns_applied'].items(),
                                       key=lambda x: x[1], reverse=True):
                print(f"   {pattern}: {count} times")

        # Show failed files for investigation
        failed_files = [r for r in results if not r['success'] and not r['original_valid']]
        if failed_files:
            print(f"\nFAILED FILES ({len(failed_files)}):")
            for result in failed_files[:10]:
                print(f"   {Path(result['file']).name}: {result['error']}")
            if len(failed_files) > 10:
                print(f"   ... and {len(failed_files) - 10} more")

        print(f"\nBackups saved to: {self.backup_dir}")
        print("="*60)


def main():
    """Main execution function."""
    if len(sys.argv) > 1:
        max_files = int(sys.argv[1])
    else:
        max_files = 50

    print("Test File Syntax Error Fixer - P0 Infrastructure Crisis Resolution")
    print(f"Processing up to {max_files} priority test files")

    fixer = SyntaxFixer()
    results = fixer.fix_batch(max_files)
    fixer.print_final_report(results)

    # Validate success
    total_fixed = fixer.stats['fixed_successfully'] + fixer.stats['already_valid']
    success_rate = (total_fixed / fixer.stats['total_processed']) * 100 if fixer.stats['total_processed'] > 0 else 0

    print(f"\nSUCCESS RATE: {success_rate:.1f}% ({total_fixed}/{fixer.stats['total_processed']})")

    if success_rate >= 80:
        print("BATCH SUCCESSFUL - Ready for larger scale processing")
        return 0
    else:
        print("BATCH NEEDS REVIEW - Check failed files before proceeding")
        return 1


if __name__ == "__main__":
    sys.exit(main())