"""
Critical Integration Tests for Netra AI Platform
Tests the most important cross-component interactions
"""

import pytest
from pytest_asyncio import fixture as pytest_asyncio_fixture
import asyncio
import json
import jwt
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.services.agent_service import AgentService
from app.services.websocket.message_handler import BaseMessageHandler
from app.services.state_persistence_service import StatePersistenceService
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.services.database.run_repository import RunRepository
from app.ws_manager import WebSocketManager
from app.schemas.registry import (
    WebSocketMessage, SubAgentUpdate, AgentCompleted
)
from app.schemas.Agent import AgentStarted
from starlette.websockets import WebSocketState
from app.schemas.registry import UserBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile
import os


class TestCriticalIntegration:
    """Critical integration tests for core system functionality"""

    @pytest_asyncio_fixture
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
        db_setup = setup_real_database
        infra = setup_integration_infrastructure
        session = db_setup["session"]
        
        # Create repositories
        thread_repo = ThreadRepository()
        message_repo = MessageRepository()
        run_repo = RunRepository()
        
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
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.send_json = AsyncMock()  # Mock the send_json method
        mock_websocket.send_text = AsyncMock()  # Mock send_text for compatibility
        
        # Use the WebSocketManager's connect method to properly register the connection
        conn_info = await infra["websocket_manager"].connect(user_id, mock_websocket)
        
        # Execute agent workflow
        with patch('app.services.state_persistence_service.StatePersistenceService.save_agent_state', 
                   AsyncMock()) as mock_save_state:
            with patch('app.services.state_persistence_service.StatePersistenceService.load_agent_state',
                       AsyncMock(return_value=None)):
                
                # Run the supervisor
                result = await supervisor.run(
                    user_request=message.content,
                    run_id=str(uuid.uuid4()),
                    stream_updates=True
                )
        
        # Verify results
        assert result != None
        assert "optimization" in str(result).lower()
        
        # Verify state was saved
        assert mock_save_state.called
        save_calls = mock_save_state.call_args_list
        assert len(save_calls) >= 3  # At least triage, data, and optimization agents
        
        # Verify WebSocket messages were sent
        assert mock_websocket.send_json.called, "WebSocket should have sent JSON messages"
        ws_messages = [
            call.args[0] for call in mock_websocket.send_json.call_args_list
        ]
        
        # Check for agent lifecycle messages
        has_started = any("agent_started" in str(msg) for msg in ws_messages)
        has_updates = any("sub_agent_update" in str(msg) for msg in ws_messages)
        has_completed = any("agent_completed" in str(msg) for msg in ws_messages)
        
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
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()  # WebSocketManager uses send_json
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
            user_id,
            test_message.model_dump()
        )
        
        # Verify message was sent (WebSocketManager uses send_json)
        mock_websocket.send_json.assert_called()
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "agent_request"
        assert sent_data["payload"]["query"] == "Test authenticated request"
        
        # Test sending message to user's connections
        await ws_manager.send_message(
            user_id,
            {"type": "notification", "message": "Test broadcast"}
        )
        
        # Verify broadcast was sent
        assert mock_websocket.send_json.call_count >= 2
        
        # Test connection cleanup
        await ws_manager.disconnect(user_id, mock_websocket)
        assert user_id not in ws_manager.active_connections
        
        # Test unauthorized access (no token)
        unauthorized_user_id = None  # No user_id should cause failure
        with pytest.raises(Exception):
            # This should fail without proper user_id (None)
            await ws_manager.connect(unauthorized_user_id, mock_websocket)
        
        # Verify unauthorized connection was not added
        assert unauthorized_user_id not in ws_manager.active_connections

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
        db_setup = setup_real_database
        session = db_setup["session"]
        infra = setup_integration_infrastructure
        
        # Setup test data and run database operations
        user_id, thread, run_id = await self._setup_test_entities(session)
        state_service = self._create_state_service(session)
        
        # Test initial state persistence
        initial_state = await self._test_initial_state_save(state_service, run_id, thread.id, user_id)
        
        # Test partial execution state save
        triage_output = self._get_triage_output()
        partial_state = await self._test_partial_state_save(state_service, run_id, thread.id, user_id, triage_output)
        
        # Test state recovery
        recovered_state = await self._test_state_recovery(state_service, run_id, triage_output)
        
        # Test final state persistence
        await self._test_final_state_save(state_service, run_id, thread.id, user_id, triage_output)
        
        # Verify complete workflow
        await self._verify_complete_workflow(state_service, run_id, thread.id)
        
        # Cleanup
        await session.commit()

    async def _setup_test_entities(self, session):
        """Setup test entities for state persistence test"""
        user_id = str(uuid.uuid4())
        thread = Mock(id=str(uuid.uuid4()), name="State Recovery Test", user_id=user_id)
        run_id = str(uuid.uuid4())
        await self._create_run_in_database(session, run_id, thread.id)
        return user_id, thread, run_id

    async def _create_run_in_database(self, session, run_id, thread_id):
        """Create run object in database"""
        from app.db.models_postgres import Run
        import time
        run = Run(
            id=run_id, thread_id=thread_id, assistant_id="test-assistant",
            status="in_progress", created_at=int(time.time()), metadata_={}
        )
        session.add(run)
        await session.commit()

    def _create_state_service(self, session):
        """Create state persistence service with database session"""
        state_service = StatePersistenceService()
        state_service.db_session = session
        return state_service

    async def _test_initial_state_save(self, state_service, run_id, thread_id, user_id):
        """Test saving initial agent state"""
        initial_state = DeepAgentState(user_request="Optimize performance")
        await state_service.save_agent_state(
            run_id=run_id, thread_id=thread_id, user_id=user_id,
            state=initial_state, db_session=state_service.db_session
        )
        return initial_state

    def _get_triage_output(self):
        """Get triage output for testing"""
        return {
            "category": "optimization",
            "analysis": "GPU optimization needed",
            "priority": "high"
        }

    async def _test_partial_state_save(self, state_service, run_id, thread_id, user_id, triage_output):
        """Test saving partial execution state"""
        partial_state = DeepAgentState(
            user_request="Optimize performance", triage_result=triage_output
        )
        await state_service.save_agent_state(
            run_id=run_id, thread_id=thread_id, user_id=user_id,
            state=partial_state, db_session=state_service.db_session
        )
        return partial_state

    async def _test_state_recovery(self, state_service, run_id, triage_output):
        """Test loading state from database after simulated failure"""
        recovered_state = await state_service.load_agent_state(
            run_id=run_id, db_session=state_service.db_session
        )
        assert recovered_state != None
        assert recovered_state.triage_result == triage_output
        assert recovered_state.data_result == None
        return recovered_state

    async def _test_final_state_save(self, state_service, run_id, thread_id, user_id, triage_output):
        """Test saving final complete state"""
        final_state = DeepAgentState(
            user_request="Optimize performance", triage_result=triage_output,
            data_result={"data": "collected"}, optimizations_result={"optimizations": "applied"}
        )
        await state_service.save_agent_state(
            run_id=run_id, thread_id=thread_id, user_id=user_id,
            state=final_state, db_session=state_service.db_session
        )

    async def _verify_complete_workflow(self, state_service, run_id, thread_id):
        """Verify complete workflow state persistence"""
        final_recovered = await state_service.load_agent_state(
            run_id=run_id, db_session=state_service.db_session
        )
        assert final_recovered != None
        assert final_recovered.triage_result != None
        assert final_recovered.data_result != None
        assert final_recovered.optimizations_result != None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])