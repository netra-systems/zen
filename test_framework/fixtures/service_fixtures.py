"""
Service fixtures for testing.

Provides pytest fixtures for service components including databases, 
caches, message queues, and external API clients.
"""

import asyncio
import logging
from typing import AsyncIterator, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE SERVICE FIXTURES
# =============================================================================

@pytest.fixture
async def postgres_service():
    """PostgreSQL database service fixture."""
    # Mock: Database service isolation for transaction testing without real database dependency
    mock_service = AsyncMock()
    mock_service.connection = AsyncMock()
    mock_service.execute = AsyncMock(return_value=[])
    mock_service.fetchone = AsyncMock(return_value=None)
    mock_service.fetchall = AsyncMock(return_value=[])
    mock_service.fetchval = AsyncMock(return_value=None)
    mock_service.transaction = AsyncMock()
    mock_service.close = AsyncMock()
    
    # Context manager support for connections
    mock_service.__aenter__ = AsyncMock(return_value=mock_service)
    mock_service.__aexit__ = AsyncMock(return_value=None)
    
    yield mock_service
    await mock_service.close()


@pytest.fixture 
async def clickhouse_service():
    """ClickHouse analytics service fixture."""
    # Mock: Analytics service isolation for query testing without real ClickHouse dependency
    mock_service = AsyncMock()
    mock_service.execute = AsyncMock(return_value=[])
    mock_service.insert = AsyncMock(return_value=True)
    mock_service.query = AsyncMock(return_value=[])
    mock_service.close = AsyncMock()
    
    # ClickHouse-specific methods
    mock_service.create_table = AsyncMock(return_value=True)
    mock_service.drop_table = AsyncMock(return_value=True)
    mock_service.optimize_table = AsyncMock(return_value=True)
    
    yield mock_service
    await mock_service.close()


# =============================================================================
# CACHE SERVICE FIXTURES  
# =============================================================================

@pytest.fixture
async def redis_service():
    """Redis cache service fixture."""
    # Mock: Cache service isolation for testing without real Redis dependency
    mock_service = AsyncMock()
    
    # Redis basic operations
    mock_service.get = AsyncMock(return_value=None)
    mock_service.set = AsyncMock(return_value=True)
    mock_service.delete = AsyncMock(return_value=True)
    mock_service.exists = AsyncMock(return_value=False)
    mock_service.expire = AsyncMock(return_value=True)
    mock_service.ttl = AsyncMock(return_value=-1)
    
    # Redis advanced operations
    mock_service.hget = AsyncMock(return_value=None)
    mock_service.hset = AsyncMock(return_value=True)
    mock_service.hdel = AsyncMock(return_value=True)
    mock_service.hgetall = AsyncMock(return_value={})
    mock_service.sadd = AsyncMock(return_value=True)
    mock_service.smembers = AsyncMock(return_value=set())
    mock_service.zadd = AsyncMock(return_value=True)
    mock_service.zrange = AsyncMock(return_value=[])
    
    # Redis connection management
    mock_service.ping = AsyncMock(return_value=True)
    mock_service.close = AsyncMock()
    mock_service.flushdb = AsyncMock(return_value=True)
    mock_service.info = AsyncMock(return_value={"redis_version": "7.0.0"})
    
    yield mock_service
    await mock_service.close()


# =============================================================================
# MESSAGE QUEUE SERVICE FIXTURES
# =============================================================================

@pytest.fixture
async def message_queue_service():
    """Message queue service fixture."""
    # Mock: Message queue isolation for event testing without real queue dependency
    mock_service = AsyncMock()
    
    # Queue operations
    mock_service.publish = AsyncMock(return_value=True)
    mock_service.subscribe = AsyncMock()
    mock_service.unsubscribe = AsyncMock(return_value=True)
    mock_service.consume = AsyncMock()
    mock_service.ack = AsyncMock(return_value=True)
    mock_service.nack = AsyncMock(return_value=True)
    
    # Queue management
    mock_service.create_queue = AsyncMock(return_value=True)
    mock_service.delete_queue = AsyncMock(return_value=True)
    mock_service.purge_queue = AsyncMock(return_value=True)
    mock_service.queue_length = AsyncMock(return_value=0)
    
    # Connection management
    mock_service.connect = AsyncMock()
    mock_service.disconnect = AsyncMock()
    mock_service.is_connected = AsyncMock(return_value=True)
    
    yield mock_service
    await mock_service.disconnect()


# =============================================================================
# EXTERNAL API SERVICE FIXTURES
# =============================================================================

