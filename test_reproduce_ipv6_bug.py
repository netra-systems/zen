#!/usr/bin/env python3
"""
Test script to reproduce the IPv6 localhost CORS origins bug.
This test demonstrates the exact issue before applying the fix.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.cors_config_builder import CORSConfigurationBuilder


def test_reproduces_ipv6_bug():
    """Reproduces the IPv6 localhost address bug."""
    print("Testing IPv6 localhost address inclusion in development CORS origins...")
    
    env_vars = {"ENVIRONMENT": "development"}
    cors = CORSConfigurationBuilder(env_vars)
    
    # Debug: check which method is being called
    print(f"Environment detected: {cors.environment}")
    
    # Check SSOT origins first
    from shared.security_origins_config import SecurityOriginsConfig
    ssot_origins = SecurityOriginsConfig.get_cors_origins("development")
    print(f"SSOT origins count: {len(ssot_origins)}")
    
    # Check if _get_development_origins is being called
    dev_origins = cors.origins._get_development_origins()
    print(f"_get_development_origins count: {len(dev_origins)}")
    
    origins = cors.origins.allowed
    
    print(f"\nTotal origins found: {len(origins)}")
    print("\nIPv6 localhost addresses in origins:")
    ipv6_origins = [origin for origin in origins if "[::1]" in origin]
    for origin in ipv6_origins:
        print(f"  - {origin}")
    
    # Test for expected IPv6 addresses
    expected_ipv6_addresses = [
        "http://[::1]:3000",  # This should be present but is currently missing
        "http://[::1]:3001",  # This should be present
        "http://[::1]:8000",  # This should be present
        "http://[::1]:8080",  # This should be present
    ]
    
    print("\nTesting expected IPv6 addresses:")
    bug_found = False
    for address in expected_ipv6_addresses:
        present = address in origins
        status = "PRESENT" if present else "MISSING"
        print(f"  {address}: {status}")
        if not present and address == "http://[::1]:3000":
            bug_found = True
    
    if bug_found:
        print("\nBUG CONFIRMED: http://[::1]:3000 is missing from development origins!")
        print("This is the exact issue causing the test failure.")
        return False
    else:
        print("\nAll expected IPv6 addresses are present.")
        return True


if __name__ == "__main__":
    success = test_reproduces_ipv6_bug()
    sys.exit(0 if success else 1)