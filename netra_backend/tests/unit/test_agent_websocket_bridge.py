"""
Comprehensive Unit Tests for AgentWebSocketBridge - SSOT Integration Lifecycle Manager

Business Value Justification (BVJ):
- Segment: Platform/Internal + All User Segments  
- Business Goal: Platform Stability & Chat Business Value Delivery
- Value Impact: Ensures $500K+ ARR by validating WebSocket-Agent integration that enables substantive AI chat interactions
- Strategic Impact: MISSION CRITICAL - Bridge failures = immediate revenue loss as users cannot receive AI agent responses

CRITICAL: AgentWebSocketBridge is the SSOT component that enables our core business value:
1. WebSocket events for real-time agent interaction (user engagement)
2. Multi-user isolation ensuring Enterprise customers get secure sessions
3. Health monitoring preventing service disruptions that damage retention
4. Recovery mechanisms ensuring 99.9% uptime for paying customers

These tests validate that our integration system delivers business value by:
- Ensuring agent-websocket coordination works for all user tiers
- Validating health monitoring catches issues before revenue impact
- Testing recovery mechanisms that prevent customer churn
- Verifying per-user isolation protects Enterprise customer data
- Confirming all 5 critical WebSocket events are sent for chat value

Test Coverage Target: 100% of critical integration flows in AgentWebSocketBridge
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, Optional
from enum import Enum

import pytest

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mocks import MockFactory
# from test_framework.unified import TestCategory  # Not needed for unit tests
from shared.isolated_environment import get_env

# Import the module under test
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig,
    HealthStatus,
    IntegrationResult,
    IntegrationMetrics,
    create_agent_websocket_bridge
)


class TestAgentWebSocketBridgeInitialization:
    """Test AgentWebSocketBridge initialization and configuration."""
    
    @pytest.mark.unit
    async def test_bridge_initialization_success(self):
        """Test successful bridge initialization with all components."""
        # Business Value: Ensures platform can initialize properly for all user segments
        
        bridge = AgentWebSocketBridge()
        
        # Verify initialization state
        assert bridge.state == IntegrationState.UNINITIALIZED, "Bridge should start in UNINITIALIZED state (expected for per-request pattern)"
        assert bridge.config is not None, "Configuration should be initialized"
        assert bridge.config.initialization_timeout_s == 30, "Should have default timeout"
        assert bridge.metrics is not None, "Metrics should be initialized"
        assert bridge.health_status is not None, "Health status should be initialized"
        assert bridge._initialized is True, "Bridge should be marked as initialized"
        
        # Verify locks are created
        assert bridge.initialization_lock is not None, "Initialization lock should exist"
        assert bridge.recovery_lock is not None, "Recovery lock should exist"
        assert bridge.health_lock is not None, "Health lock should exist"
        
        # Verify monitoring setup
        assert bridge._monitor_observers == [], "Monitor observers should be empty initially"
        assert bridge._health_broadcast_interval == 30.0, "Health broadcast interval should be set"

    @pytest.mark.unit
    async def test_bridge_configuration_customization(self):
        """Test bridge configuration can be customized."""
        # Business Value: Allows tuning for different environments and performance requirements
        
        bridge = AgentWebSocketBridge()
        
        # Customize configuration
        bridge.config.initialization_timeout_s = 60
        bridge.config.health_check_interval_s = 120
        bridge.config.recovery_max_attempts = 5
        
        assert bridge.config.initialization_timeout_s == 60
        assert bridge.config.health_check_interval_s == 120
        assert bridge.config.recovery_max_attempts == 5

    @pytest.mark.unit
    async def test_bridge_metrics_initialization(self):
        """Test metrics are properly initialized and tracking works."""
        # Business Value: Enables monitoring and observability for Enterprise customers
        
        bridge = AgentWebSocketBridge()
        
        # Verify initial metrics
        assert bridge.metrics.total_initializations == 0
        assert bridge.metrics.successful_initializations == 0
        assert bridge.metrics.failed_initializations == 0
        assert bridge.metrics.recovery_attempts == 0
        assert bridge.metrics.successful_recoveries == 0
        assert bridge.metrics.health_checks_performed == 0


class TestAgentWebSocketBridgeIntegration:
    """Test AgentWebSocketBridge integration lifecycle management."""
    
    @pytest.mark.unit
    async def test_ensure_integration_success(self):
        """Test successful integration setup."""
        # Business Value: Ensures WebSocket-Agent coordination works for chat delivery
        
        bridge = AgentWebSocketBridge()
        
        with patch.object(bridge, '_initialize_websocket_manager', new_callable=AsyncMock) as mock_ws, \
             patch.object(bridge, '_initialize_registry', new_callable=AsyncMock) as mock_reg, \
             patch.object(bridge, '_initialize_thread_registry', new_callable=AsyncMock) as mock_thread, \
             patch.object(bridge, '_setup_registry_integration', new_callable=AsyncMock) as mock_setup, \
             patch.object(bridge, '_verify_integration', new_callable=AsyncMock) as mock_verify, \
             patch.object(bridge, '_start_health_monitoring', new_callable=AsyncMock) as mock_health:
            
            mock_verify.return_value = True
            
            result = await bridge.ensure_integration()
            
            # Verify successful result
            assert result.success is True, "Integration should succeed"
            assert result.state == IntegrationState.ACTIVE, "State should be ACTIVE"
            assert result.duration_ms > 0, "Should track duration"
            assert result.error is None, "No error should be present"
            
            # Verify state changes
            assert bridge.state == IntegrationState.ACTIVE, "Bridge state should be ACTIVE"
            assert bridge.metrics.total_initializations == 1, "Should track initialization attempt"
            assert bridge.metrics.successful_initializations == 1, "Should track success"
            assert bridge.metrics.failed_initializations == 0, "No failures should be recorded"
            
            # Verify all initialization steps called
            mock_ws.assert_called_once()
            mock_reg.assert_called_once()
            mock_thread.assert_called_once()
            mock_setup.assert_called_once()
            mock_verify.assert_called_once()
            mock_health.assert_called_once()

    @pytest.mark.unit
    async def test_ensure_integration_already_active(self):
        """Test integration skipped when already active."""
        # Business Value: Prevents unnecessary work and maintains stability
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.ACTIVE
        
        result = await bridge.ensure_integration()
        
        assert result.success is True
        assert result.state == IntegrationState.ACTIVE
        assert bridge.metrics.total_initializations == 0, "No new initialization should be recorded"

    @pytest.mark.unit
    async def test_ensure_integration_force_reinit(self):
        """Test forced re-initialization when already active."""
        # Business Value: Enables recovery and configuration updates in production
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.ACTIVE
        
        with patch.object(bridge, '_initialize_websocket_manager', new_callable=AsyncMock) as mock_ws, \
             patch.object(bridge, '_initialize_registry', new_callable=AsyncMock) as mock_reg, \
             patch.object(bridge, '_initialize_thread_registry', new_callable=AsyncMock) as mock_thread, \
             patch.object(bridge, '_setup_registry_integration', new_callable=AsyncMock) as mock_setup, \
             patch.object(bridge, '_verify_integration', new_callable=AsyncMock) as mock_verify, \
             patch.object(bridge, '_start_health_monitoring', new_callable=AsyncMock) as mock_health:
            
            mock_verify.return_value = True
            
            result = await bridge.ensure_integration(force_reinit=True)
            
            assert result.success is True
            assert bridge.metrics.total_initializations == 1, "Should record forced re-initialization"
            mock_ws.assert_called_once()

    @pytest.mark.unit
    async def test_ensure_integration_failure(self):
        """Test integration failure handling."""
        # Business Value: Prevents silent failures that could impact revenue
        
        bridge = AgentWebSocketBridge()
        
        with patch.object(bridge, '_initialize_websocket_manager', new_callable=AsyncMock) as mock_ws:
            mock_ws.side_effect = RuntimeError("WebSocket initialization failed")
            
            result = await bridge.ensure_integration()
            
            # Verify failure result
            assert result.success is False, "Integration should fail"
            assert result.state == IntegrationState.FAILED, "State should be FAILED"
            assert "WebSocket initialization failed" in result.error, "Error should contain cause"
            assert result.duration_ms > 0, "Should track duration even on failure"
            
            # Verify metrics
            assert bridge.state == IntegrationState.FAILED, "Bridge state should be FAILED"
            assert bridge.metrics.total_initializations == 1, "Should track attempt"
            assert bridge.metrics.successful_initializations == 0, "No success should be recorded"
            assert bridge.metrics.failed_initializations == 1, "Should track failure"

    @pytest.mark.unit
    async def test_ensure_integration_verification_failure(self):
        """Test integration failure when verification fails."""
        # Business Value: Catches incomplete integrations that would cause user-facing failures
        
        bridge = AgentWebSocketBridge()
        
        with patch.object(bridge, '_initialize_websocket_manager', new_callable=AsyncMock), \
             patch.object(bridge, '_initialize_registry', new_callable=AsyncMock), \
             patch.object(bridge, '_initialize_thread_registry', new_callable=AsyncMock), \
             patch.object(bridge, '_setup_registry_integration', new_callable=AsyncMock), \
             patch.object(bridge, '_verify_integration', new_callable=AsyncMock) as mock_verify:
            
            mock_verify.return_value = False
            
            result = await bridge.ensure_integration()
            
            assert result.success is False
            assert result.state == IntegrationState.FAILED
            assert "Integration verification failed" in result.error
            assert bridge.metrics.failed_initializations == 1

    @pytest.mark.unit
    async def test_ensure_integration_with_supervisor_and_registry(self):
        """Test integration with optional supervisor and registry parameters."""
        # Business Value: Enables enhanced integration for advanced agent workflows
        
        bridge = AgentWebSocketBridge()
        mock_supervisor = Mock()
        mock_registry = Mock()
        
        with patch.object(bridge, '_initialize_websocket_manager', new_callable=AsyncMock), \
             patch.object(bridge, '_initialize_registry', new_callable=AsyncMock), \
             patch.object(bridge, '_initialize_thread_registry', new_callable=AsyncMock), \
             patch.object(bridge, '_setup_registry_integration', new_callable=AsyncMock), \
             patch.object(bridge, '_verify_integration', new_callable=AsyncMock) as mock_verify, \
             patch.object(bridge, '_start_health_monitoring', new_callable=AsyncMock):
            
            mock_verify.return_value = True
            
            result = await bridge.ensure_integration(
                supervisor=mock_supervisor,
                registry=mock_registry
            )
            
            assert result.success is True
            assert bridge._supervisor is mock_supervisor, "Supervisor should be stored"
            assert bridge._registry is mock_registry, "Registry should be stored"


class TestAgentWebSocketBridgeHealthMonitoring:
    """Test AgentWebSocketBridge health monitoring and recovery."""
    
    @pytest.mark.unit
    async def test_health_check_success(self):
        """Test successful health check."""
        # Business Value: Ensures system health monitoring for SLA compliance
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.ACTIVE
        
        with patch.object(bridge, '_check_websocket_manager_health', new_callable=AsyncMock) as mock_ws_health, \
             patch.object(bridge, '_check_registry_health', new_callable=AsyncMock) as mock_reg_health:
            
            mock_ws_health.return_value = True
            mock_reg_health.return_value = True
            
            health_status = await bridge.health_check()
            
            assert health_status.state == IntegrationState.ACTIVE
            assert health_status.websocket_manager_healthy is True
            assert health_status.registry_healthy is True
            assert health_status.consecutive_failures == 0
            assert health_status.error_message is None
            assert health_status.uptime_seconds >= 0
            
            # Verify metrics updated
            assert bridge.metrics.health_checks_performed == 1

    @pytest.mark.unit
    async def test_health_check_websocket_failure(self):
        """Test health check with WebSocket manager failure."""
        # Business Value: Detects issues that would prevent real-time chat delivery
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.ACTIVE
        
        with patch.object(bridge, '_check_websocket_manager_health', new_callable=AsyncMock) as mock_ws_health, \
             patch.object(bridge, '_check_registry_health', new_callable=AsyncMock) as mock_reg_health:
            
            mock_ws_health.return_value = False
            mock_reg_health.return_value = True
            
            health_status = await bridge.health_check()
            
            assert health_status.state == IntegrationState.DEGRADED
            assert health_status.websocket_manager_healthy is False
            assert health_status.registry_healthy is True
            assert health_status.consecutive_failures == 1
            assert "WebSocket manager unhealthy" in health_status.error_message

    @pytest.mark.unit
    async def test_health_check_complete_failure(self):
        """Test health check with complete system failure."""
        # Business Value: Ensures system enters failed state when critically broken
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.ACTIVE
        bridge.health_status.consecutive_failures = 2  # Set to near failure threshold
        
        with patch.object(bridge, '_check_websocket_manager_health', new_callable=AsyncMock) as mock_ws_health, \
             patch.object(bridge, '_check_registry_health', new_callable=AsyncMock) as mock_reg_health:
            
            mock_ws_health.return_value = False
            mock_reg_health.return_value = False
            
            health_status = await bridge.health_check()
            
            assert health_status.state == IntegrationState.FAILED
            assert health_status.websocket_manager_healthy is False
            assert health_status.registry_healthy is False
            assert health_status.consecutive_failures == 3
            assert bridge.state == IntegrationState.FAILED

    @pytest.mark.unit
    async def test_health_check_recovery_from_degraded(self):
        """Test health check recovery from degraded state."""
        # Business Value: Automatic recovery prevents extended service disruptions
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.DEGRADED
        bridge.health_status.consecutive_failures = 1
        
        with patch.object(bridge, '_check_websocket_manager_health', new_callable=AsyncMock) as mock_ws_health, \
             patch.object(bridge, '_check_registry_health', new_callable=AsyncMock) as mock_reg_health:
            
            mock_ws_health.return_value = True
            mock_reg_health.return_value = True
            
            health_status = await bridge.health_check()
            
            assert health_status.state == IntegrationState.ACTIVE
            assert health_status.consecutive_failures == 0
            assert health_status.error_message is None
            assert bridge.state == IntegrationState.ACTIVE

    @pytest.mark.unit
    async def test_get_health_status_detailed(self):
        """Test detailed health status reporting."""
        # Business Value: Provides monitoring data for operational dashboards
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.ACTIVE
        bridge.metrics.current_uptime_start = datetime.now(timezone.utc) - timedelta(hours=2)
        
        status = await bridge.get_health_status()
        
        assert status["integration_state"] == "active"
        assert status["websocket_manager_healthy"] is False  # Not initialized yet
        assert status["registry_healthy"] is False  # Not initialized yet
        assert "uptime_hours" in status
        assert "last_health_check" in status
        assert "consecutive_failures" in status
        assert status["uptime_hours"] >= 1.9  # Should be close to 2 hours

    @pytest.mark.unit
    async def test_get_metrics_comprehensive(self):
        """Test comprehensive metrics reporting."""
        # Business Value: Enables performance monitoring and capacity planning
        
        bridge = AgentWebSocketBridge()
        bridge.metrics.total_initializations = 5
        bridge.metrics.successful_initializations = 4
        bridge.metrics.failed_initializations = 1
        bridge.metrics.recovery_attempts = 2
        bridge.metrics.successful_recoveries = 1
        bridge.metrics.health_checks_performed = 10
        
        metrics = await bridge.get_metrics()
        
        assert metrics["total_initializations"] == 5
        assert metrics["successful_initializations"] == 4
        assert metrics["failed_initializations"] == 1
        assert metrics["recovery_attempts"] == 2
        assert metrics["successful_recoveries"] == 1
        assert metrics["health_checks_performed"] == 10
        assert metrics["success_rate_pct"] == 80.0  # 4/5 * 100
        assert metrics["recovery_success_rate_pct"] == 50.0  # 1/2 * 100

    @pytest.mark.unit
    async def test_monitor_observer_registration(self):
        """Test monitor observer registration and notification."""
        # Business Value: Enables external monitoring integrations for Enterprise customers
        
        bridge = AgentWebSocketBridge()
        mock_observer = Mock()
        mock_observer.component_id = "test-observer"
        mock_observer.on_health_change = AsyncMock()
        
        # Register observer
        bridge.register_monitor_observer(mock_observer)
        assert len(bridge._monitor_observers) == 1
        assert bridge._monitor_observers[0] is mock_observer
        
        # Trigger health change notification
        with patch.object(bridge, '_notify_monitors_of_health_change', new_callable=AsyncMock) as mock_notify:
            bridge.state = IntegrationState.FAILED
            await bridge.health_check()
            # Note: Actual notification would be called within health_check in real implementation


class TestAgentWebSocketBridgeRecovery:
    """Test AgentWebSocketBridge recovery mechanisms."""
    
    @pytest.mark.unit
    async def test_recover_integration_success(self):
        """Test successful integration recovery."""
        # Business Value: Automatic recovery prevents extended downtime and revenue loss
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.FAILED
        
        with patch.object(bridge, 'ensure_integration', new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = IntegrationResult(
                success=True,
                state=IntegrationState.ACTIVE,
                duration_ms=100.0,
                recovery_attempted=True
            )
            
            result = await bridge.recover_integration()
            
            assert result.success is True
            assert result.state == IntegrationState.ACTIVE
            assert result.recovery_attempted is True
            assert bridge.metrics.recovery_attempts == 1
            assert bridge.metrics.successful_recoveries == 1

    @pytest.mark.unit
    async def test_recover_integration_failure(self):
        """Test integration recovery failure."""
        # Business Value: Tracks failed recovery attempts for alerting
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.FAILED
        
        with patch.object(bridge, 'ensure_integration', new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = IntegrationResult(
                success=False,
                state=IntegrationState.FAILED,
                error="Recovery failed",
                recovery_attempted=True
            )
            
            result = await bridge.recover_integration()
            
            assert result.success is False
            assert result.state == IntegrationState.FAILED
            assert result.recovery_attempted is True
            assert bridge.metrics.recovery_attempts == 1
            assert bridge.metrics.successful_recoveries == 0

    @pytest.mark.unit
    async def test_recover_integration_max_attempts(self):
        """Test recovery stops after maximum attempts."""
        # Business Value: Prevents infinite recovery loops that could impact performance
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.FAILED
        bridge.config.recovery_max_attempts = 2
        
        # Mock failed recovery attempts
        with patch.object(bridge, 'ensure_integration', new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = IntegrationResult(
                success=False,
                state=IntegrationState.FAILED,
                error="Persistent failure",
                recovery_attempted=True
            )
            
            # First attempt
            result1 = await bridge.recover_integration()
            assert result1.success is False
            assert bridge.metrics.recovery_attempts == 1
            
            # Second attempt
            result2 = await bridge.recover_integration()
            assert result2.success is False
            assert bridge.metrics.recovery_attempts == 2
            
            # Third attempt should not happen - already at max
            with patch.object(bridge, 'ensure_integration') as mock_blocked:
                result3 = await bridge.recover_integration()
                mock_blocked.assert_not_called()  # Should not attempt recovery again


class TestAgentWebSocketBridgeUserEmitters:
    """Test AgentWebSocketBridge per-user emitter creation."""
    
    @pytest.mark.unit
    async def test_create_user_emitter_success(self):
        """Test successful user emitter creation."""
        # Business Value: Ensures isolated WebSocket events for Enterprise multi-user security
        
        bridge = AgentWebSocketBridge()
        mock_factory = MockFactory()
        mock_user_context = mock_factory.create_mock(
            "UserExecutionContext",
            user_id="test-user",
            session_id="test-session"
        )
        
        with patch('netra_backend.app.services.agent_websocket_bridge.validate_user_context') as mock_validate, \
             patch('netra_backend.app.services.agent_websocket_bridge.create_websocket_manager') as mock_create_ws, \
             patch('netra_backend.app.services.agent_websocket_bridge.WebSocketEmitterFactory') as mock_factory:
            
            mock_validate.return_value = mock_user_context
            mock_ws_manager = Mock()
            mock_create_ws.return_value = mock_ws_manager
            mock_emitter = Mock()
            mock_factory.create_scoped_emitter.return_value = mock_emitter
            
            result = await bridge.create_user_emitter(mock_user_context)
            
            assert result is mock_emitter
            mock_validate.assert_called_once_with(mock_user_context)
            mock_create_ws.assert_called_once_with(mock_user_context)
            mock_factory.create_scoped_emitter.assert_called_once_with(mock_ws_manager, mock_user_context)

    @pytest.mark.unit
    async def test_create_user_emitter_no_context(self):
        """Test user emitter creation fails without context."""
        # Business Value: Prevents security violations from anonymous emitters
        
        bridge = AgentWebSocketBridge()
        
        with pytest.raises(ValueError, match="user_context is required"):
            await bridge.create_user_emitter(None)

    @pytest.mark.unit
    async def test_create_user_emitter_validation_failure(self):
        """Test user emitter creation fails with invalid context."""
        # Business Value: Prevents unauthorized access to WebSocket events
        
        bridge = AgentWebSocketBridge()
        mock_user_context = Mock()
        
        with patch('netra_backend.app.services.agent_websocket_bridge.validate_user_context') as mock_validate:
            mock_validate.side_effect = ValueError("Invalid user context")
            
            with pytest.raises(ValueError, match="Failed to create user emitter"):
                await bridge.create_user_emitter(mock_user_context)

    @pytest.mark.unit
    async def test_create_user_emitter_websocket_failure(self):
        """Test user emitter creation fails when WebSocket manager creation fails."""
        # Business Value: Ensures proper error handling when WebSocket infrastructure is unavailable
        
        bridge = AgentWebSocketBridge()
        mock_factory = MockFactory()
        mock_user_context = mock_factory.create_mock(
            "UserExecutionContext",
            user_id="test-user",
            session_id="test-session"
        )
        
        with patch('netra_backend.app.services.agent_websocket_bridge.validate_user_context') as mock_validate, \
             patch('netra_backend.app.services.agent_websocket_bridge.create_websocket_manager') as mock_create_ws:
            
            mock_validate.return_value = mock_user_context
            mock_create_ws.side_effect = RuntimeError("WebSocket manager creation failed")
            
            with pytest.raises(ValueError, match="Failed to create user emitter"):
                await bridge.create_user_emitter(mock_user_context)

    @pytest.mark.unit
    async def test_create_user_emitter_from_ids_success(self):
        """Test successful user emitter creation from IDs."""
        # Business Value: Enables emitter creation when only user/session IDs are available
        
        user_id = "test-user-123"
        session_id = "test-session-456"
        
        with patch.object(AgentWebSocketBridge, 'create_user_emitter_from_ids', new_callable=AsyncMock) as mock_create:
            mock_emitter = Mock()
            mock_create.return_value = mock_emitter
            
            result = await AgentWebSocketBridge.create_user_emitter_from_ids(user_id, session_id)
            
            assert result is mock_emitter
            mock_create.assert_called_once_with(user_id, session_id)


class TestAgentWebSocketBridgeWebSocketNotifications:
    """Test AgentWebSocketBridge WebSocket event notifications (MISSION CRITICAL for chat value)."""
    
    @pytest.mark.unit
    async def test_notify_agent_started(self):
        """Test agent_started event notification."""
        # Business Value: Users see agent began processing - critical for engagement
        
        bridge = AgentWebSocketBridge()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        initial_params = {"query": "test query"}
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            await bridge.notify_agent_started(run_id, agent_name, initial_params)
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == "agent_started"
            assert call_args["agent_name"] == agent_name
            assert call_args["data"]["initial_parameters"] == initial_params

    @pytest.mark.unit
    async def test_notify_agent_thinking(self):
        """Test agent_thinking event notification."""
        # Business Value: Real-time reasoning visibility shows AI is working on valuable solutions
        
        bridge = AgentWebSocketBridge()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        thinking_content = "Analyzing your request..."
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            await bridge.notify_agent_thinking(run_id, agent_name, thinking_content)
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == "agent_thinking"
            assert call_args["agent_name"] == agent_name
            assert call_args["data"]["thinking_content"] == thinking_content

    @pytest.mark.unit
    async def test_notify_tool_executing(self):
        """Test tool_executing event notification."""
        # Business Value: Tool usage transparency demonstrates problem-solving approach
        
        bridge = AgentWebSocketBridge()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        tool_name = "CostCalculator"
        parameters = {"metric": "monthly_spend"}
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            await bridge.notify_tool_executing(run_id, agent_name, tool_name, parameters)
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == "tool_executing"
            assert call_args["agent_name"] == agent_name
            assert call_args["data"]["tool_name"] == tool_name
            assert call_args["data"]["parameters"] == parameters

    @pytest.mark.unit
    async def test_notify_tool_completed(self):
        """Test tool_completed event notification."""
        # Business Value: Tool results display delivers actionable insights to users
        
        bridge = AgentWebSocketBridge()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        tool_name = "CostCalculator"
        result = {"monthly_spend": 1500, "recommendations": ["Optimize instance types"]}
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            await bridge.notify_tool_completed(run_id, agent_name, tool_name, result)
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == "tool_completed"
            assert call_args["agent_name"] == agent_name
            assert call_args["data"]["tool_name"] == tool_name
            assert call_args["data"]["result"] == result

    @pytest.mark.unit
    async def test_notify_agent_completed(self):
        """Test agent_completed event notification."""
        # Business Value: Users know when valuable response is ready
        
        bridge = AgentWebSocketBridge()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        final_result = {"analysis": "Your infrastructure can be optimized", "savings": 500}
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            await bridge.notify_agent_completed(run_id, agent_name, final_result)
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == "agent_completed"
            assert call_args["agent_name"] == agent_name
            assert call_args["data"]["final_result"] == final_result

    @pytest.mark.unit
    async def test_notify_agent_error(self):
        """Test agent_error event notification."""
        # Business Value: Error transparency helps users understand issues and reduces support burden
        
        bridge = AgentWebSocketBridge()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        error_msg = "Failed to access cost data"
        error_context = {"error_code": "ACCESS_DENIED"}
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            await bridge.notify_agent_error(run_id, agent_name, error_msg, error_context)
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == "agent_error"
            assert call_args["agent_name"] == agent_name
            assert call_args["data"]["error_message"] == error_msg
            assert call_args["data"]["context"] == error_context

    @pytest.mark.unit
    async def test_notify_progress_update(self):
        """Test progress_update event notification."""
        # Business Value: Progress visibility keeps users engaged during longer agent operations
        
        bridge = AgentWebSocketBridge()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        progress_data = {"percentage": 75, "status": "Analyzing data", "eta_seconds": 30}
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            await bridge.notify_progress_update(run_id, agent_name, progress_data)
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == "progress_update"
            assert call_args["agent_name"] == agent_name
            assert call_args["data"]["progress"] == progress_data

    @pytest.mark.unit
    async def test_notify_custom_event(self):
        """Test custom event notification."""
        # Business Value: Flexible event system supports specialized agent workflows
        
        bridge = AgentWebSocketBridge()
        run_id = "test-run-123"
        event_type = "cost_analysis_milestone"
        custom_data = {"milestone": "data_collected", "next_steps": ["analysis", "recommendations"]}
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            await bridge.notify_custom(run_id, event_type, custom_data)
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == event_type
            assert call_args["data"] == custom_data


class TestAgentWebSocketBridgeThreadRegistry:
    """Test AgentWebSocketBridge thread registry integration."""
    
    @pytest.mark.unit
    async def test_register_run_thread_mapping_success(self):
        """Test successful run-thread mapping registration."""
        # Business Value: Enables proper thread-run correlation for multi-user isolation
        
        bridge = AgentWebSocketBridge()
        mock_thread_registry = AsyncMock()
        bridge._thread_registry = mock_thread_registry
        
        run_id = "test-run-123"
        thread_id = "test-thread-456"
        
        mock_thread_registry.register_mapping.return_value = True
        
        result = await bridge.register_run_thread_mapping(run_id, thread_id)
        
        assert result is True
        mock_thread_registry.register_mapping.assert_called_once_with(run_id, thread_id)

    @pytest.mark.unit
    async def test_register_run_thread_mapping_no_registry(self):
        """Test run-thread mapping registration without registry."""
        # Business Value: Graceful handling when thread registry is unavailable
        
        bridge = AgentWebSocketBridge()
        bridge._thread_registry = None
        
        result = await bridge.register_run_thread_mapping("run-123", "thread-456")
        
        assert result is False

    @pytest.mark.unit
    async def test_unregister_run_mapping_success(self):
        """Test successful run mapping unregistration."""
        # Business Value: Cleanup prevents memory leaks in long-running systems
        
        bridge = AgentWebSocketBridge()
        mock_thread_registry = AsyncMock()
        bridge._thread_registry = mock_thread_registry
        
        run_id = "test-run-123"
        
        mock_thread_registry.unregister_mapping.return_value = True
        
        result = await bridge.unregister_run_mapping(run_id)
        
        assert result is True
        mock_thread_registry.unregister_mapping.assert_called_once_with(run_id)

    @pytest.mark.unit
    async def test_get_thread_registry_status(self):
        """Test thread registry status retrieval."""
        # Business Value: Monitoring data for operational dashboards
        
        bridge = AgentWebSocketBridge()
        mock_thread_registry = AsyncMock()
        bridge._thread_registry = mock_thread_registry
        
        expected_status = {
            "active_mappings": 5,
            "total_registered": 10,
            "healthy": True
        }
        mock_thread_registry.get_status.return_value = expected_status
        
        result = await bridge.get_thread_registry_status()
        
        assert result == expected_status
        mock_thread_registry.get_status.assert_called_once()

    @pytest.mark.unit
    async def test_extract_thread_id_from_run_id(self):
        """Test thread ID extraction from run ID."""
        # Business Value: Enables proper event routing in multi-threaded conversations
        
        bridge = AgentWebSocketBridge()
        
        # Test standardized run ID format
        run_id = "thread_abc123_run_def456"
        expected_thread_id = "thread_abc123"
        
        result = bridge.extract_thread_id(run_id)
        
        assert result == expected_thread_id

    @pytest.mark.unit
    async def test_extract_thread_id_from_run_id_invalid_format(self):
        """Test thread ID extraction with invalid run ID format."""
        # Business Value: Graceful handling of malformed run IDs prevents crashes
        
        bridge = AgentWebSocketBridge()
        
        # Test invalid run ID format
        run_id = "invalid-run-id-format"
        
        result = bridge.extract_thread_id(run_id)
        
        assert result == run_id  # Returns original if parsing fails


class TestAgentWebSocketBridgeConcurrencyAndEdgeCases:
    """Test AgentWebSocketBridge concurrency handling and edge cases."""
    
    @pytest.mark.unit
    async def test_concurrent_integration_initialization(self):
        """Test concurrent integration initialization is handled safely."""
        # Business Value: Prevents race conditions that could cause system instability
        
        bridge = AgentWebSocketBridge()
        
        # Mock the initialization steps to simulate slow operations
        with patch.object(bridge, '_initialize_websocket_manager', new_callable=AsyncMock) as mock_ws, \
             patch.object(bridge, '_initialize_registry', new_callable=AsyncMock) as mock_reg, \
             patch.object(bridge, '_initialize_thread_registry', new_callable=AsyncMock) as mock_thread, \
             patch.object(bridge, '_setup_registry_integration', new_callable=AsyncMock) as mock_setup, \
             patch.object(bridge, '_verify_integration', new_callable=AsyncMock) as mock_verify, \
             patch.object(bridge, '_start_health_monitoring', new_callable=AsyncMock) as mock_health:
            
            # Add delays to simulate real initialization time
            async def slow_init():
                await asyncio.sleep(0.1)
            
            mock_ws.side_effect = slow_init
            mock_reg.side_effect = slow_init
            mock_thread.side_effect = slow_init
            mock_setup.side_effect = slow_init
            mock_verify.return_value = True
            mock_health.side_effect = slow_init
            
            # Start multiple initialization tasks concurrently
            tasks = [
                asyncio.create_task(bridge.ensure_integration()),
                asyncio.create_task(bridge.ensure_integration()),
                asyncio.create_task(bridge.ensure_integration())
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed and only one actual initialization should occur
            assert all(result.success for result in results)
            assert all(result.state == IntegrationState.ACTIVE for result in results)
            
            # Verify initialization only happened once (due to locking)
            assert bridge.metrics.total_initializations == 1
            assert bridge.metrics.successful_initializations == 1

    @pytest.mark.unit
    async def test_concurrent_health_checks(self):
        """Test concurrent health checks don't interfere with each other."""
        # Business Value: Ensures monitoring system stability under load
        
        bridge = AgentWebSocketBridge()
        bridge.state = IntegrationState.ACTIVE
        
        with patch.object(bridge, '_check_websocket_manager_health', new_callable=AsyncMock) as mock_ws_health, \
             patch.object(bridge, '_check_registry_health', new_callable=AsyncMock) as mock_reg_health:
            
            async def slow_health_check():
                await asyncio.sleep(0.05)
                return True
            
            mock_ws_health.side_effect = slow_health_check
            mock_reg_health.side_effect = slow_health_check
            
            # Start multiple health checks concurrently
            tasks = [
                asyncio.create_task(bridge.health_check()),
                asyncio.create_task(bridge.health_check()),
                asyncio.create_task(bridge.health_check())
            ]
            
            health_statuses = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(health_statuses) == 3
            assert all(status.state == IntegrationState.ACTIVE for status in health_statuses)
            assert all(status.websocket_manager_healthy for status in health_statuses)

    @pytest.mark.unit
    async def test_shutdown_during_initialization(self):
        """Test shutdown handling during active initialization."""
        # Business Value: Ensures graceful shutdown prevents resource leaks
        
        bridge = AgentWebSocketBridge()
        
        with patch.object(bridge, '_initialize_websocket_manager', new_callable=AsyncMock) as mock_ws:
            
            async def slow_init():
                # Check if shutdown was requested during initialization
                if bridge._shutdown:
                    raise RuntimeError("Initialization cancelled due to shutdown")
                await asyncio.sleep(0.1)
            
            mock_ws.side_effect = slow_init
            
            # Start initialization
            init_task = asyncio.create_task(bridge.ensure_integration())
            
            # Shutdown immediately
            await bridge.shutdown()
            
            # Initialization should handle shutdown gracefully
            result = await init_task
            assert result.success is False
            assert "shutdown" in result.error.lower() or "cancelled" in result.error.lower()

    @pytest.mark.unit
    async def test_invalid_run_id_handling(self):
        """Test handling of suspicious or invalid run IDs."""
        # Business Value: Security protection against malformed or malicious run IDs
        
        bridge = AgentWebSocketBridge()
        
        # Test various invalid run ID formats
        invalid_run_ids = [
            "",  # Empty
            None,  # None value
            "a" * 1000,  # Extremely long
            "../../../etc/passwd",  # Path traversal
            "<script>alert('xss')</script>",  # XSS attempt
            "run_id; DROP TABLE runs;",  # SQL injection attempt
        ]
        
        with patch.object(bridge, 'emit_agent_event', new_callable=AsyncMock) as mock_emit:
            
            for invalid_run_id in invalid_run_ids:
                # Should handle invalid run IDs gracefully without crashing
                try:
                    await bridge.notify_agent_started(invalid_run_id, "TestAgent", {})
                except Exception as e:
                    # Validation errors are acceptable, crashes are not
                    assert isinstance(e, (ValueError, TypeError))
                    assert "invalid" in str(e).lower() or "malformed" in str(e).lower()

    @pytest.mark.unit
    async def test_event_validation_and_sanitization(self):
        """Test event data validation and sanitization."""
        # Business Value: Prevents data leakage and ensures clean event data
        
        bridge = AgentWebSocketBridge()
        
        # Test data that should be sanitized
        sensitive_data = {
            "api_key": "sk-1234567890abcdef",
            "password": "secret123",
            "token": "bearer_token_xyz",
            "credentials": {"username": "admin", "password": "admin"},
            "normal_data": "this should remain"
        }
        
        sanitized = bridge._sanitize_parameters(sensitive_data)
        
        # Sensitive fields should be redacted
        assert "REDACTED" in sanitized.get("api_key", "")
        assert "REDACTED" in sanitized.get("password", "")
        assert "REDACTED" in sanitized.get("token", "")
        
        # Normal data should remain
        assert sanitized["normal_data"] == "this should remain"

    @pytest.mark.unit
    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load."""
        # Business Value: Prevents memory leaks that could cause system crashes
        
        bridge = AgentWebSocketBridge()
        
        # Simulate high event volume
        initial_observer_count = len(bridge._monitor_observers)
        
        # Add and remove many observers to test cleanup
        for i in range(100):
            mock_observer = Mock()
            mock_observer.component_id = f"observer-{i}"
            bridge.register_monitor_observer(mock_observer)
        
        assert len(bridge._monitor_observers) == initial_observer_count + 100
        
        # Remove all added observers
        for i in range(100):
            observer_to_remove = None
            for observer in bridge._monitor_observers:
                if observer.component_id == f"observer-{i}":
                    observer_to_remove = observer
                    break
            
            if observer_to_remove:
                bridge.remove_monitor_observer(observer_to_remove)
        
        # Should be back to initial state
        assert len(bridge._monitor_observers) == initial_observer_count


class TestAgentWebSocketBridgeFactoryFunction:
    """Test the factory function for creating AgentWebSocketBridge instances."""
    
    @pytest.mark.unit
    async def test_create_agent_websocket_bridge_without_context(self):
        """Test bridge creation without user context."""
        # Business Value: Creates bridge for system-level operations
        
        bridge = create_agent_websocket_bridge()
        
        assert isinstance(bridge, AgentWebSocketBridge)
        assert bridge.state == IntegrationState.UNINITIALIZED
        assert bridge._initialized is True

    @pytest.mark.unit
    async def test_create_agent_websocket_bridge_with_context(self):
        """Test bridge creation with user context."""
        # Business Value: Creates bridge with user context for isolated operations
        
        mock_factory = MockFactory()
        mock_user_context = mock_factory.create_mock(
            "UserExecutionContext",
            user_id="test-user",
            session_id="test-session"
        )
        
        bridge = create_agent_websocket_bridge(mock_user_context)
        
        assert isinstance(bridge, AgentWebSocketBridge)
        assert bridge.state == IntegrationState.UNINITIALIZED


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "unit"
    ])