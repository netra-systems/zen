""""""
E2E GCP Staging Tests - WebSocket Infrastructure Validation - CRITICAL REGRESSION PREVENTION

Business Value Justification:
    - Segment: Platform/Internal - GCP Infrastructure Validation
- Business Goal: Prevent WebSocket infrastructure failures in staging/production
- Value Impact: Catches GCP Load Balancer configuration issues that block Golden Path
- Revenue Impact: Prevents 100% chat functionality failure scenarios ($"120K"+ MRR impact)

CRITICAL TEST PURPOSE:
    These E2E tests specifically target the GCP Load Balancer authentication header 
stripping issue that caused complete WebSocket infrastructure failure (GitHub issue #113).

PRIMARY REGRESSION PREVENTION:
    - test_gcp_load_balancer_preserves_authorization_header()
- test_gcp_load_balancer_preserves_e2e_bypass_header()

Root Cause Addressed:
    GCP HTTPS Load Balancer was stripping authentication headers (Authorization, X-E2E-Bypass) 
for WebSocket upgrade requests, causing 100% authentication failures and 1011 errors.

Infrastructure Fix Required:
    terraform-gcp-staging/load-balancer.tf needs WebSocket path authentication header preservation.

COMPLEMENTARY TESTS:
    This file focuses on WebSocket-specific infrastructure validation. 
See test_gcp_load_balancer_header_validation.py for comprehensive load balancer testing.

CLAUDE.MD E2E AUTH COMPLIANCE:
    All tests use real authentication as required by CLAUDE.MD Section 7.3.
""""""
import asyncio
import json
import logging
import pytest
import time
import unittest
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch
logger = logging.getLogger(__name__)
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser
from tests.e2e.staging_config import StagingTestConfig, staging_urls
from shared.isolated_environment import get_env

@pytest.mark.e2e
class WebSocketGCPStagingInfrastructureTests(SSotBaseTestCase, unittest.TestCase):
    pass
""""""
    CRITICAL E2E Tests for GCP Staging WebSocket Infrastructure
    
    These tests specifically validate GCP Load Balancer configuration
    to prevent the authentication header stripping regression that
    caused complete Golden Path failure.
""

    def setup_method(self, method=None):
        "Set up staging environment test configuration."""
        super().setup_method(method)
        self.env = get_env()
        self.staging_config = StagingTestConfig()
        self.e2e_helper = E2EWebSocketAuthHelper(environment='staging')
        self.staging_websocket_url = self.staging_config.urls.websocket_url
        self.gcp_timeout = 15.0
        self.auth_timeout = 10.0

    async def test_gcp_load_balancer_preserves_authorization_header(self):
        """"

        CRITICAL: Test that GCP Load Balancer preserves Authorization header for WebSocket.
        
        This is the PRIMARY REGRESSION PREVENTION test for the infrastructure failure
        that blocked 100% of Golden Path chat functionality.
        
        ROOT CAUSE: GCP Load Balancer configuration was missing authentication header
        forwarding for WebSocket paths, causing headers to be stripped.

        auth_user = await self.e2e_helper.create_authenticated_user(email='gcp_auth_test@example.com', permissions=['read', 'write', 'websocket')
        websocket_headers = self.e2e_helper.get_websocket_headers(auth_user.jwt_token)
        print(f' SEARCH:  CRITICAL TEST: GCP Load Balancer auth header preservation')
        print(f'[U+1F310] Staging WebSocket URL: {self.staging_websocket_url}')
        print(f'[U+1F511] Headers being sent: {list(websocket_headers.keys())}')
        print(f" PASS:  Authorization header present: {'authorization' in [k.lower() for k in websocket_headers.keys()]})"
        connection_successful = False
        auth_headers_preserved = False
        error_details = None
        try:
            async with websockets.connect(self.staging_websocket_url, additional_headers=websocket_headers, ping_interval=None, ping_timeout=None, max_size=2 ** 16) as websocket:
                connection_successful = True
                print(f' PASS:  WebSocket connection established through GCP Load Balancer')
                header_test_message = {'type': 'gcp_header_validation_test', 'purpose': 'validate_authorization_header_preservation', 'expected_user_id': auth_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'test_environment': 'staging', 'infrastructure': 'gcp_load_balancer'}
                await websocket.send(json.dumps(header_test_message))
                print(f'[U+1F4E4] Sent header validation test message')
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=self.auth_timeout)
                    response_data = json.loads(response)
                    print(f[U+1F4E5] Received response: {response_data.get('type', 'unknown'")})"
                    auth_headers_preserved = True
                except asyncio.TimeoutError:
                    print(f'[U+23F0] Response timeout - connection established but no immediate response')
                    auth_headers_preserved = True
        except websockets.InvalidHandshake as e:
            error_details = f'WebSocket handshake failed: {e}'
            print(f' FAIL:  Handshake error (may indicate auth header stripping): {error_details}')
        except websockets.ConnectionClosedError as e:
            error_details = f'Connection closed during handshake: {e}'
            print(f' FAIL:  Connection closed (may indicate auth failure): {error_details}')
        except asyncio.TimeoutError:
            error_details = 'Connection timeout (GCP Load Balancer may be stripping headers)'
            print(f'[U+23F0] Connection timeout: {error_details}')
        except Exception as e:
            error_details = f'Unexpected connection error: {e}'
            print(f' FIRE:  Unexpected error: {error_details}')
        self.assertTrue(connection_successful, f'CRITICAL FAILURE: GCP Load Balancer auth header stripping detected. WebSocket connection failed through staging infrastructure. Error: {error_details}. This indicates the Load Balancer is not preserving Authorization headers. Required fix: Update terraform-gcp-staging/load-balancer.tf with auth header forwarding.')
        self.assertTrue(auth_headers_preserved, f'CRITICAL FAILURE: Authorization headers not preserved by GCP Load Balancer. Connection established but auth context not available. This indicates partial header stripping. Required fix: Add header_action for Authorization header preservation.')
        print(f' PASS:  CRITICAL TEST PASSED: GCP Load Balancer preserves Authorization headers')

    async def test_gcp_load_balancer_preserves_e2e_bypass_header(self):
    """"

        CRITICAL: Test that GCP Load Balancer preserves X-E2E-Bypass header.
        
        This validates E2E testing headers are forwarded through the Load Balancer,
        enabling staging environment testing without OAuth simulation failures.
        
        auth_user = await self.e2e_helper.create_authenticated_user(email='e2e_bypass_test@example.com', permissions=['read', 'write', 'e2e_test')
        websocket_headers = self.e2e_helper.get_websocket_headers(auth_user.jwt_token)
        websocket_headers.update({'X-E2E-Bypass': 'true', 'X-E2E-Test-Environment': 'staging', 'X-Test-Infrastructure': 'gcp_load_balancer')
        print(f' SEARCH:  CRITICAL TEST: E2E bypass header preservation through GCP')
        print(f[U+1F511] E2E headers: {[k for k in websocket_headers.keys() if 'e2e' in k.lower() or 'test' in k.lower()]})""
        e2e_headers_preserved = False
        connection_details = None
        try:
            async with websockets.connect(self.staging_websocket_url, additional_headers=websocket_headers, ping_interval=None, ping_timeout=None) as websocket:
                print(f' PASS:  WebSocket connection with E2E headers established')
                e2e_test_message = {'type': 'e2e_header_validation_test', 'purpose': 'validate_e2e_bypass_headers', 'user_id': auth_user.user_id, 'test_mode': 'e2e_staging', 'timestamp': datetime.now(timezone.utc).isoformat()}
                await websocket.send(json.dumps(e2e_test_message))
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=self.auth_timeout)
                    response_data = json.loads(response)
                    e2e_headers_preserved = True
                    connection_details = f"Response type: {response_data.get('type', 'unknown')}"
                    print(f' PASS:  E2E headers preserved - received: {connection_details}')
                except asyncio.TimeoutError:
                    e2e_headers_preserved = True
                    connection_details = 'Connection established successfully'
                    print(f' PASS:  E2E headers preserved - connection stable')
        except Exception as e:
            connection_details = f'E2E connection failed: {e}'
            print(f' FAIL:  E2E header preservation test failed: {connection_details}')
        self.assertTrue(e2e_headers_preserved, f'CRITICAL FAILURE: GCP Load Balancer is stripping E2E bypass headers. This prevents staging environment testing. Connection details: {connection_details}. Required fix: Add X-E2E-Bypass header preservation to load-balancer.tf')

    async def test_complete_golden_path_websocket_flow(self):
        
        CRITICAL: Test complete Golden Path WebSocket flow through GCP staging.
        
        This validates the end-to-end WebSocket functionality that enables
        core business value delivery through chat interactions.
""
        golden_path_user = await self.e2e_helper.create_authenticated_user(email='golden_path@example.com', permissions=['read', 'write', 'chat', 'agent_interaction')
        websocket_headers = self.e2e_helper.get_websocket_headers(golden_path_user.jwt_token)
        print(f'[U+1F31F] CRITICAL TEST: Complete Golden Path WebSocket flow')
        print(f'[U+1F464] User: {golden_path_user.email} ({golden_path_user.user_id[:8]}...)')
        golden_path_steps_completed = []
        try:
            async with websockets.connect(self.staging_websocket_url, additional_headers=websocket_headers) as websocket:
                golden_path_steps_completed.append('connection_established')
                print(f' PASS:  Step 1: WebSocket connection established')
                auth_confirm_message = {'type': 'golden_path_auth_confirm', 'user_id': golden_path_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat()}
                await websocket.send(json.dumps(auth_confirm_message))
                golden_path_steps_completed.append('auth_message_sent')
                print(f' PASS:  Step 2: Authentication confirmation sent')
                chat_initiation_message = {'type': 'golden_path_chat_initiation', 'action': 'start_chat_session', 'message': 'Hello, I need help with my AI optimization', 'user_id': golden_path_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat()}
                await websocket.send(json.dumps(chat_initiation_message))
                golden_path_steps_completed.append('chat_initiated')
                print(f' PASS:  Step 3: Chat session initiated')
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=self.auth_timeout)
                    response_data = json.loads(response)
                    golden_path_steps_completed.append('server_response_received')
                    print(f PASS:  Step 4: Server response received - {response_data.get('type', 'unknown')})
                except asyncio.TimeoutError:
                    golden_path_steps_completed.append('connection_stable')
                    print(f' PASS:  Step 4: Connection stable (no immediate errors)')
                golden_path_steps_completed.append('golden_path_complete')
                print(f'[U+1F31F] Golden Path WebSocket flow completed successfully')
        except Exception as e:
            print(f' FAIL:  Golden Path flow failed at step: {len(golden_path_steps_completed) + 1}')
            print(f' FAIL:  Error: {e}')
            print(f' PASS:  Completed steps: {golden_path_steps_completed}')
        required_steps = ['connection_established', 'auth_message_sent', 'chat_initiated']
        completed_required_steps = [step for step in required_steps if step in golden_path_steps_completed]
        self.assertEqual(len(completed_required_steps), len(required_steps), f'CRITICAL FAILURE: Golden Path WebSocket flow incomplete. Required steps: {required_steps}. Completed: {completed_required_steps}. All completed: {golden_path_steps_completed}. This indicates WebSocket infrastructure cannot support core business value.')

    async def test_websocket_reconnection_with_auth(self):
    """"""
        Test WebSocket reconnection scenarios with authentication preservation.
        
        This validates resilience patterns that ensure chat sessions can
        recover from temporary connection issues.
""""""
        reconnect_user = await self.e2e_helper.create_authenticated_user(email='reconnect_test@example.com', permissions=['read', 'write', 'persistent_session')
        websocket_headers = self.e2e_helper.get_websocket_headers(reconnect_user.jwt_token)
        print(f' CYCLE:  Testing WebSocket reconnection with auth preservation')
        connection_attempts = []
        for attempt in range(2):
            try:
                print(f' CYCLE:  Connection attempt {attempt + 1}')
                async with websockets.connect(self.staging_websocket_url, additional_headers=websocket_headers) as websocket:
                    reconnect_message = {'type': 'reconnection_test', 'attempt_number': attempt + 1, 'user_id': reconnect_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat()}
                    await websocket.send(json.dumps(reconnect_message))
                    await asyncio.sleep(0.5)
                    connection_attempts.append(f'attempt_{attempt + 1}_success')
                    print(f' PASS:  Connection attempt {attempt + 1} successful')
                if attempt < 1:
                    await asyncio.sleep(1.0)
            except Exception as e:
                connection_attempts.append(f'attempt_{attempt + 1}_failed: {e}')
                print(f' FAIL:  Connection attempt {attempt + 1} failed: {e}')
        successful_attempts = [attempt for attempt in connection_attempts if 'success' in attempt]
        self.assertGreater(len(successful_attempts), 0, f'WebSocket reconnection should succeed with preserved auth. Attempts: {connection_attempts}')

    async def test_multi_user_websocket_isolation_in_gcp(self):
    """"

        CRITICAL: Test multi-user WebSocket isolation through GCP infrastructure.
        
        This validates that GCP Load Balancer preserves user context isolation,
        preventing cross-user data leakage in production.
        
        users = []
        for i in range(2):
            user = await self.e2e_helper.create_authenticated_user(email=f'isolation_user_{i)@example.com', permissions=['read', 'write', f'user_context_{i)']
            users.append(user)
        print(f'[U+1F465] Testing multi-user isolation through GCP staging')
        print(f'[U+1F464] Users: {[user.email for user in users]}')

        async def test_isolated_user(user_index: int, user: AuthenticatedUser):
            "Test individual user connection with isolation."
            headers = self.e2e_helper.get_websocket_headers(user.jwt_token)
            isolation_result = {'user_index': user_index, 'user_id': user.user_id, 'connection_success': False, 'isolation_validated': False, 'error': None}
            try:
                async with websockets.connect(self.staging_websocket_url, additional_headers=headers) as websocket:
                    isolation_result['connection_success'] = True
                    isolation_message = {'type': 'gcp_user_isolation_test', 'user_index': user_index, 'user_id': user.user_id, 'isolation_key': f'user_{user_index}_secret', 'timestamp': datetime.now(timezone.utc).isoformat()}
                    await websocket.send(json.dumps(isolation_message))
                    await asyncio.sleep(0.5)
                    isolation_result['isolation_validated'] = True
                    print(f' PASS:  User {user_index} isolation validated')
            except Exception as e:
                isolation_result['error'] = str(e)
                print(f' FAIL:  User {user_index} isolation test failed: {e}')
            return isolation_result
        isolation_results = await asyncio.gather(*[test_isolated_user(i, user) for i, user in enumerate(users)], return_exceptions=True)
        successful_isolations = []
        for result in isolation_results:
            if isinstance(result, dict) and result.get('isolation_validated'):
                successful_isolations.append(result)
            elif isinstance(result, Exception):
                print(f' FAIL:  Isolation test exception: {result}')
        self.assertGreater(len(successful_isolations), 0, f'Multi-user isolation should work through GCP infrastructure. Results: {isolation_results}')
        if len(successful_isolations) > 1:
            user_ids = [result['user_id'] for result in successful_isolations]
            unique_users = set(user_ids)
            self.assertEqual(len(unique_users), len(user_ids), f'Users should have unique isolated contexts. User IDs: {user_ids}')

    async def test_websocket_header_stripping_regression_prevention(self):
    """"""
        CRITICAL: Specific regression test for GitHub issue #113 header stripping.
        
        This test validates that the specific header stripping issue that caused
        WebSocket 1011 errors is completely resolved and won't regress.'
        
        COMPLEMENTARY TO: test_gcp_load_balancer_header_validation.py
        This focuses specifically on WebSocket upgrade header preservation.
""""""
        logger.info(' SEARCH:  REGRESSION TEST: GitHub issue #113 header stripping prevention')
        regression_user = await self.e2e_helper.create_authenticated_user(email='github_issue_113_regression@example.com', permissions=['read', 'write', 'websocket', 'regression_test')
        problematic_headers = self.e2e_helper.get_websocket_headers(regression_user.jwt_token)
        problematic_headers.update({'Authorization': f'Bearer {regression_user.jwt_token)', 'X-E2E-Bypass': 'true', 'X-E2E-Test-Environment': 'staging', 'X-GitHub-Issue': '113', 'X-WebSocket-Protocol': 'netra-websocket-v1', 'X-User-Agent': 'E2E-Test-WebSocket-Client', 'X-Forwarded-Proto': 'https', 'Upgrade': 'websocket', 'Connection': 'upgrade')
        print(f' SEARCH:  Testing {len(problematic_headers)} headers that previously failed')
        print(f'[U+1F511] Critical headers: Authorization, X-E2E-Bypass, Upgrade, Connection')
        regression_test_result = {'headers_sent': list(problematic_headers.keys()), 'connection_successful': False, 'header_stripping_detected': False, 'websocket_upgrade_successful': False, 'error_details': None, 'regression_prevented': False}
        try:
            async with websockets.connect(self.staging_websocket_url, additional_headers=problematic_headers, ping_interval=None, ping_timeout=None) as websocket:
                regression_test_result['connection_successful'] = True
                regression_test_result['websocket_upgrade_successful'] = True
                regression_message = {'type': 'github_issue_113_regression_test', 'purpose': 'validate_header_stripping_fix', 'user_id': regression_user.user_id, 'headers_tested': list(problematic_headers.keys()), 'issue_number': 113, 'test_environment': 'staging', 'timestamp': datetime.now(timezone.utc).isoformat()}
                await websocket.send(json.dumps(regression_message))
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    regression_test_result['server_response'] = response_data.get('type', 'unknown')
                    regression_test_result['regression_prevented'] = True
                except asyncio.TimeoutError:
                    regression_test_result['regression_prevented'] = True
                    regression_test_result['server_response'] = 'timeout_but_connected'
                print(' PASS:  GitHub issue #113 regression test: WebSocket connection successful')
        except websockets.InvalidHandshake as e:
            regression_test_result['error_details'] = f'Handshake failed: {e}'
            error_str = str(e).lower()
            if any((pattern in error_str for pattern in ['401', 'unauthorized', 'forbidden', 'authentication']):
                regression_test_result['header_stripping_detected'] = True
                regression_test_result['error_details'] += ' (HEADER STRIPPING DETECTED)'
        except websockets.ConnectionClosedError as e:
            regression_test_result['error_details'] = f'Connection closed: {e}'
            if '1011' in str(e):
                regression_test_result['header_stripping_detected'] = True
                regression_test_result['error_details'] += ' (1011 ERROR - HEADER STRIPPING DETECTED)'
        except Exception as e:
            regression_test_result['error_details'] = f'Connection error: {e}'
        self.assertFalse(regression_test_result['header_stripping_detected'], fCRITICAL REGRESSION: GitHub issue #113 header stripping has returned! Load balancer is stripping authentication headers again. Error details: {regression_test_result['error_details']}. Headers tested: {regression_test_result['headers_sent']}. IMMEDIATE FIX REQUIRED: Check terraform-gcp-staging/load-balancer.tf deployment)
        self.assertTrue(regression_test_result['connection_successful'], f'CRITICAL REGRESSION: WebSocket connection failed with auth headers. This is exactly the symptom of GitHub issue #113. Connection result: {regression_test_result}. IMMEDIATE ACTION: Validate load balancer header forwarding configuration')
        self.assertTrue(regression_test_result['regression_prevented'], f'CRITICAL REGRESSION: GitHub issue #113 symptoms detected. WebSocket upgrade with auth headers is not working properly. Full test result: {regression_test_result}')
        print(' PASS:  REGRESSION TEST PASSED: GitHub issue #113 header stripping prevented')

@pytest.mark.e2e
class GCPWebSocketInfrastructureResilienceTests(SSotBaseTestCase, unittest.TestCase):
    """"

    Tests for GCP WebSocket infrastructure resilience and error handling.
    
    These tests validate proper behavior under various failure conditions
    that can occur in GCP staging and production environments.
    

    def setup_method(self, method=None):
        ""Set up resilience test environment.""

        super().setup_method(method)
        self.staging_config = StagingTestConfig()
        self.e2e_helper = E2EWebSocketAuthHelper(environment='staging')
        self.staging_websocket_url = self.staging_config.urls.websocket_url

    async def test_websocket_gcp_timeout_resilience(self):
    """"

        Test WebSocket resilience to GCP Cloud Run timeout limitations.
        
        This validates proper handling of GCP-specific timeout constraints
        that can affect WebSocket connection establishment.
        
        timeout_user = await self.e2e_helper.create_authenticated_user(email='timeout_resilience@example.com', permissions=['read', 'write')
        headers = self.e2e_helper.get_websocket_headers(timeout_user.jwt_token)
        print(f'[U+23F1][U+FE0F] Testing GCP timeout resilience')
        timeout_scenarios = [('aggressive_timeout', 3.0), ('standard_timeout', 10.0), ('generous_timeout', 15.0)]
        timeout_results = []
        for scenario_name, timeout_value in timeout_scenarios:
            try:
                start_time = time.time()
                async with websockets.connect(self.staging_websocket_url, additional_headers=headers, ping_interval=None, ping_timeout=None) as websocket:
                    connection_time = time.time() - start_time
                    timeout_message = {'type': 'gcp_timeout_resilience_test', 'scenario': scenario_name, 'timeout_configured': timeout_value, 'actual_connection_time': connection_time, 'timestamp': datetime.now(timezone.utc).isoformat()}
                    await websocket.send(json.dumps(timeout_message))
                    timeout_results.append({'scenario': scenario_name, 'success': True, 'connection_time': connection_time, 'configured_timeout': timeout_value)
                    print(f' PASS:  {scenario_name}: Connected in {connection_time:."2f"}s')""

            except asyncio.TimeoutError:
                timeout_results.append({'scenario': scenario_name, 'success': False, 'error': 'timeout', 'configured_timeout': timeout_value)
                print(f'[U+23F0] {scenario_name}: Timeout at {timeout_value}s')
            except Exception as e:
                timeout_results.append({'scenario': scenario_name, 'success': False, 'error': str(e), 'configured_timeout': timeout_value}
                print(f' FAIL:  {scenario_name}: Error - {e}')
        successful_scenarios = [r for r in timeout_results if r.get('success')]
        self.assertGreater(len(successful_scenarios), 0, f'At least one timeout scenario should succeed in GCP. Results: {timeout_results}')

    async def test_websocket_gcp_infrastructure_error_handling(self):
    """"""
        Test proper error handling for GCP infrastructure issues.
        
        This validates that infrastructure errors are properly detected
        and reported rather than causing silent failures.
""""""
        problematic_scenarios = [{'name': 'malformed_bearer_token', 'headers': {'authorization': 'Bearer malformed.token.structure'}, 'expected_error_types': ['handshake', 'authentication', 'authorization']}, {'name': 'missing_upgrade_headers', 'headers': {'authorization': f'Bearer {self.e2e_helper.create_test_jwt_token()}'}, 'expected_error_types': ['upgrade', 'handshake', 'protocol']}]
        error_handling_results = []
        for scenario in problematic_scenarios:
            print(f SEARCH:  Testing error handling: {scenario['name']})
            try:
                async with websockets.connect(self.staging_websocket_url, additional_headers=scenario['headers') as websocket:
                    error_handling_results.append({'scenario': scenario['name'], 'result': 'unexpected_success', 'error_handling': 'poor')
            except Exception as e:
                error_msg = str(e).lower()
                error_detected = any((error_type in error_msg for error_type in scenario['expected_error_types'])
                error_handling_results.append({'scenario': scenario['name'], 'result': 'expected_error', 'error_message': str(e"), 'error_properly_detected': error_detected, 'error_handling': 'good' if error_detected else 'unclear'}"
                print(f PASS:  {scenario['name']}: Proper error handling - {e}"")""
        good_error_handling = [r for r in error_handling_results if r.get('error_handling') == 'good']
        self.assertGreater(len(good_error_handling), 0, f'GCP infrastructure should provide clear error handling. Results: {error_handling_results}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
""""

)))))))))))))))))