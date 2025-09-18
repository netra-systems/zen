#!/usr/bin/env python3
"""
Script to fix common syntax error patterns in test files
"""
import re
import os
from pathlib import Path

def fix_common_patterns(file_path):
    """Fix common syntax error patterns in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Fix common patterns
        # 1. Fix "{ )" to "{"
        content = re.sub(r'\{\s*\)', '{', content)

        # 2. Fix "[ )" to "["
        content = re.sub(r'\[\s*\)', '[', content)

        # 3. Fix unterminated strings like 'print(" )'
        # This is trickier - look for print statements ending with " )
        content = re.sub(r'print\(\s*"\s*\)\s*\n', 'print("")\n', content)

        # 4. Fix specific pattern: 'print(" )\nSOMETHING"' to 'print("SOMETHING")'
        content = re.sub(r'print\(\s*"\s*\)\s*\n\s*([^"]+)"', r'print("\1")', content)

        # 5. Fix missing async keyword before def when there's await inside
        lines = content.split('\n')
        fixed_lines = []
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and not line.strip().startswith('def test_'):
                # Check next few lines for await
                next_lines = '\n'.join(lines[i:i+10])
                if 'await ' in next_lines and 'async ' not in line:
                    line = line.replace('def ', 'async def ')
            fixed_lines.append(line)
        content = '\n'.join(fixed_lines)

        # 6. Fix missing indentation after if/for/while/try/except
        lines = content.split('\n')
        fixed_lines = []
        for i, line in enumerate(lines):
            fixed_lines.append(line)

            # Check if this line ends with : and next line is not indented
            if line.strip().endswith(':') and i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line and not next_line.startswith(' ') and not next_line.startswith('\t'):
                    # Add proper indentation
                    current_indent = len(line) - len(line.lstrip())
                    if 'if ' in line or 'for ' in line or 'while ' in line or 'try:' in line or 'except' in line:
                        lines[i + 1] = ' ' * (current_indent + 4) + next_line

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_mission_critical_files():
    """Fix syntax errors in mission critical test files"""
    mission_critical_dir = Path("tests/mission_critical")
    fixed_count = 0

    for py_file in mission_critical_dir.glob("*.py"):
        print(f"Processing {py_file}...")
        if fix_common_patterns(py_file):
            print(f"  FIXED patterns in {py_file}")
            fixed_count += 1
        else:
            print(f"  No changes needed for {py_file}")

    print(f"\nFixed {fixed_count} files")
    return fixed_count

if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    fix_mission_critical_files()