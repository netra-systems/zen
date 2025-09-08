"""Test environment service for E2E testing infrastructure."""

import asyncio
import os
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import redis.asyncio as redis
from loguru import logger
from shared.isolated_environment import get_env
from netra_backend.app.core.backend_environment import BackendEnvironment


env = get_env()
class TestEnvironment:
    """Test environment management for E2E tests with real service integration."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.database_pool = None
        self.test_data: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize test environment with real services."""
        if self._initialized:
            return
            
        logger.info("Initializing test environment")
        
        # Initialize Redis connection if not already set
        if not self.redis_client:
            backend_env = BackendEnvironment()
            redis_url = backend_env.get_redis_url()
            self.redis_client = await redis.from_url(redis_url)
        
        # Test Redis connection
        try:
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
        
        self._initialized = True
        logger.info("Test environment initialized successfully")
    
    async def seed_user_data(self) -> None:
        """Seed test data for concurrent user testing."""
        logger.info("Seeding test user data")
        
        # Create test users data
        test_users = []
        for i in range(10):
            user_data = {
                "user_id": f"test_user_{i}",
                "email": f"test{i}@example.com", 
                "session_id": f"session_{i}",
                "auth_token": f"token_{i}",
                "sensitive_data": {"test_data": f"sensitive_{i}"},
                "context_data": {"budget": 1000 * i, "region": "us-east-1"}
            }
            test_users.append(user_data)
        
        self.test_data["users"] = test_users
        
        # Store in Redis for test isolation
        if self.redis_client:
            try:
                for user in test_users:
                    key = f"test_user:{user['user_id']}"
                    await self.redis_client.hset(key, mapping=user)
            except Exception as e:
                logger.warning(f"Failed to seed Redis data: {e}")
    
    async def cleanup_user_data(self) -> None:
        """Cleanup test user data."""
        logger.info("Cleaning up test user data")
        
        if self.redis_client and "users" in self.test_data:
            try:
                for user in self.test_data["users"]:
                    key = f"test_user:{user['user_id']}"
                    await self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Failed to cleanup Redis data: {e}")
        
        self.test_data.clear()
    
    async def cleanup(self) -> None:
        """Cleanup test environment."""
        logger.info("Cleaning up test environment")
        
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception as e:
                logger.warning(f"Failed to close Redis connection: {e}")
            
        self._initialized = False
        logger.info("Test environment cleanup completed")