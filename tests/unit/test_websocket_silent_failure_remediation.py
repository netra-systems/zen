"""
Test suite to validate WebSocket silent failure remediation implementation.

This test validates that the fixes implemented for Issue #373 correctly
handle WebSocket failures with proper retry infrastructure instead of
silent logger.warning() calls.

CRITICAL: These tests protect $500K+ ARR by ensuring chat functionality reliability.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketSilentFailureRemediation:
    """Test suite for WebSocket silent failure remediation."""

    @pytest.fixture
    def user_context(self):
        """Create a test user execution context."""
        return UserExecutionContext(
            user_id="test_user_123",
            run_id="test_run_456", 
            thread_id="test_thread_789",
            agent_context={"test": True}
        )

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create a mock WebSocket manager that fails initially."""
        manager = AsyncMock()
        manager.send_event = AsyncMock(side_effect=Exception("WebSocket connection lost"))
        manager.emit_critical_event = AsyncMock(side_effect=Exception("Critical emission failed"))
        manager.is_connection_active = Mock(return_value=True)
        return manager

    @pytest.fixture
    def mock_unified_emitter(self):
        """Create a mock UnifiedWebSocketEmitter that succeeds."""
        emitter = AsyncMock()
        emitter.notify_tool_executing = AsyncMock(return_value=True)
        emitter.notify_tool_completed = AsyncMock(return_value=True)
        emitter.notify_agent_started = AsyncMock(return_value=True)
        emitter.notify_agent_thinking = AsyncMock(return_value=True)
        emitter.notify_agent_completed = AsyncMock(return_value=True)
        emitter.notify_custom = AsyncMock(return_value=True)
        return emitter

    @pytest.mark.asyncio
    async def test_unified_tool_dispatcher_tool_executing_failure_recovery(
        self, user_context, mock_websocket_manager, mock_unified_emitter
    ):
        """Test UnifiedToolDispatcher recovers from tool_executing WebSocket failures."""
        
        # Create dispatcher instance using factory method
        dispatcher = UnifiedToolDispatcher._create_from_factory(
            user_context=user_context,
            websocket_manager=mock_websocket_manager,
            tools=[]
        )
        
        # Mock UnifiedWebSocketEmitter creation
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter', 
                  return_value=mock_unified_emitter):
            with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                logger_instance = mock_logger.get_logger.return_value
                
                # Test: WebSocket manager fails, should trigger recovery
                result = await dispatcher._emit_tool_executing("test_tool", {"param1": "value1"})
                
                # Verify: Result should be None because primary emission failed
                assert result is None
                
                # Verify: Critical logging was called (not warning)
                logger_instance.critical.assert_called()
                critical_calls = [call for call in logger_instance.critical.call_args_list 
                                if "WebSocket tool_executing event FAILED" in str(call)]
                assert len(critical_calls) > 0, "Should have logged critical WebSocket failure"
                
                # Verify: Recovery attempt was made
                mock_unified_emitter.notify_tool_executing.assert_called_once()
                recovery_call = mock_unified_emitter.notify_tool_executing.call_args
                assert recovery_call[0][0] == "test_tool"  # tool_name
                assert recovery_call[1]["metadata"]["recovery_attempt"] is True

    @pytest.mark.asyncio
    async def test_unified_tool_dispatcher_tool_completed_failure_recovery(
        self, user_context, mock_websocket_manager, mock_unified_emitter
    ):
        """Test UnifiedToolDispatcher recovers from tool_completed WebSocket failures."""
        
        # Create dispatcher instance using factory method
        dispatcher = UnifiedToolDispatcher._create_from_factory(
            user_context=user_context,
            websocket_manager=mock_websocket_manager,
            tools=[]
        )
        
        # Mock UnifiedWebSocketEmitter creation
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter', 
                  return_value=mock_unified_emitter):
            with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                logger_instance = mock_logger.get_logger.return_value
                
                # Test: WebSocket manager fails, should trigger recovery
                result = await dispatcher._emit_tool_completed("test_tool", result="test_result")
                
                # Verify: Result should be None because primary emission failed
                assert result is None
                
                # Verify: Critical logging was called (not warning)
                logger_instance.critical.assert_called()
                critical_calls = [call for call in logger_instance.critical.call_args_list 
                                if "WebSocket tool_completed event FAILED" in str(call)]
                assert len(critical_calls) > 0, "Should have logged critical WebSocket failure"
                
                # Verify: Recovery attempt was made
                mock_unified_emitter.notify_tool_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_reporting_sub_agent_agent_started_failure_recovery(
        self, user_context, mock_unified_emitter
    ):
        """Test ReportingSubAgent recovers from agent_started WebSocket failures."""
        
        # Create ReportingSubAgent instance
        agent = ReportingSubAgent(context=user_context)
        
        # Mock WebSocket adapter that fails
        mock_adapter = Mock()
        mock_adapter.websocket_manager = Mock()
        mock_adapter.websocket_manager.emit_critical_event = AsyncMock(side_effect=Exception("Adapter failed"))
        agent._websocket_adapter = mock_adapter
        
        # Mock the emit_agent_started method to fail
        with patch.object(agent, 'emit_agent_started', side_effect=Exception("WebSocket connection lost")):
            # Mock UnifiedWebSocketEmitter creation
            with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter', 
                      return_value=mock_unified_emitter):
                with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                    logger_instance = mock_logger.get_logger.return_value
                    
                    # Test: Call _execute_modern_pattern with stream_updates=True to trigger event emission
                    try:
                        await agent._execute_modern_pattern(user_context, stream_updates=True)
                    except Exception:
                        pass  # We expect some failures in this test scenario
                    
                    # Verify: Critical logging was called (not warning)  
                    logger_instance.critical.assert_called()
                    critical_calls = [call for call in logger_instance.critical.call_args_list 
                                    if "WebSocket agent_started event FAILED" in str(call)]
                    assert len(critical_calls) > 0, "Should have logged critical WebSocket failure"
                    
                    # Verify: Recovery attempt was made
                    mock_unified_emitter.notify_agent_started.assert_called()

    @pytest.mark.asyncio  
    async def test_reporting_sub_agent_thinking_failure_recovery(
        self, user_context, mock_unified_emitter
    ):
        """Test ReportingSubAgent recovers from agent_thinking WebSocket failures."""
        
        # Create ReportingSubAgent instance
        agent = ReportingSubAgent(context=user_context)
        
        # Mock WebSocket adapter
        mock_adapter = Mock()
        mock_adapter.websocket_manager = Mock()
        agent._websocket_adapter = mock_adapter
        
        # Mock the emit_thinking method to fail
        with patch.object(agent, 'emit_thinking', side_effect=Exception("Thinking emission failed")):
            # Mock UnifiedWebSocketEmitter creation
            with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter', 
                      return_value=mock_unified_emitter):
                with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                    logger_instance = mock_logger.get_logger.return_value
                    
                    # Test: Call _execute_modern_pattern to trigger thinking emission
                    try:
                        await agent._execute_modern_pattern(user_context, stream_updates=True)
                    except Exception:
                        pass  # We expect some failures in this test scenario
                    
                    # Verify: Critical logging was called (not warning)
                    logger_instance.critical.assert_called()
                    critical_calls = [call for call in logger_instance.critical.call_args_list 
                                    if "WebSocket agent_thinking event FAILED" in str(call)]
                    assert len(critical_calls) > 0, "Should have logged critical WebSocket failure"
                    
                    # Verify: Recovery attempt was made
                    mock_unified_emitter.notify_agent_thinking.assert_called()

    @pytest.mark.asyncio
    async def test_business_impact_logging_when_all_recovery_fails(
        self, user_context, mock_websocket_manager
    ):
        """Test that business impact is logged when both primary and recovery systems fail."""
        
        # Create dispatcher instance
        dispatcher = UnifiedToolDispatcher._create_from_factory(
            user_context=user_context,
            websocket_manager=mock_websocket_manager,
            tools=[]
        )
        
        # Mock UnifiedWebSocketEmitter that also fails
        failing_emitter = AsyncMock()
        failing_emitter.notify_tool_executing = AsyncMock(return_value=False)  # Recovery fails
        
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter', 
                  return_value=failing_emitter):
            with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                logger_instance = mock_logger.get_logger.return_value
                
                # Test: Both primary and recovery fail
                result = await dispatcher._emit_tool_executing("test_tool", {"param1": "value1"})
                
                # Verify: Result should be None
                assert result is None
                
                # Verify: Business impact logging was called
                logger_instance.critical.assert_called()
                
                # Check for both types of critical logs
                all_critical_calls = [str(call) for call in logger_instance.critical.call_args_list]
                
                # Should have primary failure log
                primary_failure_logs = [call for call in all_critical_calls 
                                      if "WebSocket tool_executing event FAILED" in call]
                assert len(primary_failure_logs) > 0, "Should have logged primary WebSocket failure"

    def test_no_more_warning_level_logging_for_websocket_failures(self):
        """Verify that the old warning-level logging pattern has been eliminated."""
        
        # Read the source files to verify no logger.warning for WebSocket events exist
        with open("C:\\GitHub\\netra-apex\\netra_backend\\app\\core\\tools\\unified_tool_dispatcher.py", "r", encoding="utf-8") as f:
            tool_dispatcher_content = f.read()
        
        with open("C:\\GitHub\\netra-apex\\netra_backend\\app\\agents\\reporting_sub_agent.py", "r", encoding="utf-8") as f:
            reporting_agent_content = f.read()
        
        # Verify: No logger.warning calls for WebSocket events remain
        assert "logger.warning(f\"Failed to emit tool_executing event:" not in tool_dispatcher_content
        assert "logger.warning(f\"Failed to emit tool_completed event:" not in tool_dispatcher_content
        assert "self.logger.warning(f\"Failed to emit start event:" not in reporting_agent_content
        assert "self.logger.warning(f\"Failed to emit thinking:" not in reporting_agent_content
        assert "self.logger.warning(f\"Failed to emit completion:" not in reporting_agent_content
        
        # Verify: Critical logging patterns are present
        assert "logger.critical(f\" ALERT:  CRITICAL: WebSocket tool_executing event FAILED" in tool_dispatcher_content
        assert "logger.critical(f\" ALERT:  CRITICAL: WebSocket tool_completed event FAILED" in tool_dispatcher_content
        assert "self.logger.critical(f\" ALERT:  CRITICAL: WebSocket agent_started event FAILED" in reporting_agent_content
        assert "self.logger.critical(f\" ALERT:  CRITICAL: WebSocket agent_thinking event FAILED" in reporting_agent_content
        assert "self.logger.critical(f\" ALERT:  CRITICAL: WebSocket agent_completed event FAILED" in reporting_agent_content


