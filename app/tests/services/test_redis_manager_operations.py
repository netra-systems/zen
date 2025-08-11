"""
Comprehensive tests for Redis Manager operations and connection pooling
Tests Redis operations, connection management, pooling, failover, and performance
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
import redis.asyncio as redis

from app.redis_manager import RedisManager
from app.core.exceptions import NetraException


class MockRedisClient:
    """Mock Redis client for testing"""
    
    def __init__(self):
        self.data = {}  # In-memory storage
        self.ttls = {}  # TTL tracking
        self.connection_count = 0
        self.operation_count = 0
        self.should_fail = False
        self.failure_type = "connection"
        self.command_history = []
        
    async def ping(self):
        """Mock ping operation"""
        if self.should_fail and self.failure_type == "connection":
            raise redis.ConnectionError("Mock connection failed")
        return True
    
    async def get(self, key: str):
        """Mock get operation"""
        self.command_history.append(('get', key))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            raise redis.RedisError("Mock operation failed")
        
        # Check TTL
        if key in self.ttls and datetime.utcnow() > self.ttls[key]:
            del self.data[key]
            del self.ttls[key]
            return None
        
        return self.data.get(key)
    
    async def set(self, key: str, value: str, ex: int = None):
        """Mock set operation"""
        self.command_history.append(('set', key, value, ex))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            raise redis.RedisError("Mock set operation failed")
        
        self.data[key] = value
        
        # Set TTL if provided
        if ex:
            self.ttls[key] = datetime.utcnow() + timedelta(seconds=ex)
        
        return True
    
    async def delete(self, key: str):
        """Mock delete operation"""
        self.command_history.append(('delete', key))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            raise redis.RedisError("Mock delete operation failed")
        
        if key in self.data:
            del self.data[key]
            if key in self.ttls:
                del self.ttls[key]
            return 1
        return 0
    
    async def close(self):
        """Mock close operation"""
        self.connection_count = 0
    
    def clear_data(self):
        """Clear all mock data"""
        self.data.clear()
        self.ttls.clear()
        self.command_history.clear()
        self.operation_count = 0
    
    def set_failure_mode(self, should_fail: bool, failure_type: str = "connection"):
        """Set failure mode for testing"""
        self.should_fail = should_fail
        self.failure_type = failure_type


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
        if total_ops > 0:
            success_rate = self.operation_metrics['successful_operations'] / total_ops
            failure_rate = self.operation_metrics['failed_operations'] / total_ops
            cache_hit_rate = self.operation_metrics['cache_hits'] / (
                self.operation_metrics['cache_hits'] + self.operation_metrics['cache_misses'] + 1
            )
        else:
            success_rate = failure_rate = cache_hit_rate = 0
        
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


class TestRedisManagerOperations:
    """Test basic Redis manager operations"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client"""
        return MockRedisClient()
    
    @pytest.fixture
    def redis_manager(self, mock_redis_client):
        """Create Redis manager with mock client"""
        manager = RedisManager()
        manager.redis_client = mock_redis_client
        manager.enabled = True
        return manager
    
    @pytest.mark.asyncio
    async def test_redis_manager_initialization(self):
        """Test Redis manager initialization"""
        manager = RedisManager()
        
        # Should check enabled state
        assert hasattr(manager, 'enabled')
        assert hasattr(manager, 'redis_client')
        
        # Initially should not be connected
        assert manager.redis_client == None
    
    @pytest.mark.asyncio
    async def test_redis_connection_success(self, mock_redis_client):
        """Test successful Redis connection"""
        manager = RedisManager()
        
        with patch('redis.asyncio.Redis', return_value=mock_redis_client):
            with patch('app.redis_manager.settings') as mock_settings:
                mock_settings.redis.host = "localhost"
                mock_settings.redis.port = 6379
                mock_settings.redis.username = None
                mock_settings.redis.password = None
                
                await manager.connect()
        
        assert manager.redis_client is mock_redis_client
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """Test Redis connection failure handling"""
        manager = RedisManager()
        manager.enabled = True
        
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_client = MockRedisClient()
            mock_client.set_failure_mode(True, "connection")
            mock_redis_class.return_value = mock_client
            
            with patch('app.redis_manager.settings') as mock_settings:
                mock_settings.redis.host = "localhost"
                mock_settings.redis.port = 6379
                mock_settings.redis.username = None
                mock_settings.redis.password = None
                
                # Should handle connection failure gracefully
                await manager.connect()
                
                # Should remain None on connection failure
                assert manager.redis_client == None
    
    @pytest.mark.asyncio
    async def test_redis_get_operation(self, redis_manager, mock_redis_client):
        """Test Redis GET operation"""
        # Setup test data
        test_key = "test_key"
        test_value = "test_value"
        mock_redis_client.data[test_key] = test_value
        
        # Execute get operation
        result = await redis_manager.get(test_key)
        
        # Verify result
        assert result == test_value
        assert mock_redis_client.operation_count == 1
        assert ('get', test_key) in mock_redis_client.command_history
    
    @pytest.mark.asyncio
    async def test_redis_get_nonexistent_key(self, redis_manager, mock_redis_client):
        """Test Redis GET operation for nonexistent key"""
        result = await redis_manager.get("nonexistent_key")
        
        assert result == None
        assert mock_redis_client.operation_count == 1
    
    @pytest.mark.asyncio
    async def test_redis_set_operation(self, redis_manager, mock_redis_client):
        """Test Redis SET operation"""
        test_key = "set_test_key"
        test_value = "set_test_value"
        
        # Execute set operation
        result = await redis_manager.set(test_key, test_value)
        
        # Verify operation
        assert result == True
        assert mock_redis_client.data[test_key] == test_value
        assert mock_redis_client.operation_count == 1
        assert ('set', test_key, test_value, None) in mock_redis_client.command_history
    
    @pytest.mark.asyncio
    async def test_redis_set_with_expiration(self, redis_manager, mock_redis_client):
        """Test Redis SET operation with expiration"""
        test_key = "expire_test_key"
        test_value = "expire_test_value"
        expiration = 300  # 5 minutes
        
        # Execute set with expiration
        result = await redis_manager.set(test_key, test_value, ex=expiration)
        
        # Verify operation
        assert result == True
        assert mock_redis_client.data[test_key] == test_value
        assert test_key in mock_redis_client.ttls
        
        # Check TTL was set
        ttl = mock_redis_client.ttls[test_key]
        expected_expiry = datetime.utcnow() + timedelta(seconds=expiration)
        assert abs((ttl - expected_expiry).total_seconds()) < 1  # Within 1 second
    
    @pytest.mark.asyncio
    async def test_redis_set_backward_compatibility(self, redis_manager, mock_redis_client):
        """Test Redis SET backward compatibility with 'expire' parameter"""
        test_key = "compat_test_key"
        test_value = "compat_test_value"
        expiration = 600  # 10 minutes
        
        # Use old 'expire' parameter
        result = await redis_manager.set(test_key, test_value, expire=expiration)
        
        # Should work the same as 'ex'
        assert result == True
        assert mock_redis_client.data[test_key] == test_value
        assert test_key in mock_redis_client.ttls
    
    @pytest.mark.asyncio
    async def test_redis_delete_operation(self, redis_manager, mock_redis_client):
        """Test Redis DELETE operation"""
        test_key = "delete_test_key"
        test_value = "delete_test_value"
        
        # Setup test data
        mock_redis_client.data[test_key] = test_value
        
        # Execute delete
        result = await redis_manager.delete(test_key)
        
        # Verify deletion
        assert result == 1  # Number of keys deleted
        assert test_key not in mock_redis_client.data
        assert ('delete', test_key) in mock_redis_client.command_history
    
    @pytest.mark.asyncio
    async def test_redis_delete_nonexistent_key(self, redis_manager, mock_redis_client):
        """Test Redis DELETE operation for nonexistent key"""
        result = await redis_manager.delete("nonexistent_delete_key")
        
        assert result == 0  # No keys deleted
        assert mock_redis_client.operation_count == 1
    
    @pytest.mark.asyncio
    async def test_redis_operations_when_disabled(self):
        """Test Redis operations when service is disabled"""
        manager = RedisManager()
        manager.enabled = False
        manager.redis_client = None
        
        # All operations should return None gracefully
        assert await manager.get("test_key") == None
        assert await manager.set("test_key", "test_value") == None
        assert await manager.delete("test_key") == None
    
    @pytest.mark.asyncio
    async def test_redis_disconnect(self, redis_manager, mock_redis_client):
        """Test Redis disconnection"""
        # Initially connected
        assert redis_manager.redis_client != None
        
        # Disconnect
        await redis_manager.disconnect()
        
        # Should have called close on client
        assert mock_redis_client.connection_count == 0


