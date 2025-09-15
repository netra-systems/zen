#!/usr/bin/env python3
"""
SSOT Configuration Manager Import Fix Script - Issue #757

This script systematically updates all files from deprecated configuration imports
to canonical SSOT imports, protecting $500K+ ARR Golden Path functionality.

Business Value Justification (BVJ):
- Segment: Platform/All
- Business Goal: System Stability
- Value Impact: Fixes configuration manager duplication blocking Golden Path
- Strategic Impact: Enables Issue #667 SSOT consolidation completion
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


# Mapping from deprecated imports to canonical SSOT imports
IMPORT_MAPPINGS = {
    "UnifiedConfigurationManager": "UnifiedConfigManager",
    "ConfigurationManagerFactory": "config_manager",  # Factory becomes instance
    "ConfigurationEntry": "get_config",  # Entry access becomes get_config
    "ConfigurationSource": "get_environment",  # Source becomes environment
    "ConfigurationScope": "get_config_value",  # Scope becomes value access
    "ConfigurationStatus": "validate_config_value",  # Status becomes validation
    "ConfigurationError": "Exception",  # Use standard Exception
    "get_configuration_manager": "get_config"  # Main getter function
}

# The deprecated import pattern to find
DEPRECATED_IMPORT_PATTERN = r'from netra_backend\.app\.core\.managers\.unified_configuration_manager import \((.*?)\)'

# The canonical SSOT import
CANONICAL_IMPORT = """from netra_backend.app.core.configuration.base import (
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


def find_files_with_deprecated_imports(root_path: str) -> List[str]:
    """Find all Python files using deprecated configuration imports."""
    files_with_deprecated_imports = []

    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'from netra_backend.app.core.managers.unified_configuration_manager import' in content:
                            files_with_deprecated_imports.append(file_path)
                except Exception as e:
                    print(f"Warning: Could not read {file_path}: {e}")

    return files_with_deprecated_imports


def fix_file_imports(file_path: str) -> bool:
    """Fix deprecated imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the deprecated import block
        pattern = r'from netra_backend\.app\.core\.managers\.unified_configuration_manager import \((.*?)\)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            # Replace the entire import block with canonical SSOT import
            old_import = match.group(0)
            new_content = content.replace(old_import, CANONICAL_IMPORT)

            # Write the updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"✅ Fixed imports in: {file_path}")
            return True
        else:
            print(f"⚠️  No deprecated import pattern found in: {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False


def main():
    """Main execution function."""
    print("🔧 SSOT Configuration Manager Import Fix - Issue #757")
    print("=" * 60)

    # Get current directory
    root_path = os.getcwd()
    print(f"Scanning directory: {root_path}")

    # Find all files with deprecated imports
    files_to_fix = find_files_with_deprecated_imports(root_path)

    if not files_to_fix:
        print("✅ No files found with deprecated imports!")
        return

    print(f"\n📊 Found {len(files_to_fix)} files with deprecated imports:")
    for i, file_path in enumerate(files_to_fix, 1):
        rel_path = os.path.relpath(file_path, root_path)
        print(f"  {i:2d}. {rel_path}")

    # Ask for confirmation
    response = input(f"\n🚀 Proceed to fix {len(files_to_fix)} files? (y/N): ")
    if response.lower() != 'y':
        print("Aborted.")
        return

    # Fix each file
    print(f"\n🔧 Fixing {len(files_to_fix)} files...")
    fixed_count = 0

    for file_path in files_to_fix:
        rel_path = os.path.relpath(file_path, root_path)
        print(f"\nFixing: {rel_path}")

        if fix_file_imports(file_path):
            fixed_count += 1

    print(f"\n✅ COMPLETED: Fixed {fixed_count}/{len(files_to_fix)} files")

    if fixed_count == len(files_to_fix):
        print("🎉 All files successfully updated to canonical SSOT imports!")
        print("\n📋 Next Steps:")
        print("1. Test critical business functionality")
        print("2. Run mission critical tests")
        print("3. Validate Golden Path functionality")
        print("4. Remove deprecated unified_configuration_manager.py")
    else:
        print("⚠️  Some files could not be fixed. Please review manually.")


if __name__ == "__main__":
    main()