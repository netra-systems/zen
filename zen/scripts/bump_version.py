#!/usr/bin/env python3
"""
Version bump utility for Zen Orchestrator.
Updates version in all relevant files.

Usage:
    python scripts/bump_version.py patch  # 1.0.0 -> 1.0.1
    python scripts/bump_version.py minor  # 1.0.0 -> 1.1.0
    python scripts/bump_version.py major  # 1.0.0 -> 2.0.0
    python scripts/bump_version.py 1.2.3  # Set specific version
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse version string to tuple of integers."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(map(int, match.groups()))


def format_version(version_tuple: Tuple[int, int, int]) -> str:
    """Format version tuple to string."""
    return '.'.join(map(str, version_tuple))


def get_current_version() -> str:
    """Get current version from __init__.py."""
    init_file = Path(__file__).parent.parent / "__init__.py"
    content = init_file.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Could not find version in __init__.py")
    return match.group(1)


def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type."""
    if re.match(r'^\d+\.\d+\.\d+$', bump_type):
        # Specific version provided
        return bump_type
    
    major, minor, patch = parse_version(current)
    
    if bump_type == 'major':
        return format_version((major + 1, 0, 0))
    elif bump_type == 'minor':
        return format_version((major, minor + 1, 0))
    elif bump_type == 'patch':
        return format_version((major, minor, patch + 1))
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_file(file_path: Path, old_version: str, new_version: str, patterns: list):
    """Update version in a file using specified patterns."""
    if not file_path.exists():
        print(f"  ⚠️  {file_path} does not exist, skipping...")
        return
    
    content = file_path.read_text()
    original_content = content
    
    for pattern in patterns:
        old_pattern = pattern.format(version=old_version)
        new_pattern = pattern.format(version=new_version)
        content = content.replace(old_pattern, new_pattern)
    
    if content != original_content:
        file_path.write_text(content)
        print(f"  ✅ Updated {file_path}")
    else:
        print(f"  ℹ️  No changes in {file_path}")


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    
    bump_type = sys.argv[1]
    
    # Get current version
    try:
        current = get_current_version()
        print(f"Current version: {current}")
    except Exception as e:
        print(f"Error getting current version: {e}")
        sys.exit(1)
    
    # Calculate new version
    try:
        new = bump_version(current, bump_type)
        print(f"New version: {new}")
    except Exception as e:
        print(f"Error calculating new version: {e}")
        sys.exit(1)
    
    # Update files
    base_path = Path(__file__).parent.parent
    
    files_to_update = [
        (
            base_path / "__init__.py",
            ['__version__ = "{version}"']
        ),
        (
            base_path / "setup.py",
            ['version="{version}"']
        ),
        (
            base_path / "pyproject.toml",
            ['version = "{version}"']
        ),
    ]
    
    print("\nUpdating files:")
    for file_path, patterns in files_to_update:
        update_file(file_path, current, new, patterns)
    
    print(f"\n✨ Version bumped from {current} to {new}")
    print("\nNext steps:")
    print(f"  1. Update CHANGELOG.md with changes for v{new}")
    print(f"  2. Commit: git commit -am 'Bump version to {new}'")
    print(f"  3. Tag: git tag -a v{new} -m 'Release version {new}'")
    print(f"  4. Push: git push origin main --tags")
    print(f"  5. Build: python -m build")
    print(f"  6. Upload: python -m twine upload dist/*")


if __name__ == "__main__":
    main()