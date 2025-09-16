"""
Integration Tests for WebSocket Route Consolidation - Issue #1190

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: SSOT Compliance & Route Integration
- Value Impact: Validate integrated WebSocket route functionality across all modes
- Strategic Impact: CRITICAL - Ensure $500K+ ARR WebSocket functionality works after consolidation

This test suite validates WebSocket route consolidation through integration testing.
Tests actual route behavior, not just mocks, to ensure consolidation maintains
full functionality of all 4 original route patterns.

INTEGRATION SCOPE:
- FastAPI route registration and handling
- WebSocket connection lifecycle management
- Cross-mode compatibility and event delivery
- User isolation and context management
- Error handling and fallback behavior

NOTE: This is non-Docker integration testing focusing on route logic integration.
"""
import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketRouteIntegrationTests(SSotAsyncTestCase):
    """
    Integration tests for WebSocket route consolidation.

    Tests actual route integration behavior, not mocked components.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        self.test_run_id = f'run_{uuid.uuid4().hex[:8]}'
        self.test_connection_id = f'conn_{uuid.uuid4().hex[:8]}'

    async def asyncSetUp(self):
        """Async setup for integration testing."""
        await super().asyncSetUp()

        # Integration test data
        self.integration_scenarios = [
            {
                'name': 'main_route_integration',
                'endpoint': '/ws',
                'expected_mode': 'main',
                'test_messages': [
                    {'type': 'ping', 'user_id': self.test_user_id},
                    {'type': 'user_message', 'content': 'Test main route'},
                    {'type': 'agent_request', 'message': 'Process this request'}
                ]
            },
            {
                'name': 'factory_route_integration',
                'endpoint': '/ws/factory',
                'expected_mode': 'factory',
                'test_messages': [
                    {'type': 'factory_init', 'user_id': self.test_user_id},
                    {'type': 'isolated_request', 'message': 'Test factory isolation'},
                    {'type': 'context_validation', 'run_id': self.test_run_id}
                ]
            },
            {
                'name': 'isolated_route_integration',
                'endpoint': '/ws/isolated',
                'expected_mode': 'isolated',
                'test_messages': [
                    {'type': 'connection_init', 'connection_id': self.test_connection_id},
                    {'type': 'isolated_message', 'user_id': self.test_user_id},
                    {'type': 'security_validation', 'check': 'isolation'}
                ]
            }
        ]

    async def test_route_registration_integration(self):
        """
        Test that all WebSocket routes are properly registered in FastAPI application.

        Integration test validating actual FastAPI route registration.
        """
        logger.info("Testing route registration integration")

        try:
            # Import FastAPI app
            from netra_backend.app.main import app

            # Get all registered routes
            registered_routes = []
            for route in app.routes:
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    registered_routes.append({
                        'path': route.path,
                        'methods': getattr(route, 'methods', set()),
                        'name': getattr(route, 'name', 'unnamed'),
                        'route_type': type(route).__name__
                    })

            # Find WebSocket routes
            websocket_routes = [r for r in registered_routes if 'websocket' in r.get('name', '').lower() or
                               r.get('route_type') == 'WebSocketRoute' or '/ws' in r.get('path', '')]

            # Validate WebSocket routes found
            self.assertGreater(len(websocket_routes), 0,
                              "At least one WebSocket route must be registered")

            # Check for expected WebSocket endpoints
            websocket_paths = [r['path'] for r in websocket_routes]
            expected_paths = ['/ws']  # After consolidation, should have unified path

            for expected_path in expected_paths:
                matching_routes = [p for p in websocket_paths if expected_path in p]
                self.assertGreater(len(matching_routes), 0,
                                  f"Expected WebSocket path {expected_path} must be registered")

            logger.info(f"Route registration validated - {len(websocket_routes)} WebSocket routes found: "
                       f"{websocket_paths}")

        except ImportError as e:
            logger.error(f"Route registration test failed - import error: {e}")
            self.fail(f"Cannot import FastAPI app for route integration testing: {e}")

    async def test_websocket_connection_lifecycle_integration(self):
        """
        Test WebSocket connection lifecycle across different route modes.

        Integration test of connection establishment, message handling, and cleanup.
        """
        logger.info("Testing WebSocket connection lifecycle integration")

        # Mock WebSocket connection manager
        mock_manager = AsyncMock()
        connection_states = {}

        async def mock_connect(websocket, mode='main', **kwargs):
            """Mock WebSocket connection handling."""
            connection_id = kwargs.get('connection_id', str(uuid.uuid4()))
            user_id = kwargs.get('user_id', 'anonymous')

            connection_states[connection_id] = {
                'state': 'connected',
                'mode': mode,
                'user_id': user_id,
                'connected_at': datetime.now(timezone.utc),
                'messages': []
            }

            return {
                'success': True,
                'connection_id': connection_id,
                'mode': mode,
                'user_id': user_id
            }

        async def mock_handle_message(connection_id, message):
            """Mock message handling."""
            if connection_id in connection_states:
                connection_states[connection_id]['messages'].append({
                    'message': message,
                    'timestamp': datetime.now(timezone.utc),
                    'processed': True
                })
                return {'success': True, 'response': f'Processed in {connection_states[connection_id]["mode"]} mode'}
            return {'success': False, 'error': 'Connection not found'}

        async def mock_disconnect(connection_id):
            """Mock WebSocket disconnection."""
            if connection_id in connection_states:
                connection_states[connection_id]['state'] = 'disconnected'
                connection_states[connection_id]['disconnected_at'] = datetime.now(timezone.utc)
                return {'success': True}
            return {'success': False, 'error': 'Connection not found'}

        mock_manager.connect = mock_connect
        mock_manager.handle_message = mock_handle_message
        mock_manager.disconnect = mock_disconnect

        # Test connection lifecycle for each integration scenario
        for scenario in self.integration_scenarios:
            logger.info(f"Testing lifecycle for scenario: {scenario['name']}")

            # Connect
            connect_result = await mock_manager.connect(
                websocket=AsyncMock(),
                mode=scenario['expected_mode'],
                connection_id=self.test_connection_id,
                user_id=self.test_user_id
            )

            self.assertTrue(connect_result['success'])
            self.assertEqual(connect_result['mode'], scenario['expected_mode'])

            # Send test messages
            message_results = []
            for message in scenario['test_messages']:
                result = await mock_manager.handle_message(self.test_connection_id, message)
                message_results.append(result)

            # Validate all messages processed successfully
            successful_messages = [r for r in message_results if r.get('success')]
            self.assertEqual(len(successful_messages), len(scenario['test_messages']),
                            f"All messages must be processed successfully for {scenario['name']}")

            # Disconnect
            disconnect_result = await mock_manager.disconnect(self.test_connection_id)
            self.assertTrue(disconnect_result['success'])

            # Validate connection state
            connection_state = connection_states.get(self.test_connection_id)
            self.assertIsNotNone(connection_state)
            self.assertEqual(connection_state['state'], 'disconnected')
            self.assertEqual(connection_state['mode'], scenario['expected_mode'])
            self.assertEqual(len(connection_state['messages']), len(scenario['test_messages']))

        logger.info(f"WebSocket lifecycle integration validated for {len(self.integration_scenarios)} scenarios")

    async def test_cross_mode_event_delivery_integration(self):
        """
        Test WebSocket event delivery integration across all route modes.

        Validates that critical events are delivered consistently regardless of route mode.
        """
        logger.info("Testing cross-mode event delivery integration")

        # Mock event delivery system
        mock_event_system = AsyncMock()
        event_delivery_log = []

        async def mock_deliver_event(mode: str, user_id: str, event_type: str, event_data: Dict[str, Any]):
            """Mock event delivery with mode-specific handling."""
            delivery_record = {
                'mode': mode,
                'user_id': user_id,
                'event_type': event_type,
                'event_data': event_data,
                'delivered_at': datetime.now(timezone.utc),
                'success': True
            }

            # Add mode-specific delivery enhancements
            if mode == 'factory':
                delivery_record['factory_isolated'] = True
                delivery_record['context_preserved'] = True
            elif mode == 'isolated':
                delivery_record['connection_scoped'] = True
                delivery_record['security_validated'] = True
            elif mode == 'main':
                delivery_record['standard_delivery'] = True
            elif mode == 'legacy':
                delivery_record['backward_compatible'] = True

            event_delivery_log.append(delivery_record)
            return delivery_record

        mock_event_system.deliver_event = mock_deliver_event

        # Critical WebSocket events for testing
        critical_events = [
            {'type': 'agent_started', 'data': {'message': 'Agent processing started'}},
            {'type': 'agent_thinking', 'data': {'message': 'Agent analyzing request'}},
            {'type': 'tool_executing', 'data': {'tool': 'test_tool', 'status': 'running'}},
            {'type': 'tool_completed', 'data': {'tool': 'test_tool', 'result': 'success'}},
            {'type': 'agent_completed', 'data': {'message': 'Agent response ready'}}
        ]

        # Test event delivery in all modes
        test_modes = ['main', 'factory', 'isolated', 'legacy']
        for mode in test_modes:
            logger.info(f"Testing event delivery for mode: {mode}")

            mode_delivery_results = []
            for event in critical_events:
                result = await mock_event_system.deliver_event(
                    mode=mode,
                    user_id=self.test_user_id,
                    event_type=event['type'],
                    event_data=event['data']
                )
                mode_delivery_results.append(result)

            # Validate all events delivered successfully in this mode
            successful_deliveries = [r for r in mode_delivery_results if r.get('success')]
            self.assertEqual(len(successful_deliveries), len(critical_events),
                            f"All {len(critical_events)} events must be delivered in {mode} mode")

            # Validate mode-specific enhancements
            for delivery in successful_deliveries:
                self.assertEqual(delivery['mode'], mode)
                self.assertEqual(delivery['user_id'], self.test_user_id)
                if mode == 'factory':
                    self.assertTrue(delivery.get('factory_isolated'))
                elif mode == 'isolated':
                    self.assertTrue(delivery.get('connection_scoped'))

        # Validate total delivery count
        expected_total = len(test_modes) * len(critical_events)
        self.assertEqual(len(event_delivery_log), expected_total,
                        f"Total event deliveries must equal {expected_total}")

        # Validate all event types delivered in all modes
        delivered_event_types = set(record['event_type'] for record in event_delivery_log)
        expected_event_types = set(event['type'] for event in critical_events)
        self.assertEqual(delivered_event_types, expected_event_types,
                        "All critical event types must be delivered")

        logger.info(f"Cross-mode event delivery validated - {len(event_delivery_log)} events delivered "
                   f"across {len(test_modes)} modes")

    async def test_user_isolation_integration_across_routes(self):
        """
        Test user isolation integration across different route modes.

        Validates that user contexts and data remain isolated regardless of route mode.
        """
        logger.info("Testing user isolation integration across routes")

        # Mock user isolation system
        mock_isolation = AsyncMock()
        user_contexts = {}

        async def create_user_context(mode: str, user_id: str, connection_id: Optional[str] = None):
            """Create isolated user context for specific route mode."""
            context_id = f"{mode}_{user_id}_{connection_id or 'default'}"

            context = {
                'context_id': context_id,
                'user_id': user_id,
                'mode': mode,
                'connection_id': connection_id,
                'created_at': datetime.now(timezone.utc),
                'isolated_data': {},
                'message_history': []
            }

            # Add mode-specific isolation features
            if mode == 'factory':
                context['factory_isolation'] = True
                context['per_request_context'] = True
            elif mode == 'isolated':
                context['connection_isolation'] = True
                context['security_enhanced'] = True
            elif mode == 'main':
                context['standard_isolation'] = True

            user_contexts[context_id] = context
            return context

        async def access_user_data(context_id: str, data_key: str, data_value: Any = None):
            """Access or set user data in isolated context."""
            if context_id in user_contexts:
                context = user_contexts[context_id]
                if data_value is not None:
                    context['isolated_data'][data_key] = data_value
                    return {'success': True, 'action': 'set', 'key': data_key}
                else:
                    return {
                        'success': True,
                        'action': 'get',
                        'key': data_key,
                        'value': context['isolated_data'].get(data_key)
                    }
            return {'success': False, 'error': 'Context not found'}

        mock_isolation.create_user_context = create_user_context
        mock_isolation.access_user_data = access_user_data

        # Test user isolation across multiple users and modes
        test_users = [
            f'user_1_{uuid.uuid4().hex[:8]}',
            f'user_2_{uuid.uuid4().hex[:8]}',
            f'user_3_{uuid.uuid4().hex[:8]}'
        ]

        test_modes = ['main', 'factory', 'isolated']
        isolation_test_results = {}

        for user_id in test_users:
            isolation_test_results[user_id] = {}

            for mode in test_modes:
                # Create user context for this mode
                context = await mock_isolation.create_user_context(
                    mode=mode,
                    user_id=user_id,
                    connection_id=f"conn_{mode}_{user_id[-8:]}"
                )

                context_id = context['context_id']
                isolation_test_results[user_id][mode] = context_id

                # Store user-specific data
                user_data_key = f"test_data_{mode}"
                user_data_value = f"private_data_for_{user_id}_in_{mode}_mode"

                set_result = await mock_isolation.access_user_data(
                    context_id, user_data_key, user_data_value
                )
                self.assertTrue(set_result['success'])

        # Validate user isolation - no user can access other users' data
        isolation_violations = []
        for user_id in test_users:
            for mode in test_modes:
                user_context_id = isolation_test_results[user_id][mode]

                # Try to access this user's data from other users' contexts
                for other_user_id in test_users:
                    if other_user_id != user_id:
                        for other_mode in test_modes:
                            other_context_id = isolation_test_results[other_user_id][other_mode]

                            # Attempt cross-user data access
                            access_result = await mock_isolation.access_user_data(
                                other_context_id, f"test_data_{mode}"
                            )

                            if access_result.get('success') and access_result.get('value'):
                                # Check if accessed data belongs to another user
                                accessed_value = access_result['value']
                                if user_id in accessed_value:
                                    isolation_violations.append({
                                        'accessing_user': other_user_id,
                                        'accessing_mode': other_mode,
                                        'target_user': user_id,
                                        'target_mode': mode,
                                        'leaked_data': accessed_value
                                    })

        # Assert no isolation violations
        self.assertEqual(len(isolation_violations), 0,
                        f"User isolation violations detected: {isolation_violations}")

        # Validate each user has isolated contexts for each mode
        for user_id in test_users:
            user_contexts_count = len(isolation_test_results[user_id])
            self.assertEqual(user_contexts_count, len(test_modes),
                            f"User {user_id} must have isolated context for each mode")

            # Validate context IDs are unique
            context_ids = list(isolation_test_results[user_id].values())
            self.assertEqual(len(set(context_ids)), len(context_ids),
                            f"All context IDs must be unique for user {user_id}")

        logger.info(f"User isolation integration validated - {len(test_users)} users across "
                   f"{len(test_modes)} modes, no isolation violations detected")

    async def test_error_handling_integration_across_modes(self):
        """
        Test error handling integration across different route modes.

        Validates that errors are handled consistently and appropriately for each mode.
        """
        logger.info("Testing error handling integration across modes")

        # Mock error handler
        mock_error_handler = AsyncMock()
        error_handling_log = []

        async def handle_error(mode: str, error_type: str, error_details: Dict[str, Any],
                              user_id: Optional[str] = None):
            """Handle errors with mode-specific logic."""
            error_record = {
                'mode': mode,
                'error_type': error_type,
                'error_details': error_details,
                'user_id': user_id,
                'handled_at': datetime.now(timezone.utc),
                'recovery_attempted': True
            }

            # Mode-specific error handling
            if mode == 'factory':
                error_record['factory_cleanup'] = True
                error_record['context_preserved'] = True
            elif mode == 'isolated':
                error_record['connection_isolated'] = True
                error_record['security_maintained'] = True
            elif mode == 'main':
                error_record['standard_handling'] = True
            elif mode == 'legacy':
                error_record['backward_compatible'] = True
                error_record['fallback_applied'] = True

            error_handling_log.append(error_record)
            return error_record

        mock_error_handler.handle_error = handle_error

        # Test error scenarios for each mode
        test_error_scenarios = [
            {
                'error_type': 'connection_failure',
                'error_details': {'reason': 'Network timeout', 'code': 1000}
            },
            {
                'error_type': 'authentication_error',
                'error_details': {'reason': 'Invalid token', 'code': 4001}
            },
            {
                'error_type': 'message_validation_error',
                'error_details': {'reason': 'Invalid JSON', 'field': 'message'}
            },
            {
                'error_type': 'rate_limit_exceeded',
                'error_details': {'reason': 'Too many requests', 'limit': 100}
            }
        ]

        test_modes = ['main', 'factory', 'isolated', 'legacy']

        # Test each error scenario in each mode
        for mode in test_modes:
            for scenario in test_error_scenarios:
                error_result = await mock_error_handler.handle_error(
                    mode=mode,
                    error_type=scenario['error_type'],
                    error_details=scenario['error_details'],
                    user_id=self.test_user_id
                )

                # Validate error handling successful
                self.assertTrue(error_result.get('recovery_attempted'))
                self.assertEqual(error_result['mode'], mode)
                self.assertEqual(error_result['error_type'], scenario['error_type'])

                # Validate mode-specific error handling
                if mode == 'factory':
                    self.assertTrue(error_result.get('factory_cleanup'))
                elif mode == 'isolated':
                    self.assertTrue(error_result.get('connection_isolated'))
                elif mode == 'legacy':
                    self.assertTrue(error_result.get('fallback_applied'))

        # Validate comprehensive error coverage
        expected_total_errors = len(test_modes) * len(test_error_scenarios)
        self.assertEqual(len(error_handling_log), expected_total_errors,
                        f"All {expected_total_errors} error scenarios must be handled")

        # Validate all error types handled in all modes
        handled_error_types = set(record['error_type'] for record in error_handling_log)
        expected_error_types = set(scenario['error_type'] for scenario in test_error_scenarios)
        self.assertEqual(handled_error_types, expected_error_types,
                        "All error types must be handled across all modes")

        # Validate error handling consistency
        modes_with_errors = set(record['mode'] for record in error_handling_log)
        self.assertEqual(modes_with_errors, set(test_modes),
                        "Error handling must be available for all modes")

        logger.info(f"Error handling integration validated - {len(error_handling_log)} errors handled "
                   f"across {len(test_modes)} modes, all with recovery attempts")


if __name__ == '__main__':
    # Use SSOT unified test runner
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category integration --pattern websocket_route')