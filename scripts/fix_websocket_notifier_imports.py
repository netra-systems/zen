#!/usr/bin/env python3
"""
Fix WebSocketNotifier imports across the codebase.

This script updates all deprecated WebSocketNotifier import paths to use the correct
AgentWebSocketBridge import from the SSOT location.

WebSocketNotifier is DEPRECATED - replaced with AgentWebSocketBridge.
"""

import os
import re
import sys
from typing import List, Tuple, Set
from pathlib import Path

def find_files_with_notifier_imports() -> List[str]:
    """Find all Python files with WebSocketNotifier imports."""
    files = []
    root_dir = Path(".")
    
    for py_file in root_dir.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'WebSocketNotifier' in content:
                    files.append(str(py_file))
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return files

def fix_file_imports(file_path: str) -> Tuple[bool, List[str]]:
    """Fix WebSocketNotifier imports in a single file.
    
    Returns:
        Tuple of (was_modified, list_of_changes)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Pattern 1: Direct import from deprecated websocket_notifier module
        pattern1 = r'from\s+netra_backend\.app\.agents\.supervisor\.websocket_notifier\s+import\s+WebSocketNotifier'
        if re.search(pattern1, content):
            content = re.sub(pattern1, 'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge', content)
            changes.append("Updated deprecated supervisor websocket_notifier import")
        
        # Pattern 2: Import from non-existent websocket_core.websocket_notifier
        pattern2 = r'from\s+netra_backend\.app\.websocket_core\.websocket_notifier\s+import\s+WebSocketNotifier'
        if re.search(pattern2, content):
            content = re.sub(pattern2, 'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge', content)
            changes.append("Fixed non-existent websocket_core.websocket_notifier import")
        
        # Pattern 3: Import from non-existent services.websocket_notifier
        pattern3 = r'from\s+netra_backend\.app\.services\.websocket_notifier\s+import\s+WebSocketNotifier'
        if re.search(pattern3, content):
            content = re.sub(pattern3, 'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge', content)
            changes.append("Fixed non-existent services.websocket_notifier import")
        
        # Pattern 4: Replace WebSocketNotifier class references with AgentWebSocketBridge
        # Only replace instantiation and type hints, not inside comments or strings
        pattern4 = r'\bWebSocketNotifier(?!\s*=|\s*\(|\s*:)'  # Don't replace when used as variable name
        if re.search(pattern4, content):
            # This is more complex - we need to be careful not to break existing code
            # For now, just replace direct class references
            content = re.sub(r'\bWebSocketNotifier\b(?=\s*\()', 'AgentWebSocketBridge', content)
            content = re.sub(r':\s*WebSocketNotifier\b', ': AgentWebSocketBridge', content)
            changes.append("Updated WebSocketNotifier class references")
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        
        return False, []
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, []

def main():
    """Main function to fix all WebSocketNotifier imports."""
    print("Scanning for WebSocketNotifier import issues...")
    
    files = find_files_with_notifier_imports()
    print(f"Found {len(files)} files with WebSocketNotifier references")
    
    if not files:
        print("No files found with WebSocketNotifier imports to fix")
        return
    
    modified_files = 0
    total_changes = 0
    
    for file_path in files:
        was_modified, changes = fix_file_imports(file_path)
        if was_modified:
            modified_files += 1
            total_changes += len(changes)
            print(f"MODIFIED: {file_path}:")
            for change in changes:
                print(f"    - {change}")
        else:
            print(f"SKIPPED: {file_path}: No import fixes needed")
    
    print(f"\nSummary:")
    print(f"   - {modified_files} files modified")
    print(f"   - {total_changes} total changes made")
    
    if modified_files > 0:
        print(f"\nIMPORTANT:")
        print(f"   - WebSocketNotifier is DEPRECATED")
        print(f"   - Use AgentWebSocketBridge instead")
        print(f"   - Review instantiation patterns manually")
        print(f"   - Run tests to verify functionality")

if __name__ == "__main__":
    main()