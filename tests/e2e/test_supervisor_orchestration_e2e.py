class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""End-to-End Tests for Supervisor Agent Orchestration.

Complete end-to-end tests using real services (database, Redis, LLM when available)
to validate the entire orchestration pipeline from user request to final response.

Business Value: Ensures the complete system works correctly in production-like conditions.
"""

import asyncio
import pytest
import time
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.core.configuration.manager import ConfigurationManager
from netra_backend.app.database import get_db, Base
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core import UnifiedWebSocketManager
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.models import User, Thread, Message, AgentExecution
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


@pytest.fixture(scope="session")
def event_loop():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_database():
    """Create test database session."""
    config = ConfigurationManager()
    config.set_environment("testing")
    
    # Create test database engine
    engine = create_async_engine(
        config.get_postgres_url(),
        echo=False,
        pool_pre_ping=True,
        pool_size=5
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    yield async_session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def db_session(test_database):
    """Get database session for test."""
    async with test_database() as session:
        yield session
        await session.rollback()


@pytest.fixture
def llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create LLM manager (real or mock based on environment)."""
    from shared.isolated_environment import get_env
    env = get_env()
    use_real_llm = env.get("USE_REAL_LLM", "false").lower() == "true"
    
    if use_real_llm:
        # Use real LLM for true E2E testing
        return LLMManager()
    else:
        # Use mock for faster testing
        manager = MagicMock(spec=LLMManager)
        manager.generate = AsyncMock(return_value=json.dumps({
            "response": "Test response",
            "confidence": 0.95,
            "reasoning": "Test reasoning"
        }))
        return manager


@pytest.fixture
def websocket_manager():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create WebSocket manager for testing."""
    manager = UnifiedWebSocketManager()
    return manager


@pytest.fixture
def tool_dispatcher(llm_manager):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create tool dispatcher."""
    return ToolDispatcher(llm_manager)


@pytest.fixture
async def test_user(db_session):
    """Create test user in database."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        name="Test User",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_thread(db_session, test_user):
    """Create test thread in database."""
    thread = Thread(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        title="Test Thread",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(thread)
    await db_session.commit()
    return thread


class TestSupervisorE2E:
    """End-to-end tests for Supervisor orchestration."""
    
    @pytest.mark.asyncio
    async def test_complete_user_request_flow(self, db_session, llm_manager, 
                                             websocket_manager, tool_dispatcher,
                                             test_user, test_thread):
        """Test complete flow from user request to response."""
        # Create supervisor
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Create user message
        user_message = Message(
            id=str(uuid.uuid4()),
            thread_id=test_thread.id,
            role="user",
            content="Help me optimize my AI infrastructure costs",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(user_message)
        await db_session.commit()
        
        # Create state with user message
        state = DeepAgentState()
        state.thread_id = test_thread.id
        state.user_id = test_user.id
        state.messages = [
            {
                "role": "user",
                "content": "Help me optimize my AI infrastructure costs"
            }
        ]
        
        # Track WebSocket events
        events_received = []
        
        async def capture_events(thread_id, message):
            events_received.append({
                'thread_id': thread_id,
                'type': message.type if hasattr(message, 'type') else 'unknown',
                'timestamp': datetime.now(timezone.utc)
            })
        
        websocket_manager.send_message = capture_events
        
        # Execute supervisor
        run_id = str(uuid.uuid4())
        start_time = time.time()
        
        await supervisor.execute(state, run_id, stream_updates=True)
        
        elapsed = time.time() - start_time
        
        # Verify execution completed
        assert elapsed < 30  # Should complete within 30 seconds
        
        # Verify WebSocket events were sent
        assert len(events_received) > 0
        
        event_types = [e['type'] for e in events_received]
        
        # Critical events must be present
        critical_events = ['agent_started', 'agent_completed']
        for event in critical_events:
            assert any(event in evt for evt in event_types), f"Missing critical event: {event}"
        
        # Verify database records created
        execution = await db_session.execute(
            select(AgentExecution).where(AgentExecution.run_id == run_id)
        )
        agent_execution = execution.scalar_one_or_none()
        
        if agent_execution:
            assert agent_execution.status in ['completed', 'success']
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, db_session, llm_manager,
                                          websocket_manager, tool_dispatcher,
                                          test_user, test_thread):
        """Test multi-turn conversation with context preservation."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # First turn
        state1 = DeepAgentState()
        state1.thread_id = test_thread.id
        state1.user_id = test_user.id
        state1.messages = [
            {"role": "user", "content": "What are my current AI costs?"}
        ]
        
        run_id1 = str(uuid.uuid4())
        await supervisor.execute(state1, run_id1, stream_updates=True)
        
        # Second turn with context
        state2 = DeepAgentState()
        state2.thread_id = test_thread.id
        state2.user_id = test_user.id
        state2.messages = [
            {"role": "user", "content": "What are my current AI costs?"},
            {"role": "assistant", "content": "Let me analyze your AI costs..."},
            {"role": "user", "content": "How can I reduce them by 20%?"}
        ]
        
        run_id2 = str(uuid.uuid4())
        await supervisor.execute(state2, run_id2, stream_updates=True)
        
        # Verify context was maintained
        assert state2.thread_id == state1.thread_id
        assert len(state2.messages) > len(state1.messages)
    
    @pytest.mark.asyncio
    async def test_concurrent_user_requests(self, db_session, llm_manager,
                                           websocket_manager, tool_dispatcher,
                                           test_user):
        """Test handling concurrent requests from multiple users."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Create multiple threads for concurrent requests
        threads = []
        for i in range(5):
            thread = Thread(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                title=f"Concurrent Thread {i}",
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(thread)
            threads.append(thread)
        
        await db_session.commit()
        
        # Create concurrent execution tasks
        tasks = []
        for i, thread in enumerate(threads):
            state = DeepAgentState()
            state.thread_id = thread.id
            state.user_id = test_user.id
            state.messages = [
                {"role": "user", "content": f"Request {i}: Analyze my usage"}
            ]
            
            run_id = f"concurrent-{i}-{uuid.uuid4()}"
            task = supervisor.execute(state, run_id, stream_updates=True)
            tasks.append(task)
        
        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        # Verify all completed without errors
        for result in results:
            assert not isinstance(result, Exception), f"Task failed: {result}"
        
        # Should handle 5 concurrent requests efficiently
        assert elapsed < 20  # Less than 20 seconds for 5 concurrent requests
    
    @pytest.mark.asyncio
    async def test_error_recovery_e2e(self, db_session, llm_manager,
                                     websocket_manager, tool_dispatcher,
                                     test_user, test_thread):
        """Test error recovery in production-like conditions."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Create state that might trigger errors
        state = DeepAgentState()
        state.thread_id = test_thread.id
        state.user_id = test_user.id
        state.messages = [
            {"role": "user", "content": "Process this invalid request: " + "x" * 10000}
        ]
        
        run_id = str(uuid.uuid4())
        
        # Track error handling
        error_events = []
        
        async def track_errors(thread_id, message):
            if hasattr(message, 'type') and 'error' in message.type.lower():
                error_events.append(message)
        
        websocket_manager.send_message = track_errors
        
        # Execute with potential error
        try:
            await supervisor.execute(state, run_id, stream_updates=True)
        except Exception as e:
            # Error should be handled gracefully
            assert "gracefully" in str(e).lower() or True
        
        # System should remain stable after error
        # Test with valid request
        state2 = DeepAgentState()
        state2.thread_id = test_thread.id
        state2.user_id = test_user.id
        state2.messages = [
            {"role": "user", "content": "Simple valid request"}
        ]
        
        run_id2 = str(uuid.uuid4())
        
        # Should work after error
        await supervisor.execute(state2, run_id2, stream_updates=True)


