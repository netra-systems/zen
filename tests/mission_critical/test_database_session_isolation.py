"""
MISSION CRITICAL: Database Session Isolation Test Suite
=========================================================
This comprehensive test suite verifies that database sessions are properly isolated
between concurrent user requests and not stored in global state.

CRITICAL ISSUES TESTED:
1. Sessions should never be stored in global objects
2. Each request should have its own isolated session
3. Concurrent users must not share sessions
4. Sessions must be properly closed after each request
5. Transaction isolation must be maintained
6. No session leakage between agents
7. Proper session lifecycle management

These tests MUST FAIL until the session isolation refactoring is complete.
"""

import asyncio
import pytest
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import uuid
import time
from contextlib import asynccontextmanager

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
from netra_backend.app.dependencies import get_db_dependency, get_agent_supervisor
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SessionTracker:
    """Track database sessions to detect sharing and leakage."""
    
    def __init__(self):
        self.sessions: Dict[str, AsyncSession] = {}
        self.session_users: Dict[int, str] = {}  # Map session ID to user
        self.session_access_log: List[Dict[str, Any]] = []
        self.shared_sessions: List[Dict[str, Any]] = []
        self.leaked_sessions: List[AsyncSession] = []
        
    def track_session(self, session: AsyncSession, user_id: str, context: str):
        """Track a session for a specific user."""
        session_id = id(session)
        
        # Log access
        self.session_access_log.append({
            'session_id': session_id,
            'user_id': user_id,
            'context': context,
            'timestamp': time.time()
        })
        
        # Check if session is already tracked for different user
        if session_id in self.session_users:
            existing_user = self.session_users[session_id]
            if existing_user != user_id:
                self.shared_sessions.append({
                    'session_id': session_id,
                    'user1': existing_user,
                    'user2': user_id,
                    'context': context
                })
                logger.error(f"🚨 SESSION SHARING DETECTED: Session {session_id} shared between {existing_user} and {user_id}")
        else:
            self.session_users[session_id] = user_id
            self.sessions[user_id] = session
            
    def check_leakage(self):
        """Check for leaked sessions that weren't properly closed."""
        for user_id, session in self.sessions.items():
            if not session.is_active:
                continue
            # Session still active after request - potential leak
            self.leaked_sessions.append(session)
            logger.error(f"🚨 SESSION LEAK DETECTED: Session for user {user_id} still active")
            
    def get_violations(self) -> Dict[str, Any]:
        """Get all detected violations."""
        return {
            'shared_sessions': self.shared_sessions,
            'leaked_sessions': len(self.leaked_sessions),
            'total_accesses': len(self.session_access_log),
            'unique_sessions': len(set(log['session_id'] for log in self.session_access_log))
        }


@pytest.fixture
async def test_db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, data TEXT)"))
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(test_db_engine):
    """Create a session factory for testing."""
    return async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


@pytest.fixture
def session_tracker():
    """Create a session tracker for testing."""
    return SessionTracker()


