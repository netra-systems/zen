#!/usr/bin/env python3
"""
Targeted syntax error fixer for the specific pass + code pattern
"""

import os
import ast
import glob
import re

def fix_pass_docstring_pattern(filepath):
    """Fix the specific pattern: pass followed by docstring + code"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines()
        new_lines = []
        i = 0
        fixed = False
        
        while i < len(lines):
            line = lines[i]
            
            # Look for the pattern: pass followed by docstring/code
            if line.strip() == 'pass':
                # Check the next few lines for docstrings or code
                j = i + 1
                has_following_content = False
                
                # Look ahead up to 5 lines
                while j < len(lines) and j < i + 5:
                    next_line = lines[j]
                    if next_line.strip() == '' or next_line.strip().startswith('#'):
                        j += 1
                        continue
                    
                    # If we find content (docstring or code) at same or deeper indentation
                    current_indent = len(line) - len(line.lstrip())
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    if (next_indent >= current_indent and 
                        (next_line.strip().startswith('"""') or 
                         next_line.strip().startswith("'''") or
                         'TODO' in next_line or
                         'return' in next_line or
                         'assert' in next_line)):
                        has_following_content = True
                        break
                    elif next_indent <= current_indent:
                        break
                    j += 1
                
                if has_following_content:
                    # Skip the pass statement
                    fixed = True
                    i += 1
                    continue
            
            new_lines.append(line)
            i += 1
        
        if fixed:
            new_content = '\n'.join(new_lines)
            
            # Validate
            try:
                ast.parse(new_content)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True, "Fixed pass+docstring pattern"
            except SyntaxError as e:
                return False, f"Validation failed: {e.msg}"
        
        return False, "No fixes applied"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Fix the specific pass+docstring pattern in all files."""
    test_dir = 'netra_backend/tests/unit'
    py_files = glob.glob(f'{test_dir}/**/*.py', recursive=True)
    
    print(f"Targeting pass+docstring pattern in {len(py_files)} files...")
    
    fixed_count = 0
    
    for filepath in py_files:
        # Only process files with syntax errors
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            continue  # File is valid, skip
        except SyntaxError:
            pass
        
        success, message = fix_pass_docstring_pattern(filepath)
        filename = os.path.basename(filepath)
        
        if success:
            print(f"FIXED: {filename}")
            fixed_count += 1
        elif "No fixes applied" not in message:
            print(f"FAILED: {filename} - {message}")
    
    print(f"\nFixed {fixed_count} files with pass+docstring pattern")

if __name__ == "__main__":
    main()