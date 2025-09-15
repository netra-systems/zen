#!/usr/bin/env python3
"""
Pytest Marker Validation Tool - Prevents missing marker configuration errors

This script validates that all pytest markers used in test files are properly
defined in pyproject.toml to prevent test collection failures.

Usage:
    python scripts/validate_pytest_markers.py
    python scripts/validate_pytest_markers.py --fix

Features:
- Scans all test files for @pytest.mark.* usage
- Checks if markers are defined in pyproject.toml
- Reports missing markers with file locations
- Can automatically add missing markers (with --fix flag)
- Prevents Issue #1225 type collection failures

Created: 2025-09-14 (Fix for Issue #1225)
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Set, Dict, List, Tuple


def find_project_root() -> Path:
    """Find the project root by looking for pyproject.toml"""
    current = Path.cwd()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Could not find pyproject.toml in any parent directory")


def load_existing_markers(pyproject_path: Path) -> Set[str]:
    """Load existing markers from pyproject.toml"""
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find markers section using regex since we don't want to require toml package
        markers_section = re.search(r'markers\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if not markers_section:
            return set()

        existing_markers = set()
        marker_lines = markers_section.group(1).strip().split('\n')

        for line in marker_lines:
            line = line.strip()
            if line.startswith('"') and ':' in line:
                # Extract marker name from "marker_name: description" format
                marker_name = line.split(':')[0].strip().strip('"')
                existing_markers.add(marker_name)

        return existing_markers
    except Exception as e:
        print(f"Error loading pyproject.toml: {e}")
        return set()


def find_used_markers(project_root: Path) -> Dict[str, List[Tuple[str, int]]]:
    """Find all pytest markers used in test files"""
    used_markers = {}

    # Pattern to match @pytest.mark.marker_name
    marker_pattern = re.compile(r'@pytest\.mark\.(\w+)')

    # Find all Python test files (avoid virtual environments)
    test_patterns = ["tests/**/*.py", "**/test_*.py"]
    test_files = []

    for pattern in test_patterns:
        for test_file in project_root.glob(pattern):
            # Skip virtual environment directories
            if any(part in str(test_file) for part in ['.venv', 'venv', 'site-packages']):
                continue
            test_files.append(test_file)

    for test_file in test_files:
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    matches = marker_pattern.findall(line)
                    for marker in matches:
                        if marker not in used_markers:
                            used_markers[marker] = []

                        # Store relative path for cleaner output
                        rel_path = test_file.relative_to(project_root)
                        used_markers[marker].append((str(rel_path), line_num))
        except Exception as e:
            # Silently skip files that can't be read (like binary files)
            continue

    return used_markers


def add_missing_markers(pyproject_path: Path, missing_markers: Set[str]) -> bool:
    """Add missing markers to pyproject.toml"""
    try:
        # Read the current file
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the markers section end
        # Look for the pattern where markers list ends with ]
        markers_end_pattern = re.compile(r'(\s+"[^"]+",\s*\n)(\])', re.MULTILINE)
        match = markers_end_pattern.search(content)

        if not match:
            print("Could not find markers section end in pyproject.toml")
            return False

        # Prepare new markers to add
        new_markers_lines = []
        for marker in sorted(missing_markers):
            description = generate_marker_description(marker)
            new_markers_lines.append(f'    "{marker}: {description}",')

        # Insert new markers before the closing bracket
        new_content = (
            content[:match.start(2)] +
            '\n'.join(new_markers_lines) + '\n' +
            content[match.start(2):]
        )

        # Write the updated content
        with open(pyproject_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True
    except Exception as e:
        print(f"Error updating pyproject.toml: {e}")
        return False


def generate_marker_description(marker: str) -> str:
    """Generate a descriptive text for a marker based on its name"""
    descriptions = {
        'real_time_value': 'Real-time value delivery and performance tests',
        'quality_assurance': 'Quality assurance and testing validation tests',
        'business_value': 'Business value validation tests',
        'revenue_protection': 'Revenue protection tests',
        'user_experience': 'User experience validation tests',
        'performance': 'Performance benchmarks',
        'security': 'Security validation tests',
        'integration': 'Integration tests',
        'e2e': 'End-to-end tests',
        'staging': 'Staging environment tests',
        'production': 'Production environment tests',
        'regression': 'Regression prevention tests'
    }

    # Return specific description if available, otherwise generate generic one
    return descriptions.get(marker, f'{marker.replace("_", " ").title()} tests')


def main():
    parser = argparse.ArgumentParser(description='Validate pytest markers configuration')
    parser.add_argument('--fix', action='store_true',
                       help='Automatically add missing markers to pyproject.toml')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed information about marker usage')

    args = parser.parse_args()

    try:
        # Find project root
        project_root = find_project_root()
        pyproject_path = project_root / "pyproject.toml"

        print(f"Validating pytest markers in {project_root}")
        print("=" * 70)

        # Load existing markers
        existing_markers = load_existing_markers(pyproject_path)
        print(f"Found {len(existing_markers)} existing markers in pyproject.toml")

        # Find used markers
        used_markers = find_used_markers(project_root)
        print(f"Found {len(used_markers)} unique markers used in test files")

        # Find missing markers
        missing_markers = set(used_markers.keys()) - existing_markers

        if not missing_markers:
            print("\n[SUCCESS] All used markers are properly defined!")
            return 0

        # Report missing markers
        print(f"\n[MISSING MARKERS] {len(missing_markers)} markers need to be added:")
        print("-" * 50)

        for marker in sorted(missing_markers):
            print(f"\n{marker}")
            if args.verbose:
                for file_path, line_num in used_markers[marker][:5]:  # Show first 5 uses
                    print(f"   Used in: {file_path}:{line_num}")
                if len(used_markers[marker]) > 5:
                    print(f"   ... and {len(used_markers[marker]) - 5} more files")
            else:
                print(f"   Used in {len(used_markers[marker])} file(s)")

        # Fix if requested
        if args.fix:
            print(f"\n[FIXING] Adding {len(missing_markers)} missing markers to pyproject.toml...")
            if add_missing_markers(pyproject_path, missing_markers):
                print("[SUCCESS] Successfully added missing markers!")

                # Verify the fix worked
                updated_existing = load_existing_markers(pyproject_path)
                still_missing = missing_markers - updated_existing
                if still_missing:
                    print(f"[WARNING] {len(still_missing)} markers still missing: {still_missing}")
                    return 1
                else:
                    print("[SUCCESS] Verification: All markers are now properly defined!")
                    return 0
            else:
                print("[ERROR] Failed to add missing markers")
                return 1
        else:
            print(f"\n[SOLUTION] To fix this issue, run:")
            print(f"   python {__file__} --fix")
            print(f"\n   Or manually add these markers to pyproject.toml:")
            for marker in sorted(missing_markers):
                description = generate_marker_description(marker)
                print(f'   "{marker}: {description}",')
            return 1

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())