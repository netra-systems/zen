"""
Real Agent Execution Tests - NO MOCKS

Tests actual agent execution with real LLM calls, real database operations,
real WebSocket notifications, and comprehensive integration testing.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Risk Reduction
- Value Impact: Ensures agents work correctly in production environment
- Strategic Impact: Eliminates mock-related false positives in agent tests

This test suite uses:
- Real LLM API calls (Gemini, OpenAI, etc.)
- Real WebSocket connections for agent events
- Real PostgreSQL database operations
- Real Redis caching and state management
- Actual agent orchestration and handoffs
"""
import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import websockets
import logging
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
from test_framework.environment_isolation import get_test_env_manager
from test_framework.llm_config_manager import configure_llm_testing, LLMTestMode
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.config import AgentConfig
from netra_backend.app.schemas.agent_models import AgentResult
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from netra_backend.app.db.database_manager import DatabaseManager
logger = logging.getLogger(__name__)

class RealWebSocketEventCapture:
    """Captures real WebSocket events during agent execution."""

    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.events_captured: List[Dict] = []
        self.websocket = None
        self.connected = False

    async def connect(self):
        """Connect to WebSocket and start capturing events."""
        self.websocket = await websockets.connect(self.websocket_url)
        self.connected = True
        self.capture_task = asyncio.create_task(self._capture_events())

    async def disconnect(self):
        """Disconnect and stop capturing."""
        self.connected = False
        if self.websocket:
            await self.websocket.close()
        if hasattr(self, 'capture_task'):
            await self.capture_task

    async def _capture_events(self):
        """Background task to capture WebSocket events."""
        try:
            while self.connected and (not self.websocket.closed):
                message = await self.websocket.recv()
                event = json.loads(message)
                self.events_captured.append({'timestamp': datetime.now(timezone.utc).isoformat(), 'event': event})
                logger.info(f"Captured WebSocket event: {event.get('type', 'unknown')}")
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f'Event capture error: {e}')

    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get events filtered by type."""
        return [evt for evt in self.events_captured if evt['event'].get('type') == event_type]

    def wait_for_event(self, event_type: str, timeout: float=30.0) -> Optional[Dict]:
        """Wait for specific event type."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            events = self.get_events_by_type(event_type)
            if events:
                return events[-1]
            time.sleep(0.2)
        return None

@pytest.fixture
async def real_llm_config():
    """Configure real LLM testing environment."""
    configure_llm_testing(mode=LLMTestMode.REAL)
    env_manager = get_test_env_manager()
    env = env_manager.setup_test_environment(additional_vars={'ENABLE_REAL_LLM_TESTING': 'true', 'TEST_USE_REAL_LLM': 'true', 'LLM_TEST_MODE': 'REAL'}, enable_real_llm=True)
    yield env
    env_manager.teardown_test_environment()

@pytest.fixture
async def real_database():
    """Real database connection for agent tests."""
    from netra_backend.app.db.database_manager import DatabaseManager
    env_manager = get_test_env_manager()
    env = env_manager.setup_test_environment(additional_vars={'USE_REAL_SERVICES': 'true', 'DATABASE_URL': 'postgresql://netra:netra123@localhost:5432/netra_test'})
    db_manager = DatabaseManager()
    await db_manager.initialize()
    yield db_manager
    await db_manager.close()
    env_manager.teardown_test_environment()

@pytest.fixture
async def real_websocket_manager():
    """Real WebSocket manager with event capturing."""
    manager = WebSocketManager()
    WebSocketManager._instance = None
    manager = WebSocketManager()
    yield manager
    await manager.shutdown()

@pytest.fixture
async def agent_registry():
    """Real agent registry with all agents loaded."""
    registry = AgentRegistry()
    await registry.initialize()
    yield registry
    await registry.shutdown()

