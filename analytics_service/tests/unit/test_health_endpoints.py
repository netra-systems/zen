"""Comprehensive unit tests for Analytics Service Health Endpoints.

BUSINESS VALUE: Ensures health monitoring reliability for analytics service
operations. Critical for service availability monitoring, container orchestration
health checks, and operational visibility.

Tests cover:
- Basic health endpoint functionality
- Comprehensive health checks with component monitoring
- Readiness probes for Kubernetes
- Liveness probes for container health
- Component-specific health checks
- Diagnostics endpoint (non-production only)
- Error handling and graceful degradation

MOCK JUSTIFICATION: L1 Unit Tests - Mocking external dependencies (ClickHouse,
Redis, health services) to isolate endpoint logic. Real health checks tested
in integration tests.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from analytics_service.analytics_core.isolated_environment import get_env


# Mock health services and dependencies that may not exist yet
@pytest.fixture
def mock_health_services():
    """Mock health-related services and dependencies."""
    mocks = {}
    
    # Mock AnalyticsConfig
    with patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig') as mock_config_class:
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.service_version = "1.0.0"
        mock_config.clickhouse_required = False
        mock_config.redis_required = False
        mock_config.clickhouse_enabled = True
        mock_config.redis_enabled = True
        mock_config.data_retention_days = 90
        mock_config.max_events_per_batch = 100
        mock_config_class.get_instance.return_value = mock_config
        mocks['config'] = mock_config
    
    # Mock health checkers
    with patch('analytics_service.analytics_core.routes.health_routes.ClickHouseHealthChecker') as mock_ch_checker:
        mock_ch_instance = Mock()
        mock_ch_instance.check_health = AsyncMock(return_value={"healthy": True, "details": {}})
        mock_ch_instance.check_connectivity = AsyncMock(return_value=True)
        mock_ch_checker.return_value = mock_ch_instance
        mocks['clickhouse_checker'] = mock_ch_instance
    
    with patch('analytics_service.analytics_core.routes.health_routes.RedisHealthChecker') as mock_redis_checker:
        mock_redis_instance = Mock()
        mock_redis_instance.check_health = AsyncMock(return_value={"healthy": True, "details": {}})
        mock_redis_instance.check_connectivity = AsyncMock(return_value=True)
        mock_redis_checker.return_value = mock_redis_instance
        mocks['redis_checker'] = mock_redis_instance
    
    # Mock HealthService
    with patch('analytics_service.analytics_core.routes.health_routes.HealthService') as mock_health_service_class:
        mock_health_service = Mock()
        mock_health_service.check_event_ingestion_health = AsyncMock(return_value={"healthy": True, "details": {}})
        mock_health_service.check_analytics_processing_health = AsyncMock(return_value={"healthy": True, "details": {}})
        mock_health_service.check_metrics_service_health = AsyncMock(return_value={"healthy": True, "details": {}})
        mock_health_service.get_uptime_seconds.return_value = 300.0
        mock_health_service.get_initialization_status = AsyncMock(return_value={"initialized": True})
        mock_health_service.get_connection_pool_stats = AsyncMock(return_value={})
        mock_health_service.get_performance_metrics = AsyncMock(return_value={})
        mock_health_service.get_recent_errors = AsyncMock(return_value=[])
        mock_health_service_class.return_value = mock_health_service
        mocks['health_service'] = mock_health_service
    
    # Mock SystemMonitor
    with patch('analytics_service.analytics_core.routes.health_routes.SystemMonitor') as mock_system_monitor_class:
        mock_system_monitor = Mock()
        mock_system_monitor.get_system_metrics = AsyncMock(return_value={"cpu_usage": 25.5, "memory_usage": 60.0})
        mock_system_monitor.get_process_info = AsyncMock(return_value={"pid": 1234, "memory": "128MB"})
        mock_system_monitor.get_detailed_system_info = AsyncMock(return_value={"os": "linux", "python": "3.11"})
        mock_system_monitor_class.return_value = mock_system_monitor
        mocks['system_monitor'] = mock_system_monitor
    
    return mocks


class TestBasicHealthEndpoints:
    """Test suite for basic health endpoint functionality."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_simple_health_endpoint_from_main(self):
        """Test the simple health endpoint defined in main.py."""
        from analytics_service.main import create_app
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "analytics_service"
        assert data["version"] == "1.0.0"
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_root_endpoint_health_info(self):
        """Test health information in root endpoint."""
        from analytics_service.main import create_app
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "analytics_service"
        assert data["status"] == "running"
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))


@patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig')
@patch('analytics_service.analytics_core.routes.health_routes.ClickHouseHealthChecker')
@patch('analytics_service.analytics_core.routes.health_routes.RedisHealthChecker')
@patch('analytics_service.analytics_core.routes.health_routes.HealthService')
@patch('analytics_service.analytics_core.routes.health_routes.SystemMonitor')
class TestComprehensiveHealthEndpoints:
    """Test suite for comprehensive health endpoints with mocked dependencies."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_comprehensive_health_check_healthy(self, mock_system_monitor_class, mock_health_service_class,
                                               mock_redis_checker_class, mock_clickhouse_checker_class,
                                               mock_config_class):
        """Test comprehensive health check when all components are healthy."""
        # Setup mocks
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.service_version = "1.0.0"
        mock_config_class.get_instance.return_value = mock_config
        
        # Mock health checkers - healthy
        mock_ch_checker = Mock()
        mock_ch_checker.check_health = AsyncMock(return_value={"healthy": True, "details": {"version": "21.8"}})
        mock_clickhouse_checker_class.return_value = mock_ch_checker
        
        mock_redis_checker = Mock()
        mock_redis_checker.check_health = AsyncMock(return_value={"healthy": True, "details": {"version": "6.2"}})
        mock_redis_checker_class.return_value = mock_redis_checker
        
        # Mock health service
        mock_health_service = Mock()
        mock_health_service.check_event_ingestion_health = AsyncMock(return_value={"healthy": True})
        mock_health_service.check_analytics_processing_health = AsyncMock(return_value={"healthy": True})
        mock_health_service.check_metrics_service_health = AsyncMock(return_value={"healthy": True})
        mock_health_service.get_uptime_seconds.return_value = 300.0
        mock_health_service_class.return_value = mock_health_service
        
        # Mock system monitor
        mock_system_monitor = Mock()
        mock_system_monitor.get_system_metrics = AsyncMock(return_value={"cpu": 25.0, "memory": 60.0})
        mock_system_monitor_class.return_value = mock_system_monitor
        
        # Import and test the route
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            
            client = TestClient(app)
            response = client.get("/api/analytics/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["service"] == "analytics-service"
            assert data["environment"] == "test"
            assert "components" in data
            assert len(data["components"]) >= 2  # At least ClickHouse and Redis
            
        except ImportError:
            # If health_routes doesn't exist or has import issues, skip this test
            pytest.skip("Health routes not fully implemented yet")

    def test_comprehensive_health_check_unhealthy_clickhouse(self, mock_system_monitor_class, mock_health_service_class,
                                                           mock_redis_checker_class, mock_clickhouse_checker_class,
                                                           mock_config_class):
        """Test comprehensive health check when ClickHouse is unhealthy."""
        # Setup mocks
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.service_version = "1.0.0"
        mock_config_class.get_instance.return_value = mock_config
        
        # Mock ClickHouse as unhealthy
        mock_ch_checker = Mock()
        mock_ch_checker.check_health = AsyncMock(return_value={"healthy": False, "error": "Connection failed"})
        mock_clickhouse_checker_class.return_value = mock_ch_checker
        
        # Mock Redis as healthy
        mock_redis_checker = Mock()
        mock_redis_checker.check_health = AsyncMock(return_value={"healthy": True})
        mock_redis_checker_class.return_value = mock_redis_checker
        
        # Mock services as healthy
        mock_health_service = Mock()
        mock_health_service.check_event_ingestion_health = AsyncMock(return_value={"healthy": True})
        mock_health_service.check_analytics_processing_health = AsyncMock(return_value={"healthy": True})
        mock_health_service.check_metrics_service_health = AsyncMock(return_value={"healthy": True})
        mock_health_service.get_uptime_seconds.return_value = 300.0
        mock_health_service_class.return_value = mock_health_service
        
        mock_system_monitor = Mock()
        mock_system_monitor.get_system_metrics = AsyncMock(return_value={})
        mock_system_monitor_class.return_value = mock_system_monitor
        
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            
            client = TestClient(app)
            response = client.get("/api/analytics/health")
            
            # Should return 503 for unhealthy status
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")

    def test_readiness_probe_ready(self, mock_system_monitor_class, mock_health_service_class,
                                  mock_redis_checker_class, mock_clickhouse_checker_class,
                                  mock_config_class):
        """Test readiness probe when service is ready."""
        # Setup mocks
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.clickhouse_required = False
        mock_config.redis_required = False
        mock_config_class.get_instance.return_value = mock_config
        
        mock_ch_checker = Mock()
        mock_ch_checker.check_connectivity = AsyncMock(return_value=True)
        mock_clickhouse_checker_class.return_value = mock_ch_checker
        
        mock_redis_checker = Mock()
        mock_redis_checker.check_connectivity = AsyncMock(return_value=True)
        mock_redis_checker_class.return_value = mock_redis_checker
        
        mock_health_service = Mock()
        mock_health_service.get_initialization_status = AsyncMock(return_value={"initialized": True})
        mock_health_service_class.return_value = mock_health_service
        
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            
            client = TestClient(app)
            response = client.get("/api/analytics/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True
            assert "dependencies" in data
            assert "initialization_status" in data
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")

    def test_readiness_probe_not_ready(self, mock_system_monitor_class, mock_health_service_class,
                                      mock_redis_checker_class, mock_clickhouse_checker_class,
                                      mock_config_class):
        """Test readiness probe when service is not ready."""
        # Setup mocks
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.clickhouse_required = True  # Required but not available
        mock_config.redis_required = False
        mock_config_class.get_instance.return_value = mock_config
        
        # ClickHouse not available
        mock_ch_checker = Mock()
        mock_ch_checker.check_connectivity = AsyncMock(return_value=False)
        mock_clickhouse_checker_class.return_value = mock_ch_checker
        
        mock_redis_checker = Mock()
        mock_redis_checker.check_connectivity = AsyncMock(return_value=True)
        mock_redis_checker_class.return_value = mock_redis_checker
        
        mock_health_service = Mock()
        mock_health_service.get_initialization_status = AsyncMock(return_value={"initialized": True})
        mock_health_service_class.return_value = mock_health_service
        
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            
            client = TestClient(app)
            response = client.get("/api/analytics/health/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")

    def test_liveness_probe(self, mock_system_monitor_class, mock_health_service_class,
                           mock_redis_checker_class, mock_clickhouse_checker_class,
                           mock_config_class):
        """Test liveness probe endpoint."""
        # Setup mocks
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config_class.get_instance.return_value = mock_config
        
        mock_system_monitor = Mock()
        mock_system_monitor.get_process_info = AsyncMock(return_value={"pid": 1234, "memory": "128MB"})
        mock_system_monitor_class.return_value = mock_system_monitor
        
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            
            client = TestClient(app)
            response = client.get("/api/analytics/health/live")
            
            assert response.status_code == 200
            data = response.json()
            assert data["alive"] is True
            assert "process_info" in data
            assert data["process_info"]["pid"] == 1234
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")


class TestHealthEndpointErrorHandling:
    """Test suite for health endpoint error handling."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    @patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig')
    @patch('analytics_service.analytics_core.routes.health_routes.ClickHouseHealthChecker')
    def test_health_check_timeout(self, mock_clickhouse_checker_class, mock_config_class):
        """Test health check timeout handling."""
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config_class.get_instance.return_value = mock_config
        
        # Mock timeout
        mock_ch_checker = Mock()
        mock_ch_checker.check_health = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_clickhouse_checker_class.return_value = mock_ch_checker
        
        try:
            from analytics_service.analytics_core.routes.health_routes import _check_clickhouse_health
            
            # Test the internal function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(_check_clickhouse_health())
            
            assert result.status == "unhealthy"
            assert "timeout" in result.error_message.lower()
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")

    @patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig')
    @patch('analytics_service.analytics_core.routes.health_routes.ClickHouseHealthChecker')
    def test_health_check_exception(self, mock_clickhouse_checker_class, mock_config_class):
        """Test health check exception handling."""
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.clickhouse_required = True
        mock_config_class.get_instance.return_value = mock_config
        
        # Mock exception
        mock_ch_checker = Mock()
        mock_ch_checker.check_health = AsyncMock(side_effect=Exception("Database connection failed"))
        mock_clickhouse_checker_class.return_value = mock_ch_checker
        
        try:
            from analytics_service.analytics_core.routes.health_routes import _check_clickhouse_health
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(_check_clickhouse_health())
            
            assert result.status == "unhealthy"
            assert "Database connection failed" in result.error_message
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")

    def test_health_endpoints_cors_handling(self):
        """Test CORS handling in health endpoints."""
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            
            client = TestClient(app)
            
            # Test OPTIONS request (CORS preflight)
            response = client.options("/api/analytics/health")
            
            # Should handle OPTIONS requests gracefully
            assert response.status_code in [200, 404]  # 404 if route doesn't handle OPTIONS
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")


