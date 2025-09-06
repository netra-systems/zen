#!/usr/bin/env python3
"""
Final targeted approach - fix files one by one with precise patterns
"""

import os
import ast
import glob

def fix_single_file(filepath):
    """Fix a single file with manual pattern matching."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        new_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Pattern: @pytest.fixture followed by function definition
            if line.strip().startswith('@pytest.fixture'):
                new_lines.append(line)  # Add the decorator
                i += 1
                
                if i < len(lines) and lines[i].strip().startswith('def '):
                    new_lines.append(lines[i])  # Add function definition
                    func_indent = len(lines[i]) - len(lines[i].lstrip())
                    body_indent = func_indent + 4
                    i += 1
                    
                    # Process function body - collect all lines that belong to this function
                    body_lines = []
                    while i < len(lines):
                        current = lines[i]
                        
                        # If we hit another function/class/decorator at the same or higher level, stop
                        if current.strip() and not current.strip().startswith('#'):
                            current_indent = len(current) - len(current.lstrip())
                            if current_indent <= func_indent and (
                                current.strip().startswith('def ') or 
                                current.strip().startswith('class ') or
                                current.strip().startswith('@')):
                                break
                        
                        # Skip empty lines
                        if current.strip() == '':
                            body_lines.append(current)
                            i += 1
                            continue
                            
                        # Fix content lines - ensure proper indentation
                        if (current.strip().startswith('"""') or 
                            current.strip().startswith('#') or
                            current.strip().startswith('return ') or
                            current.strip().startswith('assert ') or
                            current.strip() == 'pass'):
                            
                            fixed_line = ' ' * body_indent + current.strip()
                            body_lines.append(fixed_line)
                            i += 1
                            continue
                            
                        # Keep other lines as-is if they seem properly indented
                        body_lines.append(current)
                        i += 1
                    
                    # Clean up body: remove pass if there's other content
                    non_empty_content = [l for l in body_lines if l.strip() and not l.strip().startswith('#')]
                    if len(non_empty_content) > 1:
                        # Remove standalone pass statements
                        body_lines = [l for l in body_lines if l.strip() != 'pass']
                    
                    # If body is empty, add pass
                    if not any(l.strip() and not l.strip().startswith('#') for l in body_lines):
                        body_lines = [' ' * body_indent + 'pass']
                    
                    new_lines.extend(body_lines)
                    continue
                    
            new_lines.append(line)
            i += 1
        
        new_content = '\n'.join(new_lines)
        
        # Validate and save if successful
        try:
            ast.parse(new_content)
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
            return False
        except SyntaxError:
            return False
            
    except Exception:
        return False

def main():
    """Fix unit test files with targeted approach."""
    # Focus on simpler files first
    test_dir = 'netra_backend/tests/unit'
    all_files = glob.glob(f'{test_dir}/**/*.py', recursive=True)
    
    # Sort by file size to handle simpler files first
    files_with_size = []
    for f in all_files:
        try:
            size = os.path.getsize(f)
            # Only process files with syntax errors
            with open(f, 'r') as file:
                content = file.read()
            ast.parse(content)
            # Skip valid files
        except SyntaxError:
            files_with_size.append((f, size))
        except:
            pass
    
    # Sort by size, handle smaller files first
    files_with_size.sort(key=lambda x: x[1])
    
    fixed_count = 0
    target = 20  # Try to fix 20 files
    
    for filepath, size in files_with_size[:50]:  # Try first 50 files by size
        if fixed_count >= target:
            break
            
        if fix_single_file(filepath):
            filename = os.path.basename(filepath)
            print(f"FIXED: {filename} ({size} bytes)")
            fixed_count += 1
    
    print(f"\\nSuccessfully fixed {fixed_count} files")
    
    # Final count
    remaining_errors = 0
    for filepath in all_files:
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError:
            remaining_errors += 1
    
    print(f"Remaining files with syntax errors: {remaining_errors}")

if __name__ == "__main__":
    main()