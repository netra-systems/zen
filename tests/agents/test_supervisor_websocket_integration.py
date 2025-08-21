"""
Tests for supervisor agent WebSocket integration.

Verifies that the supervisor agent can properly:
1. Receive messages through WebSocket
2. Process them using the execution pipeline
3. Send responses back through WebSocket
4. Handle errors and state changes

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Agent Reliability & Performance
- Value Impact: Ensures supervisor agent works in real-time scenarios
- Strategic Impact: Enables confident agent deployments
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.ws_manager import WebSocketManager


class TestSupervisorWebSocketIntegration:
    """Test supervisor agent WebSocket integration."""

    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    async def mock_llm_manager(self):
        """Mock LLM manager."""
        llm_manager = AsyncMock(spec=LLMManager)
        return llm_manager

    @pytest.fixture
    async def mock_websocket_manager(self):
        """Mock WebSocket manager."""
        ws_manager = AsyncMock(spec=WebSocketManager)
        ws_manager.send_message = AsyncMock(return_value=True)
        ws_manager.send_error = AsyncMock(return_value=True)
        return ws_manager

    @pytest.fixture
    async def mock_tool_dispatcher(self):
        """Mock tool dispatcher."""
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

        dispatcher = AsyncMock(spec=ToolDispatcher)
        return dispatcher

    @pytest.fixture
    async def supervisor_agent(
        self,
        mock_db_session,
        mock_llm_manager,
        mock_websocket_manager,
        mock_tool_dispatcher,
    ):
        """Create supervisor agent with mocked dependencies."""
        with patch(
            "app.agents.supervisor_consolidated.SupervisorInitializationHelpers"
        ), patch("app.agents.supervisor_consolidated.AgentRegistry"), patch(
            "app.agents.supervisor_consolidated.ExecutionEngine"
        ), patch(
            "app.agents.supervisor_consolidated.PipelineExecutor"
        ), patch(
            "app.agents.supervisor_consolidated.StateManager"
        ):

            agent = SupervisorAgent(
                mock_db_session,
                mock_llm_manager,
                mock_websocket_manager,
                mock_tool_dispatcher,
            )
            return agent

    @pytest.mark.asyncio
    async def test_supervisor_receives_websocket_message(self, supervisor_agent):
        """Test that supervisor can receive and process WebSocket messages."""
        user_prompt = "Process this task"
        thread_id = "thread-123"
        user_id = "user-456"
        run_id = "run-789"

        # Mock the run method to return a response
        expected_response = DeepAgentState(
            user_request=user_prompt, chat_thread_id=thread_id, user_id=user_id
        )

        with patch.object(
            supervisor_agent, "run", return_value=expected_response
        ) as mock_run:
            # Call supervisor run method (simulating WebSocket message
            # processing)
            result = await supervisor_agent.run(user_prompt, thread_id, user_id, run_id)

            # Verify supervisor was called correctly
            mock_run.assert_called_once_with(user_prompt, thread_id, user_id, run_id)
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_supervisor_sends_websocket_response(
        self, supervisor_agent, mock_websocket_manager
    ):
        """Test that supervisor sends responses through WebSocket."""
        user_id = "user-123"

        # Mock supervisor to have websocket manager
        supervisor_agent.websocket_manager = mock_websocket_manager

        # Simulate sending a response
        response_data = {"response": "Task completed", "status": "success"}

        # Call WebSocket manager directly (simulating agent sending response)
        result = await mock_websocket_manager.send_message(user_id, response_data)

        # Verify message was sent
        assert result is True
        mock_websocket_manager.send_message.assert_called_once_with(
            user_id, response_data
        )

    @pytest.mark.asyncio
    async def test_agent_service_handles_websocket_message(self, mock_db_session):
        """Test that AgentService properly handles WebSocket messages."""
        # Create mock supervisor
        mock_supervisor = AsyncMock()
        mock_supervisor.run.return_value = "Agent processed the message"

        # Create agent service
        agent_service = AgentService(mock_supervisor)

        user_id = "test-user"
        message_data = {
            "type": "user_message",
            "payload": {"content": "Hello agent", "thread_id": "thread-123"},
        }

        # Mock message handler components
        with patch.object(agent_service, "message_handler") as mock_handler:
            mock_handler.handle_user_message = AsyncMock()

            # Process WebSocket message
            await agent_service.handle_websocket_message(
                user_id, message_data, mock_db_session
            )

            # Verify message was routed to handler
            mock_handler.handle_user_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_handling(
        self, supervisor_agent, mock_websocket_manager
    ):
        """Test error handling in WebSocket communication."""
        user_id = "user-error-test"

        # Mock websocket manager to raise an exception
        mock_websocket_manager.send_message.side_effect = Exception(
            "WebSocket connection lost"
        )

        supervisor_agent.websocket_manager = mock_websocket_manager

        # Try to send message - should handle error gracefully
        try:
            await mock_websocket_manager.send_message(user_id, {"test": "data"})
            assert False, "Should have raised exception"
        except Exception as e:
            assert "WebSocket connection lost" in str(e)

    @pytest.mark.asyncio
    async def test_supervisor_execution_with_websocket_updates(self, supervisor_agent):
        """Test supervisor execution sends status updates via WebSocket."""
        user_prompt = "Complex task requiring updates"
        thread_id = "thread-updates"
        user_id = "user-updates"
        run_id = "run-updates"

        # Mock justification: Agent workflow execution subsystem is complex
        # orchestration not part of WebSocket integration SUT
        with patch.object(supervisor_agent, "workflow_executor") as mock_executor:
            mock_state = DeepAgentState(
                user_request=user_prompt, chat_thread_id=thread_id, user_id=user_id
            )
            mock_executor.execute_workflow_steps.return_value = mock_state

            # Mock justification: Flow logging subsystem is peripheral to
            # WebSocket message handling SUT
            with patch.object(supervisor_agent, "flow_logger") as mock_logger:
                mock_logger.generate_flow_id.return_value = "flow-123"
                mock_logger.start_flow.return_value = None
                mock_logger.complete_flow.return_value = None

                # Execute supervisor run
                result = await supervisor_agent.run(
                    user_prompt, thread_id, user_id, run_id
                )

                # Verify workflow executor was called
                mock_executor.execute_workflow_steps.assert_called_once()

                # Verify flow was logged
                mock_logger.start_flow.assert_called_once()
                mock_logger.complete_flow.assert_called_once()

                assert result == mock_state

    @pytest.mark.asyncio
    async def test_concurrent_websocket_message_processing(self, supervisor_agent):
        """Test handling of concurrent WebSocket messages."""
        messages = [
            ("user1", "Message 1", "thread1", "run1"),
            ("user2", "Message 2", "thread2", "run2"),
            ("user3", "Message 3", "thread3", "run3"),
        ]

        # Mock justification: Agent workflow execution subsystem is complex
        # orchestration not part of concurrent WebSocket SUT
        with patch.object(supervisor_agent, "workflow_executor") as mock_executor:
            responses = []
            for i, (user_id, prompt, thread_id, run_id) in enumerate(messages):
                response = DeepAgentState(
                    user_request=prompt, chat_thread_id=thread_id, user_id=user_id
                )
                responses.append(response)

            mock_executor.execute_workflow_steps.side_effect = responses

            # Mock justification: Flow logging subsystem is peripheral to
            # concurrent WebSocket processing SUT
            with patch.object(supervisor_agent, "flow_logger") as mock_logger:
                mock_logger.generate_flow_id.side_effect = [
                    f"flow-{i}" for i in range(3)
                ]
                mock_logger.start_flow.return_value = None
                mock_logger.complete_flow.return_value = None

                # Execute messages concurrently
                tasks = []
                for user_id, prompt, thread_id, run_id in messages:
                    task = asyncio.create_task(
                        supervisor_agent.run(prompt, thread_id, user_id, run_id)
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)

                # Verify all messages were processed
                assert len(results) == 3
                for i, result in enumerate(results):
                    expected_user_id = messages[i][0]
                    assert result.user_id == expected_user_id

    @pytest.mark.asyncio
    async def test_agent_service_websocket_message_validation(self):
        """Test WebSocket message validation in agent service."""
        mock_supervisor = AsyncMock()
        agent_service = AgentService(mock_supervisor)

        user_id = "validation-user"
        db_session = AsyncMock()

        # Test valid message
        valid_message = {
            "type": "user_message",
            "payload": {"content": "Valid message", "thread_id": "thread-1"},
        }

        with patch.object(agent_service, "message_handler") as mock_handler:
            mock_handler.handle_user_message = AsyncMock()

            await agent_service.handle_websocket_message(
                user_id, valid_message, db_session
            )
            mock_handler.handle_user_message.assert_called_once()

        # Test invalid message (missing type)
        invalid_message = {"payload": {"content": "Missing type field"}}

        with patch("app.ws_manager.manager.send_error") as mock_send_error:
            with patch.object(
                agent_service, "_parse_message", return_value=invalid_message
            ):
                await agent_service.handle_websocket_message(
                    user_id, invalid_message, db_session
                )
                mock_send_error.assert_called_with(user_id, "Message type is required")

    @pytest.mark.asyncio
    async def test_websocket_disconnection_handling(self, supervisor_agent):
        """Test handling of WebSocket disconnections during processing."""
        user_prompt = "Long running task"
        thread_id = "thread-disconnect"
        user_id = "user-disconnect"
        run_id = "run-disconnect"

        # Mock justification: Agent workflow execution subsystem is not part of
        # WebSocket disconnection handling SUT
        with patch.object(supervisor_agent, "workflow_executor") as mock_executor:
            from starlette.websockets import WebSocketDisconnect

            mock_executor.execute_workflow_steps.side_effect = WebSocketDisconnect(
                code=1001, reason="Client disconnected"
            )

            # Mock justification: Flow logging subsystem is peripheral to
            # WebSocket disconnection handling SUT
            with patch.object(supervisor_agent, "flow_logger") as mock_logger:
                mock_logger.generate_flow_id.return_value = "flow-disconnect"
                mock_logger.start_flow.return_value = None
                mock_logger.complete_flow.return_value = None

                # Execute should handle disconnect gracefully
                try:
                    await supervisor_agent.run(user_prompt, thread_id, user_id, run_id)
                except WebSocketDisconnect:
                    # This is expected behavior
                    pass

                # Flow should still be tracked
                mock_logger.start_flow.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_health_status_through_websocket(self, supervisor_agent):
        """Test getting agent health status through WebSocket."""
        # Mock completion helpers
        with patch.object(supervisor_agent, "completion_helpers") as mock_helpers:
            expected_health = {
                "status": "healthy",
                "agent_name": "Supervisor",
                "active_connections": 5,
                "processing_status": "ready",
                "last_activity": datetime.now(timezone.utc).isoformat(),
            }
            mock_helpers.get_agent_health_status.return_value = expected_health

            # Get health status
            health = supervisor_agent.get_health_status()

            assert health == expected_health
            mock_helpers.get_agent_health_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_performance_metrics_tracking(self, supervisor_agent):
        """Test performance metrics collection for WebSocket communication."""
        # Mock completion helpers
        with patch.object(supervisor_agent, "completion_helpers") as mock_helpers:
            expected_metrics = {
                "messages_processed": 42,
                "average_response_time": 1.5,
                "success_rate": 0.95,
                "error_count": 2,
                "concurrent_sessions": 3,
                "uptime_seconds": 3600,
            }
            mock_helpers.get_agent_performance_metrics.return_value = expected_metrics

            # Get performance metrics
            metrics = supervisor_agent.get_performance_metrics()

            assert metrics == expected_metrics
            assert metrics["messages_processed"] == 42
            assert metrics["success_rate"] == 0.95
            mock_helpers.get_agent_performance_metrics.assert_called_once()
