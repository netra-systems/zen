#!/usr/bin/env python3
"""
Anti-regression hook to prevent conftest.py violations.
Ensures conftest.py files only exist at service-level directories.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# Allowed service-level conftest.py locations
ALLOWED_CONFTEST_LOCATIONS = {
    "auth_service/tests/conftest.py",
    "netra_backend/tests/conftest.py",
    "tests/conftest.py",
    "frontend/tests/conftest.py",  # Allow if frontend tests are added
}

# Directories to exclude from scanning
EXCLUDE_DIRS = {
    ".venv", "venv", "__pycache__", ".git", "node_modules",
    "build", "dist", ".pytest_cache", "archive", ".tox"
}


def find_all_conftest_files(root_dir: Path) -> List[Path]:
    """Find all conftest.py files in the project."""
    conftest_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        if "conftest.py" in filenames:
            conftest_path = Path(dirpath) / "conftest.py"
            # Convert to relative path from root
            relative_path = conftest_path.relative_to(root_dir)
            conftest_files.append(relative_path)
    
    return conftest_files


def check_conftest_violations(root_dir: Path) -> Tuple[List[Path], List[Path]]:
    """
    Check for conftest.py violations.
    Returns (allowed_files, violation_files)
    """
    all_conftest = find_all_conftest_files(root_dir)
    
    allowed = []
    violations = []
    
    for conftest_path in all_conftest:
        path_str = str(conftest_path).replace("\\", "/")
        if path_str in ALLOWED_CONFTEST_LOCATIONS:
            allowed.append(conftest_path)
        else:
            violations.append(conftest_path)
    
    return allowed, violations


def main():
    """Main entry point for the conftest violation checker."""
    # Get project root
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    
    print("Checking for conftest.py violations...")
    print(f"   Project root: {root_dir}")
    print()
    
    allowed, violations = check_conftest_violations(root_dir)
    
    # Report allowed files
    if allowed:
        print("ALLOWED conftest.py files (service-level):")
        for file_path in allowed:
            print(f"   - {file_path}")
        print()
    
    # Report violations
    if violations:
        print("VIOLATION: conftest.py files found in non-service-level directories:")
        for file_path in violations:
            print(f"   - {file_path}")
        print()
        print("Action Required:")
        print("   1. Move fixtures to appropriate service-level conftest.py")
        print("   2. Delete the violating conftest.py files")
        print("   3. Update test imports if necessary")
        print()
        print("Allowed locations:")
        for location in sorted(ALLOWED_CONFTEST_LOCATIONS):
            print(f"   - {location}")
        
        sys.exit(1)
    else:
        print("SUCCESS: No violations found! All conftest.py files are at service-level.")
        print()
        print(f"Total conftest.py files: {len(allowed)}")
        
        # Also check for potential missing service-level conftest
        for location in ALLOWED_CONFTEST_LOCATIONS:
            location_path = root_dir / location
            if not location_path.exists():
                print(f"   Note: {location} does not exist (OK if service has no tests)")
    
    return 0


if __name__ == "__main__":
    exit(main())