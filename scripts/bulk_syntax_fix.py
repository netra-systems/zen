#!/usr/bin/env python3
"""
Comprehensive syntax error fixer for test files.
Handles all the common patterns found in the e2e test directory.
"""

import ast
import re
import os
import sys
from pathlib import Path
from typing import List, Tuple


def fix_all_syntax_issues(content: str) -> str:
    """Apply all syntax fixes to content."""
    
    # Split into lines for processing
    lines = content.split('\n')
    
    # Process line by line
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip empty lines
        if not line.strip():
            fixed_lines.append(line)
            i += 1
            continue
        
        # Fix import statement issues
        if line.strip().startswith(('from ', 'import ')):
            # Check for unclosed parentheses in imports
            if '(' in line and ')' not in line:
                # Look ahead for the closing parenthesis
                j = i + 1
                import_lines = [line]
                while j < len(lines) and ')' not in lines[j]:
                    import_lines.append(lines[j])
                    j += 1
                if j < len(lines):
                    import_lines.append(lines[j])
                    # Reconstruct the import
                    full_import = '\n'.join(import_lines)
                    if full_import.count('(') > full_import.count(')'):
                        import_lines[-1] += ')'
                    fixed_lines.extend(import_lines)
                    i = j + 1
                    continue
            # Fix malformed imports
            if line.strip().endswith(',') and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('from ') or next_line.startswith('import '):
                    # Missing closing paren
                    fixed_lines.append(line + ')')
                    i += 1
                    continue
                    
        # Fix empty class/function definitions
        if line.strip().endswith(':'):
            # Check if next line is properly indented
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                current_indent = len(line) - len(line.lstrip())
                expected_indent = current_indent + 4
                
                if (not next_line.strip() or 
                    not next_line.startswith(' ' * expected_indent) or
                    next_line.strip().startswith('#')):
                    # Add pass statement
                    fixed_lines.append(line)
                    fixed_lines.append(' ' * expected_indent + 'pass')
                    i += 1
                    continue
        
        # Fix unclosed brackets/parentheses
        if line.count('(') > line.count(')'):
            line += ')' * (line.count('(') - line.count(')'))
        elif line.count('{') > line.count('}'):
            line = line.replace('{', '{').replace(')', '}')
            
        # Fix unexpected indentation
        if line.startswith('    ') and i > 0:
            prev_line = lines[i - 1].strip()
            if prev_line and not prev_line.endswith((':', '\\', ',')):
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ', 'class ', 'def ', 'async def')):
                    line = stripped
        
        # Fix syntax issues specific to our files
        line = re.sub(r'#\s*#\s*([^#]+)# Possibly broken comprehension', r'\1', line)
        line = re.sub(r'#\s+([^#\n]+)# Possibly broken comprehension', r'\1', line)
        
        fixed_lines.append(line)
        i += 1
    
    # Join back to content
    fixed_content = '\n'.join(fixed_lines)
    
    # Fix specific patterns
    patterns = [
        # Fix mismatched brackets
        (r'\{([^}]*)\)', r'{\1}'),
        (r'\{([^}]*)\]', r'{\1}'),
        # Fix function definition splits
        (r'async def ([^(]+)\(\s*\):\s*\n\s*([^:]+):', r'async def \1(\2):'),
        (r'def ([^(]+)\(\s*\):\s*\n\s*([^:]+):', r'def \1(\2):'),
    ]
    
    for pattern, replacement in patterns:
        fixed_content = re.sub(pattern, replacement, fixed_content)
    
    # Fix unterminated strings
    if fixed_content.count('"""') % 2 == 1:
        fixed_content += '\n"""'
    if fixed_content.count("'''") % 2 == 1:
        fixed_content += "\n'''"
    
    return fixed_content


def validate_syntax(file_path: str) -> Tuple[bool, str]:
    """Validate Python syntax using ast.parse."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error: {e}"


def fix_file(file_path: str) -> bool:
    """Fix syntax errors in a file."""
    try:
        # Read original content
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Apply fixes
        fixed_content = fix_all_syntax_issues(original_content)
        
        # Only write if there are changes
        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            # Validate the fix
            is_valid, error = validate_syntax(file_path)
            if is_valid:
                print(f"[FIXED] {file_path}")
                return True
            else:
                # Restore original if fix didn't work
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                print(f"[FAILED] {file_path} - {error}")
                return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python bulk_syntax_fix.py <directory>")
        sys.exit(1)
    
    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)
    
    # Get all Python files with syntax errors
    python_files = list(directory.rglob("*.py"))
    
    syntax_error_files = []
    for file_path in python_files:
        is_valid, _ = validate_syntax(str(file_path))
        if not is_valid:
            syntax_error_files.append(str(file_path))
    
    if not syntax_error_files:
        print("No syntax errors found!")
        return
    
    print(f"Found {len(syntax_error_files)} files with syntax errors")
    
    # Fix files
    fixed_count = 0
    for file_path in syntax_error_files:
        if fix_file(file_path):
            fixed_count += 1
    
    print(f"\nResults: Fixed {fixed_count}/{len(syntax_error_files)} files")


if __name__ == "__main__":
    main()