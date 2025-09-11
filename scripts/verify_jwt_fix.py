#!/usr/bin/env python3
"""
Verify JWT Secret Manager SSOT Compliance After Fix

This script verifies that the JWT secret manager properly uses
IsolatedEnvironment and doesn't bypass it with os.environ.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Verify JWT secret manager SSOT compliance."""
    print("Verifying JWT Secret Manager SSOT Compliance...")
    print("=" * 60)
    
    # Import required modules
    from shared.isolated_environment import IsolatedEnvironment, get_env
    from shared.jwt_secret_manager import get_jwt_secret_manager, get_unified_jwt_secret
    
    # Reset singleton for clean test
    IsolatedEnvironment._instance = None
    
    # Test 1: Verify IsolatedEnvironment is used for environment access
    print("\n1. Testing IsolatedEnvironment usage...")
    env = IsolatedEnvironment()
    env.set('ENVIRONMENT', 'staging', source='test')
    env.set('JWT_SECRET_STAGING', 'test-staging-secret-value-32-chars', source='test')
    
    # Clear JWT manager cache
    manager = get_jwt_secret_manager()
    manager.clear_cache()
    
    # Get JWT secret
    secret = get_unified_jwt_secret()
    print(f"   ✓ Got JWT secret from IsolatedEnvironment: {secret[:20]}...")
    
    # Test 2: Verify no os.environ bypass
    print("\n2. Checking for os.environ bypass...")
    import os
    
    # Set a different value in os.environ (should NOT be used)
    os.environ['JWT_SECRET_STAGING'] = 'WRONG-VALUE-FROM-OS-ENVIRON'
    
    # Clear cache and get secret again
    manager.clear_cache()
    secret = get_unified_jwt_secret()
    
    if 'WRONG-VALUE' in secret:
        print("   ✗ ERROR: JWT manager is bypassing IsolatedEnvironment!")
        return 1
    else:
        print("   ✓ JWT manager correctly uses IsolatedEnvironment (not os.environ)")
    
    # Test 3: Verify proper error for missing staging secret
    print("\n3. Testing error handling for missing staging secret...")
    env.set('ENVIRONMENT', 'staging', source='test', force=True)
    env.set('JWT_SECRET_STAGING', '', source='test', force=True)  # Clear the secret
    manager.clear_cache()
    
    try:
        secret = get_unified_jwt_secret()
        print(f"   ✗ ERROR: Should have failed but got: {secret[:20]}...")
        return 1
    except ValueError as e:
        if 'staging' in str(e).lower():
            print(f"   ✓ Properly failed for staging without secret")
        else:
            print(f"   ✗ ERROR: Wrong error message: {e}")
            return 1
    
    # Test 4: Verify development fallback works
    print("\n4. Testing development environment fallback...")
    env.set('ENVIRONMENT', 'development', source='test', force=True)
    manager.clear_cache()
    
    secret = get_unified_jwt_secret()
    if secret and len(secret) >= 32:
        print(f"   ✓ Development fallback works: {secret[:20]}...")
    else:
        print(f"   ✗ ERROR: Development fallback failed")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ All JWT Secret Manager SSOT compliance tests passed!")
    print("\nThe fix successfully:")
    print("  - Removed os.environ bypass")
    print("  - Uses IsolatedEnvironment exclusively")
    print("  - Maintains proper SSOT principles")
    print("  - Preserves error handling for staging/production")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())