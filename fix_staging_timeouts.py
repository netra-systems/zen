#!/usr/bin/env python3
"""
Fix staging timeout configuration for Issue #1278
Updates the deployment script to use 90-second timeouts
"""

import re
import os

def fix_timeout_configuration():
    """Update the deployment script with correct 90-second timeouts"""
    script_path = "C:\\netra-apex\\scripts\\deploy_to_gcp_actual.py"

    # Read the current file
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update timeout values to 90 seconds
    updates = [
        ('"AUTH_DB_URL_TIMEOUT": "10.0"', '"AUTH_DB_URL_TIMEOUT": "90.0"'),
        ('"AUTH_DB_ENGINE_TIMEOUT": "30.0"', '"AUTH_DB_ENGINE_TIMEOUT": "90.0"'),
        ('"AUTH_DB_VALIDATION_TIMEOUT": "60.0"', '"AUTH_DB_VALIDATION_TIMEOUT": "90.0"')
    ]

    original_content = content
    for old_value, new_value in updates:
        if old_value in content:
            content = content.replace(old_value, new_value)
            print(f"Updated: {old_value} -> {new_value}")
        else:
            print(f"Warning: {old_value} not found in file")

    # Check if any changes were made
    if content != original_content:
        # Write the updated content back
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success: Updated timeout configuration")
        return True
    else:
        print("Error: No changes made - patterns not found")
        return False

if __name__ == "__main__":
    print("=== Fixing Issue #1278 Staging Timeout Configuration ===")
    success = fix_timeout_configuration()

    if success:
        print("\nNext steps:")
        print("1. Redeploy services with updated timeout configuration")
        print("2. Test container startup")
        print("3. Validate 90-second database timeouts")
    else:
        print("\nError: Unable to update timeout configuration")
        print("Please check the deployment script manually")