class TestRedisManagerConnectionPooling:
    """Test Redis connection pooling functionality"""
    
    @pytest.fixture
    def enhanced_redis_manager(self):
        """Create enhanced Redis manager"""
        return EnhancedRedisManager()
    
    @pytest.fixture
    def connection_pool(self):
        """Create connection pool"""
        return RedisConnectionPool(max_connections=5)
    
    @pytest.mark.asyncio
    async def test_connection_pool_creation(self, enhanced_redis_manager, connection_pool):
        """Test connection pool creation and setup"""
        enhanced_redis_manager.set_connection_pool(connection_pool)
        
        assert enhanced_redis_manager.connection_pool is connection_pool
        assert connection_pool.max_connections == 5
        assert connection_pool.active_connections == 0
    
    @pytest.mark.asyncio
    async def test_connection_pool_get_connection(self, connection_pool):
        """Test getting connection from pool"""
        # Get connection
        connection = await connection_pool.get_connection()
        
        assert connection != None
        assert isinstance(connection, MockRedisClient)
        assert connection_pool.active_connections == 1
        assert connection_pool.total_connections_created == 1
    
    @pytest.mark.asyncio
    async def test_connection_pool_return_connection(self, connection_pool):
        """Test returning connection to pool"""
        # Get and return connection
        connection = await connection_pool.get_connection()
        await connection_pool.return_connection(connection)
        
        assert connection_pool.active_connections == 0
    
    @pytest.mark.asyncio
    async def test_connection_pool_max_connections(self, connection_pool):
        """Test connection pool max connections limit"""
        connections = []
        
        # Get max connections
        for i in range(connection_pool.max_connections):
            conn = await connection_pool.get_connection()
            connections.append(conn)
        
        assert connection_pool.active_connections == connection_pool.max_connections
        assert len(connections) == connection_pool.max_connections
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_usage(self, enhanced_redis_manager, connection_pool):
        """Test concurrent usage of pooled connections"""
        enhanced_redis_manager.set_connection_pool(connection_pool)
        
        async def perform_operations(operation_id):
            """Perform Redis operations using pooled connection"""
            connection = await enhanced_redis_manager.get_pooled_connection()
            
            # Perform operations
            await connection.set(f"key_{operation_id}", f"value_{operation_id}")
            result = await connection.get(f"key_{operation_id}")
            
            await enhanced_redis_manager.return_pooled_connection(connection)
            return result
        
        # Execute concurrent operations
        tasks = [perform_operations(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == 10
        assert all(f"value_{i}" in results for i in range(10))
    
    @pytest.mark.asyncio
    async def test_connection_pool_cleanup(self, connection_pool):
        """Test connection pool cleanup"""
        # Create connections
        connections = []
        for i in range(3):
            conn = await connection_pool.get_connection()
            connections.append(conn)
        
        assert connection_pool.active_connections == 3
        
        # Cleanup
        await connection_pool.close_all()
        
        assert connection_pool.active_connections == 0
        assert len(connection_pool.connections) == 0


class TestRedisManagerRetryAndFailover:
    """Test Redis retry logic and failover mechanisms"""
    
    @pytest.fixture
    def enhanced_redis_manager_with_retry(self):
        """Create enhanced Redis manager with retry configuration"""
        manager = EnhancedRedisManager()
        manager.enabled = True
        return manager
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, enhanced_redis_manager_with_retry):
        """Test retry logic on transient failures"""
        mock_client = MockRedisClient()
        enhanced_redis_manager_with_retry.redis_client = mock_client
        
        # Setup transient failure (fails first 2 attempts, succeeds on 3rd)
        attempt_count = 0
        
        async def failing_get(key):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise redis.ConnectionError("Transient connection error")
            return f"success_{key}"
        
        mock_client.get = failing_get
        
        # Execute with retry
        result = await enhanced_redis_manager_with_retry.get_with_retry("test_key")
        
        # Should succeed after retries
        assert result == "success_test_key"
        assert attempt_count == 3  # Failed twice, succeeded on third attempt
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, enhanced_redis_manager_with_retry):
        """Test behavior when retry attempts are exhausted"""
        mock_client = MockRedisClient()
        enhanced_redis_manager_with_retry.redis_client = mock_client
        
        # Setup persistent failure
        async def always_failing_get(key):
            raise redis.ConnectionError("Persistent connection error")
        
        mock_client.get = always_failing_get
        
        # Should raise exception after max retries
        with pytest.raises(redis.ConnectionError):
            await enhanced_redis_manager_with_retry.get_with_retry("test_key", max_retries=2)
        
        # Should have attempted 3 times (original + 2 retries)
        metrics = enhanced_redis_manager_with_retry.get_metrics()
        assert metrics['failed_operations'] == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, enhanced_redis_manager_with_retry):
        """Test exponential backoff timing"""
        mock_client = MockRedisClient()
        enhanced_redis_manager_with_retry.redis_client = mock_client
        
        retry_times = []
        
        async def timing_failing_get(key):
            retry_times.append(time.time())
            if len(retry_times) <= 2:  # Fail first 2 attempts
                raise redis.ConnectionError("Timed failure")
            return "success"
        
        mock_client.get = timing_failing_get
        
        start_time = time.time()
        result = await enhanced_redis_manager_with_retry.get_with_retry("test_key")
        
        # Should succeed
        assert result == "success"
        assert len(retry_times) == 3
        
        # Check exponential backoff timing
        # First retry after ~0.1s, second after ~0.2s more
        if len(retry_times) >= 3:
            first_delay = retry_times[1] - retry_times[0]
            second_delay = retry_times[2] - retry_times[1]
            
            # Allow some tolerance for timing
            assert 0.05 < first_delay < 0.15  # ~0.1s
            assert 0.15 < second_delay < 0.25  # ~0.2s
    
    @pytest.mark.asyncio
    async def test_set_operation_retry(self, enhanced_redis_manager_with_retry):
        """Test retry logic for SET operations"""
        mock_client = MockRedisClient()
        enhanced_redis_manager_with_retry.redis_client = mock_client
        
        attempt_count = 0
        
        async def failing_set(key, value, ex=None):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise redis.ConnectionError("First attempt fails")
            return True
        
        mock_client.set = failing_set
        
        # Execute set with retry
        result = await enhanced_redis_manager_with_retry.set_with_retry("test_key", "test_value")
        
        assert result == True
        assert attempt_count == 2  # Failed once, succeeded on second attempt
    
    @pytest.mark.asyncio
    async def test_failover_to_backup_strategy(self, enhanced_redis_manager_with_retry):
        """Test failover to backup caching strategy"""
        # Setup primary Redis failure
        enhanced_redis_manager_with_retry.redis_client = None  # Simulate no connection
        
        # Implement fallback strategy (in-memory cache)
        fallback_cache = {}
        
        async def fallback_get(key):
            if enhanced_redis_manager_with_retry.redis_client == None:
                return fallback_cache.get(key)
            return await enhanced_redis_manager_with_retry.get(key)
        
        async def fallback_set(key, value, ex=None):
            if enhanced_redis_manager_with_retry.redis_client == None:
                fallback_cache[key] = value
                return True
            return await enhanced_redis_manager_with_retry.set(key, value, ex=ex)
        
        # Use fallback operations
        await fallback_set("fallback_key", "fallback_value")
        result = await fallback_get("fallback_key")
        
        assert result == "fallback_value"
        assert "fallback_key" in fallback_cache


