#!/usr/bin/env python3
"""
Batch fix for the most common syntax patterns
"""

import os
import ast
import glob

def fix_file_patterns(filepath):
    """Fix common test file patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply several regex-based fixes for common patterns
        fixes = [
            # Pattern 1: def function(): followed by misplaced docstring and pass
            (r'(@pytest\.fixture\s*\n\s*def \w+\(.*?\):\s*\n)(\s*""".*?"""\s*\n\s*# TODO.*?\n\s*""".*?"""\s*\n)\s*pass\s*\n(\s*return .*?)', 
             r'\1        \2        \3'),
             
            # Pattern 2: def function(): followed by docstring on wrong line
            (r'(@pytest\.fixture\s*\n\s*def \w+\(.*?\):\s*\n)([^\s].*?"""\s*\n\s*# TODO.*?\n\s*""".*?"""\s*\n)\s*pass\s*\n(\s*return .*?)', 
             r'\1        \2        \3'),
        ]
        
        # Try simple line-by-line fixes
        lines = content.split('\n')
        new_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Fix pattern: function definition followed by unindented docstring
            if (line.strip().startswith('@pytest.fixture') and 
                i + 1 < len(lines) and 
                lines[i+1].strip().startswith('def ')):
                
                # Add the decorator and function line
                new_lines.append(line)
                new_lines.append(lines[i+1])
                i += 2
                
                # Now fix the function body
                function_indent = len(lines[i-1]) - len(lines[i-1].lstrip()) + 4
                
                # Collect and fix body lines
                while i < len(lines):
                    current_line = lines[i]
                    
                    # Stop if we hit another function/class
                    if (current_line.strip().startswith('def ') or 
                        current_line.strip().startswith('class ') or
                        current_line.strip().startswith('@')):
                        break
                    
                    # Skip empty lines
                    if current_line.strip() == '':
                        new_lines.append(current_line)
                        i += 1
                        continue
                    
                    # Fix indentation for docstrings, comments, return statements
                    if (current_line.strip().startswith('"""') or
                        current_line.strip().startswith('#') or
                        current_line.strip().startswith('return ') or
                        current_line.strip() == 'pass'):
                        
                        # Re-indent to correct level
                        new_line = ' ' * function_indent + current_line.strip()
                        new_lines.append(new_line)
                        i += 1
                        continue
                    
                    # Line is already properly indented or is part of next item
                    current_indent = len(current_line) - len(current_line.lstrip())
                    if current_indent <= function_indent - 4:
                        break
                    
                    new_lines.append(current_line)
                    i += 1
                
                # Remove standalone pass if there's other content in function
                if len(new_lines) >= 3:
                    body_lines = new_lines[-3:]  # Last few lines we just added
                    content_lines = [l for l in body_lines if l.strip() and l.strip() != 'pass']
                    if content_lines:
                        # Remove pass statements
                        filtered_lines = [l for l in new_lines if l.strip() != 'pass']
                        new_lines = filtered_lines
                
                continue
            
            new_lines.append(line)
            i += 1
        
        new_content = '\n'.join(new_lines)
        
        # Only write if syntax is valid
        try:
            ast.parse(new_content)
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True, "Fixed"
            else:
                return False, "No changes needed"
        except SyntaxError as e:
            return False, f"Fix failed: {e.msg} at line {e.lineno}"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

# List of files to fix (the simpler ones first)
files_to_fix = [
    'test_string_utils.py',
    'test_validation_utils.py', 
    'test_datetime_utils.py',
    'test_crypto_utils.py',
    'test_message.py',
    'test_migrations.py',
    'test_session.py',
    'test_thread.py',
    'test_query_builder.py',
    'test_multi_tenant_billing_accuracy.py',
    'test_multi_tenant_data_isolation.py',
    'test_multi_tenant_resource_quotas.py',
]

def main():
    """Fix specific files with simple patterns."""
    test_dir = 'netra_backend/tests/unit'
    fixed_count = 0
    
    for filename in files_to_fix:
        filepath = os.path.join(test_dir, filename)
        if not os.path.exists(filepath):
            continue
            
        # Check if has syntax error
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            continue  # Already valid
        except SyntaxError:
            pass
        
        success, message = fix_file_patterns(filepath)
        if success:
            print(f"FIXED: {filename}")
            fixed_count += 1
        else:
            print(f"FAILED: {filename} - {message}")
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()