"""
Integration Tests for Graceful Degradation Service Dependencies

Business Value Justification:
- Segment: Platform/All Segments
- Business Goal: Revenue Protection & Service Reliability  
- Value Impact: Ensures $500K+ ARR chat functionality never completely fails
- Strategic Impact: Validates business continuity during service outages

This test suite validates the Golden Path Critical Issue #2: Missing Service Dependencies
ensuring users always receive some level of functionality when services are unavailable.

Test Coverage:
- Service dependency checking with timeout handling
- Graceful degradation activation when services unavailable 
- Fallback handler creation and basic chat functionality
- Service recovery monitoring and transition to full mode
- User messaging about service status and capabilities
- Business continuity validation - no complete service failures

🚨 CRITICAL: These tests must pass to ensure revenue protection during service outages.
"""

import asyncio
import pytest
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from netra_backend.app.websocket_core.graceful_degradation_manager import (
    GracefulDegradationManager,
    FallbackChatHandler, 
    DegradationLevel,
    ServiceStatus,
    create_graceful_degradation_manager
)
from netra_backend.app.websocket_core.utils import create_server_message, MessageType


class MockAppState:
    """Mock application state for testing."""
    
    def __init__(self, available_services: Dict[str, Any] = None):
        self.available_services = available_services or {}
        # Set all services explicitly for easier testing
        self.agent_supervisor = self.available_services.get('agent_supervisor')
        self.thread_service = self.available_services.get('thread_service') 
        self.agent_websocket_bridge = self.available_services.get('agent_websocket_bridge')
        
    def __getattr__(self, name):
        return self.available_services.get(name)


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
        self.close_code = None
        self.close_reason = None
        
    async def send_text(self, data):
        """Mock send_text method."""
        self.messages_sent.append(json.loads(data) if isinstance(data, str) else data)
        
    async def close(self, code=1000, reason=""):
        """Mock close method."""
        self.closed = True  
        self.close_code = code
        self.close_reason = reason


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    return MockWebSocket()


@pytest.fixture  
def mock_app_state_all_services():
    """Mock app state with all services available."""
    return MockAppState({
        'agent_supervisor': MagicMock(),
        'thread_service': MagicMock(), 
        'agent_websocket_bridge': MagicMock()
    })


@pytest.fixture
def mock_app_state_missing_supervisor():
    """Mock app state missing agent supervisor."""
    return MockAppState({
        'agent_supervisor': None,
        'thread_service': MagicMock(),
        'agent_websocket_bridge': MagicMock()
    })


@pytest.fixture
def mock_app_state_missing_thread():
    """Mock app state missing thread service."""  
    return MockAppState({
        'agent_supervisor': MagicMock(),
        'thread_service': None,
        'agent_websocket_bridge': MagicMock()
    })


@pytest.fixture 
def mock_app_state_all_missing():
    """Mock app state with all critical services missing."""
    return MockAppState({
        'agent_supervisor': None,
        'thread_service': None,
        'agent_websocket_bridge': None
    })


