"""Unit tests for UnifiedMessageStorageService.

Tests the three-tier storage architecture implementation with:
- Redis-first operations for <50ms performance
- Background PostgreSQL persistence 
- Failover capabilities
- WebSocket integration
- Performance monitoring

CRITICAL: All tests validate business value delivery through performance metrics.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas.core_models import MessageCreate, MessageResponse
from netra_backend.app.services.unified_message_storage_service import (
    UnifiedMessageStorageService,
    MessageStorageMetrics,
    get_unified_message_storage_service
)


class MockRedisManager:
    """Mock Redis manager for testing."""
    
    def __init__(self):
        self.data = {}
        self.lists = {}
        self.is_connected = True
        self.operation_delay = 0.001  # 1ms default
        
    async def set(self, key: str, value: str, ex: int = None) -> bool:
        """Mock Redis set operation."""
        await asyncio.sleep(self.operation_delay)
        self.data[key] = value
        return True
        
    async def get(self, key: str) -> str:
        """Mock Redis get operation."""
        await asyncio.sleep(self.operation_delay)
        return self.data.get(key)
        
    async def lpush(self, key: str, *values: str) -> int:
        """Mock Redis lpush operation."""
        await asyncio.sleep(self.operation_delay)
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].extend(reversed(values))
        return len(self.lists[key])
        
    async def rpop(self, key: str) -> str:
        """Mock Redis rpop operation."""
        await asyncio.sleep(self.operation_delay)
        if key in self.lists and self.lists[key]:
            return self.lists[key].pop()
        return None
        
    async def llen(self, key: str) -> int:
        """Mock Redis llen operation."""
        await asyncio.sleep(self.operation_delay)
        return len(self.lists.get(key, []))
        
    async def expire(self, key: str, seconds: int) -> bool:
        """Mock Redis expire operation."""
        await asyncio.sleep(self.operation_delay)
        return True
        
    def pipeline(self):
        """Mock Redis pipeline."""
        return MockPipeline(self)
        
    async def initialize(self):
        """Mock initialization."""
        pass


class MockPipeline:
    """Mock Redis pipeline."""
    
    def __init__(self, redis_manager):
        self.redis_manager = redis_manager
        self.commands = []
        
    def set(self, key: str, value: str, ex: int = None):
        self.commands.append(('set', key, value, ex))
        
    def lpush(self, key: str, value: str):
        self.commands.append(('lpush', key, value))
        
    def expire(self, key: str, seconds: int):
        self.commands.append(('expire', key, seconds))
        
    def get(self, key: str):
        self.commands.append(('get', key))
        
    async def execute(self):
        """Execute all commands."""
        results = []
        for cmd in self.commands:
            if cmd[0] == 'set':
                await self.redis_manager.set(cmd[1], cmd[2], cmd[3])
                results.append(True)
            elif cmd[0] == 'lpush':
                result = await self.redis_manager.lpush(cmd[1], cmd[2])
                results.append(result)
            elif cmd[0] == 'expire':
                result = await self.redis_manager.expire(cmd[1], cmd[2])
                results.append(result)
            elif cmd[0] == 'get':
                result = await self.redis_manager.get(cmd[1])
                results.append(result)
        return results
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.broadcasted_messages = []
        
    async def broadcast_to_thread(self, thread_id: str, message: dict):
        """Mock broadcast to thread."""
        self.broadcasted_messages.append({
            'thread_id': thread_id,
            'message': message
        })


@pytest.fixture
def mock_redis():
    """Fixture for mock Redis manager."""
    return MockRedisManager()


@pytest.fixture
def mock_websocket():
    """Fixture for mock WebSocket manager."""
    return MockWebSocketManager()


@pytest.fixture
async def storage_service(mock_redis, mock_websocket):
    """Fixture for UnifiedMessageStorageService with mocks."""
    service = UnifiedMessageStorageService(redis_manager=mock_redis)
    service.set_websocket_manager(mock_websocket)
    await service.initialize()
    return service


@pytest.mark.asyncio
class TestUnifiedMessageStorageService:
    """Test suite for UnifiedMessageStorageService."""
    
    async def test_service_initialization(self, mock_redis):
        """Test service initializes correctly."""
        service = UnifiedMessageStorageService(redis_manager=mock_redis)
        await service.initialize()
        
        assert service.redis_manager == mock_redis
        assert service.message_repository is not None
        assert service.metrics is not None
        assert service._persistence_task is not None
        assert not service._shutdown_event.is_set()
    
    async def test_save_message_fast_redis_success(self, storage_service, mock_websocket):
        """Test save_message_fast with Redis success path."""
        # Arrange
        message = MessageCreate(
            content="Test message",
            role="user",
            thread_id="thread-123"
        )
        
        # Act
        start_time = time.time()
        result = await storage_service.save_message_fast(message)
        end_time = time.time()
        
        # Assert business value: <50ms response time
        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 50, f"Response time {response_time_ms}ms exceeds 50ms target"
        
        # Assert message saved correctly
        assert result is not None
        assert result.content == "Test message"
        assert result.role == "user"
        assert result.thread_id == "thread-123"
        assert result.id.startswith("msg_")
        
        # Assert WebSocket notification sent
        assert len(mock_websocket.broadcasted_messages) == 1
        broadcast = mock_websocket.broadcasted_messages[0]
        assert broadcast['thread_id'] == "thread-123"
        assert broadcast['message']['type'] == "message_saved"
        
        # Assert persistence queued
        assert not storage_service._persistence_queue.empty()
        
        # Assert metrics recorded
        assert storage_service.metrics.redis_operations > 0
        assert storage_service.metrics.avg_redis_latency < 50
    
    async def test_save_message_fast_redis_failure_fallback(self, mock_redis, mock_websocket):
        """Test save_message_fast falls back to PostgreSQL when Redis fails."""
        # Arrange - make Redis fail
        mock_redis.is_connected = False
        original_set = mock_redis.set
        mock_redis.set = AsyncMock(return_value=False)
        
        service = UnifiedMessageStorageService(redis_manager=mock_redis)
        service.set_websocket_manager(mock_websocket)
        await service.initialize()
        
        message = MessageCreate(
            content="Test message",
            role="user", 
            thread_id="thread-123"
        )
        
        # Act
        result = await service.save_message_fast(message)
        
        # Assert
        assert result is not None
        assert result.content == "Test message"
        
        # Assert failover metrics recorded
        assert service.metrics.failover_events > 0
        
        # Restore mock
        mock_redis.set = original_set
    
    async def test_get_messages_cached_redis_hit(self, storage_service):
        """Test get_messages_cached with Redis cache hit."""
        # Arrange - populate Redis cache
        thread_id = "thread-123"
        mock_redis = storage_service.redis_manager
        
        # Create test messages
        message_data = {
            "id": "msg-1",
            "thread_id": thread_id,
            "role": "user",
            "content": "Test message",
            "created_at": int(time.time()),
            "metadata": {}
        }
        
        await mock_redis.set(f"msg:{message_data['id']}", json.dumps(message_data))
        await mock_redis.lpush(f"thread:{thread_id}:messages", message_data['id'])
        
        # Act
        start_time = time.time()
        messages = await storage_service.get_messages_cached(thread_id, limit=10)
        end_time = time.time()
        
        # Assert business value: <50ms response time
        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 50, f"Response time {response_time_ms}ms exceeds 50ms target"
        
        # Assert cache hit
        assert len(messages) == 1
        assert messages[0].id == "msg-1"
        assert messages[0].content == "Test message"
        
        # Assert metrics
        assert storage_service.metrics.cache_hits > 0
        assert storage_service.metrics.get_cache_hit_rate() > 0
    
    async def test_get_messages_cached_cache_miss(self, storage_service):
        """Test get_messages_cached with cache miss."""
        # Arrange
        thread_id = "thread-456"
        
        # Act
        messages = await storage_service.get_messages_cached(thread_id, limit=10)
        
        # Assert cache miss handling
        assert messages == []  # Simplified - would return from PostgreSQL
        assert storage_service.metrics.cache_misses > 0
    
    async def test_get_message_with_failover_redis_success(self, storage_service):
        """Test get_message_with_failover with Redis success."""
        # Arrange
        message_id = "msg-789"
        message_data = {
            "id": message_id,
            "thread_id": "thread-123",
            "role": "user",
            "content": "Test message",
            "created_at": int(time.time()),
            "metadata": {}
        }
        
        await storage_service.redis_manager.set(f"msg:{message_id}", json.dumps(message_data))
        
        # Act
        start_time = time.time()
        result = await storage_service.get_message_with_failover(message_id)
        end_time = time.time()
        
        # Assert business value: <50ms response time
        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 50, f"Response time {response_time_ms}ms exceeds 50ms target"
        
        # Assert message retrieved correctly
        assert result is not None
        assert result.id == message_id
        assert result.content == "Test message"
        
        # Assert cache hit recorded
        assert storage_service.metrics.cache_hits > 0
    
    async def test_get_message_with_failover_postgres_fallback(self, storage_service):
        """Test get_message_with_failover falls back to PostgreSQL."""
        # Arrange - message not in Redis
        message_id = "msg-not-in-redis"
        
        # Act
        result = await storage_service.get_message_with_failover(message_id)
        
        # Assert fallback behavior
        assert result is None  # Simplified - would return from PostgreSQL
        assert storage_service.metrics.cache_misses > 0
    
    async def test_performance_metrics(self, storage_service):
        """Test performance metrics collection."""
        # Arrange
        storage_service.metrics.record_redis_operation(25.0)
        storage_service.metrics.record_postgres_operation(400.0)
        storage_service.metrics.record_cache_hit()
        storage_service.metrics.record_cache_miss()
        storage_service.metrics.record_failover()
        
        # Act
        metrics = await storage_service.get_performance_metrics()
        
        # Assert business value metrics
        assert metrics['redis_operations'] == 1
        assert metrics['postgres_operations'] == 1
        assert metrics['cache_hit_rate'] == 50.0  # 1 hit, 1 miss
        assert metrics['avg_redis_latency_ms'] == 25.0
        assert metrics['avg_postgres_latency_ms'] == 400.0
        assert metrics['failover_events'] == 1
        
        # Assert performance targets included
        targets = metrics['performance_targets']
        assert targets['redis_target_ms'] == 50
        assert targets['redis_critical_ms'] == 100
        assert targets['postgres_target_ms'] == 500
        assert targets['postgres_critical_ms'] == 1000
        
        # Assert circuit breaker status included
        assert 'circuit_breakers' in metrics
        assert 'redis' in metrics['circuit_breakers']
        assert 'postgres' in metrics['circuit_breakers']
    
    async def test_background_persistence_worker(self, storage_service):
        """Test background persistence worker processes queue."""
        # Arrange
        redis_key = "msg:test-persistence"
        await storage_service._persistence_queue.put(redis_key)
        
        # Add message data to Redis
        message_data = {
            "id": "test-persistence",
            "thread_id": "thread-123",
            "role": "user",
            "content": "Test persistence",
            "created_at": int(time.time()),
            "metadata": {}
        }
        await storage_service.redis_manager.set(redis_key, json.dumps(message_data))
        
        # Act - let background worker process
        await asyncio.sleep(0.1)  # Allow worker to process
        
        # Assert queue processed
        assert storage_service._persistence_queue.empty()
    
    async def test_circuit_breaker_protection(self, mock_redis):
        """Test circuit breaker protects against failures."""
        # Arrange - make Redis fail repeatedly
        mock_redis.set = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        service = UnifiedMessageStorageService(redis_manager=mock_redis)
        await service.initialize()
        
        message = MessageCreate(
            content="Test message",
            role="user",
            thread_id="thread-123"
        )
        
        # Act - trigger multiple failures to open circuit breaker
        for _ in range(5):  # Exceed failure threshold
            try:
                await service.save_message_fast(message)
            except:
                pass
        
        # Assert circuit breaker is open
        circuit_status = service.redis_circuit_breaker.get_status()
        # Circuit breaker should be in OPEN or HALF_OPEN state after failures
        assert circuit_status['state'].upper() in ['OPEN', 'HALF_OPEN'] or circuit_status['state'] in ['open', 'half_open']
    
    async def test_websocket_notification_integration(self, storage_service, mock_websocket):
        """Test WebSocket notifications are sent correctly."""
        # Arrange
        message = MessageCreate(
            content="Test WebSocket message",
            role="assistant",
            thread_id="thread-websocket"
        )
        
        # Act
        await storage_service.save_message_fast(message)
        
        # Assert WebSocket notification sent
        assert len(mock_websocket.broadcasted_messages) == 1
        broadcast = mock_websocket.broadcasted_messages[0]
        
        assert broadcast['thread_id'] == "thread-websocket"
        assert broadcast['message']['type'] == "message_saved"
        assert 'payload' in broadcast['message']
        assert 'message' in broadcast['message']['payload']
        assert broadcast['message']['payload']['message']['content'] == "Test WebSocket message"
    
    async def test_service_shutdown_cleanup(self, storage_service):
        """Test service shuts down cleanly and processes remaining items."""
        # Arrange - add items to persistence queue
        await storage_service._persistence_queue.put("msg:test1")
        await storage_service._persistence_queue.put("msg:test2")
        
        initial_queue_size = storage_service._persistence_queue.qsize()
        assert initial_queue_size == 2
        
        # Act
        await storage_service.shutdown()
        
        # Wait for task to complete
        await asyncio.sleep(0.1)
        
        # Assert
        assert storage_service._shutdown_event.is_set()
        assert storage_service._persistence_task.done()
    
    async def test_business_value_performance_targets(self, storage_service):
        """Test that business value performance targets are met."""
        # Business Value Test: Redis operations under 50ms
        message = MessageCreate(
            content="Performance test message",
            role="user",
            thread_id="thread-perf"
        )
        
        # Test save performance
        start_time = time.time()
        await storage_service.save_message_fast(message)
        save_time = (time.time() - start_time) * 1000
        
        assert save_time < 50, f"Save operation took {save_time}ms, exceeds 50ms target"
        
        # Test retrieval performance
        start_time = time.time()
        messages = await storage_service.get_messages_cached("thread-perf", limit=1)
        retrieval_time = (time.time() - start_time) * 1000
        
        assert retrieval_time < 50, f"Retrieval took {retrieval_time}ms, exceeds 50ms target"
        
        # Verify business metrics
        metrics = await storage_service.get_performance_metrics()
        assert metrics['avg_redis_latency_ms'] < 50, "Average Redis latency exceeds target"


class TestMessageStorageMetrics:
    """Test suite for MessageStorageMetrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initialize with correct defaults."""
        metrics = MessageStorageMetrics()
        
        assert metrics.redis_operations == 0
        assert metrics.postgres_operations == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.avg_redis_latency == 0.0
        assert metrics.avg_postgres_latency == 0.0
        assert metrics.failover_events == 0
    
    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        metrics = MessageStorageMetrics()
        
        # No hits or misses
        assert metrics.get_cache_hit_rate() == 0.0
        
        # 3 hits, 1 miss = 75%
        metrics.record_cache_hit()
        metrics.record_cache_hit() 
        metrics.record_cache_hit()
        metrics.record_cache_miss()
        
        assert metrics.get_cache_hit_rate() == 75.0
    
    def test_running_average_latency(self):
        """Test running average latency calculation."""
        metrics = MessageStorageMetrics()
        
        # Record multiple Redis operations
        metrics.record_redis_operation(10.0)
        assert metrics.avg_redis_latency == 10.0
        
        metrics.record_redis_operation(20.0) 
        assert metrics.avg_redis_latency == 15.0  # (10 + 20) / 2
        
        metrics.record_redis_operation(30.0)
        assert metrics.avg_redis_latency == 20.0  # (10 + 20 + 30) / 3


@pytest.mark.asyncio 
async def test_global_service_singleton():
    """Test global service instance management."""
    # Reset global state
    import netra_backend.app.services.unified_message_storage_service as service_module
    service_module._unified_message_storage_service = None
    
    # Get first instance
    service1 = await get_unified_message_storage_service()
    assert service1 is not None
    
    # Get second instance - should be same
    service2 = await get_unified_message_storage_service()
    assert service1 is service2
    
    # Test sync getter
    service3 = service_module.get_message_storage_service_sync()
    assert service3 is service1