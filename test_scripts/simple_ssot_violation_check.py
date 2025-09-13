#!/usr/bin/env python3
"""
Issue #596 SSOT Violation Detection Script
Simple check for SSOT violations without Unicode characters
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_auth_startup_validator():
    """Check for SSOT violations in auth_startup_validator.py."""
    print("\nChecking AuthStartupValidator for SSOT violations...")
    
    auth_validator_path = project_root / "netra_backend/app/core/auth_startup_validator.py"
    
    if not auth_validator_path.exists():
        print(f"ERROR: {auth_validator_path} not found")
        return False
    
    content = auth_validator_path.read_text()
    violations = []
    
    # Check for direct os.environ usage
    if "os.environ.get(" in content:
        violations.append("Direct os.environ.get() calls found")
    
    # Check for specific fallback pattern
    if "direct os.environ fallback" in content:
        violations.append("Direct os.environ fallback pattern found")
    
    if violations:
        print("SSOT VIOLATIONS DETECTED:")
        for v in violations:
            print(f"  - {v}")
        return True
    else:
        print("No direct os.environ violations found")
        return False


def check_unified_secrets():
    """Check for SSOT violations in unified_secrets.py."""
    print("\nChecking UnifiedSecrets for SSOT violations...")
    
    secrets_path = project_root / "netra_backend/app/core/configuration/unified_secrets.py"
    
    if not secrets_path.exists():
        print(f"ERROR: {secrets_path} not found")
        return False
    
    content = secrets_path.read_text()
    violations = []
    
    if "os.getenv(" in content:
        violations.append("Direct os.getenv() calls found")
    
    if "os.environ[" in content or "os.environ.get(" in content:
        violations.append("Direct os.environ access found")
    
    if violations:
        print("SSOT VIOLATIONS DETECTED:")
        for v in violations:
            print(f"  - {v}")
        return True
    else:
        print("No direct os.getenv/os.environ violations found")
        return False


def main():
    """Run SSOT violation detection."""
    print("Issue #596 SSOT Environment Variable Violation Detection")
    print("=" * 60)
    
    violation_count = 0
    
    if check_auth_startup_validator():
        violation_count += 1
    
    if check_unified_secrets():
        violation_count += 1
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    
    if violation_count > 0:
        print(f"SUCCESS: {violation_count} files with SSOT violations detected")
        print("Issue #596 is CONFIRMED - SSOT violations exist")
        print("Business Impact: Golden Path authentication affected")
        print("Revenue Impact: $500K+ ARR at risk")
        return 1
    else:
        print("No SSOT violations detected")
        return 0


if __name__ == "__main__":
    sys.exit(main())