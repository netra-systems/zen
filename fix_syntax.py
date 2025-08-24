#!/usr/bin/env python3
"""
Fix syntax errors in integration test files caused by comments in multi-line statements
"""
import os
import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix the specific pattern: line ending with backslash followed by comment line
        lines = content.split('\n')
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if line ends with backslash and next line is a problematic comment
            if (line.strip().endswith('\\') and 
                i + 1 < len(lines) and 
                lines[i + 1].strip().startswith('#') and
                ('Mock:' in lines[i + 1] or 'Component isolation' in lines[i + 1] or 'Database session isolation' in lines[i + 1])):
                # Keep the line with backslash, skip the comment line
                fixed_lines.append(line)
                i += 2  # Skip the comment line
            else:
                fixed_lines.append(line)
                i += 1
        
        fixed_content = '\n'.join(fixed_lines)
        
        if fixed_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f'Fixed: {filepath}')
            return True
        return False
    except Exception as e:
        print(f'Error with {filepath}: {e}')
        return False

def main():
    # Fix files in netra_backend/tests/integration
    base_path = 'netra_backend/tests/integration'
    fixed_count = 0
    
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_file(filepath):
                    fixed_count += 1
    
    print(f'Fixed {fixed_count} files')

if __name__ == '__main__':
    main()