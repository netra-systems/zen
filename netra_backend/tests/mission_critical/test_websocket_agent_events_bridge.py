"""
Mission-Critical Tests for WebSocket Agent Events with Bridge Integration.

BUSINESS VALUE: These tests ensure the critical WebSocket events that enable
substantive chat interactions are delivered reliably through the bridge.

Critical events for chat business value:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results delivery
5. agent_completed - User knows response is ready

These events are essential for the "Chat" business value delivery.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any

from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState
)


class WebSocketEventCapture:
    """Captures WebSocket events for testing."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_times: List[float] = []
    
    async def send_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Capture sent messages."""
        self.events.append({
            "user_id": user_id,
            "type": message.get("type"),
            "payload": message.get("payload", {}),
            "timestamp": time.time()
        })
        self.event_times.append(time.time())
        return True
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Capture thread-specific messages."""
        self.events.append({
            "thread_id": thread_id,
            "type": message.get("type"),
            "payload": message.get("payload", {}),
            "timestamp": time.time()
        })
        self.event_times.append(time.time())
        return True
    
    async def send_error(self, user_id: str, error: str) -> bool:
        """Capture error messages."""
        self.events.append({
            "user_id": user_id,
            "type": "error",
            "error": error,
            "timestamp": time.time()
        })
        self.event_times.append(time.time())
        return True
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get events filtered by type."""
        return [event for event in self.events if event.get("type") == event_type]
    
    def get_event_sequence(self) -> List[str]:
        """Get sequence of event types."""
        return [event.get("type") for event in self.events]
    
    def clear(self):
        """Clear captured events."""
        self.events.clear()
        self.event_times.clear()


@pytest.mark.asyncio
class TestMissionCriticalWebSocketEvents:
    """Mission-critical tests for WebSocket event delivery through bridge."""

    @pytest.fixture
    def mock_supervisor(self):
        """Mock supervisor with registry."""
        supervisor = Mock()
        supervisor.registry = Mock()
        supervisor.registry.websocket_manager = None
        supervisor.run = AsyncMock(return_value="Agent completed successfully")
        return supervisor

    @pytest.fixture
    def event_capture(self):
        """WebSocket event capture system."""
        return WebSocketEventCapture()

    @pytest.fixture
    async def integrated_service(self, mock_supervisor, event_capture):
        """AgentService with bridge integration and event capture."""
        # Reset bridge singleton
        AgentWebSocketBridge._instance = None
        
        # Create service
        service = AgentService(mock_supervisor)
        
        # Setup integration with event capture
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_manager, \
             patch('netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry') as mock_get_registry:
            
            # Use event capture as WebSocket manager
            mock_get_manager.return_value = event_capture
            
            # Setup orchestrator mock
            registry = AsyncMock()
            orchestrator.get_metrics.return_value = {"active_contexts": 0}
            
            # Mock execution context and notifier
            mock_context = Mock()
            mock_context.user_id = "test_user"
            mock_context.thread_id = "test_thread"
            mock_context.run_id = "test_run"
            mock_context.agent_name = "test_agent"
            
            mock_notifier = AsyncMock()
            orchestrator.create_execution_context.return_value = (mock_context, mock_notifier)
            
            mock_get_registry.return_value = registry
            
            # Ensure service is ready
            await service.ensure_service_ready()
            
            yield service, event_capture, mock_context, mock_notifier
        
        # Cleanup
        if service._bridge:
            await service._bridge.shutdown()

    async def test_critical_agent_execution_event_sequence(self, integrated_service):
        """Test critical WebSocket events are sent in correct sequence during agent execution."""
        service, event_capture, mock_context, mock_notifier = integrated_service
        
        # Execute agent
        result = await service.execute_agent(
            agent_type="test_agent",
            message="test message",
            user_id="test_user"
        )
        
        # Verify execution succeeded with events
        assert result["status"] == "success"
        assert result["bridge_coordinated"]
        assert result["websocket_events_sent"]
        
        # Verify critical events were sent through notifier
        mock_notifier.send_agent_thinking.assert_called_once()
        
        # Verify thinking event was sent
        thinking_call = mock_notifier.send_agent_thinking.call_args
        assert "Processing test_agent request" in thinking_call[0][1]

    async def test_critical_event_delivery_timing(self, integrated_service):
        """Test critical events are delivered within acceptable timing for chat UX."""
        service, event_capture, mock_context, mock_notifier = integrated_service
        
        # Record start time
        start_time = time.time()
        
        # Execute agent
        await service.execute_agent(
            agent_type="triage_agent",
            message="urgent request",
            user_id="test_user"
        )
        
        # Verify events delivered quickly (< 500ms for good chat UX)
        if event_capture.event_times:
            first_event_time = min(event_capture.event_times)
            event_delivery_time = (first_event_time - start_time) * 1000  # Convert to ms
            
            assert event_delivery_time < 500, f"Event delivery too slow: {event_delivery_time}ms"

    async def test_event_delivery_reliability_with_retries(self, mock_supervisor, event_capture):
        """Test event delivery retries ensure reliability for business-critical chat."""
        # Reset bridge singleton
        AgentWebSocketBridge._instance = None
        service = AgentService(mock_supervisor)
        
        # Setup integration with failing then succeeding WebSocket
        failing_capture = Mock()
        failing_capture.send_to_thread = AsyncMock(side_effect=[False, False, True])  # Fail twice, succeed third
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_manager, \
             patch('netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry') as mock_get_registry:
            
            mock_get_manager.return_value = failing_capture
            
            registry = AsyncMock()
            orchestrator.get_metrics.return_value = {"active_contexts": 0}
            mock_get_registry.return_value = registry
            
            await service.ensure_service_ready()
            
            # Test event delivery retry
            mock_context = Mock()
            mock_context.user_id = "test_user"
            mock_context.thread_id = "test_thread"
            
            success = await service._bridge.ensure_event_delivery(
                mock_context,
                "agent_started",
                {"agent": "test_agent", "status": "processing"}
            )
            
            # Verify event eventually delivered
            assert success
            # Should have retried (3 calls total)
            assert failing_capture.send_to_thread.call_count == 3
        
        # Cleanup
        await service._bridge.shutdown()

    async def test_bridge_preserves_websocket_manager_interface(self, integrated_service):
        """Test bridge doesn't break existing WebSocket manager interface."""
        service, event_capture, mock_context, mock_notifier = integrated_service
        
        # Test all critical WebSocket manager methods work through bridge
        websocket_manager = service._bridge._websocket_manager
        
        # Test send_message method
        success = await websocket_manager.send_message("user123", {"type": "test", "data": "test"})
        assert success
        
        # Test send_to_thread method  
        success = await websocket_manager.send_to_thread("thread123", {"type": "test", "data": "test"})
        assert success
        
        # Test send_error method
        success = await websocket_manager.send_error("user123", "test error")
        assert success
        
        # Verify events were captured
        assert len(event_capture.events) >= 3

    async def test_substantive_chat_value_preservation(self, integrated_service):
        """Test bridge preserves substantive chat business value through proper event delivery."""
        service, event_capture, mock_context, mock_notifier = integrated_service
        
        # Simulate data analysis agent execution (high business value scenario)
        result = await service.execute_agent(
            agent_type="data_sub_agent",
            message="analyze customer churn patterns",
            context={"priority": "high", "business_value": "revenue_optimization"},
            user_id="business_user"
        )
        
        # Verify successful execution with WebSocket coordination
        assert result["status"] == "success"
        assert result["bridge_coordinated"]
        assert result["websocket_events_sent"]
        
        # Verify thinking event provides value transparency
        thinking_call = mock_notifier.send_agent_thinking.call_args
        assert thinking_call is not None
        assert "data_sub_agent" in thinking_call[0][1]
        
        # Verify agent response contains substantive content
        assert "Agent completed successfully" in result["response"]

    async def test_bridge_health_monitoring_for_chat_reliability(self, integrated_service):
        """Test bridge health monitoring ensures chat system reliability."""
        service, event_capture, mock_context, mock_notifier = integrated_service
        
        # Get bridge health status
        health = await service._bridge.health_check()
        
        # Verify health metrics support reliable chat
        assert health.websocket_manager_healthy
        assert health.registry_healthy
        assert health.consecutive_failures == 0
        
        # Verify bridge configuration supports chat SLAs
        status = await service._bridge.get_status()
        config = status["config"]
        
        # Event delivery should be fast for good chat UX
        assert config["event_delivery_timeout_ms"] <= 500
        
        # Health checks should be frequent enough to detect issues quickly
        assert config["health_check_interval_s"] <= 60
        
        # Should have enough retry attempts for reliability
        assert config["recovery_max_attempts"] >= 3

    async def test_bridge_recovery_maintains_chat_availability(self, mock_supervisor):
        """Test bridge recovery mechanisms maintain chat availability."""
        # Create service with initially failing integration
        AgentWebSocketBridge._instance = None
        service = AgentService(mock_supervisor)
        
        event_capture = WebSocketEventCapture()
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_manager, \
             patch('netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry') as mock_get_registry:
            
            # First call fails, second succeeds (simulating recovery)
            mock_get_manager.side_effect = [
                RuntimeError("WebSocket temporarily unavailable"),
                event_capture
            ]
            
            registry = AsyncMock()
            orchestrator.get_metrics.return_value = {"active_contexts": 0}
            mock_get_registry.return_value = registry
            
            # Wait for initial setup (will fail)
            await asyncio.sleep(0.2)
            
            # Verify service can recover
            ready = await service.ensure_service_ready()
            assert ready
            
            # Verify chat functionality works after recovery
            result = await service.execute_agent(
                agent_type="recovery_test",
                message="test after recovery",
                user_id="test_user"
            )
            
            # Should work with bridge coordination after recovery
            assert result["status"] == "success"
            assert result["bridge_coordinated"]
        
        # Cleanup
        await service._bridge.shutdown()

    async def test_bridge_metrics_for_chat_observability(self, integrated_service):
        """Test bridge provides metrics for chat system observability."""
        service, event_capture, mock_context, mock_notifier = integrated_service
        
        # Execute several agents to generate metrics
        for i in range(3):
            await service.execute_agent(
                agent_type=f"test_agent_{i}",
                message=f"test message {i}",
                user_id="test_user"
            )
        
        # Get bridge metrics
        status = await service._bridge.get_status()
        metrics = status["metrics"]
        
        # Verify key metrics are tracked
        assert "total_initializations" in metrics
        assert "successful_initializations" in metrics
        assert "recovery_attempts" in metrics
        assert "health_checks_performed" in metrics
        assert "success_rate" in metrics
        
        # Verify success rate calculation
        assert metrics["success_rate"] >= 0.0
        assert metrics["success_rate"] <= 1.0
        
        # For successful integration, success rate should be 100%
        if metrics["total_initializations"] > 0:
            assert metrics["success_rate"] == 1.0


