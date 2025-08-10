#!/usr/bin/env python
"""Test that services are enabled by default in dev mode."""

import os
import sys

# Don't set any environment variables - test default behavior

import asyncio
from app.config import get_config
from app.redis_manager import redis_manager
from app.db.clickhouse import get_clickhouse_client
from app.llm.llm_manager import LLMManager

async def test_dev_mode_enabled():
    """Test that services are enabled by default in dev mode."""
    
    print("=" * 60)
    print("TESTING DEV MODE WITH SERVICES ENABLED (DEFAULT)")
    print("=" * 60)
    
    # Get config
    config = get_config()
    
    print(f"\nEnvironment: {config.environment}")
    print(f"Redis Enabled: {config.dev_mode_redis_enabled}")
    print(f"ClickHouse Enabled: {config.dev_mode_clickhouse_enabled}")
    print(f"LLM Enabled: {config.dev_mode_llm_enabled}")
    
    if not config.dev_mode_redis_enabled:
        print("[FAIL] Redis should be enabled by default")
        return False
    
    if not config.dev_mode_clickhouse_enabled:
        print("[FAIL] ClickHouse should be enabled by default")
        return False
        
    if not config.dev_mode_llm_enabled:
        print("[FAIL] LLM should be enabled by default")
        return False
    
    print("\n[PASS] All services are enabled by default in dev mode")
    
    # Note: We don't actually test connections as they may fail due to missing credentials
    # The important thing is that the system TRIES to connect to real services
    
    print("\n" + "=" * 60)
    print("DEFAULT CONFIGURATION TEST PASSED")
    print("Services are enabled by default, can be disabled with:")
    print("  DEV_MODE_DISABLE_REDIS=true")
    print("  DEV_MODE_DISABLE_CLICKHOUSE=true")
    print("  DEV_MODE_DISABLE_LLM=true")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_dev_mode_enabled())
    sys.exit(0 if success else 1)