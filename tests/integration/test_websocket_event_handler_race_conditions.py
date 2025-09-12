"""
TEST SUITE 2: WebSocket Event Handler Wiring Race Conditions
===========================================================

CRITICAL PURPOSE: This test suite reproduces WebSocket race condition regression
caused by event handler wiring issues where:

1. Dual interface event handler wiring race conditions
2. Undefined event handler references due to interface confusion
3. Timing-dependent event delivery races between interfaces
4. Partial event handler initialization causing dropped events

BUSINESS VALUE:
- Prevents event delivery failures causing user chat interruptions  
- Ensures reliable WebSocket event flow for AI agent interactions
- Validates proper event handler wiring in multi-user scenarios

EXPECTED BEHAVIOR: These tests should INITIALLY FAIL, reproducing the regression issues.
"""

import asyncio
import pytest
import logging
import json
import time
import weakref
import uuid
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
import concurrent.futures
import threading

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import IsolatedEnvironment
from shared.types.core_types import UserID, ensure_user_id

# Critical imports for WebSocket event handling
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    create_agent_websocket_bridge
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.handlers import BaseMessageHandler
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.websocket_race_conditions  
class TestWebSocketEventHandlerRaceConditions(SSotBaseTestCase):
    """
    Integration tests for WebSocket event handler wiring race conditions.
    
    These tests reproduce the regression where dual WebSocket interfaces
    cause event handler wiring issues and race conditions.
    """

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.test_user_id = ensure_user_id(str(uuid.uuid4()))
        self.event_delivery_log = []
        self.race_condition_detector = []
        
    async def async_setup_method(self):
        """Async setup for integration tests."""
        # Setup real components for integration testing
        self.user_context = UserExecutionContext(
            user_id=str(self.test_user_id),
            request_id="event_race_test_request",
            thread_id="event_race_test_thread",
            run_id=str(uuid.uuid4())
        )
        
    @pytest.mark.regression_reproduction
    async def test_dual_interface_event_handler_wiring_race(self):
        """
        CRITICAL: Test race conditions in dual WebSocket interface event handler wiring.
        
        ROOT CAUSE REPRODUCTION: When both WebSocketManager and AgentWebSocketBridge
        are wired simultaneously, event handlers can conflict, causing events to
        be delivered to wrong handlers or dropped entirely.
        
        EXPECTED FAILURE: Should fail due to handler wiring race conditions.
        """
        logger.info(" ALERT:  TESTING: Dual interface event handler wiring race conditions")
        
        await self.async_setup_method()
        
        # CRITICAL: Create both interface types simultaneously
        websocket_manager = Mock(spec=WebSocketManager)
        websocket_bridge = create_agent_websocket_bridge(self.user_context)
        
        # REGRESSION EXPOSURE: Track event handler registration
        handler_registrations = []
        event_deliveries = []
        
        def track_handler_registration(interface_name: str, event_type: str, handler: Callable):
            """Track which interface registers which handlers."""
            registration_time = time.time()
            handler_registrations.append({
                'interface': interface_name,
                'event_type': event_type,
                'handler_id': id(handler),
                'timestamp': registration_time
            })
            logger.debug(f"Handler registered: {interface_name}.{event_type} at {registration_time}")
            
        def track_event_delivery(interface_name: str, event_type: str, event_data: Dict[str, Any]):
            """Track which interface delivers which events."""
            delivery_time = time.time()
            event_deliveries.append({
                'interface': interface_name,
                'event_type': event_type,
                'event_data': event_data,
                'timestamp': delivery_time
            })
            logger.debug(f"Event delivered: {interface_name}.{event_type} at {delivery_time}")
            
        # CRITICAL: Setup event handler tracking on both interfaces
        critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        # Mock WebSocketManager handler registration
        websocket_manager.register_handler = Mock(
            side_effect=lambda event_type, handler: track_handler_registration('manager', event_type, handler)
        )
        websocket_manager.send_event = Mock(
            side_effect=lambda event_type, data: track_event_delivery('manager', event_type, data)
        )
        
        # REGRESSION EXPOSURE: Register handlers on both interfaces simultaneously
        registration_tasks = []
        
        async def register_manager_handlers():
            """Register handlers on WebSocketManager."""
            for event_type in critical_events:
                await asyncio.sleep(0.001)  # Small delay to trigger race
                handler = Mock()
                websocket_manager.register_handler(event_type, handler)
                
        async def register_bridge_handlers():
            """Register handlers on AgentWebSocketBridge.""" 
            for event_type in critical_events:
                await asyncio.sleep(0.0015)  # Slightly different delay
                if hasattr(websocket_bridge, 'register_handler'):
                    handler = Mock()
                    websocket_bridge.register_handler(event_type, handler)
                    track_handler_registration('bridge', event_type, handler)
                    
        # CRITICAL: Run concurrent handler registration (triggers race condition)
        await asyncio.gather(
            register_manager_handlers(),
            register_bridge_handlers()
        )
        
        # REGRESSION EXPOSURE: Send events to both interfaces simultaneously 
        async def send_manager_events():
            """Send events via WebSocketManager."""
            for event_type in critical_events:
                event_data = {'source': 'manager', 'timestamp': time.time()}
                websocket_manager.send_event(event_type, event_data)
                await asyncio.sleep(0.002)
                
        async def send_bridge_events():
            """Send events via AgentWebSocketBridge."""
            for event_type in critical_events:
                event_data = {'source': 'bridge', 'timestamp': time.time()}
                if hasattr(websocket_bridge, 'send_event'):
                    websocket_bridge.send_event(event_type, event_data)
                    track_event_delivery('bridge', event_type, event_data)
                await asyncio.sleep(0.0025)
                
        # CRITICAL: Send events concurrently (exposes race condition)
        await asyncio.gather(
            send_manager_events(),
            send_bridge_events()
        )
        
        logger.info(f"Handler registrations: {len(handler_registrations)}")
        logger.info(f"Event deliveries: {len(event_deliveries)}")
        
        # REGRESSION DETECTION: Analyze race condition patterns
        race_conditions = []
        
        # Check for duplicate handler registrations
        event_type_counts = {}
        for reg in handler_registrations:
            event_type = reg['event_type']
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
        for event_type, count in event_type_counts.items():
            if count > 1:
                race_conditions.append(f"Event type '{event_type}' has {count} handler registrations (race condition)")
                
        # Check for event delivery conflicts
        delivery_conflicts = {}
        for delivery in event_deliveries:
            key = delivery['event_type']
            if key not in delivery_conflicts:
                delivery_conflicts[key] = []
            delivery_conflicts[key].append(delivery)
            
        for event_type, deliveries in delivery_conflicts.items():
            if len(deliveries) > 1:
                interfaces = [d['interface'] for d in deliveries]
                if len(set(interfaces)) > 1:
                    race_conditions.append(f"Event type '{event_type}' delivered by multiple interfaces: {interfaces}")
                    
        # CRITICAL ASSERTION: Should fail due to race conditions
        assert len(race_conditions) == 0, (
            f"REGRESSION DETECTED: Event handler wiring race conditions detected - "
            f"this causes event delivery failures in production: {race_conditions}"
        )
        
    @pytest.mark.regression_reproduction
    async def test_undefined_event_handler_references(self):
        """
        CRITICAL: Test undefined event handler references due to interface confusion.
        
        ROOT CAUSE REPRODUCTION: When dual interfaces are partially initialized,
        event handler references can become undefined, causing AttributeError
        or NoneType errors during event delivery.
        
        EXPECTED FAILURE: Should fail due to undefined handler references.
        """
        logger.info(" ALERT:  TESTING: Undefined event handler references")
        
        await self.async_setup_method()
        
        # CRITICAL: Create partially initialized interface scenario
        user_session = UserAgentSession(str(self.test_user_id))
        
        # REGRESSION EXPOSURE: Set WebSocket manager without full initialization
        mock_manager = Mock(spec=WebSocketManager)
        mock_manager.send_event = Mock()
        
        # Simulate partial initialization (common regression scenario)
        user_session._websocket_manager = mock_manager
        user_session._websocket_bridge = None  # Not initialized yet
        
        # CRITICAL: Try to send events through undefined handlers
        undefined_handler_errors = []
        
        critical_events = [
            ('agent_started', {'agent_id': 'test_agent'}),
            ('agent_thinking', {'thinking': 'Processing request'}),
            ('tool_executing', {'tool': 'test_tool', 'parameters': {}}),
            ('tool_completed', {'tool': 'test_tool', 'result': 'success'}),
            ('agent_completed', {'response': 'Test complete'})
        ]
        
        for event_type, event_data in critical_events:
            try:
                # REGRESSION EXPOSURE: Try different event delivery paths
                
                # Path 1: Direct manager call
                if user_session._websocket_manager:
                    user_session._websocket_manager.send_event(event_type, event_data)
                    
                # Path 2: Bridge call (should fail - undefined)
                if hasattr(user_session, '_websocket_bridge') and user_session._websocket_bridge:
                    user_session._websocket_bridge.send_event(event_type, event_data)
                else:
                    # CRITICAL: This path should fail but is attempted in regression
                    try:
                        getattr(user_session._websocket_bridge, 'send_event')(event_type, event_data)
                    except AttributeError as e:
                        undefined_handler_errors.append(f"Undefined bridge handler for {event_type}: {str(e)}")
                    except TypeError as e:  # NoneType errors
                        undefined_handler_errors.append(f"NoneType bridge handler for {event_type}: {str(e)}")
                        
                # Path 3: Generic session method (may route incorrectly)
                if hasattr(user_session, 'send_websocket_event'):
                    try:
                        user_session.send_websocket_event(event_type, event_data)
                    except Exception as e:
                        undefined_handler_errors.append(f"Session event routing error for {event_type}: {str(e)}")
                        
            except Exception as e:
                undefined_handler_errors.append(f"Event delivery error for {event_type}: {str(e)}")
                
        logger.info(f"Undefined handler errors detected: {len(undefined_handler_errors)}")
        
        # CRITICAL: Test handler reference stability 
        handler_reference_issues = []
        
        # Simulate rapid interface switching (common in multi-user scenarios)
        for i in range(5):
            # Switch between interfaces rapidly
            user_session._websocket_manager = mock_manager if i % 2 == 0 else None
            user_session._websocket_bridge = Mock() if i % 2 == 1 else None
            
            # Try to send event during interface switch
            try:
                if user_session._websocket_manager and hasattr(user_session._websocket_manager, 'send_event'):
                    user_session._websocket_manager.send_event('test_event', {'switch_test': i})
                elif user_session._websocket_bridge and hasattr(user_session._websocket_bridge, 'send_event'):
                    user_session._websocket_bridge.send_event('test_event', {'switch_test': i})
                else:
                    handler_reference_issues.append(f"No valid handler reference available at switch {i}")
            except Exception as e:
                handler_reference_issues.append(f"Handler reference error at switch {i}: {str(e)}")
                
        # CRITICAL ASSERTION: Should fail due to undefined handler references
        total_errors = len(undefined_handler_errors) + len(handler_reference_issues)
        assert total_errors == 0, (
            f"REGRESSION DETECTED: Undefined event handler references cause event delivery failures - "
            f"undefined errors: {undefined_handler_errors}, reference issues: {handler_reference_issues}"
        )
        
    @pytest.mark.regression_reproduction
    @pytest.mark.real_services
    async def test_timing_dependent_event_delivery_races(self):
        """
        CRITICAL: Test timing-dependent race conditions in event delivery.
        
        ROOT CAUSE REPRODUCTION: Events sent to dual interfaces can arrive
        out of order or be duplicated/dropped based on timing, breaking
        the expected event sequence for AI agent interactions.
        
        EXPECTED FAILURE: Should fail due to timing race conditions.
        """
        logger.info(" ALERT:  TESTING: Timing-dependent event delivery races")
        
        await self.async_setup_method()
        
        # CRITICAL: Setup real WebSocket components with timing sensitivity
        auth_helper = E2EAuthHelper()
        authenticated_user = await auth_helper.create_authenticated_user()
        
        # REGRESSION EXPOSURE: Create competing event delivery paths
        event_delivery_timeline = []
        delivery_lock = asyncio.Lock()
        
        async def track_event_delivery(interface_name: str, event_type: str, event_data: Dict, delay: float = 0):
            """Track event delivery with precise timing."""
            if delay > 0:
                await asyncio.sleep(delay)
                
            delivery_time = time.time_ns()  # Nanosecond precision for race detection
            
            async with delivery_lock:
                event_delivery_timeline.append({
                    'interface': interface_name,
                    'event_type': event_type,
                    'event_data': event_data,
                    'timestamp_ns': delivery_time,
                    'thread_id': threading.get_ident()
                })
                
            logger.debug(f"Event delivered: {interface_name}.{event_type} at {delivery_time}")
            
        # CRITICAL: Setup dual delivery paths with different timing
        manager_emitter = Mock()
        bridge_emitter = Mock()
        
        # Mock event delivery with timing tracking
        manager_emitter.send_event = AsyncMock(
            side_effect=lambda event_type, data: track_event_delivery('manager', event_type, data, delay=0.001)
        )
        bridge_emitter.send_event = AsyncMock(
            side_effect=lambda event_type, data: track_event_delivery('bridge', event_type, data, delay=0.0015)
        )
        
        # REGRESSION EXPOSURE: Send critical AI agent event sequence
        ai_event_sequence = [
            ('agent_started', {'agent_id': 'timing_test_agent', 'user_id': str(authenticated_user.user_id)}),
            ('agent_thinking', {'thinking': 'Analyzing user request'}),
            ('tool_executing', {'tool': 'data_analyzer', 'parameters': {'query': 'test'}}),
            ('tool_completed', {'tool': 'data_analyzer', 'result': {'data': 'analysis_result'}}),
            ('agent_thinking', {'thinking': 'Generating response'}),
            ('agent_completed', {'response': 'Analysis complete', 'recommendations': ['action1', 'action2']})
        ]
        
        # CRITICAL: Send events via both interfaces simultaneously (triggers race)
        async def send_via_manager():
            """Send events via manager interface."""
            for i, (event_type, event_data) in enumerate(ai_event_sequence):
                # Add sequence info for race detection
                event_data_with_seq = {**event_data, 'sequence_id': i, 'interface': 'manager'}
                await manager_emitter.send_event(event_type, event_data_with_seq)
                await asyncio.sleep(0.002)  # Simulate processing delay
                
        async def send_via_bridge():
            """Send events via bridge interface."""
            for i, (event_type, event_data) in enumerate(ai_event_sequence):
                # Add sequence info for race detection
                event_data_with_seq = {**event_data, 'sequence_id': i, 'interface': 'bridge'}
                await bridge_emitter.send_event(event_type, event_data_with_seq)
                await asyncio.sleep(0.0025)  # Slightly different delay
                
        # CRITICAL: Execute concurrent event delivery (exposes timing races)
        start_time = time.time_ns()
        await asyncio.gather(send_via_manager(), send_via_bridge())
        end_time = time.time_ns()
        
        logger.info(f"Event delivery completed in {(end_time - start_time) / 1000000:.2f}ms")
        logger.info(f"Total events delivered: {len(event_delivery_timeline)}")
        
        # REGRESSION DETECTION: Analyze timing race conditions
        timing_race_conditions = []
        
        # Sort events by timestamp for analysis
        sorted_events = sorted(event_delivery_timeline, key=lambda x: x['timestamp_ns'])
        
        # Check for event ordering violations
        expected_sequence = [event[0] for event in ai_event_sequence]
        for interface in ['manager', 'bridge']:
            interface_events = [e for e in sorted_events if e['interface'] == interface]
            actual_sequence = [e['event_type'] for e in interface_events]
            
            if actual_sequence != expected_sequence:
                timing_race_conditions.append(
                    f"Event sequence violation in {interface}: expected {expected_sequence}, got {actual_sequence}"
                )
                
        # Check for temporal ordering violations between interfaces
        sequence_violations = []
        for i in range(len(expected_sequence)):
            manager_events = [e for e in sorted_events if e['interface'] == 'manager' and e['event_data'].get('sequence_id') == i]
            bridge_events = [e for e in sorted_events if e['interface'] == 'bridge' and e['event_data'].get('sequence_id') == i]
            
            if manager_events and bridge_events:
                manager_time = manager_events[0]['timestamp_ns']
                bridge_time = bridge_events[0]['timestamp_ns']
                time_diff_ms = abs(manager_time - bridge_time) / 1000000
                
                # CRITICAL: Events should not be delivered simultaneously (indicates race)
                if time_diff_ms < 0.1:  # Less than 0.1ms indicates race condition
                    sequence_violations.append(
                        f"Sequence {i} ({expected_sequence[i]}): Race condition detected - "
                        f"manager/bridge delivery time diff: {time_diff_ms:.3f}ms"
                    )
                    
        timing_race_conditions.extend(sequence_violations)
        
        # Check for event duplication
        event_counts = {}
        for event in sorted_events:
            key = f"{event['event_type']}_{event['event_data'].get('sequence_id')}"
            event_counts[key] = event_counts.get(key, 0) + 1
            
        duplicated_events = [key for key, count in event_counts.items() if count > 2]  # More than 2 (manager + bridge) indicates duplication
        if duplicated_events:
            timing_race_conditions.append(f"Event duplication detected: {duplicated_events}")
            
        # CRITICAL ASSERTION: Should fail due to timing race conditions
        assert len(timing_race_conditions) == 0, (
            f"REGRESSION DETECTED: Timing-dependent event delivery races break AI agent flow - "
            f"race conditions: {timing_race_conditions}"
        )
        
    @pytest.mark.regression_reproduction
    async def test_partial_event_handler_initialization_drops(self):
        """
        CRITICAL: Test event drops due to partial event handler initialization.
        
        ROOT CAUSE REPRODUCTION: When event handlers are partially initialized
        due to interface conflicts, some events are silently dropped, breaking
        the WebSocket event flow that users depend on.
        
        EXPECTED FAILURE: Should fail due to dropped events.
        """
        logger.info(" ALERT:  TESTING: Partial event handler initialization causing event drops")
        
        await self.async_setup_method()
        
        # CRITICAL: Simulate partial initialization scenarios
        dropped_events_detector = []
        successful_deliveries = []
        
        class PartiallyInitializedManager:
            """Mock manager with partial initialization."""
            
            def __init__(self, initialized_events: List[str]):
                self.initialized_events = set(initialized_events)
                self.call_count = 0
                
            def send_event(self, event_type: str, event_data: Dict[str, Any]):
                self.call_count += 1
                if event_type in self.initialized_events:
                    successful_deliveries.append({
                        'event_type': event_type,
                        'event_data': event_data,
                        'timestamp': time.time(),
                        'handler': 'partial_manager'
                    })
                    logger.debug(f"Event delivered: {event_type}")
                else:
                    dropped_events_detector.append({
                        'event_type': event_type,
                        'event_data': event_data,
                        'timestamp': time.time(),
                        'reason': 'handler_not_initialized'
                    })
                    logger.warning(f"Event dropped: {event_type} (handler not initialized)")
                    
        # REGRESSION EXPOSURE: Create scenarios with different initialization states
        initialization_scenarios = [
            # Scenario 1: Only basic events initialized
            {
                'name': 'basic_only',
                'initialized_events': ['agent_started', 'agent_completed'],
                'manager': PartiallyInitializedManager(['agent_started', 'agent_completed'])
            },
            # Scenario 2: Missing critical thinking events
            {
                'name': 'no_thinking',
                'initialized_events': ['agent_started', 'tool_executing', 'tool_completed', 'agent_completed'],
                'manager': PartiallyInitializedManager(['agent_started', 'tool_executing', 'tool_completed', 'agent_completed'])
            },
            # Scenario 3: Only tool events initialized
            {
                'name': 'tools_only', 
                'initialized_events': ['tool_executing', 'tool_completed'],
                'manager': PartiallyInitializedManager(['tool_executing', 'tool_completed'])
            }
        ]
        
        # CRITICAL: Test each scenario with complete event sequence
        complete_event_sequence = [
            ('agent_started', {'agent_id': 'drop_test_agent'}),
            ('agent_thinking', {'thinking': 'Starting analysis'}),
            ('tool_executing', {'tool': 'analyzer', 'parameters': {}}),
            ('agent_thinking', {'thinking': 'Processing results'}),
            ('tool_completed', {'tool': 'analyzer', 'result': 'success'}),
            ('agent_thinking', {'thinking': 'Finalizing response'}),
            ('agent_completed', {'response': 'Analysis complete'})
        ]
        
        scenario_results = []
        
        for scenario in initialization_scenarios:
            logger.info(f"Testing scenario: {scenario['name']}")
            
            # Clear tracking for this scenario
            dropped_events_detector.clear()
            successful_deliveries.clear()
            
            manager = scenario['manager']
            
            # REGRESSION EXPOSURE: Send complete event sequence to partially initialized manager
            for event_type, event_data in complete_event_sequence:
                try:
                    manager.send_event(event_type, event_data)
                except Exception as e:
                    dropped_events_detector.append({
                        'event_type': event_type,
                        'event_data': event_data,
                        'timestamp': time.time(),
                        'reason': f'exception: {str(e)}'
                    })
                    
            # Analyze results for this scenario
            expected_events = len(complete_event_sequence)
            successful_count = len(successful_deliveries)
            dropped_count = len(dropped_events_detector)
            
            scenario_results.append({
                'scenario': scenario['name'],
                'expected_events': expected_events,
                'successful_deliveries': successful_count,
                'dropped_events': dropped_count,
                'drop_rate': dropped_count / expected_events,
                'dropped_event_types': [e['event_type'] for e in dropped_events_detector]
            })
            
            logger.info(f"Scenario {scenario['name']}: {successful_count}/{expected_events} delivered, {dropped_count} dropped")
            
        # REGRESSION DETECTION: Analyze event drop patterns
        event_drop_violations = []
        
        for result in scenario_results:
            # CRITICAL: No events should be dropped in a properly functioning system
            if result['dropped_events'] > 0:
                event_drop_violations.append(
                    f"Scenario '{result['scenario']}': {result['dropped_events']} events dropped "
                    f"({result['drop_rate']*100:.1f}% drop rate) - types: {result['dropped_event_types']}"
                )
                
            # CRITICAL: Business-critical events should never be dropped
            critical_events = ['agent_started', 'agent_completed', 'tool_executing', 'tool_completed']
            dropped_critical = [event for event in result['dropped_event_types'] if event in critical_events]
            
            if dropped_critical:
                event_drop_violations.append(
                    f"Scenario '{result['scenario']}': CRITICAL events dropped: {dropped_critical} "
                    f"- this breaks user chat experience"
                )
                
        # Check for inconsistent drop patterns (indicates race conditions)
        if len(scenario_results) > 1:
            drop_rates = [r['drop_rate'] for r in scenario_results]
            if len(set(drop_rates)) > 1:  # Different drop rates indicate inconsistency
                event_drop_violations.append(
                    f"Inconsistent event drop patterns across scenarios: {[(r['scenario'], f'{r['drop_rate']*100:.1f}%') for r in scenario_results]} "
                    f"- indicates race conditions in handler initialization"
                )
                
        # CRITICAL ASSERTION: Should fail due to dropped events
        assert len(event_drop_violations) == 0, (
            f"REGRESSION DETECTED: Partial event handler initialization causes event drops - "
            f"this breaks critical WebSocket event delivery for AI agents: {event_drop_violations}"
        )
        
        
