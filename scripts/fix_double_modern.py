"""Fix double Modern prefix in imports."""
import os
import sys
from pathlib import Path

def fix_file(file_path: Path) -> bool:
    """Fix double Modern prefix in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return False
    
    original_content = content
    
    # Fix double Modern prefix
    content = content.replace('ModernConnectionManager', 'ModernConnectionManager')
    
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
    
    print("Fixing double Modern prefix...")
    
    # Find all Python files
    python_files = list(project_root.rglob('*.py'))
    
    fixed_count = 0
    for file_path in python_files:
        if fix_file(file_path):
            print(f"  Fixed: {file_path.relative_to(project_root)}")
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())