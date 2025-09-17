#!/usr/bin/env python3
"""
WebSocket Manager SSOT Consolidation - Phase 2 Batch 4
Issue #1196 - Bulk fix for remaining canonical_import_patterns violations
"""

import os
import re
import sys
from pathlib import Path

def fix_websocket_imports():
    """Fix WebSocketManager imports in bulk"""
    total_files_modified = 0
    total_violations_fixed = 0
    errors = []

    # Patterns to fix
    patterns = [
        {
            'old': r'from netra_backend\.app\.websocket_core\.canonical_import_patterns import WebSocketManager',
            'new': 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
            'name': 'WebSocketManager'
        },
        {
            'old': r'from netra_backend\.app\.websocket_core\.canonical_import_patterns import UnifiedWebSocketManager',
            'new': 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
            'name': 'UnifiedWebSocketManager'
        },
        # Handle multi-import lines
        {
            'old': r'from netra_backend\.app\.websocket_core\.canonical_import_patterns import ([^,]*,\s*)*WebSocketManager([^,]*,\s*)*',
            'new': 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
            'name': 'WebSocketManager_multi'
        },
        {
            'old': r'from netra_backend\.app\.websocket_core\.canonical_import_patterns import ([^,]*,\s*)*UnifiedWebSocketManager([^,]*,\s*)*',
            'new': 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
            'name': 'UnifiedWebSocketManager_multi'
        }
    ]

    # Find all Python files with violations
    print("Scanning for files with violations...")
    files_to_fix = []

    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip in root for skip in ['__pycache__', '.git', 'backups', '.pytest_cache']):
            continue

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Check if file has any violations
                        has_violations = any(re.search(pattern['old'], content) for pattern in patterns)
                        if has_violations:
                            files_to_fix.append(filepath)
                except Exception as e:
                    errors.append(f"Error reading {filepath}: {e}")

    print(f"Found {len(files_to_fix)} files with violations")

    # Process each file
    for filepath in files_to_fix:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                original_content = content

            # Apply each pattern fix
            file_violations_fixed = 0
            for pattern in patterns:
                matches = re.findall(pattern['old'], content)
                if matches:
                    content = re.sub(pattern['old'], pattern['new'], content)
                    file_violations_fixed += len(matches)

            # Also fix any usage of UnifiedWebSocketManager -> WebSocketManager
            if 'UnifiedWebSocketManager' in content:
                # Replace usage but be careful not to replace import lines we already fixed
                content = re.sub(r'\bUnifiedWebSocketManager\b', 'WebSocketManager', content)
                file_violations_fixed += content.count('WebSocketManager') - original_content.count('WebSocketManager')

            # Write back if changes were made
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                total_files_modified += 1
                total_violations_fixed += file_violations_fixed
                print(f"Fixed {file_violations_fixed} violations in {filepath}")

        except Exception as e:
            errors.append(f"Error processing {filepath}: {e}")

    # Report results
    print(f"\n=== BATCH 4 BULK FIX RESULTS ===")
    print(f"Files modified: {total_files_modified}")
    print(f"Violations fixed: {total_violations_fixed}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nErrors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

    return total_files_modified, total_violations_fixed, errors

if __name__ == "__main__":
    print("WebSocket Manager SSOT Consolidation - Phase 2 Batch 4")
    print("Fixing canonical_import_patterns violations...")
    fix_websocket_imports()