#!/usr/bin/env python3
import os
import ast
import glob

def fix_file_syntax(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            ast.parse(content)
            return False  # Already valid
        except SyntaxError:
            pass
        
        lines = content.split('\n')
        modified = False
        
        # Remove standalone pass statements followed by code
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.strip() == 'pass':
                current_indent = len(line) - len(line.lstrip())
                j = i + 1
                should_remove = False
                
                while j < len(lines) and j < i + 5:
                    next_line = lines[j]
                    if next_line.strip() == '' or next_line.strip().startswith('#'):
                        j += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent >= current_indent and next_line.strip():
                        should_remove = True
                        break
                    else:
                        break
                
                if should_remove:
                    modified = True
                    i += 1
                    continue
            
            new_lines.append(line)
            i += 1
        
        lines = new_lines
        
        # Add pass to empty functions
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().endswith(':') and ('def ' in line or 'class ' in line):
                current_indent = len(line) - len(line.lstrip())
                expected_indent = current_indent + 4
                
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
                        break
                
                if not has_body:
                    lines.insert(i + 1, ' ' * expected_indent + 'pass')
                    modified = True
            i += 1
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    new_content = f.read()
                ast.parse(new_content)
                return True
            except SyntaxError:
                return False
        
        return False
        
    except Exception:
        return False

def main():
    unit_test_dir = 'netra_backend/tests/unit'
    py_files = glob.glob(f'{unit_test_dir}/**/*.py', recursive=True)
    
    fixed_count = 0
    error_files = []
    
    for filepath in py_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            continue
        except SyntaxError:
            error_files.append(filepath)
    
    print(f"Found {len(error_files)} files with syntax errors")
    
    for filepath in error_files[:30]:  # Process 30 files
        print(f"Fixing: {os.path.basename(filepath)}")
        if fix_file_syntax(filepath):
            print("  Fixed")
            fixed_count += 1
        else:
            print("  Could not fix")
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()
