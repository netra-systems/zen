#!/usr/bin/env python3
"""
Issue #974 Import Fix Script - Fix broken agent registry imports

This script systematically fixes all files using the deprecated import path:
from netra_backend.app.core.agent_registry import AgentRegistry

Replaces with the modern SSOT import:
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
"""

import os
import re
import glob
from typing import List, Tuple

def find_files_with_broken_imports() -> List[str]:
    """Find all files with the broken import pattern."""
    files_found = []

    # Search patterns for different file types
    search_patterns = [
        'tests/**/*.py',
        'netra_backend/**/*.py',
        'auth_service/**/*.py',
        'frontend/**/*.py'
    ]

    for pattern in search_patterns:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'from netra_backend.app.core.agent_registry import' in content:
                        files_found.append(file_path)
            except (UnicodeDecodeError, PermissionError, FileNotFoundError):
                # Skip files that can't be read
                continue

    return files_found

def fix_imports_in_file(file_path: str) -> Tuple[bool, str]:
    """Fix the imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern to match the broken import
        old_pattern = r'from netra_backend\.app\.core\.agent_registry import'
        new_replacement = 'from netra_backend.app.agents.supervisor.agent_registry import'

        # Check if file contains the broken import
        if not re.search(old_pattern, content):
            return False, "No broken imports found"

        # Replace the import
        new_content = re.sub(old_pattern, new_replacement, content)

        # Write the file back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True, "Fixed successfully"

    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Main execution function."""
    print("Issue #974 Import Fix Script - Starting...")
    print("=" * 60)

    # Find all files with broken imports
    print("🔍 Scanning for files with broken imports...")
    files_with_issues = find_files_with_broken_imports()

    if not files_with_issues:
        print("✅ No files found with broken imports!")
        return

    print(f"Found {len(files_with_issues)} files with broken imports:")
    for i, file_path in enumerate(files_with_issues, 1):
        print(f"  {i}. {file_path}")

    print("\n🔧 Fixing imports...")
    print("-" * 40)

    fixed_count = 0
    error_count = 0

    for file_path in files_with_issues:
        success, message = fix_imports_in_file(file_path)
        if success:
            fixed_count += 1
            print(f"✅ {file_path}: {message}")
        else:
            error_count += 1
            print(f"❌ {file_path}: {message}")

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"✅ Files fixed: {fixed_count}")
    print(f"❌ Files with errors: {error_count}")
    print(f"📊 Total files processed: {len(files_with_issues)}")

    if error_count == 0:
        print("\n🎉 All imports fixed successfully!")
        print("Issue #974 remediation completed.")
    else:
        print(f"\n⚠️  {error_count} files had errors and may need manual fixing.")

if __name__ == "__main__":
    main()