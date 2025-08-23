#!/usr/bin/env python3
"""Migrate all ws_manager imports to unified WebSocket system.

This script safely migrates all imports from ws_manager to the unified WebSocket system,
preserving backward compatibility and ensuring no breaking changes.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Define import patterns and their replacements
IMPORT_PATTERNS = [
    # Pattern 1: from ws_manager import WebSocketManager
    (
        r'from\s+netra_backend\.app\.ws_manager\s+import\s+WebSocketManager',
        'from netra_backend.app.websocket.unified import UnifiedWebSocketManager as WebSocketManager'
    ),
    # Pattern 2: from ws_manager import manager
    (
        r'from\s+netra_backend\.app\.ws_manager\s+import\s+manager',
        'from netra_backend.app.websocket.unified import get_unified_manager\nmanager = get_unified_manager()'
    ),
    # Pattern 3: from ws_manager import get_manager
    (
        r'from\s+netra_backend\.app\.ws_manager\s+import\s+get_manager',
        'from netra_backend.app.websocket.unified import get_unified_manager as get_manager'
    ),
    # Pattern 4: import ws_manager
    (
        r'import\s+netra_backend\.app\.ws_manager',
        'from netra_backend.app.websocket import unified as ws_manager'
    ),
    # Pattern 5: Combined imports
    (
        r'from\s+netra_backend\.app\.ws_manager\s+import\s+\(\s*WebSocketManager\s*,\s*manager\s*\)',
        'from netra_backend.app.websocket.unified import UnifiedWebSocketManager as WebSocketManager, get_unified_manager\nmanager = get_unified_manager()'
    ),
]

# Directories to process
DIRECTORIES_TO_PROCESS = [
    'netra_backend/app/services',
    'netra_backend/app/agents', 
    'netra_backend/app/routes',
    'netra_backend/app/handlers',
    'netra_backend/app/error_handling',
    'netra_backend/app/core',
    'netra_backend/tests',
    'tests/e2e',
]

# Files to exclude
EXCLUDE_FILES = [
    'ws_manager.py',
    'migrate_to_unified_websocket.py',
    '__pycache__',
    '.pyc',
]


def should_process_file(file_path: Path) -> bool:
    """Check if file should be processed."""
    # Skip excluded files
    for exclude in EXCLUDE_FILES:
        if exclude in str(file_path):
            return False
    
    # Only process Python files
    return file_path.suffix == '.py'


def process_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Process a single file and update imports."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, [f"Error reading file: {e}"]
    
    original_content = content
    changes = []
    
    # Apply each replacement pattern
    for pattern, replacement in IMPORT_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes.append(f"Replaced: {matches[0][:50]}...")
    
    # Write back if changed
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        except Exception as e:
            return False, [f"Error writing file: {e}"]
    
    return False, []


def main():
    """Main migration function."""
    # Force UTF-8 output on Windows
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=== WebSocket Migration to Unified System ===\n")
    
    total_files = 0
    modified_files = 0
    error_files = 0
    
    # Process each directory
    for directory in DIRECTORIES_TO_PROCESS:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"⚠️  Directory not found: {directory}")
            continue
        
        print(f"\n📁 Processing: {directory}")
        dir_modified = 0
        
        # Find all Python files
        for file_path in dir_path.rglob('*.py'):
            if not should_process_file(file_path):
                continue
            
            total_files += 1
            success, changes = process_file(file_path)
            
            if success and changes:
                modified_files += 1
                dir_modified += 1
                print(f"  ✅ {file_path.relative_to('.')}")
                for change in changes:
                    print(f"     - {change}")
            elif not success and changes:
                error_files += 1
                print(f"  ❌ {file_path.relative_to('.')}")
                for error in changes:
                    print(f"     ERROR: {error}")
        
        if dir_modified > 0:
            print(f"  Modified {dir_modified} files in {directory}")
    
    # Summary
    print("\n" + "="*50)
    print("📊 Migration Summary:")
    print(f"  Total files scanned: {total_files}")
    print(f"  Files modified: {modified_files}")
    print(f"  Files with errors: {error_files}")
    
    if modified_files > 0:
        print("\n✅ Migration completed successfully!")
        print("⚠️  Please run tests to verify the changes.")
    else:
        print("\nℹ️  No files needed migration.")
    
    # Additional check for ws_manager.py
    ws_manager_path = Path('netra_backend/app/ws_manager.py')
    if ws_manager_path.exists():
        print("\n⚠️  IMPORTANT: ws_manager.py still exists!")
        print("    Once all imports are verified, you can delete it with:")
        print("    rm netra_backend/app/ws_manager.py")


if __name__ == "__main__":
    main()