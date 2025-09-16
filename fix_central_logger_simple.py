#!/usr/bin/env python3
"""
Simple script to fix missing central_logger imports.
"""
import os

def add_import_to_file(file_path: str) -> bool:
    """Add central_logger import to a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if already has import
        if ('from netra_backend.app.logging_config import central_logger' in content or
            'from ..logging_config import central_logger' in content):
            return False

        # Skip if doesn't use central_logger
        if 'central_logger' not in content:
            return False

        lines = content.split('\n')

        # Find where to insert import (after existing imports)
        insert_pos = 0
        for i, line in enumerate(lines):
            if (line.strip().startswith('from ') or
                line.strip().startswith('import ') or
                line.strip().startswith('#') or
                line.strip() == '' or
                '"""' in line or "'''" in line):
                if line.strip().startswith('from ') or line.strip().startswith('import '):
                    insert_pos = i + 1
                continue
            else:
                break

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
    """Main function."""
    print("Fixing missing central_logger imports...")

    # Read file list
    with open('files_missing_central_logger_import.txt', 'r') as f:
        files = [line.strip() for line in f if line.strip()]

    fixed = 0
    skipped = 0

    for file_path in files:
        if not os.path.exists(file_path):
            continue

        if add_import_to_file(file_path):
            print(f"Fixed: {file_path}")
            fixed += 1
        else:
            skipped += 1

    print(f"Fixed: {fixed}, Skipped: {skipped}")

if __name__ == "__main__":
    main()