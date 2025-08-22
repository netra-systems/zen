#!/usr/bin/env python3
"""
Migration script to update imports and references from app/ to netra_backend/app/
This script helps migrate the codebase to the new netra_backend structure.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_files_to_update(root_dir: Path, extensions: List[str]) -> List[Path]:
    """Find all files that might need updating."""
    files = []
    exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'netra_backend'}
    
    for ext in extensions:
        for file_path in root_dir.rglob(f'*{ext}'):
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
            files.append(file_path)
    
    return files

def update_imports_in_file(file_path: Path, dry_run: bool = True) -> List[Tuple[str, str]]:
    """Update imports in a single file."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return changes
    
    original_content = content
    
    # Patterns to replace
    replacements = [
        # Python imports
        (r'from app\.', 'from netra_backend.app.'),
        (r'import app\.', 'import netra_backend.app.'),
        
        # String references in configs/scripts
        (r'"app/', '"netra_backend/app/'),
        (r"'app/", "'netra_backend/app/"),
        
        # Test paths
        (r'app/tests', 'netra_backend/tests'),
        
        # Docker/config references
        (r'COPY app/', 'COPY netra_backend/app/'),
        (r'app\.main:app', 'netra_backend.app.main:app'),
        
        # Alembic references
        (r'script_location = app/alembic', 'script_location = netra_backend/app/alembic'),
    ]
    
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes.append((pattern, replacement))
            content = new_content
    
    if content != original_content:
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Updated {file_path}")
            except Exception as e:
                print(f"❌ Error writing {file_path}: {e}")
        else:
            print(f"Would update {file_path}")
            for pattern, replacement in changes:
                print(f"  {pattern} -> {replacement}")
    
    return changes

def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate app/ to netra_backend/app/')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be changed without making changes')
    parser.add_argument('--apply', action='store_true',
                       help='Actually apply the changes')
    parser.add_argument('--path', type=str, default='.',
                       help='Root path to search for files')
    
    args = parser.parse_args()
    
    if args.apply:
        args.dry_run = False
    
    root_dir = Path(args.path).resolve()
    
    print(f"🔍 Searching for files to update in {root_dir}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLYING CHANGES'}")
    print()
    
    # File extensions to check
    extensions = ['.py', '.yml', '.yaml', '.ini', '.toml', '.cfg', '.json', '.md', '.txt', '.sh']
    
    files = find_files_to_update(root_dir, extensions)
    print(f"Found {len(files)} files to check")
    print()
    
    total_changes = 0
    files_changed = 0
    
    for file_path in files:
        changes = update_imports_in_file(file_path, dry_run=args.dry_run)
        if changes:
            total_changes += len(changes)
            files_changed += 1
    
    print()
    print(f"📊 Summary:")
    print(f"  Files checked: {len(files)}")
    print(f"  Files with changes: {files_changed}")
    print(f"  Total replacements: {total_changes}")
    
    if args.dry_run:
        print()
        print("ℹ️  This was a dry run. To apply changes, run with --apply flag:")
        print("    python migrate_to_netra_backend.py --apply")

if __name__ == '__main__':
    main()