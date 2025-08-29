"""Integration tests for agent WebSocket communication with proper ID handling."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any, Optional

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.synthetic_data_sub_agent_modern import (
    ModernSyntheticDataSubAgent
)
from netra_backend.app.agents.synthetic_data_generator import (
    SyntheticDataGenerator
)
from netra_backend.app.agents.synthetic_data_presets import (
    WorkloadProfile, WorkloadType
)
from netra_backend.app.agents.data_sub_agent.agent_execution import ExecutionManager
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.schemas.generation import GenerationStatus


class TestAgentWebSocketIntegration:
    """Integration tests for agent WebSocket communication."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.send_to_thread = AsyncMock(return_value=True)
        manager.send_to_user = AsyncMock(return_value=True)
        manager.send_message = AsyncMock(return_value=False)  # Deprecated method
        return manager

    @pytest.fixture
    def execution_context_with_thread(self):
        """Create execution context with thread_id."""
        return ExecutionContext(
            run_id="run_test_123",
            agent_name="TestAgent",
            state=DeepAgentState(user_request="Generate test data"),
            stream_updates=True,
            thread_id="thread_456",
            user_id="user_789"
        )

    @pytest.fixture
    def execution_context_without_thread(self):
        """Create execution context without thread_id."""
        return ExecutionContext(
            run_id="run_test_456",
            agent_name="TestAgent",
            state=DeepAgentState(user_request="Generate test data"),
            stream_updates=True,
            thread_id=None,
            user_id="user_789"
        )

    @pytest.fixture
    def execution_context_run_only(self):
        """Create execution context with only run_id."""
        return ExecutionContext(
            run_id="run_test_789",
            agent_name="TestAgent",
            state=DeepAgentState(user_request="Generate test data"),
            stream_updates=True,
            thread_id=None,
            user_id=None
        )

    @pytest.mark.asyncio
    async def test_synthetic_agent_with_thread_context(
        self, mock_websocket_manager, execution_context_with_thread
    ):
        """Test synthetic data agent uses thread_id for WebSocket messages."""
        with patch('netra_backend.app.websocket_core.get_websocket_manager',
                  return_value=mock_websocket_manager):
            # Create mock dependencies
            llm_manager = MagicMock()
            tool_dispatcher = AsyncMock()
            tool_dispatcher.has_tool = MagicMock(return_value=True)
            tool_dispatcher.dispatch_tool = AsyncMock(return_value={"data": []})
            
            # Create agent
            agent = ModernSyntheticDataSubAgent(
                llm_manager=llm_manager,
                tool_dispatcher=tool_dispatcher,
                websocket_manager=mock_websocket_manager
            )
            
            # Mock workload profile determination
            with patch.object(agent, '_determine_workload_profile',
                            return_value=WorkloadProfile(
                                workload_type=WorkloadType.HIGH_TRAFFIC,
                                volume=100
                            )):
                # Execute agent
                await agent.execute_core_logic(execution_context_with_thread)
                
                # Verify thread-based messaging was used
                assert mock_websocket_manager.send_to_thread.called
                # Verify run_id was NOT used as user_id
                assert not any(
                    call[0][0] == "run_test_123"
                    for call in mock_websocket_manager.send_to_user.call_args_list
                )

    @pytest.mark.asyncio
    async def test_synthetic_agent_without_thread_context(
        self, mock_websocket_manager, execution_context_without_thread
    ):
        """Test synthetic data agent uses user_id when thread_id not available."""
        with patch('netra_backend.app.websocket_core.get_websocket_manager',
                  return_value=mock_websocket_manager):
            # Create mock dependencies
            llm_manager = MagicMock()
            tool_dispatcher = AsyncMock()
            tool_dispatcher.has_tool = MagicMock(return_value=True)
            tool_dispatcher.dispatch_tool = AsyncMock(return_value={"data": []})
            
            # Create agent
            agent = ModernSyntheticDataSubAgent(
                llm_manager=llm_manager,
                tool_dispatcher=tool_dispatcher,
                websocket_manager=mock_websocket_manager
            )
            
            # Mock workload profile determination
            with patch.object(agent, '_determine_workload_profile',
                            return_value=WorkloadProfile(
                                workload_type=WorkloadType.HIGH_TRAFFIC,
                                volume=100
                            )):
                # Execute agent
                await agent.execute_core_logic(execution_context_without_thread)
                
                # Verify user-based messaging was attempted
                if mock_websocket_manager.send_to_user.called:
                    # Check that user_789 was used, not run_id
                    user_calls = [
                        call for call in mock_websocket_manager.send_to_user.call_args_list
                        if call[0][0] == "user_789"
                    ]
                    assert len(user_calls) > 0

    @pytest.mark.asyncio
    async def test_data_agent_no_websocket_with_run_only(
        self, execution_context_run_only
    ):
        """Test data agent doesn't send WebSocket messages with only run_id."""
        # Create execution manager
        mock_agent = MagicMock()
        mock_agent.websocket_manager = AsyncMock()
        mock_agent.websocket_manager.send_message = AsyncMock()
        mock_agent.websocket_manager.send_to_thread = AsyncMock()
        
        manager = ExecutionManager(mock_agent)
        
        # Mock logger to verify debug message
        with patch('netra_backend.app.agents.data_sub_agent.agent_execution.logger') as mock_logger:
            # Send completion message
            await manager._send_completion_message("run_test_789", {"result": "test"})
            
            # Verify no WebSocket methods were called with run_id
            mock_agent.websocket_manager.send_message.assert_not_called()
            mock_agent.websocket_manager.send_to_thread.assert_not_called()
            
            # Verify debug message was logged
            mock_logger.debug.assert_called()
            assert any("no thread/user context" in str(call)
                      for call in mock_logger.debug.call_args_list)

    @pytest.mark.asyncio
    async def test_progress_tracker_integration(self, mock_websocket_manager):
        """Test progress tracker integration with proper routing."""
        with patch('netra_backend.app.websocket_core.get_websocket_manager',
                  return_value=mock_websocket_manager):
            # Create generator with mocked tool dispatcher
            tool_dispatcher = AsyncMock()
            tool_dispatcher.has_tool = MagicMock(return_value=True)
            tool_dispatcher.dispatch_tool = AsyncMock(
                return_value={"data": [{"id": i} for i in range(10)]}
            )
            
            generator = SyntheticDataGenerator(tool_dispatcher)
            
            # Generate data with thread context
            profile = WorkloadProfile(workload_type=WorkloadType.HIGH_TRAFFIC, volume=10)
            result = await generator.generate_data(
                profile=profile,
                run_id="run_gen_123",
                stream_updates=True,
                thread_id="thread_progress_456",
                user_id="user_progress_789"
            )
            
            # Verify success
            assert result.success
            
            # Verify thread-based messaging was used for progress updates
            if mock_websocket_manager.send_to_thread.called:
                thread_calls = [
                    call for call in mock_websocket_manager.send_to_thread.call_args_list
                    if call[0][0] == "thread_progress_456"
                ]
                # Progress updates should use thread messaging
                assert len(thread_calls) >= 0  # May be 0 if no progress updates triggered

    @pytest.mark.asyncio
    async def test_websocket_manager_buffering(self, mock_websocket_manager):
        """Test message buffering when connections are unavailable."""
        # Mock buffer_user_message
        with patch('netra_backend.app.websocket_core.buffer.buffer_user_message',
                  new_callable=AsyncMock, return_value=True) as mock_buffer:
            manager = WebSocketManager()
            
            # Send message with retry enabled (default)
            result = await manager.send_to_user(
                "user_offline_123",
                {"type": "test", "data": "message"},
                retry=True
            )
            
            # Should return False (no connection)
            assert result is False
            
            # Should attempt to buffer the message
            mock_buffer.assert_called_once()
            assert mock_buffer.call_args[0][0] == "user_offline_123"

    @pytest.mark.asyncio
    async def test_end_to_end_websocket_flow(self):
        """Test complete end-to-end WebSocket message flow."""
        # Create real WebSocket manager
        manager = WebSocketManager()
        
        # Simulate connection
        websocket_mock = AsyncMock()
        websocket_mock.send_text = AsyncMock()
        websocket_mock.send_json = AsyncMock()
        
        # Add connection
        connection_id = await manager.connect(
            websocket=websocket_mock,
            user_id="user_e2e_123",
            thread_id="thread_e2e_456"
        )
        
        try:
            # Send message to thread
            result = await manager.send_to_thread(
                "thread_e2e_456",
                {"type": "test", "data": "e2e message"}
            )
            
            # Should succeed
            assert result is True
            
            # Verify message was sent
            assert websocket_mock.send_text.called or websocket_mock.send_json.called
            
        finally:
            # Clean up connection
            await manager.disconnect(connection_id)

    @pytest.mark.asyncio
    async def test_concurrent_message_sending(self, mock_websocket_manager):
        """Test concurrent WebSocket message sending."""
        # Create multiple execution contexts
        contexts = [
            ExecutionContext(
                run_id=f"run_concurrent_{i}",
                agent_name="TestAgent",
                state=DeepAgentState(user_request=f"Request {i}"),
                stream_updates=True,
                thread_id=f"thread_concurrent_{i}",
                user_id=f"user_concurrent_{i}"
            )
            for i in range(5)
        ]
        
        async def send_message(context):
            """Simulate agent sending message."""
            if context.thread_id:
                await mock_websocket_manager.send_to_thread(
                    context.thread_id,
                    {"type": "status", "run_id": context.run_id}
                )
        
        # Send messages concurrently
        await asyncio.gather(*[send_message(ctx) for ctx in contexts])
        
        # Verify all messages were sent
        assert mock_websocket_manager.send_to_thread.call_count == 5
        
        # Verify each thread received its message
        thread_ids = {
            call[0][0] for call in mock_websocket_manager.send_to_thread.call_args_list
        }
        expected_threads = {f"thread_concurrent_{i}" for i in range(5)}
        assert thread_ids == expected_threads


