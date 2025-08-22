"""Fix ModernConnectionManager import issues across the codebase."""
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def fix_imports_in_file(file_path: Path) -> bool:
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return False
    
    original_content = content
    
    # Pattern 1: ModernConnectionManager direct import
    pattern1 = r'from netra_backend\.app\.websocket\.connection_manager import ConnectionManager\b'
    replacement1 = 'from netra_backend.app.websocket.connection_manager import ModernConnectionManager'
    content = re.sub(pattern1, replacement1, content)
    
    # Pattern 2: ModernConnectionManager with alias
    pattern2 = r'from netra_backend\.app\.websocket\.connection_manager import ModernConnectionManager as (\w+)'
    replacement2 = r'from netra_backend.app.websocket.connection_manager import ModernConnectionManager as \1'
    content = re.sub(pattern2, replacement2, content)
    
    # Pattern 3: Multi-import with ModernConnectionManager
    pattern3 = r'ConnectionManager(?=[\s,\)])'
    if 'from netra_backend.app.websocket.connection_manager import' in content:
        content = re.sub(pattern3, 'ModernConnectionManager', content)
    
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"  Error writing {file_path}: {e}")
            return False
    
    return False

def find_files_to_fix(root_dir: Path) -> List[Path]:
    """Find all Python files that might need fixing."""
    files_to_fix = []
    
    # Patterns to search for
    patterns = [
        '*.py',
    ]
    
    # Directories to search
    search_dirs = [
        root_dir / 'netra_backend' / 'tests',
        root_dir / 'tests',
        root_dir / 'scripts',
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            for pattern in patterns:
                files_to_fix.extend(search_dir.rglob(pattern))
    
    return files_to_fix

def main():
    """Main function to fix all imports."""
    # Get project root
    project_root = Path(__file__).parent.parent
    
    print("Fixing ModernConnectionManager imports...")
    print(f"Project root: {project_root}")
    
    # Find files to fix
    files_to_fix = find_files_to_fix(project_root)
    print(f"Found {len(files_to_fix)} Python files to check")
    
    # Fix imports
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_imports_in_file(file_path):
            print(f"  Fixed: {file_path.relative_to(project_root)}")
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")
    
    # Also check for any remaining bad imports
    print("\nChecking for any remaining ModernConnectionManager imports...")
    remaining_issues = []
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'from netra_backend.app.websocket.connection_manager import ModernConnectionManager' in content:
                remaining_issues.append(file_path)
        except:
            pass
    
    if remaining_issues:
        print(f"Warning: {len(remaining_issues)} files still have ModernConnectionManager imports:")
        for path in remaining_issues[:5]:
            print(f"  - {path.relative_to(project_root)}")
    else:
        print("All ModernConnectionManager imports have been fixed!")
    
    return 0 if not remaining_issues else 1

if __name__ == "__main__":
    sys.exit(main())