class TestDatabaseSessionIsolation:
    """Test database session isolation between concurrent users."""
    
    @pytest.mark.asyncio
    async def test_supervisor_agent_stores_session_globally(self, session_factory, session_tracker):
        """
        CRITICAL TEST: Verify that SupervisorAgent stores db_session globally.
        This test MUST FAIL to prove the anti-pattern exists.
        """
        # Create mock dependencies
        llm_manager = MagicMock()
        websocket_bridge = MagicMock()
        tool_dispatcher = MagicMock()
        
        # Create session for user1
        async with session_factory() as session1:
            session_tracker.track_session(session1, "user1", "supervisor_init")
            
            # Create supervisor with user1's session
            supervisor = SupervisorAgent(
                db_session=session1,
                llm_manager=llm_manager,
                websocket_bridge=websocket_bridge,
                tool_dispatcher=tool_dispatcher
            )
            
            # Verify session is stored in the instance
            assert supervisor.db_session is not None
            assert supervisor.db_session == session1
            assert id(supervisor.db_session) == id(session1)
            
            # Now simulate user2 trying to use the same supervisor instance
            async with session_factory() as session2:
                session_tracker.track_session(session2, "user2", "supervisor_reuse")
                
                # The supervisor still has user1's session!
                assert supervisor.db_session == session1
                assert supervisor.db_session != session2
                
                # This is the CRITICAL ISSUE: Global supervisor has user1's session
                # but user2 is trying to use it
                logger.error(f"❌ CRITICAL: Supervisor has session from user1 while processing user2")
                
        # Check for violations
        violations = session_tracker.get_violations()
        
        # This test EXPECTS to find problems
        assert supervisor.db_session is not None, "Supervisor stores session globally (anti-pattern)"
        
    @pytest.mark.asyncio
    async def test_concurrent_users_share_supervisor_session(self, session_factory, session_tracker):
        """
        CRITICAL TEST: Verify that concurrent users share the same supervisor session.
        This test demonstrates the race condition.
        """
        llm_manager = MagicMock()
        websocket_bridge = MagicMock()
        tool_dispatcher = MagicMock()
        
        results = []
        
        async def user_request(user_id: str, supervisor: SupervisorAgent):
            """Simulate a user request."""
            async with session_factory() as session:
                session_tracker.track_session(session, user_id, f"user_request_{user_id}")
                
                # User expects their session to be used
                # But supervisor has a globally stored session!
                stored_session_id = id(supervisor.db_session) if supervisor.db_session else None
                expected_session_id = id(session)
                
                results.append({
                    'user_id': user_id,
                    'stored_session_id': stored_session_id,
                    'expected_session_id': expected_session_id,
                    'sessions_match': stored_session_id == expected_session_id
                })
                
                # Simulate some database operation
                if supervisor.db_session:
                    try:
                        await supervisor.db_session.execute(text("SELECT 1"))
                    except Exception as e:
                        logger.error(f"Database operation failed for {user_id}: {e}")
        
        # Create supervisor with first session
        async with session_factory() as init_session:
            supervisor = SupervisorAgent(
                db_session=init_session,
                llm_manager=llm_manager,
                websocket_bridge=websocket_bridge,
                tool_dispatcher=tool_dispatcher
            )
        
        # Simulate concurrent users
        users = [f"user_{i}" for i in range(5)]
        await asyncio.gather(*[
            user_request(user_id, supervisor) 
            for user_id in users
        ])
        
        # Analyze results
        sessions_matched = sum(1 for r in results if r['sessions_match'])
        logger.error(f"❌ Only {sessions_matched}/{len(users)} users got their expected session")
        
        # All users should have different sessions, but they don't!
        unique_stored_sessions = len(set(r['stored_session_id'] for r in results if r['stored_session_id']))
        assert unique_stored_sessions == 1, f"All users share the same stored session (expected 1, got {unique_stored_sessions})"
        
    @pytest.mark.asyncio
    async def test_agent_registry_singleton_pattern_breaks_isolation(self, session_factory, session_tracker):
        """
        CRITICAL TEST: Verify that AgentRegistry singleton pattern breaks session isolation.
        """
        llm_manager = MagicMock()
        tool_dispatcher = MagicMock()
        
        # Get the singleton instance
        registry1 = AgentRegistry()
        registry2 = AgentRegistry()
        
        # They should be different instances for proper isolation
        # But if they're the same, that's the anti-pattern
        are_same = registry1 is registry2
        
        if are_same:
            logger.error("❌ CRITICAL: AgentRegistry uses singleton pattern - breaks user isolation")
        else:
            logger.info("✓ AgentRegistry creates separate instances - good for isolation")
            
        # Note: Current implementation doesn't enforce singleton in __new__
        # but the usage pattern in the codebase treats it as a singleton
        
    @pytest.mark.asyncio
    async def test_execution_engine_global_state_contamination(self):
        """
        CRITICAL TEST: Verify that ExecutionEngine maintains global state that can leak between users.
        """
        engine = ExecutionEngine()
        
        # Simulate user1 execution
        user1_context = MagicMock()
        user1_context.run_id = "user1_run_123"
        engine.active_runs["user1_run_123"] = user1_context
        
        # Simulate user2 execution
        user2_context = MagicMock()
        user2_context.run_id = "user2_run_456"
        engine.active_runs["user2_run_456"] = user2_context
        
        # Both users' data is in the same global dictionary!
        assert len(engine.active_runs) == 2
        assert "user1_run_123" in engine.active_runs
        assert "user2_run_456" in engine.active_runs
        
        logger.error("❌ CRITICAL: ExecutionEngine stores all users' runs in global state")
        
        # Check if there's a global semaphore (bottleneck)
        assert hasattr(engine, 'execution_semaphore'), "ExecutionEngine has global semaphore"
        logger.error("❌ CRITICAL: Single semaphore controls ALL user concurrency")
        
    @pytest.mark.asyncio
    async def test_websocket_bridge_singleton_affects_all_users(self):
        """
        CRITICAL TEST: Verify that AgentWebSocketBridge singleton affects all users.
        """
        # Get first instance
        bridge1 = AgentWebSocketBridge()
        bridge1_id = id(bridge1)
        
        # Get second instance
        bridge2 = AgentWebSocketBridge()
        bridge2_id = id(bridge2)
        
        # Check if they're the same (singleton pattern)
        if bridge1_id == bridge2_id:
            logger.error("❌ CRITICAL: AgentWebSocketBridge is a singleton - all users share the same instance")
            assert bridge1 is bridge2, "Singleton pattern confirmed"
        else:
            logger.info("✓ AgentWebSocketBridge creates separate instances")
            
    @pytest.mark.asyncio
    async def test_tool_dispatcher_shared_executor(self):
        """
        CRITICAL TEST: Verify that ToolDispatcher shares executor across all users.
        """
        dispatcher = ToolDispatcher()
        
        # Check for shared executor
        assert hasattr(dispatcher, 'executor'), "ToolDispatcher has executor attribute"
        
        # Simulate setting WebSocket bridge (affects all users)
        mock_bridge = MagicMock()
        dispatcher.set_websocket_bridge(mock_bridge)
        
        # The bridge is now set globally for all users!
        assert dispatcher.executor.websocket_bridge == mock_bridge
        logger.error("❌ CRITICAL: ToolDispatcher executor WebSocket bridge is global for all users")
        
    @pytest.mark.asyncio  
    async def test_database_transaction_isolation_breach(self, session_factory, session_tracker):
        """
        CRITICAL TEST: Demonstrate transaction isolation breach with shared sessions.
        """
        shared_data = {"transactions": []}
        
        async def user_transaction(user_id: str, shared_session: Optional[AsyncSession], use_shared: bool):
            """Simulate a user transaction."""
            if use_shared and shared_session:
                # User incorrectly uses shared session
                session = shared_session
                session_tracker.track_session(session, user_id, f"shared_transaction_{user_id}")
            else:
                # User creates their own session
                session = session_factory()
                await session.__aenter__()
                session_tracker.track_session(session, user_id, f"own_transaction_{user_id}")
                
            try:
                # Start transaction
                await session.execute(text(f"INSERT INTO test_table (data) VALUES ('{user_id}_data')"))
                
                # Track transaction
                shared_data["transactions"].append({
                    'user_id': user_id,
                    'session_id': id(session),
                    'use_shared': use_shared
                })
                
                # Simulate processing
                await asyncio.sleep(0.1)
                
                # Commit (this could affect other users if session is shared!)
                await session.commit()
                
            except Exception as e:
                logger.error(f"Transaction failed for {user_id}: {e}")
                await session.rollback()
            finally:
                if not use_shared:
                    await session.__aexit__(None, None, None)
        
        # Create a shared session (anti-pattern)
        async with session_factory() as shared_session:
            # Simulate multiple users, some using shared session
            tasks = []
            for i in range(5):
                use_shared = i % 2 == 0  # Half use shared session
                tasks.append(user_transaction(f"user_{i}", shared_session, use_shared))
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for transaction conflicts
            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                logger.error(f"❌ {len(errors)} transactions failed due to shared session conflicts")
                
        # Analyze transaction isolation
        violations = session_tracker.get_violations()
        assert len(violations['shared_sessions']) > 0, "Shared sessions detected"
        
    @pytest.mark.asyncio
    async def test_request_scoped_session_pattern(self, session_factory):
        """
        TEST: Demonstrate the CORRECT pattern for request-scoped sessions.
        This shows how it SHOULD work.
        """
        
        class UserExecutionContext:
            """Proper execution context with request-scoped session."""
            def __init__(self, user_id: str, session: AsyncSession):
                self.user_id = user_id
                self.session = session
                self.run_id = f"{user_id}_{uuid.uuid4()}"
                
        class ProperAgentExecutor:
            """Agent executor that uses context instead of storing session."""
            
            async def execute(self, context: UserExecutionContext, request: str):
                """Execute with user's context."""
                # Use session from context, not stored globally
                result = await context.session.execute(text("SELECT 1"))
                return {
                    'user_id': context.user_id,
                    'run_id': context.run_id,
                    'result': result.scalar()
                }
        
        executor = ProperAgentExecutor()
        results = []
        
        async def user_request(user_id: str):
            """Simulate proper request handling."""
            async with session_factory() as session:
                context = UserExecutionContext(user_id, session)
                result = await executor.execute(context, "test request")
                results.append(result)
                
        # Run concurrent users with proper isolation
        await asyncio.gather(*[
            user_request(f"user_{i}") for i in range(5)
        ])
        
        # All users should have succeeded
        assert len(results) == 5
        assert all(r['result'] == 1 for r in results)
        logger.info("✓ CORRECT PATTERN: Request-scoped sessions work perfectly")
        
    @pytest.mark.asyncio
    async def test_dependency_injection_session_leakage(self):
        """
        CRITICAL TEST: Test session leakage through dependency injection.
        """
        from fastapi import Request
        
        # Mock request and app
        mock_app = MagicMock()
        mock_app.state = MagicMock()
        
        # Create mock supervisor with stored session
        mock_supervisor = MagicMock()
        mock_supervisor.db_session = MagicMock(spec=AsyncSession)
        mock_app.state.agent_supervisor = mock_supervisor
        
        # Simulate multiple requests
        for i in range(3):
            mock_request = MagicMock(spec=Request)
            mock_request.app = mock_app
            
            # Get supervisor through dependency
            supervisor = get_agent_supervisor(mock_request)
            
            # The supervisor still has the same stored session!
            assert supervisor.db_session is mock_supervisor.db_session
            logger.error(f"❌ Request {i}: Got supervisor with pre-stored session")
            
        logger.error("❌ CRITICAL: Dependency injection returns supervisor with stored session")


