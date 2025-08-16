#!/usr/bin/env python3
"""Test CORS configuration for different environments."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock settings for testing
class MockSettings:
    def __init__(self, env):
        self.environment = env

# Test the is_origin_allowed function
from app.core.middleware_setup import is_origin_allowed

def test_cors_patterns():
    """Test CORS patterns for different environments."""
    
    # Test Development
    print("=== DEVELOPMENT ENVIRONMENT ===")
    from unittest.mock import patch
    with patch('app.core.middleware_setup.settings', MockSettings('development')):
        dev_origins = ["http://localhost:3000", "http://localhost:8000", "*"]
        
        test_cases = [
            ("http://localhost:3000", True, "Direct match"),
            ("http://localhost:49672", True, "Random localhost port"),
            ("http://127.0.0.1:5000", True, "127.0.0.1 with port"),
            ("https://localhost:8080", True, "HTTPS localhost"),
            ("https://google.com", False, "External domain"),
        ]
        
        for origin, expected, description in test_cases:
            result = is_origin_allowed(origin, dev_origins)
            status = "PASS" if result == expected else "FAIL"
            print(f"  {status} {description}: {origin} -> {result}")
    
    # Test Staging
    print("\n=== STAGING ENVIRONMENT ===")
    with patch('app.core.middleware_setup.settings', MockSettings('staging')):
        staging_origins = [
            "https://staging.netrasystems.ai",
            "https://app.staging.netrasystems.ai",
            "*"
        ]
        
        test_cases = [
            ("https://app.staging.netrasystems.ai", True, "Direct match"),
            ("https://auth.staging.netrasystems.ai", True, "Subdomain pattern"),
            ("https://backend-staging-ca654d8b-uc.a.run.app", True, "Cloud Run URL"),
            ("https://api-service-xyz123-uc.a.run.app", True, "Another Cloud Run"),
            ("http://localhost:3000", True, "Localhost for staging dev"),
            ("https://production.netrasystems.ai", False, "Production domain"),
            ("https://malicious.com", False, "External domain"),
        ]
        
        for origin, expected, description in test_cases:
            result = is_origin_allowed(origin, staging_origins)
            status = "PASS" if result == expected else "FAIL"
            print(f"  {status} {description}: {origin} -> {result}")
    
    # Test Production
    print("\n=== PRODUCTION ENVIRONMENT ===")
    with patch('app.core.middleware_setup.settings', MockSettings('production')):
        prod_origins = ["https://netra.ai", "https://app.netra.ai"]
        
        test_cases = [
            ("https://netra.ai", True, "Direct match"),
            ("https://app.netra.ai", True, "Direct match"),
            ("https://staging.netrasystems.ai", False, "Staging domain"),
            ("http://localhost:3000", False, "Localhost"),
            ("https://malicious.com", False, "External domain"),
        ]
        
        for origin, expected, description in test_cases:
            result = is_origin_allowed(origin, prod_origins)
            status = "PASS" if result == expected else "FAIL"
            print(f"  {status} {description}: {origin} -> {result}")

if __name__ == "__main__":
    test_cors_patterns()