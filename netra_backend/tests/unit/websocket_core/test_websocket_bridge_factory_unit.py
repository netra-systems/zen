#!/usr/bin/env python
"""
Unit Tests for AgentWebSocketBridge Factory Pattern

MISSION CRITICAL: Bridge factory pattern that ensures proper WebSocket integration.
Tests the factory creation of AgentWebSocketBridge instances with proper isolation.

Business Value: $500K+ ARR - Factory pattern reliability for real-time chat
- Tests AgentWebSocketBridge factory creates isolated bridges per user
- Validates proper WebSocket manager injection and configuration
- Ensures factory pattern supports multi-user concurrent execution
"""

import asyncio
import pytest
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, Mock

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility

# Import production WebSocket components
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge, 
    create_agent_websocket_bridge,
    IntegrationState,
    IntegrationConfig,
    HealthStatus
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager for factory testing."""
    manager = AsyncMock(spec=UnifiedWebSocketManager)
    manager.send_to_user.return_value = True
    manager.send_to_thread.return_value = True
    manager.is_healthy.return_value = True
    manager.get_user_connections.return_value = ["conn1", "conn2"]
    return manager


@pytest.fixture
def sample_user_context():
    """Create sample user execution context."""
    context = MagicMock(spec=UserExecutionContext)
    context.user_id = UserID("factory_user_123")
    context.thread_id = ThreadID("factory_thread_456")
    context.request_id = RequestID("factory_request_789")
    context.session_id = "factory_session_abc"
    return context


class TestAgentWebSocketBridgeFactory:
    """Unit tests for AgentWebSocketBridge factory creation pattern."""
    
    def test_factory_creates_bridge_with_websocket_manager(self, sample_user_context):
        """
        Test factory creates AgentWebSocketBridge with proper WebSocket manager.
        
        CRITICAL: Factory must inject WebSocket manager for event delivery.
        No manager means no real-time chat functionality.
        """
        # Arrange
        mock_manager = AsyncMock(spec=UnifiedWebSocketManager)
        mock_manager.is_healthy.return_value = True
        
        # Mock the WebSocket manager discovery in factory
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', 
                  return_value=mock_manager):
            
            # Act
            bridge = create_agent_websocket_bridge(sample_user_context)
            
            # Assert
            assert bridge is not None, "Factory must create bridge instance"
            assert isinstance(bridge, AgentWebSocketBridge), "Factory must return AgentWebSocketBridge"
            assert hasattr(bridge, 'websocket_manager'), "Bridge must have WebSocket manager"
            assert bridge.is_healthy() is True, "Bridge must be healthy with valid manager"
    
    def test_factory_creates_isolated_bridges_for_different_users(self):
        """
        Test factory creates isolated bridges for different users.
        
        CRITICAL: Each user must get isolated bridge to prevent cross-user contamination.
        Shared bridges would leak user data and break security.
        """
        # Arrange
        user1_context = MagicMock(spec=UserExecutionContext)
        user1_context.user_id = UserID("user_1")
        user1_context.thread_id = ThreadID("thread_1")
        user1_context.request_id = RequestID("request_1")
        
        user2_context = MagicMock(spec=UserExecutionContext)
        user2_context.user_id = UserID("user_2")
        user2_context.thread_id = ThreadID("thread_2")
        user2_context.request_id = RequestID("request_2")
        
        mock_manager = AsyncMock(spec=UnifiedWebSocketManager)
        mock_manager.is_healthy.return_value = True
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', 
                  return_value=mock_manager):
            
            # Act
            bridge1 = create_agent_websocket_bridge(user1_context)
            bridge2 = create_agent_websocket_bridge(user2_context)
            
            # Assert
            assert bridge1 is not bridge2, "Factory must create separate bridge instances"
            assert bridge1.user_context.user_id != bridge2.user_context.user_id
            assert bridge1.user_context.thread_id != bridge2.user_context.thread_id
    
    def test_factory_handles_missing_websocket_manager_gracefully(self, sample_user_context):
        """
        Test factory handles missing WebSocket manager gracefully.
        
        CRITICAL: Factory must not crash when WebSocket manager unavailable.
        System must degrade gracefully without breaking agent execution.
        """
        # Arrange - Mock WebSocket manager discovery to return None
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', 
                  return_value=None):
            
            # Act
            bridge = create_agent_websocket_bridge(sample_user_context)
            
            # Assert
            assert bridge is not None, "Factory must create bridge even without manager"
            assert isinstance(bridge, AgentWebSocketBridge), "Factory must return AgentWebSocketBridge"
            
            # Bridge should be created but unhealthy
            assert bridge.websocket_manager is None, "Bridge should have no manager"
            assert bridge.is_healthy() is False, "Bridge should be unhealthy without manager"
    
    @pytest.mark.asyncio
    async def test_factory_bridge_supports_all_required_events(self, sample_user_context, mock_websocket_manager):
        """
        Test factory-created bridge supports all 5 REQUIRED WebSocket events.
        
        CRITICAL: Factory bridge must support all events for complete chat functionality.
        Missing event support breaks user experience and business value.
        """
        # Arrange
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', 
                  return_value=mock_websocket_manager):
            
            bridge = create_agent_websocket_bridge(sample_user_context)
            
            # Required events for chat business value
            required_events = [
                ("agent_started", {"agent": "triage", "status": "starting"}),
                ("agent_thinking", {"agent": "triage", "progress": "analyzing"}),
                ("tool_executing", {"tool": "analyzer", "status": "executing"}),
                ("tool_completed", {"tool": "analyzer", "result": {"data": "success"}}),
                ("agent_completed", {"agent": "triage", "status": "completed"})
            ]
            
            # Act & Assert - Test each required event
            for event_type, event_data in required_events:
                mock_websocket_manager.reset_mock()
                
                result = await bridge.emit_event(
                    context=sample_user_context,
                    event_type=event_type,
                    event_data=event_data
                )
                
                assert result is True, f"Factory bridge must support {event_type} event"
                
                # Verify manager was called
                assert (mock_websocket_manager.send_to_thread.called or 
                       mock_websocket_manager.send_to_user.called), f"Manager must be called for {event_type}"


class TestAgentWebSocketBridgeCreation:
    """Unit tests for direct AgentWebSocketBridge creation."""
    
    def test_bridge_initializes_with_valid_manager(self, mock_websocket_manager, sample_user_context):
        """
        Test AgentWebSocketBridge initializes properly with valid WebSocket manager.
        
        CRITICAL: Bridge initialization with manager enables all chat functionality.
        Proper initialization is prerequisite for real-time communication.
        """
        # Act
        bridge = AgentWebSocketBridge(mock_websocket_manager)
        
        # Assert
        assert bridge.websocket_manager is mock_websocket_manager
        assert bridge.is_healthy() is True
        assert bridge.integration_state == IntegrationState.ACTIVE
        
        # Verify bridge has required methods
        assert hasattr(bridge, 'emit_event')
        assert hasattr(bridge, 'is_healthy')
        assert callable(bridge.emit_event)
        assert callable(bridge.is_healthy)
    
    def test_bridge_initializes_with_none_manager(self):
        """
        Test AgentWebSocketBridge initializes gracefully with None manager.
        
        CRITICAL: Bridge must handle missing manager without crashing.
        Graceful degradation ensures system stability in all conditions.
        """
        # Act
        bridge = AgentWebSocketBridge(None)
        
        # Assert
        assert bridge.websocket_manager is None
        assert bridge.is_healthy() is False
        assert bridge.integration_state == IntegrationState.FAILED
        
        # Bridge should still be usable but events will fail
        assert hasattr(bridge, 'emit_event')
        assert callable(bridge.emit_event)
    
    def test_bridge_health_status_reflects_manager_health(self, sample_user_context):
        """
        Test AgentWebSocketBridge health status reflects WebSocket manager health.
        
        CRITICAL: Bridge health must accurately reflect underlying manager state.
        Health monitoring enables proper error handling and fallbacks.
        """
        # Test with healthy manager
        healthy_manager = AsyncMock(spec=UnifiedWebSocketManager)
        healthy_manager.is_healthy.return_value = True
        
        healthy_bridge = AgentWebSocketBridge(healthy_manager)
        assert healthy_bridge.is_healthy() is True
        
        # Test with unhealthy manager
        unhealthy_manager = AsyncMock(spec=UnifiedWebSocketManager)
        unhealthy_manager.is_healthy.return_value = False
        
        unhealthy_bridge = AgentWebSocketBridge(unhealthy_manager)
        assert unhealthy_bridge.is_healthy() is False
    
    @pytest.mark.asyncio
    async def test_bridge_event_emission_with_valid_manager(self, mock_websocket_manager, sample_user_context):
        """
        Test AgentWebSocketBridge event emission with valid WebSocket manager.
        
        CRITICAL: Bridge must successfully emit events through manager.
        Event emission is the core functionality for real-time chat.
        """
        # Arrange
        bridge = AgentWebSocketBridge(mock_websocket_manager)
        
        event_data = {
            "agent": "optimization_agent",
            "status": "starting",
            "timestamp": datetime.now().isoformat()
        }
        
        # Act
        result = await bridge.emit_event(
            context=sample_user_context,
            event_type="agent_started",
            event_data=event_data
        )
        
        # Assert
        assert result is True, "Bridge must successfully emit event through manager"
        
        # Verify manager was called
        mock_websocket_manager.send_to_thread.assert_called_once()
        
        # Verify event structure
        call_args = mock_websocket_manager.send_to_thread.call_args
        thread_id, message = call_args[0]
        
        assert thread_id == "factory_thread_456"
        assert message["type"] == "agent_started"
        assert message["data"] == event_data
    
    @pytest.mark.asyncio
    async def test_bridge_event_emission_without_manager(self, sample_user_context):
        """
        Test AgentWebSocketBridge event emission without WebSocket manager.
        
        CRITICAL: Bridge must handle event emission gracefully when no manager available.
        Failure must not crash agent execution but should return False.
        """
        # Arrange
        bridge = AgentWebSocketBridge(None)
        
        event_data = {
            "agent": "test_agent",
            "status": "starting"
        }
        
        # Act
        result = await bridge.emit_event(
            context=sample_user_context,
            event_type="agent_started",
            event_data=event_data
        )
        
        # Assert
        assert result is False, "Bridge must return False when no manager available"


class TestWebSocketBridgeConfiguration:
    """Unit tests for WebSocket bridge configuration and customization."""
    
    def test_integration_config_default_values(self):
        """
        Test IntegrationConfig has proper default values.
        
        CRITICAL: Default configuration must provide reasonable timeouts and limits.
        Poor defaults could cause system instability or poor user experience.
        """
        # Act
        config = IntegrationConfig()
        
        # Assert - Verify reasonable defaults
        assert config.initialization_timeout_s > 0, "Initialization timeout must be positive"
        assert config.health_check_interval_s > 0, "Health check interval must be positive"
        assert config.recovery_max_attempts > 0, "Recovery attempts must be positive"
        assert config.recovery_base_delay_s > 0, "Recovery delay must be positive"
        assert config.recovery_max_delay_s >= config.recovery_base_delay_s
        assert config.integration_verification_timeout_s > 0
        
        # Verify reasonable timeout values
        assert config.initialization_timeout_s <= 60, "Initialization timeout should be reasonable"
        assert config.health_check_interval_s <= 300, "Health check interval should be reasonable"
    
    def test_health_status_tracks_integration_state(self):
        """
        Test HealthStatus properly tracks integration state and metrics.
        
        CRITICAL: Health status must provide accurate monitoring data.
        Poor health tracking prevents proper error detection and recovery.
        """
        # Arrange
        health = HealthStatus(
            state=IntegrationState.ACTIVE,
            websocket_manager_healthy=True,
            registry_healthy=True,
            last_health_check=datetime.now(),
            consecutive_failures=0,
            total_recoveries=2,
            uptime_seconds=3600.0
        )
        
        # Assert
        assert health.state == IntegrationState.ACTIVE
        assert health.websocket_manager_healthy is True
        assert health.registry_healthy is True
        assert health.consecutive_failures == 0
        assert health.total_recoveries == 2
        assert health.uptime_seconds == 3600.0
        assert health.error_message is None
        
        # Test degraded state
        degraded_health = HealthStatus(
            state=IntegrationState.DEGRADED,
            websocket_manager_healthy=False,
            registry_healthy=True,
            last_health_check=datetime.now(),
            consecutive_failures=2,
            error_message="WebSocket manager unhealthy"
        )
        
        assert degraded_health.state == IntegrationState.DEGRADED
        assert degraded_health.websocket_manager_healthy is False
        assert degraded_health.consecutive_failures == 2
        assert degraded_health.error_message == "WebSocket manager unhealthy"
    
    def test_integration_states_enum_completeness(self):
        """
        Test IntegrationState enum covers all necessary states.
        
        CRITICAL: Integration states must cover all possible bridge conditions.
        Missing states prevent proper error handling and monitoring.
        """
        # Assert all required states exist
        required_states = [
            IntegrationState.UNINITIALIZED,
            IntegrationState.INITIALIZING,
            IntegrationState.ACTIVE,
            IntegrationState.DEGRADED,
            IntegrationState.FAILED
        ]
        
        for state in required_states:
            assert isinstance(state, IntegrationState)
            assert isinstance(state.value, str)
        
        # Verify state transitions make sense
        assert IntegrationState.UNINITIALIZED.value == "uninitialized"
        assert IntegrationState.ACTIVE.value == "active"
        assert IntegrationState.FAILED.value == "failed"


class TestWebSocketBridgeUserIsolation:
    """Unit tests for WebSocket bridge user isolation and security."""
    
    @pytest.mark.asyncio
    async def test_bridge_respects_user_context_isolation(self, mock_websocket_manager):
        """
        Test AgentWebSocketBridge respects user context isolation.
        
        CRITICAL: Bridge must properly isolate events by user context.
        Cross-user contamination breaks security and user experience.
        """
        # Arrange
        user1_context = MagicMock(spec=UserExecutionContext)
        user1_context.user_id = UserID("isolated_user_1")
        user1_context.thread_id = ThreadID("isolated_thread_1")
        
        user2_context = MagicMock(spec=UserExecutionContext)
        user2_context.user_id = UserID("isolated_user_2")
        user2_context.thread_id = ThreadID("isolated_thread_2")
        
        bridge = AgentWebSocketBridge(mock_websocket_manager)
        
        # Act - Emit events for different users
        result1 = await bridge.emit_event(
            context=user1_context,
            event_type="agent_started",
            event_data={"agent": "user1_agent", "status": "starting"}
        )
        
        result2 = await bridge.emit_event(
            context=user2_context,
            event_type="agent_started",
            event_data={"agent": "user2_agent", "status": "starting"}
        )
        
        # Assert
        assert result1 is True, "Bridge must emit event for user1"
        assert result2 is True, "Bridge must emit event for user2"
        
        # Verify manager was called twice with different contexts
        assert mock_websocket_manager.send_to_thread.call_count == 2
        
        # Verify isolation - check call arguments
        calls = mock_websocket_manager.send_to_thread.call_args_list
        
        # First call for user1
        thread1_id, message1 = calls[0][0]
        assert thread1_id == "isolated_thread_1"
        assert message1["data"]["agent"] == "user1_agent"
        
        # Second call for user2
        thread2_id, message2 = calls[1][0]
        assert thread2_id == "isolated_thread_2"
        assert message2["data"]["agent"] == "user2_agent"
    
    def test_bridge_factory_maintains_user_context_reference(self, sample_user_context):
        """
        Test bridge factory maintains proper user context reference.
        
        CRITICAL: Factory must maintain user context for proper isolation.
        Lost context breaks user-specific event routing.
        """
        # Arrange
        mock_manager = AsyncMock(spec=UnifiedWebSocketManager)
        mock_manager.is_healthy.return_value = True
        
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', 
                  return_value=mock_manager):
            
            # Act
            bridge = create_agent_websocket_bridge(sample_user_context)
            
            # Assert
            assert hasattr(bridge, 'user_context'), "Bridge must maintain user context"
            assert bridge.user_context is sample_user_context, "Bridge must reference original context"
            assert bridge.user_context.user_id == "factory_user_123"
            assert bridge.user_context.thread_id == "factory_thread_456"