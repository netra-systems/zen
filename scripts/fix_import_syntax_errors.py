#!/usr/bin/env python3
"""
Fix import syntax errors throughout the codebase.
This script identifies and fixes common import syntax issues where
imports are incorrectly split across lines.
"""

import os
import re
import ast


def fix_import_syntax_in_file(filepath):
    """Fix import syntax errors in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Test if file already parses correctly
        try:
            ast.parse(content)
            return False, "File already parses correctly"
        except SyntaxError:
            pass  # File needs fixing
        
        # Split into lines for processing
        lines = content.split('\n')
        fixed_lines = []
        i = 0
        changes_made = False
        
        while i < len(lines):
            line = lines[i]
            
            # Pattern 1: Import statement followed by incorrectly indented continuation
            if ('from ' in line and ' import ' in line and 
                i + 1 < len(lines) and lines[i + 1].strip() and 
                not lines[i + 1].startswith((' ', '\t')) == False and
                lines[i + 1].strip() != ')' and
                not lines[i + 1].strip().startswith('#')):
                
                # Check if next line looks like a continuation of imports
                next_line = lines[i + 1].strip()
                if (next_line and not next_line.startswith('from ') and 
                    not next_line.startswith('import ') and
                    not next_line.startswith('@') and
                    not next_line.startswith('class ') and
                    not next_line.startswith('def ') and
                    not next_line.startswith('if ') and
                    not next_line.startswith('logger =')):
                    
                    # Look for closing paren on subsequent lines
                    j = i + 1
                    import_items = []
                    found_closing_paren = False
                    
                    while j < len(lines) and j < i + 5:  # Limit search
                        check_line = lines[j].strip()
                        if check_line == ')':
                            found_closing_paren = True
                            # Collect import items from intermediate lines
                            for k in range(i + 1, j):
                                item_line = lines[k].strip()
                                if item_line and not item_line.startswith('#'):
                                    import_items.append(item_line.rstrip(','))
                            break
                        elif check_line and not check_line.startswith('#'):
                            import_items.append(check_line.rstrip(','))
                        j += 1
                    
                    if found_closing_paren and import_items:
                        # Reconstruct the import statement
                        base_import = line.rstrip()
                        if not base_import.endswith('('):
                            base_import += ' ('
                        else:
                            base_import = base_import[:-1] + '('
                        
                        fixed_lines.append(base_import)
                        for item in import_items:
                            if item:
                                fixed_lines.append(f'    {item}')
                        fixed_lines.append(')')
                        
                        # Skip processed lines
                        i = j + 1
                        changes_made = True
                        continue
            
            fixed_lines.append(line)
            i += 1
        
        if changes_made:
            new_content = '\n'.join(fixed_lines)
            
            # Test if the fix worked
            try:
                ast.parse(new_content)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True, "Fixed import syntax"
            except SyntaxError as e:
                return False, f"Fix failed, still has syntax error: {e}"
        
        return False, "No import syntax issues found"
        
    except Exception as e:
        return False, f"Error processing file: {e}"


def main():
    """Fix import syntax errors in all Python files."""
    root_dir = '.'
    fixed_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', '.venv'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, root_dir)
                
                success, message = fix_import_syntax_in_file(filepath)
                if success:
                    print(f"[FIXED] {rel_path}")
                    fixed_count += 1
                elif "syntax error" in message.lower():
                    print(f"[ERROR] {rel_path} - {message}")
                    error_count += 1
    
    print(f"\nSummary:")
    print(f"Files fixed: {fixed_count}")
    print(f"Files with remaining errors: {error_count}")


if __name__ == "__main__":
    main()