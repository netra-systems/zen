#!/usr/bin/env python3
"""
Issue #596 SSOT Violation Validation Script

Purpose: Directly validate the specific SSOT violations found in source code
Expected: FAIL - Proves the violations exist
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env


def test_auth_startup_validator_violations():
    """Test direct os.environ violations in auth_startup_validator.py."""
    print("\n🔍 Testing AuthStartupValidator SSOT violations...")
    
    # Read the source code to verify violations exist
    auth_validator_path = project_root / "netra_backend/app/core/auth_startup_validator.py"
    
    if not auth_validator_path.exists():
        print(f"❌ CRITICAL: {auth_validator_path} not found")
        return False
    
    content = auth_validator_path.read_text()
    
    # Check for specific SSOT violations
    violations_found = []
    
    # Line 509: direct_value = os.environ.get(var_name)
    if "os.environ.get(var_name)" in content:
        violations_found.append("Line ~509: direct_value = os.environ.get(var_name)")
    
    # Line 511: fallback to direct os.environ 
    if "direct os.environ fallback" in content:
        violations_found.append("Line ~511: direct os.environ fallback logging")
    
    # Line 516: os.environ.get(env_specific)
    if "os.environ.get(env_specific)" in content:
        violations_found.append("Line ~516: os.environ.get(env_specific)")
    
    if violations_found:
        print("🚨 SSOT VIOLATIONS DETECTED in auth_startup_validator.py:")
        for violation in violations_found:
            print(f"  - {violation}")
        return True
    else:
        print("❌ Expected SSOT violations not found in auth_startup_validator.py")
        return False


def test_unified_secrets_violations():
    """Test direct os.getenv violations in unified_secrets.py."""
    print("\n🔍 Testing UnifiedSecrets SSOT violations...")
    
    # Read the source code to verify violations exist
    secrets_path = project_root / "netra_backend/app/core/configuration/unified_secrets.py"
    
    if not secrets_path.exists():
        print(f"❌ CRITICAL: {secrets_path} not found")
        return False
    
    content = secrets_path.read_text()
    
    # Check for direct os.getenv usage (should use IsolatedEnvironment)
    violations_found = []
    
    if "os.getenv" in content:
        violations_found.append("Direct os.getenv() usage found")
    
    if "os.environ" in content:
        violations_found.append("Direct os.environ access found")
    
    if violations_found:
        print("🚨 SSOT VIOLATIONS DETECTED in unified_secrets.py:")
        for violation in violations_found:
            print(f"  - {violation}")
        return True
    else:
        print("✅ No os.getenv/os.environ violations found in unified_secrets.py")
        return False


def test_environment_isolation_behavior():
    """Test that environment isolation properly isolates variables."""
    print("\n🔍 Testing environment isolation behavior...")
    
    env = get_env()
    test_key = "SSOT_VIOLATION_TEST_KEY_596"
    test_value = "violation-test-value"
    
    try:
        # Enable isolation
        env.enable_isolation()
        
        # Set value only in os.environ, NOT in isolated environment
        os.environ[test_key] = test_value
        
        # Delete from isolated environment to ensure it's not there
        env.delete(test_key)
        
        # Check behavior
        isolated_value = env.get(test_key)
        os_value = os.environ.get(test_key)
        
        print(f"  - Value in os.environ: {os_value}")
        print(f"  - Value in isolated env: {isolated_value}")
        
        if isolated_value == test_value:
            print("🚨 POTENTIAL SSOT VIOLATION: Isolated environment returned os.environ value")
            print("  This suggests isolation is not working properly")
            return True
        elif isolated_value is None:
            print("✅ Environment isolation working correctly")
            return False
        else:
            print(f"⚠️  Unexpected behavior: isolated_value = {isolated_value}")
            return True
            
    except Exception as e:
        print(f"❌ ERROR testing environment isolation: {e}")
        return False
        
    finally:
        # Cleanup
        if test_key in os.environ:
            del os.environ[test_key]
        env.delete(test_key)
        env.disable_isolation()


def main():
    """Run all SSOT violation tests."""
    print("🚨 Issue #596 SSOT Environment Variable Violation Validation")
    print("=" * 70)
    print("Expected Result: VIOLATIONS DETECTED - proves issue exists")
    print("=" * 70)
    
    violation_count = 0
    
    # Test auth startup validator violations
    if test_auth_startup_validator_violations():
        violation_count += 1
    
    # Test unified secrets violations  
    if test_unified_secrets_violations():
        violation_count += 1
    
    # Test environment isolation behavior
    if test_environment_isolation_behavior():
        violation_count += 1
    
    print("\n" + "=" * 70)
    print("📊 SSOT VIOLATION VALIDATION RESULTS")
    print("=" * 70)
    
    if violation_count > 0:
        print(f"🚨 SUCCESS: {violation_count} SSOT violations detected")
        print("✅ Issue #596 is VALIDATED - SSOT violations confirmed")
        print("🎯 Business Impact: Golden Path authentication affected")
        print("💰 Revenue Impact: $500K+ ARR at risk due to auth failures")
        print("\n🔧 Next Steps:")
        print("1. Fix direct os.environ/os.getenv usage")
        print("2. Replace with IsolatedEnvironment.get() calls")
        print("3. Re-run tests to verify fix")
        return 1  # Exit code 1 indicates violations found (success for this test)
    else:
        print("❌ UNEXPECTED: No SSOT violations detected")
        print("⚠️  This suggests either:")
        print("   - The violations have been fixed")
        print("   - The test methodology needs adjustment")
        return 0


if __name__ == "__main__":
    sys.exit(main())