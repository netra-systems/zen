"""Integration tests for agent reliability across system components."""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import components for integration testing
from netra_backend.app.core.agent_reliability_mixin import AgentReliabilityMixin
from netra_backend.app.core.agent_reliability_types import AgentError, AgentHealthStatus
from netra_backend.app.core.fallback_coordinator import FallbackCoordinator
from netra_backend.app.core.json_parsing_utils import (
    comprehensive_json_fix,
    safe_json_parse,
)

class MockReliableAgent(AgentReliabilityMixin):
    """Mock agent with reliability mixin for integration testing."""
    
    def __init__(self, name: str = "MockAgent"):
        self.name = name
        super().__init__()
    
    async def mock_operation(self, should_fail: bool = False, response_data: Any = None):
        """Mock operation for testing."""
        if should_fail:
            raise ValueError("Mock operation failed")
        return response_data or {"success": True, "agent": self.name}

class TestAgentReliabilityIntegration:
    """Integration tests for agent reliability across system components."""
    
    @pytest.fixture
    def reliable_agent(self):
        """Create mock reliable agent."""
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability.circuit_breaker.reset = Mock()
            mock_wrapper.return_value = mock_reliability
            
            agent = MockReliableAgent("TestAgent")
            agent.reliability = mock_reliability
            return agent
    
    def _create_complex_json_test_data(self):
        """Create complex JSON response for testing."""
        return {
            "tool_recommendations": [
                {
                    "tool": "data_analyzer",
                    "parameters": '{"query": "SELECT * FROM metrics", "format": "json"}'
                }
            ],
            "recommendations": '["Optimize query performance", "Add caching layer"]',
            "nested_data": {
                "analysis": '{"findings": ["bottleneck1", "bottleneck2"]}'
            }
        }
    
    def _verify_json_parsing_integration(self, fixed_result):
        """Verify JSON parsing integration results."""
        assert fixed_result["tool_recommendations"][0]["parameters"] == {
            "query": "SELECT * FROM metrics", 
            "format": "json"
        }
        assert fixed_result["recommendations"] == ["Optimize query performance", "Add caching layer"]
    
    def _verify_reliability_tracking(self, reliable_agent):
        """Verify reliability metrics were updated correctly."""
        assert len(reliable_agent.operation_times) == 1
        assert len(reliable_agent.error_history) == 0
    async def test_agent_reliability_with_json_parsing(self, reliable_agent):
        """Test agent reliability with JSON parsing integration."""
        complex_response = self._create_complex_json_test_data()
        reliable_agent.reliability.execute_safely.return_value = complex_response
        
        result = await reliable_agent.execute_with_reliability(
            lambda: reliable_agent.mock_operation(response_data=complex_response),
            "json_processing_operation",
            timeout=10.0
        )
        
        fixed_result = comprehensive_json_fix(result)
        self._verify_json_parsing_integration(fixed_result)
        self._verify_reliability_tracking(reliable_agent)
    
    def _create_mock_health_instance(self):
        """Create mock health monitor instance."""
        mock_health_instance = Mock()
        mock_health_instance.is_emergency_mode_active = AsyncMock(return_value=False)
        mock_health_instance.should_prevent_cascade = AsyncMock(return_value=False)
        mock_health_instance.record_success = AsyncMock()
        mock_health_instance.record_failure = AsyncMock()
        mock_health_instance.update_circuit_breaker_status = AsyncMock()
        mock_health_instance.update_system_health = AsyncMock()
        return mock_health_instance
    
    def _setup_fallback_coordinator_mocks(self, mock_health_monitor, mock_emergency_manager):
        """Setup fallback coordinator with mocks."""
        mock_health_instance = self._create_mock_health_instance()
        mock_emergency_instance = Mock()
        mock_health_monitor.return_value = mock_health_instance
        mock_emergency_manager.return_value = mock_emergency_instance
        
        coordinator = FallbackCoordinator()
        coordinator.health_monitor = mock_health_instance
        coordinator.emergency_manager = mock_emergency_instance
        return coordinator, mock_health_instance
    
    def _setup_coordination_handler_mocks(self, mock_handler_class):
        """Setup coordination handler mocks."""
        mock_handler = AsyncMock()
        mock_handler.execute_with_fallback.return_value = {"coordinated": True, "agent": "TestAgent"}
        mock_handler_class.return_value = mock_handler
        return mock_handler
    
    def _verify_coordination_integration(self, result, mock_handler, mock_health_instance, reliable_agent):
        """Verify coordination integration results."""
        assert result == {"coordinated": True, "agent": "TestAgent"}
        mock_handler.execute_with_fallback.assert_called_once()
        mock_health_instance.record_success.assert_called_once_with("TestAgent")
        assert len(reliable_agent.operation_times) == 1
    
    async def _execute_coordinated_operation(self, coordinator, reliable_agent):
        """Execute coordinated operation through reliability and coordination."""
        async def coordinated_operation():
            return await coordinator.execute_with_coordination(
                "TestAgent",
                lambda: reliable_agent.mock_operation(response_data={"agent_result": "success"}),
                "integrated_operation"
            )
        
        return await reliable_agent.execute_with_reliability(
            coordinated_operation,
            "coordination_operation",
            timeout=15.0
        )
    async def test_agent_reliability_with_fallback_coordinator(self, reliable_agent):
        """Test agent reliability integration with fallback coordinator."""
        with patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            
            coordinator, mock_health_instance = self._setup_fallback_coordinator_mocks(mock_health_monitor, mock_emergency_manager)
            
            with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, \
                 patch('app.core.fallback_coordinator.CircuitBreaker'), \
                 patch('app.core.fallback_coordinator.AgentFallbackStatus'):
                
                mock_handler = self._setup_coordination_handler_mocks(mock_handler_class)
                coordinator.register_agent("TestAgent")
                
                result = await self._execute_coordinated_operation(coordinator, reliable_agent)
                self._verify_coordination_integration(result, mock_handler, mock_health_instance, reliable_agent)
    async def test_agent_failure_propagation_through_system(self, reliable_agent):
        """Test how agent failures propagate through the integrated system."""
        with patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            
            # Setup mocks for emergency scenario
            mock_health_instance = Mock()
            mock_health_instance.is_emergency_mode_active = AsyncMock(return_value=False)
            mock_health_instance.should_prevent_cascade = AsyncMock(return_value=False)
            mock_health_instance.record_success = AsyncMock()
            mock_health_instance.record_failure = AsyncMock()
            mock_health_instance.update_circuit_breaker_status = AsyncMock()
            mock_health_instance.update_system_health = AsyncMock()
            
            mock_emergency_instance = Mock()
            mock_health_monitor.return_value = mock_health_instance
            mock_emergency_manager.return_value = mock_emergency_instance
            
            coordinator = FallbackCoordinator()
            coordinator.health_monitor = mock_health_instance
            coordinator.emergency_manager = mock_emergency_instance
            
            # Setup failure scenario
            test_error = RuntimeError("Critical system failure")
            
            with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, \
                 patch('app.core.fallback_coordinator.CircuitBreaker'), \
                 patch('app.core.fallback_coordinator.AgentFallbackStatus'):
                
                mock_handler = AsyncMock()
                mock_handler.execute_with_fallback.side_effect = test_error
                mock_handler_class.return_value = mock_handler
                
                coordinator.register_agent("TestAgent")
                
                # Setup agent to fail
                reliable_agent.reliability.execute_safely.side_effect = test_error
                
                # Execute operation and expect failure propagation
                with pytest.raises(RuntimeError, match="Critical system failure"):
                    await reliable_agent.execute_with_reliability(
                        lambda: coordinator.execute_with_coordination(
                            "TestAgent",
                            lambda: reliable_agent.mock_operation(should_fail=True),
                            "failing_operation"
                        ),
                        "coordinated_failure",
                        timeout=5.0
                    )
                
                # Verify failure was recorded in both systems
                assert len(reliable_agent.error_history) == 1
                error_record = reliable_agent.error_history[0]
                assert error_record.error_type == "RuntimeError"
                assert error_record.message == "Critical system failure"
                
                # Verify coordinator recorded the failure
                mock_health_instance.record_failure.assert_called_once_with("TestAgent", test_error)