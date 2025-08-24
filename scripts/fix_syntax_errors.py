#!/usr/bin/env python3
"""
Fix systematic syntax errors in test files.

This script addresses common formatting issues that cause syntax errors:
- Missing closing parentheses and braces
- Improperly formatted multi-line statements
- Extra commas in function definitions
"""

import re
import sys
from pathlib import Path

def fix_syntax_errors(file_path: Path) -> bool:
    """Fix common syntax errors in Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix broken multi-line function calls and dictionaries
        # Pattern: function_call(\n    args,\n    more_args\n\n
        content = re.sub(r'(\w+\([^)]*)\n\n        ', r'\1\n        ', content)
        
        # Fix multi-line dictionary definitions missing closing braces
        # Look for patterns like: }\n\n with no preceding }
        
        # Fix function definitions with extra commas
        content = re.sub(r'def (\w+)\(,\s*', r'def \1(', content)
        content = re.sub(r'async def (\w+)\(,\s*', r'async def \1(', content)
        
        # Fix broken assert statements
        content = re.sub(r'assert ([^,]+),\s*\n\s*([^"]*"[^"]*")', r'assert \1, \2', content)
        
        # Fix incomplete function calls by adding missing closing parentheses
        # This is more complex and needs careful handling
        
        # Fix excessive blank lines in function calls
        content = re.sub(r'\n\n\s*([,)])', r'\n\1', content)
        
        # Fix spacing around function parameters
        content = re.sub(r',\s*\n\n\s*([^,\n])', r',\n        \1', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return True
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    target_file = Path("tests/e2e/test_concurrent_agent_startup_core.py")
    
    if not target_file.exists():
        print(f"File not found: {target_file}")
        return 1
        
    print(f"Fixing syntax errors in {target_file}...")
    if fix_syntax_errors(target_file):
        print("Syntax fixes applied. Please review the changes.")
        return 0
    else:
        print("Failed to fix syntax errors.")
        return 1

if __name__ == "__main__":
    sys.exit(main())