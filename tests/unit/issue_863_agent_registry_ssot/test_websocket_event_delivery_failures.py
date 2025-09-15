"""
Test AgentRegistry WebSocket Event Delivery Failures (Issue #914)

This test module demonstrates critical WebSocket event delivery failures caused
by AgentRegistry SSOT violations that prevent the 5 mission-critical agent events
from being delivered to users, blocking the Golden Path chat functionality.

Business Value: Protects $500K+ ARR by identifying registry conflicts that prevent
users from receiving real-time agent progress updates (agent_started, agent_thinking,
tool_executing, tool_completed, agent_completed) that are essential for chat UX.

Test Category: Unit (no Docker required)
Purpose: Failing tests to demonstrate WebSocket event delivery problems
"""
import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, AsyncMock, MagicMock, call
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class TestAgentRegistryWebSocketEventDeliveryFailures(SSotAsyncTestCase):
    """
    Test WebSocket event delivery failures in AgentRegistry implementations.
    
    These tests are DESIGNED TO FAIL initially to demonstrate how registry SSOT
    violations prevent the 5 critical WebSocket events from being delivered,
    blocking Golden Path chat functionality that users depend on.
    """

    def setup_method(self, method):
        """Setup test environment for WebSocket event testing."""
        self.basic_registry_module = 'netra_backend.app.agents.registry'
        self.advanced_registry_module = 'netra_backend.app.agents.supervisor.agent_registry'
        self.critical_websocket_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        self.test_user = {'user_id': f'test_user_{uuid.uuid4()}', 'session_id': f'session_{uuid.uuid4()}', 'connection_id': f'conn_{uuid.uuid4()}'}

    def test_missing_websocket_manager_integration_failure(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate WebSocket manager integration failures.
        
        This test shows how basic registry fails to properly integrate with WebSocket
        managers, preventing any event delivery to users.
        """
        import importlib
        integration_failures = []
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            for registry_name, registry_class in [('basic', basic_registry_class), ('advanced', advanced_registry_class)]:
                registry_instance = registry_class()
                mock_websocket_manager = Mock()
                mock_websocket_manager.send_event = Mock()
                mock_websocket_manager.user_id = self.test_user['user_id']
                websocket_setup_success = False
                setup_error = None
                if hasattr(registry_instance, 'set_websocket_manager'):
                    method = getattr(registry_instance, 'set_websocket_manager')
                    try:
                        if asyncio.iscoroutinefunction(method):
                            try:
                                mock_user_context = Mock()
                                mock_user_context.user_id = self.test_user['user_id']
                                asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager, mock_user_context))
                                websocket_setup_success = True
                            except Exception as e:
                                try:
                                    asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager))
                                    websocket_setup_success = True
                                except Exception as e2:
                                    setup_error = f'Async setup failed both with and without user context: {e2}'
                        else:
                            method(mock_websocket_manager)
                            websocket_setup_success = True
                    except Exception as e:
                        setup_error = str(e)
                else:
                    setup_error = 'set_websocket_manager method not found'
                event_notification_success = False
                notification_error = None
                if websocket_setup_success:
                    if hasattr(registry_instance, '_notify_agent_event'):
                        try:
                            test_event = {'type': 'agent_started', 'user_id': self.test_user['user_id'], 'session_id': self.test_user['session_id'], 'timestamp': time.time()}
                            registry_instance._notify_agent_event(test_event)
                            event_notification_success = True
                            if hasattr(mock_websocket_manager, 'send_event'):
                                if mock_websocket_manager.send_event.called:
                                    logger.info(f'{registry_name} registry successfully sent event to WebSocket manager')
                                else:
                                    notification_error = "Event notification method exists but didn't call WebSocket manager"
                        except Exception as e:
                            notification_error = f'Event notification failed: {e}'
                    else:
                        notification_error = '_notify_agent_event method not found'
                integration_result = {'registry': registry_name, 'websocket_setup_success': websocket_setup_success, 'setup_error': setup_error, 'event_notification_success': event_notification_success, 'notification_error': notification_error}
                logger.error(f'{registry_name} registry WebSocket integration:')
                logger.error(f'  Setup success: {websocket_setup_success}')
                if setup_error:
                    logger.error(f'  Setup error: {setup_error}')
                logger.error(f'  Event notification success: {event_notification_success}')
                if notification_error:
                    logger.error(f'  Notification error: {notification_error}')
                if not websocket_setup_success or not event_notification_success:
                    integration_failures.append(integration_result)
            if integration_failures:
                failure_details = []
                for failure in integration_failures:
                    details = f"{failure['registry']}: "
                    if not failure['websocket_setup_success']:
                        details += f"setup failed ({failure['setup_error']})"
                    if not failure['event_notification_success']:
                        if not failure['websocket_setup_success']:
                            details += ', '
                        details += f"notification failed ({failure['notification_error']})"
                    failure_details.append(details)
                self.fail(f"CRITICAL WEBSOCKET INTEGRATION FAILURE: {len(integration_failures)} registry types cannot properly integrate with WebSocket managers. This prevents all 5 critical agent events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) from being delivered to users, completely blocking $500K+ ARR Golden Path chat functionality. Integration failures: {'; '.join(failure_details)}")
        except Exception as e:
            self.fail(f'Unexpected error during WebSocket integration testing: {e}')
        logger.info('WebSocket manager integration successful - event delivery capability confirmed')

    def test_critical_agent_events_missing_or_inconsistent(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate missing or inconsistent critical agent events.
        
        This test verifies that both registries can deliver all 5 critical WebSocket events
        required for Golden Path chat functionality.
        """
        import importlib
        event_delivery_failures = []
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            for registry_name, registry_class in [('basic', basic_registry_class), ('advanced', advanced_registry_class)]:
                registry_instance = registry_class()
                captured_events = []
                mock_websocket_manager = Mock()

                def capture_event(event_data):
                    captured_events.append({'type': event_data.get('type'), 'data': event_data, 'timestamp': time.time()})
                mock_websocket_manager.send_event = capture_event
                mock_websocket_manager.send_json = capture_event
                mock_websocket_manager.user_id = self.test_user['user_id']
                websocket_setup_success = False
                if hasattr(registry_instance, 'set_websocket_manager'):
                    method = getattr(registry_instance, 'set_websocket_manager')
                    try:
                        if asyncio.iscoroutinefunction(method):
                            try:
                                mock_user_context = Mock()
                                mock_user_context.user_id = self.test_user['user_id']
                                asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager, mock_user_context))
                            except:
                                asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager))
                        else:
                            method(mock_websocket_manager)
                        websocket_setup_success = True
                    except Exception as e:
                        logger.error(f'WebSocket setup failed for {registry_name}: {e}')
                if websocket_setup_success and hasattr(registry_instance, '_notify_agent_event'):
                    for event_type in self.critical_websocket_events:
                        try:
                            test_event = {'type': event_type, 'user_id': self.test_user['user_id'], 'session_id': self.test_user['session_id'], 'agent_id': 'test_agent', 'timestamp': time.time()}
                            if event_type == 'agent_started':
                                test_event['agent_type'] = 'triage'
                            elif event_type == 'agent_thinking':
                                test_event['reasoning'] = 'Analyzing user request...'
                            elif event_type == 'tool_executing':
                                test_event['tool_name'] = 'data_analyzer'
                            elif event_type == 'tool_completed':
                                test_event['tool_result'] = {'status': 'success'}
                            elif event_type == 'agent_completed':
                                test_event['result'] = {'response': 'Analysis complete'}
                            registry_instance._notify_agent_event(test_event)
                        except Exception as e:
                            logger.error(f'Failed to send {event_type} event in {registry_name}: {e}')
                captured_event_types = [event['type'] for event in captured_events]
                missing_events = [event_type for event_type in self.critical_websocket_events if event_type not in captured_event_types]
                logger.error(f'{registry_name} registry event delivery analysis:')
                logger.error(f'  Expected events: {self.critical_websocket_events}')
                logger.error(f'  Captured events: {captured_event_types}')
                logger.error(f'  Missing events: {missing_events}')
                logger.error(f'  WebSocket setup success: {websocket_setup_success}')
                if missing_events or not websocket_setup_success:
                    event_delivery_failures.append({'registry': registry_name, 'missing_events': missing_events, 'captured_events': len(captured_events), 'websocket_setup_success': websocket_setup_success, 'total_expected': len(self.critical_websocket_events)})
            if event_delivery_failures:
                failure_summary = []
                for failure in event_delivery_failures:
                    if failure['missing_events']:
                        summary = f"{failure['registry']}: missing {len(failure['missing_events'])}/{failure['total_expected']} events {failure['missing_events']}"
                    else:
                        summary = f"{failure['registry']}: WebSocket setup failed, no events delivered"
                    failure_summary.append(summary)
                self.fail(f"CRITICAL AGENT EVENT DELIVERY FAILURE: {len(event_delivery_failures)} registry types cannot deliver all 5 critical WebSocket events required for Golden Path chat functionality. Users will not see real-time agent progress, causing poor UX and lost confidence in the $500K+ ARR chat system. Missing events block essential user feedback. Event delivery failures: {'; '.join(failure_summary)}")
        except Exception as e:
            self.fail(f'Unexpected error during critical event testing: {e}')
        logger.info('All 5 critical WebSocket events delivered successfully - Golden Path functionality enabled')

    def test_event_ordering_and_timing_consistency(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate event ordering and timing inconsistencies.
        
        This test shows how different registry implementations deliver events in
        different orders or with timing issues, confusing users about agent progress.
        """
        import importlib
        timing_inconsistencies = []
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            registry_event_sequences = {}
            for registry_name, registry_class in [('basic', basic_registry_class), ('advanced', advanced_registry_class)]:
                registry_instance = registry_class()
                event_sequence = []

                def capture_event_with_timing(event_data):
                    event_sequence.append({'type': event_data.get('type'), 'timestamp': time.time(), 'data': event_data})
                mock_websocket_manager = Mock()
                mock_websocket_manager.send_event = capture_event_with_timing
                mock_websocket_manager.user_id = self.test_user['user_id']
                websocket_setup_success = False
                if hasattr(registry_instance, 'set_websocket_manager'):
                    method = getattr(registry_instance, 'set_websocket_manager')
                    try:
                        if asyncio.iscoroutinefunction(method):
                            try:
                                mock_user_context = Mock()
                                mock_user_context.user_id = self.test_user['user_id']
                                asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager, mock_user_context))
                            except:
                                asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager))
                        else:
                            method(mock_websocket_manager)
                        websocket_setup_success = True
                    except Exception as e:
                        logger.error(f'WebSocket setup failed for {registry_name}: {e}')
                if websocket_setup_success and hasattr(registry_instance, '_notify_agent_event'):
                    expected_sequence = [('agent_started', 'Agent began processing user request'), ('agent_thinking', 'Analyzing requirements and planning approach'), ('tool_executing', 'Running data analysis tool'), ('tool_completed', 'Data analysis complete'), ('agent_completed', 'Generated response for user')]
                    for i, (event_type, description) in enumerate(expected_sequence):
                        try:
                            test_event = {'type': event_type, 'user_id': self.test_user['user_id'], 'description': description, 'sequence_number': i, 'timestamp': time.time()}
                            registry_instance._notify_agent_event(test_event)
                            time.sleep(0.01)
                        except Exception as e:
                            logger.error(f'Failed to send {event_type} in {registry_name}: {e}')
                registry_event_sequences[registry_name] = {'events': event_sequence, 'websocket_setup_success': websocket_setup_success}
                if event_sequence:
                    event_types = [event['type'] for event in event_sequence]
                    timestamps = [event['timestamp'] for event in event_sequence]
                    logger.error(f'{registry_name} registry event sequence:')
                    logger.error(f'  Event types: {event_types}')
                    logger.error(f'  Time span: {timestamps[-1] - timestamps[0]:.3f}s')
                    expected_order = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                    if event_types != expected_order:
                        timing_inconsistencies.append({'registry': registry_name, 'issue_type': 'incorrect_order', 'expected': expected_order, 'actual': event_types})
                    for i in range(1, len(timestamps)):
                        time_gap = timestamps[i] - timestamps[i - 1]
                        if time_gap < 0:
                            timing_inconsistencies.append({'registry': registry_name, 'issue_type': 'chronological_disorder', 'events': f'{event_types[i - 1]} -> {event_types[i]}', 'time_gap': time_gap})
                        elif time_gap > 1.0:
                            timing_inconsistencies.append({'registry': registry_name, 'issue_type': 'excessive_delay', 'events': f'{event_types[i - 1]} -> {event_types[i]}', 'time_gap': time_gap})
            if len(registry_event_sequences) > 1:
                registry_names = list(registry_event_sequences.keys())
                for i in range(len(registry_names)):
                    for j in range(i + 1, len(registry_names)):
                        reg1, reg2 = (registry_names[i], registry_names[j])
                        seq1 = [e['type'] for e in registry_event_sequences[reg1]['events']]
                        seq2 = [e['type'] for e in registry_event_sequences[reg2]['events']]
                        if seq1 != seq2:
                            timing_inconsistencies.append({'registry': f'{reg1}_vs_{reg2}', 'issue_type': 'registry_sequence_mismatch', 'sequence1': seq1, 'sequence2': seq2})
            if timing_inconsistencies:
                inconsistency_summary = []
                for inconsistency in timing_inconsistencies:
                    if inconsistency['issue_type'] == 'incorrect_order':
                        summary = f"{inconsistency['registry']}: wrong order {inconsistency['actual']} != {inconsistency['expected']}"
                    elif inconsistency['issue_type'] == 'chronological_disorder':
                        summary = f"{inconsistency['registry']}: time disorder in {inconsistency['events']} ({inconsistency['time_gap']:.3f}s)"
                    elif inconsistency['issue_type'] == 'excessive_delay':
                        summary = f"{inconsistency['registry']}: excessive delay in {inconsistency['events']} ({inconsistency['time_gap']:.3f}s)"
                    elif inconsistency['issue_type'] == 'registry_sequence_mismatch':
                        summary = f"{inconsistency['registry']}: sequences differ {inconsistency['sequence1']} vs {inconsistency['sequence2']}"
                    else:
                        summary = f"{inconsistency['registry']}: {inconsistency['issue_type']}"
                    inconsistency_summary.append(summary)
                self.fail(f"CRITICAL EVENT TIMING INCONSISTENCY: {len(timing_inconsistencies)} timing issues detected. Different registry implementations deliver events in inconsistent order or timing, confusing users about agent progress and degrading the Golden Path chat experience. Consistent event delivery is essential for $500K+ ARR chat functionality. Timing issues: {'; '.join(inconsistency_summary)}")
        except Exception as e:
            self.fail(f'Unexpected error during event timing testing: {e}')
        logger.info('Event timing and ordering consistent across registries - reliable Golden Path UX enabled')

    def test_websocket_connection_state_management_failures(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate WebSocket connection state management failures.
        
        This test shows how registries handle WebSocket connection state inconsistently,
        causing events to be lost when connections drop or reconnect.
        """
        import importlib
        connection_state_failures = []
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            for registry_name, registry_class in [('basic', basic_registry_class), ('advanced', advanced_registry_class)]:
                registry_instance = registry_class()
                connection_drop_events = []

                def simulate_connection_drop(event_data):
                    connection_drop_events.append(event_data)
                    if len(connection_drop_events) == 1:
                        raise ConnectionError('WebSocket connection dropped')
                mock_websocket_manager = Mock()
                mock_websocket_manager.send_event = simulate_connection_drop
                mock_websocket_manager.user_id = self.test_user['user_id']
                websocket_setup_success = False
                if hasattr(registry_instance, 'set_websocket_manager'):
                    method = getattr(registry_instance, 'set_websocket_manager')
                    try:
                        if asyncio.iscoroutinefunction(method):
                            try:
                                mock_user_context = Mock()
                                mock_user_context.user_id = self.test_user['user_id']
                                asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager, mock_user_context))
                            except:
                                asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager))
                        else:
                            method(mock_websocket_manager)
                        websocket_setup_success = True
                    except Exception as e:
                        logger.error(f'WebSocket setup failed for {registry_name}: {e}')
                connection_drop_handled = True
                if websocket_setup_success and hasattr(registry_instance, '_notify_agent_event'):
                    try:
                        registry_instance._notify_agent_event({'type': 'agent_started', 'user_id': self.test_user['user_id']})
                        registry_instance._notify_agent_event({'type': 'agent_thinking', 'user_id': self.test_user['user_id']})
                    except Exception as e:
                        if 'connection dropped' not in str(e).lower():
                            connection_drop_handled = False
                            logger.error(f'{registry_name} registry failed to handle connection drop: {e}')
                reconnection_events = []

                def capture_reconnection_events(event_data):
                    reconnection_events.append(event_data)
                new_websocket_manager = Mock()
                new_websocket_manager.send_event = capture_reconnection_events
                new_websocket_manager.user_id = self.test_user['user_id']
                reconnection_success = False
                if hasattr(registry_instance, 'set_websocket_manager'):
                    method = getattr(registry_instance, 'set_websocket_manager')
                    try:
                        if asyncio.iscoroutinefunction(method):
                            try:
                                mock_user_context = Mock()
                                mock_user_context.user_id = self.test_user['user_id']
                                asyncio.get_event_loop().run_until_complete(method(new_websocket_manager, mock_user_context))
                            except:
                                asyncio.get_event_loop().run_until_complete(method(new_websocket_manager))
                        else:
                            method(new_websocket_manager)
                        registry_instance._notify_agent_event({'type': 'agent_completed', 'user_id': self.test_user['user_id']})
                        reconnection_success = len(reconnection_events) > 0
                    except Exception as e:
                        logger.error(f'Reconnection failed for {registry_name}: {e}')
                state_management_issues = []
                if not connection_drop_handled:
                    state_management_issues.append('connection_drop_not_handled')
                if not reconnection_success:
                    state_management_issues.append('reconnection_failed')
                has_connection_state_methods = any((hasattr(registry_instance, method) for method in ['is_websocket_connected', 'get_connection_state', '_websocket_connection_status']))
                if not has_connection_state_methods:
                    state_management_issues.append('no_connection_state_visibility')
                logger.error(f'{registry_name} registry connection state analysis:')
                logger.error(f'  Connection drop handled: {connection_drop_handled}')
                logger.error(f'  Reconnection successful: {reconnection_success}')
                logger.error(f'  Has state visibility: {has_connection_state_methods}')
                logger.error(f'  Issues: {state_management_issues}')
                if state_management_issues:
                    connection_state_failures.append({'registry': registry_name, 'issues': state_management_issues, 'events_before_drop': len(connection_drop_events), 'events_after_reconnect': len(reconnection_events)})
            if connection_state_failures:
                failure_summary = []
                for failure in connection_state_failures:
                    issue_desc = ', '.join(failure['issues'])
                    summary = f"{failure['registry']}: {issue_desc} (events: {failure['events_before_drop']} before drop, {failure['events_after_reconnect']} after reconnect)"
                    failure_summary.append(summary)
                self.fail(f"CRITICAL WEBSOCKET CONNECTION STATE FAILURE: {len(connection_state_failures)} registry types cannot properly manage WebSocket connection state. This causes critical agent events to be lost when connections drop or reconnect, leaving users without feedback about agent progress. Reliable connection state management is essential for $500K+ ARR Golden Path chat functionality. Connection failures: {'; '.join(failure_summary)}")
        except Exception as e:
            self.fail(f'Unexpected error during connection state testing: {e}')
        logger.info('WebSocket connection state properly managed - reliable event delivery ensured')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')