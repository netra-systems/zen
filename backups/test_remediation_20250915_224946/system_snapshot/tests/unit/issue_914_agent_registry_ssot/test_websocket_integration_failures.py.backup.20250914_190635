"""
WebSocket Integration Failure Tests for Issue #914 AgentRegistry SSOT Consolidation

CRITICAL P0 TESTS: These tests are DESIGNED TO FAIL initially to prove WebSocket
integration failures caused by registry SSOT violations that block Golden Path.

Business Value: $500K+ ARR Golden Path protection - ensures WebSocket bridge
integration works reliably for real-time agent progress updates.

Test Focus:
- WebSocket bridge incompatibility with basic registry
- Missing WebSocket events blocking Golden Path
- Chat functionality degradation from registry conflicts
- Real-time user experience failures

Created: 2025-01-14 - Issue #914 Test Creation Plan
Priority: CRITICAL P0 - Must prove WebSocket integration failures blocking Golden Path
"""

import pytest
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Callable
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# SSOT Base Test Case - Required for all tests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Environment access through SSOT pattern only
from shared.isolated_environment import IsolatedEnvironment

# Test imports - both registries to validate WebSocket integration
from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry


class TestAgentRegistryWebSocketIntegrationFailures(SSotAsyncTestCase):
    """
    CRITICAL P0 Tests: Prove WebSocket integration failures block Golden Path
    
    These tests are DESIGNED TO FAIL initially to demonstrate WebSocket bridge
    incompatibilities that prevent real-time agent progress updates.
    """
    
    async def async_setup_method(self, method=None):
        """Set up test environment with SSOT patterns"""
        await super().async_setup_method(method)
        self.env = IsolatedEnvironment()
        
        # Initialize registries for WebSocket integration testing
        self.basic_registry = BasicRegistry()
        self.advanced_registry = AdvancedRegistry()
        
        # Mock WebSocket infrastructure components
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_bridge = AsyncMock()
        self.websocket_event_log = []
        self.websocket_integration_failures = []
        
        # Critical WebSocket events required for Golden Path
        self.critical_websocket_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        # Test user contexts for isolation validation
        self.test_users = [
            {"user_id": "websocket-user-1", "session_id": "ws-session-1"},
            {"user_id": "websocket-user-2", "session_id": "ws-session-2"}
        ]
        
        # Set up WebSocket event capture
        self._setup_websocket_event_capture()

    def _setup_websocket_event_capture(self):
        """Set up WebSocket event capture for testing"""
        
        async def capture_websocket_event(event_type: str, event_data: dict, user_id: str = None):
            """Capture WebSocket events for analysis"""
            captured_event = {
                'timestamp': time.time(),
                'event_type': event_type,
                'event_data': event_data,
                'user_id': user_id,
                'source': 'captured'
            }
            self.websocket_event_log.append(captured_event)
            self.logger.debug(f"Captured WebSocket event: {event_type} for user {user_id}")
        
        # Set up mocks with event capture
        self.mock_websocket_manager.emit_agent_event = AsyncMock(side_effect=capture_websocket_event)
        self.mock_websocket_bridge.send_agent_event = AsyncMock(side_effect=capture_websocket_event)

    async def test_websocket_bridge_incompatibility_with_basic_registry(self):
        """
        CRITICAL P0 TEST: Prove WebSocket bridge incompatible with basic registry
        
        DESIGNED TO FAIL: Basic registry lacks WebSocket bridge integration
        methods causing WebSocket bridge to fail connecting, blocking real-time updates.
        
        Business Impact: Golden Path degrades when basic registry is used,
        users don't see agent progress and chat experience becomes poor.
        """
        websocket_bridge_integration_failures = []
        registry_websocket_compatibility = {}
        
        # Test WebSocket bridge integration with both registries
        registries = {
            'basic': self.basic_registry,
            'advanced': self.advanced_registry
        }
        
        for registry_name, registry in registries.items():
            registry_websocket_compatibility[registry_name] = {
                'bridge_methods_available': [],
                'bridge_methods_missing': [],
                'integration_success': False,
                'integration_errors': [],
                'websocket_events_supported': [],
                'websocket_events_missing': []
            }
            
            # Check for WebSocket bridge integration methods
            websocket_bridge_methods = [
                'set_websocket_bridge',
                'get_websocket_bridge',
                'notify_websocket_event',
                '_websocket_bridge',
                'websocket_bridge'
            ]
            
            for method_name in websocket_bridge_methods:
                if hasattr(registry, method_name):
                    method = getattr(registry, method_name)
                    registry_websocket_compatibility[registry_name]['bridge_methods_available'].append({
                        'method_name': method_name,
                        'is_callable': callable(method),
                        'is_async': asyncio.iscoroutinefunction(method) if callable(method) else False
                    })
                    self.logger.info(f"{registry_name} registry has WebSocket bridge method: {method_name}")
                else:
                    registry_websocket_compatibility[registry_name]['bridge_methods_missing'].append(method_name)
                    self.logger.warning(f"{registry_name} registry MISSING WebSocket bridge method: {method_name}")
            
            # Test WebSocket bridge setup
            try:
                # Try setting WebSocket bridge
                if hasattr(registry, 'set_websocket_bridge'):
                    set_bridge_method = getattr(registry, 'set_websocket_bridge')
                    if asyncio.iscoroutinefunction(set_bridge_method):
                        await set_bridge_method(self.mock_websocket_bridge)
                    else:
                        set_bridge_method(self.mock_websocket_bridge)
                    
                    self.logger.info(f"{registry_name} registry WebSocket bridge setup succeeded")
                    registry_websocket_compatibility[registry_name]['integration_success'] = True
                    
                elif hasattr(registry, 'set_websocket_manager'):
                    # Fallback to WebSocket manager
                    set_manager_method = getattr(registry, 'set_websocket_manager')
                    if asyncio.iscoroutinefunction(set_manager_method):
                        await set_manager_method(self.mock_websocket_manager)
                    else:
                        set_manager_method(self.mock_websocket_manager)
                    
                    self.logger.info(f"{registry_name} registry WebSocket manager setup succeeded (fallback)")
                    registry_websocket_compatibility[registry_name]['integration_success'] = True
                    
                else:
                    registry_websocket_compatibility[registry_name]['integration_errors'].append(
                        'No WebSocket bridge or manager setup method available'
                    )
                    
            except Exception as e:
                registry_websocket_compatibility[registry_name]['integration_errors'].append(
                    f"WebSocket bridge setup failed: {e}"
                )
                self.logger.error(f"{registry_name} registry WebSocket bridge setup error: {e}")
            
            # Test WebSocket event support
            for event_type in self.critical_websocket_events:
                event_supported = False
                
                # Test different event notification methods
                event_methods_to_test = [
                    '_notify_agent_event',
                    'emit_agent_event', 
                    'notify_websocket_event',
                    'send_websocket_event'
                ]
                
                for method_name in event_methods_to_test:
                    if hasattr(registry, method_name):
                        try:
                            method = getattr(registry, method_name)
                            test_event_data = {
                                'event_type': event_type,
                                'test_data': f'test_{event_type}_{registry_name}',
                                'timestamp': time.time()
                            }
                            
                            if asyncio.iscoroutinefunction(method):
                                await method(event_type, test_event_data)
                            else:
                                method(event_type, test_event_data)
                            
                            event_supported = True
                            self.logger.debug(f"{registry_name} registry supports {event_type} via {method_name}")
                            break
                            
                        except Exception as e:
                            self.logger.warning(f"{registry_name} registry {method_name} failed for {event_type}: {e}")
                            continue
                
                if event_supported:
                    registry_websocket_compatibility[registry_name]['websocket_events_supported'].append(event_type)
                else:
                    registry_websocket_compatibility[registry_name]['websocket_events_missing'].append(event_type)
        
        # Analyze WebSocket bridge compatibility differences
        basic_compat = registry_websocket_compatibility['basic']
        advanced_compat = registry_websocket_compatibility['advanced']
        
        # Check for missing bridge methods in basic registry
        if basic_compat['bridge_methods_missing'] and not advanced_compat['bridge_methods_missing']:
            websocket_bridge_integration_failures.append({
                'failure_type': 'missing_bridge_methods',
                'registry': 'basic',
                'missing_methods': basic_compat['bridge_methods_missing'],
                'description': f"Basic registry missing WebSocket bridge methods: {basic_compat['bridge_methods_missing']}"
            })
        
        # Check for integration failures
        if not basic_compat['integration_success'] and advanced_compat['integration_success']:
            websocket_bridge_integration_failures.append({
                'failure_type': 'integration_failure',
                'registry': 'basic',
                'integration_errors': basic_compat['integration_errors'],
                'description': f"Basic registry WebSocket bridge integration failed: {basic_compat['integration_errors']}"
            })
        
        # Check for missing event support
        if basic_compat['websocket_events_missing'] and not advanced_compat['websocket_events_missing']:
            websocket_bridge_integration_failures.append({
                'failure_type': 'missing_event_support',
                'registry': 'basic',
                'missing_events': basic_compat['websocket_events_missing'],
                'description': f"Basic registry missing WebSocket event support: {basic_compat['websocket_events_missing']}"
            })
        
        # Test actual WebSocket bridge functionality
        for user_info in self.test_users:
            user_id = user_info['user_id']
            
            for registry_name, registry in registries.items():
                if registry_websocket_compatibility[registry_name]['integration_success']:
                    # Test sending critical WebSocket events
                    for event_type in self.critical_websocket_events:
                        try:
                            test_event_data = {
                                'user_id': user_id,
                                'event_type': event_type,
                                'test_payload': f'test_payload_{event_type}_{registry_name}_{user_id}'
                            }
                            
                            # Find and use event notification method
                            event_sent = False
                            for method_name in ['_notify_agent_event', 'emit_agent_event']:
                                if hasattr(registry, method_name):
                                    method = getattr(registry, method_name)
                                    if asyncio.iscoroutinefunction(method):
                                        await method(event_type, test_event_data)
                                    else:
                                        method(event_type, test_event_data)
                                    event_sent = True
                                    break
                            
                            if not event_sent:
                                websocket_bridge_integration_failures.append({
                                    'failure_type': 'event_send_failure',
                                    'registry': registry_name,
                                    'user_id': user_id,
                                    'event_type': event_type,
                                    'description': f"Could not send {event_type} event for {user_id} via {registry_name} registry"
                                })
                                
                        except Exception as e:
                            websocket_bridge_integration_failures.append({
                                'failure_type': 'event_send_error',
                                'registry': registry_name,
                                'user_id': user_id,
                                'event_type': event_type,
                                'error': str(e),
                                'description': f"Error sending {event_type} event for {user_id} via {registry_name} registry: {e}"
                            })
        
        # DESIGNED TO FAIL: WebSocket bridge incompatibilities with basic registry
        failure_reasons = []
        
        if websocket_bridge_integration_failures:
            for failure in websocket_bridge_integration_failures:
                failure_reasons.append(f"{failure['failure_type']}: {failure['description']}")
        
        # Check for asymmetric WebSocket capabilities
        basic_event_support = len(basic_compat['websocket_events_supported'])
        advanced_event_support = len(advanced_compat['websocket_events_supported'])
        
        if basic_event_support < advanced_event_support:
            failure_reasons.append(
                f"Basic registry supports {basic_event_support} WebSocket events vs "
                f"advanced registry's {advanced_event_support} events - incompatible capabilities"
            )
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL WEBSOCKET BRIDGE INCOMPATIBILITY: Basic registry incompatible with WebSocket bridge. "
                f"This prevents real-time agent progress updates blocking Golden Path user experience. "
                f"Integration failures: {'; '.join(failure_reasons)}. "
                f"IMPACT: Users don't see agent progress when basic registry is used."
            )
        
        # If no incompatibilities detected, WebSocket bridge integration is consistent
        self.logger.info("WebSocket bridge integration is consistent across all registries")

    async def test_missing_websocket_events_blocking_golden_path(self):
        """
        CRITICAL P0 TEST: Prove missing WebSocket events block Golden Path
        
        DESIGNED TO FAIL: Registry SSOT violations cause critical WebSocket events
        to be missing or inconsistent, breaking real-time agent progress visibility.
        
        Business Impact: Golden Path user experience degrades when agents appear
        to hang or complete without progress updates, causing user frustration.
        """
        websocket_event_completeness_failures = []
        registry_event_analysis = {}
        
        # Test comprehensive WebSocket event delivery for both registries
        registries = {
            'basic': self.basic_registry,
            'advanced': self.advanced_registry
        }
        
        for registry_name, registry in registries.items():
            registry_event_analysis[registry_name] = {
                'events_sent_successfully': [],
                'events_failed_to_send': [],
                'events_received_count': 0,
                'critical_events_missing': [],
                'event_delivery_rate': 0.0,
                'event_sequence_correct': True,
                'event_timing_issues': []
            }
            
            # Set up WebSocket integration for testing
            websocket_setup_success = False
            try:
                if hasattr(registry, 'set_websocket_manager'):
                    set_manager_method = getattr(registry, 'set_websocket_manager')
                    if asyncio.iscoroutinefunction(set_manager_method):
                        await set_manager_method(self.mock_websocket_manager)
                    else:
                        set_manager_method(self.mock_websocket_manager)
                    websocket_setup_success = True
                    
            except Exception as e:
                self.logger.error(f"WebSocket setup failed for {registry_name} registry: {e}")
            
            if not websocket_setup_success:
                registry_event_analysis[registry_name]['critical_events_missing'] = self.critical_websocket_events
                continue
            
            # Clear previous event logs
            initial_event_count = len(self.websocket_event_log)
            
            # Simulate complete Golden Path agent execution with all critical events
            for user_info in self.test_users:
                user_id = user_info['user_id']
                session_id = user_info['session_id']
                
                # Simulate agent execution sequence with timing
                agent_execution_sequence = [
                    {
                        'event': 'agent_started',
                        'data': {'agent_id': 'test-agent', 'user_id': user_id, 'status': 'started'},
                        'expected_order': 1
                    },
                    {
                        'event': 'agent_thinking',
                        'data': {'agent_id': 'test-agent', 'user_id': user_id, 'message': 'Analyzing request'},
                        'expected_order': 2
                    },
                    {
                        'event': 'tool_executing',
                        'data': {'agent_id': 'test-agent', 'user_id': user_id, 'tool': 'data_analyzer'},
                        'expected_order': 3
                    },
                    {
                        'event': 'tool_completed',
                        'data': {'agent_id': 'test-agent', 'user_id': user_id, 'tool': 'data_analyzer', 'result': 'success'},
                        'expected_order': 4
                    },
                    {
                        'event': 'agent_completed',
                        'data': {'agent_id': 'test-agent', 'user_id': user_id, 'status': 'completed', 'result': 'Task completed'},
                        'expected_order': 5
                    }
                ]
                
                # Send each event and track success/failure
                for event_info in agent_execution_sequence:
                    event_type = event_info['event']
                    event_data = event_info['data']
                    
                    try:
                        # Try multiple event sending methods
                        event_sent_successfully = False
                        
                        for method_name in ['_notify_agent_event', 'emit_agent_event', 'notify_websocket_event']:
                            if hasattr(registry, method_name):
                                method = getattr(registry, method_name)
                                
                                if asyncio.iscoroutinefunction(method):
                                    await method(event_type, event_data)
                                else:
                                    method(event_type, event_data)
                                
                                registry_event_analysis[registry_name]['events_sent_successfully'].append({
                                    'event_type': event_type,
                                    'user_id': user_id,
                                    'method_used': method_name,
                                    'timestamp': time.time(),
                                    'expected_order': event_info['expected_order']
                                })
                                
                                event_sent_successfully = True
                                self.logger.debug(f"Event {event_type} sent successfully for {user_id} via {registry_name} registry")
                                break
                        
                        if not event_sent_successfully:
                            registry_event_analysis[registry_name]['events_failed_to_send'].append({
                                'event_type': event_type,
                                'user_id': user_id,
                                'reason': 'No suitable event sending method found',
                                'expected_order': event_info['expected_order']
                            })
                            
                    except Exception as e:
                        registry_event_analysis[registry_name]['events_failed_to_send'].append({
                            'event_type': event_type,
                            'user_id': user_id,
                            'reason': f'Event sending failed: {e}',
                            'error': str(e),
                            'expected_order': event_info['expected_order']
                        })
                        self.logger.error(f"Failed to send {event_type} for {user_id} via {registry_name}: {e}")
                    
                    # Small delay between events to simulate realistic timing
                    await asyncio.sleep(0.05)
            
            # Allow time for event processing
            await asyncio.sleep(0.2)
            
            # Analyze event delivery results
            events_sent_count = len(registry_event_analysis[registry_name]['events_sent_successfully'])
            events_failed_count = len(registry_event_analysis[registry_name]['events_failed_to_send'])
            total_expected_events = len(self.critical_websocket_events) * len(self.test_users)
            
            if total_expected_events > 0:
                registry_event_analysis[registry_name]['event_delivery_rate'] = (events_sent_count / total_expected_events) * 100
            
            # Check for critical events that failed to send
            failed_critical_events = set()
            for failed_event in registry_event_analysis[registry_name]['events_failed_to_send']:
                failed_critical_events.add(failed_event['event_type'])
            
            registry_event_analysis[registry_name]['critical_events_missing'] = list(failed_critical_events)
            
            # Check event sequence correctness
            sent_events_by_user = {}
            for sent_event in registry_event_analysis[registry_name]['events_sent_successfully']:
                user_id = sent_event['user_id']
                if user_id not in sent_events_by_user:
                    sent_events_by_user[user_id] = []
                sent_events_by_user[user_id].append(sent_event)
            
            # Analyze event sequence for each user
            for user_id, user_events in sent_events_by_user.items():
                # Sort events by timestamp
                user_events.sort(key=lambda x: x['timestamp'])
                
                # Check if event order matches expected sequence
                for i, event in enumerate(user_events):
                    expected_order = event['expected_order']
                    actual_order = i + 1
                    
                    if actual_order != expected_order:
                        registry_event_analysis[registry_name]['event_sequence_correct'] = False
                        registry_event_analysis[registry_name]['event_timing_issues'].append({
                            'user_id': user_id,
                            'event_type': event['event_type'],
                            'expected_order': expected_order,
                            'actual_order': actual_order,
                            'issue': f"Event {event['event_type']} was #{actual_order} but should be #{expected_order}"
                        })
            
            # Check if we received the expected number of events in our capture log
            current_event_count = len(self.websocket_event_log)
            events_captured = current_event_count - initial_event_count
            registry_event_analysis[registry_name]['events_received_count'] = events_captured
        
        # Compare registry event delivery capabilities
        basic_analysis = registry_event_analysis['basic']
        advanced_analysis = registry_event_analysis['advanced']
        
        # Check for critical event delivery failures
        if basic_analysis['critical_events_missing']:
            websocket_event_completeness_failures.append({
                'failure_type': 'missing_critical_events',
                'registry': 'basic',
                'missing_events': basic_analysis['critical_events_missing'],
                'description': f"Basic registry missing critical WebSocket events: {basic_analysis['critical_events_missing']}"
            })
        
        if advanced_analysis['critical_events_missing']:
            websocket_event_completeness_failures.append({
                'failure_type': 'missing_critical_events',
                'registry': 'advanced',
                'missing_events': advanced_analysis['critical_events_missing'],
                'description': f"Advanced registry missing critical WebSocket events: {advanced_analysis['critical_events_missing']}"
            })
        
        # Check for poor event delivery rates
        for registry_name, analysis in registry_event_analysis.items():
            if analysis['event_delivery_rate'] < 100.0:  # Expect 100% delivery for Golden Path
                websocket_event_completeness_failures.append({
                    'failure_type': 'poor_event_delivery_rate',
                    'registry': registry_name,
                    'delivery_rate': analysis['event_delivery_rate'],
                    'events_failed': len(analysis['events_failed_to_send']),
                    'description': f"{registry_name} registry event delivery rate only {analysis['event_delivery_rate']:.1f}%"
                })
        
        # Check for event sequence issues
        for registry_name, analysis in registry_event_analysis.items():
            if not analysis['event_sequence_correct']:
                websocket_event_completeness_failures.append({
                    'failure_type': 'event_sequence_incorrect',
                    'registry': registry_name,
                    'timing_issues': analysis['event_timing_issues'],
                    'description': f"{registry_name} registry event sequence incorrect: {len(analysis['event_timing_issues'])} timing issues"
                })
        
        # Check for asymmetric event capabilities between registries
        basic_delivery_rate = basic_analysis['event_delivery_rate']
        advanced_delivery_rate = advanced_analysis['event_delivery_rate']
        
        if abs(basic_delivery_rate - advanced_delivery_rate) > 20.0:  # >20% difference is significant
            websocket_event_completeness_failures.append({
                'failure_type': 'asymmetric_event_capabilities',
                'basic_delivery_rate': basic_delivery_rate,
                'advanced_delivery_rate': advanced_delivery_rate,
                'difference': abs(basic_delivery_rate - advanced_delivery_rate),
                'description': f"Event delivery rates differ significantly: basic {basic_delivery_rate:.1f}% vs advanced {advanced_delivery_rate:.1f}%"
            })
        
        # DESIGNED TO FAIL: Missing or incomplete WebSocket events block Golden Path
        failure_reasons = []
        
        if websocket_event_completeness_failures:
            for failure in websocket_event_completeness_failures:
                failure_reasons.append(f"{failure['failure_type']}: {failure['description']}")
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL MISSING WEBSOCKET EVENTS: WebSocket events missing or incomplete blocking Golden Path. "
                f"This prevents users from seeing real-time agent progress causing poor user experience. "
                f"Event delivery failures: {'; '.join(failure_reasons)}. "
                f"IMPACT: Users cannot track agent execution progress and assume system is broken."
            )
        
        # If all events are delivered correctly, WebSocket event system is complete
        self.logger.info("All critical WebSocket events delivered successfully across registries")

    async def test_chat_functionality_degradation_from_registry_conflicts(self):
        """
        CRITICAL P0 TEST: Prove chat functionality degrades from registry conflicts
        
        DESIGNED TO FAIL: Registry SSOT violations cause chat functionality to
        degrade when different registries are used inconsistently across services.
        
        Business Impact: Golden Path chat experience varies unpredictably,
        sometimes working perfectly, sometimes failing completely.
        """
        chat_functionality_degradation = []
        chat_experience_analysis = {}
        
        # Simulate different registry usage scenarios in chat functionality
        chat_test_scenarios = [
            {
                'name': 'basic_registry_only',
                'description': 'All components use basic registry',
                'registry_config': {
                    'agent_registry': self.basic_registry,
                    'websocket_registry': self.basic_registry,
                    'execution_registry': self.basic_registry
                }
            },
            {
                'name': 'advanced_registry_only',
                'description': 'All components use advanced registry',
                'registry_config': {
                    'agent_registry': self.advanced_registry,
                    'websocket_registry': self.advanced_registry,
                    'execution_registry': self.advanced_registry
                }
            },
            {
                'name': 'mixed_registry_usage',
                'description': 'Components use different registries (conflict scenario)',
                'registry_config': {
                    'agent_registry': self.basic_registry,
                    'websocket_registry': self.advanced_registry,
                    'execution_registry': self.basic_registry
                }
            }
        ]
        
        for scenario in chat_test_scenarios:
            scenario_name = scenario['name']
            registry_config = scenario['registry_config']
            
            chat_experience_analysis[scenario_name] = {
                'scenario_description': scenario['description'],
                'chat_initiation_success': False,
                'agent_discovery_success': False,
                'websocket_connection_success': False,
                'real_time_updates_working': False,
                'chat_completion_success': False,
                'user_experience_score': 0,
                'critical_failures': [],
                'degradation_indicators': []
            }
            
            self.logger.info(f"Testing chat functionality scenario: {scenario['description']}")
            
            # Test chat initiation
            try:
                # 1. Agent Discovery Phase
                agent_registry = registry_config['agent_registry']
                available_agents = None
                
                if hasattr(agent_registry, 'list_available_agents'):
                    list_method = getattr(agent_registry, 'list_available_agents')
                    if asyncio.iscoroutinefunction(list_method):
                        available_agents = await list_method()
                    else:
                        available_agents = list_method()
                    
                    if available_agents is not None:
                        chat_experience_analysis[scenario_name]['agent_discovery_success'] = True
                        self.logger.debug(f"{scenario_name}: Agent discovery succeeded")
                    else:
                        chat_experience_analysis[scenario_name]['critical_failures'].append(
                            'Agent discovery returned None'
                        )
                else:
                    chat_experience_analysis[scenario_name]['critical_failures'].append(
                        'Agent registry missing list_available_agents method'
                    )
                
                # 2. WebSocket Connection Phase
                websocket_registry = registry_config['websocket_registry']
                websocket_setup_success = False
                
                if hasattr(websocket_registry, 'set_websocket_manager'):
                    set_ws_method = getattr(websocket_registry, 'set_websocket_manager')
                    if asyncio.iscoroutinefunction(set_ws_method):
                        await set_ws_method(self.mock_websocket_manager)
                    else:
                        set_ws_method(self.mock_websocket_manager)
                    
                    websocket_setup_success = True
                    chat_experience_analysis[scenario_name]['websocket_connection_success'] = True
                    self.logger.debug(f"{scenario_name}: WebSocket connection succeeded")
                else:
                    chat_experience_analysis[scenario_name]['critical_failures'].append(
                        'WebSocket registry missing set_websocket_manager method'
                    )
                
                # 3. User Session Creation Phase
                execution_registry = registry_config['execution_registry']
                user_sessions_created = 0
                
                for user_info in self.test_users:
                    user_id = user_info['user_id']
                    session_id = user_info['session_id']
                    
                    try:
                        if hasattr(execution_registry, 'create_user_session'):
                            create_session_method = getattr(execution_registry, 'create_user_session')
                            user_session = await create_session_method(user_id, session_id)
                            
                            if user_session:
                                user_sessions_created += 1
                                self.logger.debug(f"{scenario_name}: User session created for {user_id}")
                            else:
                                chat_experience_analysis[scenario_name]['degradation_indicators'].append(
                                    f'User session creation returned None for {user_id}'
                                )
                        else:
                            chat_experience_analysis[scenario_name]['degradation_indicators'].append(
                                'Execution registry missing create_user_session method'
                            )
                            
                    except Exception as e:
                        chat_experience_analysis[scenario_name]['degradation_indicators'].append(
                            f'User session creation failed for {user_id}: {e}'
                        )
                
                if user_sessions_created > 0:
                    chat_experience_analysis[scenario_name]['chat_initiation_success'] = True
                
                # 4. Real-time Updates Test Phase
                if websocket_setup_success:
                    events_sent_successfully = 0
                    total_events_attempted = 0
                    
                    for user_info in self.test_users:
                        user_id = user_info['user_id']
                        
                        for event_type in self.critical_websocket_events:
                            total_events_attempted += 1
                            event_data = {
                                'user_id': user_id,
                                'event': event_type,
                                'test_data': f'chat_test_{scenario_name}_{event_type}'
                            }
                            
                            try:
                                # Try to send event through WebSocket registry
                                event_sent = False
                                
                                for method_name in ['_notify_agent_event', 'emit_agent_event']:
                                    if hasattr(websocket_registry, method_name):
                                        method = getattr(websocket_registry, method_name)
                                        if asyncio.iscoroutinefunction(method):
                                            await method(event_type, event_data)
                                        else:
                                            method(event_type, event_data)
                                        
                                        events_sent_successfully += 1
                                        event_sent = True
                                        break
                                
                                if not event_sent:
                                    chat_experience_analysis[scenario_name]['degradation_indicators'].append(
                                        f'Could not send {event_type} event for {user_id} - no suitable method'
                                    )
                                    
                            except Exception as e:
                                chat_experience_analysis[scenario_name]['degradation_indicators'].append(
                                    f'Failed to send {event_type} event for {user_id}: {e}'
                                )
                    
                    # Calculate real-time update success rate
                    if total_events_attempted > 0:
                        real_time_success_rate = (events_sent_successfully / total_events_attempted) * 100
                        if real_time_success_rate >= 80:  # 80% threshold for acceptable experience
                            chat_experience_analysis[scenario_name]['real_time_updates_working'] = True
                        else:
                            chat_experience_analysis[scenario_name]['degradation_indicators'].append(
                                f'Real-time update success rate only {real_time_success_rate:.1f}%'
                            )
                
                # 5. Chat Completion Test Phase
                # Simulate completing a chat interaction
                chat_completion_steps = [
                    chat_experience_analysis[scenario_name]['agent_discovery_success'],
                    chat_experience_analysis[scenario_name]['websocket_connection_success'],
                    chat_experience_analysis[scenario_name]['chat_initiation_success'],
                    chat_experience_analysis[scenario_name]['real_time_updates_working']
                ]
                
                completed_steps = sum(chat_completion_steps)
                total_steps = len(chat_completion_steps)
                
                if completed_steps == total_steps:
                    chat_experience_analysis[scenario_name]['chat_completion_success'] = True
                    chat_experience_analysis[scenario_name]['user_experience_score'] = 100
                else:
                    completion_rate = (completed_steps / total_steps) * 100
                    chat_experience_analysis[scenario_name]['user_experience_score'] = completion_rate
                    
                    if completion_rate < 75:  # Below 75% is poor experience
                        chat_experience_analysis[scenario_name]['critical_failures'].append(
                            f'Chat completion rate only {completion_rate:.1f}% - poor user experience'
                        )
                
            except Exception as e:
                chat_experience_analysis[scenario_name]['critical_failures'].append(
                    f'Scenario execution failed: {e}'
                )
                self.logger.error(f"Chat functionality test failed for {scenario_name}: {e}")
        
        # Analyze chat functionality degradation patterns
        scenario_scores = {}
        for scenario_name, analysis in chat_experience_analysis.items():
            scenario_scores[scenario_name] = analysis['user_experience_score']
        
        # Check for significant degradation between scenarios
        best_score = max(scenario_scores.values())
        worst_score = min(scenario_scores.values())
        score_variance = best_score - worst_score
        
        if score_variance > 30:  # >30% variance indicates significant degradation
            chat_functionality_degradation.append({
                'degradation_type': 'inconsistent_chat_experience',
                'best_scenario': max(scenario_scores, key=scenario_scores.get),
                'worst_scenario': min(scenario_scores, key=scenario_scores.get),
                'best_score': best_score,
                'worst_score': worst_score,
                'variance': score_variance,
                'description': f'Chat experience varies by {score_variance:.1f}% between scenarios'
            })
        
        # Check for specific degradation in mixed registry scenario
        mixed_scenario_analysis = chat_experience_analysis.get('mixed_registry_usage')
        if mixed_scenario_analysis:
            mixed_score = mixed_scenario_analysis['user_experience_score']
            
            # Compare mixed scenario to pure scenarios
            pure_scenarios = ['basic_registry_only', 'advanced_registry_only']
            pure_scores = [chat_experience_analysis[s]['user_experience_score'] for s in pure_scenarios if s in chat_experience_analysis]
            
            if pure_scores and mixed_score < min(pure_scores):
                chat_functionality_degradation.append({
                    'degradation_type': 'mixed_registry_degradation',
                    'mixed_score': mixed_score,
                    'pure_scenario_min': min(pure_scores),
                    'degradation_amount': min(pure_scores) - mixed_score,
                    'critical_failures': mixed_scenario_analysis['critical_failures'],
                    'description': f'Mixed registry usage causes {min(pure_scores) - mixed_score:.1f}% degradation'
                })
        
        # Check for critical failure patterns
        for scenario_name, analysis in chat_experience_analysis.items():
            if analysis['critical_failures']:
                chat_functionality_degradation.append({
                    'degradation_type': 'critical_failures',
                    'scenario': scenario_name,
                    'failures': analysis['critical_failures'],
                    'description': f'{scenario_name} has critical failures: {"; ".join(analysis["critical_failures"])}'
                })
        
        # DESIGNED TO FAIL: Chat functionality degradation from registry conflicts
        failure_reasons = []
        
        if chat_functionality_degradation:
            for degradation in chat_functionality_degradation:
                failure_reasons.append(f"{degradation['degradation_type']}: {degradation['description']}")
        
        # Check for scenarios with poor user experience scores
        poor_experience_scenarios = []
        for scenario_name, analysis in chat_experience_analysis.items():
            if analysis['user_experience_score'] < 75:  # Below 75% is poor
                poor_experience_scenarios.append(f"{scenario_name}: {analysis['user_experience_score']:.1f}%")
        
        if poor_experience_scenarios:
            failure_reasons.append(f"Poor chat experience in scenarios: {'; '.join(poor_experience_scenarios)}")
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL CHAT FUNCTIONALITY DEGRADATION: Registry conflicts cause unpredictable chat experience. "
                f"This creates unreliable Golden Path where chat sometimes works, sometimes fails completely. "
                f"Degradation patterns: {'; '.join(failure_reasons)}. "
                f"IMPACT: Users experience inconsistent chat functionality depending on deployment configuration."
            )
        
        # If no degradation detected, chat functionality is consistent across registries
        self.logger.info("Chat functionality is consistent across all registry configurations")

    async def test_real_time_user_experience_failures(self):
        """
        CRITICAL P0 TEST: Prove real-time user experience fails with registry conflicts
        
        DESIGNED TO FAIL: Registry SSOT violations cause real-time user experience
        to fail with delayed updates, missing progress indicators, and poor responsiveness.
        
        Business Impact: Golden Path user experience degrades causing users to
        abandon chat sessions and perceive the system as broken or unresponsive.
        """
        real_time_experience_failures = []
        user_experience_metrics = {}
        
        # Test real-time user experience with both registries
        registries_to_test = {
            'basic': self.basic_registry,
            'advanced': self.advanced_registry
        }
        
        for registry_name, registry in registries_to_test.items():
            user_experience_metrics[registry_name] = {
                'response_times': [],
                'event_delivery_delays': [],
                'progress_visibility_score': 0,
                'user_feedback_responsiveness': 0,
                'real_time_experience_score': 0,
                'experience_failures': [],
                'performance_issues': []
            }
            
            # Set up WebSocket for real-time testing
            websocket_setup_success = False
            try:
                if hasattr(registry, 'set_websocket_manager'):
                    set_ws_method = getattr(registry, 'set_websocket_manager')
                    if asyncio.iscoroutinefunction(set_ws_method):
                        await set_ws_method(self.mock_websocket_manager)
                    else:
                        set_ws_method(self.mock_websocket_manager)
                    websocket_setup_success = True
                    
            except Exception as e:
                user_experience_metrics[registry_name]['experience_failures'].append(
                    f'WebSocket setup failed: {e}'
                )
            
            if not websocket_setup_success:
                user_experience_metrics[registry_name]['real_time_experience_score'] = 0
                continue
            
            # Test real-time experience for each user
            for user_info in self.test_users:
                user_id = user_info['user_id']
                session_id = user_info['session_id']
                
                # Create user session
                user_session_success = False
                try:
                    if hasattr(registry, 'create_user_session'):
                        create_session_method = getattr(registry, 'create_user_session')
                        user_session = await create_session_method(user_id, session_id)
                        if user_session:
                            user_session_success = True
                        
                except Exception as e:
                    user_experience_metrics[registry_name]['experience_failures'].append(
                        f'User session creation failed for {user_id}: {e}'
                    )
                
                if not user_session_success:
                    continue
                
                # Simulate real-time agent interaction with timing measurements
                agent_interaction_sequence = [
                    {'event': 'user_message_received', 'expected_delay_ms': 0},
                    {'event': 'agent_started', 'expected_delay_ms': 100},
                    {'event': 'agent_thinking', 'expected_delay_ms': 200},
                    {'event': 'tool_executing', 'expected_delay_ms': 500},
                    {'event': 'tool_completed', 'expected_delay_ms': 1000},
                    {'event': 'agent_completed', 'expected_delay_ms': 1200}
                ]
                
                interaction_start_time = time.time()
                previous_event_time = interaction_start_time
                
                for event_info in agent_interaction_sequence:
                    event_type = event_info['event']
                    expected_delay = event_info['expected_delay_ms'] / 1000.0  # Convert to seconds
                    
                    # Wait for expected delay
                    target_time = interaction_start_time + expected_delay
                    current_time = time.time()
                    if current_time < target_time:
                        await asyncio.sleep(target_time - current_time)
                    
                    # Send the event and measure response time
                    event_send_start = time.time()
                    
                    try:
                        event_data = {
                            'user_id': user_id,
                            'session_id': session_id,
                            'event_type': event_type,
                            'timestamp': event_send_start,
                            'sequence_number': len(agent_interaction_sequence)
                        }
                        
                        # Try to send event
                        event_sent = False
                        for method_name in ['_notify_agent_event', 'emit_agent_event']:
                            if hasattr(registry, method_name):
                                method = getattr(registry, method_name)
                                if asyncio.iscoroutinefunction(method):
                                    await method(event_type, event_data)
                                else:
                                    method(event_type, event_data)
                                event_sent = True
                                break
                        
                        event_send_end = time.time()
                        event_processing_time = (event_send_end - event_send_start) * 1000  # Convert to ms
                        
                        user_experience_metrics[registry_name]['response_times'].append(event_processing_time)
                        
                        # Calculate delivery delay from expected timing
                        actual_event_time = event_send_end - interaction_start_time
                        delivery_delay = abs(actual_event_time - expected_delay) * 1000  # Convert to ms
                        user_experience_metrics[registry_name]['event_delivery_delays'].append(delivery_delay)
                        
                        if not event_sent:
                            user_experience_metrics[registry_name]['experience_failures'].append(
                                f'Failed to send {event_type} event for {user_id} - no method available'
                            )
                        
                        # Check for slow event processing (>100ms is noticeable to users)
                        if event_processing_time > 100:
                            user_experience_metrics[registry_name]['performance_issues'].append({
                                'issue_type': 'slow_event_processing',
                                'event_type': event_type,
                                'user_id': user_id,
                                'processing_time_ms': event_processing_time,
                                'description': f'{event_type} event took {event_processing_time:.1f}ms to process'
                            })
                        
                        # Check for significant timing delays (>500ms affects user experience)
                        if delivery_delay > 500:
                            user_experience_metrics[registry_name]['performance_issues'].append({
                                'issue_type': 'event_timing_delay',
                                'event_type': event_type,
                                'user_id': user_id,
                                'delay_ms': delivery_delay,
                                'expected_delay': expected_delay * 1000,
                                'actual_delay': actual_event_time * 1000,
                                'description': f'{event_type} event delayed by {delivery_delay:.1f}ms'
                            })
                        
                        previous_event_time = event_send_end
                        
                    except Exception as e:
                        user_experience_metrics[registry_name]['experience_failures'].append(
                            f'Event {event_type} failed for {user_id}: {e}'
                        )
                        self.logger.error(f"Real-time event {event_type} failed for {user_id} in {registry_name}: {e}")
            
            # Calculate user experience scores
            response_times = user_experience_metrics[registry_name]['response_times']
            event_delays = user_experience_metrics[registry_name]['event_delivery_delays']
            
            # Progress Visibility Score (based on successful event delivery)
            total_events_attempted = len(self.critical_websocket_events) * len(self.test_users)
            successful_events = len(response_times)
            progress_visibility = (successful_events / total_events_attempted * 100) if total_events_attempted > 0 else 0
            user_experience_metrics[registry_name]['progress_visibility_score'] = progress_visibility
            
            # User Feedback Responsiveness Score (based on response times)
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                # Score decreases as response time increases (100ms = 100%, 1000ms = 0%)
                responsiveness = max(0, 100 - (avg_response_time / 10))
                user_experience_metrics[registry_name]['user_feedback_responsiveness'] = responsiveness
            else:
                user_experience_metrics[registry_name]['user_feedback_responsiveness'] = 0
            
            # Overall Real-time Experience Score
            progress_weight = 0.6  # Progress visibility is most important
            responsiveness_weight = 0.4  # Response time is secondary
            
            overall_score = (progress_visibility * progress_weight + 
                           user_experience_metrics[registry_name]['user_feedback_responsiveness'] * responsiveness_weight)
            user_experience_metrics[registry_name]['real_time_experience_score'] = overall_score
            
            self.logger.info(f"{registry_name} registry real-time experience score: {overall_score:.1f}%")
        
        # Analyze real-time experience failures
        for registry_name, metrics in user_experience_metrics.items():
            # Check for poor progress visibility
            if metrics['progress_visibility_score'] < 90:  # Less than 90% is poor
                real_time_experience_failures.append({
                    'failure_type': 'poor_progress_visibility',
                    'registry': registry_name,
                    'visibility_score': metrics['progress_visibility_score'],
                    'description': f'{registry_name} registry progress visibility only {metrics["progress_visibility_score"]:.1f}%'
                })
            
            # Check for poor responsiveness
            if metrics['user_feedback_responsiveness'] < 80:  # Less than 80% is poor
                real_time_experience_failures.append({
                    'failure_type': 'poor_responsiveness',
                    'registry': registry_name,
                    'responsiveness_score': metrics['user_feedback_responsiveness'],
                    'description': f'{registry_name} registry responsiveness only {metrics["user_feedback_responsiveness"]:.1f}%'
                })
            
            # Check for significant performance issues
            if metrics['performance_issues']:
                performance_issue_count = len(metrics['performance_issues'])
                real_time_experience_failures.append({
                    'failure_type': 'performance_issues',
                    'registry': registry_name,
                    'issue_count': performance_issue_count,
                    'issues': metrics['performance_issues'],
                    'description': f'{registry_name} registry has {performance_issue_count} performance issues'
                })
            
            # Check for experience failures
            if metrics['experience_failures']:
                failure_count = len(metrics['experience_failures'])
                real_time_experience_failures.append({
                    'failure_type': 'experience_failures',
                    'registry': registry_name,
                    'failure_count': failure_count,
                    'failures': metrics['experience_failures'],
                    'description': f'{registry_name} registry has {failure_count} experience failures'
                })
        
        # Compare real-time experience between registries
        basic_score = user_experience_metrics.get('basic', {}).get('real_time_experience_score', 0)
        advanced_score = user_experience_metrics.get('advanced', {}).get('real_time_experience_score', 0)
        
        if abs(basic_score - advanced_score) > 20:  # >20% difference is significant
            real_time_experience_failures.append({
                'failure_type': 'inconsistent_real_time_experience',
                'basic_score': basic_score,
                'advanced_score': advanced_score,
                'difference': abs(basic_score - advanced_score),
                'description': f'Real-time experience differs by {abs(basic_score - advanced_score):.1f}% between registries'
            })
        
        # Check for unacceptable overall experience
        unacceptable_registries = []
        for registry_name, metrics in user_experience_metrics.items():
            if metrics['real_time_experience_score'] < 75:  # Below 75% is unacceptable
                unacceptable_registries.append(f"{registry_name}: {metrics['real_time_experience_score']:.1f}%")
        
        if unacceptable_registries:
            real_time_experience_failures.append({
                'failure_type': 'unacceptable_user_experience',
                'registries': unacceptable_registries,
                'description': f'Unacceptable real-time experience: {"; ".join(unacceptable_registries)}'
            })
        
        # DESIGNED TO FAIL: Real-time user experience failures detected
        failure_reasons = []
        
        if real_time_experience_failures:
            for failure in real_time_experience_failures:
                failure_reasons.append(f"{failure['failure_type']}: {failure['description']}")
        
        if failure_reasons:
            pytest.fail(
                f"CRITICAL REAL-TIME USER EXPERIENCE FAILURES: Registry conflicts cause poor real-time experience. "
                f"This makes Golden Path feel broken and unresponsive causing user abandonment. "
                f"Experience failures: {'; '.join(failure_reasons)}. "
                f"IMPACT: Users perceive system as slow, broken, or unresponsive during agent interactions."
            )
        
        # If no real-time experience failures, user experience is consistent and good
        self.logger.info("Real-time user experience is excellent and consistent across all registries")

    async def async_teardown_method(self, method=None):
        """Clean up test resources"""
        # Clear event logs and tracking data
        self.websocket_event_log.clear()
        self.websocket_integration_failures.clear()
        self.user_websocket_managers.clear()
        
        await super().async_teardown_method(method)


if __name__ == "__main__":
    # Run with pytest for proper async support
    pytest.main([__file__, "-v", "--tb=short", "-s"])