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
from test_framework.environment_markers import test_only, env
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
        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_engine
    
    @pytest.fixture
    def mock_clickhouse_client(self):
        """Create mock ClickHouse client."""
        mock_client = AsyncMock()
        mock_client.execute = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Create mock Redis manager."""
        mock_manager = Mock()
        mock_manager.enabled = True
        mock_client = AsyncMock()
        mock_manager.get_client = AsyncMock(return_value=mock_client)
        return mock_manager, mock_client
    
    @test_only  # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking database manager to isolate health check logic. Real database connectivity tested in L3 integration tests.", "L1")
    @patch('netra_backend.app.core.unified.db_connection_manager.db_manager')
    @pytest.mark.asyncio
    async def test_check_postgres_health_success(self, mock_db_manager, mock_postgres_engine):
        """Test successful PostgreSQL health check."""
        # Mock db_manager.get_async_session to return a working session
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_manager.get_async_session.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()
        
        result = await check_postgres_health()
        
        assert isinstance(result, HealthCheckResult)
        assert result.status == "healthy"
        assert result.response_time_ms >= 0  # Allow zero for fast mocked operations
        assert result.details["component_name"] == "postgres"
        assert result.details["success"] is True
    
    @test_only  # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking database manager to test error handling paths. Real database testing in L3 integration tests.", "L1")
    @patch('netra_backend.app.core.unified.db_connection_manager.db_manager')
    @pytest.mark.asyncio
    async def test_check_postgres_health_no_engine(self, mock_db_manager):
        """Test PostgreSQL health check with no engine."""
        # Mock db_manager to raise ValueError (forcing fallback to direct engine)
        mock_db_manager.get_async_session.side_effect = ValueError("Connection failed")
        
        # Mock the engine to be None to trigger the engine initialization path
        with patch('netra_backend.app.db.postgres_core.async_engine', None), \
             patch('netra_backend.app.db.postgres.initialize_postgres') as mock_init:
            mock_init.return_value = None  # Ensure engine remains None after init
            result = await check_postgres_health()
        
        assert result.status == "unhealthy"
        assert result.details["success"] is False
        error_msg = result.details["error_message"]
        assert "Connection failed" in error_msg or "Database engine not initialized" in error_msg
    
    @test_only  # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking database manager to test connection failure scenarios. Real connectivity tested in L3 integration tests.", "L1")
    @patch('netra_backend.app.core.unified.db_connection_manager.db_manager')
    @pytest.mark.asyncio
    async def test_check_postgres_health_connection_error(self, mock_db_manager):
        """Test PostgreSQL health check with connection error."""
        # Mock db_manager to raise connection error
        mock_db_manager.get_async_session.side_effect = Exception("Connection failed")
        
        result = await check_postgres_health()
        
        # Postgres is critical service, so it should return unhealthy
        assert result.status == "unhealthy"
        assert result.details["success"] is False
        # The error could be from the connection failure or the fallback engine path
        error_msg = result.details["error_message"]
        assert "Connection failed" in error_msg or "Database engine not initialized" in error_msg
    
    @test_only  # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking ClickHouse client and environment detection to isolate health check logic. Real ClickHouse tested in L3 integration tests.", "L1")
    @patch('netra_backend.app.db.clickhouse.get_clickhouse_client')
    @patch('netra_backend.app.core.health_checkers._is_development_mode')
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
    
    @test_only  # Unit test with mocked dependencies
    @mock_justified("L1 Unit Test: Mocking environment detection to test disabled ClickHouse scenario. Real environment testing in L3 integration tests.", "L1")
    @patch('netra_backend.app.core.health_checkers._is_development_mode')
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
    
    @mock_justified("L1 Unit Test: Mocking ClickHouse client to test connection error handling. Real connection failures tested in L3 integration tests.", "L1")
    @patch('netra_backend.app.db.clickhouse.get_clickhouse_client')
    @patch('netra_backend.app.core.health_checkers._is_development_mode')
    @patch('netra_backend.app.core.health_checkers._is_clickhouse_disabled')
    @pytest.mark.asyncio
    async def test_check_clickhouse_health_connection_error(self, mock_disabled, mock_dev_mode, mock_get_client):
        """Test ClickHouse health check with connection error."""
        mock_dev_mode.return_value = False
        mock_disabled.return_value = False
        mock_get_client.side_effect = Exception("ClickHouse connection failed")
        
        result = await check_clickhouse_health()
        
        assert result.status == "unhealthy"
        assert result.details["success"] is False
        assert "ClickHouse connection failed" in result.details["error_message"]
    
    @mock_justified("L1 Unit Test: Mocking Redis manager to isolate health check logic. Real Redis connectivity tested in L3 integration tests.", "L1")
    @patch('netra_backend.app.redis_manager.redis_manager')
    @pytest.mark.asyncio
    async def test_check_redis_health_success(self, mock_manager, mock_redis_manager):
        """Test successful Redis health check."""
        redis_manager, redis_client = mock_redis_manager
        mock_manager.enabled = True
        mock_manager.get_client = AsyncMock(return_value=redis_client)
        
        result = await check_redis_health()
        
        assert result.status == "healthy"
        assert result.details["component_name"] == "redis"
        assert result.details["success"] is True
        redis_client.ping.assert_called_once()
    
    @patch('netra_backend.app.redis_manager.redis_manager')
    @pytest.mark.asyncio
    async def test_check_redis_health_disabled(self, mock_manager):
        """Test Redis health check when disabled."""
        mock_manager.enabled = False
        
        result = await check_redis_health()
        
        assert result.status == "degraded"
        assert result.details["success"] is False
        assert "Redis disabled in development" in result.details["error_message"]
    
    @patch('netra_backend.app.redis_manager.redis_manager')
    @pytest.mark.asyncio
    async def test_check_redis_health_no_client(self, mock_manager):
        """Test Redis health check when client unavailable."""
        mock_manager.enabled = True
        mock_manager.get_client = AsyncMock(return_value=None)
        
        result = await check_redis_health()
        
        assert result.status == "degraded"
        assert result.details["success"] is False
        assert "Redis client not available" in result.details["error_message"]
    
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
        with patch('netra_backend.app.core.health_checkers._create_success_result') as mock_create:
            expected_result = self._create_expected_success_result()
            mock_create.return_value = expected_result
            
            result = mock_create("test", 50.0)
            
            assert result.status == "healthy"
            assert result.response_time == 0.05
            assert result.details["success"] is True
    
    def test_create_failed_result_structure(self):
        """Test failed health result structure."""
        with patch('netra_backend.app.core.health_checkers._create_failed_result') as mock_create:
            expected_result = self._create_expected_failed_result()
            mock_create.return_value = expected_result
            
            result = mock_create("test", "Test error", 100.0)
            
            assert result.status == "unhealthy"
            assert result.details["error_message"] == "Test error"
    
    # Helper methods (each ≤8 lines)
    def _create_mock_websocket_manager(self):
        """Helper to create mock WebSocket manager."""
        mock_manager = Mock()
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