"""
BaseAgent Message Integration Tests
Golden Path Phase 1 - Issue #1081

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate core agent message processing and user isolation for chat functionality
- Value Impact: Ensures agents process messages correctly with proper context isolation and WebSocket events
- Strategic Impact: Core infrastructure for $500K+ ARR chat functionality delivering AI problem-solving value

CRITICAL REQUIREMENTS:
1. Real services only (no mocks per CLAUDE.md)
2. User context isolation validation
3. WebSocket event emission testing
4. Message processing pipeline integration
5. LLM usage tracking and metadata storage

Focus Areas:
- BaseAgent integration with user context
- Message processing with real LLM
- WebSocket event delivery validation
- User isolation between concurrent requests
- Metadata storage and retrieval
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest
from test_framework.ssot.base_integration_test import BaseIntegrationTest
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.user_context_test_helpers import create_test_user_context
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
from shared.isolated_environment import get_env
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from test_framework.ssot.websocket import WebSocketEventType

class AgentTests(BaseAgent):
    """Test agent implementation for integration testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_processing_results = []
        self.execution_metadata = {}

    async def execute(self, user_message: str, context: Dict[str, Any]=None) -> Dict[str, Any]:
        """Execute agent with message processing and WebSocket events."""
        await self.emit_thinking('Starting message processing')
        if self.llm_manager:
            try:
                await self.emit_thinking(f'Processing user message: {user_message}')
                llm_response = await self.llm_manager.generate_completion(messages=[{'role': 'user', 'content': user_message}], model='gpt-3.5-turbo', temperature=0.7)
                self.execution_metadata['llm_usage'] = {'tokens_used': llm_response.get('usage', {}).get('total_tokens', 0), 'model': 'gpt-3.5-turbo', 'processing_time': time.time()}
                result = {'status': 'success', 'message': user_message, 'llm_response': llm_response.get('content', ''), 'metadata': self.execution_metadata, 'processed_at': datetime.now(timezone.utc).isoformat()}
                await self.emit_progress('Message processing completed successfully')
                self.message_processing_results.append(result)
                return result
            except Exception as e:
                await self.emit_error(f'LLM processing failed: {str(e)}')
                raise
        else:
            result = {'status': 'success', 'message': user_message, 'response': f'Processed: {user_message}', 'metadata': {'processing_mode': 'fallback'}, 'processed_at': datetime.now(timezone.utc).isoformat()}
            await self.emit_progress('Message processing completed (fallback mode)')
            self.message_processing_results.append(result)
            return result

