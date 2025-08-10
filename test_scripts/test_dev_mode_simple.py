#!/usr/bin/env python
"""Simple test to verify dev mode configuration for Redis, ClickHouse, and LLMs."""

import os
import sys

# Set environment variables BEFORE importing anything
os.environ["DEV_MODE_DISABLE_REDIS"] = "true"
os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"
os.environ["DEV_MODE_DISABLE_LLM"] = "true"

import asyncio
from app.config import get_config
from app.redis_manager import redis_manager
from app.db.clickhouse import get_clickhouse_client
from app.llm.llm_manager import LLMManager

async def test_dev_mode_disabled():
    """Test that services are properly disabled in dev mode."""
    
    print("=" * 60)
    print("TESTING DEV MODE WITH SERVICES DISABLED")
    print("=" * 60)
    
    # Get config
    config = get_config()
    
    print(f"\nEnvironment: {config.environment}")
    print(f"Redis Enabled: {config.dev_mode_redis_enabled}")
    print(f"ClickHouse Enabled: {config.dev_mode_clickhouse_enabled}")
    print(f"LLM Enabled: {config.dev_mode_llm_enabled}")
    
    # Test Redis (should be disabled)
    print("\n--- Testing Redis (should be disabled) ---")
    await redis_manager.connect()
    redis_client = await redis_manager.get_client()
    if redis_client:
        print("[FAIL] Redis still available when disabled")
        return False
    else:
        print("[PASS] Redis correctly disabled")
    
    # Test ClickHouse (should be mock)
    print("\n--- Testing ClickHouse (should be mock) ---")
    async with get_clickhouse_client() as ch_client:
        result = await ch_client.execute("SELECT 1")
        if isinstance(result, list) and len(result) == 0:
            print("[PASS] ClickHouse using mock client")
        else:
            print("[FAIL] ClickHouse not using mock")
            return False
    
    # Test LLM (should be mock)
    print("\n--- Testing LLM (should be mock) ---")
    llm_manager = LLMManager(config)
    llm = llm_manager.get_llm("default")
    response = await llm.ainvoke("Test prompt")
    if "[Dev Mode - LLM Disabled]" in response.content:
        print("[PASS] LLM using mock client")
    else:
        print("[FAIL] LLM not using mock")
        return False
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED - Services correctly disabled in dev mode")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_dev_mode_disabled())
    sys.exit(0 if success else 1)