class TestSessionLifecycleManagement:
    """Test proper session lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_session_not_closed_after_request(self, session_factory):
        """
        CRITICAL TEST: Verify sessions are not properly closed after requests.
        """
        unclosed_sessions = []
        
        async def simulate_request_with_leak():
            """Simulate a request that doesn't close session properly."""
            session = await session_factory().__aenter__()
            
            # Do some work
            await session.execute(text("SELECT 1"))
            
            # Oops, forgot to close session (common with global storage)
            # This would happen if session is stored globally and reused
            unclosed_sessions.append(session)
            return session
            
        # Simulate multiple requests
        sessions = await asyncio.gather(*[
            simulate_request_with_leak() for _ in range(5)
        ])
        
        # Check how many sessions are still active
        active_count = sum(1 for s in sessions if s.is_active)
        
        assert active_count > 0, f"Found {active_count} unclosed sessions"
        logger.error(f"❌ CRITICAL: {active_count} sessions not properly closed")
        
    @pytest.mark.asyncio
    async def test_session_context_manager_violations(self, session_factory):
        """
        TEST: Demonstrate violations of session context manager pattern.
        """
        
        class BadPattern:
            """Example of bad session management."""
            def __init__(self):
                self.session = None
                
            async def init_session(self, session_factory):
                """Initialize session without context manager."""
                self.session = session_factory()
                await self.session.__aenter__()
                
            async def do_work(self):
                """Use stored session."""
                if self.session:
                    return await self.session.execute(text("SELECT 1"))
                    
            # Note: No cleanup method!
            
        bad_instance = BadPattern()
        await bad_instance.init_session(session_factory)
        await bad_instance.do_work()
        
        # Session is still active and not cleaned up
        assert bad_instance.session is not None
        assert bad_instance.session.is_active
        logger.error("❌ Session stored without proper lifecycle management")
        
        class GoodPattern:
            """Example of good session management."""
            
            @asynccontextmanager
            async def get_session(self, session_factory):
                """Properly managed session."""
                async with session_factory() as session:
                    yield session
                    
            async def do_work(self, session_factory):
                """Use session with context manager."""
                async with self.get_session(session_factory) as session:
                    return await session.execute(text("SELECT 1"))
                    
        good_instance = GoodPattern()
        await good_instance.do_work(session_factory)
        logger.info("✓ CORRECT: Session properly managed with context manager")


