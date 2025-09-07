#!/usr/bin/env python3
"""
Test script to reproduce the environment loading bug.

This demonstrates the issue where environment variables set in tests
are not visible to the configuration system.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from netra_backend.app.core.configuration.base import config_manager


def reproduce_bug():
    """Reproduce the environment loading bug."""
    
    print("=== Environment Loading Bug Reproduction ===\n")
    
    # Get the environment instance
    env = get_env()
    
    print(f"1. Initial state:")
    print(f"   - Isolation enabled: {env.is_isolated()}")
    print(f"   - Environment instance ID: {id(env)}")
    print(f"   - GEMINI_API_KEY in env: {env.get('GEMINI_API_KEY') is not None}")
    
    # Clear any existing configuration cache
    config_manager._config_cache = None
    if hasattr(config_manager.get_config, 'cache_clear'):
        config_manager.get_config.cache_clear()
    
    print(f"\n2. Setting test environment variables...")
    
    # Set environment variables as the test does
    env.set('GEMINI_API_KEY', 'test_gemini_key_from_reproduction', "test")
    env.set('JWT_SECRET_KEY', 'test_jwt_key_for_reproduction_32_chars_min', "test")  # 32+ chars required
    env.set('OAUTH_GOOGLE_CLIENT_ID_ENV', 'test_oauth_client_id', "test")
    env.set('OAUTH_GOOGLE_CLIENT_SECRET_ENV', 'test_oauth_secret', "test")
    
    print(f"   - Set GEMINI_API_KEY: {env.get('GEMINI_API_KEY')}")
    print(f"   - Set JWT_SECRET_KEY: {env.get('JWT_SECRET_KEY')}")
    
    print(f"\n3. Checking if variables are visible in same env instance:")
    print(f"   - GEMINI_API_KEY visible: {env.get('GEMINI_API_KEY')}")
    
    print(f"\n4. Getting fresh environment instance (as config system does):")
    fresh_env = get_env()
    print(f"   - Fresh env instance ID: {id(fresh_env)}")
    print(f"   - Same instance? {fresh_env is env}")
    print(f"   - GEMINI_API_KEY in fresh env: {fresh_env.get('GEMINI_API_KEY')}")
    
    print(f"\n5. Loading configuration (this is where the bug occurs):")
    try:
        config = config_manager.get_config()
        print(f"   - Config loaded successfully")
        print(f"   - Config environment: {config.environment}")
        print(f"   - LLM configs available: {list(config.llm_configs.keys())}")
        
        if 'default' in config.llm_configs:
            api_key = config.llm_configs['default'].api_key
            print(f"   - Default LLM config API key: {api_key}")
            print(f"   - Expected: test_gemini_key_from_reproduction")
            print(f"   - Match? {api_key == 'test_gemini_key_from_reproduction'}")
        else:
            print(f"   - ERROR: No 'default' LLM config found")
            
        print(f"   - JWT secret key in config: {config.jwt_secret_key}")
        
    except Exception as e:
        print(f"   - ERROR loading config: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n6. Environment state after config loading:")
    final_env = get_env()
    print(f"   - Final env instance ID: {id(final_env)}")
    print(f"   - Still same instance? {final_env is env}")
    print(f"   - GEMINI_API_KEY still visible: {final_env.get('GEMINI_API_KEY')}")
    
    return env, config if 'config' in locals() else None


def test_singleton_consistency():
    """Test singleton consistency issues."""
    
    print("\n=== Singleton Consistency Test ===\n")
    
    # Import the class directly
    from shared.isolated_environment import IsolatedEnvironment
    
    # Get instances through different methods
    instance1 = get_env()
    instance2 = IsolatedEnvironment()
    instance3 = IsolatedEnvironment.get_instance()
    
    print(f"get_env() instance ID: {id(instance1)}")
    print(f"IsolatedEnvironment() instance ID: {id(instance2)}")  
    print(f"IsolatedEnvironment.get_instance() instance ID: {id(instance3)}")
    
    print(f"All same instance? {instance1 is instance2 is instance3}")
    
    # Test variable visibility across instances
    instance1.set('TEST_SINGLETON_VAR', 'test_value', 'singleton_test')
    
    print(f"Variable set in instance1, visible in instance2? {instance2.get('TEST_SINGLETON_VAR')}")
    print(f"Variable set in instance1, visible in instance3? {instance3.get('TEST_SINGLETON_VAR')}")


if __name__ == "__main__":
    env, config = reproduce_bug()
    test_singleton_consistency()
    
    print(f"\n=== Summary ===")
    print(f"Bug reproduction completed. Check output above for issues.")
    
    if config and hasattr(config, 'llm_configs') and 'default' in config.llm_configs:
        api_key = config.llm_configs['default'].api_key
        if api_key == 'test_gemini_key_from_reproduction':
            print("✅ SUCCESS: Environment variables are being properly loaded!")
        else:
            print(f"❌ FAILURE: Expected API key 'test_gemini_key_from_reproduction', got: {api_key}")
    else:
        print("❌ FAILURE: Could not load configuration or LLM configs missing")