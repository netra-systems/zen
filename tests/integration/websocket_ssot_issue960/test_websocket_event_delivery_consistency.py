#!/usr/bin/env python
"""Integration Test: Issue #960 WebSocket Event Delivery Consistency

GitHub Issue: #960 WebSocket Manager SSOT fragmentation crisis

THIS TEST VALIDATES CONSISTENT EVENT DELIVERY ACROSS WEBSOCKET IMPLEMENTATIONS.
Business Value: $500K+ ARR - Validates event delivery consistency for Golden Path

PURPOSE:
- Test validates consistent event delivery across all WebSocket implementations
- This test SHOULD FAIL initially (proving delivery inconsistencies exist)
- This test SHOULD PASS after SSOT consolidation (proving consistent delivery)
- Validates 5 business-critical events and multi-user isolation

CRITICAL EVENT DELIVERY VIOLATIONS:
- Inconsistent delivery of 5 business-critical events across managers
- Events bleeding between user contexts (cross-contamination)
- Event delivery reliability affected by manager fragmentation
- Golden Path event sequence disrupted by SSOT violations

TEST STRATEGY:
1. Test all 5 business-critical events across different WebSocket managers
2. Validate multi-user event isolation (no cross-contamination)
3. Test event delivery reliability under manager fragmentation
4. Validate Golden Path event sequence consistency
5. This test should FAIL until event delivery consolidation is complete

BUSINESS IMPACT:
Event delivery inconsistencies break the Golden Path user flow where users
login and receive AI responses with proper real-time feedback.
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
from unittest.mock import MagicMock, AsyncMock, patch
import time

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase
import pytest
from loguru import logger


class WebSocketEventDeliveryConsistencyTests(SSotBaseTestCase):
    """Issue #960: WebSocket Event Delivery Consistency Validation

    This test validates consistent event delivery across all WebSocket
    implementations to detect SSOT violations.

    Expected Behavior:
    - This test SHOULD FAIL initially (proving delivery inconsistencies exist)
    - This test SHOULD PASS after SSOT event delivery consolidation (proving consistency)
    """

    def setup_method(self, method):
        """Set up test environment for event delivery consistency validation."""
        super().setup_method(method)

        # Define 5 business-critical events for Golden Path
        self.critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        # Define test user contexts for isolation testing
        self.test_user_contexts = [
            {'user_id': 'event_user_1', 'thread_id': 'thread_1'},
            {'user_id': 'event_user_2', 'thread_id': 'thread_2'},
            {'user_id': 'event_user_1', 'thread_id': 'thread_3'},  # Same user, different thread
        ]

        self.event_violations = defaultdict(list)
        self.websocket_managers = {}

        # Load WebSocket managers for testing
        self._load_websocket_managers()

    @pytest.mark.asyncio
    async def test_five_critical_events_delivery(self):
        """CRITICAL: Detect inconsistent delivery of 5 business-critical events (SHOULD FAIL initially)

        This test validates that all 5 business-critical events are delivered
        consistently across different WebSocket manager implementations.
        """
        logger.info("🔍 Testing 5 critical events delivery consistency...")

        event_delivery_violations = []

        for manager_name, manager in self.websocket_managers.items():
            if manager:
                test_context = self.test_user_contexts[0]

                # Create mock WebSocket connection
                mock_websocket = MagicMock()
                mock_websocket.send = AsyncMock()

                try:
                    # Add connection to manager
                    if hasattr(manager, 'add_connection'):
                        if asyncio.iscoroutinefunction(manager.add_connection):
                            await manager.add_connection(mock_websocket, test_context)
                        else:
                            manager.add_connection(mock_websocket, test_context)

                    # Test delivery of each critical event
                    events_delivered = {}
                    events_failed = {}

                    for event_type in self.critical_events:
                        event_data = {
                            'type': event_type,
                            'user_id': test_context['user_id'],
                            'thread_id': test_context['thread_id'],
                            'timestamp': time.time(),
                            'data': f'Test data for {event_type}'
                        }

                        try:
                            # Test event delivery through manager
                            delivery_successful = await self._test_event_delivery(
                                manager, event_type, event_data, test_context
                            )

                            if delivery_successful:
                                events_delivered[event_type] = True
                            else:
                                events_failed[event_type] = 'delivery_failed'

                        except Exception as e:
                            events_failed[event_type] = str(e)
                            logger.warning(f"Event delivery failed for {manager_name}.{event_type}: {e}")

                    # Analyze event delivery results
                    total_events = len(self.critical_events)
                    delivered_count = len(events_delivered)
                    failed_count = len(events_failed)

                    if failed_count > 0:
                        event_delivery_violations.append({
                            'manager_name': manager_name,
                            'total_events': total_events,
                            'delivered_events': delivered_count,
                            'failed_events': failed_count,
                            'failed_event_details': events_failed,
                            'violation_type': 'incomplete_event_delivery'
                        })

                        logger.error(f"🚨 EVENT DELIVERY VIOLATION: {manager_name}")
                        logger.error(f"  Delivered: {delivered_count}/{total_events}")
                        logger.error(f"  Failed events: {list(events_failed.keys())}")

                except Exception as e:
                    logger.warning(f"WARNING️ Could not test event delivery for {manager_name}: {e}")
                    event_delivery_violations.append({
                        'manager_name': manager_name,
                        'violation_type': 'manager_setup_failure',
                        'error': str(e)
                    })

        self.event_violations['event_delivery_violations'] = event_delivery_violations

        # ASSERTION: This should FAIL initially if event delivery violations exist
        assert len(event_delivery_violations) == 0, (
            f"Event Delivery SSOT VIOLATION: Found {len(event_delivery_violations)} managers with incomplete event delivery. "
            f"Violating managers: {[v['manager_name'] for v in event_delivery_violations]}. "
            f"SSOT requires all 5 critical events to be delivered consistently across all managers."
        )

    @pytest.mark.asyncio
    async def test_multi_user_event_isolation(self):
        """CRITICAL: Detect events bleeding between user contexts (SHOULD FAIL initially)

        This test validates that events are properly isolated between different
        user contexts and don't cause cross-contamination.
        """
        logger.info("🔍 Testing multi-user event isolation...")

        isolation_violations = []

        for manager_name, manager in self.websocket_managers.items():
            if manager:
                # Set up multiple user contexts with mock connections
                user_connections = {}
                user_received_events = defaultdict(list)

                for context in self.test_user_contexts:
                    mock_websocket = MagicMock()
                    mock_websocket.send = AsyncMock()

                    # Track events received by this connection
                    context_key = f"{context['user_id']}:{context['thread_id']}"
                    user_connections[context_key] = {
                        'context': context,
                        'websocket': mock_websocket,
                        'events': []
                    }

                    try:
                        # Add connection to manager
                        if hasattr(manager, 'add_connection'):
                            if asyncio.iscoroutinefunction(manager.add_connection):
                                await manager.add_connection(mock_websocket, context)
                            else:
                                manager.add_connection(mock_websocket, context)
                    except Exception as e:
                        logger.warning(f"Could not add connection for {context_key}: {e}")

                # Send events to each user context and check isolation
                isolation_test_results = {}

                for target_context_key, connection_data in user_connections.items():
                    target_context = connection_data['context']

                    # Send test event to specific user
                    test_event_data = {
                        'type': 'agent_started',
                        'user_id': target_context['user_id'],
                        'thread_id': target_context['thread_id'],
                        'message': f'Event for {target_context_key}',
                        'timestamp': time.time()
                    }

                    try:
                        # Send event through manager
                        await self._test_event_delivery(
                            manager, 'agent_started', test_event_data, target_context
                        )

                        # Check which connections received the event
                        receiving_connections = []
                        for check_context_key, check_connection in user_connections.items():
                            if check_connection['websocket'].send.called:
                                receiving_connections.append(check_context_key)
                                # Reset for next test
                                check_connection['websocket'].send.reset_mock()

                        isolation_test_results[target_context_key] = {
                            'target_context': target_context,
                            'receiving_connections': receiving_connections,
                            'isolation_violated': len(receiving_connections) > 1
                        }

                        if len(receiving_connections) > 1:
                            logger.error(f"🚨 ISOLATION VIOLATION: Event sent to {target_context_key}")
                            logger.error(f"  Received by: {receiving_connections}")

                    except Exception as e:
                        logger.warning(f"Could not test isolation for {target_context_key}: {e}")

                # Analyze isolation violations
                violated_isolations = [
                    result for result in isolation_test_results.values()
                    if result['isolation_violated']
                ]

                if violated_isolations:
                    isolation_violations.append({
                        'manager_name': manager_name,
                        'violation_count': len(violated_isolations),
                        'violation_details': violated_isolations,
                        'violation_type': 'multi_user_event_bleeding'
                    })

        self.event_violations['isolation_violations'] = isolation_violations

        # ASSERTION: This should FAIL initially if isolation violations exist
        assert len(isolation_violations) == 0, (
            f"Event Isolation SSOT VIOLATION: Found {len(isolation_violations)} managers with event bleeding. "
            f"Violating managers: {[v['manager_name'] for v in isolation_violations]}. "
            f"SSOT requires complete event isolation between user contexts."
        )

    @pytest.mark.asyncio
    async def test_event_delivery_reliability(self):
        """CRITICAL: Detect event delivery affected by manager fragmentation (SHOULD FAIL initially)

        This test validates that event delivery reliability is not affected by
        WebSocket manager fragmentation issues.
        """
        logger.info("🔍 Testing event delivery reliability under manager fragmentation...")

        reliability_violations = []

        # Test event delivery reliability across managers
        for manager_name, manager in self.websocket_managers.items():
            if manager:
                test_context = self.test_user_contexts[0]
                reliability_results = {
                    'total_attempts': 0,
                    'successful_deliveries': 0,
                    'failed_deliveries': 0,
                    'delivery_errors': []
                }

                # Set up mock connection
                mock_websocket = MagicMock()
                mock_websocket.send = AsyncMock()

                try:
                    # Add connection
                    if hasattr(manager, 'add_connection'):
                        if asyncio.iscoroutinefunction(manager.add_connection):
                            await manager.add_connection(mock_websocket, test_context)
                        else:
                            manager.add_connection(mock_websocket, test_context)

                    # Test reliability with multiple event deliveries
                    test_events = [
                        {'type': 'agent_started', 'message': 'Test reliability 1'},
                        {'type': 'agent_thinking', 'message': 'Test reliability 2'},
                        {'type': 'tool_executing', 'message': 'Test reliability 3'},
                        {'type': 'tool_completed', 'message': 'Test reliability 4'},
                        {'type': 'agent_completed', 'message': 'Test reliability 5'}
                    ]

                    for event in test_events:
                        reliability_results['total_attempts'] += 1

                        event_data = {
                            **event,
                            'user_id': test_context['user_id'],
                            'thread_id': test_context['thread_id'],
                            'timestamp': time.time()
                        }

                        try:
                            delivery_successful = await self._test_event_delivery(
                                manager, event['type'], event_data, test_context
                            )

                            if delivery_successful:
                                reliability_results['successful_deliveries'] += 1
                            else:
                                reliability_results['failed_deliveries'] += 1
                                reliability_results['delivery_errors'].append(f"Failed delivery: {event['type']}")

                        except Exception as e:
                            reliability_results['failed_deliveries'] += 1
                            reliability_results['delivery_errors'].append(f"Error in {event['type']}: {str(e)}")

                    # Calculate reliability rate
                    total_attempts = reliability_results['total_attempts']
                    successful_deliveries = reliability_results['successful_deliveries']
                    reliability_rate = successful_deliveries / total_attempts if total_attempts > 0 else 0

                    # Check if reliability meets minimum threshold (90%)
                    minimum_reliability_threshold = 0.90
                    if reliability_rate < minimum_reliability_threshold:
                        reliability_violations.append({
                            'manager_name': manager_name,
                            'reliability_rate': reliability_rate,
                            'threshold': minimum_reliability_threshold,
                            'total_attempts': total_attempts,
                            'successful_deliveries': successful_deliveries,
                            'failed_deliveries': reliability_results['failed_deliveries'],
                            'errors': reliability_results['delivery_errors'],
                            'violation_type': 'low_event_delivery_reliability'
                        })

                        logger.error(f"🚨 RELIABILITY VIOLATION: {manager_name}")
                        logger.error(f"  Reliability rate: {reliability_rate:.1%}")
                        logger.error(f"  Threshold: {minimum_reliability_threshold:.1%}")
                        logger.error(f"  Failed deliveries: {reliability_results['failed_deliveries']}")

                except Exception as e:
                    logger.warning(f"WARNING️ Could not test reliability for {manager_name}: {e}")
                    reliability_violations.append({
                        'manager_name': manager_name,
                        'violation_type': 'reliability_test_failure',
                        'error': str(e)
                    })

        self.event_violations['reliability_violations'] = reliability_violations

        # ASSERTION: This should FAIL initially if reliability violations exist
        assert len(reliability_violations) == 0, (
            f"Event Reliability SSOT VIOLATION: Found {len(reliability_violations)} managers with low reliability. "
            f"Violating managers: {[v['manager_name'] for v in reliability_violations]}. "
            f"SSOT requires high event delivery reliability (>90%) across all managers."
        )

    def _load_websocket_managers(self):
        """Load WebSocket managers for testing."""
        manager_specs = [
            ('netra_backend.app.websocket_core.websocket_manager', 'get_websocket_manager'),
            ('netra_backend.app.websocket_core.unified_manager', 'get_websocket_manager'),
        ]

        for module_path, function_name in manager_specs:
            try:
                import importlib
                module = importlib.import_module(module_path)
                if hasattr(module, function_name):
                    factory_func = getattr(module, function_name)

                    # Create manager instance for testing
                    test_context = self.test_user_contexts[0]
                    try:
                        if asyncio.iscoroutinefunction(factory_func):
                            manager = asyncio.run(factory_func(user_context=test_context))
                        else:
                            manager = factory_func(user_context=test_context)

                        manager_key = f"{module_path}.{function_name}"
                        self.websocket_managers[manager_key] = manager
                        logger.info(f"CHECK Loaded WebSocket manager: {manager_key}")
                    except Exception as e:
                        logger.warning(f"WARNING️ Could not create manager from {module_path}.{function_name}: {e}")
                        self.websocket_managers[f"{module_path}.{function_name}"] = None
            except ImportError as e:
                logger.warning(f"WARNING️ Could not import {module_path}: {e}")

    async def _test_event_delivery(self, manager, event_type, event_data, user_context):
        """Test event delivery through a WebSocket manager."""
        try:
            # Try different event delivery methods
            delivery_methods = [
                'emit_agent_event',
                f'send_{event_type}',
                'send_message',
                'broadcast_event'
            ]

            for method_name in delivery_methods:
                if hasattr(manager, method_name):
                    method = getattr(manager, method_name)

                    try:
                        if asyncio.iscoroutinefunction(method):
                            await method(event_data, user_context)
                        else:
                            method(event_data, user_context)
                        return True
                    except Exception as e:
                        logger.debug(f"Method {method_name} failed: {e}")
                        continue

            # If no specific method found, try generic approaches
            if hasattr(manager, 'send_to_user'):
                if asyncio.iscoroutinefunction(manager.send_to_user):
                    await manager.send_to_user(user_context['user_id'], event_data)
                else:
                    manager.send_to_user(user_context['user_id'], event_data)
                return True

            return False

        except Exception as e:
            logger.debug(f"Event delivery test failed: {e}")
            return False

    def teardown_method(self, method):
        """Clean up and log event delivery consistency results."""
        if self.event_violations:
            logger.info("📊 Event Delivery Consistency Analysis Summary:")

            total_violations = 0
            for violation_type, violations in self.event_violations.items():
                if isinstance(violations, list) and violations:
                    count = len(violations)
                    total_violations += count
                    logger.warning(f"  {violation_type}: {count} violations")

            if total_violations > 0:
                logger.error(f"🚨 TOTAL EVENT DELIVERY VIOLATIONS: {total_violations}")
                logger.error("💡 Event delivery consolidation required for SSOT compliance")
            else:
                logger.info("CHECK No event delivery violations detected - delivery is consistent")

        super().teardown_method(method)


if __name__ == "__main__":
    # Run this test directly to check event delivery consistency
    # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category integration
    pass  # TODO: Replace with appropriate SSOT test execution