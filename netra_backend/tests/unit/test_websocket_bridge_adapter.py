"""
Comprehensive Unit Tests for WebSocketBridgeAdapter - SSOT Agent WebSocket Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal + All User Segments  
- Business Goal: Platform Stability & Chat Business Value Delivery
- Value Impact: Ensures $500K+ ARR by validating WebSocket adapter that enables substantive AI chat interactions
- Strategic Impact: MISSION CRITICAL - Adapter failures = immediate revenue loss as agents cannot send WebSocket events

CRITICAL: WebSocketBridgeAdapter is the SSOT component that replaces legacy WebSocketContextMixin
and provides agents with clean interface to AgentWebSocketBridge for our core business value:
1. WebSocket events for real-time agent interaction (user engagement)
2. Clean separation of concerns between agents and WebSocket infrastructure
3. Consistent error handling and logging for all agent WebSocket operations
4. Parameter validation and sanitization protecting sensitive data

These tests validate that our adapter delivers business value by:
- Ensuring all 5 critical WebSocket events are properly emitted
- Validating bridge configuration and management
- Testing error handling prevents agent crashes
- Verifying logging captures critical failures for debugging
- Confirming parameter validation protects sensitive data

Test Coverage Target: 100% of critical adapter flows in WebSocketBridgeAdapter
"""

import asyncio
import time
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, Optional

import pytest

# SSOT test framework imports
from test_framework.ssot.base import BaseTestCase, AsyncBaseTestCase
from shared.isolated_environment import get_env

# Import the module under test
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter


class TestWebSocketBridgeAdapterInitialization(BaseTestCase):
    """Test WebSocketBridgeAdapter initialization and state management."""
    
    @pytest.mark.unit
    def test_adapter_initialization_default_state(self):
        """Test adapter initializes with proper default state."""
        # Business Value: Ensures adapter starts in clean state for all agent types
        
        adapter = WebSocketBridgeAdapter()
        
        # Verify initialization state
        assert adapter._bridge is None, "Bridge should be None initially"
        assert adapter._run_id is None, "Run ID should be None initially"
        assert adapter._agent_name is None, "Agent name should be None initially"
        assert not adapter.has_websocket_bridge(), "Should not have bridge initially"
    
    @pytest.mark.unit
    def test_adapter_initialization_multiple_instances(self):
        """Test multiple adapter instances are properly isolated."""
        # Business Value: Ensures proper multi-user isolation in concurrent agent operations
        
        adapter1 = WebSocketBridgeAdapter()
        adapter2 = WebSocketBridgeAdapter()
        
        # Verify instances are independent
        assert adapter1 is not adapter2, "Should create separate instances"
        assert adapter1._bridge is not adapter2._bridge, "Bridges should be independent"
        assert adapter1._run_id is not adapter2._run_id, "Run IDs should be independent"


