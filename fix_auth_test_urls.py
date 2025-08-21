#!/usr/bin/env python3
"""Fix auth test URLs to use correct endpoints."""

import re
from pathlib import Path

def fix_auth_urls_in_file(filepath):
    """Fix auth URLs in a test file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace /api/v1/auth with /auth
    content = re.sub(r'/api/v1/auth/', '/auth/', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all auth test files."""
    test_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests')
    
    fixed_count = 0
    
    # Process all test files that might have auth endpoints
    for test_file in test_dir.rglob('test_*.py'):
        if fix_auth_urls_in_file(test_file):
            fixed_count += 1
            print(f"Fixed: {test_file.relative_to(test_dir)}")
    
    print(f"\nFixed {fixed_count} test files")

if __name__ == "__main__":
    main()