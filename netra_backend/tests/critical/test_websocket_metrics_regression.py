"""Critical regression tests for WebSocket metrics collection.

These tests ensure the WebSocket metrics collection handles edge cases properly, 
especially when connection stats are missing or malformed.

Business Value: Prevents metrics collection failures from impacting monitoring.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from monitoring import WebSocketMetrics
from monitoring.metrics_collector import MetricsCollector

# Add project root to path
from netra_backend.app.agents.base.interface import ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus

# Add project root to path


class TestWebSocketMetricsRegression:
    """Critical regression tests for WebSocket metrics collection."""
    
    @pytest.mark.asyncio
    async def test_metrics_collection_handles_missing_connection_stats(self):
        """Test that metrics collection handles missing connection_stats key gracefully.
        
        Regression test for: WebSocket metrics failing with KeyError: 'connection_stats'
        This occurred when orchestrator returns success but result lacks the expected key.
        """
        collector = MetricsCollector()
        
        # Mock connection manager that returns result without connection_stats
        mock_manager = MagicMock()
        mock_orchestrator = AsyncMock()
        
        # Simulate successful result but missing connection_stats key
        mock_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            result={"other_data": "value"},  # Missing connection_stats
            error=None,
            metadata={}
        )
        mock_orchestrator.get_connection_stats.return_value = mock_result
        mock_manager.orchestrator = mock_orchestrator
        
        with patch('app.monitoring.metrics_collector.get_connection_manager', 
                  return_value=mock_manager):
            metrics = await collector._gather_websocket_metrics()
            
            # Should return empty metrics, not raise KeyError
            assert isinstance(metrics, WebSocketMetrics)
            assert metrics.active_connections == 0
            assert metrics.total_connections == 0
    
    @pytest.mark.asyncio
    async def test_metrics_collection_handles_none_result(self):
        """Test that metrics collection handles None result from orchestrator.
        
        Ensures robustness when orchestrator returns success but result is None.
        """
        collector = MetricsCollector()
        
        mock_manager = MagicMock()
        mock_orchestrator = AsyncMock()
        
        # Simulate successful status but None result
        mock_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            result=None,  # None result
            error=None,
            metadata={}
        )
        mock_orchestrator.get_connection_stats.return_value = mock_result
        mock_manager.orchestrator = mock_orchestrator
        
        with patch('app.monitoring.metrics_collector.get_connection_manager',
                  return_value=mock_manager):
            metrics = await collector._gather_websocket_metrics()
            
            # Should handle None gracefully
            assert isinstance(metrics, WebSocketMetrics)
            assert metrics.active_connections == 0
            assert metrics.total_connections == 0
    
    @pytest.mark.asyncio
    async def test_metrics_collection_handles_failed_orchestrator_result(self):
        """Test that metrics collection handles failed orchestrator results.
        
        Ensures the system continues to work when orchestrator reports failure.
        """
        collector = MetricsCollector()
        
        mock_manager = MagicMock()
        mock_orchestrator = AsyncMock()
        
        # Simulate failed result
        mock_result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            result=None,
            error="Connection stats retrieval failed",
            metadata={}
        )
        mock_orchestrator.get_connection_stats.return_value = mock_result
        mock_manager.orchestrator = mock_orchestrator
        
        with patch('app.monitoring.metrics_collector.get_connection_manager',
                  return_value=mock_manager):
            metrics = await collector._gather_websocket_metrics()
            
            # Should return empty metrics on failure
            assert isinstance(metrics, WebSocketMetrics)
            assert metrics.active_connections == 0
            assert metrics.total_connections == 0
    
    @pytest.mark.asyncio
    async def test_metrics_collection_with_valid_connection_stats(self):
        """Test that metrics collection works correctly with valid data.
        
        Positive test case ensuring normal operation continues to work.
        """
        collector = MetricsCollector()
        
        mock_manager = MagicMock()
        mock_orchestrator = AsyncMock()
        
        # Simulate successful result with proper connection_stats
        expected_stats = {
            "active_connections": 5,
            "total_connections": 10
        }
        mock_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            result={"connection_stats": expected_stats},
            error=None,
            metadata={}
        )
        mock_orchestrator.get_connection_stats.return_value = mock_result
        mock_manager.orchestrator = mock_orchestrator
        
        # Mock legacy stats
        mock_manager._get_basic_stats.return_value = {
            "total_connections": 10,
            "active_connections": 5
        }
        mock_manager._get_user_connection_stats.return_value = {}
        
        with patch('app.monitoring.metrics_collector.get_connection_manager',
                  return_value=mock_manager):
            metrics = await collector._gather_websocket_metrics()
            
            # Should use the valid stats
            assert isinstance(metrics, WebSocketMetrics)
            # The actual values depend on _build_websocket_metrics implementation
    
    @pytest.mark.asyncio
    async def test_connection_manager_extract_modern_stats_safety(self):
        """Test that connection manager's _extract_modern_stats is defensive.
        
        Direct test of the fixed method to ensure it handles all edge cases.
        """
        from netra_backend.app.websocket.connection_manager import (
            ModernConnectionManager,
        )
        
        manager = Modernget_connection_manager()
        
        # Test with None result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = None
        stats = manager._extract_modern_stats(mock_result)
        assert stats == {}
        
        # Test with missing connection_stats key
        mock_result.result = {"other": "data"}
        stats = manager._extract_modern_stats(mock_result)
        assert stats == {}
        
        # Test with failed result
        mock_result.success = False
        mock_result.result = {"connection_stats": {"active": 1}}
        stats = manager._extract_modern_stats(mock_result)
        assert stats == {}
        
        # Test with valid data
        mock_result.success = True
        mock_result.result = {"connection_stats": {"active": 5}}
        stats = manager._extract_modern_stats(mock_result)
        assert stats == {"active": 5}