#!/usr/bin/env python3
"""
Advanced syntax error fixer for complex indentation issues
"""

import os
import ast
import glob
import re

def fix_indentation_issues(filepath):
    """Fix complex indentation and pass statement issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines()
        new_lines = []
        i = 0
        fixed = False
        
        while i < len(lines):
            line = lines[i]
            
            # Pattern 1: Function definition followed by misplaced docstring/code
            if line.strip().endswith(':') and ('def ' in line or 'class ' in line):
                function_indent = len(line) - len(line.lstrip())
                expected_body_indent = function_indent + 4
                
                new_lines.append(line)
                i += 1
                
                # Collect lines that should be in the function body
                body_lines = []
                while i < len(lines):
                    next_line = lines[i]
                    
                    # Skip empty lines and comments
                    if next_line.strip() == '' or next_line.strip().startswith('#'):
                        new_lines.append(next_line)
                        i += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    # If this line is at function level or less, stop collecting body
                    if next_indent <= function_indent:
                        break
                    
                    # Collect body lines that might be misaligned
                    if (next_line.strip().startswith('"""') or 
                        next_line.strip().startswith("'''") or
                        'TODO' in next_line or
                        next_line.strip() == 'pass' or
                        'return ' in next_line or
                        'assert ' in next_line):
                        
                        # Fix the indentation to match expected body indent
                        fixed_line = ' ' * expected_body_indent + next_line.strip()
                        body_lines.append(fixed_line)
                        fixed = True
                        i += 1
                    else:
                        # This might be a line that's already properly indented
                        body_lines.append(next_line)
                        i += 1
                
                # Remove standalone pass if there's other content
                if len(body_lines) > 1:
                    body_lines = [line for line in body_lines if line.strip() != 'pass']
                    fixed = True
                
                # If no body, add pass
                if not body_lines:
                    body_lines = [' ' * expected_body_indent + 'pass']
                    fixed = True
                
                new_lines.extend(body_lines)
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
                return True, "Fixed indentation issues"
            except SyntaxError as e:
                return False, f"Validation failed: {e.msg} at line {e.lineno}"
        
        return False, "No fixes needed"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Fix indentation issues in test files."""
    test_dir = 'netra_backend/tests/unit'
    py_files = glob.glob(f'{test_dir}/**/*.py', recursive=True)[:30]  # Process first 30
    
    print(f"Processing {len(py_files)} files with advanced indentation fix...")
    
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
        
        success, message = fix_indentation_issues(filepath)
        filename = os.path.basename(filepath)
        
        if success:
            print(f"FIXED: {filename}")
            fixed_count += 1
        elif "No fixes needed" not in message:
            print(f"FAILED: {filename} - {message}")
    
    print(f"\nFixed {fixed_count} files with advanced indentation fix")

if __name__ == "__main__":
    main()