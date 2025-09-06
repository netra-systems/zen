import os
import re
import ast
from pathlib import Path

def fix_empty_functions(content):
    """Add pass to empty function bodies."""
    lines = content.split('\n')
    fixed = []
    
    for i, line in enumerate(lines):
        fixed.append(line)
        # Check for function/class definition
        if re.match(r'^\s*(async\s+)?def\s+\w+.*:|^\s*class\s+\w+.*:', line):
            # Check if next line needs pass
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if i + 1 == len(lines) - 1 or (next_line and not next_line.strip()):
                    # Add pass with proper indentation
                    indent = len(line) - len(line.lstrip()) + 4
                    fixed.append(' ' * indent + 'pass')
            elif i + 1 == len(lines):
                # Function at end of file
                indent = len(line) - len(line.lstrip()) + 4
                fixed.append(' ' * indent + 'pass')
    
    return '\n'.join(fixed)

def fix_unterminated_strings(content):
    """Fix unterminated string literals."""
    lines = content.split('\n')
    fixed = []
    
    for i, line in enumerate(lines):
        # Count quotes in line
        single_quotes = line.count("'") - line.count("\'")
        double_quotes = line.count('"') - line.count('\\"')
        
        # Fix odd number of quotes
        if single_quotes % 2 == 1:
            line = line + "'"
        if double_quotes % 2 == 1:
            line = line + '"'
        
        fixed.append(line)
    
    return '\n'.join(fixed)

def aggressive_indent_fix(content):
    """More aggressive indentation fixing."""
    lines = content.split('\n')
    fixed = []
    indent_level = 0
    
    for line in lines:
        stripped = line.lstrip()
        
        if not stripped or stripped.startswith('#'):
            fixed.append(line)
            continue
        
        # Decrease indent for dedent keywords
        if stripped.startswith(('return', 'break', 'continue', 'pass')):
            if indent_level > 0:
                fixed.append(' ' * (indent_level * 4) + stripped)
            else:
                fixed.append(stripped)
        elif stripped.startswith(('elif', 'else:', 'except', 'finally')):
            if indent_level > 0:
                indent_level -= 1
            fixed.append(' ' * (indent_level * 4) + stripped)
            indent_level += 1
        elif stripped.endswith(':'):
            # Block statement
            fixed.append(' ' * (indent_level * 4) + stripped)
            indent_level += 1
        else:
            # Regular statement
            fixed.append(' ' * (indent_level * 4) + stripped)
        
        # Reset indent after certain statements
        if stripped.startswith('return ') or stripped == 'return':
            if indent_level > 0:
                indent_level -= 1
    
    return '\n'.join(fixed)

def fix_file(filepath):
    """Try to fix a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Apply fixes
        content = fix_unterminated_strings(content)
        content = fix_empty_functions(content) 
        content = aggressive_indent_fix(content)
        
        # Try to parse
        try:
            ast.parse(content)
            # Save if successful
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except:
            return False
    except:
        return False

# Process all test files
test_dirs = ['netra_backend/tests', 'auth_service/tests', 'tests']
fixed_count = 0
total_errors = 0

for test_dir in test_dirs:
    if not os.path.exists(test_dir):
        continue
    
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        ast.parse(f.read())
                except:
                    total_errors += 1
                    if fix_file(filepath):
                        fixed_count += 1
                        print(f"Fixed: {filepath}")

print(f"\nFixed {fixed_count} out of {total_errors} files with errors")
