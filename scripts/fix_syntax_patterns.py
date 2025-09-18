#!/usr/bin/env python3
"""
Comprehensive syntax error pattern fixer for test files.

This script addresses the common syntax error patterns identified:
- Unterminated string literals
- Unmatched parentheses, brackets, braces
- Invalid decimal literals
- Unexpected indentation
- Invalid syntax patterns
"""

import re
import sys
import ast
from pathlib import Path
from typing import List, Tuple, Dict
import argparse


class SyntaxErrorFixer:
    """Fix common syntax error patterns in Python files."""
    
    def __init__(self):
        self.patterns_fixed = {
            'unterminated_strings': 0,
            'unmatched_parentheses': 0,
            'invalid_decimals': 0,
            'indentation_errors': 0,
            'invalid_syntax': 0,
            'triple_quote_fixes': 0
        }
    
    def fix_unterminated_strings(self, content: str) -> str:
        """Fix unterminated string literals."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Look for unterminated strings
            if line.count('"') % 2 == 1 and not line.strip().endswith('\\'):
                # If odd number of quotes and doesn't end with escape, add closing quote
                if line.rstrip().endswith('"'):
                    fixed_lines.append(line)
                else:
                    # Find last quote position
                    last_quote = line.rfind('"')
                    if last_quote != -1:
                        # Add closing quote at end of meaningful content
                        line_content = line.rstrip()
                        if line_content and not line_content.endswith('"'):
                            line = line_content + '"'
                            self.patterns_fixed['unterminated_strings'] += 1
                
            # Same for single quotes
            elif line.count("'") % 2 == 1 and not line.strip().endswith('\\'):
                if line.rstrip().endswith("'"):
                    fixed_lines.append(line)
                else:
                    last_quote = line.rfind("'")
                    if last_quote != -1:
                        line_content = line.rstrip()
                        if line_content and not line_content.endswith("'"):
                            line = line_content + "'"
                            self.patterns_fixed['unterminated_strings'] += 1
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_unmatched_parentheses(self, content: str) -> str:
        """Fix unmatched parentheses, brackets, and braces."""
        lines = content.split('\n')
        fixed_lines = []
        
        paren_stack = []
        bracket_stack = []
        brace_stack = []
        
        for line_num, line in enumerate(lines):
            # Track opening/closing characters
            for char in line:
                if char == '(':
                    paren_stack.append(line_num)
                elif char == ')':
                    if paren_stack:
                        paren_stack.pop()
                elif char == '[':
                    bracket_stack.append(line_num)
                elif char == ']':
                    if bracket_stack:
                        bracket_stack.pop()
                elif char == '{':
                    brace_stack.append(line_num)
                elif char == '}':
                    if brace_stack:
                        brace_stack.pop()
            
            # Fix common mismatched patterns
            if '}' in line and '(' in line and ')' not in line:
                # Replace } with ) if we have open parentheses
                line = line.replace('}', ')')
                self.patterns_fixed['unmatched_parentheses'] += 1
            
            if ']' in line and '(' in line and ')' not in line:
                # Replace ] with ) if we have open parentheses
                line = line.replace(']', ')')
                self.patterns_fixed['unmatched_parentheses'] += 1
            
            fixed_lines.append(line)
        
        # Add missing closing characters at end if needed
        missing_parens = len(paren_stack)
        missing_brackets = len(bracket_stack)
        missing_braces = len(brace_stack)
        
        if missing_parens > 0:
            fixed_lines.append(')' * missing_parens)
            self.patterns_fixed['unmatched_parentheses'] += missing_parens
        
        if missing_brackets > 0:
            fixed_lines.append(']' * missing_brackets)
            self.patterns_fixed['unmatched_parentheses'] += missing_brackets
            
        if missing_braces > 0:
            fixed_lines.append('}' * missing_braces)
            self.patterns_fixed['unmatched_parentheses'] += missing_braces
        
        return '\n'.join(fixed_lines)
    
    def fix_invalid_decimals(self, content: str) -> str:
        """Fix invalid decimal literals like '09' -> '9'."""
        # Pattern: numbers with leading zeros
        pattern = r'\b0+(\d+)\b'
        
        def replace_decimal(match):
            number = match.group(1)
            if number == '0':
                return '0'
            self.patterns_fixed['invalid_decimals'] += 1
            return number
        
        return re.sub(pattern, replace_decimal, content)
    
    def fix_indentation_errors(self, content: str) -> str:
        """Fix common indentation errors."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix: expected an indented block after 'if' statement
            if i > 0:
                prev_line = lines[i-1].strip()
                if (prev_line.endswith(':') and 
                    (prev_line.startswith('if ') or prev_line.startswith('elif ') or 
                     prev_line.startswith('else:') or prev_line.startswith('def ') or
                     prev_line.startswith('class ') or prev_line.startswith('try:') or
                     prev_line.startswith('except ') or prev_line.startswith('finally:'))):
                    
                    if line.strip() == '' or not line.startswith('    '):
                        # Add a pass statement with proper indentation
                        current_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                        fixed_lines.append(' ' * (current_indent + 4) + 'pass')
                        self.patterns_fixed['indentation_errors'] += 1
                        if line.strip():  # If there was content, keep it
                            fixed_lines.append(line)
                        continue
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_triple_quotes(self, content: str) -> str:
        """Fix unterminated triple-quoted strings."""
        # Find unterminated triple quotes
        if content.count('"""') % 2 == 1:
            # Add closing triple quotes at the end
            content += '\n"""'
            self.patterns_fixed['triple_quote_fixes'] += 1
        
        if content.count("'''") % 2 == 1:
            content += "\n'''"
            self.patterns_fixed['triple_quote_fixes'] += 1
        
        return content
    
    def fix_syntax_errors(self, file_path: Path) -> bool:
        """Apply all syntax error fixes to a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            original_content = content
            
            # Apply fixes in order
            content = self.fix_unterminated_strings(content)
            content = self.fix_triple_quotes(content)
            content = self.fix_invalid_decimals(content)
            content = self.fix_unmatched_parentheses(content)
            content = self.fix_indentation_errors(content)
            
            # Only write if content changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False
    
    def validate_syntax(self, file_path: Path) -> bool:
        """Check if file has valid Python syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            ast.parse(content)
            return True
            
        except SyntaxError:
            return False
        except Exception:
            return False


