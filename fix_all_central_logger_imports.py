#!/usr/bin/env python3
"""
Comprehensive script to fix ALL missing central_logger imports.
"""
import os
import sys

def check_and_fix_file(file_path: str) -> bool:
    """Check and fix a single file."""
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if already has the specific import we want
        if 'from netra_backend.app.logging_config import central_logger' in content:
            return False

        # Skip if doesn't actually use central_logger
        if 'central_logger' not in content:
            return False

        # Skip if it defines central_logger (like logging_config.py itself)
        if 'central_logger =' in content or 'def central_logger' in content:
            return False

        lines = content.split('\n')

        # Find the insertion point
        insert_pos = 0
        in_docstring = False
        docstring_chars = ['"""', "'''"]

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Handle docstrings
            for char in docstring_chars:
                if char in stripped:
                    in_docstring = not in_docstring

            if in_docstring:
                continue

            # Skip comments and empty lines at the beginning
            if (stripped.startswith('#') or stripped == '' or
                any(char in stripped for char in docstring_chars)):
                continue

            # If we find an import, keep track of the last one
            if stripped.startswith('from ') or stripped.startswith('import '):
                insert_pos = i + 1
                continue

            # If we hit non-import code, break
            break

        # Insert the import
        import_line = 'from netra_backend.app.logging_config import central_logger'
        lines.insert(insert_pos, import_line)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Process all files."""
    # Read the list of files
    with open('all_files_missing_import.txt', 'r') as f:
        all_files = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(all_files)} files...")

    fixed = 0
    skipped = 0
    errors = 0

    for i, file_path in enumerate(all_files):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(all_files)} ({i/len(all_files)*100:.1f}%)")

        if not os.path.exists(file_path):
            errors += 1
            continue

        try:
            if check_and_fix_file(file_path):
                fixed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"Error with {file_path}: {e}")
            errors += 1

    print(f"\nResults:")
    print(f"Fixed: {fixed}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print(f"Total: {len(all_files)}")

if __name__ == "__main__":
    main()