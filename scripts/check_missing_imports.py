#!/usr/bin/env python3
"""Check for files that use central_logger but don't import it."""

import os
import subprocess

def find_files_using_central_logger():
    """Find all Python files that use central_logger."""
    result = subprocess.run([
        'grep', '-r', 'central_logger', 'netra_backend/',
        '--include=*.py', '-l'
    ], capture_output=True, text=True)
    return result.stdout.strip().split('\n') if result.stdout.strip() else []

def check_file_has_import(file_path):
    """Check if file has central_logger import."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return ('from netra_backend.app.logging_config import central_logger' in content or
                'from ..logging_config import central_logger' in content or
                'import central_logger' in content)
    except:
        return False

def check_file_uses_central_logger(file_path):
    """Check if file actually uses central_logger (not just defines it)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Uses central_logger but doesn't define it
        return ('central_logger' in content and
                'central_logger =' not in content and
                'def central_logger' not in content)
    except:
        return False

def main():
    files_using_central_logger = find_files_using_central_logger()
    print(f"Total files using central_logger: {len(files_using_central_logger)}")

    missing_import = []
    has_import = []

    for file_path in files_using_central_logger:
        if not os.path.exists(file_path):
            continue

        if check_file_uses_central_logger(file_path):
            if check_file_has_import(file_path):
                has_import.append(file_path)
            else:
                missing_import.append(file_path)

    print(f"Files with proper import: {len(has_import)}")
    print(f"Files missing import: {len(missing_import)}")

    if missing_import:
        print("\nFiles missing import:")
        for file_path in missing_import[:10]:  # Show first 10
            print(f"  {file_path}")
        if len(missing_import) > 10:
            print(f"  ... and {len(missing_import) - 10} more")
    else:
        print("\n✅ All files that use central_logger have the proper import!")

if __name__ == "__main__":
    main()