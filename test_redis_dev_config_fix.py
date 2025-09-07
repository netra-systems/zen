"""Test script to verify Redis configuration fix for dev environment."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from netra_backend.app.core.backend_environment import BackendEnvironment
from netra_backend.app.redis_manager import RedisManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_redis_connection():
    """Test Redis connection using fixed configuration."""
    print("\n=== Testing Redis Connection with Fixed Configuration ===\n")
    
    # Test BackendEnvironment configuration
    print("1. Testing BackendEnvironment Redis configuration:")
    backend_env = BackendEnvironment()
    redis_url = backend_env.get_redis_url()
    print(f"   Redis URL from BackendEnvironment: {redis_url}")
    print(f"   Redis Host: {backend_env.get_redis_host()}")
    print(f"   Redis Port: {backend_env.get_redis_port()}")
    
    # Test RedisManager connection
    print("\n2. Testing RedisManager connection:")
    redis_manager = RedisManager()
    
    try:
        # Initialize connection
        connected = await redis_manager.initialize()
        if connected:
            print("   ✓ Redis connection successful!")
            
            # Test basic operations
            print("\n3. Testing basic Redis operations:")
            
            # Set a test value
            await redis_manager.set("test_key", "test_value", expire=60)
            print("   ✓ SET operation successful")
            
            # Get the test value
            value = await redis_manager.get("test_key")
            print(f"   ✓ GET operation successful: {value}")
            
            # Delete the test value
            await redis_manager.delete("test_key")
            print("   ✓ DELETE operation successful")
            
            # Check health
            is_healthy = await redis_manager.is_healthy()
            print(f"\n4. Redis health check: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")
            
        else:
            print("   ✗ Redis connection failed!")
            print("   Check that Redis container is running and accessible")
            
    except Exception as e:
        print(f"   ✗ Error during Redis operations: {e}")
    
    finally:
        # Cleanup
        await redis_manager.shutdown()
        print("\n5. Redis manager shutdown complete")


async def test_direct_redis_connection():
    """Test direct Redis connection to verify configuration."""
    print("\n=== Testing Direct Redis Connection ===\n")
    
    try:
        import redis.asyncio as redis
        
        backend_env = BackendEnvironment()
        redis_url = backend_env.get_redis_url()
        
        print(f"Connecting directly to: {redis_url}")
        client = redis.from_url(redis_url, decode_responses=True)
        
        # Test ping
        pong = await client.ping()
        print(f"✓ Direct connection successful: PING -> {pong}")
        
        # Close connection
        await client.close()
        
    except Exception as e:
        print(f"✗ Direct connection failed: {e}")


def main():
    """Main test function."""
    print("\n" + "="*60)
    print("Redis Configuration Fix Test")
    print("="*60)
    
    # Run tests
    asyncio.run(test_redis_connection())
    asyncio.run(test_direct_redis_connection())
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    
    print("\nFix Summary:")
    print("- Updated redis_manager.py to use BackendEnvironment.get_redis_url()")
    print("- Updated test_environment.py to use BackendEnvironment.get_redis_url()")
    print("- Removed hardcoded 'redis://localhost:6380' defaults")
    print("- Now uses proper environment-based configuration")
    print("\nExpected Redis URLs by environment:")
    print("- Development (Docker): redis://dev-redis:6379/0")
    print("- Test (Docker): redis://test-redis:6379/0 or localhost:6381")
    print("- Staging: Configured via REDIS_URL environment variable")
    print("- Production: Configured via REDIS_URL environment variable")


if __name__ == "__main__":
    main()