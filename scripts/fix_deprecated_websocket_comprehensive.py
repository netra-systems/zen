#!/usr/bin/env python3
"""
Comprehensive script to fix websockets deprecation warnings by updating import statements.

This script fixes:
- websockets.exceptions.* -> websockets.*
- websockets.legacy.server -> websockets.server
- websockets.legacy.client -> websockets.client
- websockets.ServerConnection -> websockets.ServerConnection
"""

import os
import re
import glob

def fix_websockets_imports(file_path: str) -> bool:
    """Fix websockets deprecation warnings in a file. Returns True if changes made."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Fix all websockets.exceptions imports
        content = re.sub(
            r'from websockets\.exceptions import ([^\n]*)',
            r'from websockets import \1',
            content
        )

        # Fix indented websockets.exceptions imports
        content = re.sub(
            r'(\s+)from websockets\.exceptions import ([^\n]*)',
            r'\1from websockets import \2',
            content
        )

        # Fix websockets.legacy.server imports
        content = re.sub(
            r'from websockets\.legacy\.server import ([^\n]*)',
            r'from websockets.server import \1',
            content
        )

        # Fix websockets.legacy.client imports
        content = re.sub(
            r'from websockets\.legacy\.client import ([^\n]*)',
            r'from websockets.client import \1',
            content
        )

        # Fix direct websockets.legacy imports
        content = re.sub(
            r'import websockets\.legacy\.server',
            'import websockets.server',
            content
        )

        content = re.sub(
            r'import websockets\.legacy\.client',
            'import websockets.client',
            content
        )

        # Fix WebSocketServerProtocol usage
        content = re.sub(
            r'websockets\.WebSocketServerProtocol',
            'websockets.ServerConnection',
            content
        )

        # Fix WebSocketClientProtocol import
        content = re.sub(
            r'from websockets\.client import WebSocketClientProtocol',
            'from websockets import ClientConnection as WebSocketClientProtocol',
            content
        )

        # Fix import statements that import WebSocketServerProtocol directly
        content = re.sub(
            r'import websockets\.WebSocketServerProtocol',
            'from websockets import ServerConnection as WebSocketServerProtocol',
            content
        )

        # Fix websockets.exceptions.* usage in code (not just imports)
        content = re.sub(
            r'websockets\.exceptions\.([A-Za-z][A-Za-z0-9]*)',
            r'websockets.\1',
            content
        )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False

def main():
    """Fix websockets deprecation warnings across the codebase."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    patterns = [
        os.path.join(base_dir, "tests/**/*.py"),
        os.path.join(base_dir, "test_framework/**/*.py"),
        os.path.join(base_dir, "netra_backend/**/*.py"),
        os.path.join(base_dir, "scripts/*.py"),
        os.path.join(base_dir, "analytics_service/**/*.py"),
        os.path.join(base_dir, "frontend/**/*.py"),
        os.path.join(base_dir, "*.py")
    ]

    fixed_count = 0
    total_files = 0
    fixed_files = []

    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            total_files += 1
            if fix_websockets_imports(file_path):
                print(f"Fixed: {file_path}")
                fixed_files.append(file_path)
                fixed_count += 1

    print(f"\nSummary: Fixed {fixed_count} out of {total_files} files")
    if fixed_files:
        print("\nFixed files:")
        for file_path in fixed_files:
            print(f"  - {file_path}")

if __name__ == "__main__":
    main()