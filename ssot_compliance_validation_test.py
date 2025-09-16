#!/usr/bin/env python3
"""
SSOT Compliance Validation Test for Infrastructure Resilience
Tests that new infrastructure components follow SSOT patterns and don't introduce violations.
"""

import sys
import os
import ast
from pathlib import Path
from typing import List, Dict, Set

def check_absolute_imports(file_path: Path) -> Dict[str, List[str]]:
    """Check that file uses only absolute imports (no relative imports)."""
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level > 0:  # Relative import detected
                    line_num = getattr(node, 'lineno', '?')
                    violations.append(f"Line {line_num}: Relative import detected: {node.module}")

        return {"violations": violations, "status": "pass" if not violations else "fail"}

    except Exception as e:
        return {"violations": [f"Error analyzing file: {e}"], "status": "error"}

def check_ssot_patterns(file_path: Path) -> Dict[str, List[str]]:
    """Check for SSOT compliance patterns."""
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for direct os.environ usage (should use IsolatedEnvironment)
        if "os.environ" in content and "import os" in content:
            violations.append("Direct os.environ access detected - should use IsolatedEnvironment")

        # Check for proper configuration usage
        if "from netra_backend.app.core.config import get_config" in content:
            # This is good - using SSOT configuration
            pass
        elif "get_config" in content:
            violations.append("get_config usage without proper import")

        # Check for proper logging setup
        if "logging.getLogger(__name__)" in content:
            # This is good - proper logging setup
            pass
        elif "logger" in content and "logging" in content:
            violations.append("Improper logging setup - should use logging.getLogger(__name__)")

        return {"violations": violations, "status": "pass" if not violations else "fail"}

    except Exception as e:
        return {"violations": [f"Error analyzing SSOT patterns: {e}"], "status": "error"}

def check_business_value_justification(file_path: Path) -> Dict[str, List[str]]:
    """Check that module includes Business Value Justification (BVJ)."""
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for BVJ in docstring
        if "Business Value Justification" in content or "BVJ" in content:
            # Check for required BVJ components
            if "Segment:" not in content:
                violations.append("BVJ missing Segment specification")
            if "Business Goal:" not in content:
                violations.append("BVJ missing Business Goal specification")
            if "Value Impact:" not in content:
                violations.append("BVJ missing Value Impact specification")
        else:
            violations.append("Missing Business Value Justification (BVJ) in module docstring")

        return {"violations": violations, "status": "pass" if not violations else "fail"}

    except Exception as e:
        return {"violations": [f"Error checking BVJ: {e}"], "status": "error"}

def test_infrastructure_resilience_ssot():
    """Test infrastructure resilience components for SSOT compliance."""
    print("🔍 Testing Infrastructure Resilience SSOT Compliance")
    print("-" * 60)

    # Files to check
    infrastructure_files = [
        Path("netra_backend/app/services/infrastructure_resilience.py"),
        Path("netra_backend/app/resilience/circuit_breaker.py"),
        Path("netra_backend/app/core/database_timeout_config.py"),
    ]

    total_files = 0
    passing_files = 0
    all_violations = []

    for file_path in infrastructure_files:
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        total_files += 1
        print(f"\n📁 Checking: {file_path}")

        # Check absolute imports
        import_result = check_absolute_imports(file_path)
        print(f"   📦 Absolute Imports: {'✅ PASS' if import_result['status'] == 'pass' else '❌ FAIL'}")
        if import_result['violations']:
            for violation in import_result['violations']:
                print(f"      - {violation}")
                all_violations.append(f"{file_path}: {violation}")

        # Check SSOT patterns
        ssot_result = check_ssot_patterns(file_path)
        print(f"   🏗️  SSOT Patterns: {'✅ PASS' if ssot_result['status'] == 'pass' else '❌ FAIL'}")
        if ssot_result['violations']:
            for violation in ssot_result['violations']:
                print(f"      - {violation}")
                all_violations.append(f"{file_path}: {violation}")

        # Check BVJ
        bvj_result = check_business_value_justification(file_path)
        print(f"   💼 Business Value: {'✅ PASS' if bvj_result['status'] == 'pass' else '❌ FAIL'}")
        if bvj_result['violations']:
            for violation in bvj_result['violations']:
                print(f"      - {violation}")
                all_violations.append(f"{file_path}: {violation}")

        # Count as passing if all checks pass
        if (import_result['status'] == 'pass' and
            ssot_result['status'] == 'pass' and
            bvj_result['status'] == 'pass'):
            passing_files += 1

    return total_files, passing_files, all_violations

def test_health_endpoints_ssot():
    """Test health endpoints for SSOT compliance."""
    print("\n🔍 Testing Health Endpoints SSOT Compliance")
    print("-" * 60)

    health_file = Path("netra_backend/app/routes/health.py")

    if not health_file.exists():
        print("⚠️  Health endpoints file not found")
        return 0, 0, ["Health endpoints file not found"]

    total_checks = 3
    passing_checks = 0
    violations = []

    print(f"📁 Checking: {health_file}")

    # Check absolute imports
    import_result = check_absolute_imports(health_file)
    print(f"   📦 Absolute Imports: {'✅ PASS' if import_result['status'] == 'pass' else '❌ FAIL'}")
    if import_result['status'] == 'pass':
        passing_checks += 1
    else:
        violations.extend([f"{health_file}: {v}" for v in import_result['violations']])

    # Check SSOT patterns
    ssot_result = check_ssot_patterns(health_file)
    print(f"   🏗️  SSOT Patterns: {'✅ PASS' if ssot_result['status'] == 'pass' else '❌ FAIL'}")
    if ssot_result['status'] == 'pass':
        passing_checks += 1
    else:
        violations.extend([f"{health_file}: {v}" for v in ssot_result['violations']])

    # Check for proper error handling
    try:
        with open(health_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if "try:" in content and "except Exception" in content:
            print("   ⚠️  Error Handling: ✅ PASS")
            passing_checks += 1
        else:
            print("   ⚠️  Error Handling: ❌ FAIL - No proper exception handling")
            violations.append(f"{health_file}: Missing proper exception handling")
    except Exception as e:
        violations.append(f"{health_file}: Error checking error handling - {e}")

    return total_checks, passing_checks, violations

def main():
    """Run all SSOT compliance validation tests."""
    print("🏗️  SSOT Compliance Validation Test")
    print("=" * 70)

    total_success = 0
    total_tests = 0
    all_violations = []

    # Test infrastructure resilience SSOT compliance
    files_tested, files_passing, violations = test_infrastructure_resilience_ssot()
    total_tests += files_tested
    total_success += files_passing
    all_violations.extend(violations)

    # Test health endpoints SSOT compliance
    checks_tested, checks_passing, violations = test_health_endpoints_ssot()
    total_tests += checks_tested
    total_success += checks_passing
    all_violations.extend(violations)

    print("\n" + "=" * 70)
    print(f"📊 SSOT Compliance Results: {total_success}/{total_tests} passing")

    if all_violations:
        print(f"\n⚠️  Found {len(all_violations)} SSOT violations:")
        for violation in all_violations:
            print(f"   - {violation}")

    if total_success == total_tests and not all_violations:
        print("🎉 All SSOT compliance checks passed")
        return 0
    else:
        print("⚠️  Some SSOT compliance checks failed - Please review violations above")
        return 1

if __name__ == "__main__":
    sys.exit(main())