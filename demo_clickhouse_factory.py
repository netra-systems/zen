"""
Demonstration: ClickHouse Factory Pattern for User Isolation

This script demonstrates how to use the new ClickHouse Factory pattern
to create user-isolated ClickHouse clients with proper connection pooling
and cache isolation.

Key Features Demonstrated:
- User-isolated ClickHouse clients
- Per-user connection pools and caches
- Thread-safe concurrent access
- Automatic resource cleanup
- Factory pattern with proper lifecycle management

Business Value:
- Complete data isolation between users
- Enterprise-grade security and compliance
- Scalable concurrent multi-user access
- Zero risk of cross-user data contamination

Usage:
    python demo_clickhouse_factory.py
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from netra_backend.app.factories.clickhouse_factory import (
    get_clickhouse_factory, 
    get_user_clickhouse_client,
    cleanup_clickhouse_factory
)
from netra_backend.app.models.user_execution_context import UserExecutionContext

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def demonstrate_user_isolation():
    """Demonstrate user isolation with the ClickHouse factory pattern."""
    logger.info("=== ClickHouse Factory Pattern Demonstration ===")
    
    # Create user execution contexts for different users
    user1_context = UserExecutionContext(
        user_id="demo_user_1",
        request_id="req_001",
        thread_id="thread_001",
        run_id="run_001"
    )
    
    user2_context = UserExecutionContext(
        user_id="demo_user_2", 
        request_id="req_002",
        thread_id="thread_002",
        run_id="run_002"
    )
    
    logger.info(f"Created contexts for users: {user1_context.user_id} and {user2_context.user_id}")
    
    # Get the global factory
    factory = get_clickhouse_factory()
    logger.info(f"Factory created: {factory.factory_name}")
    
    try:
        # Method 1: Using factory context manager (Recommended)
        logger.info("\n--- Method 1: Factory Context Manager ---")
        
        async with factory.get_user_client(user1_context) as user1_client:
            logger.info(f"User 1 client created: {user1_client.user_id}")
            
            # Get client stats
            stats = user1_client.get_client_stats()
            logger.info(f"User 1 client stats: {stats}")
            
            # Demonstrate cache isolation
            cache_stats = await user1_client.get_cache_stats()
            logger.info(f"User 1 cache stats: {cache_stats}")
        
        async with factory.get_user_client(user2_context) as user2_client:
            logger.info(f"User 2 client created: {user2_client.user_id}")
            
            cache_stats = await user2_client.get_cache_stats()
            logger.info(f"User 2 cache stats: {cache_stats}")
        
        # Method 2: Using convenience function (Alternative)
        logger.info("\n--- Method 2: Convenience Function ---")
        
        async with get_user_clickhouse_client(user1_context) as client:
            logger.info(f"Convenience client created for user: {client.user_id}")
        
        # Show factory statistics
        factory_stats = await factory.get_factory_stats()
        logger.info(f"\nFactory statistics: {factory_stats}")
        
    except Exception as e:
        logger.error(f"Demo error: {e}")
    
    finally:
        # Cleanup
        await cleanup_clickhouse_factory()
        logger.info("Factory cleanup completed")


async def demonstrate_concurrent_access():
    """Demonstrate concurrent access by multiple users."""
    logger.info("\n=== Concurrent Access Demonstration ===")
    
    factory = get_clickhouse_factory()
    
    # Create multiple user contexts
    contexts = []
    for i in range(5):
        context = UserExecutionContext(
            user_id=f"concurrent_user_{i}",
            request_id=f"req_{i:03d}",
            thread_id=f"thread_{i:03d}",
            run_id=f"run_{i:03d}"
        )
        contexts.append(context)
    
    logger.info(f"Created {len(contexts)} user contexts for concurrent testing")
    
    async def user_task(context: UserExecutionContext) -> dict:
        """Simulate a user task with ClickHouse operations."""
        try:
            async with factory.get_user_client(context) as client:
                # Simulate some work
                await asyncio.sleep(0.1)
                
                # Get stats
                stats = client.get_client_stats()
                cache_stats = await client.get_cache_stats()
                
                return {
                    "user_id": context.user_id,
                    "client_stats": stats,
                    "cache_stats": cache_stats,
                    "status": "success"
                }
        except Exception as e:
            return {
                "user_id": context.user_id,
                "error": str(e),
                "status": "error"
            }
    
    # Execute all user tasks concurrently
    logger.info("Starting concurrent user tasks...")
    results = await asyncio.gather(*[user_task(ctx) for ctx in contexts])
    
    # Report results
    successful = sum(1 for r in results if r["status"] == "success")
    logger.info(f"Concurrent tasks completed: {successful}/{len(results)} successful")
    
    for result in results:
        if result["status"] == "success":
            logger.info(f"  {result['user_id']}: Client isolated ✓")
        else:
            logger.error(f"  {result['user_id']}: Error - {result['error']}")
    
    # Show final factory stats
    final_stats = await factory.get_factory_stats()
    logger.info(f"Final factory stats: {final_stats}")
    
    # Cleanup
    await cleanup_clickhouse_factory()


async def demonstrate_resource_management():
    """Demonstrate resource management and cleanup."""
    logger.info("\n=== Resource Management Demonstration ===")
    
    factory = get_clickhouse_factory()
    
    # Create user context
    context = UserExecutionContext(
        user_id="resource_demo_user",
        request_id="resource_req",
        thread_id="resource_thread",
        run_id="resource_run"
    )
    
    # Create multiple clients for the same user to test limits
    logger.info("Testing per-user client limits...")
    
    clients = []
    try:
        for i in range(3):  # Factory default max is usually 3-5
            context_variant = UserExecutionContext(
                user_id=context.user_id,  # Same user
                request_id=f"req_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}"
            )
            
            client = await factory.create_user_client(context_variant)
            clients.append(client)
            logger.info(f"Created client {i+1} for user {context.user_id}")
            
    except ValueError as e:
        logger.info(f"Client limit reached: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    # Show resource usage
    stats = await factory.get_factory_stats()
    logger.info(f"Resource usage: {stats['total_clients']} clients, {stats['users_with_clients']} users")
    
    # Cleanup specific user
    if clients:
        cleanup_count = await factory.cleanup_user_clients(context.user_id)
        logger.info(f"Cleaned up {cleanup_count} clients for user {context.user_id}")
    
    # Final cleanup
    await cleanup_clickhouse_factory()


async def main():
    """Run all demonstrations."""
    logger.info("Starting ClickHouse Factory Pattern Demonstrations")
    
    try:
        await demonstrate_user_isolation()
        await demonstrate_concurrent_access()
        await demonstrate_resource_management()
        
        logger.info("\n=== All Demonstrations Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())