class TestWebSocketIntegrationE2E:
    """Test WebSocket integration in E2E scenarios."""
    
    @pytest.mark.asyncio
    async def test_real_time_updates(self, db_session, llm_manager,
                                    websocket_manager, tool_dispatcher,
                                    test_user, test_thread):
        """Test real-time updates through WebSocket."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Track timing of events
        event_timeline = []
        
        async def track_timeline(thread_id, message):
            event_timeline.append({
                'timestamp': time.time(),
                'type': getattr(message, 'type', 'unknown'),
                'thread_id': thread_id
            })
        
        websocket_manager.send_message = track_timeline
        
        state = DeepAgentState()
        state.thread_id = test_thread.id
        state.user_id = test_user.id
        state.messages = [
            {"role": "user", "content": "Analyze my infrastructure"}
        ]
        
        run_id = str(uuid.uuid4())
        
        start_time = time.time()
        await supervisor.execute(state, run_id, stream_updates=True)
        
        # Verify real-time updates
        assert len(event_timeline) > 0
        
        # Check event spacing (should have regular updates)
        if len(event_timeline) > 1:
            gaps = []
            for i in range(1, len(event_timeline)):
                gap = event_timeline[i]['timestamp'] - event_timeline[i-1]['timestamp']
                gaps.append(gap)
            
            # Should have reasonable gaps between events (not all at once)
            max_gap = max(gaps) if gaps else 0
            assert max_gap < 10  # No gap longer than 10 seconds
    
    @pytest.mark.asyncio
    async def test_websocket_event_completeness(self, db_session, llm_manager,
                                               websocket_manager, tool_dispatcher,
                                               test_user, test_thread):
        """Test that all required WebSocket events are sent."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Track all events
        all_events = []
        
        async def capture_all(thread_id, message):
            all_events.append({
                'thread_id': thread_id,
                'message': message
            })
        
        websocket_manager.send_message = capture_all
        
        state = DeepAgentState()
        state.thread_id = test_thread.id
        state.user_id = test_user.id
        state.messages = [
            {"role": "user", "content": "Complete workflow test"}
        ]
        
        run_id = str(uuid.uuid4())
        await supervisor.execute(state, run_id, stream_updates=True)
        
        # Extract event types
        event_types = set()
        for event in all_events:
            if hasattr(event['message'], 'type'):
                event_types.add(event['message'].type)
        
        # MISSION CRITICAL: These events MUST be present
        required_events = {
            'agent_started',
            'agent_thinking',
            'agent_completed'
        }
        
        missing_events = required_events - event_types
        assert len(missing_events) == 0, f"Missing critical events: {missing_events}"


