#!/usr/bin/env python
"""Fix boolean comparison issues in test files"""

import os
import re
from pathlib import Path

def fix_boolean_comparisons(file_path):
    """Fix is True/False/None comparisons in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace is True/False/None with == comparisons
        content = re.sub(r'\bis\s+True\b', '== True', content)
        content = re.sub(r'\bis\s+False\b', '== False', content)
        content = re.sub(r'\bis\s+None\b', '== None', content)
        
        # Also fix "is not" comparisons
        content = re.sub(r'\bis\s+not\s+True\b', '!= True', content)
        content = re.sub(r'\bis\s+not\s+False\b', '!= False', content)
        content = re.sub(r'\bis\s+not\s+None\b', '!= None', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all test files"""
    test_dir = Path('app/tests')
    fixed_count = 0
    
    for py_file in test_dir.rglob('*.py'):
        if fix_boolean_comparisons(py_file):
            fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == '__main__':
    main()