#!/usr/bin/env python3
"""
Enhanced syntax error fixer for complex Python test files.
Handles indentation issues, fixture definitions, AsyncNone references, and more.
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set
import traceback

class ComplexSyntaxFixer:
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.patterns_fixed = {
            'indentation_fixes': 0,
            'fixture_fixes': 0,
            'asyncnone_fixes': 0,
            'pass_removal': 0,
            'import_fixes': 0,
            'string_literal_fixes': 0,
            'parenthesis_fixes': 0,
            'comment_fixes': 0,
            'mock_fixes': 0
        }
        
    def fix_indentation_issues(self, lines: List[str]) -> List[str]:
        """Fix various indentation problems."""
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Fix fixture definitions with wrong indentation
            if '@pytest.fixture' in line:
                # Ensure fixture decorator is properly aligned
                indent_match = re.match(r'^(\s*)', line)
                base_indent = indent_match.group(1) if indent_match else ''
                
                fixed_lines.append(line)
                i += 1
                
                # Fix the function definition that follows
                if i < len(lines):
                    next_line = lines[i]
                    if 'def ' in next_line:
                        # Ensure function def has same indentation as fixture
                        function_def = re.sub(r'^\s*', base_indent, next_line)
                        fixed_lines.append(function_def)
                        i += 1
                        
                        # Fix function body indentation
                        func_indent = base_indent + '    '
                        while i < len(lines) and (lines[i].strip() == '' or lines[i].startswith(' ')):
                            if lines[i].strip():
                                body_line = re.sub(r'^\s*', func_indent, lines[i])
                                fixed_lines.append(body_line)
                            else:
                                fixed_lines.append(lines[i])
                            i += 1
                        continue
                    
            # Fix class method indentation
            elif re.match(r'^\s*def test_', line) or re.match(r'^\s*async def test_', line):
                # Check if this is inside a class
                class_indent = self._find_class_indent(fixed_lines)
                if class_indent is not None:
                    method_indent = class_indent + '    '
                    fixed_line = re.sub(r'^\s*', method_indent, line)
                    fixed_lines.append(fixed_line)
                    self.patterns_fixed['indentation_fixes'] += 1
                else:
                    fixed_lines.append(line)
            
            # Fix general indentation mismatches
            elif line.strip() and not line.startswith('#'):
                # Try to detect and fix obvious indentation problems
                if self._is_badly_indented(line, fixed_lines):
                    corrected_indent = self._calculate_correct_indent(line, fixed_lines)
                    if corrected_indent is not None:
                        fixed_line = corrected_indent + line.lstrip()
                        fixed_lines.append(fixed_line)
                        self.patterns_fixed['indentation_fixes'] += 1
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
            
            i += 1
            
        return fixed_lines
    
    def _find_class_indent(self, previous_lines: List[str]) -> str:
        """Find the indentation of the current class context."""
        for line in reversed(previous_lines[-20:]):  # Check last 20 lines
            if re.match(r'^(\s*)class ', line):
                return re.match(r'^(\s*)', line).group(1)
        return None
    
    def _is_badly_indented(self, line: str, previous_lines: List[str]) -> bool:
        """Check if a line has obvious indentation problems."""
        if not previous_lines:
            return False
            
        # Get the last non-empty line
        last_line = None
        for prev_line in reversed(previous_lines):
            if prev_line.strip():
                last_line = prev_line
                break
                
        if not last_line:
            return False
            
        # Check for common indentation problems
        current_indent = len(line) - len(line.lstrip())
        last_indent = len(last_line) - len(last_line.lstrip())
        
        # If current line is a continuation but not properly indented
        if (last_line.rstrip().endswith((':',)) and 
            current_indent <= last_indent):
            return True
            
        return False
    
    def _calculate_correct_indent(self, line: str, previous_lines: List[str]) -> str:
        """Calculate the correct indentation for a line."""
        if not previous_lines:
            return ''
            
        # Find the last line with meaningful content
        for prev_line in reversed(previous_lines):
            if prev_line.strip():
                last_indent = len(prev_line) - len(prev_line.lstrip())
                
                # If previous line ends with colon, increase indent
                if prev_line.rstrip().endswith(':'):
                    return ' ' * (last_indent + 4)
                else:
                    return ' ' * last_indent
                    
        return ''
    
    def fix_asyncnone_references(self, content: str) -> str:
        """Replace AsyncNone with AsyncMock()."""
        patterns = [
            (r'\bAsyncNone\b', 'AsyncMock()'),
            (r'AsyncNone\(\)', 'AsyncMock()'),
            (r'return_value=AsyncNone', 'return_value=AsyncMock()'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                self.patterns_fixed['asyncnone_fixes'] += 1
                
        return content
    
    def fix_pass_statements(self, lines: List[str]) -> List[str]:
        """Remove 'pass' statements that are followed by actual code."""
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            if line.strip() == 'pass':
                # Look ahead to see if there's actual code after this pass
                has_code_after = False
                current_indent = len(line) - len(line.lstrip())
                
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j]
                    if next_line.strip():
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent >= current_indent and not next_line.strip().startswith(('def ', 'class ', '@')):
                            has_code_after = True
                            break
                        elif next_indent < current_indent:
                            break
                
                if has_code_after:
                    # Skip the pass statement
                    self.patterns_fixed['pass_removal'] += 1
                    i += 1
                    continue
            
            fixed_lines.append(line)
            i += 1
            
        return fixed_lines
    
    def fix_import_issues(self, lines: List[str]) -> List[str]:
        """Fix import-related syntax issues."""
        fixed_lines = []
        
        for line in lines:
            # Fix invalid syntax after imports
            if re.match(r'^\s*from .+ import', line) and 'import' in line:
                # Check if line ends properly
                if not line.rstrip().endswith((')', ',')):
                    # Look for common invalid syntax patterns
                    if re.search(r'import \w+\s+[^\w\s,()]', line):
                        # Try to fix the line by removing invalid characters after import
                        line = re.sub(r'(import \w+)\s+[^\w\s,()]+.*', r'\1', line)
                        self.patterns_fixed['import_fixes'] += 1
                        
            fixed_lines.append(line)
            
        return fixed_lines
    
    def fix_string_literals(self, content: str) -> str:
        """Fix unterminated string literals and other string issues."""
        lines = content.split('\n')
        fixed_lines = []
        in_triple_quote = False
        triple_quote_type = None
        
        for i, line in enumerate(lines):
            fixed_line = line
            
            # Handle triple quotes
            if '"""' in line:
                triple_count = line.count('"""')
                if triple_count % 2 == 1:  # Odd number means opening or closing
                    if not in_triple_quote:
                        in_triple_quote = True
                        triple_quote_type = '"""'
                    else:
                        in_triple_quote = False
                        triple_quote_type = None
                elif triple_count > 0 and triple_count % 2 == 0:
                    # Even number could be complete strings on same line
                    pass
            elif "'''" in line:
                triple_count = line.count("'''")
                if triple_count % 2 == 1:  # Odd number means opening or closing
                    if not in_triple_quote:
                        in_triple_quote = True
                        triple_quote_type = "'''"
                    else:
                        in_triple_quote = False
                        triple_quote_type = None
            
            # Fix malformed triple quotes
            if re.match(r'^\s*""""\s*$', line):  # Four quotes instead of three
                fixed_line = re.sub(r'""""', '"""', line)
                self.patterns_fixed['string_literal_fixes'] += 1
            elif re.match(r"^\s*''''\s*$", line):  # Four single quotes
                fixed_line = re.sub(r"''''", "'''", line)
                self.patterns_fixed['string_literal_fixes'] += 1
            
            # Fix unterminated strings with \r at the end
            elif re.search(r'"[^"]*\\r\s*$', line) and not in_triple_quote:
                fixed_line = re.sub(r'"([^"]*\\r)\s*$', r'"\1"', line)
                self.patterns_fixed['string_literal_fixes'] += 1
            
            # Fix strings that start but never end
            elif re.search(r'"[^"]*$', line) and '"' in line and not in_triple_quote:
                quote_count = line.count('"')
                if quote_count % 2 == 1:  # Odd number of quotes
                    fixed_line = line + '"'
                    self.patterns_fixed['string_literal_fixes'] += 1
            
            # Fix specific patterns like 'return anything, that's fine for this test'
            elif "return anything, that's fine for this test" in line:
                fixed_line = re.sub(
                    r"return anything, that's fine for this test",
                    '# return anything, that\'s fine for this test',
                    line
                )
                self.patterns_fixed['string_literal_fixes'] += 1
                
            fixed_lines.append(fixed_line)
            
        return '\n'.join(fixed_lines)
    
    def fix_parenthesis_issues(self, content: str) -> str:
        """Fix unmatched parentheses and brackets."""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            fixed_line = line
            
            # Fix specific patterns like mismatched brackets/parentheses
            if re.search(r'\[.*\}', line):  # [ ... }
                fixed_line = re.sub(r'\}', ']', line)
                self.patterns_fixed['parenthesis_fixes'] += 1
            
            # Fix unclosed parentheses in function calls
            if '(' in line and line.count('(') > line.count(')'):
                # Simple case: add missing closing parenthesis at end
                if line.rstrip().endswith('  # TODO: Use real service instance'):
                    fixed_line = re.sub(r'  # TODO: Use real service instance', ')  # TODO: Use real service instance', line)
                    self.patterns_fixed['parenthesis_fixes'] += 1
                elif re.search(r'\([^)]*  # TODO:', line):
                    fixed_line = re.sub(r'(  # TODO:[^)]*)', r')\1', line)
                    self.patterns_fixed['parenthesis_fixes'] += 1
            
            fixed_lines.append(fixed_line)
            
        return '\n'.join(fixed_lines)
    
    def fix_todo_comments(self, content: str) -> str:
        """Fix TODO comments that break syntax."""
        patterns = [
            # Fix incomplete TODO comments that break function calls
            (r'None  # TODO: Use real service instance\)', 'Mock()  # TODO: Use real service instance)'),
            (r'None  # TODO: Use real service instance', 'Mock()  # TODO: Use real service instance'),
            (r'\(None  # TODO: Use real service instance\)', '(Mock())  # TODO: Use real service instance'),
            
            # Fix syntax errors in TODO comments
            (r'return_value_instance  # Initialize appropriate service\)', 'return_value_instance)  # Initialize appropriate service'),
            (r'mock_db, service\)', 'mock_db, Mock())  # service'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                self.patterns_fixed['comment_fixes'] += 1
                
        return content
    
    def add_missing_imports(self, lines: List[str]) -> List[str]:
        """Add commonly missing imports."""
        content = '\n'.join(lines)
        imports_needed = []
        
        # Check for AsyncMock usage
        if 'AsyncMock' in content and 'from unittest.mock import AsyncMock' not in content:
            imports_needed.append('from unittest.mock import AsyncMock, Mock, patch, MagicMock')
        elif 'Mock' in content and 'from unittest.mock import' not in content:
            imports_needed.append('from unittest.mock import Mock, patch, MagicMock')
            
        # Check for pytest usage
        if '@pytest' in content and 'import pytest' not in content:
            imports_needed.append('import pytest')
            
        # Check for asyncio usage
        if ('async def' in content or 'await ' in content) and 'import asyncio' not in content:
            imports_needed.append('import asyncio')
        
        if imports_needed:
            # Find where to insert imports (after existing imports)
            insert_index = 0
            for i, line in enumerate(lines):
                if line.startswith(('import ', 'from ')) or line.strip().startswith('#'):
                    insert_index = i + 1
                elif line.strip() == '':
                    continue
                else:
                    break
            
            # Insert missing imports
            for imp in imports_needed:
                lines.insert(insert_index, imp)
                insert_index += 1
                self.patterns_fixed['import_fixes'] += 1
            
            # Add empty line after imports if not present
            if insert_index < len(lines) and lines[insert_index].strip() != '':
                lines.insert(insert_index, '')
        
        return lines
    
    def fix_file(self, file_path: Path) -> bool:
        """Fix syntax errors in a single file."""
        try:
            print(f"Processing: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Apply various fixes
            original_content = content
            
            # Fix string literals first
            content = self.fix_string_literals(content)
            
            # Fix parentheses issues
            content = self.fix_parenthesis_issues(content)
            
            # Fix TODO comments
            content = self.fix_todo_comments(content)
            
            # Fix AsyncNone references
            content = self.fix_asyncnone_references(content)
            
            # Split into lines for line-by-line processing
            lines = content.split('\n')
            
            # Fix indentation issues
            lines = self.fix_indentation_issues(lines)
            
            # Remove unnecessary pass statements
            lines = self.fix_pass_statements(lines)
            
            # Fix import issues
            lines = self.fix_import_issues(lines)
            
            # Add missing imports
            lines = self.add_missing_imports(lines)
            
            # Rejoin content
            fixed_content = '\n'.join(lines)
            
            # Only write if we made changes
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                # Try to compile to verify fix
                try:
                    compile(fixed_content, str(file_path), 'exec')
                    self.fixed_files.append(str(file_path))
                    print(f"FIXED: {file_path}")
                    return True
                except SyntaxError as e:
                    print(f"WARNING: Still has errors after fix: {file_path} - {e}")
                    return False
            else:
                print(f"- No changes needed: {file_path}")
                return True
                
        except Exception as e:
            print(f"ERROR processing {file_path}: {e}")
            self.failed_files.append(str(file_path))
            return False
    
    def process_directories(self, directories: List[str]) -> None:
        """Process all Python files in specified directories."""
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                print(f"Directory not found: {directory}")
                continue
                
            print(f"\nProcessing directory: {directory}")
            
            # Find all Python test files
            py_files = list(dir_path.glob('**/*.py'))
            py_files = [f for f in py_files if f.name.startswith('test_') or '/test_' in str(f)]
            
            print(f"Found {len(py_files)} test files")
            
            for py_file in sorted(py_files):
                self.fix_file(py_file)
    
    def print_summary(self) -> None:
        """Print summary of fixes applied."""
        print("\n" + "="*50)
        print("SYNTAX ERROR FIX SUMMARY")
        print("="*50)
        
        print(f"Fixed files: {len(self.fixed_files)}")
        print(f"Failed files: {len(self.failed_files)}")
        
        print("\nPatterns fixed:")
        for pattern, count in self.patterns_fixed.items():
            if count > 0:
                print(f"  {pattern}: {count}")
        
        if self.failed_files:
            print(f"\nFiles that still need attention:")
            for file in self.failed_files[:10]:  # Show first 10
                print(f"  {file}")
            if len(self.failed_files) > 10:
                print(f"  ... and {len(self.failed_files) - 10} more")

def main():
    """Main execution function."""
    # Priority directories with most critical errors
    directories = [
        'netra_backend/tests/critical',
        'netra_backend/tests/agents',
        'netra_backend/tests/e2e',
        'netra_backend/tests/integration',
        'netra_backend/tests/auth_integration',
        'netra_backend/tests/compliance',
        'netra_backend/tests/config',
        'netra_backend/tests/core',
        'netra_backend/tests/database',
        'netra_backend/tests/clickhouse',
    ]
    
    fixer = ComplexSyntaxFixer()
    
    print("Enhanced Python Syntax Error Fixer")
    print("="*50)
    print("Fixing complex patterns:")
    print("- Fixture definitions with wrong indentation")
    print("- AsyncNone references -> AsyncMock()")
    print("- Functions with 'pass' followed by actual code")
    print("- Missing mock imports")
    print("- Misaligned test methods in classes")
    print("- Unterminated string literals")
    print("- Unmatched parentheses")
    print("- TODO comment syntax errors")
    print()
    
    fixer.process_directories(directories)
    fixer.print_summary()

if __name__ == "__main__":
    main()