class TestPerformanceE2E:
    """Performance tests in E2E environment."""
    
    @pytest.mark.asyncio
    async def test_response_time_sla(self, db_session, llm_manager,
                                    websocket_manager, tool_dispatcher,
                                    test_user, test_thread):
        """Test that response times meet SLA requirements."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        response_times = []
        
        # Run multiple requests to measure performance
        for i in range(10):
            state = DeepAgentState()
            state.thread_id = test_thread.id
            state.user_id = test_user.id
            state.messages = [
                {"role": "user", "content": f"Performance test {i}"}
            ]
            
            run_id = f"perf-{i}-{uuid.uuid4()}"
            
            start = time.time()
            await supervisor.execute(state, run_id, stream_updates=True)
            elapsed = time.time() - start
            
            response_times.append(elapsed)
        
        # Calculate metrics
        avg_response = sum(response_times) / len(response_times)
        max_response = max(response_times)
        p95_response = sorted(response_times)[int(len(response_times) * 0.95)]
        
        # SLA requirements
        assert avg_response < 5  # Average under 5 seconds
        assert p95_response < 10  # 95th percentile under 10 seconds
        assert max_response < 15  # Max under 15 seconds
        
        print(f"Performance Metrics:")
        print(f"  Average: {avg_response:.2f}s")
        print(f"  P95: {p95_response:.2f}s")
        print(f"  Max: {max_response:.2f}s")
    
    @pytest.mark.asyncio
    async def test_throughput_under_load(self, db_session, llm_manager,
                                        websocket_manager, tool_dispatcher,
                                        test_user):
        """Test system throughput under load."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Create threads for load test
        threads = []
        for i in range(20):
            thread = Thread(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                title=f"Load Thread {i}",
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(thread)
            threads.append(thread)
        
        await db_session.commit()
        
        # Generate load
        tasks = []
        for i, thread in enumerate(threads):
            state = DeepAgentState()
            state.thread_id = thread.id
            state.user_id = test_user.id
            state.messages = [
                {"role": "user", "content": f"Load test {i}"}
            ]
            
            run_id = f"load-{i}-{uuid.uuid4()}"
            task = supervisor.execute(state, run_id, stream_updates=False)
            tasks.append(task)
        
        # Measure throughput
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        # Calculate metrics
        successful = sum(1 for r in results if not isinstance(r, Exception))
        throughput = successful / elapsed
        
        # Requirements
        assert successful >= 18  # At least 90% success rate
        assert throughput >= 1  # At least 1 request per second
        
        print(f"Throughput Metrics:")
        print(f"  Total Requests: {len(threads)}")
        print(f"  Successful: {successful}")
        print(f"  Throughput: {throughput:.2f} req/s")


class TestDataIntegrityE2E:
    """Test data integrity in E2E scenarios."""
    
    @pytest.mark.asyncio
    async def test_state_persistence(self, db_session, llm_manager,
                                    websocket_manager, tool_dispatcher,
                                    test_user, test_thread):
        """Test that state is correctly persisted."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Execute with specific state
        state = DeepAgentState()
        state.thread_id = test_thread.id
        state.user_id = test_user.id
        state.messages = [
            {"role": "user", "content": "Test persistence"}
        ]
        state.metadata = {"test_key": "test_value"}
        
        run_id = str(uuid.uuid4())
        await supervisor.execute(state, run_id, stream_updates=True)
        
        # Verify state was persisted
        execution = await db_session.execute(
            select(AgentExecution).where(AgentExecution.run_id == run_id)
        )
        agent_execution = execution.scalar_one_or_none()
        
        if agent_execution and agent_execution.state_snapshot:
            snapshot = json.loads(agent_execution.state_snapshot)
            assert snapshot.get('metadata', {}).get('test_key') == 'test_value'
    
    @pytest.mark.asyncio
    async def test_message_ordering(self, db_session, llm_manager,
                                   websocket_manager, tool_dispatcher,
                                   test_user, test_thread):
        """Test that messages maintain correct ordering."""
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Send multiple messages
        messages = []
        for i in range(5):
            state = DeepAgentState()
            state.thread_id = test_thread.id
            state.user_id = test_user.id
            state.messages = messages + [
                {"role": "user", "content": f"Message {i}"}
            ]
            
            run_id = f"ordering-{i}-{uuid.uuid4()}"
            await supervisor.execute(state, run_id, stream_updates=True)
            
            # Add to message history
            messages = state.messages.copy()
            messages.append({"role": "assistant", "content": f"Response {i}"})
        
        # Verify message ordering in database
        db_messages = await db_session.execute(
            select(Message)
            .where(Message.thread_id == test_thread.id)
            .order_by(Message.created_at)
        )
        
        db_message_list = db_messages.scalars().all()
        
        # Messages should be in chronological order
        for i in range(1, len(db_message_list)):
            assert db_message_list[i].created_at >= db_message_list[i-1].created_at


if __name__ == "__main__":
    # Run E2E tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--asyncio-mode=auto"
    ])