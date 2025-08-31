#!/usr/bin/env python
"""Test script to verify Redis and GCP secret manager error fixes."""

import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_redis_connection():
    """Test Redis connection with enhanced error handling."""
    print("\n=== Testing Redis Connection ===")
    try:
        from netra_backend.app.redis_manager import RedisManager
        
        # Test with different scenarios
        scenarios = [
            ("development", False),
            ("development", True),  # test mode
            ("staging", False),
        ]
        
        for env, test_mode in scenarios:
            print(f"\nTesting {env} environment, test_mode={test_mode}")
            
            # Set environment
            os.environ["ENVIRONMENT"] = env
            
            # Create Redis manager
            manager = RedisManager(test_mode=test_mode)
            
            # Try to connect
            try:
                await manager.connect()
                print(f"[OK] Redis connection successful for {env} (test_mode={test_mode})")
                
                # Test a simple operation
                if manager.redis_client:
                    await manager.redis_client.ping()
                    print("[OK] Redis ping successful")
            except Exception as e:
                print(f"[FAIL] Redis connection failed: {e}")
                if test_mode or env == "development":
                    print("  (This might be expected with fallback behavior)")
                
    except Exception as e:
        print(f"[FAIL] Failed to test Redis: {e}")
        import traceback
        traceback.print_exc()


def test_gcp_secrets():
    """Test GCP secret manager with enhanced error handling."""
    print("\n=== Testing GCP Secret Manager ===")
    try:
        from netra_backend.app.core.configuration.secrets import SecretManager
        
        # Test with different environments
        environments = ["development", "staging", "production"]
        
        for env in environments:
            print(f"\nTesting {env} environment")
            
            # Set environment
            os.environ["ENVIRONMENT"] = env
            
            # Create secret manager
            manager = SecretManager(environment=env)
            
            # Try to load secrets
            try:
                manager.load_secrets()
                print(f"[OK] Secret loading completed for {env}")
                
                # Check what secrets were loaded
                secret_count = len(manager._secret_cache)
                print(f"  Loaded {secret_count} secrets")
                
                # Test getting a secret
                jwt_secret = manager.get_secret("JWT_SECRET")
                if jwt_secret:
                    print(f"  [OK] JWT_SECRET available")
                else:
                    print(f"  [FAIL] JWT_SECRET not available")
                    
            except Exception as e:
                print(f"[FAIL] Secret loading failed: {e}")
                
    except Exception as e:
        print(f"[FAIL] Failed to test GCP secrets: {e}")
        import traceback
        traceback.print_exc()


def test_configuration_builder():
    """Test Redis configuration builder."""
    print("\n=== Testing Redis Configuration Builder ===")
    try:
        from shared.redis_config_builder import RedisConfigurationBuilder
        
        # Test with different environment configurations
        test_configs = [
            {"ENVIRONMENT": "development", "REDIS_HOST": "localhost"},
            {"ENVIRONMENT": "staging", "REDIS_URL": "redis://staging.redis.example.com:6379"},
            {"ENVIRONMENT": "production", "REDIS_HOST": "prod.redis.example.com", "REDIS_SSL": "true"},
        ]
        
        for config in test_configs:
            env = config["ENVIRONMENT"]
            print(f"\nTesting configuration for {env}")
            
            builder = RedisConfigurationBuilder(config)
            
            # Get configuration
            try:
                client_config = builder.get_config_for_environment()
                print(f"[OK] Configuration built successfully for {env}")
                
                # Display non-sensitive config
                safe_config = {k: v for k, v in client_config.items() 
                             if k not in ['password', 'username']}
                print(f"  Config: {safe_config}")
                
            except Exception as e:
                print(f"[FAIL] Configuration failed: {e}")
                
    except Exception as e:
        print(f"[FAIL] Failed to test configuration builder: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Redis and GCP Secret Manager Error Fixes")
    print("=" * 60)
    
    # Test configuration builder first (no async)
    test_configuration_builder()
    
    # Test GCP secrets (no async)
    test_gcp_secrets()
    
    # Test Redis connection (async)
    await test_redis_connection()
    
    print("\n" + "=" * 60)
    print("Testing Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())