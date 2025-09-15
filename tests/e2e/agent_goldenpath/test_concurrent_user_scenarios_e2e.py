"""
E2E Tests for Concurrent User Scenarios - Golden Path Multi-User Isolation

MISSION CRITICAL: Tests concurrent user scenarios to validate proper user isolation
and concurrent message processing in the Golden Path agent workflow. These tests ensure
that multiple users can simultaneously interact with agents without data contamination
or performance degradation.

Business Value Justification (BVJ):
- Segment: Enterprise Users (Multi-User Organizations)
- Business Goal: Platform Scalability & Enterprise Trust through Proper User Isolation
- Value Impact: Validates concurrent user support critical for enterprise adoption
- Strategic Impact: Poor concurrent handling = enterprise churn = $500K+ ARR loss

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- CONCURRENT EXECUTION: Multiple simultaneous WebSocket connections and agent requests
- USER ISOLATION: Strict validation that users cannot access each other's data
- PERFORMANCE VALIDATION: Response times under concurrent load remain acceptable
- RESOURCE MANAGEMENT: System handles multiple users without memory leaks or crashes

CRITICAL: These tests must demonstrate actual concurrent execution with proper isolation.
No mocking of concurrent scenarios or user separation allowed.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - Gap Area 1
Coverage Target: Advanced concurrent user scenarios (identified gap)
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import uuid
import concurrent.futures
import threading
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.concurrent_scenarios
@pytest.mark.mission_critical
class TestConcurrentUserScenariosE2E(SSotAsyncTestCase):
    """
    E2E tests for validating concurrent user scenarios in staging GCP.

    Tests multi-user isolation, concurrent processing, and performance
    under realistic concurrent load conditions.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment for concurrent user testing."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EAuthHelper(environment='staging')
        cls.websocket_helper = WebSocketTestHelper(base_url=cls.staging_config.urls.websocket_url, environment='staging')
        cls.CRITICAL_EVENTS = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        cls.logger.info(f'Concurrent user scenarios E2E tests initialized for staging')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.test_session_id = f'concurrent_test_{int(time.time())}'
        self.logger.info(f'Concurrent user test setup - session: {self.test_session_id}')

    async def _create_isolated_user_context(self, user_index: int) -> Dict[str, Any]:
        """Create completely isolated user context for concurrent testing."""
        user_context = {'user_id': f'concurrent_user_{user_index}_{self.test_session_id}', 'email': f'concurrent_user_{user_index}_{int(time.time())}@netra-testing.ai', 'thread_id': f'thread_{user_index}_{self.test_session_id}', 'run_id': f'run_{user_index}_{self.test_session_id}', 'conversation_id': str(uuid.uuid4()), 'user_index': user_index}
        user_context['access_token'] = self.__class__.auth_helper.create_test_jwt_token(user_id=user_context['user_id'], email=user_context['email'], exp_minutes=60)
        return user_context

    async def _establish_user_websocket_connection(self, user_context: Dict[str, Any]) -> websockets.ServerConnection:
        """Establish WebSocket connection for a specific user."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f"Bearer {user_context['access_token']}", 'X-Environment': 'staging', 'X-Test-Suite': 'concurrent-user-scenarios', 'X-User-Index': str(user_context['user_index']), 'X-Session-Id': self.test_session_id}, ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
        return websocket

    async def _process_concurrent_agent_request(self, user_context: Dict[str, Any], message: str, agent_type: str='triage_agent') -> Dict[str, Any]:
        """Process an agent request for a specific user and return comprehensive results."""
        start_time = time.time()
        try:
            websocket = await self._establish_user_websocket_connection(user_context)
            request_message = {'type': 'agent_request', 'agent': agent_type, 'message': message, 'thread_id': user_context['thread_id'], 'run_id': user_context['run_id'], 'user_id': user_context['user_id'], 'conversation_id': user_context['conversation_id'], 'context': {'concurrent_test': True, 'user_index': user_context['user_index'], 'isolation_validation': True}}
            message_sent_time = time.time()
            await websocket.send(json.dumps(request_message))
            user_events = []
            event_types = set()
            response_timeout = 60.0
            while time.time() - message_sent_time < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    user_events.append(event)
                    event_type = event.get('type', 'unknown')
                    event_types.add(event_type)
                    if event_type == 'agent_completed':
                        break
                    elif event_type in ['error', 'agent_error']:
                        raise AssertionError(f"Agent error for user {user_context['user_index']}: {event}")
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError as e:
                    self.logger.warning(f"JSON decode error for user {user_context['user_index']}: {e}")
                    continue
            await websocket.close()
            response_content = ''
            final_event = None
            for event in reversed(user_events):
                if event.get('type') == 'agent_completed':
                    final_event = event
                    response_data = event.get('data', {})
                    result = response_data.get('result', {})
                    if isinstance(result, dict):
                        response_content = result.get('response', str(result))
                    else:
                        response_content = str(result)
                    break
            total_time = time.time() - start_time
            return {'success': True, 'user_context': user_context, 'total_time': total_time, 'events_count': len(user_events), 'event_types': event_types, 'critical_events': event_types.intersection(self.__class__.CRITICAL_EVENTS), 'response_content': response_content, 'response_length': len(response_content), 'final_event': final_event, 'all_events': user_events}
        except Exception as e:
            total_time = time.time() - start_time
            return {'success': False, 'user_context': user_context, 'error': str(e), 'total_time': total_time, 'events_count': 0, 'event_types': set(), 'critical_events': set()}

    async def test_basic_concurrent_user_isolation(self):
        """
        Test basic concurrent user isolation with 3 simultaneous users.

        ISOLATION VALIDATION: Each user should receive only their own responses
        and events, with no cross-contamination between user sessions.

        Scenario:
        1. Create 3 isolated user contexts
        2. Send simultaneous agent requests with user-specific content
        3. Validate each user receives only their own responses
        4. Verify no data leakage between users
        5. Confirm performance remains acceptable under concurrent load

        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Multiple concurrent staging connections
        STATUS: Should PASS - Basic concurrent isolation is critical
        """
        self.logger.info('🏗️ Testing basic concurrent user isolation (3 users)')
        concurrent_users = 3
        user_contexts = []
        for i in range(concurrent_users):
            user_context = await self._create_isolated_user_context(i)
            user_contexts.append(user_context)
        user_specific_messages = [f"I'm User Alpha and I need help with AI optimization for my e-commerce platform. My unique identifier is ALPHA-{int(time.time())}.", f"I'm User Beta working on marketing automation cost reduction. My unique identifier is BETA-{int(time.time())}.", f"I'm User Gamma optimizing customer support chatbot expenses. My unique identifier is GAMMA-{int(time.time())}."]
        concurrent_tasks = []
        for i, user_context in enumerate(user_contexts):
            task = self._process_concurrent_agent_request(user_context, user_specific_messages[i], 'triage_agent')
            concurrent_tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_concurrent_time = time.time() - start_time
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_results = [r for r in results if isinstance(r, dict) and (not r.get('success'))]
        exception_results = [r for r in results if isinstance(r, Exception)]
        self.logger.info(f'📊 Concurrent Execution Results:')
        self.logger.info(f'   Successful: {len(successful_results)}/{concurrent_users}')
        self.logger.info(f'   Failed: {len(failed_results)}')
        self.logger.info(f'   Exceptions: {len(exception_results)}')
        self.logger.info(f'   Total Time: {total_concurrent_time:.2f}s')
        assert len(successful_results) == concurrent_users, f'All {concurrent_users} concurrent users should succeed. Successful: {len(successful_results)}, Failed: {failed_results}, Exceptions: {exception_results}'
        user_identifiers = ['ALPHA', 'BETA', 'GAMMA']
        for i, result in enumerate(successful_results):
            user_response = result['response_content'].upper()
            user_identifier = user_identifiers[i]
            assert user_identifier in user_response, f"User {i} should receive response with their identifier '{user_identifier}'. Response: {result['response_content'][:200]}..."
            other_identifiers = [uid for uid in user_identifiers if uid != user_identifier]
            for other_id in other_identifiers:
                assert other_id not in user_response, f"User {i} response should not contain other user identifier '{other_id}'. Response: {result['response_content'][:200]}..."
        response_times = [r['total_time'] for r in successful_results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        assert avg_response_time < 45.0, f'Average response time under concurrent load too high: {avg_response_time:.2f}s (max 45s)'
        assert max_response_time < 60.0, f'Maximum response time under concurrent load too high: {max_response_time:.2f}s (max 60s)'
        for i, result in enumerate(successful_results):
            critical_events_received = len(result['critical_events'])
            assert critical_events_received >= 3, f"User {i} should receive at least 3 critical events, got {critical_events_received}. Events: {result['event_types']}"
        for i, result in enumerate(successful_results):
            assert result['response_length'] >= 50, f"User {i} response too short: {result['response_length']} chars"
        self.logger.info(f'✅ Basic concurrent user isolation validated:')
        self.logger.info(f"   Response Times: {[f'{t:.1f}s' for t in response_times]}")
        self.logger.info(f'   Average: {avg_response_time:.1f}s, Max: {max_response_time:.1f}s')
        self.logger.info('🏗️ Basic concurrent user isolation test complete')

    async def test_high_concurrency_user_load(self):
        """
        Test higher concurrency with 5 simultaneous users to validate scalability.

        SCALABILITY VALIDATION: System should handle increased concurrent load
        without significant performance degradation or failures.

        Scenario:
        1. Create 5 isolated user contexts
        2. Send simultaneous agent requests with different complexity levels
        3. Validate system handles increased load gracefully
        4. Monitor resource usage and response times
        5. Ensure no user isolation failures under load

        DIFFICULTY: Very High (40 minutes)
        REAL SERVICES: Yes - High concurrent load testing in staging
        STATUS: Should PASS - Scalability essential for enterprise adoption
        """
        self.logger.info('🚀 Testing high concurrency user load (5 users)')
        concurrent_users = 5
        user_contexts = []
        for i in range(concurrent_users):
            user_context = await self._create_isolated_user_context(i)
            user_contexts.append(user_context)
        complexity_messages = [f'What is AI cost optimization? User ID: SIMPLE-{int(time.time())}', f'I need recommendations for reducing my $5,000/month OpenAI costs for customer support. User ID: MEDIUM-{int(time.time())}', f"Please analyze my AI infrastructure for comprehensive cost optimization. I'm spending $20,000/month across GPT-4, Claude, and custom models. Provide detailed analysis with market comparisons and implementation steps. User ID: COMPLEX-{int(time.time())}", f'As CTO of a B2B SaaS company, I need to optimize our AI costs while scaling from 1,000 to 10,000 customers. Current spend is $15K/month. User ID: BUSINESS-{int(time.time())}', f'I need technical implementation details for reducing API costs through prompt optimization, caching, and model selection strategies. Include specific code examples. User ID: TECHNICAL-{int(time.time())}']
        agent_types = ['triage_agent', 'triage_agent', 'apex_optimizer_agent', 'supervisor_agent', 'apex_optimizer_agent']
        concurrent_tasks = []
        for i, (user_context, message, agent_type) in enumerate(zip(user_contexts, complexity_messages, agent_types)):
            task = self._process_concurrent_agent_request(user_context, message, agent_type)
            concurrent_tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_execution_time = time.time() - start_time
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_results = [r for r in results if isinstance(r, dict) and (not r.get('success'))]
        exception_results = [r for r in results if isinstance(r, Exception)]
        self.logger.info(f'📊 High Concurrency Results:')
        self.logger.info(f'   Users: {concurrent_users}')
        self.logger.info(f'   Successful: {len(successful_results)}')
        self.logger.info(f'   Failed: {len(failed_results)}')
        self.logger.info(f'   Exceptions: {len(exception_results)}')
        self.logger.info(f'   Total Execution: {total_execution_time:.2f}s')
        success_rate = len(successful_results) / concurrent_users
        assert success_rate >= 0.8, f'High concurrency success rate too low: {success_rate:.1%} (min 80%). Successful: {len(successful_results)}/{concurrent_users}'
        expected_identifiers = ['SIMPLE', 'MEDIUM', 'COMPLEX', 'BUSINESS', 'TECHNICAL']
        for i, result in enumerate(successful_results):
            user_response = result['response_content'].upper()
            expected_id = expected_identifiers[result['user_context']['user_index']]
            assert expected_id in user_response, f"User {i} should receive their identifier '{expected_id}' under high load. Response: {result['response_content'][:200]}..."
        response_times = [r['total_time'] for r in successful_results]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            self.logger.info(f'📈 High Load Performance:')
            self.logger.info(f'   Average Response: {avg_response_time:.1f}s')
            self.logger.info(f'   Min Response: {min_response_time:.1f}s')
            self.logger.info(f'   Max Response: {max_response_time:.1f}s')
            assert avg_response_time < 75.0, f'Average response time under high load excessive: {avg_response_time:.2f}s (max 75s)'
            assert max_response_time < 120.0, f'Maximum response time under high load excessive: {max_response_time:.2f}s (max 120s)'
        total_events = sum((r['events_count'] for r in successful_results))
        assert total_events >= len(successful_results) * 3, f'Should receive adequate events under high load. Total events: {total_events}, Users: {len(successful_results)}'
        self.logger.info(f'✅ High concurrency load test validated:')
        self.logger.info(f'   Success Rate: {success_rate:.1%}')
        self.logger.info(f'   Performance: Avg {avg_response_time:.1f}s, Max {max_response_time:.1f}s')
        self.logger.info('🚀 High concurrency user load test complete')

    async def test_concurrent_agent_type_isolation(self):
        """
        Test concurrent users with different agent types to validate agent isolation.

        AGENT ISOLATION: Different agent types running concurrently should not
        interfere with each other's processing or context.

        Scenario:
        1. Create 4 users each using different agent types
        2. Send simultaneous requests to different agents
        3. Validate each agent processes correctly without interference
        4. Ensure agent-specific responses are delivered to correct users
        5. Verify no agent cross-contamination

        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes - Multi-agent concurrent execution in staging
        STATUS: Should PASS - Agent isolation critical for multi-user system
        """
        self.logger.info('🤖 Testing concurrent agent type isolation')
        agent_scenarios = [{'agent_type': 'triage_agent', 'message': f"Quick question: What's the best way to reduce AI API costs? User: TRIAGE-{int(time.time())}", 'expected_content': ['triage', 'quick', 'recommendation'], 'user_id': 'triage_user'}, {'agent_type': 'apex_optimizer_agent', 'message': f'I need comprehensive AI cost optimization analysis with detailed recommendations and market data. User: APEX-{int(time.time())}', 'expected_content': ['optimization', 'analysis', 'detailed'], 'user_id': 'apex_user'}, {'agent_type': 'supervisor_agent', 'message': f'Please coordinate a complete review of my AI infrastructure costs and provide strategic guidance. User: SUPERVISOR-{int(time.time())}', 'expected_content': ['strategic', 'coordinate', 'comprehensive'], 'user_id': 'supervisor_user'}, {'agent_type': 'data_helper_agent', 'message': f'Help me analyze the cost data for my AI operations and create performance metrics. User: DATA-{int(time.time())}', 'expected_content': ['data', 'analyze', 'metrics'], 'user_id': 'data_user'}]
        user_contexts = []
        for i, scenario in enumerate(agent_scenarios):
            user_context = await self._create_isolated_user_context(i)
            user_context['agent_scenario'] = scenario
            user_contexts.append(user_context)
        concurrent_tasks = []
        for user_context in user_contexts:
            scenario = user_context['agent_scenario']
            task = self._process_concurrent_agent_request(user_context, scenario['message'], scenario['agent_type'])
            concurrent_tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_results = [r for r in results if isinstance(r, dict) and (not r.get('success'))]
        exception_results = [r for r in results if isinstance(r, Exception)]
        self.logger.info(f'📊 Agent Type Isolation Results:')
        self.logger.info(f'   Agent Types: {len(agent_scenarios)}')
        self.logger.info(f'   Successful: {len(successful_results)}')
        self.logger.info(f'   Failed: {len(failed_results)}')
        self.logger.info(f'   Total Time: {total_time:.2f}s')
        assert len(successful_results) == len(agent_scenarios), f'All {len(agent_scenarios)} agent types should execute successfully. Successful: {len(successful_results)}, Failed: {failed_results}, Exceptions: {exception_results}'
        user_identifiers = ['TRIAGE', 'APEX', 'SUPERVISOR', 'DATA']
        for i, result in enumerate(successful_results):
            scenario = result['user_context']['agent_scenario']
            response = result['response_content'].upper()
            expected_identifier = user_identifiers[i]
            assert expected_identifier in response, f"Agent {scenario['agent_type']} should return user-specific content with '{expected_identifier}'. Response: {result['response_content'][:200]}..."
            other_identifiers = [uid for uid in user_identifiers if uid != expected_identifier]
            for other_id in other_identifiers:
                assert other_id not in response, f"Agent {scenario['agent_type']} response should not contain '{other_id}'. Agent isolation failure. Response: {result['response_content'][:200]}..."
        for result in successful_results:
            scenario = result['user_context']['agent_scenario']
            agent_type = scenario['agent_type']
            response = result['response_content'].lower()
            if agent_type == 'triage_agent':
                assert result['response_length'] >= 30, f"Triage agent should provide substantive response: {result['response_length']} chars"
            elif agent_type == 'apex_optimizer_agent':
                assert result['response_length'] >= 100, f"APEX agent should provide detailed analysis: {result['response_length']} chars"
            elif agent_type == 'supervisor_agent':
                assert result['response_length'] >= 80, f"Supervisor agent should provide strategic guidance: {result['response_length']} chars"
            elif agent_type == 'data_helper_agent':
                assert result['response_length'] >= 60, f"Data helper agent should provide analytical response: {result['response_length']} chars"
        response_times = [r['total_time'] for r in successful_results]
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 60.0, f'Average response time for concurrent agent types too high: {avg_response_time:.2f}s (max 60s)'
        for i, result in enumerate(successful_results):
            scenario = result['user_context']['agent_scenario']
            critical_events = len(result['critical_events'])
            assert critical_events >= 2, f"Agent {scenario['agent_type']} should deliver critical events. Got {critical_events}: {result['event_types']}"
        self.logger.info(f'✅ Concurrent agent type isolation validated:')
        self.logger.info(f"   Agent Types: {[s['agent_type'] for s in agent_scenarios]}")
        self.logger.info(f"   Response Times: {[f'{t:.1f}s' for t in response_times]}")
        self.logger.info(f'   Average Time: {avg_response_time:.1f}s')
        self.logger.info('🤖 Concurrent agent type isolation test complete')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')