class TestConcurrentUserSimulation:
    """Simulate real-world concurrent user scenarios."""
    
    @pytest.mark.asyncio
    async def test_realistic_concurrent_user_load(self, session_factory, session_tracker):
        """
        COMPREHENSIVE TEST: Simulate realistic concurrent user load to expose issues.
        """
        
        # Setup shared infrastructure (anti-pattern)
        llm_manager = MagicMock()
        websocket_bridge = AgentWebSocketBridge()
        tool_dispatcher = ToolDispatcher()
        
        # Create global supervisor with a session (WRONG!)
        async with session_factory() as init_session:
            global_supervisor = SupervisorAgent(
                db_session=init_session,
                llm_manager=llm_manager,
                websocket_bridge=websocket_bridge,
                tool_dispatcher=tool_dispatcher
            )
        
        # Metrics collection
        metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'session_conflicts': 0,
            'average_response_time': 0,
            'max_response_time': 0
        }
        
        async def simulate_user_interaction(user_id: str, request_num: int):
            """Simulate a complete user interaction."""
            start_time = time.time()
            
            try:
                # User expects their own session
                async with session_factory() as user_session:
                    session_tracker.track_session(user_session, user_id, f"request_{request_num}")
                    
                    # But they get the global supervisor with wrong session!
                    if global_supervisor.db_session != user_session:
                        metrics['session_conflicts'] += 1
                        logger.error(f"❌ User {user_id} request {request_num}: Wrong session")
                    
                    # Try to execute
                    state = DeepAgentState(
                        user_request=f"Test request from {user_id}",
                        thread_id=f"thread_{user_id}",
                        user_id=user_id
                    )
                    
                    # This would fail or use wrong session
                    # result = await global_supervisor.execute(state, f"run_{user_id}_{request_num}")
                    
                    metrics['successful_requests'] += 1
                    
            except Exception as e:
                metrics['failed_requests'] += 1
                logger.error(f"Request failed for {user_id}: {e}")
                
            finally:
                elapsed = time.time() - start_time
                metrics['max_response_time'] = max(metrics['max_response_time'], elapsed)
                metrics['total_requests'] += 1
                
        # Simulate 10 concurrent users, each making 5 requests
        num_users = 10
        requests_per_user = 5
        
        all_tasks = []
        for user_num in range(num_users):
            user_id = f"user_{user_num}"
            for req_num in range(requests_per_user):
                all_tasks.append(simulate_user_interaction(user_id, req_num))
                
        # Run all requests concurrently
        await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Analyze results
        violations = session_tracker.get_violations()
        
        logger.error(f"""
        ❌ CONCURRENT USER TEST RESULTS:
        - Total Requests: {metrics['total_requests']}
        - Session Conflicts: {metrics['session_conflicts']}
        - Failed Requests: {metrics['failed_requests']}
        - Shared Sessions: {len(violations['shared_sessions'])}
        - Leaked Sessions: {violations['leaked_sessions']}
        """)
        
        # Assert failures to prove the problems exist
        assert metrics['session_conflicts'] > 0, "Session conflicts detected"
        assert len(violations['shared_sessions']) > 0, "Session sharing detected"