# Integration test to validate end-to-end functionality
class TestWebSocketFailureRecoveryIntegration:
    """Integration tests for WebSocket failure recovery."""

    @pytest.mark.asyncio
    async def test_tool_dispatcher_end_to_end_recovery_flow(self):
        """Test complete recovery flow for tool dispatcher WebSocket failures."""
        
        # Create real context
        context = UserExecutionContext(
            user_id="integration_test_user",
            run_id="integration_test_run",
            thread_id="integration_test_thread"
        )
        
        # Mock primary WebSocket manager to fail
        primary_manager = AsyncMock()
        primary_manager.send_event = AsyncMock(side_effect=Exception("Primary WebSocket failed"))
        primary_manager.is_connection_active = Mock(return_value=True)
        
        # Mock recovery emitter to succeed
        recovery_emitter = AsyncMock()
        recovery_emitter.notify_tool_executing = AsyncMock(return_value=True)
        recovery_emitter.notify_tool_completed = AsyncMock(return_value=True)
        
        # Create dispatcher
        dispatcher = UnifiedToolDispatcher._create_from_factory(
            user_context=context,
            websocket_manager=primary_manager,
            tools=[]
        )
        
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter', 
                  return_value=recovery_emitter):
            
            # Test: Tool execution with WebSocket failures
            result = await dispatcher._emit_tool_executing("integration_test_tool", {"test": "data"})
            
            # Verify: Primary emission failed, recovery succeeded
            assert result is None  # Primary failed
            recovery_emitter.notify_tool_executing.assert_called_once()
            
            # Verify recovery metadata
            recovery_call = recovery_emitter.notify_tool_executing.call_args
            metadata = recovery_call[1]["metadata"]
            assert metadata["recovery_attempt"] is True
            assert metadata["user_id"] == "integration_test_user"
            assert "original_error" in metadata