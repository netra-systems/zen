#!/usr/bin/env python3
"""
Script to fix websockets legacy imports by updating them to modern equivalents.

This script fixes the REVERSE of what fix_websockets_deprecation.py did:
- websockets.ClientConnection -> websockets.ClientConnection
- websockets.ServerConnection -> websockets.ServerConnection  
- websockets.InvalidStatusCode -> websockets.InvalidStatusCode

For websockets 15.0+ which removed the legacy module.
"""

import os
import re
import glob
from pathlib import Path

def fix_legacy_websockets_imports(file_path: str) -> bool:
    """Fix legacy websockets imports in a file. Returns True if changes made."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix legacy client imports
        content = re.sub(
            r'from websockets\.legacy\.client import WebSocketClientProtocol',
            'from websockets import ClientConnection as WebSocketClientProtocol',
            content
        )
        
        # Fix legacy server imports  
        content = re.sub(
            r'from websockets\.legacy\.server import WebSocketServerProtocol',
            'from websockets import ServerConnection as WebSocketServerProtocol',
            content
        )
        
        # Fix legacy exception imports
        content = re.sub(
            r'from websockets\.legacy\.exceptions import ([^\n]*)',
            r'from websockets import \1',
            content
        )
        
        # Fix type annotations - client protocol
        content = re.sub(
            r'websockets\.legacy\.client\.WebSocketClientProtocol',
            'websockets.ClientConnection',
            content
        )
        
        # Fix type annotations - server protocol
        content = re.sub(
            r'websockets\.legacy\.server\.WebSocketServerProtocol',
            'websockets.ServerConnection',
            content
        )
        
        # Fix exception references
        content = re.sub(
            r'websockets\.legacy\.exceptions\.InvalidStatusCode',
            'websockets.InvalidStatusCode',
            content
        )
        
        # Add necessary imports if ClientConnection or ServerConnection are referenced
        if ('websockets.ClientConnection' in content or 'websockets.ServerConnection' in content) and 'import websockets' in content:
            # Check if we need to add specific imports
            needs_client = 'websockets.ClientConnection' in content
            needs_server = 'websockets.ServerConnection' in content
            
            if needs_client and 'from websockets import ClientConnection' not in content:
                content = re.sub(
                    r'import websockets\n',
                    'import websockets\nfrom websockets import ClientConnection\n',
                    content, count=1
                )
            
            if needs_server and 'from websockets import ServerConnection' not in content:
                content = re.sub(
                    r'import websockets\n',
                    'import websockets\nfrom websockets import ServerConnection\n',
                    content, count=1
                )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

def main():
    """Fix websockets legacy imports across the codebase."""
    base_dir = Path(__file__).parent.parent
    patterns = [
        "tests/**/*.py",
        "test_framework/**/*.py", 
        "netra_backend/**/*.py",
        "auth_service/**/*.py",
        "scripts/*.py"
    ]
    
    fixed_count = 0
    total_files = 0
    
    for pattern in patterns:
        for file_path in base_dir.glob(pattern):
            if file_path.is_file():
                total_files += 1
                if fix_legacy_websockets_imports(str(file_path)):
                    print(f"Fixed: {file_path}")
                    fixed_count += 1
    
    print(f"\nSummary: Fixed {fixed_count} out of {total_files} files")
    
    # Report files that still have legacy references (for manual review)
    remaining_legacy = []
    for pattern in patterns:
        for file_path in base_dir.glob(pattern):
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if 'websockets.legacy' in content:
                        remaining_legacy.append(file_path)
                except:
                    pass
    
    if remaining_legacy:
        print(f"\nFiles still containing 'websockets.legacy' references:")
        for file_path in remaining_legacy:
            print(f"  {file_path}")

if __name__ == "__main__":
    main()