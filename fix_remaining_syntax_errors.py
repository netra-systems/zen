#!/usr/bin/env python3
"""
Advanced Syntax Error Fixer - Phase 2
Handles the more complex patterns that the first pass couldn't resolve.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set

class AdvancedSyntaxFixer:
    def __init__(self):
        self.fixed_count = 0
        self.error_count = 0
        self.patterns_fixed = {
            'f_string_bracket_fixes': 0,
            'dictionary_bracket_fixes': 0,
            'unterminated_string_fixes': 0,
            'indented_block_fixes': 0,
            'unmatched_parentheses_fixes': 0,
            'unexpected_indent_fixes': 0,
            'invalid_syntax_fixes': 0,
        }
        
    def find_bracket_mismatches(self, content: str) -> List[Tuple[int, str, str]]:
        """Find bracket mismatches in the content."""
        fixes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Look for f-string bracket issues: f"text {var]" should be f"text {var}"
            f_string_bracket_pattern = r'f["\']([^"\']*?)\{([^}]*?)\][^"\']*?["\']'
            if re.search(f_string_bracket_pattern, line):
                fixed_line = re.sub(r'(\{[^}]*?)\]', r'\1}', line)
                if fixed_line != line:
                    fixes.append((i, line, fixed_line))
                    self.patterns_fixed['f_string_bracket_fixes'] += 1
            
            # Look for dictionary bracket issues: {key] should be {key}
            dict_bracket_pattern = r'\{[^}]*?\]'
            if re.search(dict_bracket_pattern, line):
                fixed_line = re.sub(r'(\{[^}]*?)\]', r'\1}', line)
                if fixed_line != line:
                    fixes.append((i, line, fixed_line))
                    self.patterns_fixed['dictionary_bracket_fixes'] += 1
                    
        return fixes
    
    def fix_unterminated_strings(self, content: str) -> str:
        """Fix unterminated string literals."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Check for unterminated strings
            if '"""' in line:
                # Count triple quotes
                triple_count = line.count('"""')
                if triple_count % 2 != 0:
                    # Odd number of triple quotes - likely unterminated
                    line = line + '"""'
                    self.patterns_fixed['unterminated_string_fixes'] += 1
            elif '"' in line and line.strip().endswith('"') == False:
                # Simple quote check - more complex logic needed for real cases
                quote_count = line.count('"') - line.count('\\"')
                if quote_count % 2 != 0:
                    # Check if it's not an f-string or comment
                    if not line.strip().startswith('#') and 'f"' not in line:
                        line = line + '"'
                        self.patterns_fixed['unterminated_string_fixes'] += 1
                        
            fixed_lines.append(line)
            
        return '\n'.join(fixed_lines)
    
    def fix_indented_blocks(self, content: str) -> str:
        """Fix 'expected an indented block' errors."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            
            # Check if this line needs an indented block
            if (line.strip().endswith(':') and 
                i + 1 < len(lines) and 
                lines[i + 1].strip() and
                not lines[i + 1].startswith(' ' * (len(line) - len(line.lstrip()) + 4))):
                
                # Check if next line is not properly indented
                if (line.strip().startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'try:', 'except', 'finally:', 'with ', 'for ', 'while ')) and
                    i + 1 < len(lines) and lines[i + 1].strip()):
                    
                    next_line = lines[i + 1]
                    current_indent = len(line) - len(line.lstrip())
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    if next_indent <= current_indent:
                        # Need to add indentation
                        proper_indent = ' ' * (current_indent + 4)
                        if not next_line.strip().startswith('pass'):
                            lines[i + 1] = proper_indent + next_line.lstrip()
                            self.patterns_fixed['indented_block_fixes'] += 1
                        
        return '\n'.join(lines)
    
    def fix_unexpected_indents(self, content: str) -> str:
        """Fix unexpected indent errors."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            if line.strip() and not line[0].isspace():
                # This line is not indented
                fixed_lines.append(line)
            elif line.strip():
                # This line is indented - check if it should be
                prev_non_empty = None
                for j in range(i - 1, -1, -1):
                    if lines[j].strip():
                        prev_non_empty = lines[j]
                        break
                
                if prev_non_empty:
                    prev_indent = len(prev_non_empty) - len(prev_non_empty.lstrip())
                    curr_indent = len(line) - len(line.lstrip())
                    
                    # If previous line doesn't end with : and current line is indented more
                    if not prev_non_empty.strip().endswith(':') and curr_indent > prev_indent:
                        # Reduce indentation to match previous line
                        line = ' ' * prev_indent + line.lstrip()
                        self.patterns_fixed['unexpected_indent_fixes'] += 1
                        
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
                
        return '\n'.join(lines)
    
    def fix_parentheses_issues(self, content: str) -> str:
        """Fix unmatched parentheses issues."""
        # Simple approach - try to balance parentheses
        stack = []
        bracket_map = {'(': ')', '[': ']', '{': '}'}
        reverse_map = {')': '(', ']': '[', '}': '{'}
        
        fixed_content = ""
        
        for char in content:
            if char in bracket_map:
                stack.append(char)
                fixed_content += char
            elif char in reverse_map:
                if stack and stack[-1] == reverse_map[char]:
                    stack.pop()
                    fixed_content += char
                elif stack:
                    # Mismatched bracket - try to fix
                    expected = bracket_map[stack[-1]]
                    stack.pop()
                    fixed_content += expected
                    self.patterns_fixed['unmatched_parentheses_fixes'] += 1
                else:
                    fixed_content += char
            else:
                fixed_content += char
                
        return fixed_content
    
    def fix_invalid_syntax(self, content: str) -> str:
        """Fix common invalid syntax patterns."""
        fixes = [
            # Fix missing commas in function calls
            (r'(\w+)\s*=\s*([^,\n]*)\s+(\w+)\s*=', r'\1=\2, \3='),
            # Fix missing parentheses in function calls
            (r'(\w+)\s+(\w+\()', r'\1(\2'),
            # Fix missing colons after if/else/for/while
            (r'^(\s*)(if|else|elif|for|while|try|except|finally|with|def|class)\s+([^:\n]+)$', r'\1\2 \3:'),
        ]
        
        for pattern, replacement in fixes:
            if re.search(pattern, content, re.MULTILINE):
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                self.patterns_fixed['invalid_syntax_fixes'] += 1
                
        return content
    
    def fix_file(self, file_path: str) -> bool:
        """Fix syntax errors in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                
            # Apply fixes in order
            content = original_content
            
            # Fix bracket mismatches first
            bracket_fixes = self.find_bracket_mismatches(content)
            if bracket_fixes:
                lines = content.split('\n')
                for line_num, old_line, new_line in bracket_fixes:
                    if line_num < len(lines):
                        lines[line_num] = new_line
                content = '\n'.join(lines)
            
            # Apply other fixes
            content = self.fix_unterminated_strings(content)
            content = self.fix_indented_blocks(content)
            content = self.fix_unexpected_indents(content)
            content = self.fix_parentheses_issues(content)
            content = self.fix_invalid_syntax(content)
            
            # Validate the fix
            try:
                ast.parse(content)
                
                # Only write if content changed
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"FIXED: {file_path}")
                    self.fixed_count += 1
                    return True
                else:
                    print(f"NO_CHANGE: {file_path}")
                    return True
                    
            except SyntaxError as e:
                print(f"WARNING: Still has errors after fix: {file_path} - {e}")
                self.error_count += 1
                return False
                
        except Exception as e:
            print(f"ERROR: Could not process {file_path}: {e}")
            self.error_count += 1
            return False
    
    def process_directory(self, directory: str):
        """Process all Python files in a directory."""
        test_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py') and file.startswith('test_'):
                    test_files.append(os.path.join(root, file))
        
        print(f"Found {len(test_files)} test files")
        
        for file_path in test_files:
            rel_path = os.path.relpath(file_path)
            print(f"Processing: {rel_path}")
            self.fix_file(file_path)
    
    def print_summary(self):
        """Print summary of fixes applied."""
        print("\n" + "="*50)
        print("ADVANCED SYNTAX ERROR FIX SUMMARY")
        print("="*50)
        print(f"Fixed files: {self.fixed_count}")
        print(f"Failed files: {self.error_count}")
        print()
        print("Patterns fixed:")
        for pattern, count in self.patterns_fixed.items():
            if count > 0:
                print(f"  {pattern}: {count}")

def main():
    """Main execution function."""
    print("Advanced Python Syntax Error Fixer - Phase 2")
    print("=" * 50)
    print("Targeting complex patterns:")
    print("- F-string bracket mismatches")
    print("- Dictionary bracket issues") 
    print("- Unterminated string literals")
    print("- Missing indented blocks")
    print("- Unexpected indentation")
    print("- Unmatched parentheses")
    print("- Invalid syntax patterns")
    print()
    
    fixer = AdvancedSyntaxFixer()
    
    # Focus on directories with the most critical errors
    directories = [
        "netra_backend/tests/critical",
        "netra_backend/tests/agents", 
        "netra_backend/tests/e2e",
        "netra_backend/tests/integration"
    ]
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"\nProcessing directory: {directory}")
            fixer.process_directory(directory)
        else:
            print(f"Directory not found: {directory}")
    
    fixer.print_summary()

if __name__ == "__main__":
    main()