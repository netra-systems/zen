#!/usr/bin/env python3
"""
Fix IsolatedWebSocketManager import issues across test files.

IsolatedWebSocketManager was removed from websocket_manager_factory module for SSOT compliance.
Tests should use WebSocketManager from unified_manager module instead.
"""

import os
import re

# Files that need fixing
files_to_fix = [
    r"C:\GitHub\netra-apex\netra_backend\tests\integration\test_multi_user_isolation_routing.py",
    r"C:\GitHub\netra-apex\netra_backend\tests\unit\websocket_core\test_websocket_systems_integration.py",
    r"C:\GitHub\netra-apex\netra_backend\tests\unit\websocket_core\test_websocket_security_focused.py",
    r"C:\GitHub\netra-apex\netra_backend\tests\unit\websocket_core\test_websocket_manager_factory_security_comprehensive.py",
    r"C:\GitHub\netra-apex\netra_backend\tests\unit\websocket_core\test_websocket_manager_factory_comprehensive.py",
]

def fix_file(filepath):
    """Fix IsolatedWebSocketManager import in a single file."""
    print(f"Processing: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"  ❌ File not found: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file imports IsolatedWebSocketManager from websocket_manager_factory
        if "IsolatedWebSocketManager," not in content:
            print(f"  ℹ️ No IsolatedWebSocketManager import found")
            return False
        
        # Pattern to find the import block
        pattern = r'(from netra_backend\.app\.websocket_core\.websocket_manager_factory import \([^)]+\))'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        
        if not match:
            print(f"  ⚠️ Could not find websocket_manager_factory import block")
            return False
        
        import_block = match.group(1)
        
        # Remove IsolatedWebSocketManager from the import
        new_import_block = import_block.replace("\n    IsolatedWebSocketManager,", "")
        
        # Replace the import block
        new_content = content.replace(import_block, new_import_block)
        
        # Add the new import for IsolatedWebSocketManager after the import block
        # Find the position after the import block
        import_end = match.end()
        
        # Check if the alias import already exists
        if "from netra_backend.app.websocket_core.unified_manager import WebSocketManager as IsolatedWebSocketManager" not in new_content:
            # Insert the new import
            lines = new_content[:import_end].split('\n')
            insert_pos = import_end
            
            new_import = "\n\n# Import WebSocketManager (replacement for removed IsolatedWebSocketManager)\nfrom netra_backend.app.websocket_core.unified_manager import WebSocketManager as IsolatedWebSocketManager"
            
            new_content = new_content[:insert_pos] + new_import + new_content[insert_pos:]
        
        # Write the fixed content back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✅ Fixed IsolatedWebSocketManager import")
        return True
        
    except Exception as e:
        print(f"  ❌ Error processing file: {e}")
        return False

def main():
    """Fix all files with IsolatedWebSocketManager import issues."""
    print("Fixing IsolatedWebSocketManager import issues...")
    print("=" * 60)
    
    fixed_count = 0
    for filepath in files_to_fix:
        if fix_file(filepath):
            fixed_count += 1
        print()
    
    print("=" * 60)
    print(f"Summary: Fixed {fixed_count}/{len(files_to_fix)} files")
    
    if fixed_count == len(files_to_fix):
        print("✅ All files successfully fixed!")
    else:
        print("⚠️ Some files could not be fixed. Please check manually.")

if __name__ == "__main__":
    main()