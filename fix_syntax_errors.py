#!/usr/bin/env python3
"""
Comprehensive Python Syntax Error Auto-Fix Script for Netra Test Suite

This script automatically fixes common syntax errors in Python test files:
1. Missing colons after function/class definitions, if/for/while statements
2. Missing commas in lists, dictionaries, function parameters
3. Indentation errors (converts to 4-space indents)
4. Empty function bodies (adds 'pass' statement)
5. Unterminated string literals
6. Mismatched brackets/parentheses
7. Missing imports for common test utilities
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import tokenize
import io


class SyntaxErrorFixer:
    """Comprehensive Python syntax error fixer"""
    
    def __init__(self):
        self.fixes_applied = {
            'missing_colons': 0,
            'missing_commas': 0,
            'indentation_errors': 0,
            'empty_functions': 0,
            'unterminated_strings': 0,
            'bracket_mismatches': 0,
            'missing_imports': 0,
            'trailing_commas': 0,
            'decorator_issues': 0,
            'async_syntax': 0
        }
        self.failed_files = []
        self.processed_files = []
        
        # Common patterns for syntax fixes
        self.colon_patterns = [
            (r'^\s*(def\s+[^:]+)\s*$', r'\1:'),  # Function definitions
            (r'^\s*(class\s+[^:]+)\s*$', r'\1:'),  # Class definitions
            (r'^\s*(if\s+[^:]+)\s*$', r'\1:'),  # If statements
            (r'^\s*(elif\s+[^:]+)\s*$', r'\1:'),  # Elif statements
            (r'^\s*(else)\s*$', r'\1:'),  # Else statements
            (r'^\s*(for\s+[^:]+)\s*$', r'\1:'),  # For loops
            (r'^\s*(while\s+[^:]+)\s*$', r'\1:'),  # While loops
            (r'^\s*(try)\s*$', r'\1:'),  # Try blocks
            (r'^\s*(except[^:]*)\s*$', r'\1:'),  # Except blocks
            (r'^\s*(finally)\s*$', r'\1:'),  # Finally blocks
            (r'^\s*(with\s+[^:]+)\s*$', r'\1:'),  # With statements
        ]
        
        # Common test imports that might be missing
        self.common_test_imports = [
            "import pytest",
            "import asyncio",
            "from unittest.mock import Mock, patch, MagicMock, AsyncMock",
            "from typing import Dict, List, Optional, Any, Tuple",
            "import uuid",
            "from datetime import datetime",
            "import json",
        ]

    def fix_file(self, file_path: str) -> bool:
        """Fix syntax errors in a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            if not original_content.strip():
                # Empty file, add minimal content
                fixed_content = "# Empty test file\npass\n"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                return True
            
            # Apply fixes in order
            content = original_content
            content = self._fix_encoding_issues(content)
            content = self._fix_unterminated_strings(content)
            content = self._fix_bracket_mismatches(content)
            content = self._fix_missing_colons(content)
            content = self._fix_indentation(content)
            content = self._fix_empty_functions(content)
            content = self._fix_trailing_commas(content)
            content = self._fix_decorator_issues(content)
            content = self._fix_async_syntax(content)
            content = self._add_missing_imports(content)
            content = self._fix_common_syntax_issues(content)
            
            # Try to parse the fixed content
            try:
                ast.parse(content)
                # If parsing succeeds, write the fixed content
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"+ Fixed: {file_path}")
                else:
                    print(f"- No changes needed: {file_path}")
                self.processed_files.append(file_path)
                return True
            except SyntaxError as e:
                # Try more aggressive fixes
                content = self._aggressive_syntax_fixes(content, str(e))
                try:
                    ast.parse(content)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"+ Aggressively fixed: {file_path}")
                    self.processed_files.append(file_path)
                    return True
                except:
                    print(f"X Failed to fix: {file_path} - {str(e)}")
                    self.failed_files.append((file_path, str(e)))
                    return False
            
        except Exception as e:
            print(f"X Error processing {file_path}: {str(e)}")
            self.failed_files.append((file_path, str(e)))
            return False

    def _fix_encoding_issues(self, content: str) -> str:
        """Fix encoding and BOM issues"""
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
        return content

    def _fix_unterminated_strings(self, content: str) -> str:
        """Fix unterminated string literals"""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Simple heuristic: if line has odd number of quotes, add closing quote
            if line.count('"') % 2 == 1 and not line.strip().endswith('\\'):
                line = line + '"'
                self.fixes_applied['unterminated_strings'] += 1
            elif line.count("'") % 2 == 1 and not line.strip().endswith('\\'):
                line = line + "'"
                self.fixes_applied['unterminated_strings'] += 1
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def _fix_bracket_mismatches(self, content: str) -> str:
        """Fix mismatched brackets and parentheses"""
        # Count and balance brackets
        bracket_stack = []
        bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            for char in line:
                if char in bracket_pairs:
                    bracket_stack.append((char, i))
                elif char in bracket_pairs.values():
                    if bracket_stack and bracket_pairs[bracket_stack[-1][0]] == char:
                        bracket_stack.pop()
                    else:
                        # Mismatched closing bracket - remove it for now
                        line = line.replace(char, '', 1)
                        self.fixes_applied['bracket_mismatches'] += 1
            lines[i] = line
        
        # Add missing closing brackets at the end if needed
        closing_brackets = []
        while bracket_stack:
            opening, line_num = bracket_stack.pop()
            closing_brackets.append(bracket_pairs[opening])
            self.fixes_applied['bracket_mismatches'] += 1
        
        if closing_brackets:
            lines.append(''.join(closing_brackets))
        
        return '\n'.join(lines)

    def _fix_missing_colons(self, content: str) -> str:
        """Fix missing colons after function definitions, if statements, etc."""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            original_line = line
            for pattern, replacement in self.colon_patterns:
                if re.match(pattern, line):
                    line = re.sub(pattern, replacement, line)
                    if line != original_line:
                        self.fixes_applied['missing_colons'] += 1
                    break
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def _fix_indentation(self, content: str) -> str:
        """Fix indentation errors by normalizing to 4-space indents"""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            if line.strip():  # Non-empty line
                # Count leading whitespace
                leading_space = len(line) - len(line.lstrip())
                if leading_space > 0:
                    # Convert to 4-space indents
                    indent_level = leading_space // 4
                    remainder = leading_space % 4
                    if remainder > 0:
                        indent_level += 1  # Round up partial indents
                    new_line = '    ' * indent_level + line.lstrip()
                    if new_line != line:
                        self.fixes_applied['indentation_errors'] += 1
                    fixed_lines.append(new_line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def _fix_empty_functions(self, content: str) -> str:
        """Add 'pass' to empty function bodies"""
        lines = content.split('\n')
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            fixed_lines.append(line)
            
            # Check if this line is a function/class/if/etc definition
            if re.match(r'^\s*(def|class|if|elif|else|for|while|try|except|finally|with|async def)', line.strip()):
                if line.strip().endswith(':'):
                    # Look ahead to see if there's an indented block
                    next_non_empty = i + 1
                    while next_non_empty < len(lines) and not lines[next_non_empty].strip():
                        next_non_empty += 1
                    
                    if (next_non_empty >= len(lines) or 
                        not lines[next_non_empty].startswith('    ') or
                        lines[next_non_empty].strip() == ''):
                        # Empty block, add pass
                        indent = len(line) - len(line.lstrip()) + 4
                        fixed_lines.append(' ' * indent + 'pass')
                        self.fixes_applied['empty_functions'] += 1
            i += 1
        
        return '\n'.join(fixed_lines)

    def _fix_trailing_commas(self, content: str) -> str:
        """Fix missing trailing commas in multi-line structures"""
        # Simple approach: add comma before closing bracket if missing
        patterns = [
            (r'([^\s,])\s*\n\s*\)', r'\1,\n)'),  # Function parameters
            (r'([^\s,])\s*\n\s*\]', r'\1,\n]'),  # Lists
            (r'([^\s,])\s*\n\s*\}', r'\1,\n}'),  # Dictionaries
        ]
        
        for pattern, replacement in patterns:
            old_content = content
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if content != old_content:
                self.fixes_applied['trailing_commas'] += 1
        
        return content

    def _fix_decorator_issues(self, content: str) -> str:
        """Fix decorator syntax issues"""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix @decorator syntax
            if line.strip().startswith('@') and not line.strip().startswith('@@'):
                # Ensure decorator is on its own line
                if '@' in line and line.index('@') > 0:
                    # Decorator is not at start of line
                    before_decorator = line[:line.index('@')]
                    decorator_part = line[line.index('@'):]
                    if before_decorator.strip():
                        fixed_lines.append(before_decorator.rstrip())
                    fixed_lines.append(decorator_part)
                    self.fixes_applied['decorator_issues'] += 1
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def _fix_async_syntax(self, content: str) -> str:
        """Fix async/await syntax issues"""
        # Fix common async syntax problems
        fixes = [
            (r'\basync\s+def\s+', 'async def '),  # Normalize async def spacing
            (r'\bawait\s+', 'await '),  # Normalize await spacing
        ]
        
        for pattern, replacement in fixes:
            old_content = content
            content = re.sub(pattern, replacement, content)
            if content != old_content:
                self.fixes_applied['async_syntax'] += 1
        
        return content

    def _add_missing_imports(self, content: str) -> str:
        """Add common missing imports for test files"""
        if not content.strip():
            return content
            
        # Check if any imports are missing
        missing_imports = []
        for import_stmt in self.common_test_imports:
            if import_stmt not in content:
                # Check if we actually need this import
                module_name = import_stmt.split()[-1] if 'import' in import_stmt else import_stmt.split()[1]
                if module_name.lower() in content.lower():
                    missing_imports.append(import_stmt)
        
        if missing_imports:
            # Add imports at the top after any existing imports
            lines = content.split('\n')
            import_insert_pos = 0
            
            # Find where to insert imports
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#'):
                    if line.startswith('import ') or line.startswith('from '):
                        import_insert_pos = i + 1
                    else:
                        break
            
            # Insert missing imports
            for import_stmt in missing_imports:
                lines.insert(import_insert_pos, import_stmt)
                import_insert_pos += 1
                self.fixes_applied['missing_imports'] += 1
            
            content = '\n'.join(lines)
        
        return content

    def _fix_common_syntax_issues(self, content: str) -> str:
        """Fix other common syntax issues"""
        fixes = [
            # Fix function calls without parentheses
            (r'\b(print|len|str|int|float|bool|list|dict|set|tuple)\s+([^(\s][^\n]*)', r'\1(\2)'),
            # Fix assignment in conditions (should be ==)
            (r'\bif\s+([^=]+)=([^=][^:]+):', r'if \1==\2:'),
            # Fix missing spaces around operators
            (r'([a-zA-Z_]\w*)=([^=])', r'\1 = \2'),
            (r'([^=])=([a-zA-Z_]\w*)', r'\1 = \2'),
        ]
        
        for pattern, replacement in fixes:
            old_content = content
            try:
                content = re.sub(pattern, replacement, content)
                if content != old_content:
                    self.fixes_applied['trailing_commas'] += 1  # Using existing counter
            except:
                content = old_content  # Revert if regex fails
        
        return content

    def _aggressive_syntax_fixes(self, content: str, error_msg: str) -> str:
        """Apply more aggressive fixes for stubborn syntax errors"""
        lines = content.split('\n')
        
        # If we get specific line number from error message
        line_num_match = re.search(r'line (\d+)', error_msg)
        if line_num_match:
            error_line = int(line_num_match.group(1)) - 1
            if 0 <= error_line < len(lines):
                # Try to fix the specific error line
                error_line_content = lines[error_line]
                
                # Common aggressive fixes
                if 'invalid syntax' in error_msg.lower():
                    # Add missing colons, parentheses, etc.
                    if error_line_content.strip() and not error_line_content.strip().endswith(':'):
                        if any(keyword in error_line_content for keyword in ['def ', 'class ', 'if ', 'else', 'elif ', 'for ', 'while ', 'try', 'except', 'finally', 'with ']):
                            lines[error_line] = error_line_content + ':'
                    
                elif 'expected an indented block' in error_msg.lower():
                    # Add pass statement after the error line
                    indent = len(error_line_content) - len(error_line_content.lstrip()) + 4
                    lines.insert(error_line + 1, ' ' * indent + 'pass')
        
        # Last resort: wrap everything in a try-except
        if 'EOF while scanning' in error_msg or 'unterminated' in error_msg:
            # Likely string or bracket issue - add closing characters
            if content.count('"') % 2 == 1:
                content += '"'
            if content.count("'") % 2 == 1:
                content += "'"
            if content.count('(') > content.count(')'):
                content += ')' * (content.count('(') - content.count(')'))
            if content.count('[') > content.count(']'):
                content += ']' * (content.count('[') - content.count(']'))
            if content.count('{') > content.count('}'):
                content += '}' * (content.count('{') - content.count('}'))
        
        return '\n'.join(lines) if isinstance(lines, list) else content

    def fix_directory(self, directory: str) -> Dict[str, int]:
        """Fix all Python files in a directory"""
        directory = Path(directory)
        if not directory.exists():
            print(f"Directory not found: {directory}")
            return {}
        
        python_files = list(directory.rglob("*.py"))
        print(f"Found {len(python_files)} Python files in {directory}")
        
        successful_fixes = 0
        for file_path in python_files:
            try:
                if self.fix_file(str(file_path)):
                    successful_fixes += 1
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        print(f"\nSummary for {directory}:")
        print(f"  Successfully processed: {successful_fixes}/{len(python_files)}")
        print(f"  Failed files: {len(self.failed_files)}")
        
        return {
            'total_files': len(python_files),
            'successful': successful_fixes,
            'failed': len(self.failed_files)
        }

    def print_summary(self):
        """Print summary of all fixes applied"""
        print("\n" + "="*60)
        print("SYNTAX ERROR FIXING SUMMARY")
        print("="*60)
        
        total_fixes = sum(self.fixes_applied.values())
        print(f"Total fixes applied: {total_fixes}")
        print(f"Files processed: {len(self.processed_files)}")
        print(f"Files failed: {len(self.failed_files)}")
        
        print("\nBreakdown of fixes:")
        for fix_type, count in self.fixes_applied.items():
            if count > 0:
                print(f"  {fix_type.replace('_', ' ').title()}: {count}")
        
        if self.failed_files:
            print(f"\nFailed files ({len(self.failed_files)}):")
            for file_path, error in self.failed_files[:10]:  # Show first 10
                print(f"  {file_path}: {error}")
            if len(self.failed_files) > 10:
                print(f"  ... and {len(self.failed_files) - 10} more")


def main():
    """Main execution function"""
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        # Default to key test directories
        directories = [
            "netra_backend/tests",
            "auth_service/tests", 
            "frontend/tests"
        ]
        
        print("Python Syntax Error Auto-Fixer")
        print("="*40)
        print("Processing key test directories...")
        
        total_results = {'total_files': 0, 'successful': 0, 'failed': 0}
        
        for directory in directories:
            if os.path.exists(directory):
                print(f"\nProcessing: {directory}")
                fixer = SyntaxErrorFixer()
                results = fixer.fix_directory(directory)
                
                if results:
                    total_results['total_files'] += results['total_files']
                    total_results['successful'] += results['successful']
                    total_results['failed'] += results['failed']
        
        print(f"\n{'='*60}")
        print("OVERALL SUMMARY")
        print(f"{'='*60}")
        print(f"Total files: {total_results['total_files']}")
        print(f"Successfully processed: {total_results['successful']}")
        print(f"Failed: {total_results['failed']}")
        
        if total_results['failed'] == 0:
            print("\n+ All files processed successfully!")
            sys.exit(0)
        else:
            print(f"\n! {total_results['failed']} files could not be automatically fixed")
            sys.exit(1)
        
        return
    
    print("Python Syntax Error Auto-Fixer")
    print("="*40)
    print(f"Target directory: {directory}")
    print()
    
    fixer = SyntaxErrorFixer()
    results = fixer.fix_directory(directory)
    fixer.print_summary()
    
    # Return exit code based on results
    if results and results['failed'] == 0:
        print("\n+ All files processed successfully!")
        sys.exit(0)
    else:
        print(f"\n! {results.get('failed', 0)} files could not be automatically fixed")
        sys.exit(1)


if __name__ == "__main__":
    main()
