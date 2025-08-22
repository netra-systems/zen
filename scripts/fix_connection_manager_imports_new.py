"""Fix all ConnectionManager imports to use ConnectionManager.

Business Value Justification (BVJ):
1. Segment: Platform/Internal
2. Business Goal: Development Velocity, Stability
3. Value Impact: Reduces confusion and bugs from duplicate class names
4. Strategic Impact: Cleaner codebase improves development speed
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_files_with_pattern(root_dir: str, pattern: str) -> List[Path]:
    """Find all Python files containing the pattern."""
    files_to_fix = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip virtual environments and cache directories
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if pattern in content:
                            files_to_fix.append(file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return files_to_fix

def fix_imports_in_file(file_path: Path) -> bool:
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix the import patterns
        replacements = [
            # Fix ConnectionManager imports
            (r'from netra_backend\.app\.websocket\.connection_manager import ConnectionManager\b',
             'from netra_backend.app.websocket.connection_manager import ConnectionManager'),
            
            # Fix ConnectionManager as alias
            (r'ConnectionManager as (\w+)',
             r'ConnectionManager as \1'),
            
            # Fix any remaining ConnectionManager references
            (r'\bConnectionManager\b',
             'ConnectionManager'),
            
            # Also fix ConnectionManager references (single Modern)
            (r'from netra_backend\.app\.websocket\.connection_manager import ConnectionManager\b',
             'from netra_backend.app.websocket.connection_manager import ConnectionManager'),
            
            (r'\bModernConnectionManager\b',
             'ConnectionManager'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main execution function."""
    print("Starting ConnectionManager import fixes...")
    
    # Get the project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Find all files with incorrect imports
    print("\nSearching for files with ConnectionManager imports...")
    files_to_fix = find_files_with_pattern(
        str(project_root), 
        'ConnectionManager'
    )
    
    print(f"Found {len(files_to_fix)} files to fix")
    
    # Fix each file
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_imports_in_file(file_path):
            print(f"Fixed: {file_path.relative_to(project_root)}")
            fixed_count += 1
    
    # Also check for ConnectionManager (single Modern)
    print("\nSearching for files with ConnectionManager imports...")
    files_with_modern = find_files_with_pattern(
        str(project_root),
        'ConnectionManager'
    )
    
    for file_path in files_with_modern:
        if file_path not in files_to_fix:  # Don't process twice
            if fix_imports_in_file(file_path):
                print(f"Fixed: {file_path.relative_to(project_root)}")
                fixed_count += 1
    
    print(f"\n✅ Successfully fixed {fixed_count} files")
    print("ConnectionManager consolidation complete!")

if __name__ == "__main__":
    main()