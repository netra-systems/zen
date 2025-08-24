"""
Unified mock objects package.
Consolidates mock implementations from across the project.

This is the single source of truth for all mock implementations across Netra.
Eliminates duplicate mock utilities as per CLAUDE.md Section 2.1 SSOT requirements.
"""

# Import all mock categories
from test_framework.mocks.websocket_mocks import *
from test_framework.mocks.service_mocks import *
from test_framework.mocks.database_mocks import *
from test_framework.mocks.http_mocks import *
from test_framework.mocks.llm_mocks import *

# Explicit exports for clarity and IDE support
__all__ = [
    # WebSocket Mocks
    "MockWebSocket",
    "MockWebSocketManager", 
    "MockWebSocketConnectionManager",
    "MockWebSocketBroadcaster",
    "MockHighVolumeWebSocketServer",
    
    # Service Mocks
    "MockClickHouseService",
    "MockRedisService",
    "MockLLMService",
    "MockAgentService",
    "MockWebSocketBroadcaster",
    "MockNotificationService",
    "MockPaymentService",
    "MockHealthCheckService",
    
    # Quality Gate Mock Helpers
    "setup_redis_mock_with_error",
    "setup_redis_mock_with_large_cache", 
    "setup_quality_service_with_redis_error",
    "setup_quality_service_with_large_cache",
    "setup_validation_error_patch",
    "setup_threshold_error_patch",
    "setup_slow_validation_mock",
    "create_metrics_storage_error",
    
    # Database Mocks
    "MockDatabaseSession",
    "MockAsyncDatabaseFactory",
    "MockPostgreSQLConnection",
    "MockClickHouseConnection",
    "MockDatabaseManager",
    "MockRepositoryBase",
    
    # HTTP/API Mocks
    "MockHttpClient",
    "MockResponse",
    "MockTimeoutException",
    "MockServiceProcess",
    "MockServicesManager",
    "MockE2EServiceOrchestrator",
    "MockQualityGateService",
    "MockDatabaseConnections",
    "MockPostgresPool",
    "MockRedisClient", 
    "MockClickHouseClient",
    
    # LLM/AI Mocks  
    "MockLLMService",
    "MockAgentService",
    "MockOpenAIClient",
    "MockEmbeddingService",
    "create_mock_structured_response",
    "get_mock_value_for_field",
    "get_complex_mock_value",
    "handle_generic_type",
]