#!/usr/bin/env python3
"""
Simple test to verify auth_core coverage configuration fix
"""

def test_simple_auth_core_import():
    """Test that we can import from auth_service.auth_core without issues"""
    # This test will trigger coverage tracking of auth_service.auth_core
    from auth_service.auth_core.config import AuthConfig
    
    # Just verify the class exists
    assert AuthConfig is not None
    assert hasattr(AuthConfig, '__init__')

if __name__ == "__main__":
    test_simple_auth_core_import()
    print("Test passed - auth_service.auth_core can be imported")