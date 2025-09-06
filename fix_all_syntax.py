#!/usr/bin/env python3
"""
Comprehensive syntax error fixer for test files.
"""

import os
import ast
import glob
import re

def fix_syntax_errors(filepath):
    """Fix common syntax errors in Python files."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already valid
        try:
            ast.parse(content)
            return False, "Already valid"
        except SyntaxError:
            pass
        
        lines = content.splitlines()
        modified = False
        
        # Pattern 1: Remove standalone 'pass' when followed by actual code
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.strip() == 'pass':
                # Look ahead for actual code
                current_indent = len(line) - len(line.lstrip())
                j = i + 1
                found_code_at_same_level = False
                
                # Look ahead up to 10 lines
                while j < len(lines) and j < i + 10:
                    next_line = lines[j]
                    if next_line.strip() == '' or next_line.strip().startswith('#'):
                        j += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    # If we find non-empty code at same or greater indentation
                    if next_indent >= current_indent and next_line.strip():
                        found_code_at_same_level = True
                        break
                    else:
                        # Found code at lesser indentation, stop looking
                        break
                
                if found_code_at_same_level:
                    # Skip this 'pass' line
                    modified = True
                    i += 1
                    continue
            
            new_lines.append(line)
            i += 1
        
        lines = new_lines
        
        # Pattern 2: Fix functions with no body
        for i in range(len(lines)):
            line = lines[i]
            if line.strip().endswith(':') and ('def ' in line or 'class ' in line):
                current_indent = len(line) - len(line.lstrip())
                expected_body_indent = current_indent + 4
                
                # Check if there's a body
                j = i + 1
                has_body = False
                while j < len(lines):
                    next_line = lines[j]
                    if next_line.strip() == '' or next_line.strip().startswith('#'):
                        j += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent > current_indent:
                        has_body = True
                        break
                    else:
                        # Found line at same or lesser indent
                        break
                
                if not has_body:
                    # Insert 'pass' at the right indentation
                    lines.insert(i + 1, ' ' * expected_body_indent + 'pass')
                    modified = True
        
        # Pattern 3: Fix indentation errors (common pattern)
        fixed_lines = []
        for line in lines:
            # Fix common indentation issues
            if line.strip().startswith('"""') and line.startswith(' ' * 4):
                # Likely a misplaced docstring
                if fixed_lines and fixed_lines[-1].strip() == 'pass':
                    # Remove the preceding pass
                    fixed_lines.pop()
                    modified = True
            fixed_lines.append(line)
        
        if modified:
            new_content = '\n'.join(fixed_lines)
            
            # Validate the fix
            try:
                ast.parse(new_content)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True, "Fixed successfully"
            except SyntaxError as e:
                return False, f"Fix failed: {e.msg} at line {e.lineno}"
        
        return False, "No fixes applied"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Fix all syntax errors in unit test files."""
    test_dir = 'netra_backend/tests/unit'
    py_files = glob.glob(f'{test_dir}/**/*.py', recursive=True)
    
    print(f"Processing {len(py_files)} files...")
    
    fixed_count = 0
    remaining_errors = 0
    
    for filepath in py_files:
        # Check if file has syntax errors
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            continue  # File is valid
        except SyntaxError:
            pass  # Continue with fixing
        
        success, message = fix_syntax_errors(filepath)
        filename = os.path.basename(filepath)
        
        if success:
            print(f"FIXED: {filename}")
            fixed_count += 1
        else:
            print(f"FAILED: {filename} - {message}")
            remaining_errors += 1
    
    print(f"\nResults:")
    print(f"Fixed: {fixed_count}")
    print(f"Remaining errors: {remaining_errors}")

if __name__ == "__main__":
    main()