#!/usr/bin/env python3
"""Fix test imports by removing app. prefix from imports in all test directories."""

import os
import re
from pathlib import Path

def fix_imports_in_file(filepath):
    """Fix imports in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match imports starting with "from app."
    original_content = content
    
    # Replace patterns
    replacements = [
        (r'^from app\.db\.', 'from db.'),
        (r'^from app\.redis_manager', 'from redis_manager'),
        (r'^from app\.core\.', 'from core.'),
        (r'^from app\.agents\.', 'from agents.'),
        (r'^from app\.services\.', 'from services.'),
        (r'^from app\.schemas\.', 'from schemas.'),
        (r'^from app\.models\.', 'from models.'),
        (r'^from app\.utils\.', 'from utils.'),
        (r'^from app\.auth_integration\.', 'from auth_integration.'),
        (r'^from app\.routes\.', 'from routes.'),
        (r'^from app\.websocket_manager', 'from websocket_manager'),
        (r'^from app\.main', 'from main'),
        (r'^from app\.config', 'from config'),
        (r'^from app\.', 'from '),  # Catch-all for remaining app. imports
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Also fix imports with parentheses
    content = re.sub(r'^from app\.([\w.]+) import \(', r'from \1 import (', content, flags=re.MULTILINE)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all test files."""
    base_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests')
    
    fixed_count = 0
    total_count = 0
    
    # Process all test files recursively
    for test_file in base_dir.rglob('test_*.py'):
        total_count += 1
        if fix_imports_in_file(test_file):
            fixed_count += 1
            print(f"Fixed: {test_file.relative_to(base_dir)}")
    
    # Also process conftest.py files
    for test_file in base_dir.rglob('conftest.py'):
        total_count += 1
        if fix_imports_in_file(test_file):
            fixed_count += 1
            print(f"Fixed: {test_file.relative_to(base_dir)}")
    
    print(f"\nFixed {fixed_count} out of {total_count} test files")

if __name__ == "__main__":
    main()