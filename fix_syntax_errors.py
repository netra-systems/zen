#!/usr/bin/env python3
"""
Automated syntax error fixer for unit test files.
Focuses on common patterns:
1. Functions with 'pass' followed by actual code
2. Missing indented blocks after function definitions
"""

import os
import ast
import glob

def fix_file_syntax(filepath):
    """Fix common syntax errors in a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file already has valid syntax
        try:
            ast.parse(content)
            return False  # Already valid
        except SyntaxError:
            pass  # Continue with fixes
        
        lines = content.split('\n')
        modified = False
        
        # Fix 1: Remove standalone 'pass' statements that are followed by actual code
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.strip() == 'pass':
                # Look ahead to see if there's actual code at same indent level
                current_indent = len(line) - len(line.lstrip())
                j = i + 1
                should_remove_pass = False
                
                # Look for non-empty, non-comment lines
                while j < len(lines) and j < i + 10:  # Look ahead max 10 lines
                    next_line = lines[j]
                    if next_line.strip() == '' or next_line.strip().startswith('#'):
                        j += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    # If we find code at the same level or indented more, remove pass
                    if next_indent >= current_indent and next_line.strip():
                        should_remove_pass = True
                        break
                    else:
                        break
                
                if should_remove_pass:
                    # Skip this pass line
                    modified = True
                    i += 1
                    continue
            
            new_lines.append(line)
            i += 1
        
        lines = new_lines
        
        # Fix 2: Add pass to empty function/class definitions
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().endswith(':') and ('def ' in line or 'class ' in line):
                current_indent = len(line) - len(line.lstrip())
                expected_indent = current_indent + 4
                
                # Check if next non-empty line is properly indented
                j = i + 1
                has_body = False
                while j < len(lines):
                    if j >= len(lines):
                        break
                    next_line = lines[j]
                    if next_line.strip() == '' or next_line.strip().startswith('#'):
                        j += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent > current_indent:
                        has_body = True
                        break
                    else:
                        # No proper body found
                        break
                
                if not has_body:
                    # Insert pass
                    lines.insert(i + 1, ' ' * expected_indent + 'pass')
                    modified = True
            
            i += 1
        
        if modified:
            # Write back the fixed content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            # Verify the fix works
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    new_content = f.read()
                ast.parse(new_content)
                return True
            except SyntaxError:
                return False
        
        return False
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main function to fix syntax errors in unit test files."""
    unit_test_dir = 'netra_backend/tests/unit'
    
    # Get all Python files
    py_files = glob.glob(f'{unit_test_dir}/**/*.py', recursive=True)
    print(f"Found {len(py_files)} Python files")
    
    fixed_count = 0
    error_files = []
    
    for filepath in py_files:
        # Check if file has syntax errors
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            continue  # File is already valid
        except SyntaxError:
            error_files.append(filepath)
    
    print(f"Found {len(error_files)} files with syntax errors")
    
    for filepath in error_files[:50]:  # Process first 50 files
        print(f"Fixing: {filepath}")
        if fix_file_syntax(filepath):
            print(f"  ✓ Fixed")
            fixed_count += 1
        else:
            print(f"  ✗ Could not fix")
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()
