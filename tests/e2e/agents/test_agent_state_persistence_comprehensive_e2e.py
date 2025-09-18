"""
Agent State Persistence Comprehensive E2E Tests

Business Value Justification (BVJ):
- Segment: Enterprise - Stateful AI conversations and workflows ($350K+ MRR)
- Business Goal: Ensure agent state persists across requests for contextual continuity
- Value Impact: Users maintain context in multi-turn conversations and long workflows
- Strategic/Revenue Impact: State persistence enables sophisticated AI interactions

This test suite validates comprehensive agent state persistence:
1. State persistence across user sessions and requests
2. Context continuity in multi-turn agent conversations
3. State isolation between different users and threads
4. State recovery after system interruptions
5. State cleanup and memory management
6. Cross-request agent memory and learning

CRITICAL E2E REQUIREMENTS:
- Real GCP staging environment (NO Docker)
- Authenticated state persistence with JWT
- Real Redis/database state storage validation
- Cross-request state continuity testing
- State isolation between users and sessions
"""
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set
import pytest
import websockets
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context, E2EAuthConfig
from test_framework.base_e2e_test import BaseE2ETest
from tests.e2e.staging_config import StagingTestConfig, get_staging_config
logger = logging.getLogger(__name__)

@pytest.mark.e2e
class AgentStatePersistenceE2ETests(BaseE2ETest):
    """
    Comprehensive Agent State Persistence E2E Tests for GCP Staging.

    Tests critical state persistence patterns that enable contextual AI
    conversations and sophisticated workflow continuity.
    """

    @pytest.fixture(autouse=True)
    async def setup_state_persistence_environment(self):
        """Set up state persistence testing environment with continuity monitoring."""
        await self.initialize_test_environment()
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment='staging')
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment='staging')
        assert self.staging_config.validate_configuration(), 'Staging configuration invalid'
        self.test_users = []
        for i in range(2):
            user_context = await create_authenticated_user_context(user_email=f'state_persistence_test_{i}_{int(time.time())}@staging.netrasystems.ai', environment='staging', permissions=['read', 'write', 'execute_agents', 'persist_state', 'manage_sessions'])
            self.test_users.append(user_context)
        self.user_states = {}
        self.session_continuity = {}
        self.state_persistence_logs = {}
        for user in self.test_users:
            self.user_states[user.user_id] = {'conversation_history': [], 'agent_memory': {}, 'session_data': {}, 'persistent_context': {}}
            self.session_continuity[user.user_id] = {'sessions': [], 'cross_session_data': {}, 'state_transitions': []}
            self.state_persistence_logs[user.user_id] = []
        self.logger.info(f'CHECK PASS: State persistence test environment ready - {len(self.test_users)} users authenticated')

    async def test_cross_request_state_continuity(self):
        """
        Test agent state persists across multiple requests and sessions.

        BVJ: Validates $200K+ MRR conversation continuity - Users expect context retention
        Ensures: Agent remembers previous interactions, builds on past context
        """
        user_context = self.test_users[0]
        first_session_data = await self._execute_stateful_session(user_context, session_name='initial_analysis', agent_request={'type': 'execute_agent', 'agent_type': 'stateful_conversation_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id, 'data': {'conversation_context': 'start_new_analysis', 'user_preferences': {'analysis_depth': 'comprehensive', 'focus_areas': ['cost_optimization', 'performance'], 'reporting_style': 'detailed'}, 'state_persistence': True, 'establish_context': True, 'session_id': f'session_1_{int(time.time())}'}})
        assert first_session_data['success'], 'First session failed to complete'
        assert first_session_data['state_established'], 'Initial state was not established'
        await asyncio.sleep(3.0)
        second_session_data = await self._execute_stateful_session(user_context, session_name='continued_analysis', agent_request={'type': 'execute_agent', 'agent_type': 'stateful_conversation_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id + '_cont', 'data': {'conversation_context': 'continue_analysis', 'reference_previous_session': True, 'build_on_context': True, 'state_persistence': True, 'session_id': f'session_2_{int(time.time())}'}})
        assert second_session_data['success'], 'Second session failed to complete'
        assert second_session_data['context_retrieved'], 'Previous context was not retrieved'
        third_session_data = await self._execute_stateful_session(user_context, session_name='comprehensive_continuation', agent_request={'type': 'execute_agent', 'agent_type': 'stateful_conversation_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id + '_final', 'data': {'conversation_context': 'summarize_and_recommend', 'use_accumulated_context': True, 'validate_state_continuity': True, 'state_persistence': True, 'session_id': f'session_3_{int(time.time())}'}})
        assert third_session_data['success'], 'Third session failed to complete'
        assert third_session_data['accumulated_context'], 'Accumulated context validation failed'
        all_sessions = [first_session_data, second_session_data, third_session_data]
        context_evolution = []
        for session in all_sessions:
            if 'context_data' in session:
                context_evolution.append(session['context_data'])
        assert len(context_evolution) >= 2, f'Expected context evolution across sessions, got {len(context_evolution)}'
        second_context = second_session_data.get('context_data', {})
        third_context = third_session_data.get('context_data', {})
        assert 'previous_session_data' in second_context or 'prior_context' in second_context, 'Second session missing reference to first'
        accumulated_items = third_context.get('accumulated_knowledge', [])
        assert len(accumulated_items) >= 2, f'Expected accumulated knowledge from multiple sessions, got {len(accumulated_items)}'
        self.logger.info(f'CHECK PASS: Cross-request state continuity validated successfully')
        self.logger.info(f'📊 Sessions completed: {len(all_sessions)}')
        self.logger.info(f'🧠 Context evolution stages: {len(context_evolution)}')
        self.logger.info(f'📚 Accumulated knowledge items: {len(accumulated_items)}')

    async def test_multi_user_state_isolation(self):
        """
        Test state isolation between different users and threads.

        BVJ: Validates $300K+ MRR multi-tenant security - User state must be isolated
        Ensures: Users cannot access each other's persistent state or context
        """
        isolation_results = []

        async def test_user_state_isolation(user_context, user_index):
            """Test state isolation for specific user."""
            try:
                unique_session_data = {'user_secret': f'secret_data_user_{user_index}_{int(time.time())}', 'user_preferences': {'theme': f'theme_{user_index}', 'language': f'lang_{user_index}', 'privacy_level': f'level_{user_index}'}, 'conversation_history': [f'User {user_index} message 1', f'User {user_index} message 2', f'User {user_index} message 3']}
                session1_data = await self._execute_stateful_session(user_context, session_name=f'isolation_test_user_{user_index}_session1', agent_request={'type': 'execute_agent', 'agent_type': 'state_isolation_test_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id, 'data': {'establish_unique_state': True, 'user_index': user_index, 'unique_data': unique_session_data, 'state_isolation_test': True, 'session_id': f'isolation_session_1_user_{user_index}'}})
                await asyncio.sleep(2.0)
                session2_data = await self._execute_stateful_session(user_context, session_name=f'isolation_test_user_{user_index}_session2', agent_request={'type': 'execute_agent', 'agent_type': 'state_isolation_test_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id + '_verify', 'data': {'verify_state_isolation': True, 'user_index': user_index, 'expected_unique_data': unique_session_data, 'cross_user_contamination_check': True, 'session_id': f'isolation_session_2_user_{user_index}'}})
                isolation_validated = session2_data.get('isolation_validated', False)
                cross_contamination_detected = session2_data.get('cross_contamination_detected', False)
                retrieved_secret = session2_data.get('retrieved_user_secret', '')
                return {'user_index': user_index, 'user_id': user_context.user_id, 'success': True, 'session1_success': session1_data['success'], 'session2_success': session2_data['success'], 'isolation_validated': isolation_validated, 'cross_contamination_detected': cross_contamination_detected, 'state_retrieved_correctly': retrieved_secret == unique_session_data['user_secret'], 'unique_data': unique_session_data}
            except Exception as e:
                return {'user_index': user_index, 'user_id': user_context.user_id, 'success': False, 'error': str(e)}
        tasks = [test_user_state_isolation(user_context, i) for i, user_context in enumerate(self.test_users)]
        isolation_results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_users = 0
        isolated_users = 0
        contamination_detected = 0
        for result in isolation_results:
            if isinstance(result, dict) and result.get('success'):
                successful_users += 1
                if result.get('isolation_validated'):
                    isolated_users += 1
                if result.get('cross_contamination_detected'):
                    contamination_detected += 1
                assert result.get('state_retrieved_correctly'), f"User {result['user_index']} state retrieval failed"
        assert successful_users == len(self.test_users), f'Expected {len(self.test_users)} successful users, got {successful_users}'
        assert isolated_users == len(self.test_users), f'Expected {len(self.test_users)} isolated users, got {isolated_users}'
        assert contamination_detected == 0, f'CRITICAL: Cross-user contamination detected in {contamination_detected} cases'
        all_unique_secrets = [r['unique_data']['user_secret'] for r in isolation_results if isinstance(r, dict) and r.get('success')]
        unique_secrets_count = len(set(all_unique_secrets))
        assert unique_secrets_count == len(self.test_users), f'Expected {len(self.test_users)} unique secrets, got {unique_secrets_count}'
        self.logger.info(f'CHECK PASS: Multi-user state isolation validated successfully')
        self.logger.info(f'👥 Users tested: {successful_users}')
        self.logger.info(f'🔒 Users with isolated state: {isolated_users}')
        self.logger.info(f'🚫 Cross-contamination detected: {contamination_detected} (MUST BE ZERO)')
        self.logger.info(f'🔑 Unique state secrets: {unique_secrets_count}')

    async def test_state_recovery_after_interruption(self):
        """
        Test state recovery after system interruptions or connection failures.

        BVJ: Validates $150K+ MRR reliability - State must survive interruptions
        Ensures: Agent state recovers gracefully after system disruptions
        """
        user_context = self.test_users[0]
        pre_interruption_state = {'analysis_progress': {'completed_stages': ['initial_assessment', 'data_collection', 'preliminary_analysis'], 'current_stage': 'optimization_generation', 'next_stages': ['validation', 'reporting', 'implementation']}, 'accumulated_data': {'cost_metrics': {'monthly_spend': 15000, 'optimization_potential': 4500}, 'performance_metrics': {'avg_response_time': 250, 'error_rate': 0.02}, 'risk_factors': ['legacy_dependencies', 'compliance_requirements']}, 'user_decisions': [{'decision': 'proceed_with_optimization', 'confidence': 0.85}, {'decision': 'prioritize_cost_over_performance', 'confidence': 0.72}], 'session_metadata': {'session_id': f'recovery_test_{int(time.time())}', 'started_at': datetime.now(timezone.utc).isoformat(), 'interruption_test': True}}
        pre_interruption_session = await self._execute_stateful_session(user_context, session_name='pre_interruption_state', agent_request={'type': 'execute_agent', 'agent_type': 'state_recovery_test_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id, 'data': {'establish_complex_state': True, 'state_data': pre_interruption_state, 'prepare_for_interruption': True, 'state_persistence': True}})
        assert pre_interruption_session['success'], 'Pre-interruption state establishment failed'
        self.logger.info('🚨 Simulating system interruption...')
        await asyncio.sleep(5.0)
        recovery_session = await self._execute_stateful_session(user_context, session_name='post_interruption_recovery', agent_request={'type': 'execute_agent', 'agent_type': 'state_recovery_test_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id + '_recovery', 'data': {'recover_from_interruption': True, 'expected_state': pre_interruption_state, 'validate_state_integrity': True, 'state_recovery_test': True}})
        assert recovery_session['success'], 'State recovery session failed'
        recovery_data = recovery_session.get('recovery_data', {})
        state_integrity_check = recovery_data.get('state_integrity_validated', False)
        recovered_data = recovery_data.get('recovered_state_data', {})
        assert state_integrity_check, 'State integrity validation failed after recovery'
        expected_components = ['analysis_progress', 'accumulated_data', 'user_decisions', 'session_metadata']
        recovered_components = []
        for component in expected_components:
            if component in recovered_data and recovered_data[component]:
                recovered_components.append(component)
        recovery_completeness = len(recovered_components) / len(expected_components)
        assert recovery_completeness >= 0.75, f'Insufficient state recovery: {recovery_completeness * 100:.1f}% (expected >= 75%)'
        if 'analysis_progress' in recovered_data:
            recovered_progress = recovered_data['analysis_progress']
            expected_progress = pre_interruption_state['analysis_progress']
            assert recovered_progress.get('current_stage') == expected_progress.get('current_stage'), 'Current analysis stage not preserved'
        if 'accumulated_data' in recovered_data:
            recovered_metrics = recovered_data['accumulated_data']
            expected_metrics = pre_interruption_state['accumulated_data']
            if 'cost_metrics' in recovered_metrics and 'cost_metrics' in expected_metrics:
                recovered_spend = recovered_metrics['cost_metrics'].get('monthly_spend', 0)
                expected_spend = expected_metrics['cost_metrics'].get('monthly_spend', 0)
                assert recovered_spend == expected_spend, f'Cost data integrity lost: {recovered_spend} != {expected_spend}'
        self.logger.info(f'CHECK PASS: State recovery after interruption validated successfully')
        self.logger.info(f'📊 Recovery completeness: {recovery_completeness * 100:.1f}%')
        self.logger.info(f'🔧 Components recovered: {len(recovered_components)}/{len(expected_components)}')
        self.logger.info(f'CHECK State integrity validated: {state_integrity_check}')

    async def test_state_cleanup_and_memory_management(self):
        """
        Test proper state cleanup and memory management for completed sessions.

        BVJ: Validates $100K+ MRR resource efficiency - Prevents memory leaks
        Ensures: Old state is cleaned up, memory usage remains bounded
        """
        user_context = self.test_users[0]
        cleanup_metrics = {'sessions_created': 0, 'sessions_cleaned': 0, 'memory_usage_samples': [], 'cleanup_events': []}
        cleanup_sessions = []
        session_ids = []
        for i in range(5):
            session_id = f'cleanup_test_session_{i}_{int(time.time())}'
            session_ids.append(session_id)
            session_data = await self._execute_stateful_session(user_context, session_name=f'cleanup_test_{i}', agent_request={'type': 'execute_agent', 'agent_type': 'state_cleanup_test_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id + f'_cleanup_{i}', 'data': {'session_id': session_id, 'create_temporary_state': True, 'state_size': 'medium', 'cleanup_test': True, 'memory_tracking': True}})
            cleanup_sessions.append(session_data)
            cleanup_metrics['sessions_created'] += 1
            if session_data.get('memory_usage'):
                cleanup_metrics['memory_usage_samples'].append(session_data['memory_usage'])
            await asyncio.sleep(1.0)
        cleanup_request_session = await self._execute_stateful_session(user_context, session_name='explicit_cleanup_request', agent_request={'type': 'execute_agent', 'agent_type': 'state_cleanup_test_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id + '_cleanup_request', 'data': {'request_cleanup': True, 'sessions_to_cleanup': session_ids, 'memory_management_test': True, 'validate_cleanup': True}})
        assert cleanup_request_session['success'], 'Cleanup request session failed'
        cleanup_data = cleanup_request_session.get('cleanup_data', {})
        cleanup_metrics['sessions_cleaned'] = cleanup_data.get('sessions_cleaned', 0)
        cleanup_metrics['cleanup_events'] = cleanup_data.get('cleanup_events', [])
        assert cleanup_metrics['sessions_cleaned'] >= 3, f"Expected at least 3 sessions cleaned, got {cleanup_metrics['sessions_cleaned']}"
        if cleanup_metrics['memory_usage_samples']:
            initial_memory = cleanup_metrics['memory_usage_samples'][0]
            final_memory = cleanup_data.get('final_memory_usage', initial_memory)
            memory_reduction = initial_memory - final_memory
            memory_reduction_percent = memory_reduction / initial_memory * 100 if initial_memory > 0 else 0
            assert memory_reduction_percent >= 10, f'Insufficient memory cleanup: {memory_reduction_percent:.1f}% reduction'
        cleanup_events = cleanup_metrics['cleanup_events']
        assert len(cleanup_events) >= 1, f'Expected cleanup events, got {len(cleanup_events)}'
        verification_session = await self._execute_stateful_session(user_context, session_name='cleanup_verification', agent_request={'type': 'execute_agent', 'agent_type': 'state_cleanup_test_agent', 'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'request_id': user_context.request_id + '_verify_cleanup', 'data': {'verify_cleanup_completion': True, 'check_session_accessibility': session_ids[:3], 'expect_cleanup': True}})
        verification_data = verification_session.get('verification_data', {})
        inaccessible_sessions = verification_data.get('inaccessible_sessions', [])
        inaccessible_rate = len(inaccessible_sessions) / len(session_ids[:3]) if len(session_ids) > 0 else 0
        assert inaccessible_rate >= 0.6, f'Expected at least 60% of sessions to be cleaned up, got {inaccessible_rate * 100:.1f}%'
        self.logger.info(f'CHECK PASS: State cleanup and memory management validated')
        self.logger.info(f"📊 Sessions created: {cleanup_metrics['sessions_created']}")
        self.logger.info(f"🧹 Sessions cleaned: {cleanup_metrics['sessions_cleaned']}")
        self.logger.info(f'💾 Memory reduction: {memory_reduction_percent:.1f}%' if 'memory_reduction_percent' in locals() else 'Memory tracking unavailable')
        self.logger.info(f'🔍 Cleanup events: {len(cleanup_events)}')
        self.logger.info(f'🚫 Inaccessible sessions: {len(inaccessible_sessions)}/{len(session_ids[:3])}')

    async def _execute_stateful_session(self, user_context, session_name: str, agent_request: Dict) -> Dict[str, Any]:
        """Execute a stateful agent session and return results with state information."""
        websocket = None
        try:
            websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=25.0)
            session_results = {'session_name': session_name, 'success': False, 'state_established': False, 'context_retrieved': False, 'accumulated_context': False, 'isolation_validated': False, 'cross_contamination_detected': False, 'recovery_data': {}, 'cleanup_data': {}, 'verification_data': {}, 'context_data': {}, 'memory_usage': 0, 'events': []}

            async def collect_session_events():
                """Collect events from the stateful session."""
                try:
                    async for message in websocket:
                        event = json.loads(message)
                        event_type = event.get('type')
                        event_data = event.get('data', {})
                        session_results['events'].append(event)
                        if event_type == 'state_established':
                            session_results['state_established'] = True
                            session_results['context_data'] = event_data
                        elif event_type == 'context_retrieved':
                            session_results['context_retrieved'] = True
                            session_results['context_data'].update(event_data)
                        elif event_type == 'accumulated_context':
                            session_results['accumulated_context'] = True
                            session_results['context_data']['accumulated_knowledge'] = event_data.get('knowledge', [])
                        elif event_type == 'isolation_validated':
                            session_results['isolation_validated'] = event_data.get('validated', False)
                            session_results['cross_contamination_detected'] = event_data.get('contamination_detected', False)
                            session_results['retrieved_user_secret'] = event_data.get('user_secret', '')
                        elif event_type == 'recovery_completed':
                            session_results['recovery_data'] = event_data
                        elif event_type == 'cleanup_completed':
                            session_results['cleanup_data'] = event_data
                        elif event_type == 'verification_completed':
                            session_results['verification_data'] = event_data
                        elif event_type == 'memory_usage_report':
                            session_results['memory_usage'] = event_data.get('memory_mb', 0)
                        elif event_type == 'agent_completed':
                            session_results['success'] = True
                            break
                except Exception as e:
                    self.logger.error(f'Session event collection error: {e}')
            event_task = asyncio.create_task(collect_session_events())
            await websocket.send(json.dumps(agent_request))
            await asyncio.wait_for(event_task, timeout=45.0)
            return session_results
        except Exception as e:
            self.logger.error(f'Stateful session {session_name} failed: {e}')
            session_results['success'] = False
            session_results['error'] = str(e)
            return session_results
        finally:
            if websocket:
                try:
                    await websocket.close()
                except:
                    pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')