import asyncio
from app.services.llm_cache_service import llm_cache_service
from app.redis_manager import redis_manager

async def test_redis_get():
    """Test to reproduce the redis get error"""
    try:
        # First ensure redis is connected
        await redis_manager.connect()
        print("Redis connected successfully")
        
        # Test direct get on redis_manager
        print(f"redis_manager has 'get' method: {hasattr(redis_manager, 'get')}")
        
        # Try to get a cached response
        result = await llm_cache_service.get_cached_response(
            prompt="test prompt",
            llm_config_name="test_config"
        )
        print(f"Cache lookup result: {result}")
        
        # Test direct redis_manager.get call
        test_result = await redis_manager.get("test_key")
        print(f"Direct redis_manager.get result: {test_result}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await redis_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(test_redis_get())