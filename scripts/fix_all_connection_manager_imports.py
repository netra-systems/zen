"""Fix all ConnectionManager import issues properly."""
import os
import re
import sys
from pathlib import Path

def fix_file(file_path: Path) -> bool:
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return False
    
    original_content = content
    
    # Fix all variations of the import to use just ConnectionManager
    patterns = [
        (r'from netra_backend\.app\.websocket\.connection_manager import ConnectionManager\b', 
         'from netra_backend.app.websocket.connection_manager import ConnectionManager'),
        (r'from netra_backend\.app\.websocket\.connection_manager import ConnectionManager\b',
         'from netra_backend.app.websocket.connection_manager import ConnectionManager'),
        (r'from netra_backend\.app\.websocket\.connection_manager import ConnectionManager as (\w+)',
         r'from netra_backend.app.websocket.connection_manager import ConnectionManager as \1'),
        (r'from netra_backend\.app\.websocket\.connection_manager import ConnectionManager as (\w+)',
         r'from netra_backend.app.websocket.connection_manager import ConnectionManager as \1'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Also fix standalone references
    if 'netra_backend.app.websocket.connection_manager' in content:
        content = content.replace('ConnectionManager', 'ConnectionManager')
        content = content.replace('ConnectionManager', 'ConnectionManager')
    
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"  Error writing {file_path}: {e}")
            return False
    
    return False

def main():
    """Main function."""
    project_root = Path(__file__).parent.parent
    
    print("Fixing all ConnectionManager imports...")
    print(f"Project root: {project_root}")
    
    # Find Python files to fix
    dirs_to_check = [
        project_root / 'netra_backend' / 'tests',
        project_root / 'tests',
        project_root / 'scripts',
    ]
    
    python_files = []
    for dir_path in dirs_to_check:
        if dir_path.exists():
            python_files.extend(dir_path.rglob('*.py'))
    
    print(f"Found {len(python_files)} Python files to check")
    
    fixed_count = 0
    for file_path in python_files:
        if fix_file(file_path):
            print(f"  Fixed: {file_path.relative_to(project_root)}")
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")
    
    # Check for any remaining issues
    print("\nChecking for any remaining incorrect imports...")
    remaining_issues = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if ('ConnectionManager' in content or 'ConnectionManager' in content) and 'netra_backend.app.websocket.connection_manager' in content:
                remaining_issues.append(file_path)
        except:
            pass
    
    if remaining_issues:
        print(f"Warning: {len(remaining_issues)} files still have incorrect imports:")
        for path in remaining_issues[:5]:
            print(f"  - {path.relative_to(project_root)}")
    else:
        print("All ConnectionManager imports have been fixed!")
    
    return 0 if not remaining_issues else 1

if __name__ == "__main__":
    sys.exit(main())