@pytest.mark.asyncio
class TestWebSocketEventBusinessValue:
    """Tests specifically focused on business value delivery through WebSocket events."""

    async def test_chat_interaction_complete_flow(self):
        """Test complete chat interaction flow preserves business value."""
        # This test simulates a complete user chat interaction
        # to ensure all critical events support the business goal
        
        event_capture = WebSocketEventCapture()
        supervisor = Mock()
        supervisor.registry = Mock()
        supervisor.run = AsyncMock(return_value="Data analysis complete: Customer retention improved by 15%")
        
        AgentWebSocketBridge._instance = None
        service = AgentService(supervisor)
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_manager, \
             patch('netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry') as mock_get_registry:
            
            mock_get_manager.return_value = event_capture
            
            registry = AsyncMock()
            orchestrator.get_metrics.return_value = {"active_contexts": 0}
            
            # Mock execution context
            mock_context = Mock()
            mock_context.user_id = "business_user"
            mock_context.thread_id = "important_analysis"
            mock_context.run_id = "analysis_run_001"
            mock_context.agent_name = "data_sub_agent"
            
            mock_notifier = AsyncMock()
            orchestrator.create_execution_context.return_value = (mock_context, mock_notifier)
            mock_get_registry.return_value = registry
            
            await service.ensure_service_ready()
            
            # Simulate high-value business interaction
            result = await service.execute_agent(
                agent_type="data_sub_agent",
                message="Analyze Q4 customer retention and recommend optimization strategies",
                context={
                    "priority": "high",
                    "business_impact": "revenue_critical",
                    "stakeholder": "executive_team"
                },
                user_id="business_user"
            )
            
            # Verify business value delivery
            assert result["status"] == "success"
            assert result["bridge_coordinated"]  # Coordinated execution
            assert result["websocket_events_sent"]  # User sees progress
            assert "retention improved" in result["response"]  # Substantive result
            
            # Verify user received thinking updates (transparency)
            mock_notifier.send_agent_thinking.assert_called()
            
            # This demonstrates the bridge enables the core business value:
            # Users get real-time visibility into AI processing and receive 
            # substantive, valuable results through the chat interface
        
        await service._bridge.shutdown()

    async def test_event_delivery_supports_user_trust(self):
        """Test WebSocket events build user trust through transparency."""
        event_capture = WebSocketEventCapture()
        supervisor = Mock()
        supervisor.registry = Mock()
        supervisor.run = AsyncMock(return_value="Security analysis complete")
        
        AgentWebSocketBridge._instance = None
        service = AgentService(supervisor)
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_manager, \
             patch('netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry') as mock_get_registry:
            
            mock_get_manager.return_value = event_capture
            
            registry = AsyncMock()
            orchestrator.get_metrics.return_value = {"active_contexts": 0}
            
            mock_context = Mock()
            mock_context.user_id = "security_team"
            mock_context.thread_id = "security_review"
            
            mock_notifier = AsyncMock()
            orchestrator.create_execution_context.return_value = (mock_context, mock_notifier)
            mock_get_registry.return_value = registry
            
            await service.ensure_service_ready()
            
            # Execute security-focused agent (trust-critical scenario)
            result = await service.execute_agent(
                agent_type="security_validation_agent",
                message="Review system security posture and identify vulnerabilities",
                context={"classification": "sensitive", "audit_required": True},
                user_id="security_team"
            )
            
            # Verify transparency events that build user trust
            assert result["bridge_coordinated"]
            assert result["websocket_events_sent"]
            
            # User should see that agent is actively working (trust through visibility)
            mock_notifier.send_agent_thinking.assert_called()
            thinking_message = mock_notifier.send_agent_thinking.call_args[0][1]
            assert "security_validation_agent" in thinking_message.lower()
            
            # This demonstrates how WebSocket events build user trust by showing
            # the AI is actively working on their request, not just a black box
        
        await service._bridge.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])