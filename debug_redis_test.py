#!/usr/bin/env python3
"""Debug script to test Redis configuration in test environment."""

import os
import asyncio

# Set up test environment
os.environ["TESTING"] = "1"
os.environ["NETRA_ENV"] = "e2e_testing"
os.environ["ENVIRONMENT"] = "test"
os.environ["USE_REAL_SERVICES"] = "true"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6380"
os.environ["REDIS_URL"] = "redis://localhost:6380/0"

# Import after setting environment variables
from dev_launcher.isolated_environment import get_env
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.redis_manager import redis_manager

async def debug_redis():
    print("=== Debug Redis Configuration ===")
    
    # Check environment variables
    env = get_env()
    print(f"Environment variables:")
    print(f"  TESTING: {env.get('TESTING')}")
    print(f"  ENVIRONMENT: {env.get('ENVIRONMENT')}")
    print(f"  USE_REAL_SERVICES: {env.get('USE_REAL_SERVICES')}")
    print(f"  REDIS_URL: {env.get('REDIS_URL')}")
    print(f"  REDIS_HOST: {env.get('REDIS_HOST')}")
    print(f"  REDIS_PORT: {env.get('REDIS_PORT')}")
    print(f"  TEST_DISABLE_REDIS: {env.get('TEST_DISABLE_REDIS')}")
    
    # Check unified configuration
    print(f"\nUnified configuration:")
    config = get_unified_config()
    print(f"  environment: {config.environment}")
    print(f"  redis_mode: {config.redis_mode}")
    print(f"  dev_mode_redis_enabled: {config.dev_mode_redis_enabled}")
    
    # Check Redis manager state
    print(f"\nRedis manager state:")
    print(f"  enabled: {redis_manager.enabled}")
    print(f"  test_mode: {redis_manager.test_mode}")
    
    # Try to reinitialize
    print(f"\nReinitializing Redis manager...")
    redis_manager.reinitialize_configuration()
    print(f"  enabled after reinit: {redis_manager.enabled}")
    
    # Try to get client
    print(f"\nTrying to get Redis client...")
    try:
        client = await redis_manager.get_client()
        print(f"  client: {client}")
        if client:
            print("  Redis client obtained successfully!")
        else:
            print("  Redis client is None!")
    except Exception as e:
        print(f"  Error getting client: {e}")

if __name__ == "__main__":
    asyncio.run(debug_redis())