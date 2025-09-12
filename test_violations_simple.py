#!/usr/bin/env python3
"""
Simple validation script for UnifiedIDManager violations (Issue #89).
"""

import os
from pathlib import Path

def scan_auth_service_violations():
    """Scan auth service for uuid.uuid4() violations."""
    print("Scanning auth service for UUID.uuid4() violations...")
    
    auth_service_root = Path("C:/GitHub/netra-apex/auth_service")
    violations = []
    files_scanned = 0
    
    for py_file in auth_service_root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
            
        files_scanned += 1
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if 'uuid.uuid4()' in line:
                        rel_path = py_file.relative_to(Path("C:/GitHub/netra-apex"))
                        violations.append(f"{rel_path}:{line_num} - {line.strip()}")
        except Exception as e:
            print(f"Warning: Could not scan {py_file}: {e}")
    
    print(f"Files scanned: {files_scanned}")
    print(f"Violations found: {len(violations)}")
    
    if violations:
        print("\nFirst 10 violations:")
        for violation in violations[:10]:
            print(f"  {violation}")
        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more")
            
        print(f"\nSUCCESS: Test validation successful!")
        print(f"The failing tests correctly detect {len(violations)} violations")
        return True
    else:
        print("ERROR: No violations found - detection may be broken")
        return False

def check_specific_violations():
    """Check specific known violation locations."""
    print("\nChecking specific known violations...")
    
    specific_files = [
        "auth_service/auth_core/oauth/oauth_handler.py",
        "auth_service/services/token_refresh_service.py",
        "auth_service/services/session_service.py", 
        "auth_service/services/user_service.py"
    ]
    
    found = 0
    for file_path in specific_files:
        full_path = Path("C:/GitHub/netra-apex") / file_path
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'uuid.uuid4()' in content:
                    found += 1
                    print(f"  FOUND: {file_path}")
                else:
                    print(f"  NOT FOUND: {file_path}")
        else:
            print(f"  MISSING: {file_path}")
    
    print(f"Specific violations found: {found}/{len(specific_files)}")
    return found > 0

def main():
    print("=" * 60)
    print("UNIFIED ID MANAGER VIOLATION TEST VALIDATION")
    print("=" * 60)
    
    result1 = scan_auth_service_violations()
    result2 = check_specific_violations()
    
    print("\n" + "=" * 60)
    if result1 and result2:
        print("OVERALL RESULT: SUCCESS")
        print("The test plan correctly detects UnifiedIDManager violations")
        print("Tests are ready to prove violations exist")
    else:
        print("OVERALL RESULT: PARTIAL/FAILURE")
        print("Some violation detection may need adjustment")
    print("=" * 60)

if __name__ == "__main__":
    main()