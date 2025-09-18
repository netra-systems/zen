#!/usr/bin/env python3
"""
Script to systematically add missing central_logger imports to all files that use it.
This fixes the critical staging deployment failures caused by missing imports.
"""
import os
import re
from pathlib import Path
from typing import List, Set

def find_files_missing_import() -> List[str]:
    """Find all Python files that use central_logger but don't import it."""
    files_missing_import = []

    # Read the file list we created
    with open('files_missing_central_logger_import.txt', 'r') as f:
        files_missing_import = [line.strip() for line in f if line.strip()]

    return files_missing_import

def has_central_logger_import(file_path: str) -> bool:
    """Check if file already has central_logger import."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return ('from netra_backend.app.logging_config import central_logger' in content or
                   'from ..logging_config import central_logger' in content or
                   'import central_logger' in content)
    except Exception:
        return False

def uses_central_logger(file_path: str) -> bool:
    """Check if file uses central_logger."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return 'central_logger' in content and 'def central_logger' not in content and 'central_logger =' not in content
    except Exception:
        return False

def get_import_location(content: str) -> int:
    """Find the best location to insert the import."""
    lines = content.split('\n')

    # Look for existing imports
    last_import_line = -1
    for i, line in enumerate(lines):
        if (line.strip().startswith('import ') or
            line.strip().startswith('from ') or
            line.strip().startswith('#') or
            line.strip().startswith('"""') or
            line.strip().startswith("'''") or
            line.strip() == ''):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                last_import_line = i
            continue
        else:
            break

    # If no imports found, add after docstring/comments
    if last_import_line == -1:
        for i, line in enumerate(lines):
            if (line.strip().startswith('#') or
                line.strip().startswith('"""') or
                line.strip().startswith("'''") or
                line.strip() == ''):
                continue
            else:
                return i
        return 0

    return last_import_line + 1

def add_import_to_file(file_path: str) -> bool:
    """Add central_logger import to a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if already has import
        if has_central_logger_import(file_path):
            return False

        # Skip if doesn't use central_logger
        if not uses_central_logger(file_path):
            return False

        lines = content.split('\n')
        insert_pos = get_import_location(content)

        # Add the import
        import_line = 'from netra_backend.app.logging_config import central_logger'
        lines.insert(insert_pos, import_line)

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all missing imports."""
    print("Starting systematic fix of missing central_logger imports...")

    files_missing_import = find_files_missing_import()
    print(f"Found {len(files_missing_import)} files that might need the import")

    fixed_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in files_missing_import:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            error_count += 1
            continue

        try:
            if add_import_to_file(file_path):
                print(f"✅ Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"⏭️  Skipped: {file_path} (already has import or doesn't use central_logger)")
                skipped_count += 1
        except Exception as e:
            print(f"❌ Error: {file_path} - {e}")
            error_count += 1

    print(f"\n📊 Summary:")
    print(f"   Fixed: {fixed_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Errors: {error_count}")
    print(f"   Total: {len(files_missing_import)}")

if __name__ == "__main__":
    main()