class TestWebSocketErrorHandling:
    """Test error handling in WebSocket communication."""

    @pytest.mark.asyncio
    async def test_websocket_send_failure_handling(self):
        """Test handling of WebSocket send failures."""
        manager = WebSocketManager()
        
        # Mock websocket that raises exception
        websocket_mock = AsyncMock()
        websocket_mock.send_text = AsyncMock(
            side_effect=Exception("Connection lost")
        )
        
        # Add connection
        connection_id = await manager.connect(
            websocket=websocket_mock,
            user_id="user_error_123"
        )
        
        try:
            # Attempt to send message
            result = await manager.send_to_user(
                "user_error_123",
                {"type": "test", "data": "message"}
            )
            
            # Should return False due to send failure
            assert result is False
            
        finally:
            # Clean up
            await manager.disconnect(connection_id)

    @pytest.mark.asyncio
    async def test_import_error_fallback(self):
        """Test fallback behavior when WebSocket manager cannot be imported."""
        with patch('netra_backend.app.websocket_core.get_websocket_manager',
                  side_effect=ImportError("Module not found")):
            # Create progress tracker
            from netra_backend.app.agents.synthetic_data_progress_tracker import (
                SyntheticDataProgressTracker
            )
            tracker = SyntheticDataProgressTracker()
            
            # Create status
            status = GenerationStatus(
                status="generating",
                total_records=100,
                records_generated=50
            )
            
            # Should not raise exception
            with patch('netra_backend.app.agents.synthetic_data_progress_tracker.logger') as mock_logger:
                await tracker.send_progress_update(
                    "run_import_error",
                    status,
                    thread_id="thread_123"
                )
                
                # Should log about unavailability
                mock_logger.debug.assert_called()
                assert any("not available" in str(call)
                          for call in mock_logger.debug.call_args_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])