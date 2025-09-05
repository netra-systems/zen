#!/usr/bin/env python3
"""
Test CORS configuration for staging environment
Verifies that all required origins are included in CORS configuration
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.cors_config_builder import CORSConfigurationBuilder


def test_cors_staging_origins():
    """Test that staging CORS configuration includes all required origins."""
    print("\n=== Testing CORS Configuration for Staging Environment ===\n")
    
    # Initialize CORS builder with staging environment
    cors = CORSConfigurationBuilder({"ENVIRONMENT": "staging"})
    
    # Get allowed origins
    allowed_origins = cors.origins.allowed
    
    print(f"Environment: {cors.environment}")
    print(f"Total allowed origins: {len(allowed_origins)}\n")
    
    # Required origins that must be present
    required_origins = [
        "https://staging.netrasystems.ai",  # Base staging domain (frontend might redirect here)
        "https://app.staging.netrasystems.ai",  # Main frontend
        "https://auth.staging.netrasystems.ai",  # Auth service
        "https://api.staging.netrasystems.ai",  # Backend API
    ]
    
    print("Required origins check:")
    print("-" * 50)
    
    all_present = True
    for origin in required_origins:
        is_present = origin in allowed_origins
        status = "[OK]" if is_present else "[FAIL]"
        print(f"{status} {origin}: {'PRESENT' if is_present else 'MISSING'}")
        if not is_present:
            all_present = False
    
    print("\nAll configured origins:")
    print("-" * 50)
    for i, origin in enumerate(allowed_origins, 1):
        print(f"{i:2}. {origin}")
    
    # Test origin validation
    print("\n\nOrigin validation tests:")
    print("-" * 50)
    
    test_origins = [
        "https://staging.netrasystems.ai",
        "https://app.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai",
        "https://api.staging.netrasystems.ai",
        "http://localhost:3000",
        "https://evil.com",
        "https://auth.staging.netrasystems.ai",
    ]
    
    for origin in test_origins:
        is_allowed = cors.origins.is_allowed(origin)
        status = "[ALLOWED]" if is_allowed else "[BLOCKED]"
        print(f"{status}: {origin}")
    
    # Get FastAPI middleware config
    print("\n\nFastAPI CORS Middleware Configuration:")
    print("-" * 50)
    config = cors.fastapi.get_middleware_config()
    
    print(f"Allow credentials: {config.get('allow_credentials')}")
    print(f"Max age: {config.get('max_age')} seconds")
    print(f"Allowed methods: {', '.join(config.get('allow_methods', []))}")
    print(f"Allowed headers count: {len(config.get('allow_headers', []))}")
    print(f"Exposed headers: {', '.join(config.get('expose_headers', []))}")
    
    print("\n" + "=" * 50)
    if all_present:
        print("[SUCCESS] All required origins are configured correctly!")
    else:
        print("[FAILURE] Some required origins are missing from CORS configuration!")
        print("   This will cause CORS errors in staging environment.")
    print("=" * 50 + "\n")
    
    return all_present


def test_cors_production_origins():
    """Test that production CORS configuration is secure."""
    print("\n=== Testing CORS Configuration for Production Environment ===\n")
    
    # Initialize CORS builder with production environment
    cors = CORSConfigurationBuilder({"ENVIRONMENT": "production"})
    
    # Get allowed origins
    allowed_origins = cors.origins.allowed
    
    print(f"Environment: {cors.environment}")
    print(f"Total allowed origins: {len(allowed_origins)}\n")
    
    # Check for wildcard (should not exist in production)
    has_wildcard = "*" in allowed_origins
    
    print("Security checks:")
    print("-" * 50)
    print(f"{'[OK]' if not has_wildcard else '[FAIL]'} No wildcard origins: {'' if not has_wildcard else 'SECURITY ISSUE - Wildcard found!'}")
    
    print("\nProduction origins:")
    print("-" * 50)
    for i, origin in enumerate(allowed_origins, 1):
        print(f"{i:2}. {origin}")
    
    # Validate configuration
    is_valid, error_msg = cors.validate()
    print(f"\n{'[OK]' if is_valid else '[FAIL]'} Configuration validation: {error_msg if error_msg else 'Valid'}")
    
    return not has_wildcard and is_valid


if __name__ == "__main__":
    staging_ok = test_cors_staging_origins()
    production_ok = test_cors_production_origins()
    
    if staging_ok and production_ok:
        print("\n[SUCCESS] All CORS tests passed!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Some CORS tests failed!")
        sys.exit(1)