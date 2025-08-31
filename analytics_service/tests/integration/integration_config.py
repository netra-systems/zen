"""
Analytics Service Integration Test Configuration
===============================================

Configuration management for Analytics Service integration tests.
Provides environment-specific settings and test infrastructure setup.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Reliability
- Value Impact: Ensures consistent test environments and reliable test execution
- Strategic Impact: Enables stable CI/CD pipeline for analytics service deployment
"""

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from test_framework import setup_test_path

# CRITICAL: setup_test_path() MUST be called before any project imports per CLAUDE.md
setup_test_path()

from analytics_service.analytics_core.isolated_environment import get_env


@dataclass
class DatabaseTestConfig:
    """Configuration for database integration testing."""
    # ClickHouse Configuration
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_database: str = "analytics_test"
    clickhouse_username: str = "default"
    clickhouse_password: str = ""
    clickhouse_connection_timeout: int = 10
    clickhouse_query_timeout: int = 30
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 15  # Use high DB number for tests to avoid conflicts
    redis_password: Optional[str] = None
    redis_connection_timeout: int = 5
    
    # Test Data Management
    cleanup_after_tests: bool = True
    preserve_test_data_on_failure: bool = True
    test_data_retention_hours: int = 24
    
    # Performance Requirements
    max_connection_time_ms: float = 1000.0
    max_query_time_ms: float = 5000.0
    max_insert_time_ms: float = 2000.0


@dataclass
class ServiceTestConfig:
    """Configuration for service communication integration testing."""
    # Analytics Service
    analytics_service_url: str = "http://localhost:8090"
    analytics_api_key: str = "test_analytics_api_key"
    
    # Backend Service
    backend_service_url: str = "http://localhost:8000"
    backend_api_key: str = "test_backend_api_key"
    
    # Auth Service
    auth_service_url: str = "http://localhost:8080"
    auth_api_key: str = "test_auth_api_key"
    
    # WebSocket Configuration
    websocket_url: str = "ws://localhost:8000/ws"
    analytics_websocket_url: str = "ws://localhost:8090/ws/analytics"
    websocket_connection_timeout: int = 10
    
    # Service Readiness
    service_startup_wait_seconds: int = 30
    service_health_check_interval_seconds: int = 5
    max_service_startup_attempts: int = 6
    
    # Communication Timeouts
    http_request_timeout_seconds: int = 30
    websocket_message_timeout_seconds: int = 10
    service_discovery_timeout_seconds: int = 15


@dataclass
class APITestConfig:
    """Configuration for API integration testing."""
    # Rate Limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_events_per_request: int = 50
    rate_limit_test_margin: float = 0.1  # 10% margin for rate limit testing
    
    # Performance Requirements
    max_api_response_time_ms: float = 2000.0
    max_event_ingestion_time_ms: float = 1000.0
    max_report_generation_time_ms: float = 5000.0
    
    # Concurrent Testing
    max_concurrent_requests: int = 20
    concurrent_test_timeout_seconds: int = 60
    
    # Payload Testing
    max_events_per_batch: int = 100
    max_payload_size_mb: int = 10
    large_payload_test_events: int = 50
    
    # Error Testing
    error_response_timeout_ms: float = 5000.0
    expected_error_codes: List[int] = field(default_factory=lambda: [400, 401, 403, 404, 429, 500, 503])


@dataclass
class EventPipelineTestConfig:
    """Configuration for event processing pipeline testing."""
    # Event Generation
    test_event_batch_size: int = 10
    high_volume_event_count: int = 1000
    performance_test_event_count: int = 10000
    test_user_count: int = 100
    
    # Processing Requirements
    max_event_processing_time_ms: float = 500.0
    max_batch_processing_time_ms: float = 5000.0
    min_throughput_events_per_second: float = 100.0
    min_success_rate: float = 0.95
    
    # Pipeline Testing
    enable_real_time_testing: bool = True
    enable_high_volume_testing: bool = True
    enable_error_injection_testing: bool = True
    
    # Data Validation
    event_deduplication_window_minutes: int = 5
    rate_limiting_window_minutes: int = 1
    max_events_per_user_per_minute: int = 1000


