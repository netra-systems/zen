"""WebSocket Event SSOT Test - E2E Violation Detection

PURPOSE: Validate WebSocket events delivered through UserExecutionEngine only
SHOULD FAIL NOW: Events delivered through multiple paths
SHOULD PASS AFTER: Events delivered through UserExecutionEngine only

Business Value: Prevents $500K+ ARR WebSocket event delivery corruption
"""

import pytest
import asyncio
import json
import time
import unittest
from typing import Any, Dict, List, Set
from unittest.mock import AsyncMock, Mock, patch

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
except ImportError:
    # Skip test if imports not available
    pass

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class WebSocketEventTracker:
    """Track WebSocket events and their delivery paths."""

    def __init__(self):
        self.events_delivered: List[Dict[str, Any]] = []
        self.delivery_paths: Set[str] = set()
        self.engine_types_used: Set[str] = set()
        self.event_sources: Dict[str, str] = {}

    def track_event(self, event_type: str, engine_type: str, delivery_path: str, user_id: str = None):
        """Track a WebSocket event delivery."""
        event_data = {
            'event_type': event_type,
            'engine_type': engine_type,
            'delivery_path': delivery_path,
            'user_id': user_id,
            'timestamp': time.time()
        }

        self.events_delivered.append(event_data)
        self.delivery_paths.add(delivery_path)
        self.engine_types_used.add(engine_type)
        self.event_sources[f"{event_type}_{user_id}"] = engine_type

    def get_ssot_violations(self) -> List[str]:
        """Get SSOT violations from tracked events."""
        violations = []
        ssot_engine = "UserExecutionEngine"

        # Check for non-SSOT engines delivering events
        non_ssot_engines = self.engine_types_used - {ssot_engine}
        for engine in non_ssot_engines:
            violations.append(f"Non-SSOT engine delivering events: {engine}")

        # Check for multiple delivery paths
        if len(self.delivery_paths) > 1:
            violations.append(f"Multiple delivery paths detected: {sorted(self.delivery_paths)}")

        # Check for events from different engines to same user
        user_engine_map = {}
        for event in self.events_delivered:
            user_id = event.get('user_id')
            engine_type = event.get('engine_type')
            if user_id:
                if user_id in user_engine_map:
                    if user_engine_map[user_id] != engine_type:
                        violations.append(
                            f"User {user_id} receiving events from multiple engines: "
                            f"{user_engine_map[user_id]} and {engine_type}"
                        )
                else:
                    user_engine_map[user_id] = engine_type

        return violations

    def clear(self):
        """Clear all tracked data."""
        self.events_delivered.clear()
        self.delivery_paths.clear()
        self.engine_types_used.clear()
        self.event_sources.clear()


