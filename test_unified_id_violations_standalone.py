#!/usr/bin/env python3
"""
Standalone test to validate UnifiedIDManager violations are detected.

This script runs independently to prove that the violation detection logic works
without pytest framework complications.

Purpose: Validate that Issue #89 test plan correctly detects UUID.uuid4() violations.
"""

import os
import re
import uuid
from pathlib import Path
from typing import List, Tuple

def scan_file_for_uuid4_violations(file_path: Path) -> List[Tuple[str, int, str]]:
    """
    Scan a Python file for direct uuid.uuid4() usage.
    
    Args:
        file_path: Path to Python file to scan
        
    Returns:
        List of tuples: (file_path, line_number, line_content)
    """
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Look for direct uuid.uuid4() calls
                if 'uuid.uuid4()' in line:
                    violations.append((str(file_path), line_num, line.strip()))
        
    except Exception as e:
        # Continue scanning even if one file fails
        print(f"Warning: Could not scan {file_path}: {e}")
    
    return violations

def test_direct_uuid4_violations_in_auth_service():
    """
    Test that detects direct UUID.uuid4() violations in auth service.
    
    This test MUST FAIL initially proving violations exist.
    """
    print("🔍 Scanning auth service for UUID.uuid4() violations...")
    
    auth_service_root = Path("C:/GitHub/netra-apex/auth_service")
    if not auth_service_root.exists():
        print(f"❌ Auth service directory not found: {auth_service_root}")
        return False
    
    all_violations = []
    
    # Comprehensive scan of entire auth_service directory
    for py_file in auth_service_root.rglob("*.py"):
        # Skip __pycache__ directories
        if "__pycache__" in str(py_file):
            continue
        
        violations = scan_file_for_uuid4_violations(py_file)
        all_violations.extend(violations)
    
    print(f"📊 VIOLATION DETECTION RESULTS:")
    print(f"   Total files scanned: {len(list(auth_service_root.rglob('*.py')))}")
    print(f"   Violations found: {len(all_violations)}")
    
    if all_violations:
        print(f"\n🚨 VIOLATIONS DETECTED (showing first 20):")
        for i, (file_path, line_num, line_content) in enumerate(all_violations[:20]):
            rel_path = str(Path(file_path).relative_to(Path("C:/GitHub/netra-apex")))
            print(f"   {i+1:2d}. {rel_path}:{line_num} - {line_content}")
        
        if len(all_violations) > 20:
            print(f"   ... and {len(all_violations) - 20} more violations")
        
        print(f"\n✅ TEST VALIDATION: SUCCESSFUL - Violations detected as expected")
        print(f"   The test plan correctly identifies {len(all_violations)} UUID.uuid4() violations")
        print(f"   These violations prove that UnifiedIDManager is not being used consistently")
        
        return True
    else:
        print(f"\n❌ TEST VALIDATION: FAILED - No violations found")
        print(f"   Either all violations have been fixed (unexpected) or detection logic is broken")
        return False

def test_specific_known_violations():
    """
    Test specific violations that should be found based on audit results.
    """
    print(f"\n🎯 Testing specific known violation locations...")
    
    # Known violation locations from audit
    known_violations = [
        ("auth_service/auth_core/oauth/oauth_handler.py", [65, 161, 162]),
        ("auth_service/services/token_refresh_service.py", [84]),
        ("auth_service/services/session_service.py", [77]), 
        ("auth_service/services/user_service.py", [88]),
    ]
    
    violations_found = 0
    violations_expected = sum(len(lines) for _, lines in known_violations)
    
    for file_path, expected_lines in known_violations:
        full_path = Path("C:/GitHub/netra-apex") / file_path
        
        if not full_path.exists():
            print(f"   ⚠️  File not found: {file_path}")
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num in expected_lines:
                if line_num <= len(lines):
                    line_content = lines[line_num - 1].strip()
                    if 'uuid.uuid4()' in line_content:
                        violations_found += 1
                        print(f"   ✓ Found expected violation: {file_path}:{line_num}")
                    else:
                        print(f"   ❌ Expected violation not found: {file_path}:{line_num}")
                else:
                    print(f"   ❌ Line number out of range: {file_path}:{line_num}")
                    
        except Exception as e:
            print(f"   ❌ Error reading {file_path}: {e}")
    
    print(f"\n📋 SPECIFIC VIOLATION RESULTS:")
    print(f"   Expected violations: {violations_expected}")
    print(f"   Found violations: {violations_found}")
    
    if violations_found > 0:
        print(f"   ✅ Detection successful - Found {violations_found} specific violations")
        return True
    else:
        print(f"   ❌ Detection failed - No specific violations found")
        return False

def test_unified_id_manager_correct_usage():
    """
    Test that UnifiedIDManager works correctly (positive test).
    """
    print(f"\n✨ Testing correct UnifiedIDManager usage...")
    
    try:
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType, get_id_manager
        
        manager = get_id_manager()
        manager.clear_all()  # Clean slate for testing
        
        # Test basic ID generation
        user_id = manager.generate_id(IDType.USER)
        session_id = manager.generate_id(IDType.SESSION)
        
        print(f"   Generated user ID: {user_id}")
        print(f"   Generated session ID: {session_id}")
        
        # Verify IDs are different and valid format
        if user_id != session_id:
            print(f"   ✓ IDs are unique")
        else:
            print(f"   ❌ IDs are not unique")
            return False
        
        if manager.is_valid_id(user_id, IDType.USER):
            print(f"   ✓ User ID is valid")
        else:
            print(f"   ❌ User ID is invalid")
            return False
        
        if manager.is_valid_id(session_id, IDType.SESSION):
            print(f"   ✓ Session ID is valid")
        else:
            print(f"   ❌ Session ID is invalid")
            return False
        
        # Test structured format vs raw UUID
        raw_uuid = str(uuid.uuid4())
        print(f"   Raw UUID example: {raw_uuid}")
        
        # Raw UUIDs should not be tracked by manager
        if not manager.is_valid_id(raw_uuid):
            print(f"   ✓ Raw UUID correctly not tracked by manager")
        else:
            print(f"   ❌ Raw UUID incorrectly tracked by manager")
            return False
        
        print(f"   ✅ UnifiedIDManager works correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing UnifiedIDManager: {e}")
        return False

def main():
    """Run all validation tests."""
    print("=" * 80)
    print("UNIFIED ID MANAGER VIOLATION TEST VALIDATION")
    print("=" * 80)
    print("Purpose: Validate that Issue #89 test plan correctly detects violations")
    print("")
    
    # Run all tests
    test_results = []
    
    test_results.append(("Direct UUID4 Violations", test_direct_uuid4_violations_in_auth_service()))
    test_results.append(("Specific Known Violations", test_specific_known_violations()))
    test_results.append(("Correct UnifiedIDManager Usage", test_unified_id_manager_correct_usage()))
    
    print("\n" + "=" * 80)
    print("FINAL VALIDATION RESULTS")
    print("=" * 80)
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Issue #89 test plan validation SUCCESSFUL")
        print("   The failing tests correctly detect UnifiedIDManager violations")
        print("   Tests are ready to prove violations exist and guide remediation")
    else:
        print("⚠️  SOME TESTS FAILED - Issue #89 test plan needs adjustment")
        print("   Review failed tests and improve violation detection logic")
    
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)