@dataclass
class IntegrationTestConfig:
    """Main configuration container for all integration tests."""
    # Sub-configurations
    database: DatabaseTestConfig = field(default_factory=DatabaseTestConfig)
    service: ServiceTestConfig = field(default_factory=ServiceTestConfig)
    api: APITestConfig = field(default_factory=APITestConfig)
    event_pipeline: EventPipelineTestConfig = field(default_factory=EventPipelineTestConfig)
    
    # Test Environment
    environment: str = "test"
    log_level: str = "DEBUG"
    enable_detailed_logging: bool = True
    
    # Test Execution
    parallel_test_execution: bool = True
    max_test_duration_minutes: int = 30
    retry_failed_tests: bool = False
    retry_attempts: int = 1
    
    # Test Data
    use_fixed_test_data_seed: bool = False
    test_data_seed: Optional[int] = None
    generate_test_report: bool = True
    test_report_format: str = "json"  # json, xml, html
    
    # Resource Management
    cleanup_test_resources: bool = True
    max_memory_usage_mb: int = 1024
    max_disk_usage_mb: int = 512


class IntegrationTestConfigManager:
    """Manages integration test configuration with environment overrides."""
    
    def __init__(self, config_override_file: Optional[str] = None):
        """Initialize configuration manager with optional override file."""
        self.env = get_env()
        self.config = IntegrationTestConfig()
        
        # Load environment-specific overrides
        self._load_environment_config()
        
        # Load configuration file overrides if provided
        if config_override_file and Path(config_override_file).exists():
            self._load_config_file(config_override_file)
    
    def _load_environment_config(self) -> None:
        """Load configuration from environment variables."""
        # Database Configuration
        if self.env.get("CLICKHOUSE_HOST"):
            self.config.database.clickhouse_host = self.env.get("CLICKHOUSE_HOST")
        if self.env.get("CLICKHOUSE_PORT"):
            self.config.database.clickhouse_port = int(self.env.get("CLICKHOUSE_PORT"))
        if self.env.get("CLICKHOUSE_DATABASE"):
            self.config.database.clickhouse_database = self.env.get("CLICKHOUSE_DATABASE")
        if self.env.get("CLICKHOUSE_USERNAME"):
            self.config.database.clickhouse_username = self.env.get("CLICKHOUSE_USERNAME")
        if self.env.get("CLICKHOUSE_PASSWORD"):
            self.config.database.clickhouse_password = self.env.get("CLICKHOUSE_PASSWORD")
        
        if self.env.get("REDIS_HOST"):
            self.config.database.redis_host = self.env.get("REDIS_HOST")
        if self.env.get("REDIS_PORT"):
            self.config.database.redis_port = int(self.env.get("REDIS_PORT"))
        if self.env.get("REDIS_ANALYTICS_DB"):
            self.config.database.redis_db = int(self.env.get("REDIS_ANALYTICS_DB"))
        if self.env.get("REDIS_PASSWORD"):
            self.config.database.redis_password = self.env.get("REDIS_PASSWORD")
        
        # Service Configuration
        if self.env.get("ANALYTICS_SERVICE_URL"):
            self.config.service.analytics_service_url = self.env.get("ANALYTICS_SERVICE_URL")
        elif self.env.get("ANALYTICS_SERVICE_PORT"):
            port = self.env.get("ANALYTICS_SERVICE_PORT")
            self.config.service.analytics_service_url = f"http://localhost:{port}"
        
        if self.env.get("BACKEND_SERVICE_URL"):
            self.config.service.backend_service_url = self.env.get("BACKEND_SERVICE_URL")
        
        if self.env.get("AUTH_SERVICE_URL"):
            self.config.service.auth_service_url = self.env.get("AUTH_SERVICE_URL")
        
        # API Configuration
        if self.env.get("ANALYTICS_API_KEY"):
            self.config.service.analytics_api_key = self.env.get("ANALYTICS_API_KEY")
        
        if self.env.get("RATE_LIMIT_REQUESTS_PER_MINUTE"):
            self.config.api.rate_limit_requests_per_minute = int(
                self.env.get("RATE_LIMIT_REQUESTS_PER_MINUTE")
            )
        
        # Event Pipeline Configuration
        if self.env.get("EVENT_BATCH_SIZE"):
            self.config.event_pipeline.test_event_batch_size = int(self.env.get("EVENT_BATCH_SIZE"))
        
        if self.env.get("MAX_EVENTS_PER_USER_PER_MINUTE"):
            self.config.event_pipeline.max_events_per_user_per_minute = int(
                self.env.get("MAX_EVENTS_PER_USER_PER_MINUTE")
            )
        
        # General Configuration
        if self.env.get("ENVIRONMENT"):
            self.config.environment = self.env.get("ENVIRONMENT")
        
        if self.env.get("LOG_LEVEL"):
            self.config.log_level = self.env.get("LOG_LEVEL")
    
    def _load_config_file(self, config_file_path: str) -> None:
        """Load configuration from JSON file."""
        import json
        
        try:
            with open(config_file_path, 'r') as f:
                file_config = json.load(f)
            
            # Apply file configuration overrides
            self._apply_config_overrides(file_config)
            
        except Exception as e:
            print(f"Warning: Failed to load config file {config_file_path}: {e}")
    
    def _apply_config_overrides(self, overrides: Dict[str, Any]) -> None:
        """Apply configuration overrides from file or environment."""
        # This would recursively apply overrides to the configuration
        # Implementation depends on specific override structure needed
        pass
    
    def get_config(self) -> IntegrationTestConfig:
        """Get the fully configured integration test configuration."""
        return self.config
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of validation errors."""
        errors = []
        
        # Validate database configuration
        if not self.config.database.clickhouse_host:
            errors.append("ClickHouse host is required")
        
        if not (1024 <= self.config.database.clickhouse_port <= 65535):
            errors.append("ClickHouse port must be between 1024 and 65535")
        
        if not self.config.database.redis_host:
            errors.append("Redis host is required")
        
        if not (1024 <= self.config.database.redis_port <= 65535):
            errors.append("Redis port must be between 1024 and 65535")
        
        # Validate service URLs
        service_urls = [
            self.config.service.analytics_service_url,
            self.config.service.backend_service_url,
            self.config.service.auth_service_url,
        ]
        
        for url in service_urls:
            if url and not (url.startswith("http://") or url.startswith("https://")):
                errors.append(f"Invalid service URL format: {url}")
        
        # Validate performance requirements
        if self.config.api.max_api_response_time_ms <= 0:
            errors.append("API response time requirement must be positive")
        
        if self.config.event_pipeline.min_throughput_events_per_second <= 0:
            errors.append("Event throughput requirement must be positive")
        
        if not (0.0 < self.config.event_pipeline.min_success_rate <= 1.0):
            errors.append("Success rate must be between 0.0 and 1.0")
        
        return errors
    
    def create_test_environment_summary(self) -> Dict[str, Any]:
        """Create a summary of the test environment configuration."""
        return {
            "environment": self.config.environment,
            "database": {
                "clickhouse": f"{self.config.database.clickhouse_host}:{self.config.database.clickhouse_port}",
                "redis": f"{self.config.database.redis_host}:{self.config.database.redis_port}",
            },
            "services": {
                "analytics": self.config.service.analytics_service_url,
                "backend": self.config.service.backend_service_url,
                "auth": self.config.service.auth_service_url,
            },
            "performance_requirements": {
                "max_api_response_ms": self.config.api.max_api_response_time_ms,
                "min_throughput_events_per_sec": self.config.event_pipeline.min_throughput_events_per_second,
                "min_success_rate": self.config.event_pipeline.min_success_rate,
            },
            "test_execution": {
                "parallel_execution": self.config.parallel_test_execution,
                "max_duration_minutes": self.config.max_test_duration_minutes,
                "cleanup_resources": self.config.cleanup_test_resources,
            },
        }


# Global configuration manager instance
_config_manager: Optional[IntegrationTestConfigManager] = None


def get_integration_test_config(
    config_override_file: Optional[str] = None,
    force_reload: bool = False
) -> IntegrationTestConfig:
    """Get the global integration test configuration."""
    global _config_manager
    
    if _config_manager is None or force_reload:
        _config_manager = IntegrationTestConfigManager(config_override_file)
        
        # Validate configuration
        validation_errors = _config_manager.validate_config()
        if validation_errors:
            print(f"Configuration validation warnings: {validation_errors}")
    
    return _config_manager.get_config()


def create_test_config_for_environment(environment: str) -> IntegrationTestConfig:
    """Create test configuration optimized for specific environment."""
    config = IntegrationTestConfig()
    
    if environment.lower() == "ci":
        # CI/CD environment optimizations
        config.max_test_duration_minutes = 15
        config.parallel_test_execution = True
        config.api.max_concurrent_requests = 10
        config.event_pipeline.high_volume_event_count = 500
        config.event_pipeline.performance_test_event_count = 2000
        
    elif environment.lower() == "local":
        # Local development optimizations
        config.max_test_duration_minutes = 60
        config.enable_detailed_logging = True
        config.database.preserve_test_data_on_failure = True
        config.retry_failed_tests = True
        
    elif environment.lower() == "staging":
        # Staging environment with production-like settings
        config.api.rate_limit_requests_per_minute = 500
        config.event_pipeline.high_volume_event_count = 2000
        config.event_pipeline.performance_test_event_count = 10000
        config.api.max_concurrent_requests = 50
    
    return config


# Export main configuration functions
__all__ = [
    "IntegrationTestConfig",
    "DatabaseTestConfig", 
    "ServiceTestConfig",
    "APITestConfig",
    "EventPipelineTestConfig",
    "IntegrationTestConfigManager",
    "get_integration_test_config",
    "create_test_config_for_environment",
]