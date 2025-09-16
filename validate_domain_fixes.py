#!/usr/bin/env python3
"""
Domain Remediation Validation Script
Validates that Phase 1 domain fixes have been applied correctly.

This script verifies that critical configuration files have been updated
to use the correct staging domains (*.netrasystems.ai) instead of the
deprecated (*.staging.netrasystems.ai) format.
"""

import re
from pathlib import Path
from typing import List, Tuple, Dict


def check_file_for_deprecated_domains(file_path: str) -> Tuple[bool, List[str]]:
    """
    Check a file for deprecated staging domain patterns.

    Returns:
        (has_deprecated, list_of_deprecated_lines)
    """
    deprecated_patterns = [
        r'https?://[^/]*\.staging\.netrasystems\.ai',
        r'wss?://[^/]*\.staging\.netrasystems\.ai',
    ]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        deprecated_lines = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            for pattern in deprecated_patterns:
                if re.search(pattern, line):
                    deprecated_lines.append(f"Line {i}: {line.strip()}")

        return len(deprecated_lines) > 0, deprecated_lines
    except Exception as e:
        return False, [f"Error reading file: {e}"]


def check_file_for_correct_domains(file_path: str) -> Tuple[bool, List[str]]:
    """
    Check a file for correct staging domain patterns.

    Returns:
        (has_correct, list_of_correct_lines)
    """
    correct_patterns = [
        r'https://staging\.netrasystems\.ai',
        r'https://api-staging\.netrasystems\.ai',
        r'wss://api-staging\.netrasystems\.ai',
    ]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        correct_lines = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            for pattern in correct_patterns:
                if re.search(pattern, line):
                    correct_lines.append(f"Line {i}: {line.strip()}")

        return len(correct_lines) > 0, correct_lines
    except Exception as e:
        return False, [f"Error reading file: {e}"]


def validate_critical_files() -> Dict[str, Dict[str, any]]:
    """Validate the top 10 critical files that were fixed."""

    critical_files = [
        # P0 - Mission Critical
        "netra_backend/app/schemas/config.py",
        "shared/security_origins_config.py",
        "frontend/next.config.js",

        # P1 - High Priority
        "frontend/lib/unified-api-config.ts",
        "test_framework/test_config.py",
        "scripts/verify_auth_config.py",

        # SSOT Module
        "shared/constants/staging_domains.py",
    ]

    results = {}

    for file_path in critical_files:
        full_path = Path(file_path)
        if not full_path.exists():
            results[file_path] = {
                "status": "FILE_NOT_FOUND",
                "deprecated_found": False,
                "correct_found": False,
                "deprecated_lines": [],
                "correct_lines": []
            }
            continue

        has_deprecated, deprecated_lines = check_file_for_deprecated_domains(str(full_path))
        has_correct, correct_lines = check_file_for_correct_domains(str(full_path))

        # Determine status
        if has_deprecated:
            status = "NEEDS_FIX"
        elif has_correct:
            status = "FIXED"
        else:
            status = "NO_STAGING_DOMAINS"

        results[file_path] = {
            "status": status,
            "deprecated_found": has_deprecated,
            "correct_found": has_correct,
            "deprecated_lines": deprecated_lines,
            "correct_lines": correct_lines
        }

    return results


def test_ssot_module():
    """Test that the SSOT staging domains module works correctly."""
    try:
        from shared.constants.staging_domains import (
            STAGING_DOMAINS,
            validate_staging_domain,
            is_deprecated_staging_domain
        )

        # Test key domains exist
        required_keys = ["FRONTEND_URL", "BACKEND_URL", "API_BASE_URL", "AUTH_SERVICE_URL", "WEBSOCKET_URL"]
        missing_keys = [key for key in required_keys if key not in STAGING_DOMAINS]

        if missing_keys:
            return False, f"Missing required domain keys: {missing_keys}"

        # Test validation functions
        valid, _ = validate_staging_domain(STAGING_DOMAINS["FRONTEND_URL"])
        if not valid:
            return False, "SSOT domain validation failed for frontend URL"

        # Test deprecated detection
        deprecated = is_deprecated_staging_domain("https://app.staging.netrasystems.ai")
        if not deprecated:
            return False, "Failed to detect deprecated domain format"

        return True, "SSOT module working correctly"
    except Exception as e:
        return False, f"SSOT module error: {e}"


def main():
    """Main validation function."""
    print("=" * 60)
    print("PHASE 1 DOMAIN REMEDIATION VALIDATION")
    print("=" * 60)

    # Test SSOT module
    print("\nSSOT MODULE VALIDATION")
    print("-" * 40)
    ssot_working, ssot_message = test_ssot_module()
    if ssot_working:
        print(f"PASS: SSOT Module: {ssot_message}")
    else:
        print(f"FAIL: SSOT Module: {ssot_message}")

    # Validate critical files
    print("\nCRITICAL FILES VALIDATION")
    print("-" * 40)

    results = validate_critical_files()

    fixed_count = 0
    needs_fix_count = 0

    for file_path, result in results.items():
        status = result["status"]

        if status == "FIXED":
            print(f"PASS: {file_path}: DOMAIN FIXES APPLIED")
            fixed_count += 1
        elif status == "NEEDS_FIX":
            print(f"FAIL: {file_path}: STILL HAS DEPRECATED DOMAINS")
            needs_fix_count += 1
            for line in result["deprecated_lines"][:3]:  # Show first 3
                print(f"   {line}")
        elif status == "FILE_NOT_FOUND":
            print(f"WARN: {file_path}: FILE NOT FOUND")
        else:
            print(f"INFO: {file_path}: NO STAGING DOMAINS FOUND")

    # Summary
    print("\nVALIDATION SUMMARY")
    print("-" * 40)
    total_files = len(results)
    print(f"Total files checked: {total_files}")
    print(f"Files with domain fixes applied: {fixed_count}")
    print(f"Files still needing fixes: {needs_fix_count}")

    if ssot_working and needs_fix_count == 0:
        print("\nSUCCESS: Phase 1 domain remediation completed successfully!")
        print("   All critical files have been updated with correct staging domains.")
        return True
    else:
        print("\nINCOMPLETE: Phase 1 domain remediation needs more work.")
        if not ssot_working:
            print("   - SSOT module has issues")
        if needs_fix_count > 0:
            print(f"   - {needs_fix_count} files still have deprecated domains")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)