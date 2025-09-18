#!/usr/bin/env python3
"""Quick syntax fix for websocket_real_test_base.py"""

import re

def fix_malformed_docstrings(content):
    """Fix common malformed docstring patterns"""
    # Fix pattern: """"
    content = re.sub(r'^\s*""""\s*$', '    """', content, flags=re.MULTILINE)

    # Fix patterns like '95th percentile latency.""'
    content = re.sub(r'(\s+)([^"]*?)\.""', r'\1"""\2."""', content)

    # Fix patterns like '"Some text."'
    content = re.sub(r'^\s*"([^"]*\.)\s*"$', r'    """\1"""', content, flags=re.MULTILINE)

    # Fix malformed f-string patterns like 'f{variable}"'
    content = re.sub(r'([^f])f([^"]*)([^"]*)"', r'\1f"\2\3"', content)

    # Fix unterminated strings that end with extra quotes
    content = re.sub(r'"""([^"]*?)""$', r'"""\1"""', content, flags=re.MULTILINE)

    return content

# Read the file
with open('tests/mission_critical/websocket_real_test_base.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Apply fixes
fixed_content = fix_malformed_docstrings(content)

# Write back
with open('tests/mission_critical/websocket_real_test_base.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("Applied quick syntax fixes to websocket_real_test_base.py")