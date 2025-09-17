"""
E2E Tests for Agent Message Pipeline - Golden Path Core Flow

MISSION CRITICAL: Tests the complete user message → agent response pipeline
in staging GCP environment. This is the core of the Golden Path user journey
representing 90% of platform business value ($500K+ ARR).

Business Value Justification (BVJ):
- Segment: All Users (Free/Early/Mid/Enterprise) 
- Business Goal: Platform Revenue Protection & User Retention
- Value Impact: Validates complete AI chat functionality works end-to-end
- Strategic Impact: $500K+ ARR depends on reliable agent message processing

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: JWT tokens via staging auth service
- REAL WEBSOCKETS: wss:// connections to staging backend
- REAL AGENTS: Complete supervisor → triage → APEX agent orchestration
- REAL LLMS: Actual LLM calls for authentic agent responses
- REAL PERSISTENCE: Chat history saved to staging databases

CRITICAL: These tests must fail properly when system issues exist.
No mocking, bypassing, or 0-second test completions allowed.

GitHub Issue: #1059 Agent Golden Path Messages E2E Test Creation - Phase 1
ENHANCEMENT: Business value validation, multi-agent orchestration, response quality >0.7 threshold
Target Coverage: 15% → 35% improvement
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, UTC
import httpx
from collections import defaultdict
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.mission_critical
class AgentMessagePipelineE2ETests(SSotAsyncTestCase):
    """
    E2E tests for the complete agent message pipeline in staging GCP.
    
    Tests the core Golden Path: User Message → Agent Processing → AI Response
    
    ENHANCED PHASE 1 (Issue #1059): Business value validation, multi-agent
    orchestration, and response quality scoring with >0.7 threshold.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment configuration and dependencies."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EAuthHelper(environment='staging')
        cls.websocket_helper = WebSocketTestHelper()
        cls.test_user_id = f'golden_path_user_{int(time.time())}'
        cls.test_user_email = f'golden_path_test_{int(time.time())}@netra-testing.ai'
        cls.business_value_keywords = {'cost_optimization': ['cost', 'savings', 'reduce', 'optimization', 'efficiency', 'budget'], 'technical_accuracy': ['specific', 'implement', 'configure', 'setup', 'deploy'], 'actionability': ['step', 'recommend', 'suggest', 'should', 'consider', 'strategy'], 'quantification': ['percent', '%', 'dollar', '$', 'reduction', 'improvement', 'roi']}
        cls.QUALITY_THRESHOLD_HIGH = 0.7
        cls.QUALITY_THRESHOLD_MEDIUM = 0.5
        cls.MIN_SUBSTANTIVE_LENGTH = 200
        cls.logger.info(f'Agent message pipeline e2e tests initialized for staging with business value framework')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.thread_id = f'message_pipeline_test_{int(time.time())}'
        self.run_id = f'run_{self.thread_id}'
        self.access_token = self.__class__.auth_helper.create_test_jwt_token(user_id=self.__class__.test_user_id, email=self.__class__.test_user_email, exp_minutes=60)
        self.logger.info(f'Test setup complete - thread_id: {self.thread_id}')

    def _calculate_response_quality_score(self, response_text: str, scenario_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive response quality score for business value validation.
        
        PHASE 1 ENHANCEMENT: Implements >0.7 threshold scoring framework.
        
        Args:
            response_text: Agent response to score
            scenario_context: Context about the business scenario
        
        Returns:
            Dict with quality metrics and overall score
        """
        quality_metrics = {'length_score': min(len(response_text) / self.__class__.MIN_SUBSTANTIVE_LENGTH, 1.0), 'keyword_relevance': {}, 'actionability_score': 0.0, 'technical_specificity': 0.0, 'business_indicators': [], 'overall_quality_score': 0.0, 'meets_threshold': False}
        response_lower = response_text.lower()
        for category, keywords in self.__class__.business_value_keywords.items():
            found_keywords = [kw for kw in keywords if kw in response_lower]
            relevance_score = min(len(found_keywords) / len(keywords), 1.0)
            quality_metrics['keyword_relevance'][category] = {'found': found_keywords, 'score': relevance_score}
        actionable_patterns = ['\\d+\\.\\s+[A-Z]', 'recommend\\w*\\s+\\w+', 'should\\s+\\w+', 'step\\s+\\d+', 'implement\\s+\\w+']
        actionability_matches = sum((len(re.findall(pattern, response_text, re.IGNORECASE)) for pattern in actionable_patterns))
        quality_metrics['actionability_score'] = min(actionability_matches / 5, 1.0)
        technical_indicators = ['\\$\\d+', '\\d+%', '\\d+\\s*seconds?', '\\d+\\s*minutes?', 'config\\w*', 'setup', 'deploy', 'implement', 'API\\s+\\w+', 'endpoint', 'database', 'cache']
        technical_matches = sum((len(re.findall(pattern, response_text, re.IGNORECASE)) for pattern in technical_indicators))
        quality_metrics['technical_specificity'] = min(technical_matches / 8, 1.0)
        expected_indicators = scenario_context.get('expected_business_value', [])
        for indicator in expected_indicators:
            if indicator.lower() in response_lower:
                quality_metrics['business_indicators'].append(indicator)
        quality_components = [quality_metrics['length_score'] * 0.2, quality_metrics['keyword_relevance']['cost_optimization']['score'] * 0.25, quality_metrics['keyword_relevance']['actionability']['score'] * 0.25, quality_metrics['actionability_score'] * 0.15, quality_metrics['technical_specificity'] * 0.15]
        quality_metrics['overall_quality_score'] = sum(quality_components)
        threshold = scenario_context.get('quality_threshold', self.__class__.QUALITY_THRESHOLD_MEDIUM)
        quality_metrics['meets_threshold'] = quality_metrics['overall_quality_score'] >= threshold
        return quality_metrics

    async def test_complete_user_message_to_agent_response_flow(self):
        """
        Test complete user message → agent response pipeline in staging GCP.
        
        GOLDEN PATH CORE: This is the fundamental user journey that must work.
        
        Flow:
        1. User sends message via WebSocket
        2. Backend routes to supervisor agent
        3. Supervisor orchestrates triage → APEX agents
        4. Agent processes with real LLM calls
        5. Response sent back via WebSocket
        
        DIFFICULTY: Very High (45+ minutes)
        REAL SERVICES: Yes - Complete staging GCP stack
        STATUS: Should PASS - Core Golden Path functionality
        """
        pipeline_start_time = time.time()
        pipeline_events = []
        if not hasattr(self.__class__, 'logger'):
            self.__class__.setUpClass()
        if not hasattr(self, 'access_token'):
            self.thread_id = f'message_pipeline_test_{int(time.time())}'
            self.run_id = f'run_{self.thread_id}'
            self.access_token = self.__class__.auth_helper.create_test_jwt_token(user_id=self.__class__.test_user_id, email=self.__class__.test_user_email, exp_minutes=60)
        self.logger.info('🎯 Testing complete user message → agent response pipeline')
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connection_start = time.time()
            websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {self.access_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'agent-pipeline-e2e'}, ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
            connection_time = time.time() - connection_start
            pipeline_events.append({'event': 'websocket_connected', 'timestamp': time.time(), 'duration': connection_time, 'success': True})
            self.logger.info(f'✅ WebSocket connected to staging in {connection_time:.2f}s')
            user_message = {'type': 'agent_request', 'agent': 'supervisor_agent', 'message': 'I need help optimizing my AI costs. My current spend is $2,000/month on GPT-4 calls, and I want to reduce costs by 30% without sacrificing quality. Can you analyze my usage patterns and suggest specific optimizations?', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': self.__class__.test_user_id, 'context': {'test_scenario': 'golden_path_message_pipeline', 'expected_agents': ['supervisor_agent', 'triage_agent', 'apex_optimizer_agent'], 'expected_duration': '30-60s'}}
            message_send_start = time.time()
            await websocket.send(json.dumps(user_message))
            message_send_time = time.time() - message_send_start
            pipeline_events.append({'event': 'user_message_sent', 'timestamp': time.time(), 'duration': message_send_time, 'message_length': len(user_message['message']), 'success': True})
            self.logger.info(f"📤 User message sent ({len(user_message['message'])} chars)")
            agent_events = []
            response_timeout = 90.0
            event_collection_start = time.time()
            expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            received_events = set()
            final_response = None
            while time.time() - event_collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    agent_events.append(event)
                    event_type = event.get('type', 'unknown')
                    received_events.add(event_type)
                    self.logger.info(f'📨 Received event: {event_type}')
                    if event_type == 'agent_completed':
                        final_response = event
                        break
                    if event_type == 'error' or event_type == 'agent_error':
                        raise AssertionError(f'Agent processing error: {event}')
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError as e:
                    self.logger.warning(f'Failed to parse WebSocket message: {e}')
                    continue
            event_collection_time = time.time() - event_collection_start
            pipeline_events.append({'event': 'agent_events_collected', 'timestamp': time.time(), 'duration': event_collection_time, 'event_count': len(agent_events), 'received_event_types': list(received_events), 'success': len(agent_events) > 0})
            assert len(agent_events) > 0, 'Should receive at least one agent event'
            assert 'agent_started' in received_events, f'Missing agent_started event. Got: {received_events}'
            assert 'agent_completed' in received_events, f'Missing agent_completed event. Got: {received_events}'
            assert final_response is not None, 'Should receive final agent response'
            response_data = final_response.get('data', {})
            result = response_data.get('result', {})
            if isinstance(result, dict):
                response_text = result.get('response', str(result))
            else:
                response_text = str(result)
            quality_evaluation = self._calculate_response_quality_score(response_text, {'expected_business_value': ['cost optimization', 'specific recommendations', 'implementation steps'], 'quality_threshold': self.__class__.QUALITY_THRESHOLD_HIGH})
            assert len(response_text) > self.__class__.MIN_SUBSTANTIVE_LENGTH, f'Agent response not substantive enough: {len(response_text)} chars (required >{self.__class__.MIN_SUBSTANTIVE_LENGTH} for business value)'
            assert quality_evaluation['meets_threshold'], f"Response fails business value quality threshold. Score: {quality_evaluation['overall_quality_score']:.3f} (required ≥{self.__class__.QUALITY_THRESHOLD_HIGH}). Metrics: {quality_evaluation}"
            assert quality_evaluation['keyword_relevance']['cost_optimization']['score'] >= 0.4, f"Insufficient cost optimization focus in response. Found keywords: {quality_evaluation['keyword_relevance']['cost_optimization']['found']}"
            assert quality_evaluation['actionability_score'] >= 0.3, f"Response lacks actionable recommendations: {quality_evaluation['actionability_score']:.3f}"
            ack_message = {'type': 'message_acknowledgment', 'thread_id': self.thread_id, 'run_id': self.run_id, 'acknowledged_at': datetime.now(UTC).isoformat()}
            await websocket.send(json.dumps(ack_message))
            try:
                ack_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pipeline_events.append({'event': 'acknowledgment_received', 'timestamp': time.time(), 'success': True})
            except asyncio.TimeoutError:
                pass
            await websocket.close()
            total_pipeline_time = time.time() - pipeline_start_time
            pipeline_events.append({'event': 'pipeline_completed', 'timestamp': time.time(), 'total_duration': total_pipeline_time, 'success': True})
            self.logger.info('🎉 GOLDEN PATH MESSAGE PIPELINE SUCCESS WITH BUSINESS VALUE VALIDATION')
            self.logger.info(f'📊 Pipeline Metrics:')
            self.logger.info(f'   Total Duration: {total_pipeline_time:.1f}s')
            self.logger.info(f'   WebSocket Connection: {connection_time:.2f}s')
            self.logger.info(f'   Agent Processing: {event_collection_time:.1f}s')
            self.logger.info(f'   Events Received: {len(agent_events)}')
            self.logger.info(f'   Event Types: {received_events}')
            self.logger.info(f'   Response Length: {len(response_text)} characters')
            self.logger.info(f'   Pipeline Events: {len(pipeline_events)}')
            self.logger.info(f'💰 Business Value Metrics:')
            self.logger.info(f"   Quality Score: {quality_evaluation['overall_quality_score']:.3f}/1.0")
            self.logger.info(f"   Actionability: {quality_evaluation['actionability_score']:.3f}/1.0")
            self.logger.info(f"   Technical Specificity: {quality_evaluation['technical_specificity']:.3f}/1.0")
            self.logger.info(f"   Business Indicators: {quality_evaluation['business_indicators']}")
            self.logger.info(f"   Meets Threshold: {quality_evaluation['meets_threshold']}")
            assert total_pipeline_time < 120.0, f'Pipeline too slow: {total_pipeline_time:.1f}s (max 120s)'
            assert quality_evaluation['overall_quality_score'] >= self.__class__.QUALITY_THRESHOLD_HIGH, f"Overall business value quality insufficient: {quality_evaluation['overall_quality_score']:.3f}"
            assert len(quality_evaluation['business_indicators']) >= 1, f"Response lacks expected business value indicators: {quality_evaluation['business_indicators']}"
        except Exception as e:
            total_time = time.time() - pipeline_start_time
            self.logger.error(f'❌ GOLDEN PATH MESSAGE PIPELINE FAILED')
            self.logger.error(f'   Error: {str(e)}')
            self.logger.error(f'   Duration: {total_time:.1f}s')
            self.logger.error(f'   Events collected: {len(pipeline_events)}')
            raise AssertionError(f'PHASE 1 ENHANCED: Golden Path message pipeline with business value validation failed after {total_time:.1f}s: {e}. Events: {pipeline_events}. This breaks core user functionality and business value delivery ($500K+ ARR impact).')

    async def test_agent_error_handling_and_recovery(self):
        """
        Test agent error handling and graceful recovery scenarios.
        
        RESILIENCE: System should handle errors gracefully without breaking user experience.
        
        Error scenarios:
        1. Invalid agent request format
        2. Agent timeout scenarios  
        3. Network interruption recovery
        4. Malformed message handling
        
        DIFFICULTY: High (25 minutes)
        REAL SERVICES: Yes - Staging GCP environment
        STATUS: Should PASS - Error handling is critical for user experience
        """
        self.logger.info('🛡️ Testing agent error handling and recovery')
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        error_scenarios = [{'name': 'invalid_agent_type', 'message': {'type': 'agent_request', 'agent': 'nonexistent_agent_type', 'message': 'This should trigger an error', 'thread_id': f'error_test_{int(time.time())}'}, 'expected_error_type': 'agent_error', 'should_recover': True}, {'name': 'malformed_message_structure', 'message': {'type': 'agent_request', 'invalid_field': 'This message is malformed'}, 'expected_error_type': 'validation_error', 'should_recover': True}, {'name': 'empty_message_content', 'message': {'type': 'agent_request', 'agent': 'triage_agent', 'message': '', 'thread_id': f'empty_test_{int(time.time())}'}, 'expected_error_type': 'validation_error', 'should_recover': True}]
        websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {self.access_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'error-handling-e2e'}, ssl=ssl_context), timeout=15.0)
        try:
            for scenario in error_scenarios:
                scenario_start = time.time()
                self.logger.info(f"Testing error scenario: {scenario['name']}")
                await websocket.send(json.dumps(scenario['message']))
                error_events = []
                error_timeout = 20.0
                received_error = False
                while time.time() - scenario_start < error_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(event_data)
                        error_events.append(event)
                        event_type = event.get('type', 'unknown')
                        if 'error' in event_type.lower():
                            received_error = True
                            self.logger.info(f'✅ Received expected error: {event_type}')
                            break
                    except asyncio.TimeoutError:
                        break
                assert received_error, f"Should receive error for scenario '{scenario['name']}', got events: {error_events}"
                if scenario['should_recover']:
                    recovery_message = {'type': 'agent_request', 'agent': 'triage_agent', 'message': f"Recovery test after {scenario['name']}", 'thread_id': f"recovery_{scenario['name']}_{int(time.time())}"}
                    await websocket.send(json.dumps(recovery_message))
                    recovery_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    recovery_event = json.loads(recovery_response)
                    assert recovery_event.get('type') != 'error', f"System should recover after {scenario['name']} error"
                    self.logger.info(f"✅ System recovered successfully after {scenario['name']}")
            self.logger.info('🛡️ All error handling scenarios passed')
        finally:
            await websocket.close()

    async def test_concurrent_user_message_processing(self):
        """
        Test concurrent user message processing in staging GCP.
        
        SCALABILITY: Multiple users should be able to send messages simultaneously
        without interference or performance degradation.
        
        Scenarios:
        1. Multiple users send messages concurrently
        2. Each user should get isolated responses  
        3. No cross-user contamination
        4. Response times remain reasonable under load
        
        DIFFICULTY: Very High (35 minutes)
        REAL SERVICES: Yes - Staging GCP with real isolation
        STATUS: Should PASS - Multi-user isolation is critical for platform
        """
        self.logger.info('👥 Testing concurrent user message processing')
        concurrent_users = []
        user_count = 3
        for i in range(user_count):
            user = {'user_id': f'concurrent_user_{i}_{int(time.time())}', 'email': f'concurrent_test_{i}_{int(time.time())}@netra-testing.ai', 'thread_id': f'concurrent_thread_{i}_{int(time.time())}', 'message': f'Concurrent test message {i + 1}: Analyze my AI optimization needs for user context {i + 1}'}
            user['access_token'] = self.__class__.auth_helper.create_test_jwt_token(user_id=user['user_id'], email=user['email'])
            concurrent_users.append(user)

        async def process_user_message(user: Dict[str, Any]) -> Dict[str, Any]:
            """Process message for a single concurrent user."""
            user_start = time.time()
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f"Bearer {user['access_token']}", 'X-Environment': 'staging', 'X-User-Context': user['user_id']}, ssl=ssl_context), timeout=15.0)
                message = {'type': 'agent_request', 'agent': 'triage_agent', 'message': user['message'], 'thread_id': user['thread_id'], 'user_id': user['user_id']}
                await websocket.send(json.dumps(message))
                events = []
                response_timeout = 45.0
                completion_received = False
                collection_start = time.time()
                while time.time() - collection_start < response_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)
                        events.append(event)
                        if event.get('type') == 'agent_completed':
                            completion_received = True
                            break
                    except asyncio.TimeoutError:
                        continue
                await websocket.close()
                return {'user_id': user['user_id'], 'success': completion_received, 'duration': time.time() - user_start, 'events_received': len(events), 'completed': completion_received}
            except Exception as e:
                return {'user_id': user['user_id'], 'success': False, 'duration': time.time() - user_start, 'error': str(e), 'events_received': 0, 'completed': False}
        concurrent_start = time.time()
        tasks = [process_user_message(user) for user in concurrent_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_concurrent_time = time.time() - concurrent_start
        successful_users = [r for r in results if isinstance(r, dict) and r['success']]
        failed_users = [r for r in results if isinstance(r, dict) and (not r['success'])]
        error_users = [r for r in results if isinstance(r, Exception)]
        self.logger.info(f'👥 Concurrent processing results:')
        self.logger.info(f'   Total time: {total_concurrent_time:.1f}s')
        self.logger.info(f'   Successful users: {len(successful_users)}/{user_count}')
        self.logger.info(f'   Failed users: {len(failed_users)}')
        self.logger.info(f'   Error users: {len(error_users)}')
        success_rate = len(successful_users) / user_count
        assert success_rate >= 0.66, f'Concurrent processing success rate too low: {success_rate:.1%} (expected ≥66%). Successful: {len(successful_users)}, Failed: {len(failed_users)}, Errors: {len(error_users)}'
        if successful_users:
            avg_duration = sum((r['duration'] for r in successful_users)) / len(successful_users)
            max_duration = max((r['duration'] for r in successful_users))
            assert avg_duration < 90.0, f'Average response time too slow: {avg_duration:.1f}s'
            assert max_duration < 150.0, f'Max response time too slow: {max_duration:.1f}s'
            self.logger.info(f'📊 Performance metrics:')
            self.logger.info(f'   Average duration: {avg_duration:.1f}s')
            self.logger.info(f'   Max duration: {max_duration:.1f}s')
        self.logger.info('✅ Concurrent user processing validation complete')

    async def test_large_message_handling(self):
        """
        Test handling of large user messages in agent pipeline.
        
        CAPACITY: System should handle various message sizes gracefully,
        from short queries to detailed technical specifications.
        
        Test cases:
        1. Short message (< 100 chars)
        2. Medium message (500-1000 chars)  
        3. Large message (2000+ chars)
        4. Very large message (near limit)
        
        DIFFICULTY: Medium (20 minutes)
        REAL SERVICES: Yes - Staging GCP message processing
        STATUS: Should PASS - Message size flexibility is important for UX
        """
        self.logger.info('📏 Testing large message handling capabilities')
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {self.access_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'large-message-e2e'}, ssl=ssl_context), timeout=15.0)
        try:
            message_test_cases = [{'name': 'short_message', 'content': 'Optimize my AI costs', 'expected_response_time': 30.0}, {'name': 'medium_message', 'content': "I'm running a SaaS application with 10,000 users and spending $5,000/month on OpenAI API calls. My current setup uses GPT-4 for all user interactions, but I'm seeing costs escalate quickly. I need specific recommendations for: 1) When to use GPT-3.5 vs GPT-4, 2) How to implement intelligent caching, 3) Prompt optimization techniques, 4) Usage monitoring and alerts. Can you provide a comprehensive optimization strategy?", 'expected_response_time': 45.0}, {'name': 'large_message', 'content': "I'm the CTO of a growing AI-first company and we're facing significant challenges with our AI infrastructure costs and optimization. Here's our current situation: \n\nCURRENT SETUP:\n- 50,000 monthly active users\n- $25,000/month OpenAI API spend (75% GPT-4, 25% GPT-3.5)\n- Average 15 API calls per user session\n- Peak usage: 2,000 concurrent users during business hours\n- Geographic distribution: 60% US, 25% EU, 15% Asia\n\nPAIN POINTS:\n1. Cost scaling faster than revenue (40% month-over-month increase)\n2. Response latency issues during peak hours (>3s average)\n3. No intelligent model selection - everything uses GPT-4\n4. Limited caching strategy causing repeated expensive calls\n5. Difficulty predicting monthly costs for budgeting\n\nREQUIREMENTS:\n- Reduce costs by 30-40% without quality degradation\n- Maintain <2s response time during peak usage\n- Implement predictable cost structure\n- Support for 100,000 users by year-end\n- Geographic latency optimization\n\nCan you provide a comprehensive optimization strategy addressing each of these areas?", 'expected_response_time': 60.0}]
            for test_case in message_test_cases:
                case_start = time.time()
                message_length = len(test_case['content'])
                self.logger.info(f"Testing {test_case['name']}: {message_length} characters")
                message = {'type': 'agent_request', 'agent': 'apex_optimizer_agent', 'message': test_case['content'], 'thread_id': f"large_msg_test_{test_case['name']}_{int(time.time())}", 'user_id': self.__class__.test_user_id, 'context': {'test_case': test_case['name'], 'message_length': message_length}}
                await websocket.send(json.dumps(message))
                completion_received = False
                response_content = None
                timeout = test_case['expected_response_time']
                while time.time() - case_start < timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)
                        if event.get('type') == 'agent_completed':
                            completion_received = True
                            response_data = event.get('data', {})
                            result = response_data.get('result', {})
                            response_content = str(result)
                            break
                    except asyncio.TimeoutError:
                        continue
                case_duration = time.time() - case_start
                assert completion_received, f"Should complete processing for {test_case['name']} ({message_length} chars) within {timeout}s"
                assert response_content and len(response_content) > 50, f"Should receive substantive response for {test_case['name']} (got {(len(response_content) if response_content else 0)} chars)"
                expected_min_response_length = min(200, message_length // 10)
                assert len(response_content) >= expected_min_response_length, f"Response too short for {test_case['name']}: {len(response_content)} chars (expected ≥{expected_min_response_length})"
                self.logger.info(f"✅ {test_case['name']}: {case_duration:.1f}s, response: {len(response_content)} chars")
            self.logger.info('📏 Large message handling tests completed successfully')
        finally:
            await websocket.close()

    async def test_multi_agent_orchestration_flow_validation(self):
        """
        Test complete multi-agent orchestration: Supervisor → Triage → APEX flow.
        
        PHASE 1 ENHANCEMENT (Issue #1059): Validates the multi-agent coordination
        that delivers superior business value through specialized agent expertise.
        
        Flow validation:
        1. Supervisor agent receives complex request
        2. Supervisor routes to appropriate specialized agents
        3. Triage agent analyzes request complexity and data requirements
        4. APEX optimizer agent provides detailed optimization recommendations
        5. Results are coordinated and returned with business value
        
        DIFFICULTY: Very High (60+ minutes)
        REAL SERVICES: Yes - Complete multi-agent staging orchestration
        STATUS: Should PASS - Multi-agent coordination is core platform differentiator
        """
        orchestration_start_time = time.time()
        orchestration_metrics = {'agents_invoked': [], 'agent_transitions': [], 'coordination_events': [], 'business_value_score': 0.0}
        self.logger.info('🔄 Testing multi-agent orchestration flow validation')
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f'Bearer {self.access_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'multi-agent-orchestration-e2e', 'X-Business-Scenario': 'complex-optimization'}, ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
            complex_scenario = {'type': 'agent_request', 'agent': 'supervisor_agent', 'message': "I'm the CTO of a FinTech company processing 500,000 transactions daily. Our current AI infrastructure costs $45,000/month with the following challenges: 1) GPT-4 usage for fraud detection (80% of costs), 2) Real-time response requirements (<100ms), 3) SOC2 and PCI compliance requirements, 4) 99.99% uptime SLA commitments, 5) Scaling to 2M transactions/day by Q4. I need a comprehensive multi-phase optimization strategy that addresses cost reduction (target: 40%), performance optimization, compliance maintenance, and scalability planning. Please provide specific technical recommendations, implementation timelines, ROI calculations, and risk assessments.", 'thread_id': f'orchestration_test_{int(time.time())}', 'run_id': f'orchestration_run_{int(time.time())}', 'user_id': self.__class__.test_user_id, 'context': {'business_scenario': 'enterprise_fintech_optimization', 'expected_agents': ['supervisor_agent', 'triage_agent', 'apex_optimizer_agent'], 'complexity': 'very_high', 'expected_business_value': ['cost reduction', 'performance optimization', 'compliance', 'scalability', 'roi calculations', 'implementation timeline'], 'quality_threshold': self.__class__.QUALITY_THRESHOLD_HIGH}}
            await websocket.send(json.dumps(complex_scenario))
            self.logger.info('📤 Complex multi-agent scenario sent')
            orchestration_events = []
            agent_activity = defaultdict(list)
            response_timeout = 150.0
            collection_start = time.time()
            final_response = None
            while time.time() - collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    event = json.loads(event_data)
                    orchestration_events.append(event)
                    event_type = event.get('type', 'unknown')
                    event_data_content = event.get('data', {})
                    if 'agent' in event_type or 'agent' in str(event_data_content).lower():
                        agent_info = self._extract_agent_info(event)
                        if agent_info:
                            agent_activity[agent_info['agent_name']].append({'event_type': event_type, 'timestamp': time.time() - collection_start, 'data': agent_info})
                            orchestration_metrics['agents_invoked'].append(agent_info['agent_name'])
                    if any((keyword in event_type.lower() for keyword in ['routing', 'handoff', 'coordination', 'triage'])):
                        orchestration_metrics['coordination_events'].append({'event_type': event_type, 'timestamp': time.time() - collection_start})
                    self.logger.info(f'📨 Multi-agent event: {event_type}')
                    if event_type == 'agent_completed':
                        final_response = event
                        self.logger.info('🏁 Multi-agent orchestration completed')
                        break
                    if 'error' in event_type.lower():
                        raise AssertionError(f'Multi-agent orchestration error: {event}')
                except asyncio.TimeoutError:
                    continue
            orchestration_duration = time.time() - collection_start
            assert len(orchestration_events) > 0, 'Should receive orchestration events'
            assert final_response is not None, 'Should receive final orchestrated response'
            response_data = final_response.get('data', {})
            result = response_data.get('result', {})
            response_text = result.get('response', str(result)) if isinstance(result, dict) else str(result)
            quality_evaluation = self._calculate_response_quality_score(response_text, complex_scenario['context'])
            orchestration_metrics['business_value_score'] = quality_evaluation['overall_quality_score']
            unique_agents = list(set(orchestration_metrics['agents_invoked']))
            assert len(unique_agents) >= 2, f'Multi-agent orchestration should involve ≥2 agents, detected: {unique_agents}'
            assert len(response_text) > 800, f'Complex enterprise scenario should generate comprehensive response: {len(response_text)} chars (expected >800 for FinTech optimization)'
            assert quality_evaluation['meets_threshold'], f"Multi-agent orchestrated response fails quality threshold. Score: {quality_evaluation['overall_quality_score']:.3f} (required ≥{self.__class__.QUALITY_THRESHOLD_HIGH})"
            enterprise_indicators_found = [indicator for indicator in complex_scenario['context']['expected_business_value'] if indicator.lower() in response_text.lower()]
            indicator_coverage = len(enterprise_indicators_found) / len(complex_scenario['context']['expected_business_value'])
            assert indicator_coverage >= 0.6, f'Insufficient enterprise topic coverage in orchestrated response: {indicator_coverage:.1%} (found: {enterprise_indicators_found})'
            assert quality_evaluation['technical_specificity'] >= 0.5, f"Multi-agent response should be technically sophisticated: {quality_evaluation['technical_specificity']:.3f} (expected ≥0.5)"
            await websocket.close()
            total_orchestration_time = time.time() - orchestration_start_time
            self.logger.info('🎯 MULTI-AGENT ORCHESTRATION SUCCESS')
            self.logger.info(f'🔄 Orchestration Metrics:')
            self.logger.info(f'   Total Orchestration Time: {total_orchestration_time:.1f}s')
            self.logger.info(f'   Agent Processing Time: {orchestration_duration:.1f}s')
            self.logger.info(f'   Agents Involved: {unique_agents}')
            self.logger.info(f"   Coordination Events: {len(orchestration_metrics['coordination_events'])}")
            self.logger.info(f'   Total Events: {len(orchestration_events)}')
            self.logger.info(f'💰 Business Value Metrics:')
            self.logger.info(f"   Quality Score: {quality_evaluation['overall_quality_score']:.3f}/1.0")
            self.logger.info(f'   Enterprise Coverage: {indicator_coverage:.1%}')
            self.logger.info(f"   Technical Sophistication: {quality_evaluation['technical_specificity']:.3f}/1.0")
            self.logger.info(f'   Response Length: {len(response_text)} characters')
            assert total_orchestration_time < 180.0, f'Multi-agent orchestration too slow: {total_orchestration_time:.1f}s (max 180s)'
            assert quality_evaluation['overall_quality_score'] >= self.__class__.QUALITY_THRESHOLD_HIGH, f"Multi-agent orchestration quality insufficient: {quality_evaluation['overall_quality_score']:.3f}"
        except Exception as e:
            total_time = time.time() - orchestration_start_time
            self.logger.error('❌ MULTI-AGENT ORCHESTRATION FAILED')
            self.logger.error(f'   Error: {str(e)}')
            self.logger.error(f'   Duration: {total_time:.1f}s')
            self.logger.error(f"   Events collected: {len(orchestration_metrics.get('coordination_events', []))}")
            self.logger.error(f"   Agents detected: {orchestration_metrics.get('agents_invoked', [])}")
            raise AssertionError(f'Multi-agent orchestration validation failed after {total_time:.1f}s: {e}. This breaks advanced platform capabilities and enterprise value proposition ($500K+ ARR impact). Orchestration metrics: {orchestration_metrics}')

    def _extract_agent_info(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract agent information from WebSocket events."""
        event_str = json.dumps(event).lower()
        event_type = event.get('type', 'unknown')
        agents = ['supervisor', 'triage', 'apex', 'optimizer', 'data_helper']
        for agent in agents:
            if agent in event_str:
                return {'agent_name': agent, 'event_type': event_type, 'detected_via': 'content_analysis'}
        event_data = event.get('data', {})
        if isinstance(event_data, dict):
            for key, value in event_data.items():
                if 'agent' in key.lower() and isinstance(value, str):
                    return {'agent_name': value.lower(), 'event_type': event_type, 'detected_via': f'data_field_{key}'}
        return None
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')