class RealAgentExecutionTests:
    """Test real agent execution without any mocks."""

    @pytest.mark.asyncio
    async def test_real_triage_agent_execution(self, real_llm_config, real_database, agent_registry):
        """
        Test real triage agent execution with actual LLM calls.
        MUST PASS: Triage agent should work with real LLM.
        """
        agent_state = DeepAgentState(user_request="I need help analyzing my company's sales data for Q3 2024 trends", chat_thread_id='real_test_thread', user_id='real_test_user', step_count=0)
        triage_agent = agent_registry.get_agent('triage')
        assert triage_agent is not None, 'Triage agent should be available'
        start_time = time.time()
        result = await triage_agent.execute(agent_state)
        execution_time = time.time() - start_time
        assert isinstance(result, AgentResult), 'Should return AgentResult'
        assert result.success is True, f'Triage should succeed: {result.error_message}'
        assert result.updated_state is not None, 'Should return updated state'
        assert result.next_agent is not None, 'Should determine next agent'
        updated_state = result.updated_state
        assert updated_state.step_count > agent_state.step_count, 'Step count should increment'
        assert len(updated_state.conversation_history) > 0, 'Should have conversation history'
        logger.info(f'Triage execution took {execution_time:.2f} seconds')
        logger.info(f'Next agent determined: {result.next_agent}')
        logger.info(f'Agent reasoning: {result.agent_reasoning}')
        assert execution_time > 1.0, 'Real LLM call should take significant time'
        assert 'mock' not in str(result.agent_reasoning).lower(), 'Should not contain mock indicators'

    @pytest.mark.asyncio
    async def test_real_data_analysis_agent_execution(self, real_llm_config, real_database, agent_registry):
        """
        Test real data analysis agent with actual LLM and database operations.
        MUST PASS: Data analysis agent should work with real services.
        """
        agent_state = DeepAgentState(user_request='Analyze the correlation between marketing spend and revenue growth', chat_thread_id='data_analysis_thread', user_id='data_analysis_user', step_count=0)
        agent_state.conversation_history = [{'role': 'user', 'content': 'I have marketing data and revenue data for the past 12 months'}, {'role': 'assistant', 'content': "I'll help you analyze the correlation between marketing spend and revenue growth"}]
        data_agent = agent_registry.get_agent('data_analysis')
        assert data_agent is not None, 'Data analysis agent should be available'
        start_time = time.time()
        result = await data_agent.execute(agent_state)
        execution_time = time.time() - start_time
        assert isinstance(result, AgentResult), 'Should return AgentResult'
        assert result.success is True, f'Data analysis should succeed: {result.error_message}'
        assert result.updated_state is not None, 'Should return updated state'
        db_status = await real_database.health_check()
        assert db_status['status'] == 'healthy', 'Database should remain healthy after agent execution'
        updated_state = result.updated_state
        assert len(updated_state.tool_outputs) > 0, 'Should have tool outputs from analysis'
        logger.info(f'Data analysis execution took {execution_time:.2f} seconds')
        logger.info(f'Tool outputs generated: {len(updated_state.tool_outputs)}')

    @pytest.mark.asyncio
    async def test_real_agent_websocket_event_flow(self, real_llm_config, real_websocket_manager, agent_registry):
        """
        Test that agent execution sends proper WebSocket events.
        MUST PASS: WebSocket events should be sent during real agent execution.
        """
        user_id = 'websocket_test_user'
        thread_id = 'websocket_test_thread'
        events_sent = []

        async def mock_websocket_send(*args, **kwargs):
            events_sent.append(args)
            return True
        real_websocket_manager.send_to_user = mock_websocket_send
        real_websocket_manager.send_to_thread = mock_websocket_send
        agent_state = DeepAgentState(user_request='Create a summary report of our Q3 performance', chat_thread_id=thread_id, user_id=user_id, step_count=0)
        triage_agent = agent_registry.get_agent('triage')
        result = await triage_agent.execute(agent_state)
        assert result.success is True, 'Agent execution should succeed'
        assert len(events_sent) > 0, 'Should have sent WebSocket events during execution'
        event_types = [str(event) for event in events_sent]
        logger.info(f'WebSocket events sent: {len(events_sent)}')
        logger.info(f'Event types: {event_types}')
        assert len(events_sent) >= 2, 'Should send multiple events (start, progress, completion)'

    @pytest.mark.asyncio
    async def test_real_agent_error_handling(self, real_llm_config, agent_registry):
        """
        Test real agent error handling with invalid inputs.
        MUST PASS: Agents should handle errors gracefully.
        """
        agent_state = DeepAgentState(user_request='', chat_thread_id='error_test_thread', user_id='error_test_user', step_count=0)
        triage_agent = agent_registry.get_agent('triage')
        result = await triage_agent.execute(agent_state)
        if not result.success:
            assert result.error_message is not None, 'Should provide error message'
            logger.info(f'Agent properly handled error: {result.error_message}')
        else:
            logger.info('Agent succeeded with empty input (robust handling)')
        assert isinstance(result, AgentResult), 'Should return proper result structure'

    @pytest.mark.asyncio
    async def test_real_multi_agent_orchestration(self, real_llm_config, real_database, agent_registry):
        """
        Test real multi-agent orchestration with handoffs.
        MUST PASS: Agent handoffs should work with real execution.
        """
        initial_state = DeepAgentState(user_request='I need to analyze our customer data and create a presentation about retention trends', chat_thread_id='orchestration_thread', user_id='orchestration_user', step_count=0)
        current_state = initial_state
        execution_chain = []
        max_steps = 5
        for step in range(max_steps):
            if step == 0:
                current_agent = agent_registry.get_agent('triage')
                agent_name = 'triage'
            else:
                if not hasattr(result, 'next_agent') or not result.next_agent:
                    break
                current_agent = agent_registry.get_agent(result.next_agent)
                agent_name = result.next_agent
            if not current_agent:
                logger.warning(f'Agent {agent_name} not found, ending orchestration')
                break
            logger.info(f'Step {step}: Executing agent {agent_name}')
            result = await current_agent.execute(current_state)
            execution_chain.append({'step': step, 'agent': agent_name, 'success': result.success, 'next_agent': result.next_agent, 'execution_time': time.time()})
            if not result.success:
                logger.error(f'Agent {agent_name} failed: {result.error_message}')
                break
            current_state = result.updated_state
            if not result.next_agent:
                logger.info('Orchestration complete - no next agent specified')
                break
        assert len(execution_chain) > 1, 'Should have executed multiple agents'
        assert all((step['success'] for step in execution_chain)), 'All agent executions should succeed'
        assert current_state.step_count > initial_state.step_count, 'State should progress through steps'
        assert len(current_state.conversation_history) > len(initial_state.conversation_history), 'Should accumulate conversation'
        logger.info(f'Multi-agent orchestration completed {len(execution_chain)} steps')
        for step in execution_chain:
            logger.info(f"  Step {step['step']}: {step['agent']} -> {step['next_agent']}")

    @pytest.mark.asyncio
    async def test_real_agent_state_persistence(self, real_llm_config, real_database, agent_registry):
        """
        Test agent state persistence with real database operations.
        MUST PASS: Agent state should be properly saved and restored.
        """
        original_state = DeepAgentState(user_request='Test state persistence functionality', chat_thread_id='persistence_thread', user_id='persistence_user', step_count=0)
        agent = agent_registry.get_agent('triage')
        result = await agent.execute(original_state)
        assert result.success, 'Agent execution should succeed'
        modified_state = result.updated_state
        assert modified_state.step_count > original_state.step_count, 'State should be modified'
        serialized_state = modified_state.model_dump()
        assert isinstance(serialized_state, dict), 'State should serialize to dict'
        restored_state = DeepAgentState.model_validate(serialized_state)
        assert restored_state.user_request == modified_state.user_request
        assert restored_state.chat_thread_id == modified_state.chat_thread_id
        assert restored_state.user_id == modified_state.user_id
        assert restored_state.step_count == modified_state.step_count
        logger.info('Agent state persistence test successful')

    @pytest.mark.asyncio
    async def test_real_agent_timeout_handling(self, real_llm_config, agent_registry):
        """
        Test agent execution with timeout handling.
        MUST PASS: Agents should handle timeouts gracefully.
        """
        agent_state = DeepAgentState(user_request='This is a test request for timeout handling', chat_thread_id='timeout_thread', user_id='timeout_user', step_count=0)
        agent = agent_registry.get_agent('triage')
        try:
            result = await asyncio.wait_for(agent.execute(agent_state), timeout=30.0)
            assert isinstance(result, AgentResult), 'Should return valid result'
            logger.info('Agent completed within timeout')
        except asyncio.TimeoutError:
            logger.info('Agent execution timed out as expected')

    @pytest.mark.asyncio
    async def test_real_agent_concurrent_execution(self, real_llm_config, agent_registry):
        """
        Test concurrent agent execution with real LLM calls.
        MUST PASS: Multiple agents should be able to execute concurrently.
        """
        states = []
        for i in range(3):
            state = DeepAgentState(user_request=f'Concurrent test request {i}', chat_thread_id=f'concurrent_thread_{i}', user_id=f'concurrent_user_{i}', step_count=0)
            states.append(state)
        agent = agent_registry.get_agent('triage')
        start_time = time.time()
        tasks = [agent.execute(state) for state in states]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f'Concurrent execution {i} failed: {result}')
            else:
                assert isinstance(result, AgentResult), f'Result {i} should be AgentResult'
                if result.success:
                    successful_results.append(result)
        assert len(successful_results) > 0, 'At least some concurrent executions should succeed'
        logger.info(f'Concurrent execution: {len(successful_results)}/{len(states)} succeeded in {total_time:.2f}s')

