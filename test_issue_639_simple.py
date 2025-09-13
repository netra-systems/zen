#!/usr/bin/env python3
"""
Simple test to validate Issue #639 bug reproduction without complex markers
"""

import pytest
from shared.isolated_environment import get_env


def test_get_env_signature_error_simple():
    """
    Simple test to reproduce the get_env() signature error.
    
    This should demonstrate the exact TypeError that occurs when get_env() 
    is called with arguments.
    """
    print("🔍 Testing get_env signature error...")
    
    # This should fail with TypeError
    with pytest.raises(TypeError, match=r"get_env\(\) takes 0 positional arguments but 2 were given"):
        result = get_env("STAGING_BASE_URL", "https://staging.netra.ai")
    
    print("✅ Successfully reproduced the signature error")


def test_correct_get_env_usage_simple():
    """
    Test the correct usage of get_env().
    """
    print("🔍 Testing correct get_env usage...")
    
    # This should work
    env = get_env()
    result = env.get("STAGING_BASE_URL", "https://staging.netra.ai")
    
    assert result == "https://staging.netra.ai"
    print(f"✅ Correct usage works: {result}")


def test_staging_configuration_pattern_validation():
    """
    Test the staging configuration pattern that should work after fixes.
    """
    print("🔍 Testing staging configuration pattern...")
    
    env = get_env()
    
    # This is the CORRECT pattern for staging configuration
    staging_config = {
        "base_url": env.get("STAGING_BASE_URL", "https://staging.netra.ai"),
        "websocket_url": env.get("STAGING_WEBSOCKET_URL", "wss://staging.netra.ai/ws"),
        "api_url": env.get("STAGING_API_URL", "https://staging.netra.ai/api"),
        "auth_url": env.get("STAGING_AUTH_URL", "https://staging.netra.ai/auth")
    }
    
    # Validate configuration structure
    assert "base_url" in staging_config
    assert "websocket_url" in staging_config
    assert "api_url" in staging_config
    assert "auth_url" in staging_config
    
    # Validate URLs have proper format
    assert staging_config["base_url"].startswith("https://")
    assert staging_config["websocket_url"].startswith("wss://")
    assert staging_config["api_url"].startswith("https://")
    assert staging_config["auth_url"].startswith("https://")
    
    print("✅ Staging configuration pattern validated")
    print(f"   Base URL: {staging_config['base_url']}")
    print(f"   WebSocket URL: {staging_config['websocket_url']}")
    print(f"   API URL: {staging_config['api_url']}")
    print(f"   Auth URL: {staging_config['auth_url']}")