class TestRedisManagerPerformance:
    """Test Redis manager performance characteristics"""
    
    @pytest.fixture
    def performance_redis_manager(self):
        """Create Redis manager for performance testing"""
        manager = EnhancedRedisManager()
        manager.redis_client = MockRedisClient()
        manager.enabled = True
        return manager
    
    @pytest.mark.asyncio
    async def test_high_throughput_operations(self, performance_redis_manager):
        """Test high throughput Redis operations"""
        num_operations = 1000
        
        # Execute many operations concurrently
        async def perform_batch_operations():
            tasks = []
            
            # Mix of different operations
            for i in range(num_operations // 3):
                tasks.append(performance_redis_manager.set(f"key_{i}", f"value_{i}"))
                
            for i in range(num_operations // 3):
                tasks.append(performance_redis_manager.get(f"key_{i}"))
                
            for i in range(num_operations // 3):
                tasks.append(performance_redis_manager.delete(f"delete_key_{i}"))
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Measure performance
        start_time = time.time()
        results = await perform_batch_operations()
        end_time = time.time()
        
        execution_time = end_time - start_time
        throughput = len(results) / execution_time
        
        # Should handle high throughput
        assert execution_time < 2.0  # Complete within 2 seconds
        assert throughput > 500  # At least 500 ops/second
        assert len([r for r in results if isinstance(r, Exception)]) == 0  # No errors
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_redis_manager):
        """Test memory usage under high load"""
        import tracemalloc
        
        # Start memory tracking
        tracemalloc.start()
        
        # Create large dataset
        large_data_size = 100
        large_value = "x" * 1000  # 1KB per value
        
        # Store large dataset
        tasks = []
        for i in range(large_data_size):
            tasks.append(performance_redis_manager.set(f"large_key_{i}", large_value))
        
        await asyncio.gather(*tasks)
        
        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should use reasonable memory (less than 50MB for this test)
        assert peak < 50 * 1024 * 1024  # 50MB
    
    @pytest.mark.asyncio
    async def test_operation_latency_measurement(self, performance_redis_manager):
        """Test operation latency measurement"""
        latencies = []
        
        # Measure latency for multiple operations
        for i in range(50):
            start_time = time.time()
            await performance_redis_manager.set(f"latency_key_{i}", f"latency_value_{i}")
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)
        
        # Analyze latencies
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        # Should have low latency for mock operations
        assert avg_latency < 10.0  # Average < 10ms
        assert max_latency < 50.0  # Max < 50ms
        assert min_latency >= 0.0   # Non-negative
    
    def test_metrics_collection_accuracy(self, performance_redis_manager):
        """Test accuracy of collected metrics"""
        # Reset metrics
        performance_redis_manager.reset_metrics()
        
        # Perform known operations
        asyncio.run(performance_redis_manager.set("metric_key_1", "value_1"))
        asyncio.run(performance_redis_manager.get("metric_key_1"))  # Hit
        asyncio.run(performance_redis_manager.get("nonexistent"))   # Miss
        
        # Check metrics
        metrics = performance_redis_manager.get_metrics()
        
        assert metrics['successful_operations'] == 3
        assert metrics['cache_hits'] == 1
        assert metrics['cache_misses'] == 1
        assert metrics['failed_operations'] == 0
        
        # Calculate rates
        expected_hit_rate = 1 / 2  # 1 hit out of 2 get operations
        assert abs(metrics['cache_hit_rate'] - expected_hit_rate) < 0.01
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_safety(self, performance_redis_manager):
        """Test thread safety of concurrent connections"""
        connection_pool = RedisConnectionPool(max_connections=3)
        performance_redis_manager.set_connection_pool(connection_pool)
        
        concurrent_operations = 20
        operation_results = []
        
        async def concurrent_operation(op_id):
            try:
                connection = await performance_redis_manager.get_pooled_connection()
                
                # Perform operations
                await connection.set(f"concurrent_key_{op_id}", f"concurrent_value_{op_id}")
                result = await connection.get(f"concurrent_key_{op_id}")
                
                await performance_redis_manager.return_pooled_connection(connection)
                return result
                
            except Exception as e:
                return e
        
        # Execute concurrent operations
        tasks = [concurrent_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == concurrent_operations
        
        # Verify no connection leaks
        assert connection_pool.active_connections <= connection_pool.max_connections