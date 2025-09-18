"""
End-to-End WebSocket UnifiedIDManager Tests - GCP Staging

Complete business workflow validation using UnifiedIDManager IDs in WebSocket
infrastructure on GCP staging environment. Tests validate that migration
maintains business value delivery while ensuring proper ID management.

Business Value Justification:
- Segment: All (Complete user journey validation)
- Business Goal: Business Continuity & System Reliability
- Value Impact: Ensures migration maintains full chat functionality
- Strategic Impact: 500K+ ARR depends on reliable end-to-end WebSocket workflows
"""

import pytest
import asyncio
import json
from typing import Dict, List, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.websocket_helpers import WebSocketTestClient
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.gcp_staging
class UnifiedIdManagerWebSocketE2ETests(SSotBaseTestCase):
    """
    End-to-end validation of UnifiedIDManager in complete WebSocket workflows.

    Tests complete user journeys on GCP staging to ensure migration
    maintains business value while implementing proper ID management.
    """

    def setup_method(self, method=None):
        """Set up E2E test environment."""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.staging_base_url = "wss://api.staging.netrasystems.ai"
        self.business_critical_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

    async def test_complete_chat_workflow_with_unified_ids(self):
        """
        Test complete chat workflow using UnifiedIDManager IDs.

        Validates that end-to-end chat functionality works properly
        when WebSocket infrastructure uses structured ID patterns.
        """
        # Test scenario configuration
        test_user = {
            'user_id': self.id_manager.generate_id(IDType.USER, prefix="e2e_test"),
            'email': 'e2e-test@staging.netrasystems.ai',
            'subscription_tier': 'enterprise'
        }

        chat_scenario = {
            'message': "Help me analyze cost optimization opportunities for my cloud infrastructure",
            'expected_agent': 'cost_optimizer',
            'expected_tools': ['analyze_costs', 'recommend_optimizations'],
            'timeout_seconds': 60
        }

        workflow_results = {
            'websocket_connection': None,
            'message_sent': False,
            'events_received': [],
            'agent_response': None,
            'id_validation_results': {},
            'business_value_delivered': False
        }

        try:
            # Create test user authentication token
            auth_token = await self._create_test_user_token(test_user)

            # Establish WebSocket connection with structured connection ID tracking
            async with WebSocketTestClient(
                base_url=self.staging_base_url,
                token=auth_token,
                connection_id_callback=self._validate_connection_id_format
            ) as websocket_client:

                workflow_results['websocket_connection'] = True

                # Send chat message
                message_payload = {
                    'type': 'agent_request',
                    'agent': chat_scenario['expected_agent'],
                    'message': chat_scenario['message'],
                    'thread_id': self.id_manager.generate_id(IDType.THREAD, prefix="e2e_chat"),
                    'request_id': self.id_manager.generate_id(IDType.REQUEST, prefix="e2e_msg")
                }

                await websocket_client.send_json(message_payload)
                workflow_results['message_sent'] = True

                # Collect all events until completion
                collected_events = []
                timeout_reached = False

                try:
                    async with asyncio.timeout(chat_scenario['timeout_seconds']):
                        async for event in websocket_client.receive_events():
                            collected_events.append(event)

                            # Validate event ID format
                            event_id = event.get('event_id') or event.get('message_id')
                            if event_id:
                                self._validate_event_id_format(event_id, event.get('type'))

                            # Check for completion
                            if event.get('type') == 'agent_completed':
                                break

                except asyncio.TimeoutError:
                    timeout_reached = True

                workflow_results['events_received'] = collected_events
                workflow_results['timeout_reached'] = timeout_reached

                # Validate business critical events were received
                received_event_types = [event.get('type') for event in collected_events]
                missing_critical_events = []

                for critical_event in self.business_critical_events:
                    if critical_event not in received_event_types:
                        missing_critical_events.append(critical_event)

                # Validate agent response content
                agent_completed_events = [e for e in collected_events if e.get('type') == 'agent_completed']
                if agent_completed_events:
                    final_response = agent_completed_events[-1]
                    response_data = final_response.get('data', {})

                    # Check for business value indicators
                    business_value_indicators = [
                        'recommendations' in str(response_data).lower(),
                        'savings' in str(response_data).lower(),
                        'optimization' in str(response_data).lower(),
                        len(str(response_data)) > 100  # Substantial response
                    ]

                    workflow_results['business_value_delivered'] = sum(business_value_indicators) >= 2
                    workflow_results['agent_response'] = response_data

                # Validate ID formats across the entire workflow
                id_validation_results = self._comprehensive_id_format_validation(
                    message_payload, collected_events
                )
                workflow_results['id_validation_results'] = id_validation_results

        except Exception as e:
            workflow_results['error'] = str(e)

        # Record comprehensive metrics
        self.record_metric('e2e_chat_workflow_results', {
            'test_user': test_user['user_id'],
            'workflow_completed': workflow_results.get('websocket_connection', False) and workflow_results.get('message_sent', False),
            'events_received_count': len(workflow_results['events_received']),
            'business_critical_events_received': len(set(received_event_types) & set(self.business_critical_events)),
            'missing_critical_events': missing_critical_events,
            'business_value_delivered': workflow_results.get('business_value_delivered', False),
            'timeout_reached': workflow_results.get('timeout_reached', False),
            'id_validation_passed': id_validation_results.get('all_formats_valid', False),
            'total_ids_validated': id_validation_results.get('total_ids_validated', 0)
        })

        # Critical assertions for business value
        assert workflow_results.get('websocket_connection', False), \
            "Failed to establish WebSocket connection to staging environment"

        assert workflow_results.get('message_sent', False), \
            "Failed to send chat message through WebSocket"

        assert len(missing_critical_events) == 0, \
            f"Missing {len(missing_critical_events)} business-critical WebSocket events: {missing_critical_events}"

        assert workflow_results.get('business_value_delivered', False), \
            f"Agent response did not deliver business value. Response: {workflow_results.get('agent_response', 'None')}"

        assert not workflow_results.get('timeout_reached', False), \
            f"Chat workflow timed out after {chat_scenario['timeout_seconds']} seconds"

        assert id_validation_results.get('all_formats_valid', False), \
            f"ID format validation failed: {id_validation_results.get('validation_failures', [])}"

    async def test_multi_user_concurrent_websocket_e2e(self):
        """
        Test multiple users concurrently using WebSocket with UnifiedIDManager IDs.

        Validates enterprise-scale concurrent usage maintains proper
        user isolation and business value delivery for all users.
        """
        # Concurrent test configuration
        num_concurrent_users = 10
        concurrent_scenarios = [
            {'agent': 'cost_optimizer', 'message': 'Analyze my AWS costs', 'tier': 'enterprise'},
            {'agent': 'triage_agent', 'message': 'Help me troubleshoot performance issues', 'tier': 'mid'},
            {'agent': 'data_helper', 'message': 'What data do I need for analysis?', 'tier': 'early'},
        ]

        concurrent_results = {}

        async def run_user_scenario(user_index: int):
            """Run complete WebSocket scenario for a single user."""
            scenario = concurrent_scenarios[user_index % len(concurrent_scenarios)]

            test_user = {
                'user_id': self.id_manager.generate_id(IDType.USER, prefix=f"concurrent_{user_index}"),
                'email': f'concurrent-user-{user_index}@staging.netrasystems.ai',
                'subscription_tier': scenario['tier'],
                'user_index': user_index
            }

            user_results = {
                'user_info': test_user,
                'connection_established': False,
                'message_sent': False,
                'events_received': [],
                'business_value_delivered': False,
                'id_validation_passed': False,
                'execution_time_seconds': 0
            }

            import time
            start_time = time.perf_counter()

            try:
                # Create user-specific auth token
                auth_token = await self._create_test_user_token(test_user)

                # User-specific WebSocket connection
                async with WebSocketTestClient(
                    base_url=self.staging_base_url,
                    token=auth_token,
                    user_context=test_user
                ) as websocket_client:

                    user_results['connection_established'] = True

                    # Send user-specific message
                    message_payload = {
                        'type': 'agent_request',
                        'agent': scenario['agent'],
                        'message': scenario['message'],
                        'thread_id': self.id_manager.generate_id(IDType.THREAD, prefix=f"user_{user_index}"),
                        'request_id': self.id_manager.generate_id(IDType.REQUEST, prefix=f"req_{user_index}"),
                        'user_context': test_user
                    }

                    await websocket_client.send_json(message_payload)
                    user_results['message_sent'] = True

                    # Collect events for this user
                    user_events = []
                    async with asyncio.timeout(30):  # 30 second timeout per user
                        async for event in websocket_client.receive_events():
                            user_events.append(event)
                            if event.get('type') == 'agent_completed':
                                break

                    user_results['events_received'] = user_events

                    # Validate user got appropriate business response
                    agent_responses = [e for e in user_events if e.get('type') == 'agent_completed']
                    if agent_responses:
                        response_content = str(agent_responses[-1].get('data', ''))
                        user_results['business_value_delivered'] = len(response_content) > 50

                    # Validate ID formats for this user's session
                    user_id_validation = self._comprehensive_id_format_validation(
                        message_payload, user_events
                    )
                    user_results['id_validation_passed'] = user_id_validation.get('all_formats_valid', False)

            except Exception as e:
                user_results['error'] = str(e)

            finally:
                end_time = time.perf_counter()
                user_results['execution_time_seconds'] = end_time - start_time

            return test_user['user_id'], user_results

        # Execute all users concurrently
        tasks = [run_user_scenario(i) for i in range(num_concurrent_users)]
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_users = 0
        failed_users = 0
        total_events_collected = 0
        users_with_business_value = 0
        users_with_valid_ids = 0

        for result in completed_results:
            if isinstance(result, Exception):
                failed_users += 1
                continue

            user_id, user_results = result
            concurrent_results[user_id] = user_results

            if user_results.get('connection_established') and user_results.get('message_sent'):
                successful_users += 1

            total_events_collected += len(user_results.get('events_received', []))

            if user_results.get('business_value_delivered'):
                users_with_business_value += 1

            if user_results.get('id_validation_passed'):
                users_with_valid_ids += 1

        # Calculate success metrics
        connection_success_rate = successful_users / num_concurrent_users * 100
        business_value_rate = users_with_business_value / max(1, successful_users) * 100
        id_validation_rate = users_with_valid_ids / max(1, successful_users) * 100

        # Record comprehensive concurrent metrics
        self.record_metric('multi_user_concurrent_e2e_results', {
            'total_users': num_concurrent_users,
            'successful_users': successful_users,
            'failed_users': failed_users,
            'connection_success_rate': connection_success_rate,
            'business_value_delivery_rate': business_value_rate,
            'id_validation_success_rate': id_validation_rate,
            'total_events_collected': total_events_collected,
            'average_events_per_user': total_events_collected / max(1, successful_users)
        })

        # Enterprise-grade concurrent performance assertions
        assert connection_success_rate >= 90.0, \
            f"Concurrent WebSocket connection success rate too low: {connection_success_rate:.1f}%. " \
            f"Enterprise deployment requires >90% concurrent connection reliability."

        assert business_value_rate >= 80.0, \
            f"Business value delivery rate too low: {business_value_rate:.1f}%. " \
            f"Most users should receive meaningful agent responses in concurrent scenarios."

        assert id_validation_rate >= 95.0, \
            f"ID validation success rate too low: {id_validation_rate:.1f}%. " \
            f"UnifiedIDManager ID format compliance critical for system consistency."

        assert failed_users == 0, \
            f"Found {failed_users} failed users in concurrent testing. " \
            f"All users should successfully complete WebSocket workflows concurrently."

    async def test_websocket_enterprise_data_isolation_e2e(self):
        """
        Test enterprise-grade data isolation across WebSocket users.

        Validates that different enterprise users with sensitive data
        maintain complete isolation in WebSocket communications.
        """
        # Enterprise test scenarios with different compliance requirements
        enterprise_users = [
            {
                'user_id': self.id_manager.generate_id(IDType.USER, prefix="hipaa_healthcare"),
                'email': 'healthcare-admin@staging.netrasystems.ai',
                'compliance_tier': 'HIPAA',
                'data_sensitivity': 'PHI',
                'test_message': 'Analyze patient cost data for our healthcare network'
            },
            {
                'user_id': self.id_manager.generate_id(IDType.USER, prefix="sox_financial"),
                'email': 'financial-controller@staging.netrasystems.ai',
                'compliance_tier': 'SOX',
                'data_sensitivity': 'Financial',
                'test_message': 'Review quarterly financial optimization strategies'
            },
            {
                'user_id': self.id_manager.generate_id(IDType.USER, prefix="sec_government"),
                'email': 'government-analyst@staging.netrasystems.ai',
                'compliance_tier': 'SEC',
                'data_sensitivity': 'Classified',
                'test_message': 'Analyze defense spending optimization opportunities'
            }
        ]

        isolation_results = {
            'user_sessions': {},
            'cross_contamination_checks': [],
            'compliance_validation': {}
        }

        # Execute isolated sessions for each enterprise user
        for user_config in enterprise_users:
            user_id = user_config['user_id']

            # Create isolated session for this user
            auth_token = await self._create_test_user_token(user_config)

            async with WebSocketTestClient(
                base_url=self.staging_base_url,
                token=auth_token,
                isolation_context=user_config['compliance_tier']
            ) as websocket_client:

                # Send compliance-sensitive message
                sensitive_message = {
                    'type': 'agent_request',
                    'agent': 'compliance_analyzer',
                    'message': user_config['test_message'],
                    'thread_id': self.id_manager.generate_id(IDType.THREAD, prefix=f"secure_{user_config['compliance_tier']}"),
                    'request_id': self.id_manager.generate_id(IDType.REQUEST, prefix=f"sensitive_{user_config['data_sensitivity']}"),
                    'compliance_context': {
                        'tier': user_config['compliance_tier'],
                        'data_sensitivity': user_config['data_sensitivity'],
                        'user_id': user_id
                    }
                }

                await websocket_client.send_json(sensitive_message)

                # Collect this user's session data
                user_events = []
                async with asyncio.timeout(45):
                    async for event in websocket_client.receive_events():
                        user_events.append(event)
                        if event.get('type') == 'agent_completed':
                            break

                isolation_results['user_sessions'][user_id] = {
                    'user_config': user_config,
                    'message_sent': sensitive_message,
                    'events_received': user_events,
                    'session_ids': self._extract_session_ids(sensitive_message, user_events),
                    'response_content': self._extract_response_content(user_events)
                }

        # Validate enterprise data isolation
        contamination_violations = []

        for user_id_1, session_1 in isolation_results['user_sessions'].items():
            for user_id_2, session_2 in isolation_results['user_sessions'].items():
                if user_id_1 != user_id_2:
                    # Check for cross-contamination between different compliance tiers
                    contamination_check = self._check_cross_user_contamination(
                        session_1, session_2, user_id_1, user_id_2
                    )
                    if contamination_check['contamination_detected']:
                        contamination_violations.append(contamination_check)

        # Validate compliance-specific ID patterns
        compliance_validation = {}
        for user_id, session in isolation_results['user_sessions'].items():
            user_config = session['user_config']
            compliance_tier = user_config['compliance_tier']

            compliance_check = self._validate_compliance_id_patterns(
                session['session_ids'], compliance_tier
            )
            compliance_validation[user_id] = compliance_check

        isolation_results['cross_contamination_checks'] = contamination_violations
        isolation_results['compliance_validation'] = compliance_validation

        # Record enterprise isolation metrics
        self.record_metric('enterprise_data_isolation_results', {
            'total_enterprise_users': len(enterprise_users),
            'compliance_tiers_tested': [u['compliance_tier'] for u in enterprise_users],
            'contamination_violations': len(contamination_violations),
            'compliance_validation_summary': {
                tier: all(checks.values()) if isinstance(checks, dict) else False
                for tier, checks in compliance_validation.items()
            }
        })

        # Critical enterprise security assertions
        assert len(contamination_violations) == 0, \
            f"Found {len(contamination_violations)} cross-user data contamination violations. " \
            f"Enterprise compliance requires perfect user isolation: {contamination_violations}"

        # Validate each compliance tier passed validation
        failed_compliance_validations = []
        for user_id, validation_results in compliance_validation.items():
            if isinstance(validation_results, dict):
                failed_checks = [k for k, v in validation_results.items() if not v]
                if failed_checks:
                    failed_compliance_validations.append({'user': user_id, 'failed_checks': failed_checks})

        assert len(failed_compliance_validations) == 0, \
            f"Found {len(failed_compliance_validations)} compliance validation failures. " \
            f"Enterprise deployment requires perfect compliance validation: {failed_compliance_validations}"

    # Helper methods for E2E testing

    async def _create_test_user_token(self, user_config: Dict[str, Any]) -> str:
        """Create authentication token for test user."""
        # Mock implementation - in real tests this would call auth service
        return f"test_token_{user_config['user_id']}"

    def _validate_connection_id_format(self, connection_id: str) -> bool:
        """Validate WebSocket connection ID follows UnifiedIDManager format."""
        if not connection_id:
            return False
        return self.id_manager.is_valid_id_format_compatible(connection_id)

    def _validate_event_id_format(self, event_id: str, event_type: str) -> bool:
        """Validate WebSocket event ID follows structured format."""
        if not event_id:
            return False

        is_compatible = self.id_manager.is_valid_id_format_compatible(event_id)

        # Record validation for metrics
        validation_key = f'event_id_validation_{event_type}'
        current_validations = self.test_metrics.get(validation_key, [])
        current_validations.append({'event_id': event_id, 'valid': is_compatible})
        self.test_metrics[validation_key] = current_validations

        return is_compatible

    def _comprehensive_id_format_validation(self, message_payload: Dict, events: List[Dict]) -> Dict[str, Any]:
        """Perform comprehensive ID format validation across workflow."""
        validation_results = {
            'total_ids_validated': 0,
            'valid_ids': 0,
            'invalid_ids': 0,
            'validation_failures': [],
            'all_formats_valid': True
        }

        # Validate IDs in message payload
        payload_ids = [
            message_payload.get('thread_id'),
            message_payload.get('request_id'),
            message_payload.get('user_id')
        ]

        for payload_id in payload_ids:
            if payload_id:
                validation_results['total_ids_validated'] += 1
                if self.id_manager.is_valid_id_format_compatible(payload_id):
                    validation_results['valid_ids'] += 1
                else:
                    validation_results['invalid_ids'] += 1
                    validation_results['validation_failures'].append({
                        'id': payload_id, 'source': 'message_payload'
                    })
                    validation_results['all_formats_valid'] = False

        # Validate IDs in received events
        for event in events:
            event_ids = [
                event.get('event_id'),
                event.get('message_id'),
                event.get('thread_id'),
                event.get('run_id')
            ]

            for event_id in event_ids:
                if event_id:
                    validation_results['total_ids_validated'] += 1
                    if self.id_manager.is_valid_id_format_compatible(event_id):
                        validation_results['valid_ids'] += 1
                    else:
                        validation_results['invalid_ids'] += 1
                        validation_results['validation_failures'].append({
                            'id': event_id, 'source': f'event_{event.get("type", "unknown")}'
                        })
                        validation_results['all_formats_valid'] = False

        return validation_results

    def _extract_session_ids(self, message: Dict, events: List[Dict]) -> List[str]:
        """Extract all session-related IDs from message and events."""
        session_ids = []

        # From message
        for id_field in ['thread_id', 'request_id', 'user_id']:
            if message.get(id_field):
                session_ids.append(message[id_field])

        # From events
        for event in events:
            for id_field in ['event_id', 'message_id', 'thread_id', 'run_id']:
                if event.get(id_field):
                    session_ids.append(event[id_field])

        return list(set(session_ids))  # Remove duplicates

    def _extract_response_content(self, events: List[Dict]) -> str:
        """Extract agent response content from events."""
        for event in events:
            if event.get('type') == 'agent_completed':
                return str(event.get('data', ''))
        return ''

    def _check_cross_user_contamination(self, session_1: Dict, session_2: Dict,
                                       user_id_1: str, user_id_2: str) -> Dict[str, Any]:
        """Check for cross-user data contamination between sessions."""
        contamination_check = {
            'user_1': user_id_1,
            'user_2': user_id_2,
            'contamination_detected': False,
            'contamination_details': []
        }

        # Check if User 1's IDs appear in User 2's session
        user_1_ids = set(session_1['session_ids'])
        user_2_ids = set(session_2['session_ids'])

        id_overlap = user_1_ids & user_2_ids
        if id_overlap:
            contamination_check['contamination_detected'] = True
            contamination_check['contamination_details'].append({
                'type': 'id_overlap',
                'overlapping_ids': list(id_overlap)
            })

        # Check if User 1's response content appears in User 2's response
        user_1_content = session_1.get('response_content', '').lower()
        user_2_content = session_2.get('response_content', '').lower()

        if user_1_content and user_2_content and len(user_1_content) > 20:
            # Check for substantial content overlap (>50% similar)
            content_similarity = self._calculate_content_similarity(user_1_content, user_2_content)
            if content_similarity > 0.5:
                contamination_check['contamination_detected'] = True
                contamination_check['contamination_details'].append({
                    'type': 'content_similarity',
                    'similarity_score': content_similarity
                })

        return contamination_check

    def _calculate_content_similarity(self, content_1: str, content_2: str) -> float:
        """Calculate content similarity between two response strings."""
        # Simple similarity calculation - in production use more sophisticated methods
        words_1 = set(content_1.split())
        words_2 = set(content_2.split())

        if not words_1 or not words_2:
            return 0.0

        intersection = words_1 & words_2
        union = words_1 | words_2

        return len(intersection) / len(union) if union else 0.0

    def _validate_compliance_id_patterns(self, session_ids: List[str], compliance_tier: str) -> Dict[str, bool]:
        """Validate ID patterns meet compliance tier requirements."""
        compliance_validation = {
            'all_ids_structured': True,
            'compliance_prefix_present': True,
            'no_plain_uuids': True,
            'sufficient_entropy': True
        }

        for session_id in session_ids:
            # All IDs must be UnifiedIDManager compatible
            if not self.id_manager.is_valid_id_format_compatible(session_id):
                compliance_validation['all_ids_structured'] = False

            # Check for plain UUID format (not allowed in compliance environments)
            try:
                import uuid
                uuid.UUID(session_id)
                compliance_validation['no_plain_uuids'] = False  # Plain UUID found
            except ValueError:
                pass  # Not a plain UUID, which is good

            # Check for compliance-appropriate prefixes
            compliance_prefixes = {
                'HIPAA': ['hipaa', 'healthcare', 'secure', 'phi'],
                'SOX': ['sox', 'financial', 'secure', 'fin'],
                'SEC': ['sec', 'government', 'secure', 'classified']
            }

            expected_prefixes = compliance_prefixes.get(compliance_tier, [])
            has_appropriate_prefix = any(prefix in session_id.lower() for prefix in expected_prefixes)
            if not has_appropriate_prefix:
                compliance_validation['compliance_prefix_present'] = False

            # Check for sufficient entropy (structured IDs should have enough randomness)
            if len(session_id) < 20:  # Minimum length for adequate entropy
                compliance_validation['sufficient_entropy'] = False

        return compliance_validation


if __name__ == '__main__':
    # MIGRATED: Use SSOT unified test runner
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category e2e --pattern "*unified_id_manager_websocket_e2e*" --env staging')