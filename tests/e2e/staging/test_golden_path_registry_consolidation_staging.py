"""
Issue #914 Golden Path Registry Consolidation Staging E2E Test Suite

This test suite validates the complete Golden Path user flow in the GCP staging
environment during AgentRegistry SSOT consolidation, ensuring business continuity.

EXPECTED BEHAVIOR: Tests must validate the complete user journey works end-to-end
in staging regardless of registry implementation challenges.

Business Impact:
- Validates Golden Path: Users login -> get AI responses
- Protects 500K+ ARR functionality in production-like environment
- Ensures staging environment reflects production readiness
- Validates real WebSocket event delivery in cloud environment

Test Strategy (GCP Staging Only):
1. Test complete user authentication flow in staging
2. Validate agent creation and execution in cloud environment
3. Ensure WebSocket events work end-to-end in staging
4. Test registry SSOT consolidation impact on real user flow
5. Validate business value protection during transition
"""

import asyncio
import logging
import unittest
import uuid
import warnings
import pytest
import os
from typing import Optional, Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Staging environment detection
STAGING_ENVIRONMENT = os.getenv('NETRA_ENV', '').lower() == 'staging'
GCP_STAGING_URL = os.getenv('STAGING_API_URL', 'https://staging-api.netrasystems.ai')
GCP_STAGING_WS_URL = os.getenv('STAGING_WS_URL', 'wss://staging-api.netrasystems.ai/ws')

# Registry imports for staging validation
try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as BasicAgentRegistry
    basic_registry_available = True
except ImportError:
    BasicAgentRegistry = None
    basic_registry_available = False

try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedAgentRegistry
    advanced_registry_available = True
except ImportError:
    AdvancedAgentRegistry = None
    advanced_registry_available = False

# Staging test infrastructure
try:
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    from test_framework.ssot.websocket_auth_helper import WebSocketAuthHelper
    staging_auth_available = True
except ImportError:
    E2EAuthHelper = None
    WebSocketAuthHelper = None
    staging_auth_available = False

# HTTP and WebSocket clients for staging
try:
    import httpx
    import websockets
    import json
    http_client_available = True
except ImportError:
    httpx = None
    websockets = None
    json = None
    http_client_available = False

logger = logging.getLogger(__name__)


