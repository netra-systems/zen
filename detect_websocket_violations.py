#!/usr/bin/env python3
"""
Detect WebSocket import violations for Issue #1196 Phase 2 Batch 5
Identifies files importing from canonical_import_patterns instead of websocket_manager
"""

import os
import re
from typing import List, Dict, Set

def find_websocket_import_violations(directory: str) -> Dict[str, List[str]]:
    """Find all files with WebSocket import violations."""
    violations = {
        'canonical_import_patterns': [],
        'unified_manager': [],
        'other_violations': []
    }

    # Patterns to detect
    patterns = {
        'canonical_import_patterns': [
            r'from netra_backend\.app\.websocket_core\.canonical_import_patterns import (\w+)',
            r'from netra_backend\.app\.websocket_core\.canonical_import_patterns import \(',
        ],
        'unified_manager': [
            r'from netra_backend\.app\.websocket_core\.unified_manager import (\w+)',
        ]
    }

    total_files_scanned = 0

    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache',
                                               'node_modules', '.venv', 'venv', 'backups'}]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                total_files_scanned += 1

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for canonical_import_patterns violations
                    for pattern in patterns['canonical_import_patterns']:
                        if re.search(pattern, content):
                            violations['canonical_import_patterns'].append(filepath)
                            break

                    # Check for unified_manager violations
                    for pattern in patterns['unified_manager']:
                        if re.search(pattern, content):
                            violations['unified_manager'].append(filepath)
                            break

                except Exception as e:
                    print(f'Error reading {filepath}: {e}')

    # Remove duplicates and sort
    for key in violations:
        violations[key] = sorted(list(set(violations[key])))

    print(f"Files scanned: {total_files_scanned}")
    print(f"canonical_import_patterns violations: {len(violations['canonical_import_patterns'])}")
    print(f"unified_manager violations: {len(violations['unified_manager'])}")

    return violations

def show_violation_summary(violations: Dict[str, List[str]]):
    """Show summary of violations by directory."""
    print("\n=== VIOLATION SUMMARY ===")

    for violation_type, files in violations.items():
        if not files:
            continue

        print(f"\n{violation_type.upper()} VIOLATIONS ({len(files)} files):")

        # Group by directory for better analysis
        dir_groups = {}
        for file in files:
            dir_name = os.path.dirname(file)
            if dir_name not in dir_groups:
                dir_groups[dir_name] = []
            dir_groups[dir_name].append(os.path.basename(file))

        for directory, filenames in sorted(dir_groups.items()):
            print(f"  {directory}/: {len(filenames)} files")
            for filename in sorted(filenames)[:5]:  # Show first 5 files
                print(f"    - {filename}")
            if len(filenames) > 5:
                print(f"    ... and {len(filenames) - 5} more")

if __name__ == '__main__':
    print("Detecting WebSocket import violations for Issue #1196...")

    # Scan the entire repository
    violations = find_websocket_import_violations('.')
    show_violation_summary(violations)

    total_violations = sum(len(files) for files in violations.values())
    print(f"\nTotal violations found: {total_violations}")