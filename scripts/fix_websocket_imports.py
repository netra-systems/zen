#!/usr/bin/env python
"""Fix WebSocket imports to use unified system directly.

This script updates all imports from the duplicate compatibility wrappers
to use the main WebSocket manager directly.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_files_with_pattern(root_dir: str, pattern: str) -> List[Path]:
    """Find all Python files containing the pattern."""
    files = []
    root_path = Path(root_dir)
    
    for py_file in root_path.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(encoding='utf-8')
            if re.search(pattern, content):
                files.append(py_file)
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return files

def update_imports(file_path: Path, replacements: List[Tuple[str, str]]) -> bool:
    """Update imports in a file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        for old_import, new_import in replacements:
            content = re.sub(old_import, new_import, content)
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main function to fix WebSocket imports."""
    root_dir = Path(__file__).parent.parent / "netra_backend"
    
    # Define import replacements
    replacements = [
        # Replace imports from services.websocket_manager
        (
            r'from netra_backend\.app\.services\.websocket_manager import ([^\n]+)',
            r'from netra_backend.app.ws_manager import \1'
        ),
        # Replace imports from services.websocket.ws_manager
        (
            r'from netra_backend\.app\.services\.websocket\.ws_manager import ([^\n]+)',
            r'from netra_backend.app.ws_manager import \1'
        ),
        # Replace imports from services.websocket_service
        (
            r'from netra_backend\.app\.services\.websocket_service import ([^\n]+)',
            r'from netra_backend.app.ws_manager import WebSocketManager as IWebSocketService'
        ),
        # Replace get_ws_manager imports
        (
            r'from netra_backend\.app\.services\.websocket import get_ws_manager',
            r'from netra_backend.app.ws_manager import get_ws_manager'
        ),
    ]
    
    # Find all files that need updating
    patterns = [
        r'from netra_backend\.app\.services\.websocket_manager import',
        r'from netra_backend\.app\.services\.websocket\.ws_manager import',
        r'from netra_backend\.app\.services\.websocket_service import',
        r'from netra_backend\.app\.services\.websocket import get_ws_manager'
    ]
    
    all_files = set()
    for pattern in patterns:
        files = find_files_with_pattern(str(root_dir), pattern)
        all_files.update(files)
    
    print(f"Found {len(all_files)} files to update")
    
    # Update imports in each file
    updated_count = 0
    for file_path in sorted(all_files):
        if update_imports(file_path, replacements):
            print(f"Updated: {file_path.relative_to(root_dir.parent)}")
            updated_count += 1
    
    print(f"\nSuccessfully updated {updated_count} files")
    
    # Files to remove
    files_to_remove = [
        root_dir / "app" / "services" / "websocket_manager.py",
        root_dir / "app" / "services" / "websocket_service.py",
        root_dir / "app" / "services" / "websocket" / "ws_manager.py",
        root_dir / "tests" / "supervisor_test_helpers.py.backup",
        root_dir / "tests" / "supervisor_test_helpers.py.backup2",
    ]
    
    print("\n" + "="*50)
    print("Files to remove:")
    for file_path in files_to_remove:
        if file_path.exists():
            print(f"  - {file_path.relative_to(root_dir.parent)}")
    
    print("\nRun the following commands to remove duplicate files:")
    for file_path in files_to_remove:
        if file_path.exists():
            print(f'del "{file_path}"')

if __name__ == "__main__":
    main()