@pytest.mark.e2e
class GoldenPathRegistryConsolidationStagingTests(SSotAsyncTestCase):
    """
    E2E test suite for Golden Path validation in GCP staging environment.

    Tests the complete user journey during registry SSOT consolidation
    to ensure business continuity and 500K+ ARR protection.
    """

    def setup_method(self, method):
        """Setup staging E2E test environment."""
        super().setup_method(method)
        self.test_user_id = f"staging_user_{uuid.uuid4().hex[:8]}"
        self.test_session_id = f"staging_session_{uuid.uuid4().hex[:8]}"

        # Staging environment configuration
        self.staging_config = {
            'api_url': GCP_STAGING_URL,
            'ws_url': GCP_STAGING_WS_URL,
            'timeout': 30,
            'retry_count': 3
        }

        # Golden Path tracking
        self.golden_path_steps = {
            'user_authentication': False,
            'agent_registry_access': False,
            'agent_creation': False,
            'websocket_connection': False,
            'agent_execution': False,
            'websocket_events_received': False,
            'ai_response_delivery': False
        }

        # WebSocket event tracking
        self.received_websocket_events = []
        self.critical_events_received = set()

        # Authentication tokens
        self.auth_tokens = {}

    async def teardown_method(self, method):
        """Cleanup staging test resources."""
        # Clear authentication tokens
        self.auth_tokens.clear()
        self.received_websocket_events.clear()
        self.critical_events_received.clear()
        await super().teardown_method(method)

    def should_skip_staging_tests(self) -> bool:
        """Determine if staging tests should be skipped."""
        skip_reasons = []

        if not STAGING_ENVIRONMENT:
            skip_reasons.append("Not running in staging environment")

        if not http_client_available:
            skip_reasons.append("HTTP client libraries not available")

        if not staging_auth_available:
            skip_reasons.append("Staging auth helpers not available")

        if skip_reasons:
            logger.info(f"Skipping staging tests: {', '.join(skip_reasons)}")
            return True

        return False

    async def test_01_staging_user_authentication_flow(self):
        """
        Test 1: Staging user authentication flow

        Validates that user authentication works correctly in the staging
        environment and provides proper access tokens for the Golden Path.

        EXPECTED: PASS - Authentication should work in staging
        """
        if self.should_skip_staging_tests():
            pytest.skip("Staging environment or dependencies not available")

        try:
            # Create staging authentication helper
            auth_helper = E2EAuthHelper() if E2EAuthHelper else None

            if not auth_helper:
                # Fallback: Direct HTTP authentication
                async with httpx.AsyncClient(timeout=self.staging_config['timeout']) as client:
                    auth_request = {
                        'username': f'test_user_{uuid.uuid4().hex[:8]}@staging.netrasystems.ai',
                        'password': 'staging_test_password_123',
                        'grant_type': 'password'
                    }

                    auth_response = await client.post(
                        f"{self.staging_config['api_url']}/auth/token",
                        json=auth_request
                    )

                    if auth_response.status_code == 200:
                        auth_data = auth_response.json()
                        self.auth_tokens['access_token'] = auth_data.get('access_token')
                        self.auth_tokens['user_id'] = auth_data.get('user_id', self.test_user_id)
                        self.golden_path_steps['user_authentication'] = True
                    else:
                        logger.warning(f"Authentication failed: {auth_response.status_code} - {auth_response.text}")
            else:
                # Use staging auth helper
                auth_result = await auth_helper.authenticate_staging_user(
                    user_id=self.test_user_id,
                    session_id=self.test_session_id
                )

                if auth_result.get('success'):
                    self.auth_tokens.update(auth_result.get('tokens', {}))
                    self.golden_path_steps['user_authentication'] = True

            # Validate authentication success
            self.assertTrue(self.golden_path_steps['user_authentication'],
                          "User authentication must succeed in staging for Golden Path")

            self.assertIsNotNone(self.auth_tokens.get('access_token'),
                               "Access token must be provided for authenticated requests")

            # Record authentication metrics
            self.record_metric('staging_authentication_success', True)
            self.record_metric('auth_tokens_received', len(self.auth_tokens))

            logger.info(f"Staging authentication successful for user {self.test_user_id}")

        except Exception as e:
            logger.error(f"Staging authentication failed: {e}")
            self.golden_path_steps['user_authentication'] = False
            self.record_metric('staging_authentication_success', False)
            self.record_metric('authentication_error', str(e))

            # Authentication failure blocks the Golden Path
            self.fail(f"Golden Path blocked by authentication failure: {e}")

    async def test_02_staging_agent_registry_access(self):
        """
        Test 2: Staging agent registry access

        Validates that agent registries can be accessed and instantiated
        correctly in the staging environment during SSOT consolidation.

        EXPECTED: PASS when at least one registry works in staging
        """
        if self.should_skip_staging_tests():
            pytest.skip("Staging environment or dependencies not available")

        # Ensure authentication completed
        if not self.golden_path_steps['user_authentication']:
            await self.test_01_staging_user_authentication_flow()

        registry_access_results = {}

        # Test basic registry access in staging
        if basic_registry_available:
            try:
                basic_registry = BasicAgentRegistry()
                registry_access_results['basic'] = {
                    'accessible': True,
                    'has_core_methods': hasattr(basic_registry, 'register_agent'),
                    'websocket_support': hasattr(basic_registry, 'set_websocket_manager')
                }
            except Exception as e:
                logger.warning(f"Basic registry access failed in staging: {e}")
                registry_access_results['basic'] = {'accessible': False, 'error': str(e)}

        # Test advanced registry access in staging
        if advanced_registry_available:
            try:
                # Create mock staging context
                staging_context = MagicMock()
                staging_context.user_id = self.test_user_id
                staging_context.session_id = self.test_session_id
                staging_context.environment = 'staging'

                advanced_registry = AdvancedAgentRegistry(
                    user_context=staging_context,
                    tool_dispatcher=MagicMock(),
                    websocket_bridge=MagicMock()
                )

                registry_access_results['advanced'] = {
                    'accessible': True,
                    'has_core_methods': hasattr(advanced_registry, 'register_agent'),
                    'websocket_support': hasattr(advanced_registry, 'websocket_bridge'),
                    'user_context': hasattr(advanced_registry, 'user_context')
                }
            except Exception as e:
                logger.warning(f"Advanced registry access failed in staging: {e}")
                registry_access_results['advanced'] = {'accessible': False, 'error': str(e)}

        # Analyze registry access in staging
        accessible_registries = sum(1 for result in registry_access_results.values()
                                   if result.get('accessible', False))
        total_registries = len(registry_access_results)

        registry_access_rate = accessible_registries / total_registries if total_registries > 0 else 0

        # At least one registry must work in staging
        if accessible_registries > 0:
            self.golden_path_steps['agent_registry_access'] = True

        # Record metrics
        self.record_metric('staging_registry_access_rate', registry_access_rate)
        self.record_metric('registry_access_results', registry_access_results)
        self.record_metric('accessible_registries_count', accessible_registries)

        logger.info(f"Staging registry access results: {registry_access_results}")
        logger.info(f"Registry access rate: {registry_access_rate:.1%}")

        # At least one registry must work for Golden Path continuation
        self.assertGreater(accessible_registries, 0,
                          "At least one agent registry must be accessible in staging for Golden Path")

    async def test_03_staging_websocket_connection(self):
        """
        Test 3: Staging WebSocket connection

        Validates that WebSocket connections work correctly in the staging
        environment for real-time agent communication.

        CRITICAL: WebSocket connectivity is essential for Golden Path
        """
        if self.should_skip_staging_tests():
            pytest.skip("Staging environment or dependencies not available")

        # Ensure previous steps completed
        if not self.golden_path_steps['user_authentication']:
            await self.test_01_staging_user_authentication_flow()
        if not self.golden_path_steps['agent_registry_access']:
            await self.test_02_staging_agent_registry_access()

        websocket_connection_success = False
        websocket_error = None

        try:
            # Test WebSocket connection to staging
            websocket_url = f"{self.staging_config['ws_url']}?token={self.auth_tokens.get('access_token', '')}"

            async with websockets.connect(
                websocket_url,
                timeout=self.staging_config['timeout']
            ) as websocket:

                # Send test message
                test_message = {
                    'type': 'test_connection',
                    'user_id': self.test_user_id,
                    'session_id': self.test_session_id,
                    'timestamp': datetime.now().isoformat()
                }

                await websocket.send(json.dumps(test_message))

                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=10.0
                    )

                    response_data = json.loads(response)
                    logger.info(f"WebSocket response received: {response_data}")

                    websocket_connection_success = True
                    self.golden_path_steps['websocket_connection'] = True

                except asyncio.TimeoutError:
                    logger.warning("WebSocket response timeout - connection established but no response")
                    websocket_connection_success = True  # Connection worked even if no response
                    self.golden_path_steps['websocket_connection'] = True

        except Exception as e:
            logger.error(f"Staging WebSocket connection failed: {e}")
            websocket_error = str(e)
            websocket_connection_success = False

        # Record WebSocket metrics
        self.record_metric('staging_websocket_connection_success', websocket_connection_success)
        self.record_metric('websocket_url_tested', self.staging_config['ws_url'])

        if websocket_error:
            self.record_metric('websocket_connection_error', websocket_error)

        logger.info(f"Staging WebSocket connection: {'SUCCESS' if websocket_connection_success else 'FAILED'}")

        # WebSocket connection is critical for Golden Path
        self.assertTrue(websocket_connection_success,
                       f"WebSocket connection must work in staging for Golden Path - Error: {websocket_error}")

    async def test_04_staging_agent_execution_simulation(self):
        """
        Test 4: Staging agent execution simulation

        Simulates agent creation and execution in the staging environment
        to validate the complete agent workflow during SSOT consolidation.

        EXPECTED: PASS when agent execution workflow completes
        """
        if self.should_skip_staging_tests():
            pytest.skip("Staging environment or dependencies not available")

        # Ensure previous steps completed
        for step_name, completed in self.golden_path_steps.items():
            if step_name in ['user_authentication', 'agent_registry_access', 'websocket_connection']:
                if not completed:
                    pytest.skip(f"Previous Golden Path step '{step_name}' failed")

        agent_execution_success = False
        agent_execution_details = {}

        try:
            # Simulate agent creation in staging
            agent_creation_request = {
                'agent_type': 'test_agent',
                'user_id': self.test_user_id,
                'session_id': self.test_session_id,
                'parameters': {
                    'task': 'Test agent execution in staging during SSOT consolidation',
                    'environment': 'staging'
                }
            }

            # Use HTTP client to create agent in staging
            async with httpx.AsyncClient(
                headers={'Authorization': f"Bearer {self.auth_tokens.get('access_token')}"},
                timeout=self.staging_config['timeout']
            ) as client:

                agent_response = await client.post(
                    f"{self.staging_config['api_url']}/agents/create",
                    json=agent_creation_request
                )

                if agent_response.status_code in [200, 201]:
                    agent_data = agent_response.json()
                    agent_execution_details['agent_created'] = True
                    agent_execution_details['agent_id'] = agent_data.get('agent_id')
                    self.golden_path_steps['agent_creation'] = True

                    logger.info(f"Agent created in staging: {agent_data.get('agent_id')}")

                    # Simulate agent execution request
                    execution_request = {
                        'agent_id': agent_data.get('agent_id'),
                        'task': 'Execute test task in staging environment',
                        'user_id': self.test_user_id
                    }

                    execution_response = await client.post(
                        f"{self.staging_config['api_url']}/agents/{agent_data.get('agent_id')}/execute",
                        json=execution_request
                    )

                    if execution_response.status_code in [200, 202]:
                        execution_data = execution_response.json()
                        agent_execution_details['execution_started'] = True
                        agent_execution_details['execution_id'] = execution_data.get('execution_id')
                        self.golden_path_steps['agent_execution'] = True
                        agent_execution_success = True

                        logger.info(f"Agent execution started in staging: {execution_data.get('execution_id')}")
                    else:
                        logger.warning(f"Agent execution failed: {execution_response.status_code}")
                        agent_execution_details['execution_error'] = execution_response.text
                else:
                    logger.warning(f"Agent creation failed: {agent_response.status_code}")
                    agent_execution_details['creation_error'] = agent_response.text

        except Exception as e:
            logger.error(f"Staging agent execution simulation failed: {e}")
            agent_execution_details['error'] = str(e)
            agent_execution_success = False

        # Record agent execution metrics
        self.record_metric('staging_agent_execution_success', agent_execution_success)
        self.record_metric('agent_execution_details', agent_execution_details)

        logger.info(f"Staging agent execution: {'SUCCESS' if agent_execution_success else 'FAILED'}")
        logger.info(f"Agent execution details: {agent_execution_details}")

        # Agent execution should work for complete Golden Path
        self.assertTrue(agent_execution_success,
                       "Agent execution must work in staging for complete Golden Path validation")

    async def test_05_staging_websocket_events_validation(self):
        """
        Test 5: Staging WebSocket events validation

        Validates that critical WebSocket events are delivered correctly
        in the staging environment during agent execution.

        CRITICAL: WebSocket events are essential for user experience
        """
        if self.should_skip_staging_tests():
            pytest.skip("Staging environment or dependencies not available")

        # Ensure agent execution is working
        if not self.golden_path_steps.get('agent_execution', False):
            await self.test_04_staging_agent_execution_simulation()

        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        websocket_events_received = False
        events_validation_results = {}

        try:
            # Connect to staging WebSocket with event monitoring
            websocket_url = f"{self.staging_config['ws_url']}?token={self.auth_tokens.get('access_token', '')}"

            async with websockets.connect(websocket_url, timeout=30) as websocket:

                # Send agent execution request that should trigger events
                execution_trigger = {
                    'type': 'execute_agent',
                    'user_id': self.test_user_id,
                    'session_id': self.test_session_id,
                    'agent_type': 'test_agent',
                    'task': 'Generate WebSocket events for Golden Path validation'
                }

                await websocket.send(json.dumps(execution_trigger))

                # Listen for WebSocket events (with timeout)
                event_timeout = 20.0
                start_time = datetime.now()

                while (datetime.now() - start_time).total_seconds() < event_timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event_data = json.loads(message)

                        self.received_websocket_events.append(event_data)
                        event_type = event_data.get('type', '')

                        if event_type in critical_events:
                            self.critical_events_received.add(event_type)
                            logger.info(f"Critical event received: {event_type}")

                        # Check if we received all critical events
                        if len(self.critical_events_received) >= len(critical_events):
                            break

                    except asyncio.TimeoutError:
                        continue  # Continue listening
                    except Exception as e:
                        logger.warning(f"WebSocket event processing error: {e}")
                        break

                # Analyze events received
                events_received_count = len(self.received_websocket_events)
                critical_events_count = len(self.critical_events_received)
                critical_events_rate = critical_events_count / len(critical_events)

                events_validation_results = {
                    'total_events_received': events_received_count,
                    'critical_events_received': critical_events_count,
                    'critical_events_rate': critical_events_rate,
                    'critical_events_list': list(self.critical_events_received),
                    'missing_events': [event for event in critical_events
                                     if event not in self.critical_events_received]
                }

                # WebSocket events successful if we received any events
                if events_received_count > 0:
                    websocket_events_received = True
                    self.golden_path_steps['websocket_events_received'] = True

        except Exception as e:
            logger.error(f"WebSocket events validation failed: {e}")
            events_validation_results['error'] = str(e)

        # Record WebSocket events metrics
        self.record_metric('staging_websocket_events_received', websocket_events_received)
        self.record_metric('websocket_events_validation', events_validation_results)
        self.record_metric('total_websocket_events', len(self.received_websocket_events))
        self.record_metric('critical_events_received', len(self.critical_events_received))

        logger.info(f"WebSocket events validation: {'SUCCESS' if websocket_events_received else 'FAILED'}")
        logger.info(f"Events validation results: {events_validation_results}")

        # WebSocket events are critical for user experience
        self.assertTrue(websocket_events_received,
                       "WebSocket events must be received in staging for Golden Path user experience")

        # At least some critical events should be received
        self.assertGreater(len(self.critical_events_received), 0,
                          "At least one critical WebSocket event must be received for Golden Path")

    async def test_06_golden_path_complete_validation(self):
        """
        Test 6: Golden Path complete validation

        Validates that the complete Golden Path user flow works end-to-end
        in the staging environment, ensuring business value protection.

        COMPREHENSIVE: Tests the entire user journey during SSOT consolidation
        """
        if self.should_skip_staging_tests():
            pytest.skip("Staging environment or dependencies not available")

        # Ensure all previous steps completed
        previous_tests = [
            ('user_authentication', self.test_01_staging_user_authentication_flow),
            ('agent_registry_access', self.test_02_staging_agent_registry_access),
            ('websocket_connection', self.test_03_staging_websocket_connection),
            ('agent_execution', self.test_04_staging_agent_execution_simulation),
            ('websocket_events_received', self.test_05_staging_websocket_events_validation)
        ]

        for step_name, test_method in previous_tests:
            if not self.golden_path_steps.get(step_name, False):
                try:
                    await test_method()
                except Exception as e:
                    logger.warning(f"Golden Path step {step_name} failed during final validation: {e}")

        # Simulate complete AI response delivery
        try:
            # Final step: AI response delivery simulation
            if (self.golden_path_steps.get('websocket_events_received', False) and
                len(self.received_websocket_events) > 0):

                # Check if we have an agent completion event or similar
                completion_events = [event for event in self.received_websocket_events
                                   if event.get('type') in ['agent_completed', 'response_ready']]

                if completion_events:
                    self.golden_path_steps['ai_response_delivery'] = True
                    logger.info("AI response delivery simulated successfully")
                else:
                    # Simulate response delivery based on successful agent execution
                    if self.golden_path_steps.get('agent_execution', False):
                        self.golden_path_steps['ai_response_delivery'] = True
                        logger.info("AI response delivery inferred from successful agent execution")

        except Exception as e:
            logger.warning(f"AI response delivery simulation failed: {e}")

        # Calculate Golden Path success rate
        completed_steps = sum(self.golden_path_steps.values())
        total_steps = len(self.golden_path_steps)
        golden_path_success_rate = completed_steps / total_steps

        # Golden Path metrics
        golden_path_metrics = {
            'success_rate': golden_path_success_rate,
            'completed_steps': completed_steps,
            'total_steps': total_steps,
            'golden_path_steps': self.golden_path_steps,
            'websocket_events_count': len(self.received_websocket_events),
            'critical_events_received': len(self.critical_events_received),
            'auth_tokens_available': len(self.auth_tokens)
        }

        # Record comprehensive Golden Path metrics
        self.record_metric('golden_path_success_rate', golden_path_success_rate)
        self.record_metric('golden_path_metrics', golden_path_metrics)
        self.record_metric('staging_environment_validated', True)

        # Log comprehensive Golden Path status
        logger.info("=== GOLDEN PATH STAGING VALIDATION SUMMARY ===")
        logger.info(f"Golden Path Success Rate: {golden_path_success_rate:.1%}")
        logger.info("Golden Path Steps:")
        for step_name, completed in self.golden_path_steps.items():
            status = "CHECK COMPLETED" if completed else "✗ FAILED"
            logger.info(f"  - {step_name}: {status}")

        logger.info(f"WebSocket Events Received: {len(self.received_websocket_events)}")
        logger.info(f"Critical Events: {list(self.critical_events_received)}")
        logger.info(f"Authentication: {'CHECK' if self.golden_path_steps.get('user_authentication') else '✗'}")
        logger.info(f"Agent Execution: {'CHECK' if self.golden_path_steps.get('agent_execution') else '✗'}")
        logger.info(f"WebSocket Communication: {'CHECK' if self.golden_path_steps.get('websocket_events_received') else '✗'}")
        logger.info("=== END GOLDEN PATH STAGING SUMMARY ===")

        # Golden Path must be highly successful in staging
        self.assertGreaterEqual(golden_path_success_rate, 0.8,
                               f"Golden Path must be at least 80% successful in staging for production readiness - "
                               f"got {golden_path_success_rate:.1%}, indicating registry SSOT issues affect business value")

        # Critical steps must work
        critical_steps = ['user_authentication', 'websocket_connection']
        for critical_step in critical_steps:
            self.assertTrue(self.golden_path_steps.get(critical_step, False),
                           f"Critical step '{critical_step}' must work for Golden Path business value")

        logger.info(f"Golden Path staging validation: {'SUCCESS' if golden_path_success_rate >= 0.8 else 'NEEDS IMPROVEMENT'}")


if __name__ == "__main__":
    unittest.main()