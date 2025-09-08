"""
Test Startup Health Checks - Critical Service Validation

Business Value Justification (BVJ):
- Segment: All customer segments (prevents 100% service failures)
- Business Goal: Platform Reliability and Availability
- Value Impact: Prevents NoneType errors and ensures service stability
- Strategic Impact: Critical failure prevention - blocks startup until services ready

CRITICAL: These health checks prevent cascade failures identified in Five Whys analysis.
Tests MUST validate all critical services and their failure modes.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import FastAPI
from test_framework.base_integration_test import BaseIntegrationTest

from netra_backend.app.startup_health_checks import (
    StartupHealthChecker, HealthCheckResult, ServiceStatus,
    validate_startup_health
)


class TestServiceStatusEnum(BaseIntegrationTest):
    """Test ServiceStatus enum values and usage."""
    
    def test_service_status_enum_values(self):
        """Test all ServiceStatus enum values are correct."""
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.NOT_CONFIGURED.value == "not_configured"
        
    def test_service_status_string_conversion(self):
        """Test ServiceStatus string representation."""
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.NOT_CONFIGURED.value == "not_configured"


class TestHealthCheckResultDataclass(BaseIntegrationTest):
    """Test HealthCheckResult dataclass functionality."""
    
    def test_health_check_result_creation_minimal(self):
        """Test HealthCheckResult creation with minimal required fields."""
        check_time = datetime.now(timezone.utc)
        result = HealthCheckResult(
            service_name="test_service",
            status=ServiceStatus.HEALTHY,
            message="Service is operational",
            check_time=check_time
        )
        
        assert result.service_name == "test_service"
        assert result.status == ServiceStatus.HEALTHY
        assert result.message == "Service is operational"
        assert result.check_time == check_time
        assert result.latency_ms is None
        assert result.metadata is None
        
    def test_health_check_result_creation_complete(self):
        """Test HealthCheckResult creation with all fields."""
        check_time = datetime.now(timezone.utc)
        metadata = {"version": "1.2.3", "connections": 5}
        
        result = HealthCheckResult(
            service_name="database",
            status=ServiceStatus.DEGRADED,
            message="High latency detected",
            check_time=check_time,
            latency_ms=1250.5,
            metadata=metadata
        )
        
        assert result.service_name == "database"
        assert result.status == ServiceStatus.DEGRADED
        assert result.message == "High latency detected"
        assert result.check_time == check_time
        assert result.latency_ms == 1250.5
        assert result.metadata == metadata
        assert result.metadata["version"] == "1.2.3"
        assert result.metadata["connections"] == 5
        
    def test_health_check_result_dataclass_equality(self):
        """Test HealthCheckResult dataclass equality comparison."""
        check_time = datetime.now(timezone.utc)
        
        result1 = HealthCheckResult(
            service_name="redis",
            status=ServiceStatus.HEALTHY,
            message="Connected",
            check_time=check_time,
            latency_ms=50.0
        )
        
        result2 = HealthCheckResult(
            service_name="redis",
            status=ServiceStatus.HEALTHY,
            message="Connected",
            check_time=check_time,
            latency_ms=50.0
        )
        
        result3 = HealthCheckResult(
            service_name="redis",
            status=ServiceStatus.UNHEALTHY,
            message="Disconnected",
            check_time=check_time,
            latency_ms=50.0
        )
        
        assert result1 == result2  # Same values
        assert result1 != result3  # Different status


class TestStartupHealthCheckerInitialization(BaseIntegrationTest):
    """Test StartupHealthChecker initialization and configuration."""
    
    def test_startup_health_checker_initialization(self):
        """Test StartupHealthChecker initialization with FastAPI app."""
        app = FastAPI(title="Test App")
        checker = StartupHealthChecker(app)
        
        assert checker.app == app
        assert checker.health_results == {}
        assert isinstance(checker.health_results, dict)
        
    def test_startup_health_checker_critical_services_defined(self):
        """Test CRITICAL_SERVICES constant is properly defined."""
        expected_critical = ['llm_manager', 'database', 'redis']
        
        assert StartupHealthChecker.CRITICAL_SERVICES == expected_critical
        assert len(StartupHealthChecker.CRITICAL_SERVICES) == 3
        assert 'llm_manager' in StartupHealthChecker.CRITICAL_SERVICES
        assert 'database' in StartupHealthChecker.CRITICAL_SERVICES
        assert 'redis' in StartupHealthChecker.CRITICAL_SERVICES
        
    def test_startup_health_checker_optional_services_defined(self):
        """Test OPTIONAL_SERVICES constant is properly defined."""
        expected_optional = ['clickhouse', 'websocket_manager']
        
        assert StartupHealthChecker.OPTIONAL_SERVICES == expected_optional
        assert len(StartupHealthChecker.OPTIONAL_SERVICES) == 2
        assert 'clickhouse' in StartupHealthChecker.OPTIONAL_SERVICES
        assert 'websocket_manager' in StartupHealthChecker.OPTIONAL_SERVICES
        
    def test_startup_health_checker_app_assignment(self):
        """Test app is properly stored and accessible."""
        app1 = FastAPI(title="App 1")
        app2 = FastAPI(title="App 2")
        
        checker1 = StartupHealthChecker(app1)
        checker2 = StartupHealthChecker(app2)
        
        assert checker1.app == app1
        assert checker2.app == app2
        assert checker1.app != checker2.app


class TestLLMManagerHealthCheck(BaseIntegrationTest):
    """Test LLM manager health check functionality."""
    
    async def test_check_llm_manager_not_configured(self):
        """Test LLM manager health check when not configured."""
        app = FastAPI()
        # app.state has no llm_manager attribute
        checker = StartupHealthChecker(app)
        
        result = await checker.check_llm_manager()
        
        assert result.service_name == "llm_manager"
        assert result.status == ServiceStatus.NOT_CONFIGURED
        assert "LLM manager not found in app.state" in result.message
        assert result.latency_ms is None
        assert isinstance(result.check_time, datetime)
        
    async def test_check_llm_manager_none_value(self):
        """Test LLM manager health check when set to None."""
        app = FastAPI()
        app.state.llm_manager = None
        checker = StartupHealthChecker(app)
        
        result = await checker.check_llm_manager()
        
        assert result.service_name == "llm_manager"
        assert result.status == ServiceStatus.UNHEALTHY
        assert "LLM manager is None" in result.message
        assert isinstance(result.check_time, datetime)
        
    async def test_check_llm_manager_missing_methods(self):
        """Test LLM manager health check when required methods are missing."""
        app = FastAPI()
        
        # Mock LLM manager without required methods
        mock_llm_manager = Mock()
        # Deliberately omit required methods: ask_llm, get_llm_config
        app.state.llm_manager = mock_llm_manager
        
        checker = StartupHealthChecker(app)
        result = await checker.check_llm_manager()
        
        assert result.service_name == "llm_manager"
        assert result.status == ServiceStatus.DEGRADED
        assert "LLM manager missing methods" in result.message
        assert "ask_llm" in result.message
        assert "get_llm_config" in result.message
        assert isinstance(result.check_time, datetime)
        
    async def test_check_llm_manager_no_configs_available(self):
        """Test LLM manager health check when no LLM configs are available."""
        app = FastAPI()
        
        # Mock LLM manager with required methods but no configs
        mock_llm_manager = Mock()
        mock_llm_manager.ask_llm = Mock()
        mock_llm_manager.get_llm_config = Mock()
        mock_llm_manager.llm_configs = None  # No configs available
        
        app.state.llm_manager = mock_llm_manager
        
        checker = StartupHealthChecker(app)
        result = await checker.check_llm_manager()
        
        assert result.service_name == "llm_manager"
        assert result.status == ServiceStatus.DEGRADED
        assert "No LLM configurations available" in result.message
        assert isinstance(result.check_time, datetime)
        
    async def test_check_llm_manager_configs_check_exception(self):
        """Test LLM manager health check when config check raises exception."""
        app = FastAPI()
        
        # Mock LLM manager that raises exception when accessing configs
        mock_llm_manager = Mock()
        mock_llm_manager.ask_llm = Mock()
        mock_llm_manager.get_llm_config = Mock()
        # Accessing llm_configs raises exception
        mock_llm_manager.llm_configs = Mock(side_effect=Exception("Config access error"))
        
        app.state.llm_manager = mock_llm_manager
        
        checker = StartupHealthChecker(app)
        result = await checker.check_llm_manager()
        
        assert result.service_name == "llm_manager"
        assert result.status == ServiceStatus.DEGRADED
        assert "Error checking LLM configs" in result.message
        assert "Config access error" in result.message
        assert isinstance(result.check_time, datetime)
        
    async def test_check_llm_manager_healthy_with_configs(self):
        """Test LLM manager health check when healthy with configurations."""
        app = FastAPI()
        
        # Mock healthy LLM manager with configs
        mock_llm_manager = Mock()
        mock_llm_manager.ask_llm = Mock()
        mock_llm_manager.get_llm_config = Mock()
        mock_llm_manager.llm_configs = {"gpt-4": {"model": "gpt-4"}}  # Mock configs
        
        app.state.llm_manager = mock_llm_manager
        
        checker = StartupHealthChecker(app)
        result = await checker.check_llm_manager()
        
        assert result.service_name == "llm_manager"
        assert result.status == ServiceStatus.HEALTHY
        assert "LLM manager is initialized and functional" in result.message
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        assert isinstance(result.check_time, datetime)
        
    async def test_check_llm_manager_exception_handling(self):
        """Test LLM manager health check exception handling."""
        app = FastAPI()
        
        # Mock that raises exception during health check
        mock_llm_manager = Mock()
        mock_llm_manager.ask_llm = Mock()
        mock_llm_manager.get_llm_config = Mock()
        # Accessing any attribute raises exception
        type(mock_llm_manager).llm_configs = Mock(side_effect=RuntimeError("Critical error"))
        
        app.state.llm_manager = mock_llm_manager
        
        checker = StartupHealthChecker(app)
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            result = await checker.check_llm_manager()
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            
        assert result.service_name == "llm_manager"
        assert result.status == ServiceStatus.UNHEALTHY
        assert "Exception during health check" in result.message
        assert "Critical error" in result.message


class TestDatabaseHealthCheck(BaseIntegrationTest):
    """Test database health check functionality."""
    
    async def test_check_database_not_configured(self):
        """Test database health check when session factory not configured."""
        app = FastAPI()
        # app.state has no db_session_factory
        checker = StartupHealthChecker(app)
        
        result = await checker.check_database()
        
        assert result.service_name == "database"
        assert result.status == ServiceStatus.NOT_CONFIGURED
        assert "Database session factory not found in app.state" in result.message
        assert result.latency_ms is None
        assert isinstance(result.check_time, datetime)
        
    async def test_check_database_factory_none(self):
        """Test database health check when session factory is None."""
        app = FastAPI()
        app.state.db_session_factory = None
        checker = StartupHealthChecker(app)
        
        result = await checker.check_database()
        
        assert result.service_name == "database"
        assert result.status == ServiceStatus.UNHEALTHY
        assert "Database session factory is None" in result.message
        assert isinstance(result.check_time, datetime)
        
    async def test_check_database_connection_success(self):
        """Test database health check with successful connection."""
        app = FastAPI()
        
        # Mock successful database session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        # Mock session factory
        mock_factory = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__ = AsyncMock()
        
        app.state.db_session_factory = mock_factory
        checker = StartupHealthChecker(app)
        
        result = await checker.check_database()
        
        assert result.service_name == "database"
        assert result.status == ServiceStatus.HEALTHY
        assert "Database connection successful" in result.message
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        assert isinstance(result.check_time, datetime)
        
        # Verify database query was executed
        mock_session.execute.assert_called_once()
        mock_result.scalar.assert_called_once()
        
    async def test_check_database_connection_failure(self):
        """Test database health check with connection failure."""
        app = FastAPI()
        
        # Mock failing database session factory
        mock_factory = AsyncMock()
        mock_factory.side_effect = Exception("Connection refused")
        
        app.state.db_session_factory = mock_factory
        checker = StartupHealthChecker(app)
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            result = await checker.check_database()
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            
        assert result.service_name == "database"
        assert result.status == ServiceStatus.UNHEALTHY
        assert "Database connection failed" in result.message
        assert "Connection refused" in result.message
        assert isinstance(result.check_time, datetime)
        
    async def test_check_database_query_failure(self):
        """Test database health check when query execution fails."""
        app = FastAPI()
        
        # Mock session that fails during query execution
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Query timeout")
        
        mock_factory = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__ = AsyncMock()
        
        app.state.db_session_factory = mock_factory
        checker = StartupHealthChecker(app)
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            result = await checker.check_database()
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            
        assert result.service_name == "database"
        assert result.status == ServiceStatus.UNHEALTHY
        assert "Database connection failed" in result.message
        assert "Query timeout" in result.message


class TestRedisHealthCheck(BaseIntegrationTest):
    """Test Redis health check functionality."""
    
    async def test_check_redis_manager_not_available(self):
        """Test Redis health check when redis_manager is not available."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock redis_manager import to return None
        with patch('netra_backend.app.startup_health_checks.redis_manager', None):
            result = await checker.check_redis()
            
        assert result.service_name == "redis"
        assert result.status == ServiceStatus.NOT_CONFIGURED
        assert "Redis manager not initialized" in result.message
        assert isinstance(result.check_time, datetime)
        
    async def test_check_redis_ping_successful_redis_client(self):
        """Test Redis health check with successful ping using redis_client."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock redis_manager with redis_client attribute
        mock_redis_manager = Mock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_manager.redis_client = mock_redis_client
        
        with patch('netra_backend.app.startup_health_checks.redis_manager', mock_redis_manager):
            result = await checker.check_redis()
            
        assert result.service_name == "redis"
        assert result.status == ServiceStatus.HEALTHY
        assert "Redis connection successful" in result.message
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        assert isinstance(result.check_time, datetime)
        
        # Verify ping was called
        mock_redis_client.ping.assert_called_once()
        
    async def test_check_redis_ping_successful_private_client(self):
        """Test Redis health check with successful ping using _client."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock redis_manager with _client attribute (no redis_client)
        mock_redis_manager = Mock()
        mock_private_client = AsyncMock()
        mock_private_client.ping = AsyncMock(return_value=True)
        mock_redis_manager._client = mock_private_client
        # Remove redis_client attribute
        del mock_redis_manager.redis_client  # Simulate not having redis_client
        
        with patch('netra_backend.app.startup_health_checks.redis_manager', mock_redis_manager):
            # Patch hasattr to return False for redis_client
            with patch('builtins.hasattr', side_effect=lambda obj, attr: attr != 'redis_client'):
                result = await checker.check_redis()
        
        assert result.service_name == "redis"
        assert result.status == ServiceStatus.HEALTHY
        assert "Redis connection successful" in result.message
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        
        # Verify ping was called on _client
        mock_private_client.ping.assert_called_once()
        
    async def test_check_redis_connected_flag_true(self):
        """Test Redis health check using _connected flag when true."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock redis_manager with _connected flag (no clients available)
        mock_redis_manager = Mock()
        mock_redis_manager._connected = True
        # Remove both client attributes
        mock_redis_manager.spec = ['_connected']  # Only has _connected
        
        with patch('netra_backend.app.startup_health_checks.redis_manager', mock_redis_manager):
            with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == '_connected'):
                result = await checker.check_redis()
        
        assert result.service_name == "redis"
        assert result.status == ServiceStatus.HEALTHY
        assert "Redis connection successful" in result.message
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        
    async def test_check_redis_connected_flag_false(self):
        """Test Redis health check using _connected flag when false."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock redis_manager with _connected=False
        mock_redis_manager = Mock()
        mock_redis_manager._connected = False
        mock_redis_manager.spec = ['_connected']
        
        with patch('netra_backend.app.startup_health_checks.redis_manager', mock_redis_manager):
            with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == '_connected'):
                result = await checker.check_redis()
        
        assert result.service_name == "redis"
        assert result.status == ServiceStatus.DEGRADED
        assert "Redis manager exists but not connected" in result.message
        
    async def test_check_redis_ping_failure(self):
        """Test Redis health check when ping fails."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock redis_manager with failing redis_client
        mock_redis_manager = Mock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping.side_effect = Exception("Redis connection timeout")
        mock_redis_manager.redis_client = mock_redis_client
        
        with patch('netra_backend.app.startup_health_checks.redis_manager', mock_redis_manager):
            with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
                result = await checker.check_redis()
                
                # Verify error was logged
                mock_logger.error.assert_called_once()
        
        assert result.service_name == "redis"
        assert result.status == ServiceStatus.UNHEALTHY
        assert "Redis connection failed" in result.message
        assert "Redis connection timeout" in result.message
        
    async def test_check_redis_no_client_methods(self):
        """Test Redis health check when no client methods are available."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock redis_manager without any client attributes or connected flag
        mock_redis_manager = Mock()
        mock_redis_manager.spec = []  # No attributes
        
        with patch('netra_backend.app.startup_health_checks.redis_manager', mock_redis_manager):
            with patch('builtins.hasattr', return_value=False):  # No attributes found
                result = await checker.check_redis()
        
        assert result.service_name == "redis"
        assert result.status == ServiceStatus.DEGRADED
        assert "Redis manager exists but not connected" in result.message


