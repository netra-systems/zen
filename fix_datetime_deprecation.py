#!/usr/bin/env python3
"""
Systematic fix for datetime.utcnow() deprecation warnings (Issue #826)
Replaces datetime.utcnow() with datetime.now(UTC) across the codebase
"""

import os
import re
from pathlib import Path

def fix_datetime_in_file(file_path):
    """Fix datetime.utcnow() deprecation in a single file"""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Check if file already uses UTC import
        has_utc_import = 'from datetime import' in content and 'UTC' in content
        has_datetime_import = re.search(r'from datetime import.*datetime', content)
        has_datetime_utcnow = 'datetime.utcnow()' in content

        if not has_datetime_utcnow:
            return False, "No datetime.utcnow() found"

        # Fix the import statement
        if has_datetime_import and not has_utc_import:
            # Find and update existing datetime import
            content = re.sub(
                r'from datetime import ([^UTC\n]*?)(?=\n|$)',
                r'from datetime import \1, UTC',
                content
            )
            # Clean up any duplicate commas or spaces
            content = re.sub(r'from datetime import ([^,\n]*), , UTC', r'from datetime import \1, UTC', content)
            content = re.sub(r'from datetime import , UTC', r'from datetime import UTC', content)

        # Replace datetime.utcnow() with datetime.now(UTC)
        content = re.sub(r'datetime\.utcnow\(\)', 'datetime.now(UTC)', content)

        # Check if any changes were made
        if content != original_content:
            # Write the file back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Fixed datetime.utcnow() deprecation"
        else:
            return False, "No changes needed"

    except Exception as e:
        return False, f"Error: {str(e)}"

def find_files_with_datetime_utcnow(base_path, exclude_dirs=None):
    """Find all Python files with datetime.utcnow() excluding backup directories"""
    if exclude_dirs is None:
        exclude_dirs = ['backups', '.git', '__pycache__', '.pytest_cache', 'node_modules']

    files_found = []

    for root, dirs, files in os.walk(base_path):
        # Remove excluded directories from dirs list to prevent walking into them
        dirs[:] = [d for d in dirs if not any(exclude in d for exclude in exclude_dirs)]

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'datetime.utcnow()' in content:
                            files_found.append(file_path)
                except:
                    continue

    return files_found

def main():
    """Main function to fix all datetime deprecation warnings"""
    base_path = Path(__file__).parent
    print(f"🔍 Scanning for datetime.utcnow() usage in: {base_path}")

    # Find all files with datetime.utcnow()
    files_to_fix = find_files_with_datetime_utcnow(base_path)

    print(f"📊 Found {len(files_to_fix)} files with datetime.utcnow()")

    if not files_to_fix:
        print("✅ No files need fixing!")
        return

    print("🛠️ Starting fixes...")

    success_count = 0
    error_count = 0

    for file_path in files_to_fix:
        relative_path = os.path.relpath(file_path, base_path)
        success, message = fix_datetime_in_file(file_path)

        if success:
            print(f"✅ {relative_path}: {message}")
            success_count += 1
        else:
            print(f"❌ {relative_path}: {message}")
            error_count += 1

    print(f"\n📈 Summary:")
    print(f"✅ Successfully fixed: {success_count} files")
    print(f"❌ Errors: {error_count} files")

    # Show some examples of remaining usage
    remaining_files = find_files_with_datetime_utcnow(base_path)
    if remaining_files:
        print(f"⚠️ Still {len(remaining_files)} files with datetime.utcnow() - may need manual review")
        for file_path in remaining_files[:5]:  # Show first 5
            relative_path = os.path.relpath(file_path, base_path)
            print(f"   - {relative_path}")
        if len(remaining_files) > 5:
            print(f"   ... and {len(remaining_files) - 5} more")
    else:
        print("🎉 All datetime.utcnow() instances have been fixed!")

if __name__ == "__main__":
    main()