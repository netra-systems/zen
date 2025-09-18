#!/usr/bin/env python3
"""
Batch convert fragmented imports to SSOT patterns for Issue #1196
"""

import re
import subprocess
from pathlib import Path

def get_files_to_convert():
    """Get files that need conversion using ripgrep"""
    try:
        result = subprocess.run([
            'rg', '-l', 'from netra_backend\\.app\\.core\\.configuration\\.base import',
            'tests/', 'netra_backend/'
        ], capture_output=True, text=True, cwd='C:/GitHub/netra-apex')

        files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
        # Filter out backup files
        files = [f for f in files if 'backup' not in f.lower()]
        return files
    except Exception as e:
        print(f"Error getting files: {e}")
        return []

def convert_file(file_path):
    """Convert a single file"""
    full_path = Path('C:/GitHub/netra-apex') / file_path

    if not full_path.exists():
        return False, "File not found"

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Pattern 1: Replace get_unified_config with get_config
        content = re.sub(r'\bget_unified_config\b', 'get_config', content)

        # Pattern 2: Replace simple fragmented imports
        content = re.sub(
            r'from netra_backend\.app\.core\.configuration\.base import get_unified_config',
            'from netra_backend.app.config import get_config',
            content
        )

        # Pattern 3: Replace UnifiedConfigManager instantiation
        content = re.sub(r'\bUnifiedConfigManager\(\)', 'config_manager', content)

        # Pattern 4: Replace complex imports - handle common patterns
        content = re.sub(
            r'from netra_backend\.app\.core\.configuration\.base import UnifiedConfigManager',
            'from netra_backend.app.config import config_manager',
            content
        )

        content = re.sub(
            r'from netra_backend\.app\.core\.configuration\.base import config_manager',
            'from netra_backend.app.config import config_manager',
            content
        )

        # Pattern 5: Handle multi-line complex imports
        patterns_to_replace = [
            (r'from netra_backend\.app\.core\.configuration\.base import UnifiedConfigManager, get_config.*',
             'from netra_backend.app.config import get_config, config_manager'),
            (r'from netra_backend\.app\.core\.configuration\.base import get_config, config_manager.*',
             'from netra_backend.app.config import get_config, config_manager'),
        ]

        for pattern, replacement in patterns_to_replace:
            content = re.sub(pattern, replacement, content)

        if content != original_content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Converted"
        else:
            return False, "No changes needed"

    except Exception as e:
        return False, f"Error: {e}"

def main():
    print("Getting files to convert...")
    files = get_files_to_convert()

    if not files:
        print("No files found to convert.")
        return

    print(f"Found {len(files)} files to process")

    converted = 0
    skipped = 0
    errors = 0

    for file_path in files:
        success, message = convert_file(file_path)
        if success:
            print(f"[OK] {file_path}")
            converted += 1
        elif "No changes needed" in message:
            print(f"[SKIP] {file_path}")
            skipped += 1
        else:
            print(f"[ERROR] {file_path}: {message}")
            errors += 1

    print(f"\nSummary: {converted} converted, {skipped} skipped, {errors} errors")

if __name__ == '__main__':
    main()