class TestGracefulDegradationManager:
    """Test graceful degradation manager functionality."""
    
    @pytest.mark.asyncio
    async def test_service_assessment_all_available(self, mock_websocket, mock_app_state_all_services):
        """Test service assessment when all services are available."""
        # Create degradation manager
        manager = GracefulDegradationManager(mock_websocket, mock_app_state_all_services)
        
        # Assess service availability
        degradation_context = await manager.assess_service_availability()
        
        # Verify no degradation when all services available
        assert degradation_context.level == DegradationLevel.NONE
        assert len(degradation_context.available_services) == 3
        assert len(degradation_context.degraded_services) == 0
        assert "All systems operational" in degradation_context.user_message
        
        # Verify service health tracking
        assert len(manager.service_health) == 3
        for service_name, health in manager.service_health.items():
            assert health.is_healthy
            assert health.status == ServiceStatus.AVAILABLE
    
    @pytest.mark.asyncio
    async def test_service_assessment_missing_supervisor(self, mock_websocket, mock_app_state_missing_supervisor):
        """Test service assessment when agent supervisor is missing.""" 
        manager = GracefulDegradationManager(mock_websocket, mock_app_state_missing_supervisor)
        
        degradation_context = await manager.assess_service_availability()
        
        # Should have moderate degradation with 2/3 services available (67% < 75%)
        assert degradation_context.level == DegradationLevel.MODERATE
        assert len(degradation_context.available_services) == 2
        assert len(degradation_context.degraded_services) == 1
        assert "agent_supervisor" in degradation_context.degraded_services
        assert "temporarily unavailable" in degradation_context.user_message
    
    @pytest.mark.asyncio
    async def test_service_assessment_missing_thread_service(self, mock_websocket, mock_app_state_missing_thread):
        """Test service assessment when thread service is missing."""
        manager = GracefulDegradationManager(mock_websocket, mock_app_state_missing_thread)
        
        degradation_context = await manager.assess_service_availability()
        
        # Should have moderate degradation with 2/3 services available (67% < 75%)
        assert degradation_context.level == DegradationLevel.MODERATE
        assert len(degradation_context.available_services) == 2
        assert len(degradation_context.degraded_services) == 1
        assert "thread_service" in degradation_context.degraded_services
    
    @pytest.mark.asyncio
    async def test_service_assessment_all_services_missing(self, mock_websocket, mock_app_state_all_missing):
        """Test service assessment when all critical services are missing."""
        manager = GracefulDegradationManager(mock_websocket, mock_app_state_all_missing)
        
        degradation_context = await manager.assess_service_availability()
        
        # Should be emergency degradation with no services available
        assert degradation_context.level == DegradationLevel.EMERGENCY
        assert len(degradation_context.available_services) == 0
        assert len(degradation_context.degraded_services) == 3
        assert "emergency mode" in degradation_context.user_message
    
    @pytest.mark.asyncio
    async def test_fallback_handler_creation(self, mock_websocket, mock_app_state_missing_supervisor):
        """Test creation of fallback chat handler."""
        manager = GracefulDegradationManager(mock_websocket, mock_app_state_missing_supervisor)
        await manager.assess_service_availability()
        
        # Create fallback handler
        fallback_handler = await manager.create_fallback_handler()
        
        # Verify handler creation
        assert fallback_handler is not None
        assert isinstance(fallback_handler, FallbackChatHandler)
        assert fallback_handler.degradation_level == DegradationLevel.MODERATE
        assert hasattr(fallback_handler, 'handle_message')  # MessageRouter interface
        assert hasattr(fallback_handler, 'handler_id')
        assert hasattr(fallback_handler, 'handler_type')
    
    @pytest.mark.asyncio
    async def test_user_degradation_notification(self, mock_websocket, mock_app_state_missing_supervisor):
        """Test user notification about service degradation."""
        # Mock safe_websocket_send to capture messages
        sent_messages = []
        
        async def mock_send(websocket, message):
            sent_messages.append(message)
        
        with patch('netra_backend.app.websocket_core.graceful_degradation_manager.safe_websocket_send', mock_send):
            manager = GracefulDegradationManager(mock_websocket, mock_app_state_missing_supervisor)
            await manager.assess_service_availability()
            
            # Send degradation notification
            await manager.notify_user_of_degradation()
            
            # Verify notification was sent
            assert len(sent_messages) == 1
            notification = sent_messages[0]
            assert notification['type'] == MessageType.SYSTEM_MESSAGE.value
            notification_data = notification.get('data', notification.get('content', {}))
            assert notification_data['event'] == 'service_degradation'
            assert 'degradation_context' in notification_data
            
            degradation_data = notification_data['degradation_context']
            assert degradation_data['level'] == DegradationLevel.MODERATE.value
            assert 'agent_supervisor' in degradation_data['degraded_services']


