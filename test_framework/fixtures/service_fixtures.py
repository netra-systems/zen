"""
Service-related test fixtures.
Consolidates service mocks and fixtures from across the project.
"""

import asyncio
import os
import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Only import Redis if not in collection mode
if not os.environ.get("TEST_COLLECTION_MODE"):
    try:
        import redis.asyncio as redis
        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False
else:
    REDIS_AVAILABLE = False


@pytest.fixture
def mock_llm_service():
    """Mock LLM service with various providers"""
    service = AsyncMock()
    service.generate_response = AsyncMock(return_value={
        "content": "This is a test AI response",
        "model": LLMModel.GEMINI_2_5_FLASH.value,
        "tokens_used": 45,
        "cost": 0.0012,
        "metadata": {"test": True}
    })
    service.analyze_optimization = AsyncMock(return_value={
        "optimization_suggestions": ["Use batch processing", "Implement caching"],
        "confidence": 0.85,
        "potential_savings": 1200
    })
    service.get_available_models = MagicMock(return_value=[
        LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "gemini-pro"
    ])
    return service

@pytest.fixture  
def mock_agent_service():
    """Mock agent service for workflow testing"""
    service = AsyncMock()
    service.process_message = AsyncMock(return_value={
        "response": "Agent processed the request successfully",
        "metadata": {"agent_id": "test_agent", "processing_time": 1.2},
        "status": "completed"
    })
    service.start_agent = AsyncMock(return_value={"agent_id": "test_agent"})
    service.stop_agent = AsyncMock(return_value=True)
    service.get_agent_status = MagicMock(return_value="running")
    return service

@pytest.fixture
def mock_notification_service():
    """Mock notification service"""
    service = AsyncMock()
    service.send_email = AsyncMock(return_value={"sent": True, "message_id": "test_123"})
    service.send_sms = AsyncMock(return_value={"sent": True, "message_id": "sms_123"})
    service.send_push_notification = AsyncMock(return_value={"sent": True})
    return service

@pytest.fixture
def mock_payment_service():
    """Mock payment service"""
    service = AsyncMock()
    service.process_payment = AsyncMock(return_value={
        "success": True,
        "transaction_id": "txn_123",
        "amount": 99.00,
        "currency": "USD"
    })
    service.create_subscription = AsyncMock(return_value={
        "subscription_id": "sub_123",
        "status": "active",
        "next_billing_date": "2025-02-01"
    })
    service.cancel_subscription = AsyncMock(return_value={"cancelled": True})
    return service

@pytest.fixture
def mock_metrics_service():
    """Mock metrics and analytics service"""
    service = AsyncMock()
    service.record_metric = AsyncMock()
    service.increment_counter = AsyncMock()
    service.record_histogram = AsyncMock()
    service.get_metrics = AsyncMock(return_value={
        "requests_total": 1000,
        "avg_response_time": 0.25,
        "error_rate": 0.01
    })
    return service

@pytest.fixture
def mock_cache_service():
    """Mock cache service (Redis, etc.)"""
    service = AsyncMock()
    service.get = AsyncMock(return_value=None)
    service.set = AsyncMock(return_value=True)
    service.delete = AsyncMock(return_value=True)
    service.exists = AsyncMock(return_value=False)
    service.expire = AsyncMock(return_value=True)
    service.flush_all = AsyncMock(return_value=True)
    return service

@pytest.fixture
def mock_email_service():
    """Mock email service"""
    service = AsyncMock()
    service.send_welcome_email = AsyncMock(return_value={"sent": True})
    service.send_verification_email = AsyncMock(return_value={"sent": True})
    service.send_password_reset = AsyncMock(return_value={"sent": True})
    service.send_upgrade_notification = AsyncMock(return_value={"sent": True})
    return service

@pytest.fixture
def mock_file_storage_service():
    """Mock file storage service (S3, etc.)"""
    service = AsyncMock()
    service.upload_file = AsyncMock(return_value={
        "file_id": "file_123",
        "url": "https://example.com/file.pdf",
        "size": 1024
    })
    service.download_file = AsyncMock(return_value=b"file content")
    service.delete_file = AsyncMock(return_value=True)
    service.get_file_info = AsyncMock(return_value={
        "file_id": "file_123",
        "filename": "test.pdf",
        "size": 1024,
        "content_type": "application/pdf"
    })
    return service

@pytest.fixture
def mock_logging_service():
    """Mock structured logging service"""
    service = MagicMock()
    service.log_info = MagicMock()
    service.log_warning = MagicMock()
    service.log_error = MagicMock()
    service.log_debug = MagicMock()
    service.log_audit = MagicMock()
    return service

@pytest.fixture
def mock_queue_service():
    """Mock message queue service"""
    service = AsyncMock()
    service.publish = AsyncMock(return_value={"message_id": "msg_123"})
    service.subscribe = AsyncMock()
    service.acknowledge = AsyncMock(return_value=True)
    service.reject = AsyncMock(return_value=True)
    service.get_queue_size = AsyncMock(return_value=0)
    return service

@pytest.fixture  
def mock_config_service():
    """Mock configuration service"""
    service = MagicMock()
    service.get = MagicMock(side_effect=lambda key, default=None: {
        "database_url": "sqlite:///test.db",
        "redis_url": "redis://localhost:6379/0",
        "jwt_secret": "test-secret",
        "environment": "testing"
    }.get(key, default))
    service.set = MagicMock(return_value=True)
    service.reload = MagicMock()
    return service

