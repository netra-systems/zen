"""Critical regression tests for WebSocket metrics collection.

These tests ensure the WebSocket metrics collection handles edge cases properly, 
especially when connection stats are missing or malformed.

Business Value: Prevents metrics collection failures from impacting monitoring.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
from typing import Any, Dict

import pytest
from netra_backend.app.monitoring.metrics_collector import MetricsCollector, WebSocketMetrics

from netra_backend.app.agents.base.interface import ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus

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
        mock_manager = MagicNone  # TODO: Use real service instance
        mock_orchestrator = AsyncNone  # TODO: Use real service instance
        
        # Simulate successful result but missing connection_stats key
        mock_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            result={"other_data": "value"},  # Missing connection_stats
            error=None,
            metadata={}
        )
        mock_orchestrator.get_connection_stats.return_value = mock_result
        mock_manager.orchestrator = mock_orchestrator
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.monitoring.metrics_collector.get_connection_monitor', 
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
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicNone  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_orchestrator = AsyncNone  # TODO: Use real service instance
        
        # Simulate successful status but None result
        mock_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            result=None,  # None result
            error=None,
            metadata={}
        )
        mock_orchestrator.get_connection_stats.return_value = mock_result
        mock_manager.orchestrator = mock_orchestrator
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.monitoring.metrics_collector.get_connection_monitor',
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
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicNone  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_orchestrator = AsyncNone  # TODO: Use real service instance
        
        # Simulate failed result
        mock_result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            result=None,
            error="Connection stats retrieval failed",
            metadata={}
        )
        mock_orchestrator.get_connection_stats.return_value = mock_result
        mock_manager.orchestrator = mock_orchestrator
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.monitoring.metrics_collector.get_connection_monitor',
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
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicNone  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_orchestrator = AsyncNone  # TODO: Use real service instance
        
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
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.monitoring.metrics_collector.get_connection_monitor',
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
        from netra_backend.app.websocket_core import (
    WebSocketManager as ConnectionManager,
        )
        
        manager = ConnectionManager()
        
        # Test with None result
        # Mock: Generic component isolation for controlled unit testing
        mock_result = MagicNone  # TODO: Use real service instance
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