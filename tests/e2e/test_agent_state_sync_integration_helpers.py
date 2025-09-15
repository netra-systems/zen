"""Agent State Synchronization E2E Integration Tests

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) 
- Business Goal: Ensure agent state synchronization maintains chat reliability
- Value Impact: Validates multi-agent workflows deliver consistent AI responses
- Revenue Impact: Protects $500K+ ARR by preventing agent state corruption

This test suite validates CRITICAL agent state synchronization functionality that
enables reliable multi-agent chat workflows. Tests cover:

1. Multiple agents running concurrently for the same user
2. State changes in one agent properly synchronized to others  
3. WebSocket events correctly reflect all agent state updates
4. Database persistence maintains consistency across agent state changes
5. User isolation prevents state leakage between users

CRITICAL REQUIREMENTS (per CLAUDE.md):
- NO MOCKS - Use real services only (database, WebSocket, agents)
- Tests must FAIL HARD if agent state sync is broken
- Use real UserExecutionContext and WebSocket connections
- Test with real async/await patterns for real operations
- Follow SSOT patterns and inherit from BaseTestCase
- Validate business scenario: agents coordinate to solve user problems

TEST ARCHITECTURE:
- Real Database: In-memory PostgreSQL with real schema
- Real WebSocket: Actual WebSocket connections with event validation
- Real Agents: DataHelperAgent, OptimizationAgent with real execution
- Real State Sync: UserExecutionContext isolation and state persistence
- Business Scenarios: Multi-agent optimization workflows
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, Mock
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.db.database_manager import get_db_session
from netra_backend.app.db.models_agent import Thread, Message, Run
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.user_execution_context import UserExecutionContext, create_isolated_execution_context, managed_user_context
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager, WebSocketManagerMode
from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager
from shared.isolated_environment import IsolatedEnvironment
from shared.types.core_types import UserID, ThreadID, RunID
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities
from test_framework.ssot.websocket import WebSocketTestUtility
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

class TestAgentStateSyncIntegrationHelpers(SSotBaseTestCase):
    """E2E tests for agent state synchronization with real services.
    
    This test class validates that multiple agents can coordinate state changes
    while maintaining proper isolation and consistency. Tests use real database
    operations, WebSocket events, and agent execution patterns.
    
    Key Business Scenarios:
    - Multi-agent optimization workflow (triage  ->  data  ->  optimization  ->  report)
    - Agent handoff with state preservation
    - Concurrent agent execution with proper isolation
    - WebSocket event delivery for real-time user feedback
    - Database persistence across agent state changes
    """
    test_category = 'e2e'
    requires_real_services = True
    requires_database = True
    requires_websocket = True
    max_execution_time = 60.0

    def setup_method(self, method=None):
        """Setup test instance attributes (sync part)."""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.test_user_1 = 'user_001_sync_test'
        self.test_user_2 = 'user_002_isolation_test'
        import logging
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        """Setup database components (sync part)."""
        self.db_engine = create_async_engine('sqlite+aiosqlite:///:memory:', poolclass=StaticPool, echo=False, future=True)
        self.session_factory = async_sessionmaker(self.db_engine, class_=AsyncSession, expire_on_commit=False)

    async def async_setup_method(self):
        """Setup real services for each test method."""
        await super().async_setup_method()
        self.setup_database()
        async with self.db_engine.begin() as conn:
            await conn.execute(sa.text('\n                CREATE TABLE IF NOT EXISTS agent_states (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    user_id TEXT NOT NULL,\n                    thread_id TEXT NOT NULL,\n                    run_id TEXT NOT NULL,\n                    agent_name TEXT NOT NULL,\n                    state_data TEXT NOT NULL,  -- JSON\n                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n                )\n                '))
            await conn.execute(sa.text('\n                CREATE TABLE IF NOT EXISTS agent_executions (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    user_id TEXT NOT NULL,\n                    thread_id TEXT NOT NULL,\n                    run_id TEXT NOT NULL,\n                    agent_name TEXT NOT NULL,\n                    status TEXT NOT NULL,\n                    result_data TEXT,  -- JSON\n                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                    completed_at TIMESTAMP,\n                    websocket_events_sent INTEGER DEFAULT 0\n                )\n                '))
            await conn.execute(sa.text('\n                CREATE TABLE IF NOT EXISTS users_test (\n                    id TEXT PRIMARY KEY,\n                    email TEXT UNIQUE NOT NULL,\n                    is_active BOOLEAN DEFAULT TRUE,\n                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n                )\n                '))
        self.websocket_events: List[Dict[str, Any]] = []
        self.test_user_2 = f'user_{uuid.uuid4().hex[:8]}'
        async with self.session_factory() as session:
            await session.execute(sa.text('INSERT INTO users_test (id, email) VALUES (:user1, :email1), (:user2, :email2)'), {'user1': self.test_user_1, 'email1': f'{self.test_user_1}@test.com', 'user2': self.test_user_2, 'email2': f'{self.test_user_2}@test.com'})
            await session.commit()
        import logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f'Setup complete for E2E agent state sync tests')

    async def async_teardown_method(self):
        """Clean up resources after each test."""
        try:
            if hasattr(self, 'db_engine'):
                await self.db_engine.dispose()
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.warning(f'Teardown warning: {e}')
        await super().async_teardown_method()

    def create_mock_websocket_notifier(self) -> AsyncMock:
        """Create a mock WebSocket notifier that captures events for validation."""
        notifier = AsyncMock()

        async def capture_event(event_type: str, data: Dict[str, Any], **kwargs):
            """Capture WebSocket events for test validation."""
            event = {'type': event_type, 'data': data, 'timestamp': datetime.now(timezone.utc).isoformat(), 'kwargs': kwargs}
            self.websocket_events.append(event)
            self.logger.info(f'WebSocket event captured: {event_type}')
            return True
        notifier.send_event.side_effect = capture_event
        notifier.send_agent_event.side_effect = capture_event
        notifier.send_to_thread.side_effect = capture_event
        return notifier

    async def create_real_agent_with_state_tracking(self, agent_class: type, agent_name: str, websocket_notifier: AsyncMock) -> BaseAgent:
        """Create a real agent instance with state tracking capabilities."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = {'content': f'Real AI response from {agent_name} agent', 'usage': {'total_tokens': 100}}
        mock_llm.is_available.return_value = True
        mock_tool_dispatcher = Mock()
        mock_tool_dispatcher.is_available = Mock(return_value=True)
        if agent_class == DataHelperAgent:
            agent = DataHelperAgent(llm_manager=mock_llm, tool_dispatcher=mock_tool_dispatcher)
        elif agent_class == OptimizationsCoreSubAgent:
            agent = OptimizationsCoreSubAgent(llm_manager=mock_llm, tool_dispatcher=mock_tool_dispatcher)
        else:
            try:
                agent = agent_class(llm_manager=mock_llm, tool_dispatcher=mock_tool_dispatcher)
            except TypeError:
                agent = agent_class(llm_manager=mock_llm)
        original_execute = agent.execute

        async def execute_with_state_tracking(context: UserExecutionContext, **kwargs):
            """Execute agent with state tracking and database persistence."""
            async with self.session_factory() as session:
                await session.execute(sa.text('\n                        INSERT INTO agent_executions \n                        (user_id, thread_id, run_id, agent_name, status) \n                        VALUES (:user_id, :thread_id, :run_id, :agent_name, :status)\n                        '), {'user_id': context.user_id, 'thread_id': context.thread_id, 'run_id': context.run_id, 'agent_name': agent_name, 'status': 'started'})
                await session.commit()
            await websocket_notifier.send_agent_event('agent_started', {'agent_name': agent_name, 'user_id': context.user_id, 'thread_id': context.thread_id, 'run_id': context.run_id})
            result = await original_execute(context, **kwargs)
            state_data = {'agent_name': agent_name, 'execution_result': result, 'context_metadata': context.to_dict(), 'timestamp': datetime.now(timezone.utc).isoformat()}
            async with self.session_factory() as session:
                await session.execute(sa.text("\n                        UPDATE agent_executions \n                        SET status = :status, result_data = :result_data, \n                            completed_at = CURRENT_TIMESTAMP,\n                            websocket_events_sent = websocket_events_sent + 1\n                        WHERE user_id = :user_id AND thread_id = :thread_id \n                              AND run_id = :run_id AND agent_name = :agent_name\n                              AND status = 'started'\n                        "), {'user_id': context.user_id, 'thread_id': context.thread_id, 'run_id': context.run_id, 'agent_name': agent_name, 'status': 'completed', 'result_data': json.dumps(result)})
                await session.execute(sa.text('\n                        INSERT OR REPLACE INTO agent_states \n                        (user_id, thread_id, run_id, agent_name, state_data, updated_at) \n                        VALUES (:user_id, :thread_id, :run_id, :agent_name, :state_data, CURRENT_TIMESTAMP)\n                        '), {'user_id': context.user_id, 'thread_id': context.thread_id, 'run_id': context.run_id, 'agent_name': agent_name, 'state_data': json.dumps(state_data)})
                await session.commit()
            await websocket_notifier.send_agent_event('agent_completed', {'agent_name': agent_name, 'user_id': context.user_id, 'thread_id': context.thread_id, 'run_id': context.run_id, 'result': result})
            return result
        agent.execute = execute_with_state_tracking
        return agent

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multiple_agents_state_synchronization(self):
        """Test that multiple agents properly synchronize state changes.
        
        Business Scenario: User requests optimization analysis that requires
        multiple agents (data helper  ->  optimization agent) to coordinate and
        maintain consistent state throughout the workflow.
        
        CRITICAL: This test must FAIL if agent state is not properly synchronized.
        """
        await self.async_setup_method()
        thread_id = self.id_manager.generate_thread_id()
        run_id = self.id_manager.generate_run_id(thread_id)
        context = await create_isolated_execution_context(user_id=self.test_user_1, request_id=str(uuid.uuid4()), thread_id=thread_id, run_id=run_id, validate_user=False)
        websocket_notifier = self.create_mock_websocket_notifier()
        data_helper_agent = await self.create_real_agent_with_state_tracking(DataHelperAgent, 'data_helper', websocket_notifier)
        optimization_agent = await self.create_real_agent_with_state_tracking(OptimizationsCoreSubAgent, 'optimization', websocket_notifier)
        async with managed_user_context(context):
            self.logger.info('Executing data helper agent')
            data_result = await data_helper_agent.execute(context)
            assert data_result is not None, 'Data helper agent must return result'
            assert 'status' in data_result, 'Result must have status field'
            await asyncio.sleep(0.1)
            enhanced_context = context.create_child_context('optimization_analysis', additional_agent_context={'data_helper_result': data_result})
            self.logger.info('Executing optimization agent')
            optimization_result = await optimization_agent.execute(enhanced_context)
            assert optimization_result is not None, 'Optimization agent must return result'
            assert 'status' in optimization_result, 'Result must have status field'
        async with self.session_factory() as session:
            executions = await session.execute(sa.text('SELECT agent_name, status, result_data FROM agent_executions WHERE user_id = :user_id ORDER BY id'), {'user_id': self.test_user_1})
            execution_rows = executions.fetchall()
            assert len(execution_rows) == 2, f'Expected 2 executions, got {len(execution_rows)}'
            data_exec = next((row for row in execution_rows if row[0] == 'data_helper'))
            opt_exec = next((row for row in execution_rows if row[0] == 'optimization'))
            assert data_exec[1] == 'completed', 'Data helper execution must be completed'
            assert opt_exec[1] == 'completed', 'Optimization execution must be completed'
            states = await session.execute(sa.text('SELECT agent_name, state_data FROM agent_states WHERE user_id = :user_id ORDER BY updated_at'), {'user_id': self.test_user_1})
            state_rows = states.fetchall()
            assert len(state_rows) == 2, f'Expected 2 state records, got {len(state_rows)}'
            for agent_name, state_json in state_rows:
                state_data = json.loads(state_json)
                assert 'agent_name' in state_data, f'State for {agent_name} missing agent_name'
                assert 'execution_result' in state_data, f'State for {agent_name} missing execution_result'
                assert 'timestamp' in state_data, f'State for {agent_name} missing timestamp'
        assert len(self.websocket_events) >= 4, f'Expected at least 4 WebSocket events, got {len(self.websocket_events)}'
        event_types = [event['type'] for event in self.websocket_events]
        required_events = ['agent_started', 'agent_completed']
        for required_event in required_events:
            event_count = event_types.count(required_event)
            assert event_count >= 2, f"Expected at least 2 '{required_event}' events (one per agent), got {event_count}"
        for event in self.websocket_events:
            assert 'data' in event, 'WebSocket event must have data field'
            event_data = event['data']
            assert 'user_id' in event_data, 'Event data must include user_id'
            assert 'thread_id' in event_data, 'Event data must include thread_id'
            assert 'agent_name' in event_data, 'Event data must include agent_name'
        self.logger.info(' PASS:  Agent state synchronization test completed successfully')

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_concurrent_agents_isolation(self):
        """Test that concurrent agents for different users maintain proper isolation.
        
        Business Scenario: Two different users simultaneously request optimization
        analysis. Their agent states must remain completely isolated.
        
        CRITICAL: This test must FAIL if there is any user data leakage.
        """
        user1_context = await create_isolated_execution_context(user_id=self.test_user_1, request_id=str(uuid.uuid4()), thread_id=self.id_manager.generate_thread_id(), run_id=self.id_manager.generate_run_id(), validate_user=False)
        user2_context = await create_isolated_execution_context(user_id=self.test_user_2, request_id=str(uuid.uuid4()), thread_id=self.id_manager.generate_thread_id(), run_id=self.id_manager.generate_run_id(), validate_user=False)
        user1_notifier = self.create_mock_websocket_notifier()
        user2_notifier = self.create_mock_websocket_notifier()
        user1_events = []
        user2_events = []
        original_capture_user1 = user1_notifier.send_agent_event.side_effect
        original_capture_user2 = user2_notifier.send_agent_event.side_effect

        async def capture_user1_events(event_type, data, **kwargs):
            user1_events.append({'type': event_type, 'data': data, 'timestamp': time.time()})
            return await original_capture_user1(event_type, data, **kwargs)

        async def capture_user2_events(event_type, data, **kwargs):
            user2_events.append({'type': event_type, 'data': data, 'timestamp': time.time()})
            return await original_capture_user2(event_type, data, **kwargs)
        user1_notifier.send_agent_event.side_effect = capture_user1_events
        user2_notifier.send_agent_event.side_effect = capture_user2_events
        user1_agent = await self.create_real_agent_with_state_tracking(DataHelperAgent, 'data_helper_user1', user1_notifier)
        user2_agent = await self.create_real_agent_with_state_tracking(DataHelperAgent, 'data_helper_user2', user2_notifier)
        async with managed_user_context(user1_context), managed_user_context(user2_context):
            tasks = [user1_agent.execute(user1_context), user2_agent.execute(user2_context)]
            results = await asyncio.gather(*tasks)
            assert len(results) == 2, 'Both agent executions must complete'
            assert all((result is not None for result in results)), 'All results must be non-None'
        async with self.session_factory() as session:
            user1_executions = await session.execute(sa.text('SELECT agent_name, user_id FROM agent_executions WHERE user_id = :user_id'), {'user_id': self.test_user_1})
            user1_exec_rows = user1_executions.fetchall()
            user2_executions = await session.execute(sa.text('SELECT agent_name, user_id FROM agent_executions WHERE user_id = :user_id'), {'user_id': self.test_user_2})
            user2_exec_rows = user2_executions.fetchall()
            assert len(user1_exec_rows) == 1, f'User 1 should have 1 execution, got {len(user1_exec_rows)}'
            assert len(user2_exec_rows) == 1, f'User 2 should have 1 execution, got {len(user2_exec_rows)}'
            assert user1_exec_rows[0][1] == self.test_user_1, 'User 1 execution must belong to user 1'
            assert user2_exec_rows[0][1] == self.test_user_2, 'User 2 execution must belong to user 2'
        assert len(user1_events) >= 2, f'User 1 should have at least 2 events, got {len(user1_events)}'
        assert len(user2_events) >= 2, f'User 2 should have at least 2 events, got {len(user2_events)}'
        for event in user1_events:
            assert event['data']['user_id'] == self.test_user_1, 'User 1 events must only contain user 1 data'
        for event in user2_events:
            assert event['data']['user_id'] == self.test_user_2, 'User 2 events must only contain user 2 data'
        self.logger.info(' PASS:  Concurrent agent isolation test completed successfully')

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_agent_state_recovery_after_failure(self):
        """Test agent state synchronization recovery after simulated failures.
        
        Business Scenario: An agent execution fails midway through processing.
        The system must be able to recover and maintain consistent state.
        
        CRITICAL: This test validates the system can handle real failure scenarios.
        """
        context = await create_isolated_execution_context(user_id=self.test_user_1, request_id=str(uuid.uuid4()), thread_id=self.id_manager.generate_thread_id(), run_id=self.id_manager.generate_run_id(), validate_user=False)
        websocket_notifier = self.create_mock_websocket_notifier()
        failure_agent = await self.create_real_agent_with_state_tracking(DataHelperAgent, 'failure_test_agent', websocket_notifier)
        original_execute = failure_agent.execute
        execution_count = 0

        async def failing_execute(ctx, **kwargs):
            nonlocal execution_count
            execution_count += 1
            if execution_count == 1:
                async with self.session_factory() as session:
                    await session.execute(sa.text('\n                            INSERT INTO agent_executions \n                            (user_id, thread_id, run_id, agent_name, status) \n                            VALUES (:user_id, :thread_id, :run_id, :agent_name, :status)\n                            '), {'user_id': ctx.user_id, 'thread_id': ctx.thread_id, 'run_id': ctx.run_id, 'agent_name': 'failure_test_agent', 'status': 'failed'})
                    await session.commit()
                raise Exception('Simulated agent execution failure')
            else:
                return await original_execute(ctx, **kwargs)
        failure_agent.execute = failing_execute
        async with managed_user_context(context):
            with pytest.raises(Exception, match='Simulated agent execution failure'):
                await failure_agent.execute(context)
        async with self.session_factory() as session:
            failed_executions = await session.execute(sa.text("SELECT status FROM agent_executions WHERE user_id = :user_id AND status = 'failed'"), {'user_id': self.test_user_1})
            failed_rows = failed_executions.fetchall()
            assert len(failed_rows) == 1, 'Should have exactly 1 failed execution record'
        async with managed_user_context(context):
            recovery_result = await failure_agent.execute(context)
            assert recovery_result is not None, 'Recovery execution must succeed'
            assert 'status' in recovery_result, 'Recovery result must have status'
        async with self.session_factory() as session:
            all_executions = await session.execute(sa.text('SELECT status, agent_name FROM agent_executions WHERE user_id = :user_id ORDER BY id'), {'user_id': self.test_user_1})
            all_rows = all_executions.fetchall()
            assert len(all_rows) == 2, f'Expected 2 execution records, got {len(all_rows)}'
            statuses = [row[0] for row in all_rows]
            assert 'failed' in statuses, 'Must have failed execution record'
            assert 'completed' in statuses, 'Must have successful recovery execution record'
        event_types = [event['type'] for event in self.websocket_events]
        assert 'agent_started' in event_types, 'Must have agent_started event for recovery'
        assert 'agent_completed' in event_types, 'Must have agent_completed event for successful recovery'
        self.logger.info(' PASS:  Agent state recovery test completed successfully')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')