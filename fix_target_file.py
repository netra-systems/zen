#!/usr/bin/env python3
"""Simple script to fix the specific syntax patterns in our target file."""

import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix { ) patterns
    content = re.sub(r'\{\s*\)', '{}', content)

    # Fix [ ) patterns
    content = re.sub(r'\[\s*\)', '[]', content)

    # Fix { )) patterns
    content = re.sub(r'\{\s*\)\)', '})', content)

    # Fix ( ) patterns when part of function calls
    content = re.sub(r'await asyncio\.wait_for\(\s*\)', 'await asyncio.wait_for(', content)
    content = re.sub(r'ServiceStatus\(\s*\)', 'ServiceStatus(', content)
    content = re.sub(r'ServiceAvailability\(\s*\)', 'ServiceAvailability(', content)

    # Fix incomplete string prints
    content = re.sub(r'print\(\s*"\s*\)', 'print("")', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed syntax patterns in {filepath}")

if __name__ == "__main__":
    fix_file("tests/e2e/service_availability.py")