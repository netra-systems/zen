#!/usr/bin/env python3
"""
Pre-commit hook script to prevent numbered file naming patterns.

This script prevents files with non-semantic numbered suffixes like:
- _1.py, _2.py, _3.py (arbitrary splits)
- _11_20.py (range patterns)
- _core_1.py, _utilities_2.py (numbered variants)

Usage:
    python scripts/prevent_numbered_files.py [files...]
    
Returns:
    0 if all files pass validation
    1 if any files have problematic naming patterns
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate bad naming conventions
BAD_PATTERNS = [
    # Direct number suffixes
    r'_\d+\.py$',  # _1.py, _2.py, etc.
    r'_\d+_\d+\.py$',  # _11_20.py, etc.
    # Numbered variants of common suffixes
    r'_core_\d+\.py$',  # _core_1.py, _core_2.py
    r'_utilities_\d+\.py$',  # _utilities_1.py, _utilities_2.py
    r'_helpers_\d+\.py$',  # _helpers_1.py
    r'_fixtures_\d+\.py$',  # _fixtures_1.py
    r'_services_\d+\.py$',  # _services_1.py
    r'_managers_\d+\.py$',  # _managers_1.py
    r'_batch_\d+\.py$',  # _batch_1.py
    # Other problematic patterns
    r'_enhanced\.py$',  # _enhanced.py
    r'_fixed\.py$',  # _fixed.py
    r'_backup\.py$',  # _backup.py
    r'_old\.py$',  # _old.py
    r'_new\.py$',  # _new.py
    r'_temp\.py$',  # _temp.py
    r'_tmp\.py$',  # _tmp.py
]

# Allowed exceptions (e.g., version numbers in library code)
ALLOWED_PATTERNS = [
    r'v\d+',  # Version numbers like v1, v2
    r'api/v\d+',  # API versioning
    r'_v\d+\.py$',  # Version suffixes like _v1.py
]


def check_file_naming(filepath: Path) -> Tuple[bool, str]:
    """
    Check if a file has a problematic naming pattern.
    
    Args:
        filepath: Path to the file to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    filename = filepath.name
    
    # Skip non-Python files
    if not filename.endswith('.py'):
        return True, ""
    
    # Check if file is in an allowed location (e.g., venv, node_modules)
    path_str = str(filepath).replace('\\', '/')
    if any(part in path_str for part in ['/venv/', '/.venv/', '/node_modules/', '__pycache__', '/site-packages/']):
        return True, ""
    
    # Check for allowed patterns first
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, path_str):
            return True, ""
    
    # Check for bad patterns
    for pattern in BAD_PATTERNS:
        if re.search(pattern, filename):
            return False, f"File '{filepath}' uses non-semantic numbered naming pattern"
    
    return True, ""


def suggest_better_name(filepath: Path) -> str:
    """
    Suggest a better name for a file with bad naming.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Suggested better name
    """
    filename = filepath.name
    
    # Remove number suffixes
    if re.search(r'_\d+\.py$', filename):
        base = re.sub(r'_\d+\.py$', '.py', filename)
        return f"Consider using a descriptive name instead of '{filename}'. Base name would be '{base}'"
    
    # For _core_1, _utilities_2, etc.
    if re.search(r'_(core|utilities|helpers|fixtures|services|managers)_\d+\.py$', filename):
        return f"Split '{filename}' by functionality, not arbitrary numbers. Use names like 'test_user_auth_{{}}.py' or 'test_data_validation_{{}}.py'"
    
    # For batch files
    if re.search(r'_batch_\d+\.py$', filename):
        return f"Replace '{filename}' with semantic names describing the test groups, e.g., 'test_persistence_and_recovery.py'"
    
    return f"Use a descriptive name for '{filename}' that explains its purpose"


def main(files: List[str]) -> int:
    """
    Main function to check files.
    
    Args:
        files: List of file paths to check
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if not files:
        # If no files specified, check all Python files
        files = [str(p) for p in Path('.').rglob('*.py')]
    
    violations = []
    
    for file_str in files:
        filepath = Path(file_str)
        if not filepath.exists():
            continue
            
        is_valid, error_msg = check_file_naming(filepath)
        if not is_valid:
            violations.append((filepath, error_msg))
    
    if violations:
        print("ERROR: Found files with non-semantic numbered naming patterns:\n")
        for filepath, error_msg in violations:
            print(f"  - {error_msg}")
            print(f"    {suggest_better_name(filepath)}\n")
        
        print("\nFiles should be named based on their content and purpose, not arbitrary numbers.")
        print("Examples of good naming:")
        print("  [OK] test_user_authentication.py")
        print("  [OK] test_data_validation_fields.py")
        print("  [OK] test_message_persistence.py")
        print("\nExamples of bad naming:")
        print("  [BAD] test_integration_batch_1.py")
        print("  [BAD] test_core_2.py")
        print("  [BAD] test_utilities_3.py")
        
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))