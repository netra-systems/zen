#!/usr/bin/env python3
"""Script to update WebSocketNotifier imports from deprecated to SSOT pattern.

This script is part of Phase 1 of the WebSocketNotifier SSOT remediation.
It updates import statements but NOT instantiation patterns (those need manual review).
"""

import os
import re
import subprocess
from typing import List, Set

def find_files_with_deprecated_imports() -> List[str]:
    """Find all files with deprecated WebSocketNotifier imports."""
    cmd = ['grep', '-r', '-l', 
           'from netra_backend\.app\.agents\.supervisor\.websocket_notifier import',
           '.']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/anthony/Desktop/netra-apex')
        files = [f for f in result.stdout.strip().split('\n') if f.strip()]
        # Filter to Python files only
        return [f for f in files if f.endswith('.py')]
    except subprocess.CalledProcessError:
        return []

def update_import_in_file(file_path: str) -> bool:
    """Update the deprecated import in a single file.
    
    Returns True if file was modified, False otherwise.
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Pattern to match the deprecated import
        old_pattern = r'from netra_backend\.app\.agents\.supervisor\.websocket_notifier import WebSocketNotifier'
        new_import = 'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'
        
        # Replace the import
        new_content = re.sub(old_pattern, new_import, content)
        
        if new_content != content:
            with open(file_path, 'w') as f:
                f.write(new_content)
            return True
        
        return False
    
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main function to update all files with deprecated imports."""
    print("🔍 Finding files with deprecated WebSocketNotifier imports...")
    
    files = find_files_with_deprecated_imports()
    print(f"📁 Found {len(files)} files with deprecated imports")
    
    if not files:
        print("✅ No files found with deprecated imports")
        return
    
    # Filter out files we already updated
    already_updated = [
        'tests/mission_critical/test_websocket_agent_events_suite.py',
        'tests/mission_critical/test_first_message_experience.py', 
        'tests/mission_critical/test_websocket_basic_events.py'
    ]
    
    files = [f for f in files if not any(f.endswith(skip) for skip in already_updated)]
    
    print(f"📝 Updating {len(files)} files...")
    
    updated_count = 0
    failed_files = []
    
    for file_path in files:
        print(f"  📄 Updating {file_path}...")
        if update_import_in_file(file_path):
            updated_count += 1
            print(f"    ✅ Updated")
        else:
            failed_files.append(file_path)
            print(f"    ❌ Failed or no changes needed")
    
    print(f"\n📊 Summary:")
    print(f"  ✅ Updated: {updated_count} files")
    print(f"  ❌ Failed: {len(failed_files)} files")
    
    if failed_files:
        print(f"\n❌ Failed files:")
        for f in failed_files:
            print(f"  - {f}")
    
    print(f"\n⚠️  IMPORTANT: This script only updates IMPORT statements.")
    print(f"   WebSocketNotifier instantiation still needs manual review!")
    print(f"   Next step: Review and update instantiation patterns to SSOT factory.")

if __name__ == "__main__":
    main()