class TestClickHouseHealthCheck(BaseIntegrationTest):
    """Test ClickHouse health check functionality."""
    
    async def test_check_clickhouse_successful_connection(self):
        """Test ClickHouse health check with successful connection."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock ClickHouseService
        mock_ch_service = AsyncMock()
        mock_ch_service.initialize = AsyncMock()
        mock_ch_service.execute = AsyncMock(return_value="1")  # SELECT 1 result
        mock_ch_service.close = AsyncMock()
        
        with patch('netra_backend.app.startup_health_checks.ClickHouseService') as mock_ch_class:
            mock_ch_class.return_value = mock_ch_service
            
            result = await checker.check_clickhouse()
            
        assert result.service_name == "clickhouse"
        assert result.status == ServiceStatus.HEALTHY
        assert "ClickHouse connection successful" in result.message
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        assert isinstance(result.check_time, datetime)
        
        # Verify service lifecycle was called
        mock_ch_service.initialize.assert_called_once()
        mock_ch_service.execute.assert_called_once_with("SELECT 1")
        mock_ch_service.close.assert_called_once()
        
    async def test_check_clickhouse_initialization_failure(self):
        """Test ClickHouse health check when initialization fails."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock ClickHouseService that fails during initialization
        mock_ch_service = AsyncMock()
        mock_ch_service.initialize.side_effect = Exception("ClickHouse unreachable")
        
        with patch('netra_backend.app.startup_health_checks.ClickHouseService') as mock_ch_class:
            mock_ch_class.return_value = mock_ch_service
            
            with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
                result = await checker.check_clickhouse()
                
                # Verify warning was logged (not error, since ClickHouse is optional)
                mock_logger.warning.assert_called_once()
                assert "ClickHouse health check failed (optional service)" in mock_logger.warning.call_args[0][0]
        
        assert result.service_name == "clickhouse"
        assert result.status == ServiceStatus.DEGRADED
        assert "ClickHouse unavailable" in result.message
        assert "ClickHouse unreachable" in result.message
        
    async def test_check_clickhouse_query_failure(self):
        """Test ClickHouse health check when query execution fails."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock ClickHouseService that fails during query
        mock_ch_service = AsyncMock()
        mock_ch_service.initialize = AsyncMock()
        mock_ch_service.execute.side_effect = Exception("Query execution failed")
        mock_ch_service.close = AsyncMock()
        
        with patch('netra_backend.app.startup_health_checks.ClickHouseService') as mock_ch_class:
            mock_ch_class.return_value = mock_ch_service
            
            with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
                result = await checker.check_clickhouse()
                
                # Verify warning was logged
                mock_logger.warning.assert_called_once()
        
        assert result.service_name == "clickhouse"
        assert result.status == ServiceStatus.DEGRADED
        assert "ClickHouse unavailable" in result.message
        assert "Query execution failed" in result.message
        
        # Verify cleanup was still attempted
        mock_ch_service.close.assert_called_once()
        
    async def test_check_clickhouse_cleanup_on_exception(self):
        """Test ClickHouse health check ensures cleanup even on exception."""
        checker = StartupHealthChecker(FastAPI())
        
        # Mock ClickHouseService where execute fails
        mock_ch_service = AsyncMock()
        mock_ch_service.initialize = AsyncMock()
        mock_ch_service.execute.side_effect = RuntimeError("Connection lost")
        mock_ch_service.close = AsyncMock()
        
        with patch('netra_backend.app.startup_health_checks.ClickHouseService') as mock_ch_class:
            mock_ch_class.return_value = mock_ch_service
            
            result = await checker.check_clickhouse()
        
        # Verify cleanup was called despite exception
        mock_ch_service.close.assert_called_once()
        
        assert result.service_name == "clickhouse"
        assert result.status == ServiceStatus.DEGRADED


class TestHealthCheckOrchestration(BaseIntegrationTest):
    """Test health check orchestration and aggregation."""
    
    async def test_run_all_health_checks_all_services(self):
        """Test running all health checks returns all service results."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock all health check methods to return healthy results
        async def mock_healthy_check(service_name):
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.HEALTHY,
                message=f"{service_name} is healthy",
                check_time=datetime.now(timezone.utc),
                latency_ms=100.0
            )
        
        checker.check_llm_manager = AsyncMock(return_value=await mock_healthy_check("llm_manager"))
        checker.check_database = AsyncMock(return_value=await mock_healthy_check("database"))
        checker.check_redis = AsyncMock(return_value=await mock_healthy_check("redis"))
        checker.check_clickhouse = AsyncMock(return_value=await mock_healthy_check("clickhouse"))
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            all_healthy, results = await checker.run_all_health_checks()
        
        # Verify all services were checked
        assert len(results) == 4
        service_names = [r.service_name for r in results]
        assert "llm_manager" in service_names
        assert "database" in service_names
        assert "redis" in service_names
        assert "clickhouse" in service_names
        
        # All critical services are healthy
        assert all_healthy is True
        
        # Verify health results were stored
        assert len(checker.health_results) == 4
        assert "llm_manager" in checker.health_results
        assert checker.health_results["llm_manager"].status == ServiceStatus.HEALTHY
        
        # Verify logging occurred
        mock_logger.info.assert_called()
        
    async def test_run_all_health_checks_critical_service_failure(self):
        """Test health checks when critical service fails."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock critical service failure
        unhealthy_result = HealthCheckResult(
            service_name="database",
            status=ServiceStatus.UNHEALTHY,
            message="Database connection failed",
            check_time=datetime.now(timezone.utc)
        )
        
        healthy_result = HealthCheckResult(
            service_name="llm_manager",
            status=ServiceStatus.HEALTHY,
            message="LLM manager healthy",
            check_time=datetime.now(timezone.utc)
        )
        
        checker.check_llm_manager = AsyncMock(return_value=healthy_result)
        checker.check_database = AsyncMock(return_value=unhealthy_result)
        checker.check_redis = AsyncMock(return_value=healthy_result)
        checker.check_clickhouse = AsyncMock(return_value=healthy_result)
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            all_healthy, results = await checker.run_all_health_checks()
        
        # Critical service failed, so all_healthy should be False
        assert all_healthy is False
        
        # Verify error logging for critical service
        mock_logger.error.assert_called()
        error_calls = [call for call in mock_logger.error.call_args_list]
        assert any("CRITICAL service database is not healthy" in str(call) for call in error_calls)
        
    async def test_run_all_health_checks_optional_service_failure(self):
        """Test health checks when optional service fails."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock optional service failure (ClickHouse)
        degraded_result = HealthCheckResult(
            service_name="clickhouse",
            status=ServiceStatus.DEGRADED,
            message="ClickHouse unavailable",
            check_time=datetime.now(timezone.utc)
        )
        
        healthy_result = HealthCheckResult(
            service_name="test",
            status=ServiceStatus.HEALTHY,
            message="Service healthy",
            check_time=datetime.now(timezone.utc)
        )
        
        checker.check_llm_manager = AsyncMock(return_value=healthy_result)
        checker.check_database = AsyncMock(return_value=healthy_result)
        checker.check_redis = AsyncMock(return_value=healthy_result)
        checker.check_clickhouse = AsyncMock(return_value=degraded_result)
        
        all_healthy, results = await checker.run_all_health_checks()
        
        # Optional service degraded, but all critical services healthy
        assert all_healthy is True
        
    async def test_run_all_health_checks_logging_output(self):
        """Test health check logging output for different statuses."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock different service statuses
        results = {
            "healthy_service": HealthCheckResult(
                service_name="healthy_service",
                status=ServiceStatus.HEALTHY,
                message="All good",
                check_time=datetime.now(timezone.utc),
                latency_ms=50.0
            ),
            "degraded_service": HealthCheckResult(
                service_name="degraded_service",
                status=ServiceStatus.DEGRADED,
                message="High latency",
                check_time=datetime.now(timezone.utc)
            ),
            "not_configured_service": HealthCheckResult(
                service_name="not_configured_service",
                status=ServiceStatus.NOT_CONFIGURED,
                message="Not configured",
                check_time=datetime.now(timezone.utc)
            ),
            "unhealthy_service": HealthCheckResult(
                service_name="unhealthy_service",
                status=ServiceStatus.UNHEALTHY,
                message="Connection failed",
                check_time=datetime.now(timezone.utc)
            )
        }
        
        # Override health check methods
        checker.check_llm_manager = AsyncMock(return_value=results["healthy_service"])
        checker.check_database = AsyncMock(return_value=results["degraded_service"])
        checker.check_redis = AsyncMock(return_value=results["not_configured_service"])
        checker.check_clickhouse = AsyncMock(return_value=results["unhealthy_service"])
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            all_healthy, result_list = await checker.run_all_health_checks()
        
        # Verify different log levels were used
        mock_logger.info.assert_called()  # For healthy service
        mock_logger.warning.assert_called()  # For degraded and not_configured
        mock_logger.error.assert_called()  # For unhealthy service


class TestValidateStartup(BaseIntegrationTest):
    """Test startup validation orchestration."""
    
    async def test_validate_startup_all_healthy_success(self):
        """Test validate_startup when all critical services are healthy."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock run_all_health_checks to return all healthy
        healthy_results = [
            HealthCheckResult("llm_manager", ServiceStatus.HEALTHY, "Healthy", datetime.now(timezone.utc)),
            HealthCheckResult("database", ServiceStatus.HEALTHY, "Healthy", datetime.now(timezone.utc)),
            HealthCheckResult("redis", ServiceStatus.HEALTHY, "Healthy", datetime.now(timezone.utc)),
            HealthCheckResult("clickhouse", ServiceStatus.HEALTHY, "Healthy", datetime.now(timezone.utc))
        ]
        
        checker.run_all_health_checks = AsyncMock(return_value=(True, healthy_results))
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            result = await checker.validate_startup(fail_on_critical=True)
        
        assert result is True
        mock_logger.info.assert_called()
        # Verify success message was logged
        success_calls = [call for call in mock_logger.info.call_args_list]
        assert any("All critical services passed health checks" in str(call) for call in success_calls)
        
    async def test_validate_startup_critical_failure_with_exception(self):
        """Test validate_startup raises exception when critical services fail."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock critical service failure
        failed_results = [
            HealthCheckResult("llm_manager", ServiceStatus.UNHEALTHY, "Failed", datetime.now(timezone.utc)),
            HealthCheckResult("database", ServiceStatus.NOT_CONFIGURED, "Not found", datetime.now(timezone.utc)),
            HealthCheckResult("redis", ServiceStatus.HEALTHY, "Healthy", datetime.now(timezone.utc)),
        ]
        
        checker.run_all_health_checks = AsyncMock(return_value=(False, failed_results))
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            with pytest.raises(RuntimeError) as excinfo:
                await checker.validate_startup(fail_on_critical=True)
        
        # Verify exception details
        assert "Startup validation failed" in str(excinfo.value)
        assert "critical services unhealthy" in str(excinfo.value)
        
        # Verify error logging
        mock_logger.error.assert_called()
        error_calls = [call for call in mock_logger.error.call_args_list]
        assert any("STARTUP VALIDATION FAILED" in str(call) for call in error_calls)
        
    async def test_validate_startup_critical_failure_no_exception(self):
        """Test validate_startup without exception when fail_on_critical=False."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock critical service failure
        failed_results = [
            HealthCheckResult("database", ServiceStatus.UNHEALTHY, "Connection failed", datetime.now(timezone.utc)),
            HealthCheckResult("llm_manager", ServiceStatus.HEALTHY, "Healthy", datetime.now(timezone.utc)),
        ]
        
        checker.run_all_health_checks = AsyncMock(return_value=(False, failed_results))
        
        with patch('netra_backend.app.startup_health_checks.logger'):
            result = await checker.validate_startup(fail_on_critical=False)
        
        # Should return False but not raise exception
        assert result is False
        
    async def test_validate_startup_health_check_summary_logging(self):
        """Test validate_startup logs health check summary."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock health results stored in checker
        checker.health_results = {
            "llm_manager": HealthCheckResult("llm_manager", ServiceStatus.HEALTHY, "OK", datetime.now(timezone.utc)),
            "database": HealthCheckResult("database", ServiceStatus.DEGRADED, "Slow", datetime.now(timezone.utc)),
            "redis": HealthCheckResult("redis", ServiceStatus.NOT_CONFIGURED, "Missing", datetime.now(timezone.utc)),
        }
        
        checker.run_all_health_checks = AsyncMock(return_value=(True, []))
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            await checker.validate_startup(fail_on_critical=False)
        
        # Verify summary logging
        mock_logger.info.assert_called()
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        
        # Should log summary for each service
        summary_calls = [call for call in info_calls if "Health Check Summary" in call]
        assert len(summary_calls) > 0
        
    async def test_validate_startup_degraded_critical_service(self):
        """Test validate_startup treats degraded critical services as healthy."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock degraded critical service (should still pass)
        degraded_results = [
            HealthCheckResult("llm_manager", ServiceStatus.DEGRADED, "Slow response", datetime.now(timezone.utc)),
            HealthCheckResult("database", ServiceStatus.HEALTHY, "OK", datetime.now(timezone.utc)),
            HealthCheckResult("redis", ServiceStatus.DEGRADED, "High latency", datetime.now(timezone.utc)),
        ]
        
        checker.run_all_health_checks = AsyncMock(return_value=(True, degraded_results))
        
        result = await checker.validate_startup(fail_on_critical=True)
        
        # Degraded is considered acceptable for critical services
        assert result is True