class TestFallbackChatHandler:
    """Test fallback chat handler responses."""
    
    @pytest.fixture
    def minimal_handler(self, mock_websocket):
        """Create minimal degradation fallback handler."""
        return FallbackChatHandler(DegradationLevel.MINIMAL, mock_websocket)
    
    @pytest.fixture
    def emergency_handler(self, mock_websocket):
        """Create emergency degradation fallback handler."""
        return FallbackChatHandler(DegradationLevel.EMERGENCY, mock_websocket)
    
    @pytest.mark.asyncio
    async def test_handle_greeting_message(self, minimal_handler):
        """Test handling of greeting messages."""
        # Mock safe_websocket_send
        sent_messages = []
        
        async def mock_send(websocket, message):
            sent_messages.append(message)
        
        with patch('netra_backend.app.websocket_core.graceful_degradation_manager.safe_websocket_send', mock_send):
            # Send greeting message
            message = {"content": "hello", "type": "user_message"}
            handled = await minimal_handler.handle_message(message)
            
            # Verify message was handled
            assert handled is True
            assert len(sent_messages) == 1
            
            response = sent_messages[0]
            assert response['type'] == MessageType.AGENT_RESPONSE.value
            # Response data is in 'data' key due to fallback create_server_message implementation
            response_data = response.get('data', response.get('content', {}))
            assert 'limited capabilities' in response_data['content']
            assert response_data['degradation_level'] == DegradationLevel.MINIMAL.value
    
    @pytest.mark.asyncio
    async def test_handle_status_request(self, minimal_handler):
        """Test handling of status request messages.""" 
        sent_messages = []
        
        async def mock_send(websocket, message):
            sent_messages.append(message)
        
        with patch('netra_backend.app.websocket_core.graceful_degradation_manager.safe_websocket_send', mock_send):
            # Send status request
            message = {"content": "what is the system status?", "type": "user_message"}
            handled = await minimal_handler.handle_message(message)
            
            assert handled is True
            assert len(sent_messages) == 1
            
            response = sent_messages[0]
            assert response['type'] == MessageType.SYSTEM_MESSAGE.value
            response_data = response.get('data', response.get('content', {}))
            assert response_data['event'] == 'service_status_update'
            assert 'capabilities' in response_data
    
    @pytest.mark.asyncio  
    async def test_handle_agent_request(self, minimal_handler):
        """Test handling of agent execution requests."""
        sent_messages = []
        
        async def mock_send(websocket, message):
            sent_messages.append(message)
        
        with patch('netra_backend.app.websocket_core.graceful_degradation_manager.safe_websocket_send', mock_send):
            # Send agent request
            message = {"content": "run AI agent analysis", "type": "user_message"}
            handled = await minimal_handler.handle_message(message)
            
            assert handled is True  
            assert len(sent_messages) == 1
            
            response = sent_messages[0]
            response_data = response.get('data', response.get('content', {}))
            assert 'temporarily unavailable' in response_data['content']
    
    @pytest.mark.asyncio
    async def test_emergency_handler_responses(self, emergency_handler):
        """Test emergency handler provides minimal responses."""
        sent_messages = []
        
        async def mock_send(websocket, message):
            sent_messages.append(message)
        
        with patch('netra_backend.app.websocket_core.graceful_degradation_manager.safe_websocket_send', mock_send):
            # Send any message
            message = {"content": "hello", "type": "user_message"}
            handled = await emergency_handler.handle_message(message)
            
            assert handled is True
            assert len(sent_messages) == 1
            
            response = sent_messages[0] 
            response_data = response.get('data', response.get('content', {}))
            assert 'maintenance mode' in response_data['content']
            assert response_data['degradation_level'] == DegradationLevel.EMERGENCY.value
    
    @pytest.mark.asyncio
    async def test_fallback_error_handling(self, minimal_handler):
        """Test fallback handler error resilience."""
        # Mock safe_websocket_send to raise error first, then succeed
        call_count = 0
        sent_messages = []
        
        async def mock_send(websocket, message):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            sent_messages.append(message)
        
        with patch('netra_backend.app.websocket_core.graceful_degradation_manager.safe_websocket_send', mock_send):
            # Handler should not crash on send errors
            message = {"content": "test message", "type": "user_message"}
            handled = await minimal_handler.handle_message(message)
            
            # Should still claim to handle message to prevent crashes
            assert handled is True
            # Should have attempted emergency response
            assert call_count == 2  # First call failed, second was emergency response
            assert len(sent_messages) == 1


class TestServiceRecoveryMonitoring:
    """Test service recovery monitoring and transition logic."""
    
    @pytest.mark.asyncio
    async def test_service_recovery_detection(self, mock_websocket):
        """Test detection of service recovery."""
        # Start with missing services
        app_state = MockAppState({
            'agent_supervisor': None,
            'thread_service': None,
            'agent_websocket_bridge': MagicMock()
        })
        
        manager = GracefulDegradationManager(mock_websocket, app_state)
        initial_context = await manager.assess_service_availability()
        
        # Should be in moderate degradation
        assert initial_context.level == DegradationLevel.MODERATE
        
        # Simulate service recovery - add services back
        app_state.available_services['agent_supervisor'] = MagicMock()  
        app_state.available_services['thread_service'] = MagicMock()
        
        # Reassess after recovery
        recovered_context = await manager.assess_service_availability()
        
        # Should now be fully recovered
        assert recovered_context.level == DegradationLevel.NONE
        assert len(recovered_context.available_services) == 3
        assert len(recovered_context.degraded_services) == 0
    
    @pytest.mark.asyncio
    async def test_recovery_callback_execution(self, mock_websocket, mock_app_state_missing_supervisor):
        """Test execution of recovery callbacks."""
        manager = GracefulDegradationManager(mock_websocket, mock_app_state_missing_supervisor)
        
        # Register recovery callback
        callback_called = False
        callback_args = None
        
        async def test_callback(old_degradation, new_degradation):
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = (old_degradation, new_degradation)
        
        manager.register_recovery_callback(test_callback)
        
        # Simulate calling recovery handler directly
        old_context = await manager.assess_service_availability()
        
        # Simulate service recovery
        mock_app_state_missing_supervisor.available_services['agent_supervisor'] = MagicMock()
        new_context = await manager.assess_service_availability()
        
        # Manually trigger recovery handler for testing
        await manager._handle_service_recovery(old_context, new_context)
        
        # Verify callback was executed
        assert callback_called is True
        assert callback_args is not None
        assert callback_args[0].level == DegradationLevel.MODERATE
        assert callback_args[1].level == DegradationLevel.NONE


