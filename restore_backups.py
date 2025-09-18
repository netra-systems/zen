#!/usr/bin/env python3
"""
Emergency Rollback Script - Restore from backups
"""

import os
import shutil
from pathlib import Path

def restore_from_backups():
    """Restore files from 084026 backup timestamp"""

    base_path = Path(".")
    backup_timestamp = "20250917_084026"

    # Find all backup files
    backup_files = list(base_path.rglob(f"*.backup_{backup_timestamp}"))

    print(f"Found {len(backup_files)} backup files from {backup_timestamp}")

    restored_count = 0
    failed_count = 0

    for backup_file in backup_files:
        try:
            # Determine original file path
            original_file = Path(str(backup_file).replace(f".backup_{backup_timestamp}", ""))

            if backup_file.exists():
                print(f"Restoring: {original_file}")
                shutil.copy2(backup_file, original_file)
                restored_count += 1
            else:
                print(f"WARNING: Backup file missing: {backup_file}")
                failed_count += 1

        except Exception as e:
            print(f"ERROR restoring {backup_file}: {e}")
            failed_count += 1

    print(f"\nRollback Summary:")
    print(f"- Restored: {restored_count} files")
    print(f"- Failed: {failed_count} files")

    return restored_count > 0

if __name__ == "__main__":
    success = restore_from_backups()
    print("Rollback completed" if success else "Rollback failed")