@pytest.fixture
async def llm_service():
    """LLM API service fixture."""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock_service = AsyncMock()
    
    # LLM operations
    mock_service.generate = AsyncMock(return_value={
        "content": "Test LLM response",
        "model": "test-model",
        "tokens_used": 50,
        "cost": 0.001,
        "finish_reason": "stop"
    })
    
    mock_service.chat = AsyncMock(return_value={
        "messages": [{"role": "assistant", "content": "Test response"}],
        "model": "test-model",
        "tokens_used": 45,
        "cost": 0.0008
    })
    
    mock_service.embedding = AsyncMock(return_value={
        "embedding": [0.1, 0.2, 0.3],  # Simplified embedding vector
        "model": "text-embedding-test",
        "tokens_used": 10,
        "cost": 0.0001
    })
    
    # Model management
    mock_service.list_models = AsyncMock(return_value=["test-model-1", "test-model-2"])
    mock_service.get_model_info = AsyncMock(return_value={
        "name": "test-model",
        "max_tokens": 4000,
        "cost_per_token": 0.00002
    })
    
    # Rate limiting info
    mock_service.get_rate_limits = AsyncMock(return_value={
        "requests_per_minute": 60,
        "tokens_per_minute": 60000,
        "remaining_requests": 59,
        "remaining_tokens": 59950
    })
    
    yield mock_service


@pytest.fixture
async def auth_service():
    """Authentication service fixture."""
    # Mock: Auth service isolation for security testing without real auth provider dependency
    mock_service = AsyncMock()
    
    # Authentication operations
    mock_service.authenticate = AsyncMock(return_value={
        "user_id": "test-user-123",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "expires_in": 3600,
        "token_type": "Bearer"
    })
    
    mock_service.verify_token = AsyncMock(return_value={
        "valid": True,
        "user_id": "test-user-123",
        "email": "test@example.com",
        "roles": ["user"],
        "expires_at": "2024-12-31T23:59:59Z"
    })
    
    mock_service.refresh_token = AsyncMock(return_value={
        "access_token": "new-test-access-token",
        "expires_in": 3600
    })
    
    mock_service.logout = AsyncMock(return_value=True)
    
    # User management
    mock_service.get_user = AsyncMock(return_value={
        "id": "test-user-123", 
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["user"],
        "is_active": True
    })
    
    mock_service.create_user = AsyncMock(return_value={
        "id": "new-user-123",
        "email": "new@example.com",
        "name": "New User"
    })
    
    mock_service.update_user = AsyncMock(return_value=True)
    mock_service.delete_user = AsyncMock(return_value=True)
    
    yield mock_service


# =============================================================================
# MONITORING AND OBSERVABILITY SERVICE FIXTURES
# =============================================================================

@pytest.fixture
async def metrics_service():
    """Metrics collection service fixture."""
    # Mock: Metrics service isolation for monitoring testing without real telemetry dependency
    mock_service = AsyncMock()
    
    # Metric operations
    mock_service.counter = AsyncMock()
    mock_service.gauge = AsyncMock()
    mock_service.histogram = AsyncMock()
    mock_service.summary = AsyncMock()
    
    # Recording methods
    mock_service.increment = AsyncMock()
    mock_service.decrement = AsyncMock()
    mock_service.set_gauge = AsyncMock()
    mock_service.observe = AsyncMock()
    mock_service.time_function = AsyncMock()
    
    # Query methods
    mock_service.get_metric = AsyncMock(return_value={"value": 42, "timestamp": "2024-01-01T00:00:00Z"})
    mock_service.get_metrics = AsyncMock(return_value=[])
    mock_service.export_metrics = AsyncMock(return_value="# Mock metrics export")
    
    yield mock_service


@pytest.fixture
async def logging_service():
    """Structured logging service fixture.""" 
    # Mock: Logging service isolation for audit testing without real log aggregation dependency
    mock_service = AsyncMock()
    
    # Logging operations
    mock_service.debug = AsyncMock()
    mock_service.info = AsyncMock()
    mock_service.warning = AsyncMock()
    mock_service.error = AsyncMock()
    mock_service.critical = AsyncMock()
    
    # Structured logging
    mock_service.log_structured = AsyncMock()
    mock_service.log_event = AsyncMock()
    mock_service.log_transaction = AsyncMock()
    mock_service.log_performance = AsyncMock()
    
    # Log management
    mock_service.set_level = AsyncMock()
    mock_service.get_logs = AsyncMock(return_value=[])
    mock_service.search_logs = AsyncMock(return_value=[])
    mock_service.export_logs = AsyncMock(return_value="Mock log export")
    
    yield mock_service


# =============================================================================
# FILE STORAGE SERVICE FIXTURES  
# =============================================================================