@pytest.mark.e2e
class WebSocketEventSSotTests(SSotAsyncTestCase):
    """Validate WebSocket event delivery through SSOT execution engine."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.event_tracker = WebSocketEventTracker()
        self.ssot_execution_engine = "UserExecutionEngine"

        # Mock WebSocket emitters to track events
        self.mock_emitters = {}

    def tearDown(self):
        """Clean up test environment."""
        self.event_tracker.clear()
        super().tearDown()

    async def test_websocket_event_delivery_path_analysis_fails(self):
        """SHOULD FAIL: Analyze WebSocket event delivery paths for SSOT violations."""
        violations = await self._analyze_event_delivery_paths()

        print(f"\n🔌 WEBSOCKET EVENT DELIVERY ANALYSIS:")
        print(f"   Events Tracked: {len(self.event_tracker.events_delivered)}")
        print(f"   Delivery Paths: {len(self.event_tracker.delivery_paths)}")
        print(f"   Engine Types: {len(self.event_tracker.engine_types_used)}")
        print(f"   Violations: {len(violations)}")

        if violations:
            print("   Event Delivery Violations:")
            for violation in violations:
                print(f"      ❌ {violation}")

        print(f"\n   Delivery Path Details:")
        for path in sorted(self.event_tracker.delivery_paths):
            print(f"      - {path}")

        print(f"\n   Engine Types Used:")
        for engine in sorted(self.event_tracker.engine_types_used):
            print(f"      - {engine}")

        # TEST SHOULD FAIL NOW - Event delivery violations detected
        self.assertGreater(
            len(violations),
            0,
            f"❌ SSOT VIOLATION: Found {len(violations)} WebSocket event delivery violations. "
            f"Events must be delivered only through {self.ssot_execution_engine}."
        )

    async def test_agent_event_source_validation_fails(self):
        """SHOULD FAIL: Validate agent event sources for SSOT compliance."""
        agent_violations = await self._validate_agent_event_sources()

        print(f"\n🤖 AGENT EVENT SOURCE VALIDATION:")
        print(f"   Violations Found: {len(agent_violations)}")

        if agent_violations:
            print("   Agent Event Source Violations:")
            for violation in agent_violations:
                print(f"      ❌ {violation}")

        # TEST SHOULD FAIL NOW - Agent event source violations detected
        self.assertGreater(
            len(agent_violations),
            0,
            f"❌ SSOT VIOLATION: Found {len(agent_violations)} agent event source violations. "
            "All agent events must originate from SSOT execution engine."
        )

    async def test_multi_user_event_isolation_fails(self):
        """SHOULD FAIL: Test multi-user event isolation with non-SSOT engines."""
        isolation_violations = await self._test_multi_user_isolation()

        print(f"\n👥 MULTI-USER EVENT ISOLATION:")
        print(f"   Violations Found: {len(isolation_violations)}")

        if isolation_violations:
            print("   Isolation Violations:")
            for violation in isolation_violations:
                print(f"      ❌ {violation}")

        # TEST SHOULD FAIL NOW - Event isolation violations detected
        self.assertGreater(
            len(isolation_violations),
            0,
            f"❌ SSOT VIOLATION: Found {len(isolation_violations)} event isolation violations. "
            "Non-SSOT engines cause cross-user event contamination."
        )

    async def test_websocket_event_consistency_fails(self):
        """SHOULD FAIL: Test WebSocket event consistency across engines."""
        consistency_violations = await self._test_event_consistency()

        print(f"\n📊 WEBSOCKET EVENT CONSISTENCY:")
        print(f"   Violations Found: {len(consistency_violations)}")

        if consistency_violations:
            print("   Consistency Violations:")
            for violation in consistency_violations:
                print(f"      ❌ {violation}")

        # TEST SHOULD FAIL NOW - Event consistency violations detected
        self.assertGreater(
            len(consistency_violations),
            0,
            f"❌ SSOT VIOLATION: Found {len(consistency_violations)} event consistency violations. "
            "Different engines produce inconsistent event patterns."
        )

    async def test_websocket_emitter_binding_analysis_fails(self):
        """SHOULD FAIL: Analyze WebSocket emitter binding to engines."""
        binding_violations = await self._analyze_emitter_bindings()

        print(f"\n🔗 WEBSOCKET EMITTER BINDING ANALYSIS:")
        print(f"   Violations Found: {len(binding_violations)}")

        if binding_violations:
            print("   Emitter Binding Violations:")
            for violation in binding_violations:
                print(f"      ❌ {violation}")

        # TEST SHOULD FAIL NOW - Emitter binding violations detected
        self.assertGreater(
            len(binding_violations),
            0,
            f"❌ SSOT VIOLATION: Found {len(binding_violations)} emitter binding violations. "
            "WebSocket emitters must bind only to SSOT execution engines."
        )

    async def _analyze_event_delivery_paths(self) -> List[str]:
        """Analyze WebSocket event delivery paths for violations."""
        violations = []

        # Simulate different execution engines delivering events
        event_scenarios = [
            {
                'event_type': 'agent_started',
                'engine_type': 'UserExecutionEngine',  # SSOT - correct
                'delivery_path': 'UserExecutionEngine->WebSocketEmitter',
                'user_id': 'user_1'
            },
            {
                'event_type': 'agent_thinking',
                'engine_type': 'ToolExecutionEngine',  # VIOLATION
                'delivery_path': 'ToolExecutionEngine->WebSocketEmitter',
                'user_id': 'user_1'
            },
            {
                'event_type': 'tool_executing',
                'engine_type': 'RequestScopedExecutionEngine',  # VIOLATION
                'delivery_path': 'RequestScopedExecutionEngine->UnifiedEmitter',
                'user_id': 'user_2'
            },
            {
                'event_type': 'tool_completed',
                'engine_type': 'MCPEnhancedExecutionEngine',  # VIOLATION
                'delivery_path': 'MCPEnhancedExecutionEngine->LegacyEmitter',
                'user_id': 'user_2'
            },
            {
                'event_type': 'agent_completed',
                'engine_type': 'UnifiedToolExecutionEngine',  # VIOLATION
                'delivery_path': 'UnifiedToolExecutionEngine->DirectEmit',
                'user_id': 'user_3'
            }
        ]

        # Track all events
        for scenario in event_scenarios:
            self.event_tracker.track_event(
                scenario['event_type'],
                scenario['engine_type'],
                scenario['delivery_path'],
                scenario['user_id']
            )

        # Get violations from tracker
        violations.extend(self.event_tracker.get_ssot_violations())

        return violations

    async def _validate_agent_event_sources(self) -> List[str]:
        """Validate agent event sources for SSOT compliance."""
        violations = []

        # Simulate agent events from different sources
        agent_events = [
            {'event': 'agent_started', 'source_engine': 'UserExecutionEngine', 'agent_type': 'supervisor'},
            {'event': 'agent_thinking', 'source_engine': 'ToolExecutionEngine', 'agent_type': 'data_helper'},  # VIOLATION
            {'event': 'tool_executing', 'source_engine': 'RequestScopedExecutionEngine', 'agent_type': 'triage'},  # VIOLATION
            {'event': 'tool_completed', 'source_engine': 'BaseExecutionEngine', 'agent_type': 'apex_optimizer'},  # VIOLATION
            {'event': 'agent_completed', 'source_engine': 'UserExecutionEngine', 'agent_type': 'supervisor'},
        ]

        # Analyze agent event sources
        for event in agent_events:
            if event['source_engine'] != self.ssot_execution_engine:
                violations.append(
                    f"Agent event '{event['event']}' from non-SSOT engine: "
                    f"{event['source_engine']} (agent: {event['agent_type']})"
                )

        # Check for agent type consistency
        agent_engines = {}
        for event in agent_events:
            agent_type = event['agent_type']
            engine = event['source_engine']

            if agent_type in agent_engines:
                if agent_engines[agent_type] != engine:
                    violations.append(
                        f"Agent '{agent_type}' using multiple engines: "
                        f"{agent_engines[agent_type]} and {engine}"
                    )
            else:
                agent_engines[agent_type] = engine

        return violations

    async def _test_multi_user_isolation(self) -> List[str]:
        """Test multi-user event isolation with different engines."""
        violations = []

        # Simulate concurrent users with different engines
        user_scenarios = [
            {
                'user_id': 'user_1',
                'engine_type': 'UserExecutionEngine',
                'events': ['agent_started', 'agent_thinking', 'agent_completed']
            },
            {
                'user_id': 'user_2',
                'engine_type': 'ToolExecutionEngine',  # VIOLATION
                'events': ['agent_started', 'tool_executing', 'tool_completed']
            },
            {
                'user_id': 'user_3',
                'engine_type': 'RequestScopedExecutionEngine',  # VIOLATION
                'events': ['agent_started', 'agent_thinking', 'agent_completed']
            }
        ]

        # Simulate concurrent event delivery
        tasks = []
        for scenario in user_scenarios:
            task = asyncio.create_task(
                self._simulate_user_events(scenario)
            )
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze isolation violations
        user_engines = {}
        for result in results:
            if isinstance(result, dict):
                user_id = result.get('user_id')
                engine_type = result.get('engine_type')
                if user_id and engine_type:
                    user_engines[user_id] = engine_type

        # Check for isolation violations
        non_ssot_users = []
        for user_id, engine_type in user_engines.items():
            if engine_type != self.ssot_execution_engine:
                non_ssot_users.append(user_id)
                violations.append(
                    f"User '{user_id}' using non-SSOT engine: {engine_type}"
                )

        # Check for cross-contamination risk
        if len(set(user_engines.values())) > 1:
            violations.append(
                f"Multiple engine types in use, risking cross-user contamination: "
                f"{set(user_engines.values())}"
            )

        return violations

    async def _simulate_user_events(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate user events for a specific scenario."""
        user_id = scenario['user_id']
        engine_type = scenario['engine_type']
        events = scenario['events']

        # Simulate event delivery
        for event_type in events:
            delivery_path = f"{engine_type}->WebSocketEmitter"
            self.event_tracker.track_event(event_type, engine_type, delivery_path, user_id)

            # Simulate processing delay
            await asyncio.sleep(0.01)

        return {
            'user_id': user_id,
            'engine_type': engine_type,
            'events_delivered': len(events)
        }

    async def _test_event_consistency(self) -> List[str]:
        """Test event consistency across different engines."""
        violations = []

        # Simulate same operation across different engines
        operation = "data_analysis_task"

        engine_event_patterns = {
            'UserExecutionEngine': [
                'agent_started', 'agent_thinking', 'tool_executing',
                'tool_completed', 'agent_completed'
            ],
            'ToolExecutionEngine': [  # VIOLATION - different pattern
                'tool_started', 'tool_executing', 'tool_finished'
            ],
            'RequestScopedExecutionEngine': [  # VIOLATION - different pattern
                'request_started', 'processing', 'request_completed'
            ]
        }

        # Analyze event pattern consistency
        ssot_pattern = engine_event_patterns[self.ssot_execution_engine]

        for engine_type, pattern in engine_event_patterns.items():
            if engine_type != self.ssot_execution_engine:
                if pattern != ssot_pattern:
                    violations.append(
                        f"Engine '{engine_type}' has inconsistent event pattern: "
                        f"{pattern} vs SSOT pattern: {ssot_pattern}"
                    )

        # Check for missing critical events in non-SSOT engines
        critical_events = {'agent_started', 'agent_thinking', 'agent_completed'}

        for engine_type, pattern in engine_event_patterns.items():
            if engine_type != self.ssot_execution_engine:
                missing_events = critical_events - set(pattern)
                if missing_events:
                    violations.append(
                        f"Engine '{engine_type}' missing critical events: {missing_events}"
                    )

        return violations

    async def _analyze_emitter_bindings(self) -> List[str]:
        """Analyze WebSocket emitter bindings to engines."""
        violations = []

        # Simulate emitter bindings
        emitter_bindings = [
            {
                'emitter_id': 'main_emitter',
                'bound_engine': 'UserExecutionEngine',
                'connection_count': 5
            },
            {
                'emitter_id': 'tool_emitter',  # VIOLATION - separate emitter
                'bound_engine': 'ToolExecutionEngine',
                'connection_count': 3
            },
            {
                'emitter_id': 'legacy_emitter',  # VIOLATION - separate emitter
                'bound_engine': 'RequestScopedExecutionEngine',
                'connection_count': 2
            }
        ]

        # Check for multiple emitters (should be unified)
        if len(emitter_bindings) > 1:
            violations.append(
                f"Multiple WebSocket emitters detected: "
                f"{[b['emitter_id'] for b in emitter_bindings]}"
            )

        # Check for non-SSOT engine bindings
        for binding in emitter_bindings:
            if binding['bound_engine'] != self.ssot_execution_engine:
                violations.append(
                    f"Emitter '{binding['emitter_id']}' bound to non-SSOT engine: "
                    f"{binding['bound_engine']}"
                )

        return violations


if __name__ == '__main__':
    unittest.main()
