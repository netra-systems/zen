#!/usr/bin/env python3
"""
Comprehensive Test Syntax Fixer for Issue #1332
Fixes the most common syntax patterns found in test files.

Focus: Fast automated fixes for the most frequent issues
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict


class ComprehensiveTestFixer:
    """Comprehensive fixer for common test file syntax issues"""

    def __init__(self):
        self.fixes_applied = []

    def check_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Check if file has valid Python syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content, filename=str(file_path))
            return True, "Valid"
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Parse Error: {str(e)}"

    def fix_malformed_docstrings(self, content: str) -> str:
        """Fix common docstring issues"""
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # Pattern 1: Fix lines like '95th percentile latency.""' -> '"""95th percentile latency."""'
            if re.match(r'\s+\d+\w+.*\."*$', line.strip()):
                # This is likely a malformed docstring
                indent = len(line) - len(line.lstrip())
                content_match = re.search(r'(\d+\w+.*?)\.', line.strip())
                if content_match:
                    fixed_line = ' ' * indent + f'"""{content_match.group(1)}."""'
                    fixed_lines.append(fixed_line)
                    continue

            # Pattern 2: Fix lines like '""Average connection time."' -> '"""Average connection time."""'
            if re.match(r'\s*""[^"]*"*$', line):
                # Malformed docstring start
                indent = len(line) - len(line.lstrip())
                content_match = re.search(r'""([^"]*)"*', line.strip())
                if content_match:
                    fixed_line = ' ' * indent + f'"""{content_match.group(1)}."""'
                    fixed_lines.append(fixed_line)
                    continue

            # Pattern 3: Fix lines like 'Average CPU usage.""' -> '"""Average CPU usage."""'
            if re.match(r'\s*[A-Z][^"]*\."*$', line.strip()) and i > 0:
                # Check if previous line suggests this should be a docstring
                prev_line = lines[i-1].strip()
                if 'def ' in prev_line or '@property' in prev_line:
                    indent = len(line) - len(line.lstrip())
                    content_match = re.search(r'([^"]*?)\.', line.strip())
                    if content_match:
                        fixed_line = ' ' * indent + f'"""{content_match.group(1)}."""'
                        fixed_lines.append(fixed_line)
                        continue

            # Pattern 4: Fix double docstring markers
            if line.strip() == '"""' and i > 0 and fixed_lines and fixed_lines[-1].strip() == '"""':
                # Skip duplicate docstring marker
                continue

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_currency_references(self, content: str) -> str:
        """Fix currency reference issues"""
        # Replace $500K+ with safer alternatives
        content = content.replace('$500K+', '$500K plus')
        content = content.replace('$500K ARR', '$500K plus ARR')
        return content

    def fix_number_literals(self, content: str) -> str:
        """Fix invalid number literal issues"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Don't fix lines that are clearly in docstrings
            if '"""' in line or "'''" in line:
                fixed_lines.append(line)
                continue

            # Fix patterns like "25+ concurrent" -> "25 plus concurrent"
            line = re.sub(r'\b(\d+)\+(\s+\w)', r'\1 plus\2', line)

            # Fix patterns like "500K ARR" that aren't in strings
            if '"' not in line and "'" not in line:
                line = re.sub(r'\b(\d+)([A-Za-z]+)\b', r'"\1\2"', line)

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_unterminated_strings(self, content: str) -> str:
        """Fix unterminated string literals"""
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # Count quotes
            single_quotes = line.count("'")
            double_quotes = line.count('"')

            # If odd number of quotes, likely unterminated
            if double_quotes % 2 != 0 and not line.strip().endswith('\\'):
                # Check if next line might complete it
                if i < len(lines) - 1:
                    next_line = lines[i + 1]
                    if '"' not in next_line:
                        # Likely needs termination
                        line = line.rstrip() + '"'

            if single_quotes % 2 != 0 and not line.strip().endswith('\\'):
                # Check if next line might complete it
                if i < len(lines) - 1:
                    next_line = lines[i + 1]
                    if "'" not in next_line:
                        # Likely needs termination
                        line = line.rstrip() + "'"

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_bracket_mismatches(self, content: str) -> str:
        """Fix simple bracket mismatches"""
        lines = content.split('\n')

        # Simple check: if file ends with unmatched brackets, try to close them
        open_parens = content.count('(') - content.count(')')
        open_brackets = content.count('[') - content.count(']')
        open_braces = content.count('{') - content.count('}')

        if open_parens > 0 or open_brackets > 0 or open_braces > 0:
            # Add closing brackets to the last non-empty line
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip():
                    closing = ')' * open_parens + ']' * open_brackets + '}' * open_braces
                    lines[i] = lines[i].rstrip() + closing
                    break

        return '\n'.join(lines)

    def fix_file(self, file_path: Path) -> Tuple[bool, str, List[str]]:
        """Comprehensively fix a file"""
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Apply fixes in order
            content = original_content
            fixes_applied = []

            # Fix 1: Currency references
            new_content = self.fix_currency_references(content)
            if new_content != content:
                fixes_applied.append("Fixed currency references")
                content = new_content

            # Fix 2: Malformed docstrings
            new_content = self.fix_malformed_docstrings(content)
            if new_content != content:
                fixes_applied.append("Fixed malformed docstrings")
                content = new_content

            # Fix 3: Number literals
            new_content = self.fix_number_literals(content)
            if new_content != content:
                fixes_applied.append("Fixed number literals")
                content = new_content

            # Fix 4: Unterminated strings
            new_content = self.fix_unterminated_strings(content)
            if new_content != content:
                fixes_applied.append("Fixed unterminated strings")
                content = new_content

            # Fix 5: Bracket mismatches
            new_content = self.fix_bracket_mismatches(content)
            if new_content != content:
                fixes_applied.append("Fixed bracket mismatches")
                content = new_content

            # Save fixed content
            if content != original_content:
                # Create backup
                backup_path = file_path.with_suffix('.backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)

                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                return True, f"Applied fixes: {', '.join(fixes_applied)}", fixes_applied
            else:
                return True, "No fixes needed", []

        except Exception as e:
            return False, f"Error: {str(e)}", []

    def process_critical_files(self, project_root: Path) -> Dict[str, Dict]:
        """Process the most critical test files first"""

        # Priority files (manually selected based on mission-critical importance)
        priority_files = [
            "tests/mission_critical/test_websocket_agent_events_suite.py",
            "tests/mission_critical/performance_test_clean.py",
            "tests/mission_critical/standalone_performance_test.py",
            "tests/mission_critical/test_agent_execution_business_value.py",
            "tests/mission_critical/test_agent_factory_ssot_validation.py",
            "tests/mission_critical/test_actions_to_meet_goals_websocket_failures.py",
        ]

        results = {}

        print("COMPREHENSIVE TEST SYNTAX FIXER - CRITICAL FILES")
        print("=" * 60)

        for file_rel_path in priority_files:
            file_path = project_root / file_rel_path
            if not file_path.exists():
                results[file_rel_path] = {
                    'status': 'not_found',
                    'message': 'File not found'
                }
                continue

            print(f"\nProcessing: {file_rel_path}")

            # Check initial syntax
            is_valid_before, error_before = self.check_syntax(file_path)
            if is_valid_before:
                print(f"  ✓ Already valid")
                results[file_rel_path] = {
                    'status': 'already_valid',
                    'message': 'No fixes needed'
                }
                continue

            print(f"  Initial error: {error_before}")

            # Apply fixes
            success, message, fixes = self.fix_file(file_path)
            if not success:
                print(f"  ✗ Fix failed: {message}")
                results[file_rel_path] = {
                    'status': 'fix_failed',
                    'message': message
                }
                continue

            # Check syntax after fixes
            is_valid_after, error_after = self.check_syntax(file_path)
            if is_valid_after:
                print(f"  ✓ Fixed successfully: {message}")
                results[file_rel_path] = {
                    'status': 'fixed',
                    'message': message,
                    'fixes': fixes
                }
            else:
                print(f"  ⚠ Partially fixed: {message}")
                print(f"    Remaining error: {error_after}")
                results[file_rel_path] = {
                    'status': 'partially_fixed',
                    'message': message,
                    'fixes': fixes,
                    'remaining_error': error_after
                }

        return results


def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    fixer = ComprehensiveTestFixer()
    results = fixer.process_critical_files(project_root)

    print("\n" + "=" * 60)
    print("SUMMARY REPORT")
    print("=" * 60)

    for file_path, result in results.items():
        status = result['status']
        if status == 'fixed':
            print(f"✓ {file_path}: FIXED")
        elif status == 'already_valid':
            print(f"✓ {file_path}: ALREADY VALID")
        elif status == 'partially_fixed':
            print(f"⚠ {file_path}: PARTIALLY FIXED")
        elif status == 'fix_failed':
            print(f"✗ {file_path}: FAILED")
        elif status == 'not_found':
            print(f"- {file_path}: NOT FOUND")

    # Count successes
    fixed = sum(1 for r in results.values() if r['status'] == 'fixed')
    already_valid = sum(1 for r in results.values() if r['status'] == 'already_valid')
    total_success = fixed + already_valid
    total_files = len(results)

    print(f"\nResults: {total_success}/{total_files} files now have valid syntax")

    if total_success == total_files:
        print("🎉 All critical files now have valid syntax!")
        return 0
    else:
        print("⚠️ Some files still need manual attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())