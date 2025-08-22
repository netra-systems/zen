#!/usr/bin/env python3
"""
Fix all import syntax errors in the codebase by recognizing multiple patterns.
"""

import os
import re
import ast


def fix_import_syntax_patterns(content):
    """Fix various import syntax patterns that cause syntax errors."""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    changes_made = False
    
    while i < len(lines):
        line = lines[i]
        
        # Pattern 1: Single line import with continuation on next lines and closing paren
        if ('from ' in line and ' import ' in line and 
            i + 1 < len(lines) and not line.strip().endswith('(')):
            
            # Look ahead to find pattern: items on next line(s) followed by ')'
            j = i + 1
            import_items = []
            found_closing_paren = False
            
            # Scan up to 5 lines ahead for closing paren
            while j < len(lines) and j < i + 6:
                check_line = lines[j].strip()
                
                if check_line == ')':
                    found_closing_paren = True
                    break
                elif (check_line and not check_line.startswith('#') and 
                      not check_line.startswith('from ') and
                      not check_line.startswith('import ') and
                      not check_line.startswith('class ') and
                      not check_line.startswith('def ') and
                      not check_line.startswith('logger =')):
                    # This looks like an import item
                    import_items.append(check_line.rstrip(','))
                j += 1
            
            if found_closing_paren and import_items:
                # Reconstruct as proper multi-line import
                base_import = line.strip()
                if not base_import.endswith('('):
                    # Add opening paren
                    if ', ' in base_import:
                        # Has existing imports, need to move them to new lines
                        parts = base_import.split(' import ')
                        module_part = parts[0] + ' import ('
                        existing_imports = parts[1] if len(parts) > 1 else ''
                        
                        fixed_lines.append(module_part)
                        if existing_imports.strip():
                            fixed_lines.append(f'    {existing_imports.rstrip(",")},')
                    else:
                        # Simple case
                        fixed_lines.append(base_import.replace(' import ', ' import ('))
                else:
                    fixed_lines.append(base_import)
                
                # Add import items
                for item in import_items:
                    if item.strip():
                        fixed_lines.append(f'    {item.strip()}')
                
                fixed_lines.append(')')
                
                # Skip processed lines
                i = j + 1
                changes_made = True
                continue
        
        fixed_lines.append(line)
        i += 1
    
    if changes_made:
        return '\n'.join(fixed_lines), True
    return content, False


def fix_file(filepath):
    """Fix import syntax in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        # Try to parse original - if it works, no fix needed
        try:
            ast.parse(original_content)
            return False, "Already valid"
        except SyntaxError:
            pass
        
        # Apply fixes
        new_content, changed = fix_import_syntax_patterns(original_content)
        
        if changed:
            # Test if fix worked
            try:
                ast.parse(new_content)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True, "Fixed"
            except SyntaxError as e:
                return False, f"Fix failed: {e}"
        
        return False, "No patterns matched"
        
    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Fix import syntax errors in all Python files."""
    fixed_files = []
    error_files = []
    
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', '.venv'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, '.')
                
                success, message = fix_file(filepath)
                if success:
                    print(f"Fixed: {rel_path}")
                    fixed_files.append(rel_path)
                elif "Fix failed" in message or "error" in message.lower():
                    print(f"Error: {rel_path} - {message}")
                    error_files.append((rel_path, message))
    
    print(f"\nSummary:")
    print(f"Files fixed: {len(fixed_files)}")
    print(f"Files with errors: {len(error_files)}")
    
    if error_files:
        print(f"\nFiles still with errors:")
        for file, error in error_files[:10]:  # Show first 10
            print(f"  {file}: {error}")


if __name__ == "__main__":
    main()