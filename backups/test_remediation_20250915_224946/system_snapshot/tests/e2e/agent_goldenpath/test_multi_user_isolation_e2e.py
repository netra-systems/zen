"""
E2E Tests for Multi-User Isolation - Golden Path Concurrent User Validation

MISSION CRITICAL: Tests that multiple users can use the agent system concurrently
without interference, data leakage, or performance degradation. This validates
the platform's ability to serve multiple customers simultaneously.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid-Market (Multi-tenant customers)
- Business Goal: Platform Scalability & Enterprise Trust
- Value Impact: Proves platform can serve multiple enterprise customers safely
- Strategic Impact: $500K+ ARR depends on enterprise confidence in isolation

Multi-User Isolation Requirements:
1. Complete user context isolation (no data leakage between users)
2. Concurrent WebSocket connections without interference
3. Independent agent processing per user
4. User-specific response delivery (no cross-contamination)
5. Scalable performance under multi-user load

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: Unique JWT tokens per test user
- REAL WEBSOCKETS: Concurrent wss:// connections per user
- REAL AGENTS: Independent agent contexts per user
- ISOLATION VALIDATION: Cross-user data leakage prevention testing

CRITICAL: These tests must validate USER ISOLATION, not just concurrent capacity.
Data privacy and context separation are primary success metrics.

GitHub Issue: #1059 Agent Golden Path Messages E2E Test Creation
Phase: Phase 1 - Multi-User Isolation Enhancement
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
import uuid
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.multi_user_isolation
@pytest.mark.mission_critical
class MultiUserIsolationE2ETests(SSotAsyncTestCase):
    """
    E2E tests validating complete multi-user isolation in the agent system.

    Tests that concurrent users receive isolated, secure agent processing
    without data leakage or interference between user contexts.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment configuration and multi-user test utilities."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available for multi-user isolation validation')
        cls.auth_helper = E2EAuthHelper(environment='staging')
        cls.websocket_helper = WebSocketTestHelper()
        cls.max_concurrent_users = 4
        cls.isolation_test_scenarios = ['cost_optimization', 'performance_analysis', 'security_assessment', 'infrastructure_review']
        cls.logger.info(f'Multi-user isolation tests initialized for staging')

    def setup_method(self, method):
        """Setup for each multi-user isolation test method."""
        super().setup_method(method)
        self.test_session_id = f'multi_user_session_{int(time.time())}'
        self.logger.info(f'Multi-user isolation test setup - session: {self.test_session_id}')

    def _create_test_user(self, user_index: int, scenario: str) -> Dict[str, Any]:
        """
        Create isolated test user with unique context.

        Args:
            user_index: Numeric index for user identification
            scenario: Business scenario this user will test

        Returns:
            Dict with user configuration and credentials
        """
        user_id = f'isolation_user_{user_index}_{self.test_session_id}'
        user_email = f'isolation_test_{user_index}_{self.test_session_id}@netra-testing.ai'
        access_token = self.__class__.auth_helper.create_test_jwt_token(user_id=user_id, email=user_email, exp_minutes=60)
        user_context = {'user_id': user_id, 'user_index': user_index, 'email': user_email, 'access_token': access_token, 'scenario': scenario, 'thread_id': f'thread_{user_id}_{int(time.time())}', 'run_id': f'run_{user_id}_{int(time.time())}', 'business_context': self._get_scenario_business_context(scenario, user_index), 'expected_isolation_markers': [user_id, user_email, f'user_{user_index}', scenario]}
        return user_context

    def _get_scenario_business_context(self, scenario: str, user_index: int) -> Dict[str, Any]:
        """
        Get business context specific to scenario and user.

        Args:
            scenario: Business scenario name
            user_index: User index for unique context

        Returns:
            Dict with scenario-specific business context
        """
        scenario_contexts = {'cost_optimization': {'company_size': f'Company_{user_index}_size', 'monthly_spend': 5000 + user_index * 2000, 'growth_rate': 10 + user_index * 5, 'target_savings': 20 + user_index * 5, 'unique_identifier': f'cost_opt_user_{user_index}'}, 'performance_analysis': {'system_load': f'System_{user_index}_load', 'response_time': 2.0 + user_index * 0.5, 'throughput': 1000 + user_index * 500, 'optimization_goal': f'perf_goal_{user_index}', 'unique_identifier': f'perf_user_{user_index}'}, 'security_assessment': {'compliance_level': f'Level_{user_index}', 'data_sensitivity': f'Sensitivity_{user_index}', 'audit_requirements': f'Audit_{user_index}', 'security_priority': user_index + 1, 'unique_identifier': f'security_user_{user_index}'}, 'infrastructure_review': {'infrastructure_type': f'Infrastructure_{user_index}', 'deployment_scale': f'Scale_{user_index}', 'service_count': 10 + user_index * 5, 'review_focus': f'focus_area_{user_index}', 'unique_identifier': f'infra_user_{user_index}'}}
        return scenario_contexts.get(scenario, {'unique_identifier': f'default_user_{user_index}'})

    def _create_user_message(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create user-specific message with unique identifiers for isolation validation.

        Args:
            user_context: User context with scenario and business details

        Returns:
            Dict with message payload including isolation markers
        """
        scenario = user_context['scenario']
        business_context = user_context['business_context']
        user_index = user_context['user_index']
        message_templates = {'cost_optimization': f"I'm from {business_context['company_size']} spending ${business_context['monthly_spend']}/month on AI with {business_context['growth_rate']}% growth. My unique situation is {business_context['unique_identifier']}. I need {business_context['target_savings']}% savings. This is user {user_index} requesting cost optimization analysis.", 'performance_analysis': f"Our {business_context['system_load']} has {business_context['response_time']}s response time with {business_context['throughput']} requests/min. Optimization goal: {business_context['optimization_goal']}. User identifier: {business_context['unique_identifier']}. This is user {user_index} analysis request.", 'security_assessment': f"Security assessment needed for {business_context['compliance_level']} with {business_context['data_sensitivity']} data and {business_context['audit_requirements']} requirements. Priority: {business_context['security_priority']}. User context: {business_context['unique_identifier']}. This is user {user_index} security review.", 'infrastructure_review': f"Infrastructure review for {business_context['infrastructure_type']} at {business_context['deployment_scale']} with {business_context['service_count']} services. Focus: {business_context['review_focus']}. Context identifier: {business_context['unique_identifier']}. User {user_index} infrastructure analysis."}
        message_content = message_templates.get(scenario, f'Default analysis request for user {user_index}')
        return {'type': 'agent_request', 'agent': 'supervisor_agent', 'message': message_content, 'thread_id': user_context['thread_id'], 'run_id': user_context['run_id'], 'user_id': user_context['user_id'], 'context': {'isolation_test': True, 'user_index': user_index, 'scenario': scenario, 'business_context': business_context, 'session_id': self.test_session_id, 'expected_isolation_markers': user_context['expected_isolation_markers']}}

    def _validate_response_isolation(self, user_context: Dict[str, Any], response_text: str) -> Dict[str, Any]:
        """
        Validate that response is isolated to the specific user and doesn't contain other user data.

        Args:
            user_context: Expected user context
            response_text: Agent response to validate

        Returns:
            Dict with isolation validation results
        """
        validation = {'contains_own_markers': False, 'contains_other_user_data': False, 'isolation_score': 0.0, 'own_markers_found': [], 'other_user_data_found': [], 'isolation_violation_details': [], 'isolation_validated': False}
        response_lower = response_text.lower()
        own_markers_found = [marker for marker in user_context['expected_isolation_markers'] if marker.lower() in response_lower]
        validation['own_markers_found'] = own_markers_found
        validation['contains_own_markers'] = len(own_markers_found) > 0
        other_user_patterns = []
        for other_index in range(self.__class__.max_concurrent_users):
            if other_index != user_context['user_index']:
                other_user_patterns.extend([f'user_{other_index}', f'user {other_index}', f'isolation_user_{other_index}'])
        other_scenarios = [s for s in self.__class__.isolation_test_scenarios if s != user_context['scenario']]
        for other_scenario in other_scenarios:
            for other_index in range(self.__class__.max_concurrent_users):
                if other_index != user_context['user_index']:
                    other_user_patterns.extend([f'{other_scenario}_user_{other_index}', f'unique_identifier_{other_scenario}_{other_index}'])
        contamination_found = []
        for pattern in other_user_patterns:
            if pattern.lower() in response_lower:
                contamination_found.append(pattern)
        validation['other_user_data_found'] = contamination_found
        validation['contains_other_user_data'] = len(contamination_found) > 0
        if validation['contains_own_markers'] and (not validation['contains_other_user_data']):
            validation['isolation_score'] = 1.0
        elif validation['contains_own_markers']:
            validation['isolation_score'] = 0.5
        elif not validation['contains_other_user_data']:
            validation['isolation_score'] = 0.7
        else:
            validation['isolation_score'] = 0.0
        if validation['contains_other_user_data']:
            validation['isolation_violation_details'] = [f'Response contains other user data: {contamination_found}', f"Expected isolation for user {user_context['user_index']} in scenario {user_context['scenario']}"]
        validation['isolation_validated'] = validation['isolation_score'] >= 0.7
        return validation

    async def _process_user_scenario(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process complete agent scenario for a single user with isolation validation.

        Args:
            user_context: User context and configuration

        Returns:
            Dict with user processing results and isolation validation
        """
        user_start_time = time.time()
        user_results = {'user_id': user_context['user_id'], 'user_index': user_context['user_index'], 'scenario': user_context['scenario'], 'success': False, 'duration': 0.0, 'events_received': 0, 'final_response': None, 'isolation_validation': None, 'error': None}
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f"Bearer {user_context['access_token']}", 'X-Environment': 'staging', 'X-Test-Suite': 'multi-user-isolation-e2e', 'X-User-Context': user_context['user_id'], 'X-Isolation-Test': 'enabled'}, ssl=ssl_context), timeout=20.0)
            user_message = self._create_user_message(user_context)
            await websocket.send(json.dumps(user_message))
            user_events = []
            response_timeout = 75.0
            collection_start = time.time()
            while time.time() - collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    user_events.append(event)
                    event_type = event.get('type', 'unknown')
                    if event_type == 'agent_completed':
                        user_results['final_response'] = event
                        break
                    if event_type == 'error' or event_type == 'agent_error':
                        user_results['error'] = f'Agent error: {event}'
                        break
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError as e:
                    continue
            await websocket.close()
            user_results['events_received'] = len(user_events)
            user_results['duration'] = time.time() - user_start_time
            if user_results['final_response']:
                response_data = user_results['final_response'].get('data', {})
                result = response_data.get('result', {})
                response_text = result.get('response', str(result)) if isinstance(result, dict) else str(result)
                isolation_validation = self._validate_response_isolation(user_context, response_text)
                user_results['isolation_validation'] = isolation_validation
                user_results['success'] = isolation_validation['isolation_validated']
            else:
                user_results['error'] = 'No final response received'
        except Exception as e:
            user_results['error'] = str(e)
            user_results['duration'] = time.time() - user_start_time
        return user_results

    async def test_concurrent_multi_user_agent_processing_isolation(self):
        """
        Test concurrent multi-user agent processing with complete isolation validation.

        CONCURRENT ISOLATION CORE: This validates that multiple users can simultaneously
        use the agent system without any data leakage, context contamination, or
        response mixing between users.

        Concurrent scenarios:
        1. Multiple users send different requests simultaneously
        2. Each user receives responses specific to their context
        3. No user data leaks into other user responses
        4. WebSocket events are delivered to correct users only
        5. Performance remains acceptable under concurrent load

        DIFFICULTY: Very High (90+ minutes)
        REAL SERVICES: Yes - Complete staging GCP with concurrent user simulation
        STATUS: Should PASS - Multi-user isolation is critical for enterprise trust
        """
        concurrent_test_start_time = time.time()
        isolation_metrics = []
        self.logger.info('👥 Testing concurrent multi-user agent processing isolation')
        try:
            test_users = []
            for i in range(self.__class__.max_concurrent_users):
                scenario = self.__class__.isolation_test_scenarios[i % len(self.__class__.isolation_test_scenarios)]
                user_context = self._create_test_user(i, scenario)
                test_users.append(user_context)
            self.logger.info(f'🎯 Created {len(test_users)} test users for concurrent processing')
            concurrent_start = time.time()
            user_tasks = [self._process_user_scenario(user_context) for user_context in test_users]
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            concurrent_duration = time.time() - concurrent_start
            successful_results = [r for r in user_results if isinstance(r, dict) and r.get('success')]
            failed_results = [r for r in user_results if isinstance(r, dict) and (not r.get('success'))]
            exception_results = [r for r in user_results if isinstance(r, Exception)]
            isolation_metrics.append({'metric': 'concurrent_processing', 'duration': concurrent_duration, 'total_users': len(test_users), 'successful_users': len(successful_results), 'failed_users': len(failed_results), 'exception_users': len(exception_results), 'success_rate': len(successful_results) / len(test_users)})
            self.logger.info(f'📊 Concurrent Processing Results:')
            self.logger.info(f'   Total Users: {len(test_users)}')
            self.logger.info(f'   Successful: {len(successful_results)}')
            self.logger.info(f'   Failed: {len(failed_results)}')
            self.logger.info(f'   Exceptions: {len(exception_results)}')
            self.logger.info(f'   Success Rate: {len(successful_results) / len(test_users):.1%}')
            success_rate = len(successful_results) / len(test_users)
            assert success_rate >= 0.75, f'Concurrent processing success rate too low: {success_rate:.1%} (required ≥75%). Failed: {len(failed_results)}, Exceptions: {len(exception_results)}'
            isolation_violations = []
            for i, result in enumerate(successful_results):
                isolation_validation = result.get('isolation_validation', {})
                if not isolation_validation.get('isolation_validated', False):
                    isolation_violations.append({'user_index': result['user_index'], 'user_id': result['user_id'], 'scenario': result['scenario'], 'violation_details': isolation_validation.get('isolation_violation_details', []), 'isolation_score': isolation_validation.get('isolation_score', 0.0), 'other_user_data': isolation_validation.get('other_user_data_found', [])})
            assert len(isolation_violations) == 0, f'Isolation violations detected across {len(isolation_violations)} users: {isolation_violations}. Multi-user isolation is critical for enterprise security.'
            if successful_results:
                avg_duration = sum((r['duration'] for r in successful_results)) / len(successful_results)
                max_duration = max((r['duration'] for r in successful_results))
                min_duration = min((r['duration'] for r in successful_results))
                assert avg_duration < 120.0, f'Average response time too slow under concurrent load: {avg_duration:.1f}s (max 120s)'
                assert max_duration < 180.0, f'Max response time too slow: {max_duration:.1f}s (max 180s)'
                isolation_metrics.append({'metric': 'concurrent_performance', 'avg_duration': avg_duration, 'max_duration': max_duration, 'min_duration': min_duration, 'duration_variance': max_duration - min_duration})
            isolation_scores = [r['isolation_validation']['isolation_score'] for r in successful_results if r.get('isolation_validation')]
            if isolation_scores:
                avg_isolation_score = sum(isolation_scores) / len(isolation_scores)
                min_isolation_score = min(isolation_scores)
                assert avg_isolation_score >= 0.8, f'Average isolation score too low: {avg_isolation_score:.2f} (required ≥0.8)'
                assert min_isolation_score >= 0.7, f'Minimum isolation score too low: {min_isolation_score:.2f} (required ≥0.7)'
                isolation_metrics.append({'metric': 'isolation_quality', 'avg_isolation_score': avg_isolation_score, 'min_isolation_score': min_isolation_score, 'isolation_scores': isolation_scores})
            total_test_time = time.time() - concurrent_test_start_time
            self.logger.info('👥 CONCURRENT MULTI-USER ISOLATION SUCCESS')
            self.logger.info(f'🔒 Isolation Validation Metrics:')
            self.logger.info(f'   Total Test Time: {total_test_time:.1f}s')
            self.logger.info(f'   Concurrent Processing Time: {concurrent_duration:.1f}s')
            self.logger.info(f'   Users Processed: {len(successful_results)}/{len(test_users)}')
            self.logger.info(f'   Isolation Violations: {len(isolation_violations)}')
            if isolation_scores:
                self.logger.info(f'   Average Isolation Score: {avg_isolation_score:.2f}/1.0')
                self.logger.info(f'   Minimum Isolation Score: {min_isolation_score:.2f}/1.0')
            for result in successful_results:
                isolation_val = result.get('isolation_validation', {})
                self.logger.info(f"   User {result['user_index']} ({result['scenario']}): Score {isolation_val.get('isolation_score', 0):.2f}, Duration {result['duration']:.1f}s")
        except Exception as e:
            total_time = time.time() - concurrent_test_start_time
            self.logger.error(f'❌ CONCURRENT MULTI-USER ISOLATION FAILED')
            self.logger.error(f'   Error: {str(e)}')
            self.logger.error(f'   Duration: {total_time:.1f}s')
            self.logger.error(f'   Metrics collected: {len(isolation_metrics)}')
            raise AssertionError(f'Multi-user isolation validation failed after {total_time:.1f}s: {e}. Isolation failures threaten enterprise trust and regulatory compliance. Isolation metrics: {isolation_metrics}')

    async def test_user_context_boundary_validation(self):
        """
        Test strict user context boundaries and data privacy enforcement.

        PRIVACY BOUNDARY VALIDATION: Ensures that user data, context, and processing
        results are completely isolated at the platform level, preventing any
        accidental or malicious data access between users.

        Context boundary tests:
        1. User A cannot access User B's thread data
        2. Agent responses contain only user-specific information
        3. WebSocket events are delivered to correct user only
        4. User context persists correctly throughout processing
        5. Memory isolation prevents cross-user state leakage

        DIFFICULTY: High (60 minutes)
        REAL SERVICES: Yes - Staging GCP with privacy boundary validation
        STATUS: Should PASS - Privacy boundaries critical for compliance
        """
        boundary_test_start_time = time.time()
        boundary_metrics = []
        self.logger.info('🔒 Testing user context boundary validation')
        try:
            user_a_context = self._create_test_user(1, 'cost_optimization')
            user_b_context = self._create_test_user(2, 'security_assessment')
            user_a_context['sensitive_data'] = {'company_name': 'ACME_Corp_User_A', 'budget_secret': 'UserA_Budget_12345', 'confidential_metric': 'UserA_Metric_Secret'}
            user_b_context['sensitive_data'] = {'company_name': 'Beta_Industries_User_B', 'security_level': 'UserB_Security_Level_9', 'confidential_assessment': 'UserB_Assessment_Secret'}
            boundary_metrics.append({'metric': 'user_context_setup', 'user_a_id': user_a_context['user_id'], 'user_b_id': user_b_context['user_id'], 'context_separation': 'configured'})
            user_a_message = self._create_user_message(user_a_context)
            user_a_message['message'] += f" My company {user_a_context['sensitive_data']['company_name']} has budget constraints with reference {user_a_context['sensitive_data']['budget_secret']}."
            user_b_message = self._create_user_message(user_b_context)
            user_b_message['message'] += f" Our organization {user_b_context['sensitive_data']['company_name']} requires security level {user_b_context['sensitive_data']['security_level']} assessment."
            user_results = []
            for user_context, user_message in [(user_a_context, user_a_message), (user_b_context, user_b_message)]:
                user_start = time.time()
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers={'Authorization': f"Bearer {user_context['access_token']}", 'X-Environment': 'staging', 'X-Test-Suite': 'boundary-validation-e2e', 'X-User-Boundary-Test': user_context['user_id']}, ssl=ssl_context), timeout=20.0)
                await websocket.send(json.dumps(user_message))
                final_response = None
                timeout = 60.0
                collection_start = time.time()
                while time.time() - collection_start < timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                        event = json.loads(event_data)
                        if event.get('type') == 'agent_completed':
                            final_response = event
                            break
                    except asyncio.TimeoutError:
                        continue
                await websocket.close()
                user_duration = time.time() - user_start
                response_text = ''
                if final_response:
                    response_data = final_response.get('data', {})
                    result = response_data.get('result', {})
                    response_text = result.get('response', str(result)) if isinstance(result, dict) else str(result)
                user_results.append({'user_context': user_context, 'response_text': response_text, 'duration': user_duration, 'success': len(response_text) > 50})
            contamination_violations = []
            for i, result in enumerate(user_results):
                current_user = result['user_context']
                current_response = result['response_text']
                for j, other_result in enumerate(user_results):
                    if i != j:
                        other_user = other_result['user_context']
                        for sensitive_key, sensitive_value in other_user['sensitive_data'].items():
                            if sensitive_value.lower() in current_response.lower():
                                contamination_violations.append({'victim_user': current_user['user_id'], 'leaked_from_user': other_user['user_id'], 'leaked_data': sensitive_value, 'data_type': sensitive_key, 'response_excerpt': current_response[:200] + '...'})
            assert len(contamination_violations) == 0, f'PRIVACY VIOLATION: Cross-user data contamination detected: {contamination_violations}. This is a critical security and compliance failure.'
            context_validation_failures = []
            for result in user_results:
                user_context = result['user_context']
                response_text = result['response_text']
                own_markers_found = [marker for marker in user_context['expected_isolation_markers'] if marker.lower() in response_text.lower()]
                if len(own_markers_found) == 0:
                    context_validation_failures.append({'user_id': user_context['user_id'], 'scenario': user_context['scenario'], 'expected_markers': user_context['expected_isolation_markers'], 'response_excerpt': response_text[:200] + '...'})
            assert len(context_validation_failures) == 0, f'Context validation failures: {context_validation_failures}. Users should receive responses relevant to their specific context.'
            total_boundary_test_time = time.time() - boundary_test_start_time
            boundary_metrics.append({'metric': 'boundary_validation_complete', 'total_test_time': total_boundary_test_time, 'users_tested': len(user_results), 'contamination_violations': len(contamination_violations), 'context_validation_failures': len(context_validation_failures), 'privacy_boundaries_validated': True})
            self.logger.info('🔒 USER CONTEXT BOUNDARY VALIDATION SUCCESS')
            self.logger.info(f'🛡️ Boundary Validation Metrics:')
            self.logger.info(f'   Total Test Time: {total_boundary_test_time:.1f}s')
            self.logger.info(f'   Users Tested: {len(user_results)}')
            self.logger.info(f'   Contamination Violations: {len(contamination_violations)}')
            self.logger.info(f'   Context Validation Failures: {len(context_validation_failures)}')
            self.logger.info(f'   Privacy Boundaries: SECURE')
        except Exception as e:
            total_time = time.time() - boundary_test_start_time
            self.logger.error(f'❌ USER CONTEXT BOUNDARY VALIDATION FAILED')
            self.logger.error(f'   Error: {str(e)}')
            self.logger.error(f'   Duration: {total_time:.1f}s')
            raise AssertionError(f'User context boundary validation failed after {total_time:.1f}s: {e}. Privacy boundary failures create serious compliance and security risks.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')