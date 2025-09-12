#!/usr/bin/env python3
"""
Verify that all E2E test files have been fixed for environment violations.
"""

import os
import re
from pathlib import Path

def check_file_violations(file_path: Path) -> list:
    """Check for remaining environment violations in a file."""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for direct os.environ or os.getenv usage
        if 'os.environ' in content:
            # Count occurrences
            environ_matches = re.findall(r'os\.environ', content)
            if environ_matches:
                violations.append(f"Found {len(environ_matches)} os.environ usage(s)")
        
        if 'os.getenv' in content:
            getenv_matches = re.findall(r'os\.getenv', content)
            if getenv_matches:
                violations.append(f"Found {len(getenv_matches)} os.getenv usage(s)")
        
        # Check if file has import but still uses violations
        has_get_env_import = 'from shared.isolated_environment import get_env' in content
        
        if violations and not has_get_env_import:
            violations.append("Missing get_env import")
        
        # Check for syntax errors from batch processing
        syntax_issues = re.findall(r'get_env\(\)\.set\([^)]+,\s+\)\)', content)
        if syntax_issues:
            violations.append(f"Found {len(syntax_issues)} syntax error(s) from batch processing")
    
    except Exception as e:
        violations.append(f"Error reading file: {e}")
    
    return violations

def main():
    """Check all E2E test files for violations."""
    project_root = Path(__file__).parent
    e2e_dir = project_root / "tests" / "e2e"
    
    if not e2e_dir.exists():
        print(f"E2E directory not found: {e2e_dir}")
        return
    
    # Find all Python files in E2E directory
    python_files = list(e2e_dir.rglob("*.py"))
    
    print(f"Checking {len(python_files)} Python files in E2E directory for violations...")
    
    violation_count = 0
    files_with_violations = 0
    
    for py_file in python_files:
        violations = check_file_violations(py_file)
        if violations:
            files_with_violations += 1
            print(f"\n FAIL:  {py_file.relative_to(project_root)}:")
            for violation in violations:
                print(f"   - {violation}")
                violation_count += 1
    
    if files_with_violations == 0:
        print(f"\n PASS:  All {len(python_files)} files are clean! No environment violations found.")
    else:
        print(f"\n CHART:  Summary:")
        print(f"   Files checked: {len(python_files)}")
        print(f"   Files with violations: {files_with_violations}")
        print(f"   Total violations: {violation_count}")

if __name__ == "__main__":
    main()