"""
Migration Example: Converting Tests to Use Flexible URL Assertions

This file demonstrates how to migrate existing tests to use the new
URL assertion utilities for better compatibility with dynamic ports.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Improve test reliability and maintainability
- Value Impact: Reduces false test failures from port conflicts
- Strategic Impact: Enables parallel CI/CD and Docker dynamic ports
"""

import pytest
from typing import Dict
from test_framework.url_assertions import (
    assert_base_url_matches,
    assert_is_localhost_url,
    assert_service_url_valid,
    get_dynamic_service_url,
    URLAssertion
)

# ============================================================================
# EXAMPLE 1: Basic Service URL Test
# ============================================================================

# BEFORE: Hardcoded port expectations
def test_auth_service_url_OLD():
    """OLD: Test with hardcoded port - fails with dynamic ports."""
    auth_url = get_auth_service_url()  # Returns "http://127.0.0.1:8082"
    
    # This fails if Docker assigns port 8083 instead
    assert auth_url == "http://127.0.0.1:8001"  #  FAIL:  Brittle


# AFTER: Flexible assertion
def test_auth_service_url_NEW():
    """NEW: Test with flexible port handling."""
    auth_url = get_auth_service_url()  # Returns "http://127.0.0.1:8082"
    
    # Option 1: Just verify it's a localhost URL (most flexible)
    assert_is_localhost_url(auth_url)
    
    # Option 2: Use service-aware validation
    assert_service_url_valid("auth", auth_url, allow_dynamic=True)
    
    # Option 3: Check base URL only, ignore port
    assert_base_url_matches(auth_url, "http://127.0.0.1", ignore_port=True)


# ============================================================================
# EXAMPLE 2: Environment-Specific URL Tests
# ============================================================================

# BEFORE: Direct comparison with hardcoded URLs
class TestServiceURLAlignmentOLD:
    def __init__(self):
        self.expected_url_patterns = {
            "auth_service": {
                "development": "http://127.0.0.1:8001",  #  FAIL:  Hardcoded port
                "staging": "https://auth.staging.netrasystems.ai",
                "production": "https://auth.netrasystems.ai"
            }
        }
    
    def test_auth_url(self, environment):
        auth_url = get_auth_service_url()
        expected = self.expected_url_patterns["auth_service"][environment]
        assert auth_url == expected  #  FAIL:  Fails with dynamic ports in dev


# AFTER: Flexible comparison based on environment
class TestServiceURLAlignmentNEW:
    def __init__(self):
        # For staging/prod, exact URLs are required
        # For dev/test, we allow flexible ports
        self.expected_url_patterns = {
            "auth_service": {
                "staging": "https://auth.staging.netrasystems.ai",
                "production": "https://auth.netrasystems.ai"
            }
        }
    
    def test_auth_url(self, environment):
        auth_url = get_auth_service_url()
        
        if environment in ["staging", "production"]:
            # Staging/Production must use exact URLs
            expected = self.expected_url_patterns["auth_service"][environment]
            assert auth_url == expected  #  PASS:  Exact match for prod environments
        else:
            # Development/Test can use dynamic ports
            assert_is_localhost_url(auth_url)  #  PASS:  Flexible for dev
            
            # Optional: verify against dynamic discovery
            assert_service_url_valid("auth", auth_url, allow_dynamic=True)


# ============================================================================
# EXAMPLE 3: Multiple Service URLs
# ============================================================================

# BEFORE: Testing multiple services with hardcoded ports
def test_all_services_OLD():
    """OLD: Multiple hardcoded assertions."""
    services = get_all_service_urls()
    
    assert services["backend"] == "http://localhost:8000"  #  FAIL: 
    assert services["auth"] == "http://localhost:8081"     #  FAIL:   
    assert services["frontend"] == "http://localhost:3000" #  FAIL: 


