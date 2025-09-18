#!/usr/bin/env python3
"""
Enhanced syntax error fixer for test files - Issue #1332 Phase 2
"""

import re
import sys
from pathlib import Path

def fix_file_syntax(file_path: str) -> bool:
    """Fix common syntax errors in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Fix 1: Replace 4-quote docstrings with 3-quote docstrings  
        content = re.sub(r'^\s*""""\s*$', '"""', content, flags=re.MULTILINE)
        
        # Fix 2: Fix invalid decimal literals like ""30s"" -> "30s"
        content = re.sub(r'""(\d+[a-zA-Z]+)""', r'"\1"', content)
        
        # Fix 3: Fix standalone quote issues
        content = re.sub(r'^"$', '"""', content, flags=re.MULTILINE)
        
        # Fix 4: Fix Unicode literals that break Python syntax
        content = re.sub(r'\[U\+[0-9A-F]+\]', lambda m: m.group(0).replace('[U+', '\U000').replace(']', ''), content)
        
        # Fix 5: Fix mismatched quotes in f-strings and print statements
        content = re.sub(r'f"([^"]*?)"([^"]*?)"([^"]*?)"\)', r'f"\1\2\3")', content)
        
        # Fix 6: Fix unterminated strings in function calls
        content = re.sub(r'logger\.info\(([^)]*?)"\)\)', r'logger.info(\1")', content)
        
        # Fix 7: Fix missing quotes
        content = re.sub(r'(\w+) = ([^",\[\]{}()]+),', r'\1 = "\2",', content)

        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        else:
            print(f"No changes needed: {file_path}")
            return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_syntax_errors_enhanced.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    success = fix_file_syntax(file_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
