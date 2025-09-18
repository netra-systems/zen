#!/usr/bin/env python3
"""
Batch SSOT Logging Migration Script for Issue #1076

This script efficiently migrates multiple files from deprecated logging patterns
to the SSOT unified logging system.
"""

import os
import re
import sys
from pathlib import Path

def migrate_file(file_path):
    """Migrate a single file to SSOT logging pattern."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Pattern 1: Standard import logging + logger = logging.getLogger(__name__)
        pattern1 = r'^import logging\n(.*?)^logger = logging\.getLogger\(__name__\)$'
        replacement1 = r'from shared.logging.unified_logging_ssot import get_logger\n\1logger = get_logger(__name__)'
        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 2: import logging within imports + separate logger line
        pattern2 = r'^(.*?)import logging\n(.*?)^logger = logging\.getLogger\(__name__\)$'
        def replacement2(match):
            before = match.group(1)
            between = match.group(2)
            # Add the SSOT import at the end of the import section
            return f"{before}{between}from shared.logging.unified_logging_ssot import get_logger\n\nlogger = get_logger(__name__)"

        content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 3: Just remove standalone import logging if logger line was already handled
        content = re.sub(r'^import logging\n', '', content, flags=re.MULTILINE)

        # Pattern 4: Handle central_logger imports
        content = re.sub(
            r'from netra_backend\.app\.logging_config import central_logger',
            'from shared.logging.unified_logging_ssot import get_logger',
            content
        )

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error migrating {file_path}: {e}")
        return False

def main():
    """Main migration function."""
    if len(sys.argv) < 2:
        print("Usage: python migrate_logging_batch.py <file1> <file2> ...")
        sys.exit(1)

    files = sys.argv[1:]
    migrated_count = 0

    for file_path in files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue

        if migrate_file(file_path):
            print(f"[OK] Migrated: {file_path}")
            migrated_count += 1
        else:
            print(f"[--] No changes: {file_path}")

    print(f"\nMigration complete: {migrated_count}/{len(files)} files updated")

if __name__ == "__main__":
    main()