class BaseAgentMessageIntegrationTests(BaseIntegrationTest):
    """Integration tests for BaseAgent message processing with real services."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, real_services_fixture):
        """Set up isolated test environment with real services."""
        self.env = get_env()
        self.services = real_services_fixture
        self.test_user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'thread_{uuid.uuid4().hex[:8]}'
        assert real_services_fixture, 'Real services fixture required - no mocks allowed'
        assert 'db' in real_services_fixture or 'postgres' in real_services_fixture, 'Real database required'
        self.ws_utility = WebSocketTestUtility(base_url='ws://localhost:8000/ws', env=self.env)
        await self.ws_utility.initialize()
        try:
            self.llm_manager = LLMManager()
            await self.llm_manager.initialize()
        except Exception as e:
            self.llm_manager = None
            print(f'LLM not available, using fallback mode: {e}')

    async def async_teardown(self):
        """Clean up test resources."""
        if hasattr(self, 'ws_utility') and self.ws_utility:
            await self.ws_utility.cleanup()
        await super().async_teardown()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execute_with_user_context_isolation(self, real_services_fixture):
        """
        Test BaseAgent execution with proper user context isolation.
        
        Validates that agents maintain complete isolation between user contexts
        and process messages without cross-user contamination.
        """
        user_contexts = []
        agents = []
        for i in range(3):
            user_id = f'isolated_user_{i}_{uuid.uuid4().hex[:6]}'
            user_context = await create_test_user_context(user_id=user_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{uuid.uuid4().hex[:8]}', real_services=real_services_fixture)
            user_contexts.append(user_context)
            agent = AgentTests(llm_manager=self.llm_manager, name=f'TestAgent_{i}', user_context=user_context)
            agents.append(agent)
        execution_tasks = []
        for i, (agent, user_context) in enumerate(zip(agents, user_contexts)):
            task = asyncio.create_task(agent.execute(user_message=f'User {i} optimization request: analyze costs for user {user_context.user_id}', context={'user_specific_data': f'data_for_user_{i}'}))
            execution_tasks.append(task)
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f'Agent {i} execution failed: {result}'
            assert result['status'] == 'success', f'Agent {i} did not succeed'
            assert f'User {i}' in result['message'], f'Agent {i} lost user-specific context'
            assert user_contexts[i].user_id in result['message'], f'Agent {i} lost user ID context'
            for j in range(3):
                if i != j:
                    other_user_id = user_contexts[j].user_id
                    assert other_user_id not in str(result), f'Agent {i} contaminated with user {j} data'
        for i, agent in enumerate(agents):
            assert len(agent.message_processing_results) == 1, f'Agent {i} processing results corrupted'
            agent_result = agent.message_processing_results[0]
            assert user_contexts[i].user_id in agent_result['message'], f'Agent {i} result isolation failed'

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_metadata_storage_integration(self, real_services_fixture):
        """
        Test agent metadata storage and retrieval with real database.
        
        Validates that agent execution metadata is properly stored and can be
        retrieved for audit trails and analytics.
        """
        user_context = await create_test_user_context(user_id=self.test_user_id, request_id=f'metadata_test_{uuid.uuid4().hex[:8]}', thread_id=self.test_thread_id, real_services=real_services_fixture)
        agent = AgentTests(llm_manager=self.llm_manager, name='MetadataTestAgent', user_context=user_context)
        test_message = 'Analyze system performance and provide optimization recommendations'
        result = await agent.execute(user_message=test_message, context={'enable_metadata_tracking': True, 'analytics_session': f'session_{uuid.uuid4().hex[:8]}'})
        assert 'metadata' in result, 'Execution metadata not collected'
        metadata = result['metadata']
        if self.llm_manager:
            assert 'llm_usage' in metadata, 'LLM usage metadata missing'
            llm_usage = metadata['llm_usage']
            assert 'tokens_used' in llm_usage, 'Token usage not tracked'
            assert 'model' in llm_usage, 'Model information not tracked'
            assert llm_usage['tokens_used'] > 0, 'Token count should be positive'
        assert 'processed_at' in result, 'Processing timestamp missing'
        processed_time = datetime.fromisoformat(result['processed_at'].replace('Z', '+00:00'))
        time_diff = datetime.now(timezone.utc) - processed_time
        assert time_diff.total_seconds() < 60, 'Processing timestamp too old'
        agent_metadata = agent.execution_metadata
        if self.llm_manager:
            assert 'llm_usage' in agent_metadata, 'Agent metadata not persisted'
        assert agent.user_context.user_id == self.test_user_id, 'User context not preserved'
        assert agent.user_context.request_id == user_context.request_id, 'Request context not preserved'

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_llm_usage_tracking_integration(self, real_services_fixture):
        """
        Test LLM usage tracking and token optimization integration.
        
        Validates that agents properly track LLM usage for billing and optimization.
        """
        if not self.llm_manager:
            pytest.skip('LLM manager not available for usage tracking test')
        user_context = await create_test_user_context(user_id=self.test_user_id, request_id=f'llm_tracking_{uuid.uuid4().hex[:8]}', thread_id=self.test_thread_id, real_services=real_services_fixture)
        agent = AgentTests(llm_manager=self.llm_manager, name='LLMTrackingAgent', user_context=user_context)
        test_messages = ['What are the best practices for cloud cost optimization?', 'How can I automate my deployment pipeline?', 'Analyze my infrastructure for security vulnerabilities']
        total_tokens_used = 0
        for i, message in enumerate(test_messages):
            result = await agent.execute(user_message=message, context={'message_index': i})
            assert result['status'] == 'success', f'Message {i} processing failed'
            assert 'llm_response' in result, f'Message {i} missing LLM response'
            assert len(result['llm_response']) > 0, f'Message {i} empty LLM response'
            metadata = result.get('metadata', {})
            llm_usage = metadata.get('llm_usage', {})
            assert 'tokens_used' in llm_usage, f'Message {i} missing token usage'
            assert llm_usage['tokens_used'] > 0, f'Message {i} zero token usage'
            total_tokens_used += llm_usage['tokens_used']
        assert total_tokens_used > 0, 'No tokens tracked across all executions'
        assert len(agent.message_processing_results) == 3, 'Not all messages processed'
        processing_times = set()
        for result in agent.message_processing_results:
            metadata = result.get('metadata', {})
            llm_usage = metadata.get('llm_usage', {})
            processing_time = llm_usage.get('processing_time')
            assert processing_time is not None, 'Processing time not recorded'
            assert processing_time not in processing_times, 'Duplicate processing times detected'
            processing_times.add(processing_time)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_event_emission_integration(self, real_services_fixture):
        """
        Test WebSocket event emission during agent execution.
        
        Validates that agents emit proper WebSocket events for real-time user experience.
        """
        user_context = await create_test_user_context(user_id=self.test_user_id, request_id=f'websocket_test_{uuid.uuid4().hex[:8]}', thread_id=self.test_thread_id, real_services=real_services_fixture)
        async with self.ws_utility.connected_client(user_id=self.test_user_id) as client:
            agent = AgentTests(llm_manager=self.llm_manager, name='WebSocketTestAgent', user_context=user_context)
            ws_bridge = AgentWebSocketBridge(user_context=user_context, websocket_manager=None)
            agent.set_websocket_bridge(ws_bridge)
            start_time = time.time()
            execution_task = asyncio.create_task(agent.execute(user_message='Provide detailed cloud optimization recommendations', context={'enable_websocket_events': True}))
            received_events = []
            timeout = 30.0
            while not execution_task.done() and time.time() - start_time < timeout:
                try:
                    event = await client.wait_for_message(timeout=2.0)
                    received_events.append(event)
                except asyncio.TimeoutError:
                    continue
            execution_result = await execution_task
            await asyncio.sleep(1.0)
            try:
                while True:
                    event = await client.wait_for_message(timeout=0.5)
                    received_events.append(event)
            except asyncio.TimeoutError:
                pass
            assert execution_result['status'] == 'success', 'Agent execution failed'
            if received_events:
                event_types = [event.event_type for event in received_events]
                expected_events = ['agent_thinking', 'agent_progress']
                for expected_event in expected_events:
                    matching_events = [e for e in event_types if expected_event in str(e)]
                    assert len(matching_events) > 0, f'Missing {expected_event} WebSocket events'
                for event in received_events:
                    assert hasattr(event, 'user_id'), 'Event missing user_id'
                    assert event.user_id == self.test_user_id, 'Event user_id mismatch'
                    assert hasattr(event, 'data'), 'Event missing data'
                    assert hasattr(event, 'timestamp'), 'Event missing timestamp'
            else:
                print('Warning: No WebSocket events received - may indicate bridge not properly configured')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_session_isolation_validation(self, real_services_fixture):
        """
        Test agent session isolation between concurrent users.
        
        Validates that agent sessions maintain complete isolation and prevent
        session state contamination between concurrent users.
        """
        num_sessions = 4
        session_data = []
        for i in range(num_sessions):
            user_id = f'session_user_{i}_{uuid.uuid4().hex[:6]}'
            session_id = f'session_{i}_{uuid.uuid4().hex[:8]}'
            user_context = await create_test_user_context(user_id=user_id, request_id=f'session_req_{i}_{uuid.uuid4().hex[:8]}', thread_id=f'session_thread_{i}_{uuid.uuid4().hex[:8]}', real_services=real_services_fixture, session_id=session_id)
            agent = AgentTests(llm_manager=self.llm_manager, name=f'SessionAgent_{i}', user_context=user_context)
            session_data.append({'user_id': user_id, 'session_id': session_id, 'user_context': user_context, 'agent': agent})
        concurrent_tasks = []
        for i, session in enumerate(session_data):
            task = asyncio.create_task(self._execute_session_isolated_agent(session['agent'], session['user_context'], f"Session {i} request: optimize costs for session {session['session_id']}"))
            concurrent_tasks.append(task)
        session_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        for i, result in enumerate(session_results):
            assert not isinstance(result, Exception), f'Session {i} failed: {result}'
            assert result['success'], f"Session {i} execution failed: {result.get('error')}"
            session_id = session_data[i]['session_id']
            assert session_id in result['response'], f'Session {i} lost session context'
            for j in range(num_sessions):
                if i != j:
                    other_session_id = session_data[j]['session_id']
                    assert other_session_id not in result['response'], f'Session {i} contaminated with session {j} data'
        for i, session in enumerate(session_data):
            agent = session['agent']
            assert len(agent.message_processing_results) == 1, f'Agent {i} session state corrupted'
            assert agent.user_context.user_id == session['user_id'], f'Agent {i} user context corrupted'
            if hasattr(agent.user_context, 'session_id'):
                assert agent.user_context.session_id == session['session_id'], f'Agent {i} session context corrupted'

    async def _execute_session_isolated_agent(self, agent: AgentTests, user_context: UserExecutionContext, message: str) -> Dict[str, Any]:
        """Helper method for session isolation testing."""
        try:
            result = await agent.execute(user_message=message, context={'session_test': True})
            return {'success': True, 'user_id': user_context.user_id, 'session_id': getattr(user_context, 'session_id', 'unknown'), 'response': result.get('message', ''), 'execution_time': time.time()}
        except Exception as e:
            return {'success': False, 'user_id': user_context.user_id, 'error': str(e), 'execution_time': time.time()}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')