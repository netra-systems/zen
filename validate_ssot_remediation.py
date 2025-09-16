#!/usr/bin/env python3
"""
SSOT Remediation Validation Script
Validates the improvements made during SSOT remediation Phase 2
"""

import json
import sys
from pathlib import Path

def validate_remediation():
    """Validate SSOT remediation results"""
    print("🔍 SSOT Remediation Validation Report")
    print("=" * 50)

    # Read current compliance
    compliance_file = Path("compliance_status.json")
    if not compliance_file.exists():
        print("❌ No compliance status file found")
        return False

    with open(compliance_file) as f:
        compliance = json.load(f)

    score = compliance.get("compliance_score", 0)
    total_violations = compliance.get("total_violations", 0)

    print(f"📊 Current Compliance Score: {score:.2f}%")
    print(f"📊 Total Violations: {total_violations}")

    # Validate production systems
    categories = compliance.get("category_scores", {})
    production_score = categories.get("real_system", {}).get("score", 0)

    print(f"🏭 Production System Score: {production_score}%")

    # Check our remediation targets
    remediation_success = True

    if score < 98.0:
        print(f"❌ Compliance score {score:.2f}% below 98% target")
        remediation_success = False
    else:
        print(f"✅ Compliance score {score:.2f}% meets target")

    if production_score < 100.0:
        print(f"❌ Production score {production_score}% not 100%")
        remediation_success = False
    else:
        print(f"✅ Production systems 100% compliant (Golden Path protected)")

    if total_violations > 20:
        print(f"❌ Too many violations: {total_violations} > 20")
        remediation_success = False
    else:
        print(f"✅ Violation count {total_violations} within acceptable range")

    # Check violation types
    violations_by_type = compliance.get("violations_by_type", {})
    print("\n📋 Violation Breakdown:")
    for violation_type, count in violations_by_type.items():
        print(f"   {violation_type}: {count}")

    print("\n🎯 Remediation Assessment:")
    if remediation_success:
        print("✅ SSOT Remediation Phase 2 SUCCESSFUL")
        print("✅ All targets met, Golden Path protected")
        print("✅ Ready for production deployment")
    else:
        print("⚠️  SSOT Remediation needs additional work")
        print("⚠️  Some targets not met")

    return remediation_success

if __name__ == "__main__":
    success = validate_remediation()
    sys.exit(0 if success else 1)