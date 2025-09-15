#!/usr/bin/env python3
"""
Comprehensive SSOT Configuration Manager Import Fix - Issue #757
Handles both single-line and multi-line deprecated import patterns.
"""

import os
import re


def fix_imports_in_file(file_path):
    """Fix all deprecated import patterns in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        content = original_content
        changes_made = False

        # Pattern 1: Multi-line import block
        multiline_pattern = r'from netra_backend\.app\.core\.managers\.unified_configuration_manager import \((.*?)\)'
        if re.search(multiline_pattern, content, re.DOTALL):
            canonical_import = """from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_config,
    get_config_value,
    set_config_value,
    validate_config_value,
    get_environment,
    is_production,
    is_development,
    is_testing,
    config_manager
)"""
            content = re.sub(multiline_pattern, canonical_import, content, flags=re.DOTALL)
            changes_made = True

        # Pattern 2: Single-line import for UnifiedConfigurationManager
        single_line_pattern = r'from netra_backend\.app\.core\.managers\.unified_configuration_manager import UnifiedConfigurationManager'
        if re.search(single_line_pattern, content):
            replacement = 'from netra_backend.app.core.configuration.base import UnifiedConfigManager'
            content = re.sub(single_line_pattern, replacement, content)
            changes_made = True

        # Pattern 3: Other single imports (like get_configuration_manager)
        other_imports = [
            ('get_configuration_manager', 'get_config'),
            ('ConfigurationManagerFactory', 'config_manager'),
            ('ConfigurationEntry', 'get_config'),
            ('ConfigurationSource', 'get_environment'),
            ('ConfigurationScope', 'get_config_value'),
            ('ConfigurationStatus', 'validate_config_value'),
        ]

        for old_import, new_import in other_imports:
            pattern = f'from netra_backend\.app\.core\.managers\.unified_configuration_manager import {old_import}'
            if re.search(pattern, content):
                replacement = f'from netra_backend.app.core.configuration.base import {new_import}'
                content = re.sub(pattern, replacement, content)
                changes_made = True

        # Write back if changes were made
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def find_files_with_deprecated_imports():
    """Find all files with any form of deprecated imports."""
    files_with_imports = []

    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'netra_backend.app.core.managers.unified_configuration_manager' in content:
                            files_with_imports.append(file_path)
                except Exception:
                    pass

    return files_with_imports


def main():
    """Main execution function."""
    print("Comprehensive SSOT Configuration Import Fix - Issue #757")
    print("=" * 60)

    # Find all files with deprecated imports
    files_to_fix = find_files_with_deprecated_imports()

    # Remove the deprecated manager file itself and our fix scripts
    files_to_fix = [f for f in files_to_fix if not f.endswith('unified_configuration_manager.py')
                    and not f.endswith('fix_config_imports.py')
                    and not f.endswith('fix_imports_simple.py')
                    and not f.endswith('fix_all_imports.py')]

    print(f"Found {len(files_to_fix)} files with deprecated imports")

    fixed_count = 0
    for file_path in files_to_fix:
        rel_path = os.path.relpath(file_path)
        print(f"Processing: {rel_path}")

        if fix_imports_in_file(file_path):
            print(f"  -> Fixed imports in {rel_path}")
            fixed_count += 1
        else:
            print(f"  -> No changes needed in {rel_path}")

    print(f"\nCompleted: Fixed imports in {fixed_count}/{len(files_to_fix)} files")

    if fixed_count > 0:
        print("\nNext steps:")
        print("1. Test critical business functionality")
        print("2. Run mission critical tests")
        print("3. Validate Golden Path functionality")


if __name__ == "__main__":
    main()