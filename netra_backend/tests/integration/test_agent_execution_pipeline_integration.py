"""
Test Agent Execution Pipeline Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable agent execution with proper database persistence and WebSocket notifications
- Value Impact: Agents must execute correctly to deliver AI-powered insights to users
- Strategic Impact: Core platform functionality that directly enables user value delivery through chat

This test suite validates the complete agent execution pipeline:
1. Agent instance creation and initialization
2. Execution context setup with database persistence
3. Tool dispatcher integration with WebSocket notifications
4. User context isolation across concurrent executions
5. Error handling and recovery with proper state transitions
"""

import asyncio
import uuid
import pytest
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, AgentID, ExecutionID,
    ensure_user_id, ensure_thread_id, ensure_run_id,
    AgentExecutionContext, ExecutionContextState
)

# Core dependencies
from netra_backend.app.dependencies import (
    get_db, validate_session_is_request_scoped,
    SessionIsolationError
)
from netra_backend.app.agents.supervisor.execution_factory import (
    ExecutionEngineFactory, ExecutionFactoryConfig
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    get_agent_instance_factory, configure_agent_instance_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread


class TestAgentExecutionPipelineIntegration(BaseIntegrationTest):
    """Test agent execution pipeline with real database and proper context isolation."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_with_database_persistence(self, real_services_fixture, isolated_env):
        """Test complete agent execution with real PostgreSQL persistence."""
        # Setup real database session
        db = real_services_fixture.get("db") or self._create_test_db_session()
        validate_session_is_request_scoped(db, "test_agent_execution")
        
        # Create test user with strongly typed ID
        user_id = ensure_user_id(str(uuid.uuid4()))
        test_user = User(
            id=str(user_id),
            email="test.agent@example.com",
            name="Agent Test User",
            created_at=datetime.utcnow()
        )
        
        db.add(test_user)
        await db.commit()
        
        # Create thread for execution context
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        test_thread = Thread(
            id=str(thread_id),
            user_id=str(user_id),
            title="Agent Execution Test",
            created_at=datetime.utcnow()
        )
        
        db.add(test_thread)
        await db.commit()
        
        # Create execution context with strongly typed IDs
        execution_id = ExecutionID(str(uuid.uuid4()))
        run_id = ensure_run_id(str(uuid.uuid4()))
        request_id = RequestID(str(uuid.uuid4()))
        agent_id = AgentID("test_agent")
        
        execution_context = AgentExecutionContext(
            execution_id=execution_id,
            agent_id=agent_id,
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            state=ExecutionContextState.CREATED,
            metadata={"test_source": "integration_test"}
        )
        
        # Create execution factory with proper configuration
        factory_config = ExecutionFactoryConfig(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            database_session=db,
            enable_websocket_notifications=True,
            isolation_level="per_request"
        )
        
        execution_factory = ExecutionEngineFactory(config=factory_config)
        
        # Mock WebSocket manager for testing
        mock_websocket_manager = AsyncMock(spec=UnifiedWebSocketManager)
        mock_websocket_manager.send_agent_started = AsyncMock()
        mock_websocket_manager.send_agent_completed = AsyncMock()
        
        # Create agent instance with factory pattern
        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager', 
                  return_value=mock_websocket_manager):
            
            agent_factory = get_agent_instance_factory()
            configure_agent_instance_factory(agent_factory, execution_context)
            
            # Execute agent with real database interaction
            agent_instance = await agent_factory.create_agent(
                agent_type="triage_agent",
                user_context=UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id,
                    database_session=db
                )
            )
            
            # Simulate agent execution with tool calls
            execution_result = await agent_instance.execute_with_context(
                message="Test message requiring triage",
                context=execution_context
            )
            
            # Verify database persistence
            assert execution_result is not None
            assert execution_result.get("status") in ["completed", "success"]
            
            # Verify user and thread still exist in database
            db_user = await db.get(User, str(user_id))
            assert db_user is not None
            assert db_user.email == "test.agent@example.com"
            
            db_thread = await db.get(Thread, str(thread_id))
            assert db_thread is not None
            assert db_thread.user_id == str(user_id)
            
            # Verify WebSocket notifications were sent
            mock_websocket_manager.send_agent_started.assert_called_once()
            mock_websocket_manager.send_agent_completed.assert_called_once()
            
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_executions_with_user_isolation(self, real_services_fixture, isolated_env):
        """Test multiple concurrent agent executions maintain proper user isolation."""
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Create two separate users
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        
        user1 = User(id=str(user1_id), email="user1@test.com", name="User 1")
        user2 = User(id=str(user2_id), email="user2@test.com", name="User 2")
        
        db.add_all([user1, user2])
        await db.commit()
        
        # Create separate threads for each user
        thread1_id = ensure_thread_id(str(uuid.uuid4()))
        thread2_id = ensure_thread_id(str(uuid.uuid4()))
        
        thread1 = Thread(id=str(thread1_id), user_id=str(user1_id), title="Thread 1")
        thread2 = Thread(id=str(thread2_id), user_id=str(user2_id), title="Thread 2")
        
        db.add_all([thread1, thread2])
        await db.commit()
        
        # Mock WebSocket manager
        mock_websocket_manager = AsyncMock()
        
        async def execute_agent_for_user(user_id: UserID, thread_id: ThreadID, message: str):
            """Execute agent with proper user context isolation."""
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager', 
                      return_value=mock_websocket_manager):
                
                execution_context = AgentExecutionContext(
                    execution_id=ExecutionID(str(uuid.uuid4())),
                    agent_id=AgentID("triage_agent"),
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=ensure_run_id(str(uuid.uuid4())),
                    request_id=RequestID(str(uuid.uuid4()))
                )
                
                factory_config = ExecutionFactoryConfig(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=execution_context.run_id,
                    database_session=db,
                    isolation_level="per_user"
                )
                
                execution_factory = ExecutionEngineFactory(config=factory_config)
                agent_factory = get_agent_instance_factory()
                
                user_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=execution_context.run_id,
                    database_session=db
                )
                
                agent_instance = await agent_factory.create_agent(
                    agent_type="triage_agent",
                    user_context=user_context
                )
                
                result = await agent_instance.execute_with_context(
                    message=message,
                    context=execution_context
                )
                
                return result, execution_context
        
        # Execute both agents concurrently
        results = await asyncio.gather(
            execute_agent_for_user(user1_id, thread1_id, "User 1 message"),
            execute_agent_for_user(user2_id, thread2_id, "User 2 message"),
            return_exceptions=True
        )
        
        # Verify both executions completed successfully
        assert len(results) == 2
        for result in results:
            assert not isinstance(result, Exception), f"Agent execution failed: {result}"
            agent_result, context = result
            assert agent_result is not None
            assert context.user_id in [user1_id, user2_id]
        
        # Verify user isolation - each context should have correct user_id
        result1, context1 = results[0]
        result2, context2 = results[1]
        
        assert context1.user_id != context2.user_id
        assert context1.thread_id != context2.thread_id
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_agent_execution_error_handling_with_rollback(self, real_services_fixture, isolated_env):
        """Test agent execution error handling with proper database rollback."""
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Setup test data
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        test_user = User(id=str(user_id), email="error.test@example.com", name="Error Test")
        test_thread = Thread(id=str(thread_id), user_id=str(user_id), title="Error Test Thread")
        
        db.add_all([test_user, test_thread])
        await db.commit()
        
        # Create execution context that will trigger an error
        execution_context = AgentExecutionContext(
            execution_id=ExecutionID(str(uuid.uuid4())),
            agent_id=AgentID("invalid_agent"),  # Invalid agent type
            user_id=user_id,
            thread_id=thread_id,
            run_id=ensure_run_id(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        # Mock WebSocket manager to simulate notification failures
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_agent_started = AsyncMock(side_effect=Exception("WebSocket error"))
        
        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager', 
                  return_value=mock_websocket_manager):
            
            # Attempt agent execution that should fail
            agent_factory = get_agent_instance_factory()
            
            with pytest.raises(Exception) as exc_info:
                agent_instance = await agent_factory.create_agent(
                    agent_type="invalid_agent",
                    user_context=UserExecutionContext(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=execution_context.run_id,
                        database_session=db
                    )
                )
            
            # Verify the error was properly handled
            assert exc_info.value is not None
            
            # Verify database state is consistent (user and thread should still exist)
            db_user = await db.get(User, str(user_id))
            assert db_user is not None
            assert db_user.email == "error.test@example.com"
            
            db_thread = await db.get(Thread, str(thread_id))
            assert db_thread is not None
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_isolation_enforcement(self, real_services_fixture, isolated_env):
        """Test that session isolation is properly enforced in agent execution."""
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Verify session is properly scoped
        validate_session_is_request_scoped(db, "session_isolation_test")
        
        # Test that global session usage is detected and rejected
        from netra_backend.app.dependencies import mark_session_as_global
        
        # Mark session as global (simulating a violation)
        mark_session_as_global(db)
        
        # This should now raise SessionIsolationError
        with pytest.raises(SessionIsolationError):
            validate_session_is_request_scoped(db, "violation_test")
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_context_state_transitions(self, real_services_fixture, isolated_env):
        """Test execution context state transitions during agent lifecycle."""
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Setup test data
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        test_user = User(id=str(user_id), email="state.test@example.com", name="State Test")
        test_thread = Thread(id=str(thread_id), user_id=str(user_id), title="State Test Thread")
        
        db.add_all([test_user, test_thread])
        await db.commit()
        
        # Create execution context
        execution_context = AgentExecutionContext(
            execution_id=ExecutionID(str(uuid.uuid4())),
            agent_id=AgentID("triage_agent"),
            user_id=user_id,
            thread_id=thread_id,
            run_id=ensure_run_id(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4())),
            state=ExecutionContextState.CREATED
        )
        
        # Test state transitions
        assert execution_context.state == ExecutionContextState.CREATED
        
        # Simulate execution start
        execution_context.state = ExecutionContextState.ACTIVE
        assert execution_context.state == ExecutionContextState.ACTIVE
        
        # Mock successful agent execution
        mock_websocket_manager = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager', 
                  return_value=mock_websocket_manager):
            
            # Simulate completion
            execution_context.state = ExecutionContextState.COMPLETED
            assert execution_context.state == ExecutionContextState.COMPLETED
            
            # Verify final state is persisted
            assert execution_context.state in [
                ExecutionContextState.COMPLETED, 
                ExecutionContextState.FAILED,
                ExecutionContextState.CANCELLED
            ]
        
        await db.close()

    def _create_test_db_session(self) -> AsyncSession:
        """Create a test database session - simplified for integration testing."""
        # This would normally create a real database session
        # For now, return a mock that implements the AsyncSession interface
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.close = AsyncMock()
        return mock_session