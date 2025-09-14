#!/usr/bin/env python3
"""
Import Path Standardization Script
Mission: Convert non-canonical import paths to SSOT canonical patterns
"""

import os
import re
from pathlib import Path

def standardize_websocket_imports(file_path):
    """Standardize WebSocket Manager import paths to canonical SSOT patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # WebSocket Manager Standardizations (based on SSOT_IMPORT_REGISTRY.md)
        # Canonical: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        
        standardizations = [
            # WebSocketManager imports
            (
                r'from netra_backend\.app\.websocket_core\.manager import WebSocketManager',
                'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager'
            ),
            (
                r'from netra_backend\.app\.websocket_core\.unified_manager import WebSocketManager',
                'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager'
            ),
            # UnifiedWebSocketManager imports (note: this may need special handling)
            (
                r'from netra_backend\.app\.websocket_core\.unified_manager import UnifiedWebSocketManager',
                'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager'
            ),
        ]
        
        changes_made = False
        for pattern, replacement in standardizations:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                changes_made = True
                content = new_content
        
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Standardized: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def standardize_config_imports(file_path):
    """Standardize Config import paths to canonical SSOT patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Config Standardizations (based on SSOT_IMPORT_REGISTRY.md)
        # Canonical: from netra_backend.app.config import get_config
        
        standardizations = [
            (
                r'from netra_backend\.app\.core\.configuration\.base import get_config',
                'from netra_backend.app.config import get_config'
            ),
        ]
        
        changes_made = False
        for pattern, replacement in standardizations:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                changes_made = True
                content = new_content
        
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Standardized config: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error processing config in {file_path}: {e}")
        return False

def main():
    """Main standardization process."""
    test_dir = Path("tests")
    
    if not test_dir.exists():
        print("❌ Tests directory not found")
        return
    
    python_files = list(test_dir.rglob("*.py"))
    print(f"📁 Found {len(python_files)} Python test files")
    
    websocket_changes = 0
    config_changes = 0
    
    for file_path in python_files:
        if standardize_websocket_imports(file_path):
            websocket_changes += 1
        
        if standardize_config_imports(file_path):
            config_changes += 1
    
    print(f"\n📊 Standardization Results:")
    print(f"✅ WebSocket imports standardized: {websocket_changes} files")
    print(f"✅ Config imports standardized: {config_changes} files")
    print(f"✅ Total files processed: {len(python_files)}")
    
    if websocket_changes > 0 or config_changes > 0:
        print(f"\n🎯 Import paths standardized according to SSOT_IMPORT_REGISTRY.md")
        print(f"🔧 Run test collection to verify improvements")
    else:
        print(f"\n✅ All imports already standardized")

if __name__ == "__main__":
    main()