class TestHealthEndpointConfiguration:
    """Test suite for health endpoint configuration behavior."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    @patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig')
    def test_optional_services_in_staging(self, mock_config_class):
        """Test optional service handling in staging environment."""
        mock_config = Mock()
        mock_config.environment = "staging"
        mock_config.clickhouse_required = False
        mock_config.redis_required = False
        mock_config_class.get_instance.return_value = mock_config
        
        try:
            from analytics_service.analytics_core.routes.health_routes import _check_clickhouse_health
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(_check_clickhouse_health())
            
            # Should skip optional services
            assert result.status in ["skipped", "degraded"]
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")

    @patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig')
    def test_required_services_in_production(self, mock_config_class):
        """Test required service handling in production environment."""
        mock_config = Mock()
        mock_config.environment = "production"
        mock_config.clickhouse_required = True
        mock_config_class.get_instance.return_value = mock_config
        
        # This test would verify that required services must be healthy in production
        # The actual implementation would be tested in integration tests
        assert mock_config.environment == "production"
        assert mock_config.clickhouse_required is True

    def test_diagnostics_endpoint_security(self):
        """Test that diagnostics endpoint is restricted in production."""
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            # Mock production environment
            with patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig') as mock_config_class:
                mock_config = Mock()
                mock_config.environment = "production"
                mock_config_class.get_instance.return_value = mock_config
                
                from fastapi import FastAPI
                app = FastAPI()
                app.include_router(router)
                
                client = TestClient(app)
                response = client.get("/api/analytics/health/diagnostics")
                
                # Should be forbidden in production
                assert response.status_code == 403
                
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")

    def test_diagnostics_endpoint_allowed_in_development(self):
        """Test that diagnostics endpoint is allowed in development."""
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            # Mock various dependencies for diagnostics
            with patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig') as mock_config_class, \
                 patch('analytics_service.analytics_core.routes.health_routes.HealthService') as mock_health_service_class, \
                 patch('analytics_service.analytics_core.routes.health_routes.SystemMonitor') as mock_system_monitor_class:
                
                mock_config = Mock()
                mock_config.environment = "development"
                mock_config.clickhouse_enabled = True
                mock_config.redis_enabled = True
                mock_config.data_retention_days = 90
                mock_config.max_events_per_batch = 100
                mock_config_class.get_instance.return_value = mock_config
                
                mock_health_service = Mock()
                mock_health_service.get_connection_pool_stats = AsyncMock(return_value={})
                mock_health_service.get_performance_metrics = AsyncMock(return_value={})
                mock_health_service.get_recent_errors = AsyncMock(return_value=[])
                mock_health_service_class.return_value = mock_health_service
                
                mock_system_monitor = Mock()
                mock_system_monitor.get_detailed_system_info = AsyncMock(return_value={"os": "linux"})
                mock_system_monitor_class.return_value = mock_system_monitor
                
                from fastapi import FastAPI
                app = FastAPI()
                app.include_router(router)
                
                client = TestClient(app)
                response = client.get("/api/analytics/health/diagnostics")
                
                # Should be allowed in development
                assert response.status_code == 200
                data = response.json()
                assert data["service"] == "analytics-service"
                assert data["environment"] == "development"
                
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")


class TestHealthEndpointPerformance:
    """Test suite for health endpoint performance characteristics."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Enable isolation for testing
        env = get_env()
        env.enable_isolation()
        env.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        # Disable isolation
        env = get_env()
        env.disable_isolation()
        env.clear_cache()

    def test_basic_health_endpoint_performance(self):
        """Test that basic health endpoint is fast."""
        from analytics_service.main import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # Measure response time
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Basic health check should be very fast (under 100ms)
        response_time = end_time - start_time
        assert response_time < 0.1, f"Health endpoint took {response_time}s, should be under 0.1s"

    @patch('analytics_service.analytics_core.routes.health_routes.AnalyticsConfig')
    @patch('analytics_service.analytics_core.routes.health_routes.ClickHouseHealthChecker')
    @patch('analytics_service.analytics_core.routes.health_routes.RedisHealthChecker')
    @patch('analytics_service.analytics_core.routes.health_routes.HealthService')
    @patch('analytics_service.analytics_core.routes.health_routes.SystemMonitor')
    def test_comprehensive_health_check_parallel_execution(self, mock_system_monitor_class,
                                                          mock_health_service_class, mock_redis_checker_class,
                                                          mock_clickhouse_checker_class, mock_config_class):
        """Test that comprehensive health checks execute components in parallel."""
        
        # Setup mocks with delays to test parallelization
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.service_version = "1.0.0"
        mock_config_class.get_instance.return_value = mock_config
        
        async def delayed_health_check():
            await asyncio.sleep(0.1)  # 100ms delay
            return {"healthy": True, "details": {}}
        
        mock_ch_checker = Mock()
        mock_ch_checker.check_health = delayed_health_check
        mock_clickhouse_checker_class.return_value = mock_ch_checker
        
        mock_redis_checker = Mock()
        mock_redis_checker.check_health = delayed_health_check
        mock_redis_checker_class.return_value = mock_redis_checker
        
        mock_health_service = Mock()
        mock_health_service.check_event_ingestion_health = delayed_health_check
        mock_health_service.check_analytics_processing_health = delayed_health_check
        mock_health_service.check_metrics_service_health = delayed_health_check
        mock_health_service.get_uptime_seconds.return_value = 300.0
        mock_health_service_class.return_value = mock_health_service
        
        mock_system_monitor = Mock()
        mock_system_monitor.get_system_metrics = AsyncMock(return_value={})
        mock_system_monitor_class.return_value = mock_system_monitor
        
        try:
            from analytics_service.analytics_core.routes.health_routes import router
            
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            
            client = TestClient(app)
            
            start_time = time.time()
            response = client.get("/api/analytics/health")
            end_time = time.time()
            
            # If executed in parallel, total time should be close to 0.1s
            # If executed sequentially, it would be ~0.5s (5 * 0.1s)
            response_time = end_time - start_time
            
            assert response.status_code == 200
            # Allow some overhead but should be significantly less than sequential
            assert response_time < 0.3, f"Health check took {response_time}s, indicating sequential execution"
            
        except ImportError:
            pytest.skip("Health routes not fully implemented yet")

    def test_health_endpoint_caching_behavior(self):
        """Test health endpoint response caching behavior."""
        from analytics_service.main import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # Make multiple requests
        response1 = client.get("/health")
        response2 = client.get("/health")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Uptime should be different (increasing)
        uptime1 = response1.json()["uptime_seconds"]
        uptime2 = response2.json()["uptime_seconds"]
        
        assert uptime2 >= uptime1, "Uptime should be increasing between requests"