@pytest.fixture
async def file_storage_service():
    """File storage service fixture."""
    # Mock: Storage service isolation for file testing without real cloud storage dependency
    mock_service = AsyncMock()
    
    # File operations
    mock_service.upload = AsyncMock(return_value={
        "file_id": "test-file-123",
        "url": "https://storage.example.com/test-file-123",
        "size": 1024,
        "content_type": "text/plain"
    })
    
    mock_service.download = AsyncMock(return_value=b"test file content")
    mock_service.delete = AsyncMock(return_value=True)
    mock_service.exists = AsyncMock(return_value=True)
    mock_service.get_metadata = AsyncMock(return_value={
        "size": 1024,
        "created_at": "2024-01-01T00:00:00Z",
        "content_type": "text/plain"
    })
    
    # Directory operations
    mock_service.create_directory = AsyncMock(return_value=True)
    mock_service.list_files = AsyncMock(return_value=[])
    mock_service.delete_directory = AsyncMock(return_value=True)
    
    # Bulk operations
    mock_service.upload_batch = AsyncMock(return_value=[])
    mock_service.download_batch = AsyncMock(return_value=[])
    mock_service.delete_batch = AsyncMock(return_value=True)
    
    yield mock_service


# =============================================================================
# SERVICE CONFIGURATION FIXTURES
# =============================================================================

@pytest.fixture
def service_config() -> Dict[str, Any]:
    """Common service configuration for tests."""
    return {
        "postgres": {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass",
            "pool_size": 5,
            "max_overflow": 10
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None,
            "max_connections": 10
        },
        "clickhouse": {
            "host": "localhost", 
            "port": 8123,
            "database": "test_analytics",
            "user": "test_user",
            "password": "test_pass"
        },
        "llm": {
            "provider": "test",
            "model": "test-model",
            "api_key": "test-api-key",
            "max_tokens": 4000,
            "temperature": 0.7
        },
        "auth": {
            "provider": "test",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "redirect_uri": "http://localhost/auth/callback"
        }
    }


@pytest.fixture
def service_health_check():
    """Service health check utility for tests."""
    # Mock: Health check isolation for availability testing without real service dependency
    class MockHealthChecker:
        async def check_service(self, service_name: str) -> bool:
            # Always return healthy for tests
            return True
            
        async def check_all_services(self) -> Dict[str, bool]:
            return {
                "postgres": True,
                "redis": True, 
                "clickhouse": True,
                "llm": True,
                "auth": True
            }
            
        async def wait_for_service(self, service_name: str, timeout: int = 30) -> bool:
            # Simulate waiting
            await asyncio.sleep(0.1)
            return True
    
    return MockHealthChecker()


# =============================================================================
# SERVICE LIFECYCLE FIXTURES
# =============================================================================

@pytest.fixture
async def service_lifecycle_manager():
    """Service lifecycle management for tests."""
    # Mock: Lifecycle management isolation for orchestration testing without real service dependency
    mock_manager = AsyncMock()
    
    # Lifecycle operations
    mock_manager.start_service = AsyncMock(return_value=True)
    mock_manager.stop_service = AsyncMock(return_value=True)
    mock_manager.restart_service = AsyncMock(return_value=True)
    mock_manager.scale_service = AsyncMock(return_value=True)
    
    # Status operations
    mock_manager.get_service_status = AsyncMock(return_value="running")
    mock_manager.is_service_healthy = AsyncMock(return_value=True)
    mock_manager.get_service_logs = AsyncMock(return_value=[])
    
    # Batch operations
    mock_manager.start_all_services = AsyncMock(return_value=True)
    mock_manager.stop_all_services = AsyncMock(return_value=True)
    mock_manager.get_all_service_status = AsyncMock(return_value={})
    
    yield mock_manager


# =============================================================================
# LEGACY COMPATIBILITY HELPERS REMOVED
# Use unified configuration management and app factory patterns instead
# =============================================================================


# =============================================================================
# EXPORT ALL FIXTURES
# =============================================================================

__all__ = [
    # Database fixtures
    'postgres_service',
    'clickhouse_service', 
    
    # Cache fixtures
    'redis_service',
    
    # Message queue fixtures  
    'message_queue_service',
    
    # External API fixtures
    'llm_service',
    'auth_service',
    
    # Monitoring fixtures
    'metrics_service', 
    'logging_service',
    
    # Storage fixtures
    'file_storage_service',
    
    # Configuration fixtures
    'service_config',
    'service_health_check',
    'service_lifecycle_manager',
    
    # Legacy helpers
    'create_test_app'
]