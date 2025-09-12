#!/usr/bin/env python3
"""
ClickHouse SSOT Compliance Verification Script

Ensures that ClickHouse implementation follows SSOT principles and all
documentation/indexes are properly maintained.

Created: 2025-08-28
Purpose: Prevent regression of ClickHouse SSOT violations
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent


def check_deleted_files() -> Tuple[bool, List[str]]:
    """Verify that deleted SSOT violation files do not exist."""
    deleted_files = [
        "netra_backend/app/db/clickhouse_client.py",
        "netra_backend/app/db/client_clickhouse.py",
        "netra_backend/app/db/clickhouse_reliable_manager.py",
        "netra_backend/app/agents/data_sub_agent/clickhouse_client.py",
    ]
    
    existing_violations = []
    for file_path in deleted_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            existing_violations.append(str(file_path))
    
    return len(existing_violations) == 0, existing_violations


def check_canonical_exists() -> Tuple[bool, str]:
    """Verify canonical implementation exists."""
    canonical_path = PROJECT_ROOT / "netra_backend/app/db/clickhouse.py"
    
    if not canonical_path.exists():
        return False, f"Canonical implementation missing: {canonical_path}"
    
    # Check for required entry point
    with open(canonical_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "def get_clickhouse_client" not in content:
            return False, "Missing get_clickhouse_client() entry point"
        if "class ClickHouseService" not in content:
            return False, "Missing ClickHouseService class"
    
    return True, "Canonical implementation verified"


def check_documentation() -> Tuple[bool, List[str]]:
    """Verify documentation is properly maintained."""
    issues = []
    
    # Check LLM_MASTER_INDEX.md
    index_path = PROJECT_ROOT / "LLM_MASTER_INDEX.md"
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "CANONICAL CLICKHOUSE" not in content:
                issues.append("LLM_MASTER_INDEX.md missing CANONICAL CLICKHOUSE entry")
            if "clickhouse_client.py" in content and "DELETED" not in content:
                issues.append("LLM_MASTER_INDEX.md still references deleted clickhouse_client.py")
    
    # Check learnings exist
    learnings_path = PROJECT_ROOT / "SPEC/learnings/clickhouse_ssot_violation_remediation.xml"
    if not learnings_path.exists():
        issues.append(f"Missing learnings file: {learnings_path}")
    
    # Check architecture spec exists
    arch_spec_path = PROJECT_ROOT / "SPEC/clickhouse_client_architecture.xml"
    if not arch_spec_path.exists():
        issues.append(f"Missing architecture spec: {arch_spec_path}")
    
    return len(issues) == 0, issues


def check_import_patterns() -> Tuple[bool, List[str]]:
    """Check for old import patterns that violate SSOT."""
    violations = []
    
    # Patterns to detect
    bad_patterns = [
        r"from.*clickhouse_client\s+import",
        r"from.*client_clickhouse\s+import",
        r"from.*clickhouse_reliable_manager\s+import",
        r"import.*clickhouse_client",
        r"import.*client_clickhouse",
    ]
    
    # Exclude test files and this script
    for py_file in PROJECT_ROOT.rglob("*.py"):
        # Skip test files, migrations, and this script
        if ("test" in str(py_file) or 
            "migration" in str(py_file) or 
            py_file.name == "verify_clickhouse_ssot.py"):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in bad_patterns:
                    if re.search(pattern, content):
                        violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: {pattern}")
        except Exception:
            pass  # Skip files we can't read
    
    return len(violations) == 0, violations


def main():
    """Run all compliance checks."""
    # Set UTF-8 encoding for Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        
    print("=" * 70)
    print("ClickHouse SSOT Compliance Verification")
    print("=" * 70)
    
    all_passed = True
    
    # Check 1: Deleted files
    print("\n1. Checking deleted SSOT violation files...")
    passed, violations = check_deleted_files()
    if passed:
        print("    PASS:  All SSOT violation files properly deleted")
    else:
        print("    FAIL:  SSOT violation files still exist:")
        for file in violations:
            print(f"      - {file}")
        all_passed = False
    
    # Check 2: Canonical exists
    print("\n2. Checking canonical implementation...")
    passed, message = check_canonical_exists()
    if passed:
        print(f"    PASS:  {message}")
    else:
        print(f"    FAIL:  {message}")
        all_passed = False
    
    # Check 3: Documentation
    print("\n3. Checking documentation...")
    passed, issues = check_documentation()
    if passed:
        print("    PASS:  Documentation properly maintained")
    else:
        print("    FAIL:  Documentation issues found:")
        for issue in issues:
            print(f"      - {issue}")
        all_passed = False
    
    # Check 4: Import patterns
    print("\n4. Checking for old import patterns...")
    passed, violations = check_import_patterns()
    if passed:
        print("    PASS:  No old import patterns found")
    else:
        print(f"    WARNING: [U+FE0F]  Found {len(violations)} files with old imports:")
        for violation in violations[:5]:  # Show first 5
            print(f"      - {violation}")
        if len(violations) > 5:
            print(f"      ... and {len(violations) - 5} more")
        # This is a warning, not a failure for now
    
    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print(" PASS:  CLICKHOUSE SSOT COMPLIANCE: PASSED")
        print("\nCanonical implementation properly maintained at:")
        print("  /netra_backend/app/db/clickhouse.py")
        print("\nUsage pattern:")
        print("  from netra_backend.app.db.clickhouse import get_clickhouse_client")
        print("  async with get_clickhouse_client() as client:")
        print("      results = await client.execute('SELECT 1')")
    else:
        print(" FAIL:  CLICKHOUSE SSOT COMPLIANCE: FAILED")
        print("\nPlease address the issues above to maintain SSOT compliance.")
        sys.exit(1)
    
    print("=" * 70)


if __name__ == "__main__":
    main()