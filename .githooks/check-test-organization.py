#!/usr/bin/env python3
"""
Test organization checker for pre-commit hook.
Prevents conftest.py violations and enforces test naming standards.
"""

import subprocess
import sys
from pathlib import Path

def check_conftest_violations() -> bool:
    """Check for conftest.py placement violations."""
    script_path = Path(__file__).parent.parent / "scripts" / "check_conftest_violations.py"
    
    if not script_path.exists():
        print(" WARNING: [U+FE0F]  Warning: check_conftest_violations.py not found")
        return True
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(result.stdout)
        return False
    
    return True

def check_test_naming() -> bool:
    """Check for test file naming violations."""
    root_dir = Path(__file__).parent.parent
    
    violations = []
    
    # Find files ending with _test.py (should be test_*.py)
    for file in root_dir.rglob("*_test.py"):
        # Skip virtual environments and archives
        if any(part in file.parts for part in [".venv", "venv", "__pycache__", "archive"]):
            continue
        violations.append(file.relative_to(root_dir))
    
    if violations:
        print("VIOLATION: Test file naming violations found:")
        print("   Files ending with '_test.py' should be renamed to 'test_*.py':")
        for file in violations:
            suggested = file.parent / f"test_{file.stem[:-5]}.py"
            print(f"   - {file} -> {suggested}")
        return False
    
    return True

def main():
    """Main test organization checker."""
    print("\nChecking test organization compliance...")
    
    all_passed = True
    
    # Check conftest.py placement
    if not check_conftest_violations():
        all_passed = False
    
    # Check test naming conventions
    if not check_test_naming():
        all_passed = False
    
    if all_passed:
        print("SUCCESS: Test organization checks passed!")
        return 0
    else:
        print("\nVIOLATION: Test organization violations detected!")
        print("   Please fix the violations before committing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())