class TestConvenienceFunction(BaseIntegrationTest):
    """Test validate_startup_health convenience function."""
    
    async def test_validate_startup_health_function_success(self):
        """Test validate_startup_health convenience function success path."""
        app = FastAPI()
        
        # Mock the StartupHealthChecker class
        with patch('netra_backend.app.startup_health_checks.StartupHealthChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker.validate_startup.return_value = True
            mock_checker_class.return_value = mock_checker
            
            result = await validate_startup_health(app, fail_on_critical=True)
        
        assert result is True
        
        # Verify checker was created with correct app
        mock_checker_class.assert_called_once_with(app)
        
        # Verify validate_startup was called with correct parameters
        mock_checker.validate_startup.assert_called_once_with(fail_on_critical=True)
        
    async def test_validate_startup_health_function_failure(self):
        """Test validate_startup_health convenience function failure path."""
        app = FastAPI()
        
        with patch('netra_backend.app.startup_health_checks.StartupHealthChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker.validate_startup.side_effect = RuntimeError("Health check failed")
            mock_checker_class.return_value = mock_checker
            
            with pytest.raises(RuntimeError) as excinfo:
                await validate_startup_health(app, fail_on_critical=True)
        
        assert "Health check failed" in str(excinfo.value)
        
        # Verify checker was created and called
        mock_checker_class.assert_called_once_with(app)
        mock_checker.validate_startup.assert_called_once_with(fail_on_critical=True)
        
    async def test_validate_startup_health_function_default_parameters(self):
        """Test validate_startup_health with default parameters."""
        app = FastAPI()
        
        with patch('netra_backend.app.startup_health_checks.StartupHealthChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker.validate_startup.return_value = True
            mock_checker_class.return_value = mock_checker
            
            result = await validate_startup_health(app)  # No fail_on_critical specified
        
        assert result is True
        
        # Verify default parameter was used (fail_on_critical=True by default)
        mock_checker.validate_startup.assert_called_once_with(fail_on_critical=True)
        
    async def test_validate_startup_health_function_explicit_false(self):
        """Test validate_startup_health with explicit fail_on_critical=False."""
        app = FastAPI()
        
        with patch('netra_backend.app.startup_health_checks.StartupHealthChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker.validate_startup.return_value = False
            mock_checker_class.return_value = mock_checker
            
            result = await validate_startup_health(app, fail_on_critical=False)
        
        assert result is False
        
        # Verify parameter was passed correctly
        mock_checker.validate_startup.assert_called_once_with(fail_on_critical=False)


class TestCriticalVsOptionalServiceBehavior(BaseIntegrationTest):
    """Test the behavior difference between critical and optional services."""
    
    async def test_critical_services_block_startup(self):
        """Test critical services block startup when unhealthy."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock critical service as unhealthy
        critical_unhealthy = HealthCheckResult(
            service_name="database",  # Critical service
            status=ServiceStatus.UNHEALTHY,
            message="Cannot connect",
            check_time=datetime.now(timezone.utc)
        )
        
        checker.run_all_health_checks = AsyncMock(return_value=(False, [critical_unhealthy]))
        
        with pytest.raises(RuntimeError):
            await checker.validate_startup(fail_on_critical=True)
            
    async def test_optional_services_dont_block_startup(self):
        """Test optional services don't block startup when unhealthy."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Mock optional service as unhealthy but critical services healthy
        results = [
            HealthCheckResult("llm_manager", ServiceStatus.HEALTHY, "OK", datetime.now(timezone.utc)),
            HealthCheckResult("database", ServiceStatus.HEALTHY, "OK", datetime.now(timezone.utc)),
            HealthCheckResult("redis", ServiceStatus.HEALTHY, "OK", datetime.now(timezone.utc)),
            HealthCheckResult("clickhouse", ServiceStatus.UNHEALTHY, "Failed", datetime.now(timezone.utc))  # Optional
        ]
        
        checker.run_all_health_checks = AsyncMock(return_value=(True, results))
        
        # Should not raise exception despite optional service being unhealthy
        result = await checker.validate_startup(fail_on_critical=True)
        assert result is True
        
    def test_critical_services_list_matches_expectations(self):
        """Test CRITICAL_SERVICES constant contains expected services."""
        expected_critical = {'llm_manager', 'database', 'redis'}
        actual_critical = set(StartupHealthChecker.CRITICAL_SERVICES)
        
        assert actual_critical == expected_critical
        
    def test_optional_services_list_matches_expectations(self):
        """Test OPTIONAL_SERVICES constant contains expected services."""
        expected_optional = {'clickhouse', 'websocket_manager'}
        actual_optional = set(StartupHealthChecker.OPTIONAL_SERVICES)
        
        assert actual_optional == expected_optional
        
    def test_no_overlap_between_critical_and_optional(self):
        """Test no services are listed as both critical and optional."""
        critical_set = set(StartupHealthChecker.CRITICAL_SERVICES)
        optional_set = set(StartupHealthChecker.OPTIONAL_SERVICES)
        
        overlap = critical_set.intersection(optional_set)
        assert len(overlap) == 0, f"Services listed as both critical and optional: {overlap}"


class TestLatencyMeasurement(BaseIntegrationTest):
    """Test latency measurement in health checks."""
    
    async def test_latency_measurement_successful_check(self):
        """Test latency is measured for successful health checks."""
        app = FastAPI()
        
        # Mock LLM manager that takes some time
        mock_llm_manager = Mock()
        mock_llm_manager.ask_llm = Mock()
        mock_llm_manager.get_llm_config = Mock()
        mock_llm_manager.llm_configs = {"gpt-4": {}}
        
        app.state.llm_manager = mock_llm_manager
        checker = StartupHealthChecker(app)
        
        # Add a small delay to simulate processing time
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_time = Mock()
            # Simulate 50ms elapsed time
            mock_time.time.side_effect = [0.0, 0.05]  # Start and end times
            mock_loop.return_value = mock_time
            
            result = await checker.check_llm_manager()
        
        assert result.latency_ms is not None
        # Should be around 50ms (50.0 milliseconds)
        assert result.latency_ms == 50.0
        
    async def test_latency_not_measured_for_failed_checks(self):
        """Test latency is not measured for failed health checks."""
        app = FastAPI()
        # No llm_manager in app.state (will fail immediately)
        checker = StartupHealthChecker(app)
        
        result = await checker.check_llm_manager()
        
        # Failed check should not have latency measurement
        assert result.latency_ms is None
        assert result.status == ServiceStatus.NOT_CONFIGURED


class TestErrorHandlingAndLogging(BaseIntegrationTest):
    """Test error handling and logging across all health checks."""
    
    async def test_exception_handling_preserves_service_name(self):
        """Test exceptions in health checks preserve service name in results."""
        app = FastAPI()
        
        # Mock LLM manager that raises exception
        mock_llm_manager = Mock()
        type(mock_llm_manager).ask_llm = Mock(side_effect=RuntimeError("Unexpected error"))
        
        app.state.llm_manager = mock_llm_manager
        checker = StartupHealthChecker(app)
        
        result = await checker.check_llm_manager()
        
        assert result.service_name == "llm_manager"
        assert result.status == ServiceStatus.UNHEALTHY
        assert "Exception during health check" in result.message
        assert "Unexpected error" in result.message
        
    async def test_logging_occurs_for_all_health_check_failures(self):
        """Test that failures in health checks are properly logged."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        # Test database failure logging
        app.state.db_session_factory = Mock(side_effect=Exception("DB error"))
        
        with patch('netra_backend.app.startup_health_checks.logger') as mock_logger:
            await checker.check_database()
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            logged_message = mock_logger.error.call_args[0][0]
            assert "Health check failed for database" in logged_message
            
    async def test_health_check_results_timestamp_accuracy(self):
        """Test health check results have accurate timestamps."""
        app = FastAPI()
        checker = StartupHealthChecker(app)
        
        before_check = datetime.now(timezone.utc)
        result = await checker.check_llm_manager()  # Will fail (not configured)
        after_check = datetime.now(timezone.utc)
        
        # Timestamp should be between before and after
        assert before_check <= result.check_time <= after_check
        assert result.check_time.tzinfo == timezone.utc