def main():
    parser = argparse.ArgumentParser(description='Fix syntax error patterns in Python files')
    parser.add_argument('--directory', type=str, default='tests', 
                        help='Directory to scan for Python files')
    parser.add_argument('--apply-fixes', action='store_true',
                        help='Apply fixes to files (default: dry run)')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    fixer = SyntaxErrorFixer()
    directory = Path(args.directory)
    
    if not directory.exists():
        print(f"Directory {directory} does not exist")
        return 1
    
    # Find all Python files
    python_files = list(directory.rglob('*.py'))
    print(f"Found {len(python_files)} Python files in {directory}")
    
    files_with_errors = []
    files_fixed = []
    
    # Check each file for syntax errors
    for file_path in python_files:
        if not fixer.validate_syntax(file_path):
            files_with_errors.append(file_path)
            
            if args.apply_fixes:
                if args.verbose:
                    print(f"Fixing: {file_path}")
                
                if fixer.fix_syntax_errors(file_path):
                    files_fixed.append(file_path)
                    
                    # Validate fix worked
                    if fixer.validate_syntax(file_path):
                        if args.verbose:
                            print(f"  ✅ Fixed successfully")
                    else:
                        if args.verbose:
                            print(f"  ❌ Still has syntax errors")
    
    # Report results
    print(f"\n📊 SYNTAX ERROR FIXING RESULTS")
    print(f"=" * 50)
    print(f"Files with syntax errors: {len(files_with_errors)}")
    
    if args.apply_fixes:
        print(f"Files fixed: {len(files_fixed)}")
        print(f"\nPatterns fixed:")
        for pattern, count in fixer.patterns_fixed.items():
            if count > 0:
                print(f"  {pattern}: {count}")
    else:
        print("Run with --apply-fixes to fix the errors")
    
    return 0 if len(files_with_errors) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())