#!/usr/bin/env python3
"""Fix all indentation errors in test_deploy_to_gcp.py"""

import re
from pathlib import Path

def fix_indentation_errors(file_path):
    """Fix all indentation errors in the file."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Pattern to detect incorrectly indented def statements
    # Look for def statements with 8 spaces (incorrect) that should have 4 spaces
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check if this is a def statement with incorrect indentation
        if line.startswith('        def '):  # 8 spaces
            # Check if the previous line indicates this should be a class method
            if i > 0:
                prev_line = lines[i-1].strip()
                # If the previous line is blank or is a fixture/class end, this should be a class method
                if prev_line == '' or prev_line.endswith(')'):
                    # Change to 4 spaces (class method indentation)
                    fixed_line = line[4:]  # Remove 4 spaces
                    fixed_lines.append(fixed_line)
                    print(f"Fixed line {i+1}: {line.strip()}")
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    # Write the fixed content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"\nFixed indentation errors in {file_path}")

if __name__ == "__main__":
    file_path = Path("tests/unit/scripts/test_deploy_to_gcp.py")
    fix_indentation_errors(file_path)