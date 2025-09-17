#!/usr/bin/env python3
"""
Modern WebSocket Deprecation Fix Script

This script fixes all deprecated WebSocket patterns to use modern websockets library
without the legacy module. It handles:
- WebSocketClientProtocol -> ClientConnection
- WebSocketServerProtocol -> ServerConnection
- Proper imports from websockets (not websockets.legacy)
- Type annotations and variable declarations
"""

import os
import re
import glob
from pathlib import Path
from typing import List, Tuple

def fix_websocket_imports_and_types(file_path: str) -> bool:
    """Fix WebSocket imports and type annotations in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # 1. Fix imports - WebSocketClientProtocol
        if "websockets.ClientConnection" in content:
            content = re.sub(
                r'from websockets import ClientConnection as WebSocketClientProtocol',
                'from websockets import ClientConnection as WebSocketClientProtocol',
                content
            )
            changes_made = True
            
        # 2. Fix imports - WebSocketServerProtocol 
        if "from websockets import ServerConnection as WebSocketServerProtocol" in content:
            content = re.sub(
                r'from websockets import ServerConnection as WebSocketServerProtocol',
                'from websockets import ServerConnection as WebSocketServerProtocol',
                content
            )
            changes_made = True
        
        # 3. Fix type annotations - client protocol
        if "websockets.ClientConnection" in content:
            content = re.sub(
                r'websockets\.WebSocketClientProtocol',
                'websockets.ClientConnection',
                content
            )
            changes_made = True
        
        # 4. Fix type annotations - server protocol
        if "websockets.ServerConnection" in content:
            content = re.sub(
                r'websockets\.WebSocketServerProtocol',
                'websockets.ServerConnection',
                content
            )
            changes_made = True
        
        # 5. Fix client imports with proper fallback handling
        content = re.sub(
            r'try:\s*\n\s*import websockets\s*\n\s*from websockets import ServerConnection as WebSocketServerProtocol\s*\n\s*WEBSOCKETS_AVAILABLE = True\s*\nexcept ImportError:\s*\n\s*WEBSOCKETS_AVAILABLE = False',
            '''try:
    import websockets
    from websockets import ServerConnection as WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = None
    WebSocketServerProtocol = None''',
            content,
            flags=re.MULTILINE
        )
        
        # 6. Fix Optional typing with modern imports
        content = re.sub(
            r'Optional\[websockets\.WebSocketClientProtocol\]',
            'Optional[websockets.ClientConnection]',
            content
        )
        
        content = re.sub(
            r'Optional\[websockets\.WebSocketServerProtocol\]', 
            'Optional[websockets.ServerConnection]',
            content
        )
        
        # 7. Fix List typing
        content = re.sub(
            r'List\[websockets\.WebSocketClientProtocol\]',
            'List[websockets.ClientConnection]',
            content
        )
        
        content = re.sub(
            r'Set\[WebSocketServerProtocol\]',
            'Set[websockets.ServerConnection]',
            content
        )
        
        # 8. Handle modern import pattern for better compatibility
        if "from websockets import ClientConnection as WebSocketClientProtocol" not in content and "WebSocketClientProtocol" in content:
            # Add import if WebSocketClientProtocol is used but not imported
            if "import websockets" in content and "from websockets import" not in content:
                content = re.sub(
                    r'import websockets',
                    'import websockets\nfrom websockets import ClientConnection as WebSocketClientProtocol',
                    content,
                    count=1
                )
                changes_made = True
        
        # 9. Fix the specific connection client patterns
        content = re.sub(
            r'self\.websocket: Optional\[websockets\.WebSocketClientProtocol\]',
            'self.websocket: Optional[websockets.ClientConnection]',
            content
        )
        
        # 10. Update method signatures and variable declarations
        content = re.sub(
            r'connection: websockets\.WebSocketClientProtocol',
            'connection: websockets.ClientConnection',
            content
        )
        
        content = re.sub(
            r'connection: websockets\.WebSocketServerProtocol',
            'connection: websockets.ServerConnection', 
            content
        )
        
        # 11. Fix function return types
        content = re.sub(
            r'-> Optional\[websockets\.WebSocketClientProtocol\]',
            '-> Optional[websockets.ClientConnection]',
            content
        )
        
        content = re.sub(
            r'-> Optional\[WebSocketServerProtocol\]',
            '-> Optional[websockets.ServerConnection]',
            content
        )
        
        # 12. Handle imports from websockets.server (deprecated)
        content = re.sub(
            r'from websockets\.server import WebSocketServerProtocol',
            'from websockets import ServerConnection as WebSocketServerProtocol',
            content
        )
        
        # 13. Handle imports from websockets.client (deprecated)  
        content = re.sub(
            r'from websockets\.client import WebSocketClientProtocol',
            'from websockets import ClientConnection as WebSocketClientProtocol',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

def find_files_with_websocket_usage() -> List[str]:
    """Find all Python files that contain WebSocket-related code."""
    base_dir = Path(__file__).parent.parent
    patterns = [
        "tests/**/*.py",
        "test_framework/**/*.py", 
        "netra_backend/**/*.py",
        "auth_service/**/*.py",
        "scripts/**/*.py",
        "analytics_service/**/*.py",
        "dev_launcher/**/*.py"
    ]
    
    files_to_check = []
    
    for pattern in patterns:
        for file_path in base_dir.glob(pattern):
            if file_path.is_file() and file_path.suffix == '.py':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check if file contains WebSocket-related patterns
                    if any(pattern in content for pattern in [
                        'WebSocketClientProtocol',
                        'WebSocketServerProtocol', 
                        'websockets.WebSocket',
                        'websockets.client',
                        'websockets.server'
                    ]):
                        files_to_check.append(str(file_path))
                        
                except Exception:
                    # Skip files that can't be read
                    continue
                    
    return files_to_check

def main():
    """Fix WebSocket deprecation warnings across the codebase."""
    print("Starting Modern WebSocket Deprecation Fix...")
    
    files_to_fix = find_files_with_websocket_usage()
    print(f"Found {len(files_to_fix)} files with WebSocket usage")
    
    fixed_count = 0
    
    for file_path in files_to_fix:
        try:
            if fix_websocket_imports_and_types(file_path):
                print(f"Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"No changes needed: {file_path}")
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
    
    print(f"\nSummary: Fixed {fixed_count} out of {len(files_to_fix)} files")
    
    # Check for remaining issues
    remaining_issues = []
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            issues = []
            if 'websockets.legacy' in content:
                issues.append('websockets.legacy')
            if 'from websockets.server import' in content:
                issues.append('websockets.server import')  
            if 'from websockets.client import' in content:
                issues.append('websockets.client import')
                
            if issues:
                remaining_issues.append((file_path, issues))
                
        except Exception:
            continue
    
    if remaining_issues:
        print(f"\nFiles with remaining deprecated patterns:")
        for file_path, issues in remaining_issues:
            print(f"  {file_path}: {', '.join(issues)}")
    else:
        print("\nAll WebSocket deprecation warnings should be resolved!")
        
    return fixed_count

if __name__ == "__main__":
    main()