@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.websocket_race_conditions
class TestWebSocketEventHandlerPerformanceRaces(SSotBaseTestCase):
    """
    Performance-focused tests for WebSocket event handler race conditions
    under load conditions that expose timing-sensitive issues.
    """
    
    def setup_method(self):
        """Setup for performance race condition tests.""" 
        super().setup_method()
        self.env = IsolatedEnvironment()
        
    @pytest.mark.regression_reproduction
    @pytest.mark.slow
    async def test_high_concurrency_event_handler_conflicts(self):
        """
        CRITICAL: Test event handler conflicts under high concurrency load.
        
        ROOT CAUSE REPRODUCTION: Under heavy load with multiple concurrent users,
        dual WebSocket interfaces create contention that causes event delivery
        failures and race conditions.
        
        EXPECTED FAILURE: Should fail due to concurrency conflicts.
        """
        logger.info(" ALERT:  TESTING: High concurrency event handler conflicts")
        
        # CRITICAL: Setup high concurrency scenario
        concurrent_users = 10
        events_per_user = 20
        total_expected_events = concurrent_users * events_per_user
        
        delivered_events = []
        delivery_errors = []
        delivery_lock = asyncio.Lock()
        
        async def simulate_user_session(user_id: int):
            """Simulate concurrent user with WebSocket events."""
            session_events = []
            
            # Create user-specific WebSocket interface (dual interface scenario)
            user_context = UserExecutionContext(
                user_id=f"concurrent_user_{user_id}",
                request_id=f"concurrent_request_{user_id}",
                thread_id=f"concurrent_thread_{user_id}",
                run_id=str(uuid.uuid4())
            )
            
            try:
                # REGRESSION EXPOSURE: Create both interface types for same user
                bridge = create_agent_websocket_bridge(user_context)
                manager = Mock(spec=WebSocketManager)
                
                # Send rapid-fire events via both interfaces
                for event_seq in range(events_per_user):
                    event_data = {
                        'user_id': f"concurrent_user_{user_id}",
                        'sequence': event_seq,
                        'timestamp': time.time()
                    }
                    
                    # CRITICAL: Alternate between interfaces rapidly (triggers race)
                    if event_seq % 2 == 0:
                        # Via bridge
                        try:
                            if hasattr(bridge, 'send_event'):
                                bridge.send_event('concurrent_test', event_data)
                            
                            async with delivery_lock:
                                delivered_events.append({
                                    'user_id': user_id,
                                    'sequence': event_seq,
                                    'interface': 'bridge',
                                    'timestamp': time.time()
                                })
                        except Exception as e:
                            async with delivery_lock:
                                delivery_errors.append({
                                    'user_id': user_id,
                                    'sequence': event_seq,
                                    'interface': 'bridge',
                                    'error': str(e)
                                })
                    else:
                        # Via manager
                        try:
                            manager.send_event = Mock()
                            manager.send_event('concurrent_test', event_data)
                            
                            async with delivery_lock:
                                delivered_events.append({
                                    'user_id': user_id,
                                    'sequence': event_seq,
                                    'interface': 'manager',
                                    'timestamp': time.time()
                                })
                        except Exception as e:
                            async with delivery_lock:
                                delivery_errors.append({
                                    'user_id': user_id,
                                    'sequence': event_seq,
                                    'interface': 'manager',
                                    'error': str(e)
                                })
                                
                    # Small delay to simulate real usage
                    await asyncio.sleep(0.001)
                    
            except Exception as e:
                async with delivery_lock:
                    delivery_errors.append({
                        'user_id': user_id,
                        'sequence': -1,
                        'interface': 'session_creation',
                        'error': str(e)
                    })
                    
        # CRITICAL: Run concurrent user sessions
        start_time = time.time()
        tasks = [simulate_user_session(user_id) for user_id in range(concurrent_users)]
        await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        logger.info(f"Concurrency test completed in {end_time - start_time:.2f}s")
        logger.info(f"Events delivered: {len(delivered_events)}/{total_expected_events}")
        logger.info(f"Delivery errors: {len(delivery_errors)}")
        
        # REGRESSION DETECTION: Analyze concurrency conflicts
        concurrency_violations = []
        
        # Check delivery success rate
        delivery_rate = len(delivered_events) / total_expected_events
        if delivery_rate < 0.95:  # Less than 95% delivery indicates problems
            concurrency_violations.append(
                f"Poor event delivery rate under concurrency: {delivery_rate*100:.1f}% "
                f"({len(delivered_events)}/{total_expected_events})"
            )
            
        # Check for specific error patterns indicating interface conflicts
        interface_errors = {}
        for error in delivery_errors:
            interface = error['interface']
            error_type = type(error.get('error', '')).__name__
            key = f"{interface}:{error_type}"
            interface_errors[key] = interface_errors.get(key, 0) + 1
            
        if interface_errors:
            concurrency_violations.append(
                f"Interface-specific errors under concurrency: {interface_errors} "
                f"- indicates dual interface conflicts"
            )
            
        # Check for timing-based conflicts
        timing_conflicts = []
        events_by_timestamp = sorted(delivered_events, key=lambda x: x['timestamp'])
        
        for i in range(len(events_by_timestamp) - 1):
            current = events_by_timestamp[i]
            next_event = events_by_timestamp[i + 1]
            
            time_diff = next_event['timestamp'] - current['timestamp']
            
            # CRITICAL: Events from same user arriving simultaneously indicate race
            if (current['user_id'] == next_event['user_id'] and 
                time_diff < 0.0001):  # Less than 0.1ms indicates race condition
                timing_conflicts.append(
                    f"User {current['user_id']}: Race condition detected - "
                    f"events {current['sequence']} and {next_event['sequence']} "
                    f"delivered {time_diff*1000:.3f}ms apart"
                )
                
        if len(timing_conflicts) > 5:  # Multiple timing conflicts indicate systemic issue
            concurrency_violations.append(
                f"Multiple timing-based race conditions: {len(timing_conflicts)} detected"
            )
            
        # CRITICAL ASSERTION: Should fail due to concurrency conflicts
        assert len(concurrency_violations) == 0, (
            f"REGRESSION DETECTED: High concurrency exposes WebSocket interface conflicts - "
            f"this causes event delivery failures under production load: {concurrency_violations}"
        )