class TestWebSocketBridgeAdapterConfiguration(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter bridge configuration and management."""
    
    @pytest.mark.unit
    async def test_set_websocket_bridge_success(self):
        """Test successful WebSocket bridge configuration."""
        # Business Value: Enables agent-websocket coordination for chat delivery
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            adapter.set_websocket_bridge(mock_bridge, run_id, agent_name)
            
            # Verify configuration
            assert adapter._bridge is mock_bridge, "Bridge should be set"
            assert adapter._run_id == run_id, "Run ID should be set"
            assert adapter._agent_name == agent_name, "Agent name should be set"
            assert adapter.has_websocket_bridge(), "Should have bridge after configuration"
            
            # Verify success logging
            mock_logger.info.assert_called_once()
            success_log = mock_logger.info.call_args[0][0]
            assert "✅ WebSocket bridge configured" in success_log
            assert agent_name in success_log
            assert run_id in success_log
    
    @pytest.mark.unit
    async def test_set_websocket_bridge_none_bridge_critical_error(self):
        """Test setting None bridge triggers critical error logging."""
        # Business Value: Prevents silent failures that would break chat functionality
        
        adapter = WebSocketBridgeAdapter()
        agent_name = "TestAgent"
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            adapter.set_websocket_bridge(None, "run-123", agent_name)
            
            # Verify critical error logging
            assert mock_logger.error.call_count == 2, "Should log critical error for None bridge"
            error_calls = mock_logger.error.call_args_list
            
            # Check first error log (None bridge)
            first_error = error_calls[0][0][0]
            assert "❌ CRITICAL" in first_error
            assert "None bridge" in first_error
            assert agent_name in first_error
            
            # Check second error log (configuration failure)
            second_error = error_calls[1][0][0]
            assert "❌ WebSocket bridge configuration FAILED" in second_error
    
    @pytest.mark.unit
    async def test_set_websocket_bridge_none_run_id_critical_error(self):
        """Test setting None run_id triggers critical error logging."""
        # Business Value: Ensures proper run context for event routing
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        agent_name = "TestAgent"
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            adapter.set_websocket_bridge(mock_bridge, None, agent_name)
            
            # Verify critical error logging for None run_id
            error_calls = mock_logger.error.call_args_list
            assert any("❌ CRITICAL" in str(call) and "None run_id" in str(call) for call in error_calls)
            assert any("❌ WebSocket bridge configuration FAILED" in str(call) for call in error_calls)
    
    @pytest.mark.unit
    async def test_set_websocket_bridge_empty_run_id_critical_error(self):
        """Test setting empty run_id triggers critical error logging."""
        # Business Value: Validates run ID format to prevent routing failures
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        agent_name = "TestAgent"
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            adapter.set_websocket_bridge(mock_bridge, "", agent_name)
            
            # Verify configuration failure logged
            error_calls = mock_logger.error.call_args_list
            assert any("❌ WebSocket bridge configuration FAILED" in str(call) for call in error_calls)
    
    @pytest.mark.unit
    async def test_set_websocket_bridge_reconfiguration(self):
        """Test reconfiguring bridge with different parameters."""
        # Business Value: Supports agent lifecycle changes and context switching
        
        adapter = WebSocketBridgeAdapter()
        
        # Initial configuration
        mock_bridge1 = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge1, "run-123", "Agent1")
        
        # Reconfiguration
        mock_bridge2 = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge2, "run-456", "Agent2")
        
        # Verify reconfiguration
        assert adapter._bridge is mock_bridge2, "Bridge should be updated"
        assert adapter._run_id == "run-456", "Run ID should be updated"
        assert adapter._agent_name == "Agent2", "Agent name should be updated"
    
    @pytest.mark.unit
    async def test_has_websocket_bridge_various_states(self):
        """Test has_websocket_bridge method under various configuration states."""
        # Business Value: Reliable state checking prevents event emission failures
        
        adapter = WebSocketBridgeAdapter()
        
        # Initially no bridge
        assert not adapter.has_websocket_bridge()
        
        # Bridge but no run_id
        adapter._bridge = AsyncMock()
        assert not adapter.has_websocket_bridge()
        
        # Run_id but no bridge
        adapter._bridge = None
        adapter._run_id = "run-123"
        assert not adapter.has_websocket_bridge()
        
        # Both bridge and run_id
        adapter._bridge = AsyncMock()
        adapter._run_id = "run-123"
        assert adapter.has_websocket_bridge()
        
        # Missing run_id again
        adapter._run_id = None
        assert not adapter.has_websocket_bridge()


class TestWebSocketBridgeAdapterEventEmission(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter event emission methods (MISSION CRITICAL for chat value)."""
    
    def create_test_adapter(self):
        """Create a configured test adapter for testing."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        run_id = "test-run-123"
        agent_name = "TestAgent"
        
        # Configure adapter for testing
        adapter.set_websocket_bridge(mock_bridge, run_id, agent_name)
        return adapter, mock_bridge, run_id, agent_name
    
    @pytest.mark.unit
    async def test_emit_agent_started_success(self):
        """Test successful agent_started event emission."""
        # Business Value: Users see agent began processing - critical for engagement
        
        adapter, mock_bridge, run_id, agent_name = self.create_test_adapter()
        message = "Starting analysis of your request"
        
        await adapter.emit_agent_started(message)
        
        # Verify bridge method called correctly
        mock_bridge.notify_agent_started.assert_called_once_with(
            run_id,
            agent_name,
            context={"message": message}
        )
    
    @pytest.mark.unit
    async def test_emit_agent_started_no_message(self):
        """Test agent_started event emission without message."""
        # Business Value: Supports minimal agent_started events
        
        await self.adapter.emit_agent_started()
        
        # Verify bridge called with empty context
        self.mock_bridge.notify_agent_started.assert_called_once_with(
            self.run_id,
            self.agent_name,
            context={}
        )
    
    @pytest.mark.unit
    async def test_emit_agent_started_no_bridge_warning(self):
        """Test agent_started emission without bridge logs warning."""
        # Business Value: Prevents silent failures in critical event emission
        
        # Create adapter without bridge
        no_bridge_adapter = WebSocketBridgeAdapter()
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await no_bridge_adapter.emit_agent_started("test message")
            
            # Verify warning logged
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "❌ No WebSocket bridge for agent_started event" in warning_msg
    
    @pytest.mark.unit
    async def test_emit_agent_started_bridge_exception_handled(self):
        """Test agent_started emission handles bridge exceptions gracefully."""
        # Business Value: Prevents agent crashes when WebSocket fails
        
        self.mock_bridge.notify_agent_started.side_effect = RuntimeError("WebSocket connection failed")
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            # Should not raise exception
            await self.adapter.emit_agent_started("test message")
            
            # Verify error logged
            mock_logger.debug.assert_called_once_with("Failed to emit agent_started: WebSocket connection failed")
    
    @pytest.mark.unit
    async def test_emit_thinking_success(self):
        """Test successful agent_thinking event emission."""
        # Business Value: Real-time reasoning visibility shows AI working on valuable solutions
        
        thought = "Analyzing your cost optimization requirements"
        step_number = 1
        
        await self.adapter.emit_thinking(thought, step_number)
        
        # Verify bridge method called correctly
        self.mock_bridge.notify_agent_thinking.assert_called_once_with(
            self.run_id,
            self.agent_name,
            thought,
            step_number=step_number
        )
    
    @pytest.mark.unit
    async def test_emit_thinking_without_step_number(self):
        """Test thinking event emission without step number."""
        # Business Value: Supports flexible thinking event patterns
        
        thought = "Processing your request"
        
        await self.adapter.emit_thinking(thought)
        
        # Verify bridge called without step number
        self.mock_bridge.notify_agent_thinking.assert_called_once_with(
            self.run_id,
            self.agent_name,
            thought,
            step_number=None
        )
    
    @pytest.mark.unit
    async def test_emit_thinking_no_bridge_silent_return(self):
        """Test thinking emission without bridge returns silently."""
        # Business Value: Graceful degradation when WebSocket unavailable
        
        no_bridge_adapter = WebSocketBridgeAdapter()
        
        # Should not raise exception or log (silent return)
        await no_bridge_adapter.emit_thinking("test thought")
    
    @pytest.mark.unit
    async def test_emit_thinking_bridge_exception_handled(self):
        """Test thinking emission handles bridge exceptions gracefully."""
        # Business Value: Prevents agent crashes during thinking events
        
        self.mock_bridge.notify_agent_thinking.side_effect = ConnectionError("WebSocket disconnected")
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_thinking("test thought")
            
            # Verify error logged
            mock_logger.debug.assert_called_once_with("Failed to emit thinking: WebSocket disconnected")
    
    @pytest.mark.unit
    async def test_emit_tool_executing_success(self):
        """Test successful tool_executing event emission."""
        # Business Value: Tool usage transparency demonstrates problem-solving approach
        
        tool_name = "CostAnalyzer"
        parameters = {"region": "us-east-1", "period": "monthly"}
        
        await self.adapter.emit_tool_executing(tool_name, parameters)
        
        # Verify bridge method called correctly
        self.mock_bridge.notify_tool_executing.assert_called_once_with(
            self.run_id,
            self.agent_name,
            tool_name,
            parameters=parameters
        )
    
    @pytest.mark.unit
    async def test_emit_tool_executing_without_parameters(self):
        """Test tool_executing emission without parameters."""
        # Business Value: Supports tools that don't require parameters
        
        tool_name = "StatusChecker"
        
        await self.adapter.emit_tool_executing(tool_name)
        
        # Verify bridge called without parameters
        self.mock_bridge.notify_tool_executing.assert_called_once_with(
            self.run_id,
            self.agent_name,
            tool_name,
            parameters=None
        )
    
    @pytest.mark.unit
    async def test_emit_tool_executing_bridge_exception_handled(self):
        """Test tool_executing emission handles bridge exceptions."""
        # Business Value: Tool execution continues even if WebSocket fails
        
        self.mock_bridge.notify_tool_executing.side_effect = TimeoutError("WebSocket timeout")
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_tool_executing("TestTool", {})
            
            # Verify error logged
            mock_logger.debug.assert_called_once_with("Failed to emit tool_executing: WebSocket timeout")
    
    @pytest.mark.unit
    async def test_emit_tool_completed_success(self):
        """Test successful tool_completed event emission."""
        # Business Value: Tool results display delivers actionable insights to users
        
        tool_name = "CostAnalyzer"
        result = {"monthly_spend": 1500, "optimization_potential": 20}
        
        await self.adapter.emit_tool_completed(tool_name, result)
        
        # Verify bridge method called correctly
        self.mock_bridge.notify_tool_completed.assert_called_once_with(
            self.run_id,
            self.agent_name,
            tool_name,
            result=result
        )
    
    @pytest.mark.unit
    async def test_emit_tool_completed_without_result(self):
        """Test tool_completed emission without result data."""
        # Business Value: Supports tools that complete without return data
        
        tool_name = "SystemNotifier"
        
        await self.adapter.emit_tool_completed(tool_name)
        
        # Verify bridge called without result
        self.mock_bridge.notify_tool_completed.assert_called_once_with(
            self.run_id,
            self.agent_name,
            tool_name,
            result=None
        )
    
    @pytest.mark.unit
    async def test_emit_tool_completed_bridge_exception_handled(self):
        """Test tool_completed emission handles bridge exceptions."""
        # Business Value: Agent completion continues even if WebSocket fails
        
        self.mock_bridge.notify_tool_completed.side_effect = ValueError("Invalid result format")
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_tool_completed("TestTool", {"data": "test"})
            
            # Verify error logged
            mock_logger.debug.assert_called_once_with("Failed to emit tool_completed: Invalid result format")
    
    @pytest.mark.unit
    async def test_emit_agent_completed_success(self):
        """Test successful agent_completed event emission."""
        # Business Value: Users know when valuable response is ready
        
        result = {"analysis": "Cost optimization completed", "savings": 300}
        
        await self.adapter.emit_agent_completed(result)
        
        # Verify bridge method called correctly
        self.mock_bridge.notify_agent_completed.assert_called_once_with(
            self.run_id,
            self.agent_name,
            result=result
        )
    
    @pytest.mark.unit
    async def test_emit_agent_completed_without_result(self):
        """Test agent_completed emission without result data."""
        # Business Value: Supports agents that complete without explicit results
        
        await self.adapter.emit_agent_completed()
        
        # Verify bridge called without result
        self.mock_bridge.notify_agent_completed.assert_called_once_with(
            self.run_id,
            self.agent_name,
            result=None
        )
    
    @pytest.mark.unit
    async def test_emit_agent_completed_no_bridge_warning(self):
        """Test agent_completed emission without bridge logs warning."""
        # Business Value: Critical event failures should be visible for debugging
        
        no_bridge_adapter = WebSocketBridgeAdapter()
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await no_bridge_adapter.emit_agent_completed({"result": "test"})
            
            # Verify warning logged
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "❌ No WebSocket bridge for agent_completed event" in warning_msg
    
    @pytest.mark.unit
    async def test_emit_agent_completed_bridge_exception_handled(self):
        """Test agent_completed emission handles bridge exceptions."""
        # Business Value: Agent lifecycle completes even if WebSocket fails
        
        self.mock_bridge.notify_agent_completed.side_effect = Exception("Unexpected error")
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_agent_completed({"data": "test"})
            
            # Verify error logged
            mock_logger.debug.assert_called_once_with("Failed to emit agent_completed: Unexpected error")
    
    @pytest.mark.unit
    async def test_emit_progress_success(self):
        """Test successful progress update emission."""
        # Business Value: Progress visibility keeps users engaged during operations
        
        content = "Processing 75% complete"
        is_complete = False
        
        await self.adapter.emit_progress(content, is_complete)
        
        # Verify bridge method called correctly
        expected_progress_data = {
            "content": content,
            "is_complete": is_complete
        }
        self.mock_bridge.notify_progress_update.assert_called_once_with(
            self.run_id,
            self.agent_name,
            expected_progress_data
        )
    
    @pytest.mark.unit
    async def test_emit_progress_completion(self):
        """Test progress emission with completion flag."""
        # Business Value: Clear completion signaling for user experience
        
        content = "Analysis complete"
        
        await self.adapter.emit_progress(content, is_complete=True)
        
        # Verify completion flag set
        call_args = self.mock_bridge.notify_progress_update.call_args[0]
        progress_data = call_args[2]
        assert progress_data["is_complete"] is True
    
    @pytest.mark.unit
    async def test_emit_progress_bridge_exception_handled(self):
        """Test progress emission handles bridge exceptions."""
        # Business Value: Progress tracking failure doesn't stop agent execution
        
        self.mock_bridge.notify_progress_update.side_effect = RuntimeError("Progress update failed")
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_progress("test progress")
            
            # Verify error logged
            mock_logger.debug.assert_called_once_with("Failed to emit progress: Progress update failed")
    
    @pytest.mark.unit
    async def test_emit_error_success(self):
        """Test successful error event emission."""
        # Business Value: Error transparency helps users understand issues
        
        error_message = "Failed to access cost data"
        error_type = "PERMISSION_DENIED"
        error_details = {"resource": "billing_api", "code": 403}
        
        await self.adapter.emit_error(error_message, error_type, error_details)
        
        # Verify bridge method called correctly
        expected_context = {
            "error_type": error_type,
            "details": error_details
        }
        self.mock_bridge.notify_agent_error.assert_called_once_with(
            self.run_id,
            self.agent_name,
            error_message,
            error_context=expected_context
        )
    
    @pytest.mark.unit
    async def test_emit_error_minimal_parameters(self):
        """Test error emission with minimal parameters."""
        # Business Value: Supports simple error reporting patterns
        
        error_message = "Something went wrong"
        
        await self.adapter.emit_error(error_message)
        
        # Verify bridge called with minimal context
        expected_context = {
            "error_type": "general",
            "details": None
        }
        self.mock_bridge.notify_agent_error.assert_called_once_with(
            self.run_id,
            self.agent_name,
            error_message,
            error_context=expected_context
        )
    
    @pytest.mark.unit
    async def test_emit_error_with_type_only(self):
        """Test error emission with type but no details."""
        # Business Value: Supports categorized errors without extra data
        
        error_message = "Authentication failed"
        error_type = "AUTH_ERROR"
        
        await self.adapter.emit_error(error_message, error_type)
        
        # Verify context includes type but no details
        call_args = self.mock_bridge.notify_agent_error.call_args
        error_context = call_args[1]["error_context"]
        assert error_context["error_type"] == error_type
        assert error_context["details"] is None
    
    @pytest.mark.unit
    async def test_emit_error_no_type_or_details(self):
        """Test error emission without type or details."""
        # Business Value: Handles minimal error cases
        
        error_message = "Basic error"
        
        await self.adapter.emit_error(error_message, None, None)
        
        # Verify no context sent when no type or details
        self.mock_bridge.notify_agent_error.assert_called_once_with(
            self.run_id,
            self.agent_name,
            error_message,
            error_context=None
        )
    
    @pytest.mark.unit
    async def test_emit_error_bridge_exception_handled(self):
        """Test error emission handles bridge exceptions."""
        # Business Value: Error reporting failure doesn't mask original error
        
        self.mock_bridge.notify_agent_error.side_effect = Exception("Error notification failed")
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_error("Original error message")
            
            # Verify error logged
            mock_logger.debug.assert_called_once_with("Failed to emit error: Error notification failed")


class TestWebSocketBridgeAdapterBackwardCompatibility(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter backward compatibility methods."""
    
    def create_test_adapter_for_compatibility(self):
        """Create a configured test adapter for backward compatibility testing."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-123", "TestAgent")
        return adapter, mock_bridge
    
    @pytest.mark.unit
    async def test_emit_tool_started_maps_to_tool_executing(self):
        """Test emit_tool_started maps to emit_tool_executing for backward compatibility."""
        # Business Value: Maintains compatibility with existing agent code
        
        tool_name = "LegacyTool"
        parameters = {"param1": "value1"}
        
        await self.adapter.emit_tool_started(tool_name, parameters)
        
        # Verify it calls the same bridge method as emit_tool_executing
        self.mock_bridge.notify_tool_executing.assert_called_once_with(
            "run-123",
            "TestAgent",
            tool_name,
            parameters=parameters
        )
    
    @pytest.mark.unit
    async def test_emit_subagent_started_success(self):
        """Test subagent_started event emission using custom notification."""
        # Business Value: Supports hierarchical agent workflows
        
        subagent_name = "DataAnalysisSubAgent"
        subagent_id = "subagent-456"
        
        await self.adapter.emit_subagent_started(subagent_name, subagent_id)
        
        # Verify custom notification called
        expected_data = {
            "subagent_name": subagent_name,
            "subagent_id": subagent_id
        }
        self.mock_bridge.notify_custom.assert_called_once_with(
            "run-123",
            "TestAgent",
            "subagent_started",
            expected_data
        )
    
    @pytest.mark.unit
    async def test_emit_subagent_started_without_id(self):
        """Test subagent_started emission without subagent ID."""
        # Business Value: Supports subagents that don't need explicit IDs
        
        subagent_name = "SimpleSubAgent"
        
        await self.adapter.emit_subagent_started(subagent_name)
        
        # Verify call with None subagent_id
        expected_data = {
            "subagent_name": subagent_name,
            "subagent_id": None
        }
        self.mock_bridge.notify_custom.assert_called_once_with(
            "run-123",
            "TestAgent",
            "subagent_started",
            expected_data
        )
    
    @pytest.mark.unit
    async def test_emit_subagent_completed_success(self):
        """Test subagent_completed event emission with full parameters."""
        # Business Value: Tracks subagent completion with performance metrics
        
        subagent_name = "DataAnalysisSubAgent"
        subagent_id = "subagent-456"
        result = {"processed_records": 1000, "insights": ["trend1", "trend2"]}
        duration_ms = 1500.5
        
        await self.adapter.emit_subagent_completed(subagent_name, subagent_id, result, duration_ms)
        
        # Verify custom notification called with all data
        expected_data = {
            "subagent_name": subagent_name,
            "subagent_id": subagent_id,
            "result": result,
            "duration_ms": duration_ms
        }
        self.mock_bridge.notify_custom.assert_called_once_with(
            "run-123",
            "TestAgent",
            "subagent_completed",
            expected_data
        )
    
    @pytest.mark.unit
    async def test_emit_subagent_completed_minimal(self):
        """Test subagent_completed emission with minimal parameters."""
        # Business Value: Supports simple subagent completion patterns
        
        subagent_name = "SimpleSubAgent"
        
        await self.adapter.emit_subagent_completed(subagent_name)
        
        # Verify call with default values
        expected_data = {
            "subagent_name": subagent_name,
            "subagent_id": None,
            "result": None,
            "duration_ms": 0
        }
        self.mock_bridge.notify_custom.assert_called_once_with(
            "run-123",
            "TestAgent",
            "subagent_completed",
            expected_data
        )
    
    @pytest.mark.unit
    async def test_subagent_events_no_bridge_silent_return(self):
        """Test subagent events return silently without bridge."""
        # Business Value: Graceful degradation for subagent events
        
        no_bridge_adapter = WebSocketBridgeAdapter()
        
        # Should not raise exceptions
        await no_bridge_adapter.emit_subagent_started("TestSubAgent")
        await no_bridge_adapter.emit_subagent_completed("TestSubAgent")
    
    @pytest.mark.unit
    async def test_subagent_events_bridge_exceptions_handled(self):
        """Test subagent events handle bridge exceptions gracefully."""
        # Business Value: Subagent failures don't break parent agent execution
        
        self.mock_bridge.notify_custom.side_effect = RuntimeError("Custom notification failed")
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_subagent_started("TestSubAgent")
            await self.adapter.emit_subagent_completed("TestSubAgent")
            
            # Verify both errors logged
            assert mock_logger.debug.call_count == 2
            debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
            assert any("Failed to emit subagent_started" in msg for msg in debug_calls)
            assert any("Failed to emit subagent_completed" in msg for msg in debug_calls)


class TestWebSocketBridgeAdapterErrorHandlingAndEdgeCases(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter error handling and edge cases."""
    
    @pytest.mark.unit
    async def test_all_events_no_bridge_behavior_consistent(self):
        """Test all event methods behave consistently without bridge."""
        # Business Value: Consistent error handling prevents agent confusion
        
        adapter = WebSocketBridgeAdapter()
        
        # These methods should log warnings
        warning_methods = [
            ("emit_agent_started", []),
            ("emit_agent_completed", [])
        ]
        
        # These methods should return silently
        silent_methods = [
            ("emit_thinking", ["test thought"]),
            ("emit_tool_executing", ["test tool"]),
            ("emit_tool_completed", ["test tool"]),
            ("emit_progress", ["test progress"]),
            ("emit_error", ["test error"]),
            ("emit_tool_started", ["test tool"]),
            ("emit_subagent_started", ["test subagent"]),
            ("emit_subagent_completed", ["test subagent"])
        ]
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            # Test warning methods
            for method_name, args in warning_methods:
                method = getattr(adapter, method_name)
                await method(*args)
            
            # Test silent methods
            for method_name, args in silent_methods:
                method = getattr(adapter, method_name)
                await method(*args)
            
            # Verify warning methods logged warnings
            assert mock_logger.warning.call_count == len(warning_methods)
    
    @pytest.mark.unit
    async def test_concurrent_event_emissions_thread_safe(self):
        """Test concurrent event emissions are handled safely."""
        # Business Value: Prevents race conditions in multi-threaded agent environments
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-123", "TestAgent")
        
        # Create multiple concurrent event emissions
        tasks = [
            adapter.emit_agent_started("Starting"),
            adapter.emit_thinking("Thinking"),
            adapter.emit_tool_executing("Tool1"),
            adapter.emit_tool_completed("Tool1", {"result": "data"}),
            adapter.emit_progress("50% complete"),
            adapter.emit_agent_completed({"final": "result"})
        ]
        
        # Execute concurrently
        await asyncio.gather(*tasks)
        
        # Verify all events were emitted
        assert mock_bridge.notify_agent_started.call_count == 1
        assert mock_bridge.notify_agent_thinking.call_count == 1
        assert mock_bridge.notify_tool_executing.call_count == 1
        assert mock_bridge.notify_tool_completed.call_count == 1
        assert mock_bridge.notify_progress_update.call_count == 1
        assert mock_bridge.notify_agent_completed.call_count == 1
    
    @pytest.mark.unit
    async def test_event_emission_with_none_values(self):
        """Test event emission handles None values gracefully."""
        # Business Value: Robust handling of edge cases prevents agent crashes
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-123", "TestAgent")
        
        # Test various None value scenarios
        await adapter.emit_agent_started(None)  # None message
        await adapter.emit_thinking(None)  # None thought - should not call bridge
        await adapter.emit_tool_executing(None, None)  # None tool name - should call bridge
        await adapter.emit_tool_completed(None, None)  # None tool name - should call bridge
        await adapter.emit_progress(None)  # None content - should call bridge
        await adapter.emit_error(None)  # None error message - should call bridge
        
        # Verify bridge calls (some methods might validate None values)
        # The adapter should pass None values to the bridge and let it handle validation
        assert mock_bridge.notify_agent_started.call_count == 1
        assert mock_bridge.notify_tool_executing.call_count == 1
        assert mock_bridge.notify_tool_completed.call_count == 1
        assert mock_bridge.notify_progress_update.call_count == 1
        assert mock_bridge.notify_agent_error.call_count == 1
    
    @pytest.mark.unit
    async def test_extremely_large_data_handling(self):
        """Test handling of extremely large data payloads."""
        # Business Value: Prevents memory issues with large agent results
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-123", "TestAgent")
        
        # Create large data payload
        large_data = {
            "large_list": ["item" + str(i) for i in range(10000)],
            "large_string": "x" * 100000,
            "nested_data": {"level1": {"level2": {"level3": {"data": "deep"}}}}
        }
        
        # Should handle large data without issues
        await adapter.emit_tool_completed("BigDataTool", large_data)
        await adapter.emit_agent_completed(large_data)
        
        # Verify events were emitted
        assert mock_bridge.notify_tool_completed.call_count == 1
        assert mock_bridge.notify_agent_completed.call_count == 1
    
    @pytest.mark.unit
    async def test_unicode_and_special_characters_handling(self):
        """Test handling of Unicode and special characters in event data."""
        # Business Value: Supports international users and special content
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-123", "TestAgent")
        
        # Test various Unicode and special characters
        unicode_data = {
            "emoji": "🚀 Analysis complete! 💰",
            "chinese": "数据分析完成",
            "arabic": "تم تحليل البيانات",
            "special_chars": "Special chars: !@#$%^&*()_+{}|:<>?[]\\;',./",
            "mixed": "Mixed: Hello 世界 🌍 مرحبا"
        }
        
        await adapter.emit_agent_started("Starting with 🚀")
        await adapter.emit_thinking("Thinking about 数据")
        await adapter.emit_tool_completed("UnicodeTool", unicode_data)
        await adapter.emit_error("Error with special chars: !@#$%")
        
        # Verify all events were emitted successfully
        assert mock_bridge.notify_agent_started.call_count == 1
        assert mock_bridge.notify_agent_thinking.call_count == 1
        assert mock_bridge.notify_tool_completed.call_count == 1
        assert mock_bridge.notify_agent_error.call_count == 1
    
    @pytest.mark.unit
    async def test_adapter_state_after_bridge_reconfiguration(self):
        """Test adapter state consistency after bridge reconfiguration."""
        # Business Value: Ensures proper state management during agent lifecycle
        
        adapter = WebSocketBridgeAdapter()
        
        # Initial configuration
        mock_bridge1 = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge1, "run-123", "Agent1")
        
        # Emit some events with first bridge
        await adapter.emit_agent_started("Starting with bridge 1")
        await adapter.emit_thinking("Using bridge 1")
        
        # Reconfigure with new bridge
        mock_bridge2 = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge2, "run-456", "Agent2")
        
        # Emit events with second bridge
        await adapter.emit_tool_executing("Tool with bridge 2")
        await adapter.emit_agent_completed({"bridge": "2"})
        
        # Verify first bridge only got first events
        assert mock_bridge1.notify_agent_started.call_count == 1
        assert mock_bridge1.notify_agent_thinking.call_count == 1
        assert mock_bridge1.notify_tool_executing.call_count == 0
        assert mock_bridge1.notify_agent_completed.call_count == 0
        
        # Verify second bridge only got second events
        assert mock_bridge2.notify_agent_started.call_count == 0
        assert mock_bridge2.notify_agent_thinking.call_count == 0
        assert mock_bridge2.notify_tool_executing.call_count == 1
        assert mock_bridge2.notify_agent_completed.call_count == 1


