#!/usr/bin/env python3
"""Test script to verify JWT secret key fix for staging environment."""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment to staging for testing
os.environ["ENVIRONMENT"] = "staging"
# Clear any existing JWT key to test auto-generation
if "JWT_SECRET_KEY" in os.environ:
    del os.environ["JWT_SECRET_KEY"]

def test_secret_manager():
    """Test that SecretManager handles missing JWT keys in staging."""
    from netra_backend.app.core.configuration.secrets import SecretManager
    from netra_backend.app.schemas.config import AppConfig
    
    print("Testing SecretManager with staging environment...")
    
    # Create SecretManager instance
    secret_manager = SecretManager()
    
    # Create a dummy config object
    config = AppConfig()
    
    # Populate secrets (should auto-generate missing ones)
    secret_manager.populate_secrets(config)
    
    # Check that JWT secret key was set
    jwt_key = config.jwt_secret_key
    if jwt_key:
        print(f"[OK] JWT secret key was set: {jwt_key[:10]}... (length: {len(jwt_key)})")
        if len(jwt_key) >= 32:
            print("[OK] JWT secret key meets minimum length requirement (32 chars)")
        else:
            print(f"[FAIL] JWT secret key too short: {len(jwt_key)} chars")
            return False
    else:
        print("[FAIL] JWT secret key was not set")
        return False
    
    # Check Fernet key
    if config.fernet_key:
        print(f"[OK] Fernet key was set (length: {len(str(config.fernet_key))})")
    else:
        print("[FAIL] Fernet key was not set")
        return False
    
    # Check service secret
    if hasattr(config, 'service_secret') and config.service_secret:
        print(f"[OK] Service secret was set")
    
    return True

def test_key_manager():
    """Test that KeyManager can load with auto-generated secrets."""
    from netra_backend.app.core.main_config import get_config
    from netra_backend.app.services.key_manager import KeyManager
    
    print("\nTesting KeyManager initialization...")
    
    try:
        # Get config (which should have secrets populated)
        config = get_config()
        
        # Try to load KeyManager
        key_manager = KeyManager.load_from_settings(config)
        print("[OK] KeyManager loaded successfully")
        print(f"  - JWT key length: {len(key_manager.jwt_secret_key)}")
        print(f"  - Fernet key present: {key_manager.fernet_key is not None}")
        return True
    except Exception as e:
        print(f"[FAIL] KeyManager failed to load: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing JWT Secret Key Fix for Staging Environment")
    print("=" * 60)
    
    # Test SecretManager
    secret_manager_ok = test_secret_manager()
    
    # Test KeyManager
    key_manager_ok = test_key_manager()
    
    print("\n" + "=" * 60)
    if secret_manager_ok and key_manager_ok:
        print("[SUCCESS] All tests passed! The fix is working.")
    else:
        print("[FAILURE] Some tests failed. Please review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()