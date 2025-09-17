#!/usr/bin/env python3
"""
Bulk fix WebSocket import violations for Issue #1196 Phase 2 Batch 5
Replaces canonical_import_patterns and unified_manager imports with websocket_manager imports
"""

import os
import re
import shutil
from typing import List, Dict, Set, Tuple
from datetime import datetime

def backup_file(filepath: str) -> str:
    """Create backup of file before modification."""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    return backup_path

def fix_canonical_import_patterns(content: str) -> Tuple[str, int]:
    """Fix imports from canonical_import_patterns to websocket_manager."""
    fixes = 0

    # Pattern 1: from netra_backend.app.websocket_core.canonical_import_patterns import XYZ
    pattern1 = r'from netra_backend\.app\.websocket_core\.canonical_import_patterns import ([^\n]+)'
    def replace1(match):
        nonlocal fixes
        imports = match.group(1).strip()
        fixes += 1
        return f'from netra_backend.app.websocket_core.websocket_manager import {imports}'

    content = re.sub(pattern1, replace1, content)

    return content, fixes

def fix_unified_manager_imports(content: str) -> Tuple[str, int]:
    """Fix imports from unified_manager to websocket_manager."""
    fixes = 0

    # Pattern 2: from netra_backend.app.websocket_core.unified_manager import XYZ
    pattern2 = r'from netra_backend\.app\.websocket_core\.unified_manager import ([^\n]+)'
    def replace2(match):
        nonlocal fixes
        imports = match.group(1).strip()
        fixes += 1

        # Special handling for UnifiedWebSocketManager
        if 'UnifiedWebSocketManager' in imports:
            imports = imports.replace('UnifiedWebSocketManager', 'WebSocketManager')

        return f'from netra_backend.app.websocket_core.websocket_manager import {imports}'

    content = re.sub(pattern2, replace2, content)

    return content, fixes

def process_file(filepath: str) -> Dict[str, int]:
    """Process a single file and apply fixes."""
    result = {
        'canonical_fixes': 0,
        'unified_fixes': 0,
        'total_fixes': 0,
        'backup_created': False,
        'error': None
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()

        content = original_content

        # Apply canonical_import_patterns fixes
        content, canonical_fixes = fix_canonical_import_patterns(content)
        result['canonical_fixes'] = canonical_fixes

        # Apply unified_manager fixes
        content, unified_fixes = fix_unified_manager_imports(content)
        result['unified_fixes'] = unified_fixes

        result['total_fixes'] = canonical_fixes + unified_fixes

        # Only write if changes were made
        if content != original_content:
            # Create backup
            backup_path = backup_file(filepath)
            result['backup_created'] = True

            # Write fixed content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"Fixed {result['total_fixes']} imports in: {filepath}")

    except Exception as e:
        result['error'] = str(e)
        print(f"Error processing {filepath}: {e}")

    return result

def bulk_fix_websocket_imports(directories: List[str]) -> Dict[str, any]:
    """Bulk fix WebSocket imports across specified directories."""
    stats = {
        'files_processed': 0,
        'files_modified': 0,
        'files_with_errors': 0,
        'total_canonical_fixes': 0,
        'total_unified_fixes': 0,
        'total_fixes': 0,
        'backups_created': 0,
        'directories_processed': [],
        'errors': []
    }

    for directory in directories:
        if not os.path.exists(directory):
            print(f"Warning: Directory {directory} does not exist, skipping...")
            continue

        stats['directories_processed'].append(directory)
        print(f"\nProcessing directory: {directory}")

        for root, dirs, files in os.walk(directory):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache',
                                                   'node_modules', '.venv', 'venv', 'backups'}]

            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    stats['files_processed'] += 1

                    result = process_file(filepath)

                    if result['error']:
                        stats['files_with_errors'] += 1
                        stats['errors'].append(f"{filepath}: {result['error']}")

                    if result['total_fixes'] > 0:
                        stats['files_modified'] += 1
                        stats['total_canonical_fixes'] += result['canonical_fixes']
                        stats['total_unified_fixes'] += result['unified_fixes']
                        stats['total_fixes'] += result['total_fixes']

                    if result['backup_created']:
                        stats['backups_created'] += 1

    return stats

def print_summary(stats: Dict[str, any]):
    """Print summary of bulk fix operation."""
    print("\n" + "="*60)
    print("BULK WEBSOCKET IMPORT FIX SUMMARY")
    print("="*60)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files modified: {stats['files_modified']}")
    print(f"Files with errors: {stats['files_with_errors']}")
    print(f"Backups created: {stats['backups_created']}")
    print()
    print("FIXES APPLIED:")
    print(f"  canonical_import_patterns fixes: {stats['total_canonical_fixes']}")
    print(f"  unified_manager fixes: {stats['total_unified_fixes']}")
    print(f"  Total fixes: {stats['total_fixes']}")
    print()
    print(f"Directories processed: {len(stats['directories_processed'])}")
    for directory in stats['directories_processed']:
        print(f"  - {directory}")

    if stats['errors']:
        print(f"\nERRORS ({len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"  - {error}")

def main():
    """Main execution function."""
    print("WebSocket Import Bulk Fix Tool - Issue #1196 Phase 2 Batch 5")
    print("="*60)

    # Define target directories for bulk processing
    # Focus on high-volume directories first
    target_directories = [
        './netra_backend/tests',
        './tests',
        './scripts',
        './netra_backend/app',
        './test_framework',
        './auth_service/tests'
    ]

    print("Target directories:")
    for directory in target_directories:
        print(f"  - {directory}")
    print()

    # Perform bulk fixes
    stats = bulk_fix_websocket_imports(target_directories)

    # Print summary
    print_summary(stats)

    # Run basic validation
    print("\n" + "="*60)
    print("BASIC VALIDATION")
    print("="*60)

    try:
        # Test import
        print("Testing import validation...")
        result = os.system('python -c "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager; print(\'Import test successful\')"')
        if result == 0:
            print("✅ Basic import validation passed")
        else:
            print("❌ Basic import validation failed")
    except Exception as e:
        print(f"❌ Import validation error: {e}")

if __name__ == '__main__':
    main()