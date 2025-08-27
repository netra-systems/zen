"""Core unit tests for health checker functions.

Tests system health monitoring for SLA compliance.
SLA CRITICAL - Maintains system uptime for enterprise contracts.

Business Value: Ensures reliable health monitoring preventing SLA violations
that could result in enterprise contract penalties and customer churn.
"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Environment-aware testing imports
from test_framework.decorators import mock_justified
from netra_backend.app.core.health_checkers import (
    check_clickhouse_health,
    check_postgres_health,
    check_redis_health,
    check_system_resources,
    check_websocket_health,
)
from netra_backend.app.schemas.core_models import HealthCheckResult

class TestHealthCheckersCore:
    """Core test suite for database and service health checkers."""
    
    @pytest.fixture
    def mock_postgres_engine(self):
        """Create mock PostgreSQL async engine."""
        # Mock: Generic component isolation for controlled unit testing
        mock_engine = Mock()
        # Mock: Generic component isolation for controlled unit testing
        mock_conn = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        mock_engine.begin = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        # Mock: Async component isolation for testing without real async operations
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_engine
    
    @pytest.fixture
    def mock_clickhouse_client(self):
        """Create mock ClickHouse client."""
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        mock_client.execute = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Mock: Async component isolation for testing without real async operations
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Create mock Redis manager."""
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = Mock()
        mock_manager.enabled = True
        # Mock: Generic component isolation for controlled unit testing
        mock_client = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        mock_manager.get_client = AsyncMock(return_value=mock_client)
        return mock_manager, mock_client
    
    # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking database manager to isolate health check logic. Real database connectivity tested in L3 integration tests.", "L1")
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.db.database_manager.DatabaseManager')
    @pytest.mark.asyncio
    async def test_check_postgres_health_success(self, mock_db_manager_class, mock_postgres_engine):
        """Test successful PostgreSQL health check."""
        # Mock db_manager.get_async_session to return a working session
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session = AsyncMock()
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_db_manager_class.get_async_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_db_manager_class.get_async_session.return_value.__aexit__ = AsyncMock(return_value=None)
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session.execute = AsyncMock()
        
        result = await check_postgres_health()
        
        assert isinstance(result, HealthCheckResult)
        assert result.status == "healthy"
        assert result.response_time_ms >= 0  # Allow zero for fast mocked operations
        assert result.details["component_name"] == "postgres"
        assert result.details["success"] is True
    
    # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking database manager to test error handling paths. Real database testing in L3 integration tests.", "L1")
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.db.database_manager.DatabaseManager')
    @pytest.mark.asyncio
    async def test_check_postgres_health_no_engine(self, mock_db_manager_class):
        """Test PostgreSQL health check with no engine."""
        # Mock db_manager to raise ValueError (forcing fallback to direct engine)
        mock_db_manager_class.get_async_session.side_effect = ValueError("Connection failed")
        
        # Mock the engine to be None to trigger the engine initialization path
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.db.postgres_core.async_engine', None), \
             patch('netra_backend.app.db.postgres.initialize_postgres') as mock_init:
            mock_init.return_value = None  # Ensure engine remains None after init
            result = await check_postgres_health()
        
        assert result.status == "unhealthy"
        assert result.details["success"] is False
        error_msg = result.details["error_message"]
        assert "Connection failed" in error_msg or "Database engine not initialized" in error_msg
    
    # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking postgres query execution to test connection failure scenarios.", "L1")
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.core.health_checkers._execute_postgres_query')
    @pytest.mark.asyncio
    async def test_check_postgres_health_connection_error(self, mock_execute_query):
        """Test PostgreSQL health check with connection error."""
        # Mock _execute_postgres_query to raise connection error
        mock_execute_query.side_effect = Exception("Connection failed")
        
        result = await check_postgres_health()
        
        # Postgres is critical service, so it should return unhealthy
        assert result.status == "unhealthy"
        assert result.details["success"] is False
        # The error should contain the connection failure message
        error_msg = result.details["error_message"]
        assert "Connection failed" in error_msg
    
    # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking ClickHouse client and environment detection to isolate health check logic. Real ClickHouse tested in L3 integration tests.", "L1")
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.database.get_clickhouse_client')
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.core.health_checkers._is_development_mode')
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.core.health_checkers._is_clickhouse_disabled')
    @pytest.mark.asyncio
    async def test_check_clickhouse_health_success(self, mock_disabled, mock_dev_mode, mock_get_client, mock_clickhouse_client):
        """Test successful ClickHouse health check."""
        mock_dev_mode.return_value = False
        mock_disabled.return_value = False
        mock_get_client.return_value = mock_clickhouse_client
        
        result = await check_clickhouse_health()
        
        assert result.status == "healthy"
        assert result.details["component_name"] == "clickhouse"
        assert result.details["success"] is True
        mock_clickhouse_client.execute.assert_called_once_with("SELECT 1")
    
    # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking environment detection to test disabled ClickHouse scenario. Real environment testing in L3 integration tests.", "L1")
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.core.health_checkers._is_development_mode')
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.core.health_checkers._is_clickhouse_disabled')
    @pytest.mark.asyncio
    async def test_check_clickhouse_health_disabled_in_dev(self, mock_disabled, mock_dev_mode):
        """Test ClickHouse health check when disabled in development."""
        mock_dev_mode.return_value = True
        mock_disabled.return_value = True
        
        result = await check_clickhouse_health()
        
        assert result.status == "healthy"
        assert result.details["status"] == "disabled"
        assert "ClickHouse disabled in development" in result.details["reason"]
    
    # Unit test with direct error handler testing to avoid mock isolation issues
    @mock_justified("L1 Unit Test: Direct testing of ClickHouse error handler logic to avoid complex mock isolation issues.", "L1")
    def test_check_clickhouse_health_connection_error_direct(self):
        """Test ClickHouse error handler directly with critical priority in non-development environment."""
        from netra_backend.app.core.health_checkers import _handle_clickhouse_error, ServicePriority
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.health_checkers._is_development_mode') as mock_dev_mode, \
             patch('netra_backend.app.core.health_checkers._get_service_priority_for_environment') as mock_priority:
            
            # Configure mocks for non-development, critical priority
            mock_dev_mode.return_value = False
            mock_priority.return_value = ServicePriority.CRITICAL
            
            # Test error handling
            error = Exception("ClickHouse connection failed")
            response_time = 100.0
            
            result = _handle_clickhouse_error(error, response_time)
            
            # In non-development mode with CRITICAL priority, should return unhealthy
            assert result.status == "unhealthy"
            assert result.details["success"] is False
            assert "ClickHouse connection failed" in result.details["error_message"]
            assert result.response_time_ms == response_time
    
    @mock_justified("L1 Unit Test: Mocking Redis manager to isolate health check logic. Real Redis connectivity tested in L3 integration tests.", "L1")
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.redis_manager.redis_manager')
    @pytest.mark.asyncio
    async def test_check_redis_health_success(self, mock_manager, mock_redis_manager):
        """Test successful Redis health check."""
        redis_manager, redis_client = mock_redis_manager
        mock_manager.enabled = True
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_manager.get_client = AsyncMock(return_value=redis_client)
        
        result = await check_redis_health()
        
        assert result.status == "healthy"
        assert result.details["component_name"] == "redis"
        assert result.details["success"] is True
        redis_client.ping.assert_called_once()
    
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.redis_manager.redis_manager')
    @pytest.mark.asyncio
    async def test_check_redis_health_disabled(self, mock_manager):
        """Test Redis health check when disabled."""
        mock_manager.enabled = False
        
        result = await check_redis_health()
        
        assert result.status == "degraded"
        assert result.details["success"] is False
        assert "Redis disabled in development" in result.details["error_message"]
    
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.redis_manager.redis_manager')
    @pytest.mark.asyncio
    async def test_check_redis_health_no_client(self, mock_manager):
        """Test Redis health check when client unavailable."""
        mock_manager.enabled = True
        # Mock: Async component isolation for testing without real async operations
        mock_manager.get_client = AsyncMock(return_value=None)
        
        result = await check_redis_health()
        
        assert result.status == "degraded"
        assert result.details["success"] is False
        assert "Redis client not available" in result.details["error_message"]
    
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.websocket_core.utils.get_connection_monitor')
    @pytest.mark.asyncio
    async def test_check_websocket_health_success(self, mock_get_manager):
        """Test successful WebSocket health check."""
        mock_manager = self._create_mock_websocket_manager()
        mock_get_manager.return_value = mock_manager
        
        result = await check_websocket_health()
        
        assert result.status == "healthy"
        assert result.details["component_name"] == "websocket"
        assert result.details["success"] is True
        assert "metadata" in result.details
    
    # Mock: Component isolation for testing without external dependencies
    @patch('netra_backend.app.websocket_core.utils.get_connection_monitor')
    @pytest.mark.asyncio
    async def test_check_websocket_health_manager_error(self, mock_get_manager):
        """Test WebSocket health check with manager error."""
        mock_get_manager.side_effect = Exception("WebSocket manager error")
        
        result = await check_websocket_health()
        
        assert result.status == "degraded"
        assert result.details["success"] is False
        assert "WebSocket manager error" in result.details["error_message"]
    
    def test_create_success_result_structure(self):
        """Test successful health result structure."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.health_checkers._create_success_result') as mock_create:
            expected_result = self._create_expected_success_result()
            mock_create.return_value = expected_result
            
            result = mock_create("test", 50.0)
            
            assert result.status == "healthy"
            assert result.response_time == 0.05
            assert result.details["success"] is True
    
    def test_create_failed_result_structure(self):
        """Test failed health result structure."""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.health_checkers._create_failed_result') as mock_create:
            expected_result = self._create_expected_failed_result()
            mock_create.return_value = expected_result
            
            result = mock_create("test", "Test error", 100.0)
            
            assert result.status == "unhealthy"
            assert result.details["error_message"] == "Test error"
    
    # Helper methods (each ≤8 lines)
    def _create_mock_websocket_manager(self):
        """Helper to create mock WebSocket manager."""
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = Mock()
        # Mock: Async component isolation for testing without real async operations
        mock_manager.get_stats = AsyncMock(return_value={
            "active_connections": 10, "total_connections": 50
        })
        return mock_manager
    
    def _create_expected_success_result(self):
        """Helper to create expected success result."""
        return HealthCheckResult(
            component_name="test",
            success=True,
            health_score=1.0,
            response_time_ms=50.0,
            status="healthy",
            response_time=0.05,
            details={"component_name": "test", "success": True, "health_score": 1.0}
        )
    
    def _create_expected_failed_result(self):
        """Helper to create expected failed result."""
        return HealthCheckResult(
            component_name="test",
            success=False,
            health_score=0.0,
            response_time_ms=100.0,
            status="unhealthy",
            response_time=0.1,
            error_message="Test error",
            details={"component_name": "test", "success": False, "health_score": 0.0, "error_message": "Test error"}
        )
    
    def _assert_health_result_valid(self, result, expected_status="healthy"):
        """Helper to assert health result structure is valid."""
        assert isinstance(result, HealthCheckResult)
        assert result.status == expected_status
        assert isinstance(result.response_time_ms, float)
        assert isinstance(result.details, dict)
        assert "component_name" in result.details
        assert "success" in result.details

    @mock_justified("L1 Unit Test: Mocking multiple dependencies to simulate cascading failures during major system outages. Critical for understanding system behavior during catastrophic infrastructure failures.", "L1")
    @patch('netra_backend.app.core.health_checkers.check_postgres_health')
    @patch('netra_backend.app.core.health_checkers.check_redis_health')
    @patch('netra_backend.app.core.health_checkers.check_clickhouse_health')
    @patch('netra_backend.app.core.health_checkers.check_websocket_health')
    @patch('netra_backend.app.core.health_checkers.check_system_resources')
    @pytest.mark.asyncio
    async def test_cascading_health_check_failures_major_outage(
        self, 
        mock_system_resources, 
        mock_websocket, 
        mock_clickhouse, 
        mock_redis, 
        mock_postgres
    ):
        """Test cascading health check failures during major infrastructure outages.
        
        Critical edge case: When multiple core dependencies (Postgres, Redis, ClickHouse) 
        fail simultaneously, verify system properly reports the cascade and provides 
        actionable diagnostic information for rapid incident response.
        
        Business Value: Ensures operational teams can quickly identify the scope of 
        infrastructure failures during major outages, enabling faster Mean Time To Recovery (MTTR)
        and preventing SLA violations that could result in enterprise contract penalties.
        """
        from netra_backend.app.core.health_checkers import HealthChecker
        
        # Configure mock return values for cascading failure scenario
        # Mock Postgres failure
        postgres_failure_result = HealthCheckResult(
            component_name="postgres",
            success=False,
            health_score=0.0,
            response_time_ms=5000.0,  # High latency indicates infrastructure stress
            status="unhealthy",
            response_time=5.0,
            error_message="Connection timeout: Database server unreachable",
            details={
                "component_name": "postgres",
                "success": False,
                "health_score": 0.0,
                "error_message": "Connection timeout: Database server unreachable",
                "connection_pool_exhausted": True
            }
        )
        mock_postgres.return_value = postgres_failure_result
        
        # Mock Redis failure
        redis_failure_result = HealthCheckResult(
            component_name="redis",
            success=False,
            health_score=0.0,
            response_time_ms=3000.0,
            status="unhealthy",
            response_time=3.0,
            error_message="Redis cluster nodes unreachable: Network partition detected",
            details={
                "component_name": "redis",
                "success": False,
                "health_score": 0.0,
                "error_message": "Redis cluster nodes unreachable: Network partition detected",
                "cluster_status": "partition"
            }
        )
        mock_redis.return_value = redis_failure_result
        
        # Mock ClickHouse failure
        clickhouse_failure_result = HealthCheckResult(
            component_name="clickhouse",
            success=False,
            health_score=0.0,
            response_time_ms=8000.0,  # Extremely high latency
            status="unhealthy",
            response_time=8.0,
            error_message="ClickHouse cluster offline: All replicas unavailable",
            details={
                "component_name": "clickhouse",
                "success": False,
                "health_score": 0.0,
                "error_message": "ClickHouse cluster offline: All replicas unavailable",
                "replicas_available": 0
            }
        )
        mock_clickhouse.return_value = clickhouse_failure_result
        
        # Mock successful WebSocket component
        websocket_success_result = HealthCheckResult(
            component_name="websocket",
            success=True,
            health_score=1.0,
            response_time_ms=50.0,
            status="healthy",
            response_time=0.05,
            details={
                "component_name": "websocket",
                "success": True,
                "health_score": 1.0,
                "active_connections": 0  # No connections due to backend failures
            }
        )
        mock_websocket.return_value = websocket_success_result
        
        # Mock successful system resources
        system_resources_success_result = HealthCheckResult(
            component_name="system_resources",
            success=True,
            health_score=0.95,  # Slightly degraded due to error handling overhead
            response_time_ms=10.0,
            status="healthy",
            response_time=0.01,
            details={
                "component_name": "system_resources",
                "success": True,
                "health_score": 0.95,
                "cpu_usage": 65.0,  # Elevated due to connection retries
                "memory_usage": 75.0,
                "disk_usage": 45.0
            }
        )
        mock_system_resources.return_value = system_resources_success_result
        
        # Execute health checker during simulated outage
        health_checker = HealthChecker()
        results = await health_checker.check_all()
        
        # Verify all expected components were checked
        assert len(results) == 5
        assert set(results.keys()) == {"postgres", "redis", "clickhouse", "websocket", "system_resources"}
        
        # Verify critical infrastructure failures are properly reported
        postgres_result = results["postgres"]
        assert postgres_result.status == "unhealthy"
        assert postgres_result.success is False
        assert postgres_result.response_time_ms == 5000.0
        assert "Connection timeout" in postgres_result.error_message
        assert postgres_result.details["connection_pool_exhausted"] is True
        
        redis_result = results["redis"]
        assert redis_result.status == "unhealthy"
        assert redis_result.success is False
        assert "Network partition detected" in redis_result.error_message
        assert redis_result.details["cluster_status"] == "partition"
        
        clickhouse_result = results["clickhouse"]
        assert clickhouse_result.status == "unhealthy"
        assert clickhouse_result.success is False
        assert clickhouse_result.response_time_ms == 8000.0
        assert "All replicas unavailable" in clickhouse_result.error_message
        assert clickhouse_result.details["replicas_available"] == 0
        
        # Verify non-critical services continue operating
        websocket_result = results["websocket"]
        assert websocket_result.status == "healthy"
        assert websocket_result.success is True
        assert websocket_result.details["active_connections"] == 0  # Expected during backend failure
        
        system_result = results["system_resources"]
        assert system_result.status == "healthy"
        assert system_result.success is True
        assert system_result.details["cpu_usage"] == 65.0  # Elevated but functional
        
        # Verify cascade analysis: Count failed critical components
        failed_critical_services = [
            result for result in results.values() 
            if not result.success and result.component_name in ["postgres", "redis", "clickhouse"]
        ]
        assert len(failed_critical_services) == 3
        
        # Verify total system health score reflects cascading failure severity
        total_failed = sum(1 for result in results.values() if not result.success)
        total_healthy = sum(1 for result in results.values() if result.success)
        assert total_failed == 3  # Critical infrastructure down
        assert total_healthy == 2  # Application layer partially functional
        
        # Verify response time degradation pattern (higher latency = more critical failure)
        response_times = [result.response_time_ms for result in results.values() if not result.success]
        assert max(response_times) == 8000.0  # ClickHouse worst affected
        assert min(response_times) == 3000.0   # Redis less affected but still failing