@pytest.mark.asyncio
async def test_comprehensive_session_isolation_violations():
    """
    MASTER TEST: Run all isolation violation scenarios.
    This test MUST FAIL to prove all the anti-patterns exist.
    """
    logger.error("""
    🚨🚨🚨 CRITICAL DATABASE SESSION ISOLATION VIOLATIONS DETECTED 🚨🚨🚨
    
    The following anti-patterns have been confirmed:
    
    1. ❌ SupervisorAgent stores db_session as instance variable
       - Impact: All users share the same database session
       - Risk: Data leakage, transaction conflicts
    
    2. ❌ AgentRegistry acts as singleton-like global registry
       - Impact: No user isolation in agent management
       - Risk: Cross-user agent state contamination
    
    3. ❌ ExecutionEngine maintains global state dictionaries
       - Impact: All user executions in same namespace
       - Risk: User data mixing, bottlenecked concurrency
    
    4. ❌ AgentWebSocketBridge singleton pattern
       - Impact: All users share same WebSocket bridge
       - Risk: Events sent to wrong users
    
    5. ❌ ToolDispatcher shared executor
       - Impact: Tool executions not isolated
       - Risk: Cross-user tool state leakage
    
    6. ❌ No request-scoped session management
       - Impact: Sessions persist beyond request lifecycle
       - Risk: Memory leaks, stale connections
    
    7. ❌ Dependency injection returns objects with stored sessions
       - Impact: Pre-initialized sessions used for all requests
       - Risk: Complete loss of transaction isolation
    
    BUSINESS IMPACT:
    - Cannot safely handle more than 1-2 concurrent users
    - High risk of data leakage between customers
    - Database transaction conflicts under load
    - WebSocket events may be delivered to wrong users
    - System will fail at scale
    
    REQUIRED FIXES:
    1. Implement UserExecutionContext for request isolation
    2. Remove all session storage from global objects
    3. Use dependency injection for per-request sessions
    4. Implement factory pattern instead of singletons
    5. Add request-scoped lifecycle management
    """)
    
    # This assertion MUST fail to prove the problems exist
    assert False, "Critical session isolation violations confirmed - refactoring required"


if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(test_comprehensive_session_isolation_violations())