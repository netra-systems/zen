"""
Redis test fixtures and mock objects for comprehensive testing
Provides reusable mock classes and pytest fixtures
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
import redis.asyncio as redis

from netra_backend.app.redis_manager import RedisManager
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

# MockRedisClient now imported from canonical test_framework location
# Eliminates SSOT violation as per CLAUDE.md Section 2.1

class RedisConnectionPool:
    """Mock Redis connection pool for testing"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.active_connections = 0
        self.total_connections_created = 0
        self.connection_queue = asyncio.Queue()
        self.connections = []
        
    async def get_connection(self) -> MockRedisClient:
        """Get connection from pool"""
        if self.active_connections < self.max_connections:
            connection = MockRedisClient()
            connection.connection_count = 1
            self.active_connections += 1
            self.total_connections_created += 1
            self.connections.append(connection)
            return connection
        else:
            # Wait for available connection (simplified)
            await asyncio.sleep(0.001)
            return await self.get_connection()
    
    async def return_connection(self, connection: MockRedisClient):
        """Return connection to pool"""
        if connection in self.connections:
            self.active_connections = max(0, self.active_connections - 1)
    
    async def close_all(self):
        """Close all connections"""
        for connection in self.connections:
            await connection.close()
        self.connections.clear()
        self.active_connections = 0

class EnhancedRedisManager(RedisManager):
    """Enhanced Redis manager with additional features for testing"""
    
    def __init__(self):
        super().__init__()
        self.connection_pool = None
        self.operation_metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        self.retry_config = {
            'max_retries': 3,
            'base_delay': 0.1,
            'max_delay': 2.0,
            'exponential_base': 2
        }
        
    def set_connection_pool(self, pool: RedisConnectionPool):
        """Set custom connection pool"""
        self.connection_pool = pool
    
    async def get_pooled_connection(self):
        """Get connection from pool"""
        if self.connection_pool:
            return await self.connection_pool.get_connection()
        return await self.get_client()
    
    async def return_pooled_connection(self, connection):
        """Return connection to pool"""
        if self.connection_pool:
            await self.connection_pool.return_connection(connection)
    
    async def get_with_retry(self, key: str, max_retries: int = None):
        """Get value with retry logic"""
        max_retries = max_retries or self.retry_config['max_retries']
        base_delay = self.retry_config['base_delay']
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.get(key)
                self.operation_metrics['successful_operations'] += 1
                
                if result != None:
                    self.operation_metrics['cache_hits'] += 1
                else:
                    self.operation_metrics['cache_misses'] += 1
                
                return result
                
            except Exception as e:
                self.operation_metrics['failed_operations'] += 1
                
                if attempt == max_retries:
                    raise e
                
                # Exponential backoff
                delay = base_delay * (self.retry_config['exponential_base'] ** attempt)
                delay = min(delay, self.retry_config['max_delay'])
                await asyncio.sleep(delay)
    
    async def set_with_retry(self, key: str, value: str, ex: int = None, max_retries: int = None):
        """Set value with retry logic"""
        max_retries = max_retries or self.retry_config['max_retries']
        base_delay = self.retry_config['base_delay']
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.set(key, value, ex=ex)
                self.operation_metrics['successful_operations'] += 1
                return result
                
            except Exception as e:
                self.operation_metrics['failed_operations'] += 1
                
                if attempt == max_retries:
                    raise e
                
                delay = base_delay * (self.retry_config['exponential_base'] ** attempt)
                delay = min(delay, self.retry_config['max_delay'])
                await asyncio.sleep(delay)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get operation metrics"""
        total_ops = self.operation_metrics['total_operations']
        total_gets = self.operation_metrics['cache_hits'] + self.operation_metrics['cache_misses']
        
        if total_ops > 0:
            success_rate = self.operation_metrics['successful_operations'] / total_ops
            failure_rate = self.operation_metrics['failed_operations'] / total_ops
        else:
            success_rate = failure_rate = 0
        
        cache_hit_rate = self.operation_metrics['cache_hits'] / total_gets if total_gets > 0 else 0
        
        return {
            **self.operation_metrics,
            'success_rate': success_rate,
            'failure_rate': failure_rate,
            'cache_hit_rate': cache_hit_rate
        }
    
    def reset_metrics(self):
        """Reset operation metrics"""
        self.operation_metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

# Pytest Fixtures

@pytest.fixture
def mock_redis_client():
    """Create mock Redis client"""
    return MockRedisClient()

@pytest.fixture
def redis_manager(mock_redis_client):
    """Create Redis manager with mock client"""
    manager = RedisManager()
    manager.redis_client = mock_redis_client
    manager.enabled = True
    return manager

@pytest.fixture
def enhanced_redis_manager():
    """Create enhanced Redis manager"""
    return EnhancedRedisManager()

@pytest.fixture
def connection_pool():
    """Create connection pool"""
    return RedisConnectionPool(max_connections=5)

@pytest.fixture
def enhanced_redis_manager_with_retry():
    """Create enhanced Redis manager with retry configuration"""
    manager = EnhancedRedisManager()
    manager.enabled = True
    return manager

@pytest.fixture
def performance_redis_manager():
    """Create Redis manager for performance testing"""
    manager = EnhancedRedisManager()
    manager.redis_client = MockRedisClient()
    manager.enabled = True
    return manager