#!/usr/bin/env python
"""Test script to verify dev mode configuration for Redis, ClickHouse, and LLMs."""

import os
import asyncio
from app.config import get_config, reload_config
from app.redis_manager import redis_manager
from app.db.clickhouse import get_clickhouse_client
from app.llm.llm_manager import LLMManager

async def test_dev_mode_config():
    """Test that dev mode configuration works correctly."""
    
    print("=" * 60)
    print("TESTING DEV MODE CONFIGURATION")
    print("=" * 60)
    
    # Get current config
    config = get_config()
    
    print(f"\nEnvironment: {config.environment}")
    print(f"Redis Enabled: {config.dev_mode_redis_enabled}")
    print(f"ClickHouse Enabled: {config.dev_mode_clickhouse_enabled}")
    print(f"LLM Enabled: {config.dev_mode_llm_enabled}")
    
    # Test Redis
    print("\n--- Testing Redis ---")
    await redis_manager.connect()
    redis_client = await redis_manager.get_client()
    if redis_client:
        print("[OK] Redis connected and available")
    else:
        print("[X] Redis not available (as expected if disabled)")
    
    # Test ClickHouse
    print("\n--- Testing ClickHouse ---")
    async with get_clickhouse_client() as ch_client:
        if hasattr(ch_client, 'execute'):
            result = await ch_client.execute("SELECT 1")
            if result:
                print("[OK] ClickHouse connected and query executed")
            else:
                print("[X] ClickHouse returned empty result (mock mode)")
    
    # Test LLM
    print("\n--- Testing LLM ---")
    llm_manager = LLMManager(config)
    try:
        llm = llm_manager.get_llm("default")
        response = await llm.ainvoke("Test prompt")
        if hasattr(response, 'content'):
            if "[Dev Mode - LLM Disabled]" in response.content:
                print("[OK] LLM in mock mode (as expected when disabled)")
            else:
                print("[OK] LLM working normally")
    except ValueError as e:
        print(f"[INFO] LLM unavailable: {e}")
    
    print("\n" + "=" * 60)
    print("TEST WITH SERVICES DISABLED")
    print("=" * 60)
    
    # Set environment variables to disable services
    os.environ["DEV_MODE_DISABLE_REDIS"] = "true"
    os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"
    os.environ["DEV_MODE_DISABLE_LLM"] = "true"
    
    # Force reload config
    reload_config()
    config = get_config()
    
    print(f"\nAfter setting disable flags:")
    print(f"Redis Enabled: {config.dev_mode_redis_enabled}")
    print(f"ClickHouse Enabled: {config.dev_mode_clickhouse_enabled}")
    print(f"LLM Enabled: {config.dev_mode_llm_enabled}")
    
    # Re-initialize services with new config
    redis_manager.enabled = redis_manager._check_if_enabled()
    await redis_manager.connect()
    
    # Test Redis (should be disabled)
    print("\n--- Testing Redis (disabled) ---")
    redis_client = await redis_manager.get_client()
    if redis_client:
        print("[X] Redis still available (unexpected)")
    else:
        print("[OK] Redis not available (as expected when disabled)")
    
    # Test ClickHouse (should be mock)
    print("\n--- Testing ClickHouse (disabled) ---")
    async with get_clickhouse_client() as ch_client:
        result = await ch_client.execute("SELECT 1")
        if isinstance(result, list) and len(result) == 0:
            print("[OK] ClickHouse in mock mode (as expected when disabled)")
        else:
            print("[X] ClickHouse still returning real results")
    
    # Test LLM (should be mock)
    print("\n--- Testing LLM (disabled) ---")
    llm_manager = LLMManager(config)
    llm = llm_manager.get_llm("default")
    response = await llm.ainvoke("Test prompt")
    if "[Dev Mode - LLM Disabled]" in response.content:
        print("[OK] LLM in mock mode (as expected when disabled)")
    else:
        print("[X] LLM still working normally")
    
    # Clean up
    os.environ.pop("DEV_MODE_DISABLE_REDIS", None)
    os.environ.pop("DEV_MODE_DISABLE_CLICKHOUSE", None)
    os.environ.pop("DEV_MODE_DISABLE_LLM", None)
    
    print("\n" + "=" * 60)
    print("DEV MODE CONFIGURATION TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_dev_mode_config())