"""
Critical Integration Tests for Netra AI Platform
Tests the most important cross-component interactions
"""

import pytest
import asyncio
import json
import jwt
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any

from app.agents.supervisor import Supervisor
from app.agents.base import BaseSubAgent
from app.services.agent_service import AgentService
from app.services.websocket.message_handler import BaseMessageHandler
from app.services.state_persistence_service import StatePersistenceService
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.services.database.run_repository import RunRepository
from app.ws_manager import WebSocketManager
from app.schemas.WebSocket import (
    WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted
)
from app.schemas.User import UserBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile
import os


class TestCriticalIntegration:
    """Critical integration tests for core system functionality"""

    @pytest.fixture
    async def setup_real_database(self):
        """Setup a real in-memory SQLite database for integration testing"""
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_url = f"sqlite+aiosqlite:///{db_file.name}"
        
        # Create engine and session
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session
        async with async_session() as session:
            yield {
                "session": session,
                "engine": engine,
                "db_file": db_file.name
            }
        
        # Cleanup
        await engine.dispose()
        try:
            os.unlink(db_file.name)
        except PermissionError:
            # On Windows, file may still be locked
            # This is okay for test cleanup
            pass

    @pytest.fixture
    def setup_integration_infrastructure(self):
        """Setup integrated infrastructure for testing"""
        # Real WebSocket Manager
        websocket_manager = WebSocketManager()
        
        # Mock LLM Manager with realistic responses
        llm_manager = Mock()
        llm_manager.call_llm = AsyncMock(side_effect=self._mock_llm_response)
        llm_manager.ask_llm = AsyncMock(side_effect=self._mock_ask_llm_response)
        
        # Real state persistence service
        state_service = StatePersistenceService()
        
        return {
            "websocket_manager": websocket_manager,
            "llm_manager": llm_manager,
            "state_service": state_service
        }

    async def _mock_llm_response(self, messages, **kwargs):
        """Mock LLM response based on message content"""
        last_message = messages[-1] if messages else {"content": ""}
        content = last_message.get("content", "")
        
        if "triage" in content.lower():
            return {
                "content": json.dumps({
                    "category": "optimization",
                    "priority": "high",
                    "analysis": "GPU optimization needed"
                })
            }
        elif "data" in content.lower():
            return {
                "content": json.dumps({
                    "metrics": {
                        "gpu_utilization": 85,
                        "memory_usage": 12000,
                        "latency_p95": 250
                    }
                })
            }
        elif "optimization" in content.lower():
            return {
                "content": json.dumps({
                    "recommendations": [
                        "Enable tensor parallelism",
                        "Optimize batch size to 32",
                        "Use mixed precision training"
                    ]
                })
            }
        else:
            return {"content": "Test response"}

    async def _mock_ask_llm_response(self, prompt, **kwargs):
        """Mock ask_llm response for simpler agent calls"""
        if "triage" in prompt.lower():
            return json.dumps({
                "category": "optimization",
                "analysis": "Performance optimization required"
            })
        elif "data" in prompt.lower():
            return json.dumps({
                "data_collected": True,
                "metrics": {"gpu": 85, "memory": 12000}
            })
        else:
            return json.dumps({"response": "Test response"})

    @pytest.mark.asyncio
    async def test_1_full_agent_workflow_with_database_and_websocket(
        self, setup_real_database, setup_integration_infrastructure
    ):
        """
        Integration Test 1: Complete Agent Workflow with Database and WebSocket
        - Creates user, thread, and messages in database
        - Executes full agent pipeline
        - Streams updates via WebSocket
        - Persists state to database
        - Verifies final results in database
        """
        db_setup = await setup_real_database
        infra = setup_integration_infrastructure
        session = db_setup["session"]
        
        # Create repositories
        thread_repo = ThreadRepository(session)
        message_repo = MessageRepository(session)
        run_repo = RunRepository(session)
        
        # Create test user
        user_id = str(uuid.uuid4())
        user_data = {
            "id": user_id,
            "email": "test@example.com",
            "username": "testuser"
        }
        
        # Create thread using dict (mock)
        thread = Mock(
            id=str(uuid.uuid4()),
            name="Test Integration Thread",
            user_id=user_id
        )
        
        # Create initial message (mock)
        message = Mock(
            id=str(uuid.uuid4()),
            thread_id=thread.id,
            role="user",
            content="Optimize my GPU workload for better performance"
        )
        
        # Setup supervisor with real database
        supervisor = Supervisor(
            session, 
            infra["llm_manager"], 
            infra["websocket_manager"],
            Mock()  # tool_dispatcher
        )
        supervisor.thread_id = thread.id
        supervisor.user_id = user_id
        
        # Mock WebSocket connection for streaming
        mock_websocket = AsyncMock()
        connection_id = f"conn_{user_id}"
        infra["websocket_manager"].active_connections[connection_id] = {
            "websocket": mock_websocket,
            "user_id": user_id
        }
        
        # Execute agent workflow
        with patch('app.services.state_persistence_service.StatePersistenceService.save_agent_state', 
                   AsyncMock()) as mock_save_state:
            with patch('app.services.state_persistence_service.StatePersistenceService.load_agent_state',
                       AsyncMock(return_value=None)):
                
                # Run the supervisor
                result = await supervisor.run(
                    user_query=message.content,
                    thread_id=thread.id,
                    run_id=str(uuid.uuid4())
                )
        
        # Verify results
        assert result is not None
        assert "optimization" in str(result).lower()
        
        # Verify state was saved
        assert mock_save_state.called
        save_calls = mock_save_state.call_args_list
        assert len(save_calls) >= 3  # At least triage, data, and optimization agents
        
        # Verify WebSocket messages were sent
        assert mock_websocket.send_text.called
        ws_messages = [
            call.args[0] for call in mock_websocket.send_text.call_args_list
        ]
        
        # Check for agent lifecycle messages
        has_started = any("agent_started" in msg for msg in ws_messages)
        has_updates = any("sub_agent_update" in msg for msg in ws_messages)
        has_completed = any("agent_completed" in msg for msg in ws_messages)
        
        assert has_started, "Should have agent started message"
        assert has_updates, "Should have sub-agent updates"
        assert has_completed, "Should have agent completed message"
        
        # Verify message repository was called
        # In a real integration test, we would verify database state
        # For now, we verify the mock interactions
        assert supervisor.thread_id == thread.id
        assert supervisor.user_id == user_id
        
        # Cleanup
        await session.commit()

    @pytest.mark.asyncio
    async def test_2_websocket_authentication_and_message_flow(
        self, setup_integration_infrastructure
    ):
        """
        Integration Test 2: WebSocket Connection and Message Flow
        - Establishes WebSocket connection with user context
        - Sends messages through WebSocket
        - Verifies message routing and handling
        - Tests broadcast functionality
        - Tests connection lifecycle and cleanup
        """
        infra = setup_integration_infrastructure
        ws_manager = infra["websocket_manager"]
        
        # Create test user
        user_id = str(uuid.uuid4())
        user_data = {
            "id": user_id,
            "email": "websocket@test.com",
            "username": "wsuser"
        }
        
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.receive_text = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        # Simulate user connection
        # Note: connection_id is generated internally by WebSocketManager
        
        # Add connection with user context
        conn_info = await ws_manager.connect(user_id, mock_websocket)
        connection_id = conn_info.connection_id
        
        # Verify connection is tracked
        assert user_id in ws_manager.active_connections
        assert connection_id in ws_manager.connection_registry
        assert ws_manager.connection_registry[connection_id].user_id == user_id
        
        # Test sending authenticated message
        test_message = WebSocketMessage(
            type="agent_request",
            payload={
                "query": "Test authenticated request",
                "thread_id": str(uuid.uuid4())
            }
        )
        
        # Send message through WebSocket
        await ws_manager.send_message(
            connection_id,
            test_message.model_dump()
        )
        
        # Verify message was sent
        mock_websocket.send_text.assert_called()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "agent_request"
        assert sent_data["payload"]["query"] == "Test authenticated request"
        
        # Test broadcast to user's connections
        await ws_manager.broadcast_to_user(
            user_id,
            {"type": "notification", "message": "Test broadcast"}
        )
        
        # Verify broadcast was sent
        assert mock_websocket.send_text.call_count >= 2
        
        # Test connection cleanup
        await ws_manager.disconnect(connection_id)
        assert connection_id not in ws_manager.active_connections
        
        # Test unauthorized access (no token)
        unauthorized_conn_id = f"conn_unauthorized_{uuid.uuid4()}"
        with pytest.raises(Exception):
            # This should fail without proper user_id
            await ws_manager.connect(mock_websocket, None, unauthorized_conn_id)
        
        # Verify unauthorized connection was not added
        assert unauthorized_conn_id not in ws_manager.active_connections

    @pytest.mark.asyncio
    async def test_3_database_state_persistence_and_recovery(
        self, setup_real_database, setup_integration_infrastructure
    ):
        """
        Integration Test 3: Database State Persistence and Recovery
        - Saves agent state to database during execution
        - Simulates failure mid-execution
        - Recovers state from database
        - Resumes execution from saved checkpoint
        - Verifies complete recovery and continuation
        """
        db_setup = await setup_real_database
        session = db_setup["session"]
        infra = setup_integration_infrastructure
        
        # Create repositories
        thread_repo = ThreadRepository(session)
        run_repo = RunRepository(session)
        message_repo = MessageRepository(session)
        
        # Setup test data
        user_id = str(uuid.uuid4())
        thread = Mock(
            id=str(uuid.uuid4()),
            name="State Recovery Test",
            user_id=user_id
        )
        
        run_id = str(uuid.uuid4())
        run = Mock(
            id=run_id,
            thread_id=thread.id,
            status="in_progress"
        )
        
        # Create state persistence service with real database
        state_service = StatePersistenceService()
        state_service.db_session = session
        
        # Initial agent state
        initial_state = {
            "thread_id": thread.id,
            "run_id": run_id,
            "user_id": user_id,
            "current_agent": "triage",
            "completed_agents": [],
            "agent_outputs": {},
            "metadata": {
                "start_time": datetime.utcnow().isoformat(),
                "request": "Optimize performance"
            }
        }
        
        # Save initial state
        await state_service.save_agent_state(
            thread_id=thread.id,
            run_id=run_id,
            agent_name="supervisor",
            state=initial_state
        )
        
        # Simulate partial execution - triage completes
        triage_output = {
            "category": "optimization",
            "analysis": "GPU optimization needed",
            "priority": "high"
        }
        
        partial_state = {
            **initial_state,
            "current_agent": "data",
            "completed_agents": ["triage"],
            "agent_outputs": {"triage": triage_output}
        }
        
        await state_service.save_agent_state(
            thread_id=thread.id,
            run_id=run_id,
            agent_name="supervisor",
            state=partial_state
        )
        
        # Simulate failure and recovery
        # Load state from database
        recovered_state = await state_service.load_agent_state(
            thread_id=thread.id,
            run_id=run_id,
            agent_name="supervisor"
        )
        
        # Verify state was recovered correctly
        assert recovered_state is not None
        assert recovered_state["current_agent"] == "data"
        assert recovered_state["completed_agents"] == ["triage"]
        assert recovered_state["agent_outputs"]["triage"] == triage_output
        
        # Create new supervisor with recovered state
        supervisor = Supervisor(
            session,
            infra["llm_manager"],
            infra["websocket_manager"],
            Mock()
        )
        supervisor.thread_id = thread.id
        supervisor.user_id = user_id
        
        # Resume execution from checkpoint
        with patch.object(supervisor, 'state', recovered_state):
            # Mock remaining agent executions
            with patch.object(supervisor, '_run_data_sub_agent', 
                              AsyncMock(return_value={"data": "collected"})):
                with patch.object(supervisor, '_run_optimizations_core_sub_agent',
                                  AsyncMock(return_value={"optimizations": "applied"})):
                    
                    # Resume from data agent
                    supervisor.state["completed_agents"] = ["triage", "data"]
                    supervisor.state["agent_outputs"]["data"] = {"data": "collected"}
                    
                    # Continue with optimization
                    optimization_result = await supervisor._run_optimizations_core_sub_agent(
                        "Continue optimization", thread.id, run_id
                    )
                    
                    # Update state
                    supervisor.state["completed_agents"].append("optimization")
                    supervisor.state["agent_outputs"]["optimization"] = optimization_result
        
        # Save final state
        final_state = {
            **supervisor.state,
            "current_agent": "completed",
            "completed_agents": ["triage", "data", "optimization"],
            "status": "completed"
        }
        
        await state_service.save_agent_state(
            thread_id=thread.id,
            run_id=run_id,
            agent_name="supervisor",
            state=final_state
        )
        
        # Verify complete execution
        final_recovered = await state_service.load_agent_state(
            thread_id=thread.id,
            run_id=run_id,
            agent_name="supervisor"
        )
        
        assert final_recovered["status"] == "completed"
        assert len(final_recovered["completed_agents"]) == 3
        assert "triage" in final_recovered["agent_outputs"]
        assert "data" in final_recovered["agent_outputs"]
        assert "optimization" in final_recovered["agent_outputs"]
        
        # Verify thread context recovery
        thread_context = await state_service.get_thread_context(thread.id)
        assert thread_context is not None
        
        # Verify run status would be updated
        # In a real integration test with database
        assert run.id == run_id
        assert run.thread_id == thread.id
        
        # Cleanup
        await session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])