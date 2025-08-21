#!/usr/bin/env python3
"""Script to fix common syntax errors in test files"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple


def fix_unclosed_parenthesis(content: str) -> str:
    """Fix unclosed parenthesis in import statements"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for import statements with unclosed parentheses
        if ('from ' in line and '(' in line) or ('import ' in line and '(' in line):
            paren_count = line.count('(') - line.count(')')
            
            if paren_count > 0:
                # Found unclosed parenthesis - look for the end or close it
                import_lines = [line]
                j = i + 1
                
                while j < len(lines) and paren_count > 0:
                    next_line = lines[j]
                    paren_count += next_line.count('(') - next_line.count(')')
                    import_lines.append(next_line)
                    j += 1
                
                # If we still have unclosed parentheses, close them
                if paren_count > 0:
                    import_lines[-1] = import_lines[-1].rstrip() + ')'
                
                fixed_lines.extend(import_lines)
                i = j
                continue
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)

def fix_orphaned_methods(content: str) -> str:
    """Fix methods without class definitions"""
    lines = content.split('\n')
    
    # Look for orphaned methods (functions at wrong indentation)
    orphaned_method_found = False
    first_orphan_line = -1
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Look for methods that start with spaces but no class above them
        if line.startswith('    def ') or (stripped.startswith('def ') and line.startswith('    ')):
            # Check if there's a class definition above this line
            has_class_above = False
            for j in range(i-1, -1, -1):
                prev_line = lines[j].strip()
                if prev_line.startswith('class '):
                    has_class_above = True
                    break
                elif prev_line.startswith('def ') and not lines[j].startswith('    '):
                    break
            
            if not has_class_above:
                orphaned_method_found = True
                if first_orphan_line == -1:
                    first_orphan_line = i
                break
    
    if orphaned_method_found:
        # Find where to insert the class (after imports/docstrings)
        insert_pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped and 
                not stripped.startswith('#') and 
                not stripped.startswith('"""') and
                not stripped.startswith("'''") and
                not stripped.startswith('import ') and 
                not stripped.startswith('from ') and
                not line.startswith('"""') and
                not line.startswith("'''")):
                insert_pos = i
                break
        
        # Insert a test class before the orphaned methods
        lines.insert(insert_pos, '')
        lines.insert(insert_pos + 1, 'class TestSyntaxFix:')
        lines.insert(insert_pos + 2, '    """Test class for orphaned methods"""')
        lines.insert(insert_pos + 3, '')
    
    return '\n'.join(lines)

def fix_incomplete_imports(content: str) -> str:
    """Fix incomplete import statements"""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix common incomplete import patterns
        if line.strip().startswith('from ') and line.strip().endswith('('):
            # Line ends with open paren but no closing paren
            if i + 1 < len(lines) and not lines[i + 1].strip():
                # Next line is empty, close the import
                line = line.rstrip() + ')'
        elif line.strip() == 'from' or line.strip().endswith('from'):
            # Incomplete 'from' statement
            line = '# ' + line + ' # Incomplete import statement'
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_unexpected_indent(content: str) -> str:
    """Fix unexpected indentation issues"""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # If line starts with spaces but previous meaningful line doesn't establish context
        if line.startswith('    ') and line.strip():
            # Check if this could be an orphaned method/function definition
            if i > 0:
                # Look back to find the last non-empty line
                prev_meaningful = None
                for j in range(i-1, -1, -1):
                    if lines[j].strip():
                        prev_meaningful = lines[j]
                        break
                
                # If previous line doesn't establish indentation context, this might be orphaned
                if (prev_meaningful and 
                    not prev_meaningful.strip().endswith(':') and
                    not prev_meaningful.startswith('    ') and
                    not prev_meaningful.strip().startswith('class ') and
                    not prev_meaningful.strip().startswith('def ') and
                    line.strip().startswith('def ')):
                    
                    # This looks like an orphaned method - it will be caught by fix_orphaned_methods
                    pass
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_invalid_syntax(content: str) -> str:
    """Fix various invalid syntax issues"""
    lines = content.split('\n')
    fixed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Fix incomplete import statements that end abruptly
        if ('from ' in line and 
            ('import (' in line or line.strip().endswith('(')) and
            i + 1 < len(lines)):
            
            # Look for the pattern where import statement is cut off
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            
            # If next line starts with a new statement, close the import
            if (next_line.strip().startswith('from ') or 
                next_line.strip().startswith('import ') or
                next_line.strip().startswith('class ') or
                next_line.strip().startswith('def ') or
                not next_line.strip()):
                
                if not line.strip().endswith(')'):
                    line = line.rstrip() + ')'
        
        fixed_lines.append(line)
        i += 1
    
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
    """Fix common syntax errors in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply fixes in order of complexity
        content = fix_incomplete_imports(content)
        content = fix_unclosed_parenthesis(content)
        content = fix_invalid_syntax(content)
        content = fix_unexpected_indent(content)
        content = fix_orphaned_methods(content)
        
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
    """Main function to fix syntax errors in test files"""
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
    
    print(f"Found {len(test_files)} test files")
    
    # Check for syntax errors
    files_with_errors = []
    for filepath in test_files:
        errors = check_syntax(filepath)
        if errors:
            files_with_errors.append((filepath, errors))
    
    print(f"Found {len(files_with_errors)} files with syntax errors")
    
    # Fix errors
    fixed_count = 0
    for filepath, errors in files_with_errors:
        if fix_file(filepath):
            fixed_count += 1
            print(f"Fixed: {filepath}")
    
    print(f"\nFixed {fixed_count} files")
    
    # Re-check for remaining errors
    remaining_errors = []
    for filepath, _ in files_with_errors:
        errors = check_syntax(filepath)
        if errors:
            remaining_errors.extend(errors)
    
    if remaining_errors:
        print(f"\n{len(remaining_errors)} syntax errors remain:")
        for error in remaining_errors[:10]:  # Show first 10
            print(f"  - {error}")
    else:
        print("\nAll syntax errors fixed!")

if __name__ == '__main__':
    main()