# AFTER: Flexible testing with context manager
def test_all_services_NEW():
    """NEW: Flexible assertions for all services."""
    services = get_all_service_urls()
    
    # Option 1: Use context manager for batch assertions
    with URLAssertion(ignore_port=True) as url_assert:
        url_assert.assert_equal(services["backend"], "http://localhost:8000")
        url_assert.assert_equal(services["auth"], "http://localhost:8081")
        url_assert.assert_equal(services["frontend"], "http://localhost:3000")
    
    # Option 2: Service-specific validation with discovery
    for service_name, url in services.items():
        assert_service_url_valid(service_name, url, allow_dynamic=True)
    
    # Option 3: Just verify structure
    for service_name, url in services.items():
        assert_is_localhost_url(url)


# ============================================================================
# EXAMPLE 4: Docker Dynamic Port Integration
# ============================================================================

def test_with_docker_dynamic_ports():
    """Example using Docker port discovery directly."""
    # Get the actual dynamically assigned port
    backend_url = get_dynamic_service_url("backend", use_docker=True)
    
    if backend_url:
        # We discovered the actual port
        config = get_backend_config()
        assert config.api_url == backend_url  #  PASS:  Exact match with discovered port
    else:
        # Fallback to flexible assertion
        config = get_backend_config()
        assert_is_localhost_url(config.api_url)


# ============================================================================
# EXAMPLE 5: Migration Strategy for Large Test Suite
# ============================================================================

class MigrationStrategy:
    """
    Strategy for migrating a large test suite to flexible assertions.
    
    Phase 1: Add flexible assertions alongside existing ones
    Phase 2: Remove hardcoded assertions after validation
    Phase 3: Optimize for specific test scenarios
    """
    
    @staticmethod
    def phase1_add_flexible(url: str, expected_hardcoded: str):
        """Phase 1: Add flexible check, keep hardcoded for now."""
        try:
            # Try hardcoded first (existing behavior)
            assert url == expected_hardcoded
        except AssertionError:
            # Fall back to flexible assertion
            assert_base_url_matches(url, expected_hardcoded, ignore_port=True)
            print(f"Note: Using flexible assertion for {url}")
    
    @staticmethod
    def phase2_flexible_only(url: str, service: str):
        """Phase 2: Remove hardcoded, use only flexible."""
        assert_service_url_valid(service, url, allow_dynamic=True)
    
    @staticmethod 
    def phase3_optimized(url: str, service: str, environment: str):
        """Phase 3: Optimize based on environment."""
        if environment in ["staging", "production"]:
            # Production environments need exact URLs
            expected = get_expected_url_for_env(service, environment)
            assert url == expected
        else:
            # Dev/test environments allow dynamic
            assert_service_url_valid(service, url, allow_dynamic=True)


# ============================================================================
# Helper Functions (for examples)
# ============================================================================

def get_auth_service_url() -> str:
    """Mock function to get auth service URL."""
    return "http://127.0.0.1:8082"  # Might be dynamic

def get_all_service_urls() -> Dict[str, str]:
    """Mock function to get all service URLs."""
    return {
        "backend": "http://localhost:8001",  # Dynamic port
        "auth": "http://localhost:8082",     # Dynamic port
        "frontend": "http://localhost:3001"  # Dynamic port
    }

def get_backend_config():
    """Mock function to get backend config."""
    class Config:
        api_url = "http://localhost:8000"
    return Config()

def get_expected_url_for_env(service: str, environment: str) -> str:
    """Get expected URL for service in environment."""
    urls = {
        ("auth", "staging"): "https://auth.staging.netrasystems.ai",
        ("auth", "production"): "https://auth.netrasystems.ai",
        ("backend", "staging"): "https://api.staging.netrasystems.ai",
        ("backend", "production"): "https://api.netrasystems.ai",
    }
    return urls.get((service, environment), "http://localhost:8000")


# ============================================================================
# Test the Examples
# ============================================================================

if __name__ == "__main__":
    print("Running migration examples...")
    
    # Test the NEW versions
    test_auth_service_url_NEW()
    print(" PASS:  test_auth_service_url_NEW passed")
    
    test_all_services_NEW()
    print(" PASS:  test_all_services_NEW passed")
    
    test_with_docker_dynamic_ports()
    print(" PASS:  test_with_docker_dynamic_ports passed")
    
    print("\n PASS:  All migration examples passed!")