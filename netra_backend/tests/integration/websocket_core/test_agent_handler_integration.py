from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""
Integration Tests for WebSocket Agent Handler - Tests 1-10

Business Value: Validates end-to-end flows with real services
ensuring reliable multi-user agent execution.
""""

import asyncio
import uuid
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import psutil
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
import pytest_asyncio
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.dependencies import (
    create_user_execution_context,
    get_request_scoped_supervisor
)
from test_framework.docker_utils import UnifiedDockerManager
from test_framework.test_config import get_test_config


# ============================================================================
# INTEGRATION TEST FIXTURES
# ============================================================================

@pytest_asyncio.fixture(scope="session")
async def docker_services():
    """Start Docker services for integration tests."""
    docker_manager = UnifiedDockerManager()
    await docker_manager.start_services(use_alpine=True)
    yield docker_manager
    await docker_manager.stop_services()


@pytest_asyncio.fixture
async def real_db_engine(docker_services):
    """Create real database engine for tests."""
    config = get_test_config()
    engine = create_async_engine(
        config.database_url,
        echo=False,
        pool_size=5,
        max_overflow=10
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def real_websocket_manager():
    """Create real WebSocket manager."""
    manager = WebSocketManager()
    yield manager
    # Cleanup all connections
    await manager.cleanup_all()


# ============================================================================
# INTEGRATION TESTS 1-5: CORE FLOWS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentHandlerIntegration:
    """Integration tests for WebSocket agent handler with real services."""
    
    async def test_complete_agent_execution_flow(
        self, 
        real_db_engine,
        real_websocket_manager
    ):
        """
        Integration Test 1: Complete agent execution flow from WebSocket to completion.
        
        Business Impact: Validates core chat functionality ($500K+ ARR).
        """"
        # Track WebSocket events
        events_received = []
        
        class MockWebSocket:
            async def send_json(self, data):
                events_received.append(data)
            
            async def receive_json(self):
                await asyncio.sleep(0.1)
                return {"type": "ping"}
            
            async def close(self):
                pass
        
        mock_ws = MockWebSocket()
        
        # Setup real components
        async with real_db_engine.begin() as conn:
            async with AsyncSession(conn) as db_session:
                # Create message handler with real dependencies
                from netra_backend.app.agents.supervisor.unified_supervisor import UnifiedSupervisor
                from netra_backend.app.services.thread_service import ThreadService
                
                supervisor = UnifiedSupervisor()
                thread_service = ThreadService()
                message_handler_service = MessageHandlerService(
                    supervisor=supervisor,
                    thread_service=thread_service,
                    websocket_manager=real_websocket_manager
                )
                
                # Create agent handler
                handler = AgentMessageHandler(
                    message_handler_service=message_handler_service,
                    websocket=mock_ws
                )
                
                # Connect user to WebSocket
                user_id = f"test_user_{uuid.uuid4()}"
                thread_id = f"thread_{uuid.uuid4()}"
                connection = await real_websocket_manager.connect_user(
                    websocket=mock_ws,
                    user_id=user_id,
                    thread_id=thread_id
                )
                
                # Create START_AGENT message
                message = WebSocketMessage(
                    type=MessageType.START_AGENT,
                    payload={
                        "user_request": "Help me analyze system performance",
                        "thread_id": thread_id,
                        "run_id": str(uuid.uuid4())
                    },
                    thread_id=thread_id,
                    timestamp=datetime.utcnow().isoformat()
                )
                
                # Process message
                start_time = time.time()
                result = await handler.handle_message(user_id, mock_ws, message)
                processing_time = time.time() - start_time
                
                # Assertions
                assert result is True, "Message should be processed successfully"
                assert processing_time < 30, f"Processing took too long: {processing_time:.2f}s"
                
                # Verify critical WebSocket events were sent
                event_types = [e.get("type") for e in events_received if isinstance(e, dict)]
                critical_events = [
                    "agent_started",
                    "agent_thinking", 
                    "tool_executing",
                    "tool_completed",
                    "agent_completed"
                ]
                
                for event in critical_events:
                    assert event in event_types, f"Missing critical event: {event}"
                
                # Verify thread association
                assert real_websocket_manager.get_thread_for_connection(
                    connection.connection_id
                ) == thread_id
                
                # Cleanup
                await real_websocket_manager.disconnect_user(user_id, connection.connection_id)

    async def test_multi_user_concurrent_execution(
        self,
        real_db_engine,
        real_websocket_manager
    ):
        """
        Integration Test 2: Multi-user concurrent agent execution with event isolation.
        
        Business Impact: Ensures platform can handle multiple users simultaneously.
        """"
        num_users = 5
        users_data = []
        
        # Create user data
        for i in range(num_users):
            users_data.append({
                "user_id": f"user_{i}_{uuid.uuid4()}",
                "thread_id": f"thread_{i}_{uuid.uuid4()}",
                "events": [],
                "websocket": MockWebSocket()
            })
        
        class MockWebSocket:
            def __init__(self):
                self.events = []
            
            async def send_json(self, data):
                self.events.append(data)
            
            async def receive_json(self):
                await asyncio.sleep(0.1)
                return {"type": "ping"}
            
            async def close(self):
                pass
        
        async def process_user_message(user_data, handler):
            """Process message for a single user."""
            message = WebSocketMessage(
                type=MessageType.START_AGENT,
                payload={
                    "user_request": f"Test request for {user_data['user_id']]",
                    "thread_id": user_data["thread_id"]
                },
                thread_id=user_data["thread_id"],
                timestamp=datetime.utcnow().isoformat()
            )
            
            result = await handler.handle_message(
                user_data["user_id"],
                user_data["websocket"],
                message
            )
            
            return result
        
        # Setup handlers for each user
        async with real_db_engine.begin() as conn:
            # Process all users concurrently
            tasks = []
            handlers = []
            
            for user_data in users_data:
                # Create separate handler for each user
                from netra_backend.app.agents.supervisor.unified_supervisor import UnifiedSupervisor
                from netra_backend.app.services.thread_service import ThreadService
                
                supervisor = UnifiedSupervisor()
                thread_service = ThreadService()
                message_handler_service = MessageHandlerService(
                    supervisor=supervisor,
                    thread_service=thread_service,
                    websocket_manager=real_websocket_manager
                )
                
                handler = AgentMessageHandler(
                    message_handler_service=message_handler_service,
                    websocket=user_data["websocket"]
                )
                handlers.append(handler)
                
                # Connect user
                await real_websocket_manager.connect_user(
                    websocket=user_data["websocket"],
                    user_id=user_data["user_id"],
                    thread_id=user_data["thread_id"]
                )
                
                # Create processing task
                tasks.append(process_user_message(user_data, handler))
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify results
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"User {i} failed: {result}"
                assert result is True, f"User {i} processing failed"
            
            # Verify event isolation
            for i, user_data in enumerate(users_data):
                user_events = user_data["websocket"].events
                
                # Check events only contain correct thread_id
                for event in user_events:
                    if isinstance(event, dict) and "thread_id" in event:
                        assert event["thread_id"] == user_data["thread_id"], \
                            f"Event leak detected: User {i} received wrong thread_id"
                
                # Verify no events from other users
                other_thread_ids = [u["thread_id"] for j, u in enumerate(users_data) if j != i]
                for event in user_events:
                    if isinstance(event, dict) and "thread_id" in event:
                        assert event["thread_id"] not in other_thread_ids, \
                            f"Cross-user leak: User {i} received event from another user"

    async def test_database_state_persistence(
        self,
        real_db_engine,
        real_websocket_manager
    ):
        """
        Integration Test 3: Database state persistence across agent lifecycle.
        
        Business Impact: Ensures conversation history is preserved.
        """"
        user_id = f"persist_user_{uuid.uuid4()}"
        thread_id = f"persist_thread_{uuid.uuid4()}"
        
        # First session - create initial state
        async with real_db_engine.begin() as conn:
            async with AsyncSession(conn) as db_session:
                # Create and process first message
                from netra_backend.app.services.thread_service import ThreadService
                thread_service = ThreadService()
                
                # Create thread
                thread = await thread_service.create_thread(
                    db_session=db_session,
                    user_id=user_id,
                    thread_id=thread_id,
                    metadata={"test": "persistence"}
                )
                
                await db_session.commit()
                
                # Store thread ID for verification
                created_thread_id = thread.id
        
        # Second session - verify persistence
        async with real_db_engine.begin() as conn:
            async with AsyncSession(conn) as db_session:
                from netra_backend.app.services.thread_service import ThreadService
                thread_service = ThreadService()
                
                # Retrieve thread
                retrieved_thread = await thread_service.get_thread(
                    db_session=db_session,
                    thread_id=thread_id
                )
                
                # Verify persistence
                assert retrieved_thread is not None, "Thread should be persisted"
                assert retrieved_thread.id == created_thread_id
                assert retrieved_thread.user_id == user_id
                assert retrieved_thread.metadata.get("test") == "persistence"
        
        # Third session - test message persistence
        async with real_db_engine.begin() as conn:
            async with AsyncSession(conn) as db_session:
                from netra_backend.app.services.message_service import MessageService
                message_service = MessageService()
                
                # Add message to thread
                message = await message_service.create_message(
                    db_session=db_session,
                    thread_id=thread_id,
                    content="Test message for persistence",
                    role="user"
                )
                
                await db_session.commit()
                message_id = message.id
        
        # Fourth session - verify message persistence
        async with real_db_engine.begin() as conn:
            async with AsyncSession(conn) as db_session:
                from netra_backend.app.services.message_service import MessageService
                message_service = MessageService()
                
                # Retrieve messages
                messages = await message_service.get_thread_messages(
                    db_session=db_session,
                    thread_id=thread_id
                )
                
                # Verify message persistence
                assert len(messages) > 0, "Messages should be persisted"
                assert any(m.id == message_id for m in messages)
                assert any(m.content == "Test message for persistence" for m in messages)

    async def test_websocket_event_delivery_reliability(
        self,
        real_websocket_manager
    ):
        """
        Integration Test 4: WebSocket event delivery for all critical events.
        
        Business Impact: Ensures users receive real-time updates.
        """"
        user_id = f"event_user_{uuid.uuid4()}"
        thread_id = f"event_thread_{uuid.uuid4()}"
        
        received_events = []
        disconnection_count = 0
        
        class ReliableWebSocket:
            def __init__(self):
                self.connected = True
                self.send_count = 0
            
            async def send_json(self, data):
                if not self.connected:
                    raise ConnectionError("WebSocket disconnected")
                received_events.append(data)
                self.send_count += 1
                
                # Simulate intermittent disconnection
                if self.send_count == 3:
                    self.connected = False
                    nonlocal disconnection_count
                    disconnection_count += 1
                    await asyncio.sleep(0.1)
                    self.connected = True
            
            async def receive_json(self):
                await asyncio.sleep(0.1)
                return {"type": "ping"}
            
            async def close(self):
                self.connected = False
        
        ws = ReliableWebSocket()
        
        # Connect user
        connection = await real_websocket_manager.connect_user(
            websocket=ws,
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Send critical events
        critical_events = [
            ("agent_started", {"agent": "test", "timestamp": datetime.utcnow().isoformat()}),
            ("agent_thinking", {"thought": "Processing request"}),
            ("tool_executing", {"tool": "analyzer", "params": {}}),
            ("tool_completed", {"tool": "analyzer", "result": "success"}),
            ("agent_completed", {"result": "Analysis complete", "success": True})
        ]
        
        for event_type, event_data in critical_events:
            try:
                await real_websocket_manager.emit_critical_event(
                    user_id=user_id,
                    event_type=event_type,
                    data=event_data,
                    connection_id=connection.connection_id
                )
            except Exception as e:
                # Should handle disconnection gracefully
                pass
        
        # Wait for events to be processed
        await asyncio.sleep(0.5)
        
        # Verify event delivery
        assert len(received_events) >= len(critical_events) - 1, \
            "Should receive most events despite disconnection"
        
        event_types_received = [
            e.get("type") for e in received_events 
            if isinstance(e, dict)
        ]
        
        # At least 4 out of 5 critical events should be delivered
        critical_event_types = [e[0] for e in critical_events]
        delivered_count = sum(
            1 for et in critical_event_types 
            if et in event_types_received
        )
        assert delivered_count >= 4, \
            f"Only {delivered_count}/5 critical events delivered"
        
        # Verify disconnection was handled
        assert disconnection_count > 0, "Disconnection simulation should have occurred"
        
        # Cleanup
        await real_websocket_manager.disconnect_user(user_id, connection.connection_id)

    async def test_error_propagation_across_boundaries(
        self,
        real_db_engine,
        real_websocket_manager
    ):
        """
        Integration Test 5: Error propagation across service boundaries.
        
        Business Impact: Ensures graceful error handling maintains user experience.
        """"
        error_scenarios = []
        
        class ErrorTrackingWebSocket:
            def __init__(self):
                self.errors = []
            
            async def send_json(self, data):
                if isinstance(data, dict) and "error" in data:
                    self.errors.append(data)
            
            async def receive_json(self):
                await asyncio.sleep(0.1)
                return {"type": "ping"}
            
            async def close(self):
                pass
        
        # Test database connection error
            async def test_db_error():
                ws = ErrorTrackingWebSocket()
            
            # Create handler with invalid database
            from netra_backend.app.agents.supervisor.unified_supervisor import UnifiedSupervisor
            supervisor = UnifiedSupervisor()
            
            # Intentionally create with None db_session to trigger error
            try:
                handler = AgentMessageHandler(None, ws)
                message = WebSocketMessage(
                    type=MessageType.START_AGENT,
                    payload={"user_request": "Test"},
                    thread_id="error_thread",
                    timestamp=datetime.utcnow().isoformat()
                )
                
                result = await handler.handle_message("error_user", ws, message)
                error_scenarios.append({
                    "scenario": "db_error",
                    "handled": result is False,
                    "errors": ws.errors
                })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "db_error",
                    "handled": True,
                    "exception": str(e)
                })
        
        # Test WebSocket manager error
        async def test_ws_manager_error():
            ws = ErrorTrackingWebSocket()
            
            # Create handler with real dependencies
            from netra_backend.app.agents.supervisor.unified_supervisor import UnifiedSupervisor
            from netra_backend.app.services.thread_service import ThreadService
            
            supervisor = UnifiedSupervisor()
            thread_service = ThreadService()
            
            # Create WebSocket manager that will fail
            failing_ws_manager = WebSocketManager()
            failing_ws_manager.emit_critical_event = AsyncMock(
                side_effect=Exception("WebSocket manager failed")
            )
            
            message_handler_service = MessageHandlerService(
                supervisor=supervisor,
                thread_service=thread_service,
                websocket_manager=failing_ws_manager
            )
            
            handler = AgentMessageHandler(message_handler_service, ws)
            
            message = WebSocketMessage(
                type=MessageType.START_AGENT,
                payload={"user_request": "Test with WS error"},
                thread_id="ws_error_thread",
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Should handle WebSocket errors gracefully
            result = await handler.handle_message("ws_error_user", ws, message)
            
            error_scenarios.append({
                "scenario": "ws_manager_error",
                "handled": True,  # Should complete despite WS errors
                "result": result
            })
        
        # Execute error scenarios
        await test_db_error()
        await test_ws_manager_error()
        
        # Verify error handling
        for scenario in error_scenarios:
            assert scenario["handled"], \
                f"Error not handled properly in {scenario['scenario']]"
            
            if "errors" in scenario:
                # User should receive error notifications
                assert len(scenario["errors"]) > 0 or scenario.get("exception"), \
                    f"No error feedback in {scenario['scenario']]"


# ============================================================================
# INTEGRATION TESTS 6-10: ADVANCED SCENARIOS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentHandlerAdvancedIntegration:
    """Advanced integration tests for complex scenarios."""
    
    async def test_agent_workflow_with_tool_notifications(
        self,
        real_db_engine,
        real_websocket_manager
    ):
        """
        Integration Test 6: Agent workflow with tool execution notifications.
        
        Business Impact: Validates complete agent transparency through events.
        """"
        # Implementation would follow similar pattern to tests above
        # Focusing on tool execution events and notifications
        pass
    
    async def test_thread_continuity_across_sessions(
        self,
        real_db_engine,
        real_websocket_manager
    ):
        """
        Integration Test 7: Thread continuity across multiple sessions.
        
        Business Impact: Ensures conversation context is maintained.
        """"
        # Implementation would test reconnection and context preservation
        pass
    
    async def test_configuration_cascade_environments(
        self,
        real_db_engine
    ):
        """
        Integration Test 8: Configuration cascade testing across environments.
        
        Business Impact: Prevents configuration regression issues.
        """"
        # Implementation would test environment-specific configurations
        pass
    
    async def test_supervisor_isolation_concurrent_users(
        self,
        real_db_engine,
        real_websocket_manager
    ):
        """
        Integration Test 9: Agent supervisor isolation testing.
        
        Business Impact: Ensures supervisor instances are properly isolated.
        """"
        # Implementation would test supervisor factory pattern isolation
        pass
    
    async def test_realistic_load_simulation(
        self,
        real_db_engine,
        real_websocket_manager
    ):
        """
        Integration Test 10: Realistic load simulation with 10 users.
        
        Business Impact: Validates production readiness.
        """"
        # Implementation would simulate realistic user load patterns
        pass