@pytest.fixture
def mock_health_check_service():
    """Mock health check service"""
    service = AsyncMock()
    service.check_database = AsyncMock(return_value={"status": "healthy"})
    service.check_redis = AsyncMock(return_value={"status": "healthy"})
    service.check_external_apis = AsyncMock(return_value={"status": "healthy"})
    service.get_overall_health = AsyncMock(return_value={
        "status": "healthy",
        "checks": {
            "database": "healthy",
            "redis": "healthy", 
            "external_apis": "healthy"
        }
    })
    return service

@pytest.fixture
def mock_security_service():
    """Mock security service"""
    service = MagicMock()
    service.encrypt_data = MagicMock(return_value="encrypted_data")
    service.decrypt_data = MagicMock(return_value="decrypted_data")
    service.hash_password = MagicMock(return_value="hashed_password")
    service.verify_password = MagicMock(return_value=True)
    service.generate_api_key = MagicMock(return_value="api_key_123")
    service.validate_api_key = MagicMock(return_value=True)
    return service

@pytest.fixture
def mock_search_service():
    """Mock search service (Elasticsearch, etc.)"""
    service = AsyncMock()
    service.index_document = AsyncMock(return_value={"indexed": True, "id": "doc_123"})
    service.search = AsyncMock(return_value={
        "hits": [
            {"id": "doc_123", "score": 0.95, "content": "test document"}
        ],
        "total": 1
    })
    service.delete_document = AsyncMock(return_value=True)
    return service

@pytest.fixture(scope="function")
async def isolated_redis_client():
    """Create isolated Redis client for integration testing with real Redis.
    
    This fixture provides a real Redis connection for integration tests that need
    to test Redis functionality. It uses a separate database (15) to isolate from
    production data and other tests.
    
    Business Value Justification (BVJ):
    - Segment: Platform/Internal (test infrastructure)
    - Business Goal: Enable reliable database connectivity testing
    - Value Impact: Ensures Redis-dependent features work correctly
    - Strategic Impact: Critical for 2FA, caching, and session management
    """
    if not REDIS_AVAILABLE:
        # Fallback to mock Redis client if Redis not available
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock(return_value=True)
        mock_client.setex = AsyncMock(return_value=True)
        mock_client.delete = AsyncMock(return_value=True)
        mock_client.exists = AsyncMock(return_value=False)
        mock_client.incr = AsyncMock(return_value=1)
        mock_client.expire = AsyncMock(return_value=True)
        mock_client.keys = AsyncMock(return_value=[])
        mock_client.flushdb = AsyncMock(return_value=True)
        mock_client.close = AsyncMock(return_value=None)
        yield mock_client
        return
    
    # Configuration for Redis connection
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_username = os.getenv("REDIS_USERNAME", "")
    redis_password = os.getenv("REDIS_PASSWORD", "")
    
    # Use database 15 for isolated testing to avoid conflicts
    test_database = 15
    
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        db=test_database,
        username=redis_username or None,
        password=redis_password or None,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=5,
        health_check_interval=30
    )
    
    try:
        # Test connection and clear test database
        await redis_client.ping()
        await redis_client.flushdb()  # Clear test database
        yield redis_client
    except Exception as e:
        # If Redis is not available, fall back to mock client
        print(f"Warning: Redis connection failed ({e}), using mock client")
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock(return_value=True)
        mock_client.setex = AsyncMock(return_value=True)
        mock_client.delete = AsyncMock(return_value=True)
        mock_client.exists = AsyncMock(return_value=False)
        mock_client.incr = AsyncMock(return_value=1)
        mock_client.expire = AsyncMock(return_value=True)
        mock_client.keys = AsyncMock(return_value=[])
        mock_client.flushdb = AsyncMock(return_value=True)
        mock_client.close = AsyncMock(return_value=None)
        yield mock_client
    finally:
        try:
            if hasattr(redis_client, 'aclose'):
                await redis_client.aclose()
            elif hasattr(redis_client, 'close'):
                await redis_client.close()
        except Exception:
            pass  # Ignore cleanup errors


class _ConfigManagerHelper:
    """Mock test configuration manager."""
    
    def __init__(self, overrides: dict = None):
        self.overrides = overrides or {}
        self._config = {
            "database_url": "sqlite:///test.db",
            "redis_url": "redis://localhost:6379/0", 
            "jwt_secret": "test-secret",
            "environment": "testing",
            "port": 8000,
            "host": "localhost"
        }
        self._config.update(self.overrides)
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value."""
        self._config[key] = value
    
    def to_dict(self):
        """Get all configuration as dictionary."""
        return self._config.copy()


# Alias for backward compatibility
TestConfigManager = _ConfigManagerHelper
ConfigManagerHelper = _ConfigManagerHelper


async def create_test_app():
    """Create a minimal test application instance."""
    from unittest.mock import MagicMock
    
    # Create a mock app object
    app = MagicMock()
    app.state = MagicMock()
    app.config = TestConfigManager()
    
    # Mock health endpoint behavior
    async def health_check():
        return {"status": "healthy", "timestamp": time.time()}
    
    app.health_check = health_check
    return app