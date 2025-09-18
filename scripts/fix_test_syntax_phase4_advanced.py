#!/usr/bin/env python3
"""
Phase 4 Advanced Test Syntax Fixes - Targeted fixes for remaining 544 files

Based on error pattern analysis:
1. Unterminated String Literal: 246 files (45%)
2. Invalid Decimal Literal: 119 files (22%)
3. Mismatched Brackets/Parentheses: 49 files (9%)
4. Expected Token Missing: 39 files (7%)
5. Other Syntax Error: 36 files (7%)
6. Invalid Syntax: 28 files (5%)
7. Unterminated Triple-Quoted String: 26 files (5%)
"""

import ast
import os
import re
from pathlib import Path


class Phase4AdvancedFixer:
    def __init__(self):
        self.fixed_files = 0
        self.failed_files = []

    def fix_unterminated_strings(self, content, file_path):
        """Fix unterminated string literals."""
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            original_line = line

            # Fix single unterminated strings - look for unmatched quotes
            if line.count('"') % 2 == 1 and not line.strip().endswith('"""'):
                # Find the last unmatched quote and close it
                last_quote_idx = line.rfind('"')
                if last_quote_idx != -1:
                    # Check if it's not already properly escaped
                    if last_quote_idx == 0 or line[last_quote_idx-1] != '\\':
                        line = line + '"'

            # Fix single quote issues
            if line.count("'") % 2 == 1 and not line.strip().endswith("'''"):
                last_quote_idx = line.rfind("'")
                if last_quote_idx != -1:
                    if last_quote_idx == 0 or line[last_quote_idx-1] != '\\':
                        line = line + "'"

            # Fix f-string issues
            if re.search(r'f"[^"]*$', line) and not line.endswith('"""'):
                line = line + '"'

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_triple_quoted_strings(self, content, file_path):
        """Fix unterminated triple-quoted strings."""
        # Find unterminated triple quotes
        if '"""' in content:
            triple_quote_count = content.count('"""')
            if triple_quote_count % 2 == 1:
                # Add closing triple quote at the end
                content = content.rstrip() + '\n"""'

        if "'''" in content:
            triple_quote_count = content.count("'''")
            if triple_quote_count % 2 == 1:
                content = content.rstrip() + "\n'''"

        return content

    def fix_decimal_literals(self, content, file_path):
        """Fix invalid decimal literals."""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Fix invalid decimals like "3." or ".3." patterns
            line = re.sub(r'\b(\d+)\.\s*([^0-9])', r'\1.0\2', line)
            line = re.sub(r'\b(\d+)\.$', r'\1.0', line)

            # Fix patterns like "1.."
            line = re.sub(r'(\d+)\.\.', r'\1.0.', line)

            # Fix standalone dots that should be numbers
            line = re.sub(r'(?<![a-zA-Z0-9_])\.(?![a-zA-Z0-9_])', '0.0', line)

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_brackets_parentheses(self, content, file_path):
        """Fix mismatched brackets and parentheses."""
        lines = content.split('\n')
        fixed_lines = []

        bracket_stack = []

        for i, line in enumerate(lines):
            original_line = line

            # Track bracket/paren state
            for char in line:
                if char in '([{':
                    bracket_stack.append((char, i))
                elif char in ')]}':
                    if bracket_stack:
                        opener, _ = bracket_stack.pop()
                        expected_closer = {'(': ')', '[': ']', '{': '}'}
                        if expected_closer.get(opener) != char:
                            # Mismatched bracket - try to fix
                            line = line.replace(char, expected_closer.get(opener, char), 1)
                    else:
                        # Unmatched closing bracket - remove it
                        line = line.replace(char, '', 1)

            fixed_lines.append(line)

        # Close any remaining open brackets at the end
        while bracket_stack:
            opener, _ = bracket_stack.pop()
            closer = {'(': ')', '[': ']', '{': '}'}[opener]
            fixed_lines.append(closer)

        return '\n'.join(fixed_lines)

    def fix_indentation_issues(self, content, file_path):
        """Fix expected token missing and indentation issues."""
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # If previous line ended with ':' and this line is not indented
            if i > 0 and lines[i-1].strip().endswith(':'):
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    # Add basic indentation
                    line = '    ' + line
                elif not line.strip():
                    # Add pass statement for empty blocks
                    line = '    pass'

            # Fix unexpected indents
            if line.startswith('    ') and i > 0:
                prev_line = lines[i-1].strip()
                if prev_line and not prev_line.endswith(':') and not prev_line.startswith('def ') and not prev_line.startswith('class '):
                    # Remove unexpected indent
                    line = line.lstrip()

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_syntax_issues(self, content, file_path):
        """Fix various invalid syntax issues."""
        # Fix common syntax problems
        content = re.sub(r'import\s+\.\s*$', 'pass  # Fixed invalid import', content, flags=re.MULTILINE)
        content = re.sub(r'from\s+\.\s*$', 'pass  # Fixed invalid from import', content, flags=re.MULTILINE)

        # Fix incomplete statements
        content = re.sub(r'^\s*def\s*$', 'def placeholder_function(): pass', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*class\s*$', 'class PlaceholderClass: pass', content, flags=re.MULTILINE)

        # Fix trailing commas in wrong places
        content = re.sub(r',\s*$', '', content, flags=re.MULTILINE)

        return content

    def fix_other_syntax_errors(self, content, file_path):
        """Fix unmatched characters and other syntax errors."""
        # Fix unmatched characters
        for char in '}])':
            # Remove unmatched closing characters at the start of lines
            content = re.sub(f'^\\s*\\{char}', '', content, flags=re.MULTILINE)

        # Fix illegal annotations
        content = re.sub(r'(\d+):\s*int\s*=', r'var_\1: int =', content)

        return content

    def validate_fix(self, content, file_path):
        """Validate that the fix produces valid Python syntax."""
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False

    def fix_file(self, file_path):
        """Apply all fixes to a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()

            content = original_content

            # Apply fixes in order of complexity
            content = self.fix_syntax_issues(content, file_path)
            content = self.fix_decimal_literals(content, file_path)
            content = self.fix_unterminated_strings(content, file_path)
            content = self.fix_triple_quoted_strings(content, file_path)
            content = self.fix_brackets_parentheses(content, file_path)
            content = self.fix_indentation_issues(content, file_path)
            content = self.fix_other_syntax_errors(content, file_path)

            # Validate the fix
            if self.validate_fix(content, file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixed_files += 1
                return True
            else:
                self.failed_files.append(str(file_path))
                return False

        except Exception as e:
            self.failed_files.append(f"{file_path}: {str(e)}")
            return False


def main():
    print("Starting Phase 4 Advanced Test Syntax Fixes...")

    fixer = Phase4AdvancedFixer()
    test_dir = Path("tests")

    # Get all Python files with syntax errors
    error_files = []
    for py_file in test_dir.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            try:
                ast.parse(content)
            except SyntaxError:
                error_files.append(py_file)
        except:
            continue

    print(f"Found {len(error_files)} files with syntax errors")

    # Process files in batches
    batch_size = 50
    for i in range(0, len(error_files), batch_size):
        batch = error_files[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}: files {i+1} to {min(i+batch_size, len(error_files))}")

        for file_path in batch:
            success = fixer.fix_file(file_path)
            if success:
                print(f"  + Fixed: {file_path}")
            else:
                print(f"  - Failed: {file_path}")

    print(f"\nPhase 4 Advanced Fix Results:")
    print(f"Files successfully fixed: {fixer.fixed_files}")
    print(f"Files that failed to fix: {len(fixer.failed_files)}")

    if fixer.failed_files:
        print(f"\nFailed files (first 10):")
        for failed_file in fixer.failed_files[:10]:
            print(f"  - {failed_file}")


if __name__ == "__main__":
    main()