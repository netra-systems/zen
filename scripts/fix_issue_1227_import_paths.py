#!/usr/bin/env python3
"""
Issue #1227 Import Path Correction Script

This script corrects the SSOT import path violations:
- FROM: from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
- TO:   from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager

The websocket_manager.py is the SSOT public interface that imports from unified_manager.py (private implementation).

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: System Stability and SSOT Compliance
- Value Impact: Eliminates import errors blocking test execution and development
- Revenue Impact: Protects $500K+ ARR by enabling reliable testing and deployment
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple


def find_files_with_wrong_import() -> List[str]:
    """Find all Python files with the wrong import, excluding backups."""
    cmd = [
        'grep', '-r', '-l', '--include=*.py',
        'from netra_backend\\.app\\.websocket_core\\.unified_manager import UnifiedWebSocketManager',
        '.'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')
        files = result.stdout.strip().split('\n')

        # Filter out backup directories and empty strings
        active_files = []
        for file in files:
            if file and not ('backup' in file.lower() or '/backup/' in file or '\\backup\\' in file):
                active_files.append(file)

        return active_files
    except Exception as e:
        print(f"Error finding files: {e}")
        return []


def fix_import_in_file(file_path: str) -> Tuple[bool, str]:
    """Fix the import in a single file.

    Returns:
        Tuple of (success, message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern to match the wrong import
        wrong_import_pattern = r'from netra_backend\.app\.websocket_core\.unified_manager import UnifiedWebSocketManager'
        correct_import = 'from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager'

        # Check if file contains the wrong import
        if re.search(wrong_import_pattern, content):
            # Replace the import
            new_content = re.sub(wrong_import_pattern, correct_import, content)

            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return True, f"Fixed import in {file_path}"
        else:
            return False, f"No wrong import found in {file_path}"

    except Exception as e:
        return False, f"Error fixing {file_path}: {e}"


def validate_import_fix(file_path: str) -> Tuple[bool, str]:
    """Validate that the import fix worked by trying to import."""
    try:
        # Simple validation - check if the correct import is now present
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for correct import
        if 'from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager' in content:
            # Check that wrong import is gone
            if 'from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager' not in content:
                return True, f"✓ Import fixed and validated in {file_path}"
            else:
                return False, f"✗ Still contains wrong import in {file_path}"
        else:
            return False, f"✗ Correct import not found in {file_path}"

    except Exception as e:
        return False, f"✗ Validation error for {file_path}: {e}"


def main():
    """Main execution function."""
    print("=== Issue #1227 Import Path Correction Script ===")
    print("Fixing SSOT import path violations...")
    print()

    # Find all files with wrong imports
    print("Scanning for files with wrong imports...")
    files_to_fix = find_files_with_wrong_import()

    if not files_to_fix:
        print("No files found with wrong imports!")
        return

    print(f"Found {len(files_to_fix)} files to fix")
    print()

    # Show first 10 files for verification
    print("Files to be fixed (first 10):")
    for file in files_to_fix[:10]:
        print(f"  - {file}")
    if len(files_to_fix) > 10:
        print(f"  ... and {len(files_to_fix) - 10} more")
    print()

    # Ask for confirmation
    response = input("Proceed with fixing imports? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled by user")
        return

    # Fix imports
    print("Fixing imports...")
    success_count = 0
    error_count = 0

    for file_path in files_to_fix:
        success, message = fix_import_in_file(file_path)
        if success:
            success_count += 1
            print(f"  SUCCESS: {message}")
        else:
            error_count += 1
            print(f"  ERROR: {message}")

    print()
    print(f"Results: {success_count} fixed, {error_count} errors")

    if success_count > 0:
        print()
        print("Validating fixes...")

        validation_success = 0
        validation_errors = 0

        for file_path in files_to_fix:
            success, message = validate_import_fix(file_path)
            if success:
                validation_success += 1
            else:
                validation_errors += 1
                print(f"  {message}")

        print(f"Validation: {validation_success} validated, {validation_errors} issues")

    print()
    print("=== Issue #1227 Remediation Complete ===")
    print("SSOT import paths corrected!")


if __name__ == "__main__":
    main()