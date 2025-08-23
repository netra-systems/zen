#!/usr/bin/env python3
"""
Comprehensive E2E Test Syntax Fixer
Automatically detects and fixes common syntax errors in Python test files.
"""

import os
import ast
import re
import sys
from typing import List, Tuple, Dict, Optional
import traceback
from pathlib import Path


class SyntaxFixer:
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.error_patterns = []
    
    def find_python_files(self, directory: str) -> List[str]:
        """Find all Python files in directory recursively."""
        python_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files
    
    def check_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """Check if content has valid Python syntax."""
        try:
            ast.parse(content)
            return True, None
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Other error: {str(e)}"
    
    def fix_missing_commas(self, content: str) -> str:
        """Fix missing commas in lists, tuples, function calls."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Check if line ends with closing bracket/paren but previous line doesn't end with comma
            if i > 0 and line.strip() and line.strip()[0] in ')]},':
                prev_line = lines[i-1].strip()
                if prev_line and not prev_line.endswith((',', '(', '[', '{')):
                    # Don't add comma if it's a string or number followed by closing
                    if not (prev_line.endswith('"') or prev_line.endswith("'") or 
                           prev_line[-1].isdigit() or prev_line.endswith(')')):
                        lines[i-1] = lines[i-1].rstrip() + ','
            
            # Fix function parameter lists
            if re.search(r'\w+\s*\(.*[^,\(\[\{]\s*$', line) and i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith(')'):
                    line = line.rstrip() + ','
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_missing_colons(self, content: str) -> str:
        """Fix missing colons after function/class definitions."""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Check for function/class definitions missing colons
            if re.match(r'^\s*(def|class|if|elif|else|for|while|with|try|except|finally)\b.*[^:]\s*$', line):
                # Don't add colon if it's a comment or already has one
                if not line.strip().endswith(':') and '#' not in line:
                    line = line.rstrip() + ':'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_missing_parentheses(self, content: str) -> str:
        """Fix missing closing parentheses, brackets, braces."""
        # Count opening and closing brackets
        open_parens = content.count('(')
        close_parens = content.count(')')
        open_brackets = content.count('[')
        close_brackets = content.count(']')
        open_braces = content.count('{')
        close_braces = content.count('}')
        
        # Add missing closing brackets at the end
        if open_parens > close_parens:
            content += ')' * (open_parens - close_parens)
        if open_brackets > close_brackets:
            content += ']' * (open_brackets - close_brackets)
        if open_braces > close_braces:
            content += '}' * (open_braces - close_braces)
        
        return content
    
    def fix_indentation_errors(self, content: str) -> str:
        """Fix basic indentation errors."""
        lines = content.split('\n')
        fixed_lines = []
        expected_indent = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Calculate expected indentation
            if i > 0:
                prev_line = lines[i-1].strip()
                if prev_line.endswith(':'):
                    expected_indent += 4
                elif stripped.startswith(('except', 'elif', 'else', 'finally')):
                    expected_indent = max(0, expected_indent - 4)
                elif stripped.startswith(('def', 'class')) and not prev_line.endswith(':'):
                    expected_indent = 0
            
            # Apply indentation
            if stripped:
                current_indent = len(line) - len(line.lstrip())
                if abs(current_indent - expected_indent) > 2:  # Only fix significant differences
                    line = ' ' * expected_indent + stripped
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_f_string_syntax(self, content: str) -> str:
        """Fix common f-string syntax issues."""
        # Fix f-strings with missing f prefix
        content = re.sub(r'(["\'])([^"\']*\{[^}]*\}[^"\']*)\1', r'f\1\2\1', content)
        
        # Fix f-strings with incorrect bracket usage
        content = re.sub(r'f"([^"]*)\{([^}]*)\}([^"]*)"', r'f"\1{\2}\3"', content)
        content = re.sub(r"f'([^']*)\\{([^}]*)\\}([^']*)'", r"f'\1{\2}\3'", content)
        
        return content
    
    def fix_incomplete_statements(self, content: str) -> str:
        """Fix incomplete statements and expressions."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Fix incomplete function definitions
            if stripped.startswith('def ') and not stripped.endswith(':'):
                if '(' in stripped and ')' not in stripped:
                    line = line + '):'
                elif not ':' in stripped:
                    line = line + ':'
            
            # Fix incomplete class definitions
            if stripped.startswith('class ') and not stripped.endswith(':'):
                if not ':' in stripped:
                    line = line + ':'
            
            # Fix incomplete try/except blocks
            if stripped in ('try', 'except', 'finally') and not stripped.endswith(':'):
                line = line + ':'
            
            # Add pass to empty code blocks
            if (stripped.endswith(':') and i < len(lines) - 1 and 
                lines[i + 1].strip() and not lines[i + 1].startswith(' ')):
                fixed_lines.append(line)
                fixed_lines.append('    pass')
                continue
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_dictionary_syntax(self, content: str) -> str:
        """Fix dictionary syntax issues."""
        # Fix missing colons in dictionary definitions
        content = re.sub(r'(\{[^}]*["\w]+)\s+(["\w][^}]*\})', r'\1: \2', content)
        
        # Fix missing commas in dictionaries
        lines = content.split('\n')
        fixed_lines = []
        in_dict = False
        
        for line in lines:
            stripped = line.strip()
            if '{' in stripped:
                in_dict = True
            if '}' in stripped:
                in_dict = False
            
            # Add missing commas in dictionary entries
            if (in_dict and ':' in stripped and not stripped.endswith(',') and 
                not stripped.endswith('{') and not stripped.endswith('}')):
                line = line.rstrip() + ','
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def apply_all_fixes(self, content: str) -> str:
        """Apply all syntax fixes to content."""
        original_content = content
        
        # Apply fixes in order of increasing complexity
        content = self.fix_missing_colons(content)
        content = self.fix_missing_commas(content)
        content = self.fix_dictionary_syntax(content)
        content = self.fix_f_string_syntax(content)
        content = self.fix_incomplete_statements(content)
        content = self.fix_missing_parentheses(content)
        content = self.fix_indentation_errors(content)
        
        return content
    
    def fix_file(self, filepath: str) -> bool:
        """Fix syntax errors in a single file."""
        try:
            # Read file
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Check if already valid
            is_valid, error = self.check_syntax(original_content)
            if is_valid:
                return True
            
            print(f"Fixing {filepath}: {error}")
            
            # Apply fixes
            fixed_content = self.apply_all_fixes(original_content)
            
            # Verify fix worked
            is_valid_after, error_after = self.check_syntax(fixed_content)
            
            if is_valid_after:
                # Save fixed file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"+ Fixed {filepath}")
                self.fixed_files.append(filepath)
                return True
            else:
                print(f"X Could not fix {filepath}: {error_after}")
                self.failed_files.append((filepath, error_after))
                return False
        
        except Exception as e:
            print(f"X Error processing {filepath}: {str(e)}")
            self.failed_files.append((filepath, str(e)))
            return False
    
    def fix_directory(self, directory: str) -> Dict[str, int]:
        """Fix all Python files in directory."""
        python_files = self.find_python_files(directory)
        
        print(f"Found {len(python_files)} Python files in {directory}")
        print("-" * 60)
        
        for filepath in python_files:
            self.fix_file(filepath)
        
        return {
            'total': len(python_files),
            'fixed': len(self.fixed_files),
            'failed': len(self.failed_files)
        }
    
    def print_report(self):
        """Print summary report."""
        print("\n" + "="*60)
        print("SYNTAX FIXING REPORT")
        print("="*60)
        
        if self.fixed_files:
            print(f"\n+ SUCCESSFULLY FIXED ({len(self.fixed_files)} files):")
            for filepath in self.fixed_files:
                print(f"  - {filepath}")
        
        if self.failed_files:
            print(f"\nX FAILED TO FIX ({len(self.failed_files)} files):")
            for filepath, error in self.failed_files:
                print(f"  - {filepath}")
                print(f"    Error: {error}")
        
        total_processed = len(self.fixed_files) + len(self.failed_files)
        if total_processed > 0:
            success_rate = (len(self.fixed_files) / total_processed) * 100
            print(f"\nSUCCESS RATE: {success_rate:.1f}% ({len(self.fixed_files)}/{total_processed})")


def main():
    """Main execution function."""
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "tests/e2e"
    
    if not os.path.exists(directory):
        print(f"Error: Directory {directory} does not exist")
        sys.exit(1)
    
    print(f"E2E Test Syntax Fixer")
    print(f"Target directory: {os.path.abspath(directory)}")
    print("="*60)
    
    fixer = SyntaxFixer()
    stats = fixer.fix_directory(directory)
    fixer.print_report()
    
    # Final validation pass
    print("\n" + "="*60)
    print("FINAL VALIDATION")
    print("="*60)
    
    python_files = fixer.find_python_files(directory)
    valid_count = 0
    invalid_files = []
    
    for filepath in python_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            valid_count += 1
        except SyntaxError as e:
            invalid_files.append((filepath, str(e)))
    
    print(f"Valid files: {valid_count}/{len(python_files)}")
    
    if invalid_files:
        print(f"\nRemaining syntax errors ({len(invalid_files)} files):")
        for filepath, error in invalid_files:
            print(f"  - {filepath}: {error}")
    else:
        print("SUCCESS: All files now have valid syntax!")
    
    return len(invalid_files) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)