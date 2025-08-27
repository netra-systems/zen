#!/usr/bin/env python3
"""
Script to fix websockets deprecation warnings by updating import statements.

This script fixes:
- websockets.client.WebSocketClientProtocol -> websockets.legacy.client.WebSocketClientProtocol
- websockets.exceptions.InvalidStatusCode -> websockets.legacy.exceptions.InvalidStatusCode
- websockets.legacy.server.WebSocketServerProtocol -> websockets.legacy.server.WebSocketServerProtocol
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
        
        # Fix WebSocketClientProtocol import
        content = re.sub(
            r'from websockets\.client import WebSocketClientProtocol',
            'from websockets.legacy.client import WebSocketClientProtocol',
            content
        )
        
        # Fix InvalidStatusCode import
        content = re.sub(
            r'from websockets\.exceptions import ([^\\n]*InvalidStatusCode[^\\n]*)',
            r'from websockets.legacy.exceptions import \1',
            content
        )
        
        # Fix WebSocketServerProtocol import
        content = re.sub(
            r'websockets\.WebSocketServerProtocol',
            'websockets.legacy.server.WebSocketServerProtocol',
            content
        )
        
        # Fix import statements that import WebSocketServerProtocol directly
        content = re.sub(
            r'import websockets\.WebSocketServerProtocol',
            'from websockets.legacy.server import WebSocketServerProtocol',
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
        os.path.join(base_dir, "scripts/*.py")
    ]
    
    fixed_count = 0
    total_files = 0
    
    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            total_files += 1
            if fix_websockets_imports(file_path):
                print(f"Fixed: {file_path}")
                fixed_count += 1
    
    print(f"\nSummary: Fixed {fixed_count} out of {total_files} files")

if __name__ == "__main__":
    main()