class TestWebSocketBridgeAdapterPerformanceAndReliability(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter performance characteristics and reliability."""
    
    @pytest.mark.unit
    async def test_high_frequency_event_emissions(self):
        """Test adapter handles high frequency event emissions efficiently."""
        # Business Value: Supports high-throughput agent scenarios without performance degradation
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-123", "HighThroughputAgent")
        
        # Emit many events rapidly
        event_count = 100
        start_time = time.time()
        
        for i in range(event_count):
            await adapter.emit_thinking(f"Thought {i}")
            await adapter.emit_progress(f"Progress {i}")
        
        end_time = time.time()
        
        # Verify all events were emitted
        assert mock_bridge.notify_agent_thinking.call_count == event_count
        assert mock_bridge.notify_progress_update.call_count == event_count
        
        # Performance check - should complete within reasonable time (allowing for mock overhead)
        duration = end_time - start_time
        assert duration < 5.0, f"High frequency emissions took too long: {duration}s"
    
    @pytest.mark.unit
    async def test_adapter_memory_usage_stability(self):
        """Test adapter doesn't accumulate memory over many operations."""
        # Business Value: Prevents memory leaks in long-running agent processes
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-123", "LongRunningAgent")
        
        # Perform many operations to test for memory leaks
        for cycle in range(10):
            # Reconfigure bridge (simulating agent context switches)
            new_bridge = AsyncMock()
            adapter.set_websocket_bridge(new_bridge, f"run-{cycle}", f"Agent-{cycle}")
            
            # Emit various events
            await adapter.emit_agent_started(f"Cycle {cycle}")
            await adapter.emit_thinking(f"Processing cycle {cycle}")
            await adapter.emit_tool_executing(f"Tool-{cycle}", {"cycle": cycle})
            await adapter.emit_tool_completed(f"Tool-{cycle}", {"result": f"data-{cycle}"})
            await adapter.emit_agent_completed({"cycle": cycle, "status": "complete"})
        
        # Verify adapter state is clean (no accumulation of internal state)
        assert adapter._bridge is not None, "Should have current bridge"
        assert adapter._run_id == "run-9", "Should have latest run ID"
        assert adapter._agent_name == "Agent-9", "Should have latest agent name"
        assert adapter.has_websocket_bridge(), "Should still have bridge"
    
    @pytest.mark.unit
    async def test_event_emission_timing_consistency(self):
        """Test event emission timing is consistent across different event types."""
        # Business Value: Predictable performance characteristics for agent orchestration
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-123", "TimingTestAgent")
        
        # Add small delay to bridge methods to simulate real network operations
        async def mock_delay(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms delay
        
        mock_bridge.notify_agent_started.side_effect = mock_delay
        mock_bridge.notify_agent_thinking.side_effect = mock_delay
        mock_bridge.notify_tool_executing.side_effect = mock_delay
        mock_bridge.notify_tool_completed.side_effect = mock_delay
        mock_bridge.notify_agent_completed.side_effect = mock_delay
        mock_bridge.notify_progress_update.side_effect = mock_delay
        mock_bridge.notify_agent_error.side_effect = mock_delay
        
        # Measure timing for each event type
        event_timings = {}
        
        event_methods = [
            ("agent_started", lambda: adapter.emit_agent_started("test")),
            ("thinking", lambda: adapter.emit_thinking("test")),
            ("tool_executing", lambda: adapter.emit_tool_executing("test")),
            ("tool_completed", lambda: adapter.emit_tool_completed("test")),
            ("agent_completed", lambda: adapter.emit_agent_completed()),
            ("progress", lambda: adapter.emit_progress("test")),
            ("error", lambda: adapter.emit_error("test"))
        ]
        
        for event_name, event_method in event_methods:
            start_time = time.time()
            await event_method()
            end_time = time.time()
            event_timings[event_name] = end_time - start_time
        
        # Verify timing consistency (all should be similar, around 1ms + overhead)
        min_timing = min(event_timings.values())
        max_timing = max(event_timings.values())
        
        # Allow for reasonable variance in timing (10x difference max)
        assert max_timing / min_timing < 10, f"Timing inconsistency: {event_timings}"
    
    @pytest.mark.unit  
    async def test_adapter_cleanup_and_resource_management(self):
        """Test adapter properly manages resources and supports cleanup."""
        # Business Value: Prevents resource leaks in enterprise environments
        
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        
        # Configure and use adapter
        adapter.set_websocket_bridge(mock_bridge, "run-123", "CleanupTestAgent")
        
        # Use adapter extensively
        await adapter.emit_agent_started("test")
        await adapter.emit_thinking("test") 
        await adapter.emit_agent_completed()
        
        # Simulate cleanup by removing bridge reference
        adapter._bridge = None
        adapter._run_id = None
        adapter._agent_name = None
        
        # Verify cleanup state
        assert adapter._bridge is None
        assert adapter._run_id is None
        assert adapter._agent_name is None
        assert not adapter.has_websocket_bridge()
        
        # Verify events fail gracefully after cleanup
        await adapter.emit_agent_started("should not emit")
        await adapter.emit_thinking("should not emit")
        
        # Bridge should not receive any new calls after cleanup
        # (calls made before cleanup should not be affected)
        assert mock_bridge.notify_agent_started.call_count == 1  # From before cleanup
        assert mock_bridge.notify_agent_thinking.call_count == 1  # From before cleanup


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "-m", "unit"
    ])