#!/usr/bin/env python3
"""Test script to verify staging secrets handling."""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_staging_secrets():
    """Test staging secrets loading."""
    print("Testing staging secrets handling...")
    
    # Set up test environment
    os.environ["ENVIRONMENT"] = "staging"
    os.environ["GEMINI_API_KEY_STAGING"] = "test-gemini-key-staging"
    os.environ["JWT_SECRET_KEY_STAGING"] = "test-jwt-staging"
    os.environ["FERNET_KEY_STAGING"] = "test-fernet-staging"
    
    # Import after setting environment
    from app.core.secret_manager import SecretManager
    
    # Test secret loading
    manager = SecretManager()
    secrets = manager._load_from_environment()
    
    # Check results
    print("\nLoaded secrets from environment:")
    for key in ["gemini-api-key", "jwt-secret-key", "fernet-key"]:
        if key in secrets:
            print(f"  [OK] {key}: Found (value hidden)")
        else:
            print(f"  [MISSING] {key}: Not found")
    
    # Verify staging suffix handling
    expected_keys = ["gemini-api-key", "jwt-secret-key", "fernet-key"]
    found_keys = [k for k in expected_keys if k in secrets]
    
    if len(found_keys) == len(expected_keys):
        print("\n[SUCCESS] All staging secrets loaded correctly")
        return True
    else:
        print(f"\n[FAILED] Only {len(found_keys)}/{len(expected_keys)} secrets loaded")
        return False

if __name__ == "__main__":
    success = test_staging_secrets()
    sys.exit(0 if success else 1)