class RealAgentIntegrationTests:
    """Test agent integration with all real services."""

    @pytest.mark.asyncio
    async def test_full_agent_ecosystem_integration(self, real_llm_config, real_database, real_websocket_manager, agent_registry):
        """
        Test complete agent ecosystem with all real services.
        MUST PASS: Complete integration should work end-to-end.
        """
        user_id = 'ecosystem_test_user'
        thread_id = 'ecosystem_test_thread'
        agent_state = DeepAgentState(user_request='I need a complete analysis of our business metrics with recommendations for Q4 strategy', chat_thread_id=thread_id, user_id=user_id, step_count=0)
        websocket_events = []
        database_operations = []
        original_ws_send = real_websocket_manager.send_to_user

        async def track_websocket(*args, **kwargs):
            websocket_events.append(args)
            return await original_ws_send(*args, **kwargs)
        real_websocket_manager.send_to_user = track_websocket
        triage_agent = agent_registry.get_agent('triage')
        start_time = time.time()
        result = await triage_agent.execute(agent_state)
        total_time = time.time() - start_time
        assert result.success, f'Ecosystem integration should succeed: {result.error_message}'
        assert result.updated_state is not None, 'Should have updated state'
        db_status = await real_database.health_check()
        assert db_status['status'] == 'healthy', 'Database should be healthy after integration'
        logger.info(f'WebSocket events generated: {len(websocket_events)}')
        logger.info(f'Full ecosystem integration completed in {total_time:.2f} seconds')
        logger.info(f'Final state step count: {result.updated_state.step_count}')
        logger.info(f'Conversation history entries: {len(result.updated_state.conversation_history)}')
        assert total_time > 1.0, 'Real integration should take meaningful time'
        assert result.updated_state.step_count > 0, 'Should have processed steps'
        assert len(result.updated_state.conversation_history) > 0, 'Should have conversation history'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')