class TestBusinessContinuityValidation:
    """Test business continuity requirements are met."""
    
    @pytest.mark.asyncio
    async def test_no_complete_service_failure(self, mock_websocket, mock_app_state_all_missing):
        """CRITICAL: Ensure no complete service failure - users always get responses."""
        # Even with all services missing, system should provide basic functionality
        manager = GracefulDegradationManager(mock_websocket, mock_app_state_all_missing)
        degradation_context = await manager.assess_service_availability()
        
        # Should be emergency level but still functional
        assert degradation_context.level == DegradationLevel.EMERGENCY
        
        # Should still have basic capabilities
        assert degradation_context.capabilities['websocket_connection'] is True
        assert degradation_context.capabilities['basic_messaging'] is True
        
        # Should be able to create fallback handler
        fallback_handler = await manager.create_fallback_handler()
        assert fallback_handler is not None
        
        # Handler should be able to respond to user messages
        sent_messages = []
        async def mock_send(websocket, message):
            sent_messages.append(message)
        
        with patch('netra_backend.app.websocket_core.graceful_degradation_manager.safe_websocket_send', mock_send):
            message = {"content": "hello", "type": "user_message"}
            handled = await fallback_handler.handle_message(message)
            
            # CRITICAL: Must always handle user messages to maintain business continuity
            assert handled is True
            assert len(sent_messages) == 1
            response_data = sent_messages[0].get('data', sent_messages[0].get('content', {}))
            assert 'maintenance mode' in response_data['content']
    
    @pytest.mark.asyncio
    async def test_revenue_protection_scenario(self, mock_websocket):
        """Test critical revenue protection scenario - partial service outage."""
        # Simulate realistic partial outage scenario
        app_state = MockAppState({
            'agent_supervisor': None,  # AI agents down
            'thread_service': MagicMock(),  # Basic messaging still works
            'agent_websocket_bridge': MagicMock()  # WebSocket functionality works
        })
        
        manager = GracefulDegradationManager(mock_websocket, app_state)
        degradation_context = await manager.assess_service_availability()
        
        # Should maintain basic functionality
        assert degradation_context.level == DegradationLevel.MINIMAL
        assert degradation_context.capabilities['websocket_connection'] is True
        assert degradation_context.capabilities['basic_messaging'] is True
        
        # Create fallback handler to maintain user engagement
        fallback_handler = await manager.create_fallback_handler()
        
        # Verify user gets informative responses about AI unavailability
        sent_messages = []
        async def mock_send(websocket, message):
            sent_messages.append(message)
        
        with patch('netra_backend.app.websocket_core.graceful_degradation_manager.safe_websocket_send', mock_send):
            # User tries to run AI analysis
            message = {"content": "analyze my data with AI", "type": "user_message"}
            handled = await fallback_handler.handle_message(message)
            
            assert handled is True
            response = sent_messages[0]
            assert 'temporarily unavailable' in response['content']['content']
            assert 'try again shortly' in response['content']['content']
    
    @pytest.mark.asyncio  
    async def test_estimated_recovery_time_communication(self, mock_websocket, mock_app_state_missing_supervisor):
        """Test system communicates realistic recovery expectations."""
        manager = GracefulDegradationManager(mock_websocket, mock_app_state_missing_supervisor)
        degradation_context = await manager.assess_service_availability()
        
        # Should provide recovery time estimate
        assert degradation_context.estimated_recovery_time is not None
        assert degradation_context.estimated_recovery_time > 0
        
        # Recovery time should scale with number of degraded services
        assert degradation_context.estimated_recovery_time >= 30.0  # At least 30 seconds per service


@pytest.mark.asyncio
async def test_create_graceful_degradation_manager():
    """Test factory function for creating degradation manager."""
    mock_websocket = MockWebSocket()
    mock_app_state = MockAppState({'agent_supervisor': None})
    
    # Create manager using factory
    manager = await create_graceful_degradation_manager(mock_websocket, mock_app_state)
    
    # Verify manager is properly initialized
    assert manager is not None
    assert isinstance(manager, GracefulDegradationManager)
    assert manager.current_degradation is not None
    assert manager.current_degradation.level == DegradationLevel.MODERATE


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([
        __file__, 
        "-v",
        "--tb=short",
        "--durations=10",
        "--log-cli-level=INFO",
        "-x"  # Stop on first failure for faster debugging
    ])