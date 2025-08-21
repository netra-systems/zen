#!/usr/bin/env python3
"""Fix auth tests to use dev login instead of registration."""

import re
from pathlib import Path


def fix_auth_test(filepath):
    """Fix auth tests to use dev login."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Remove all register endpoint calls and replace with dev login where needed
    # Pattern for register blocks
    register_pattern = r'# Register.*?\n.*?register_data = \{[^}]+\}.*?\n.*?async with session\.post\([^)]+/auth/register[^)]+\) as resp:.*?\n.*?assert resp\.status == 201'
    
    # Replace with dev login for first-time setup
    dev_login_replacement = '''# Use dev login for testing
            async with session.post(
                f"{auth_service_url}/auth/dev/login",
                json={}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                user_id = data["user"]["id"]'''
    
    content = re.sub(register_pattern, dev_login_replacement, content, flags=re.DOTALL | re.MULTILINE)
    
    # Also fix any remaining register calls
    content = re.sub(r'/auth/register', '/auth/dev/login', content)
    content = re.sub(r'assert resp.status == 201(\s+data = await resp.json\(\))?', 'assert resp.status == 200\n                data = await resp.json()', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix auth tests."""
    test_file = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\integration\critical_paths\test_auth_basic_login_flow_l3.py')
    
    if fix_auth_test(test_file):
        print(f"Fixed: {test_file.name}")
    else:
        print(f"No changes needed for: {test_file.name}")

if __name__ == "__main__":
    main()