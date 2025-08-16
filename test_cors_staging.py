#!/usr/bin/env python3
"""Test CORS configuration for staging environment."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment to staging for testing
os.environ["ENVIRONMENT"] = "staging"
os.environ["CORS_ORIGINS"] = "https://staging.netrasystems.ai,https://app.staging.netrasystems.ai,https://auth.staging.netrasystems.ai,https://backend.staging.netrasystems.ai"

from app.core.middleware_setup import get_cors_origins, is_origin_allowed

def test_staging_cors():
    """Test CORS configuration for staging environment."""
    print("Testing CORS configuration for staging environment...")
    
    # Get configured origins
    origins = get_cors_origins()
    print(f"\nConfigured CORS origins: {origins}")
    
    # Test cases
    test_origins = [
        ("https://app.staging.netrasystems.ai", True),
        ("https://staging.netrasystems.ai", True),
        ("https://auth.staging.netrasystems.ai", True),
        ("https://backend.staging.netrasystems.ai", True),
        ("https://backend-staging-ca654d8b-uc.a.run.app", True),
        ("https://netra-backend-e7oy7k4boa-uc.a.run.app", True),
        ("http://localhost:3000", True),
        ("http://localhost:3001", True),
        ("https://evil.com", False),
        ("https://app.production.netrasystems.ai", False),
    ]
    
    print("\nTesting origin validation:")
    print("-" * 60)
    
    all_passed = True
    for origin, expected in test_origins:
        result = is_origin_allowed(origin, origins)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            all_passed = False
        print(f"{status:4} {origin:<50} Expected: {expected}, Got: {result}")
    
    print("-" * 60)
    if all_passed:
        print("\n[PASS] All CORS tests passed!")
    else:
        print("\n[FAIL] Some CORS tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    test_staging_cors()