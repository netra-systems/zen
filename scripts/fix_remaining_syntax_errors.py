#!/usr/bin/env python3
"""Script to fix remaining specific syntax errors in test files"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple


def fix_empty_imports(content: str) -> str:
    """Fix empty import statements like 'from module import ()'"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix empty import statements
        if re.match(r'from\s+\S+\s+import\s*\(\s*\)', line):
            # Comment out empty import
            line = '# ' + line + ' # Empty import statement'
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_unmatched_parentheses(content: str) -> str:
    """Fix unmatched closing parentheses"""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check for standalone closing parenthesis
        if line.strip() == ')':
            # This is likely an orphaned closing paren - comment it out
            line = '# )  # Orphaned closing parenthesis'
        elif line.strip().endswith(')') and line.strip() != ')':
            # Check if this line has unmatched closing paren
            open_count = line.count('(')
            close_count = line.count(')')
            if close_count > open_count:
                # Remove extra closing paren
                extra_parens = close_count - open_count
                for _ in range(extra_parens):
                    line = line.rsplit(')', 1)[0]
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_docstring_in_class(content: str) -> str:
    """Fix cases where docstring got mixed up with class definition"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Look for pattern where class definition is followed by unindented content
        if line.strip().startswith('class '):
            fixed_lines.append(line)
            i += 1
            
            # Add proper indentation for docstring
            if i < len(lines) and lines[i].strip().startswith('"""'):
                fixed_lines.append('    ' + lines[i].strip())
                i += 1
                continue
                
            # Look for content that should be indented
            while i < len(lines):
                next_line = lines[i]
                stripped = next_line.strip()
                
                if not stripped:
                    fixed_lines.append(next_line)
                    i += 1
                    continue
                    
                # If it's a docstring, comment, or business value content, indent it
                if (stripped.startswith('Business Value') or
                    stripped.startswith('**Business Value') or
                    stripped.startswith('- Segment:') or
                    stripped.startswith('- Business Goal:') or
                    stripped.startswith('- Value Impact:') or
                    stripped.startswith('- Revenue Impact:') or
                    stripped.startswith('This module') or
                    stripped.startswith('Tests ') or
                    stripped.startswith('ARCHITECTURE:') or
                    stripped.startswith('COMPLIANCE:') or
                    stripped.startswith('Features:') or
                    stripped.startswith('Each function')):
                    # Indent this line as it's part of the docstring
                    fixed_lines.append('    ' + stripped)
                else:
                    # Not part of the class content, continue normally
                    break
                i += 1
            continue
        else:
            fixed_lines.append(line)
            i += 1
    
    return '\n'.join(fixed_lines)

def fix_file_structure_issues(content: str) -> str:
    """Fix structural issues in files"""
    lines = content.split('\n')
    fixed_lines = []
    
    # Remove "No newline at end of file" messages
    lines = [line for line in lines if line.strip() != " No newline at end of file"]
    
    # Fix missing closing braces for dictionaries
    for i, line in enumerate(lines):
        if line.strip().endswith('"postgres_host": os.environ.get("TEST_POSTGRES_HOST", "localhost"),'):
            # This looks like an incomplete dictionary - check if we need to add closing brace
            # Look ahead to see if there's more content
            j = i + 1
            needs_closing = True
            while j < len(lines):
                if lines[j].strip() and not lines[j].strip().startswith('"'):
                    needs_closing = True
                    break
                elif lines[j].strip().endswith('}'):
                    needs_closing = False
                    break
                j += 1
            
            if needs_closing:
                # Add the missing dictionary content
                fixed_lines.append(line)
                fixed_lines.append('            "postgres_port": os.environ.get("TEST_POSTGRES_PORT", "5432"),')
                fixed_lines.append('            "clickhouse_host": os.environ.get("TEST_CLICKHOUSE_HOST", "localhost"),')
                fixed_lines.append('            "clickhouse_port": os.environ.get("TEST_CLICKHOUSE_PORT", "8123")')
                fixed_lines.append('        }')
                continue
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def check_syntax(filepath: Path) -> List[str]:
    """Check if file has syntax errors"""
    errors = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"{filepath}: {e.msg} at line {e.lineno}")
    except Exception as e:
        errors.append(f"{filepath}: {str(e)}")
    return errors

def fix_file(filepath: Path) -> bool:
    """Fix remaining syntax errors in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply specific fixes
        content = fix_empty_imports(content)
        content = fix_unmatched_parentheses(content)
        content = fix_docstring_in_class(content)
        content = fix_file_structure_issues(content)
        
        # Only write if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def main():
    """Main function to fix remaining syntax errors"""
    test_dirs = [
        Path('app/tests'),
        Path('tests'),
        Path('auth_service/tests'),
        Path('integration_tests')
    ]
    
    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            test_files.extend(test_dir.glob('**/*.py'))
    
    print(f"Checking {len(test_files)} test files for remaining syntax errors...")
    
    # Check for syntax errors
    files_with_errors = []
    for filepath in test_files:
        errors = check_syntax(filepath)
        if errors:
            files_with_errors.append((filepath, errors))
    
    print(f"Found {len(files_with_errors)} files with syntax errors")
    
    if not files_with_errors:
        print("No syntax errors found!")
        return
    
    # Fix errors
    fixed_count = 0
    for filepath, errors in files_with_errors:
        print(f"Fixing: {filepath}")
        for error in errors:
            print(f"  Error: {error}")
        
        if fix_file(filepath):
            fixed_count += 1
            print(f"  -> Fixed")
        else:
            print(f"  -> No changes made")
    
    print(f"\nProcessed {fixed_count} files")
    
    # Re-check for remaining errors
    print("\nRe-checking for remaining errors...")
    remaining_errors = []
    for filepath, _ in files_with_errors:
        errors = check_syntax(filepath)
        if errors:
            remaining_errors.extend([(filepath, error) for error in errors])
    
    if remaining_errors:
        print(f"\n{len(remaining_errors)} syntax errors still remain:")
        for filepath, error in remaining_errors[:20]:  # Show first 20
            print(f"  - {error}")
        if len(remaining_errors) > 20:
            print(f"  ... and {len(remaining_errors) - 20} more")
    else:
        print("\nAll syntax errors fixed!")

if __name__ == '__main__':
    main()