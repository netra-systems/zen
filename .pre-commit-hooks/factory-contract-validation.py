#!/usr/bin/env python3
"""
Pre-commit hook for factory contract validation.

This hook runs before commits to validate factory interfaces and prevent
parameter mismatches like the websocket_client_id vs websocket_connection_id issue.

Exit codes:
    0: All validations passed
    1: Contract violations found
    2: Critical errors (missing dependencies, etc.)
"""

import sys
import subprocess
import os
from pathlib import Path
from typing import List, Tuple


def run_validation_script() -> Tuple[int, str, str]:
    """Run the factory contract validation script."""
    
    # Find the validation script
    repo_root = Path(__file__).parent.parent
    validation_script = repo_root / "scripts" / "validate_factory_contracts.py"
    
    if not validation_script.exists():
        return 2, "", f"Validation script not found: {validation_script}"
    
    try:
        # Run validation with specific tests focused on parameter mismatches
        result = subprocess.run([
            sys.executable,
            str(validation_script),
            "--specific-tests",
            "--validate-user-context"
        ], capture_output=True, text=True, timeout=60)
        
        return result.returncode, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        return 2, "", "Validation script timed out after 60 seconds"
    except Exception as e:
        return 2, "", f"Failed to run validation script: {e}"


def check_modified_factory_files(files: List[str]) -> List[str]:
    """Check if any modified files are factory-related."""
    
    factory_patterns = [
        "factory",
        "user_execution_context",
        "supervisor", 
        "websocket_manager",
        "__init__.py"  # Constructor changes
    ]
    
    factory_files = []
    for file in files:
        file_lower = file.lower()
        if any(pattern in file_lower for pattern in factory_patterns):
            if file.endswith('.py'):
                factory_files.append(file)
    
    return factory_files


def get_staged_files() -> List[str]:
    """Get list of staged files for commit."""
    try:
        result = subprocess.run([
            "git", "diff", "--cached", "--name-only"
        ], capture_output=True, text=True, check=True)
        
        return [line.strip() for line in result.stdout.split('\n') if line.strip()]
    except subprocess.CalledProcessError:
        return []


def main():
    """Main pre-commit hook execution."""
    
    print(" SEARCH:  Factory Contract Validation Pre-commit Hook")
    print("=" * 50)
    
    # Check if this is a factory-related change
    staged_files = get_staged_files()
    factory_files = check_modified_factory_files(staged_files)
    
    if not factory_files:
        print(" PASS:  No factory-related files modified, skipping validation")
        return 0
    
    print(f"[U+1F3ED] Factory-related files detected: {len(factory_files)}")
    for file in factory_files[:5]:  # Show first 5
        print(f"   - {file}")
    if len(factory_files) > 5:
        print(f"   ... and {len(factory_files) - 5} more")
    
    print("\n[U+1F9EA] Running factory contract validation...")
    
    # Run validation
    exit_code, stdout, stderr = run_validation_script()
    
    if stdout:
        print(stdout)
    if stderr:
        print("STDERR:", stderr, file=sys.stderr)
    
    if exit_code == 0:
        print("\n PASS:  Factory contract validation PASSED")
        print(" CELEBRATION:  All factory interfaces are valid - commit allowed!")
        return 0
    elif exit_code == 1:
        print("\n FAIL:  Factory contract validation FAILED")
        print(" ALERT:  Contract violations found - commit blocked!")
        print("\nTo fix:")
        print("1. Review the validation errors above")
        print("2. Fix parameter name mismatches")
        print("3. Ensure factory interfaces match contracts") 
        print("4. Run: python scripts/validate_factory_contracts.py --specific-tests")
        print("5. Commit again after fixing issues")
        return 1
    else:
        print("\n WARNING: [U+FE0F]  Factory contract validation encountered errors")
        print("[U+1F527] Check validation script configuration")
        return 2


if __name__ == "__main__":
    sys.exit(main())