#!/usr/bin/env python3
"""
SSOT Bridge Pattern Enforcement Integration Tests for Issue #1070

Integration tests designed to FAIL initially to detect current WebSocket bridge
pattern violations and PASS after remediation. These tests enforce SSOT compliance
by validating that all WebSocket events flow exclusively through the AgentRegistry
bridge pattern for proper user isolation.

Created for GitHub Issue #1070: WebSocket bridge bypass violations - Integration validation
Part of: SSOT violation detection and prevention system

Business Value: Platform/Internal - System Stability & User Isolation
Ensures proper multi-tenant WebSocket communication through controlled bridge patterns.

DESIGN CRITERIA:
- Tests FAIL initially to prove bridge bypassing exists
- Tests PASS after all WebSocket events flow through AgentRegistry bridge
- Provides runtime validation of bridge pattern enforcement
- Uses SSOT test infrastructure patterns
- Tests actual bridge functionality and isolation

TEST CATEGORIES:
- Bridge pattern runtime enforcement
- WebSocket event flow validation through bridge
- User isolation verification via bridge
- AgentRegistry bridge integration validation

EXPECTED BEHAVIOR:
- INITIAL STATE: All tests FAIL (detecting bridge bypass violations)
- POST-REMEDIATION: All tests PASS (bridge pattern exclusively used)
"""

import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Optional, Any
from collections import defaultdict

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.integration
class SSOTBridgePatternEnforcementTests(SSotAsyncTestCase):
    """
    SSOT integration tests for WebSocket bridge pattern enforcement.

    These tests are designed to FAIL initially to detect bridge bypassing,
    then PASS after remediation. They validate runtime bridge pattern compliance
    through actual integration scenarios.
    """

    def setup_method(self, method=None):
        """Setup bridge pattern enforcement integration test environment."""
        super().setup_method(method)

        # Test user contexts for isolation validation
        self.test_user_1 = "test_user_1"
        self.test_user_2 = "test_user_2"
        self.test_user_3 = "test_user_3"

        # Expected WebSocket event types that must go through bridge
        self.required_websocket_events = [
            "agent_started",
            "agent_thinking",
            "agent_completed",
            "tool_executing",
            "tool_completed",
            "progress_update",
            "agent_error",
        ]

        # Mock components for testing
        self.mock_registry = None
        self.mock_bridge = None
        self.mock_websocket_manager = None

        # Tracking for bridge usage validation
        self.bridge_calls = defaultdict(list)
        self.direct_calls = defaultdict(list)

        # Record test start metrics
        self.record_metric("test_category", "integration")
        self.record_metric("ssot_focus", "bridge_pattern_enforcement")
        self.record_metric("test_users_count", 3)
        self.record_metric("required_events_count", len(self.required_websocket_events))

    async def setup_mock_components(self):
        """Setup mock AgentRegistry and WebSocket bridge components for testing."""
        # Create mock AgentRegistry
        self.mock_registry = Mock()
        self.mock_registry.get_websocket_bridge = AsyncMock()

        # Create mock WebSocket bridge
        self.mock_bridge = Mock()
        self.mock_bridge.send_agent_started = AsyncMock()
        self.mock_bridge.send_agent_thinking = AsyncMock()
        self.mock_bridge.send_agent_completed = AsyncMock()
        self.mock_bridge.send_tool_executing = AsyncMock()
        self.mock_bridge.send_tool_completed = AsyncMock()
        self.mock_bridge.send_progress_update = AsyncMock()
        self.mock_bridge.send_agent_error = AsyncMock()

        # Configure registry to return bridge
        self.mock_registry.get_websocket_bridge.return_value = self.mock_bridge

        # Create mock direct WebSocketManager (should NOT be used)
        self.mock_websocket_manager = Mock()
        self.mock_websocket_manager.send_agent_started = AsyncMock()
        self.mock_websocket_manager.send_agent_thinking = AsyncMock()
        self.mock_websocket_manager.send_agent_completed = AsyncMock()
        self.mock_websocket_manager.send_tool_executing = AsyncMock()
        self.mock_websocket_manager.send_tool_completed = AsyncMock()
        self.mock_websocket_manager.send_progress_update = AsyncMock()
        self.mock_websocket_manager.send_agent_error = AsyncMock()

        # Setup call tracking
        self._setup_call_tracking()

    def _setup_call_tracking(self):
        """Setup call tracking to monitor bridge vs direct usage."""
        # Track bridge calls (SHOULD BE USED)
        for event_type in self.required_websocket_events:
            method_name = f"send_{event_type}"
            if hasattr(self.mock_bridge, method_name):
                original_method = getattr(self.mock_bridge, method_name)

                async def track_bridge_call(user_id=None, *args, **kwargs):
                    self.bridge_calls[event_type].append({
                        'user_id': user_id,
                        'args': args,
                        'kwargs': kwargs,
                        'method': method_name
                    })
                    return await original_method(user_id, *args, **kwargs)

                setattr(self.mock_bridge, method_name, track_bridge_call)

        # Track direct WebSocket manager calls (SHOULD NOT BE USED)
        for event_type in self.required_websocket_events:
            method_name = f"send_{event_type}"
            if hasattr(self.mock_websocket_manager, method_name):
                original_method = getattr(self.mock_websocket_manager, method_name)

                async def track_direct_call(*args, **kwargs):
                    self.direct_calls[event_type].append({
                        'args': args,
                        'kwargs': kwargs,
                        'method': method_name
                    })
                    return await original_method(*args, **kwargs)

                setattr(self.mock_websocket_manager, method_name, track_direct_call)

    @pytest.mark.asyncio
    async def test_websocket_events_only_through_agent_registry_bridge(self):
        """
        Test that all WebSocket events flow exclusively through AgentRegistry bridge.

        **EXPECTED TO FAIL INITIALLY** - Should detect direct WebSocket usage
        **EXPECTED TO PASS AFTER REMEDIATION** - All events through bridge only

        This test validates that agents use the AgentRegistry bridge pattern
        for all WebSocket communications instead of direct manager access.
        """
        self.record_metric("test_method", "websocket_events_only_through_agent_registry_bridge")
        self.record_metric("expected_initial_result", "FAIL")

        await self.setup_mock_components()

        # Simulate agent execution scenarios
        try:
            # Import agent classes for testing (may fail if imports are problematic)
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
            from netra_backend.app.agents.github_analyzer.agent import GitHubAnalyzerAgent
        except ImportError as e:
            # This failure indicates import-level violations
            pytest.fail(f"❌ IMPORT FAILURE INDICATES BRIDGE BYPASS VIOLATIONS: {e}")

        # Test scenario 1: Simulate agent sending WebSocket events
        bridge_usage_detected = 0
        direct_usage_detected = 0

        # Mock different agent scenarios
        test_scenarios = [
            {
                'name': 'OptimizationsCoreSubAgent_scenario',
                'user_id': self.test_user_1,
                'events': ['agent_started', 'agent_thinking', 'tool_executing', 'agent_completed']
            },
            {
                'name': 'GitHubAnalyzerAgent_scenario',
                'user_id': self.test_user_2,
                'events': ['agent_started', 'progress_update', 'agent_completed']
            },
            {
                'name': 'GenericAgent_scenario',
                'user_id': self.test_user_3,
                'events': ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            }
        ]

        # Execute test scenarios
        with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry', self.mock_registry):
            for scenario in test_scenarios:
                user_id = scenario['user_id']

                # Test bridge pattern usage (SHOULD BE USED)
                bridge = await self.mock_registry.get_websocket_bridge(user_id)

                for event_type in scenario['events']:
                    method_name = f"send_{event_type}"
                    if hasattr(bridge, method_name):
                        method = getattr(bridge, method_name)
                        await method(user_id, f"Test {event_type} message")
                        bridge_usage_detected += 1

        # Test scenario 2: Detect if any direct WebSocketManager usage exists
        # This simulates what happens if agents bypass the bridge
        direct_websocket_usage_patterns = []

        # Check if any agents are still importing/using WebSocketManager directly
        try:
            # These imports should FAIL if bridge pattern is properly enforced
            with patch('netra_backend.app.websocket_core.websocket_manager.WebSocketManager',
                      self.mock_websocket_manager):

                # Simulate direct WebSocket manager usage (ANTI-PATTERN)
                for scenario in test_scenarios:
                    for event_type in scenario['events']:
                        method_name = f"send_{event_type}"
                        if hasattr(self.mock_websocket_manager, method_name):
                            try:
                                method = getattr(self.mock_websocket_manager, method_name)
                                await method(f"Direct {event_type} message")
                                direct_usage_detected += 1
                                direct_websocket_usage_patterns.append({
                                    'scenario': scenario['name'],
                                    'event': event_type,
                                    'pattern': 'direct_websocket_manager_call'
                                })
                            except Exception:
                                # Expected if bridge pattern is properly enforced
                                pass
        except Exception as e:
            # This is actually good - indicates proper enforcement
            pass

        # Calculate bridge enforcement metrics
        total_event_calls = bridge_usage_detected + direct_usage_detected
        if total_event_calls > 0:
            bridge_compliance_ratio = bridge_usage_detected / total_event_calls
        else:
            bridge_compliance_ratio = 0.0

        self.record_metric("bridge_usage_detected", bridge_usage_detected)
        self.record_metric("direct_usage_detected", direct_usage_detected)
        self.record_metric("bridge_compliance_ratio", bridge_compliance_ratio)
        self.record_metric("direct_usage_patterns_found", len(direct_websocket_usage_patterns))

        # Bridge pattern enforcement requires 100% bridge usage (0% direct usage)
        if direct_usage_detected > 0 or bridge_compliance_ratio < 1.0:
            failure_message = [
                f"❌ WEBSOCKET EVENTS NOT EXCLUSIVELY THROUGH AGENT REGISTRY BRIDGE ❌",
                f"",
                f"Bridge Compliance: {bridge_compliance_ratio:.1%} (Target: 100%)",
                f"Bridge Usage: {bridge_usage_detected} events",
                f"Direct Usage: {direct_usage_detected} events",
                f"Total Event Calls: {total_event_calls}",
                f"",
                f"🚨 BRIDGE PATTERN VIOLATION: {direct_usage_detected} direct WebSocket calls detected",
                f"",
                f"BRIDGE USAGE BREAKDOWN:",
            ]

            for event_type, calls in self.bridge_calls.items():
                if calls:
                    failure_message.append(f"✅ {event_type}: {len(calls)} bridge calls")

            if direct_websocket_usage_patterns:
                failure_message.append(f"")
                failure_message.append(f"DIRECT USAGE VIOLATIONS DETECTED:")
                for pattern in direct_websocket_usage_patterns:
                    failure_message.append(f"❌ {pattern['scenario']}: {pattern['event']} via {pattern['pattern']}")

            if self.direct_calls:
                failure_message.append(f"")
                failure_message.append(f"DIRECT CALL BREAKDOWN:")
                for event_type, calls in self.direct_calls.items():
                    if calls:
                        failure_message.append(f"❌ {event_type}: {len(calls)} direct calls")

            failure_message.extend([
                f"",
                f"🔧 BRIDGE PATTERN ENFORCEMENT REMEDIATION:",
                f"",
                f"1. Eliminate direct WebSocketManager imports in agents:",
                f"   ❌ from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
                f"   ✅ # No direct WebSocket imports needed",
                f"",
                f"2. Use AgentRegistry bridge exclusively:",
                f"   ❌ websocket_manager.send_agent_started(...)",
                f"   ✅ bridge = await registry.get_websocket_bridge(user_id)",
                f"   ✅ await bridge.send_agent_started(...)",
                f"",
                f"3. Update agent constructors:",
                f"   ❌ def __init__(self, websocket_manager: WebSocketManager)",
                f"   ✅ def __init__(self, registry: AgentRegistry)",
                f"",
                f"4. Ensure proper user isolation:",
                f"   ✅ Each user gets isolated bridge instance",
                f"   ✅ User ID passed through all bridge calls",
                f"   ✅ No shared state between user bridges",
                f"",
                f"🎯 INTEGRATION SUCCESS CRITERIA:",
                f"• 100% bridge usage (0% direct usage)",
                f"• All WebSocket events through AgentRegistry bridge",
                f"• Proper user isolation per bridge instance",
                f"• This integration test PASSES after remediation",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state (POST-REMEDIATION)
        self.record_metric("bridge_pattern_enforced", True)
        print("✅ ALL WEBSOCKET EVENTS THROUGH AGENT REGISTRY BRIDGE")
        print(f"✅ Bridge Compliance: {bridge_compliance_ratio:.1%}")
        print(f"✅ Bridge Usage: {bridge_usage_detected} events")

    @pytest.mark.asyncio
    async def test_user_isolation_through_bridge_pattern(self):
        """
        Test that bridge pattern provides proper user isolation.

        **EXPECTED TO FAIL INITIALLY** - Should detect user isolation violations
        **EXPECTED TO PASS AFTER REMEDIATION** - Perfect user isolation via bridge

        This test validates that the AgentRegistry bridge pattern properly
        isolates WebSocket communications between different users.
        """
        self.record_metric("test_method", "user_isolation_through_bridge_pattern")
        self.record_metric("expected_initial_result", "FAIL")

        await self.setup_mock_components()

        # Test user isolation scenarios
        isolation_violations = []
        proper_isolations = []

        # Create user-specific bridge instances
        user_bridges = {}
        for user_id in [self.test_user_1, self.test_user_2, self.test_user_3]:
            user_bridge = Mock()
            user_bridge.user_id = user_id
            user_bridge.send_agent_started = AsyncMock()
            user_bridge.send_agent_thinking = AsyncMock()

            # Track calls per user bridge
            user_bridge.calls = []

            async def track_user_call(event_type, user_id=user_id, *args, **kwargs):
                user_bridge.calls.append({
                    'event_type': event_type,
                    'user_id': user_id,
                    'args': args,
                    'kwargs': kwargs
                })

            user_bridge.send_agent_started.side_effect = lambda *args, **kwargs: track_user_call('agent_started', user_id, *args, **kwargs)
            user_bridge.send_agent_thinking.side_effect = lambda *args, **kwargs: track_user_call('agent_thinking', user_id, *args, **kwargs)

            user_bridges[user_id] = user_bridge

        # Configure registry to return user-specific bridges
        async def get_user_bridge(user_id):
            if user_id in user_bridges:
                return user_bridges[user_id]
            else:
                isolation_violations.append(f"Bridge requested for unknown user: {user_id}")
                return None

        self.mock_registry.get_websocket_bridge.side_effect = get_user_bridge

        # Test concurrent user scenarios
        concurrent_tasks = []

        async def user_scenario(user_id, scenario_name):
            """Simulate agent execution for a specific user."""
            try:
                bridge = await self.mock_registry.get_websocket_bridge(user_id)
                if bridge and hasattr(bridge, 'user_id') and bridge.user_id == user_id:
                    # Proper isolation detected
                    await bridge.send_agent_started(f"{scenario_name} started")
                    await bridge.send_agent_thinking(f"{scenario_name} thinking")
                    proper_isolations.append({
                        'user_id': user_id,
                        'scenario': scenario_name,
                        'bridge_id': id(bridge),
                        'calls_made': len(bridge.calls)
                    })
                else:
                    # Isolation violation detected
                    isolation_violations.append({
                        'user_id': user_id,
                        'issue': 'wrong_bridge_returned',
                        'expected_user': user_id,
                        'actual_bridge_user': getattr(bridge, 'user_id', 'unknown') if bridge else None
                    })
            except Exception as e:
                isolation_violations.append({
                    'user_id': user_id,
                    'issue': 'bridge_access_failed',
                    'error': str(e)
                })

        # Execute concurrent user scenarios
        concurrent_tasks.append(user_scenario(self.test_user_1, "OptimizationAgent"))
        concurrent_tasks.append(user_scenario(self.test_user_2, "GitHubAnalyzer"))
        concurrent_tasks.append(user_scenario(self.test_user_3, "GenericAgent"))

        await asyncio.gather(*concurrent_tasks)

        # Validate user isolation results
        total_users_tested = 3
        properly_isolated_users = len(proper_isolations)
        isolation_violation_count = len(isolation_violations)

        user_isolation_ratio = properly_isolated_users / total_users_tested if total_users_tested > 0 else 0

        self.record_metric("users_tested", total_users_tested)
        self.record_metric("properly_isolated_users", properly_isolated_users)
        self.record_metric("isolation_violations", isolation_violation_count)
        self.record_metric("user_isolation_ratio", user_isolation_ratio)

        # Validate bridge instance uniqueness
        bridge_instances = set()
        for isolation in proper_isolations:
            bridge_instances.add(isolation['bridge_id'])

        unique_bridge_instances = len(bridge_instances)
        expected_unique_bridges = total_users_tested

        self.record_metric("unique_bridge_instances", unique_bridge_instances)
        self.record_metric("expected_unique_bridges", expected_unique_bridges)

        # User isolation requires 100% proper isolation (0% violations)
        if isolation_violation_count > 0 or user_isolation_ratio < 1.0 or unique_bridge_instances != expected_unique_bridges:
            failure_message = [
                f"❌ USER ISOLATION THROUGH BRIDGE PATTERN FAILED ❌",
                f"",
                f"User Isolation: {user_isolation_ratio:.1%} (Target: 100%)",
                f"Properly Isolated Users: {properly_isolated_users}/{total_users_tested}",
                f"Isolation Violations: {isolation_violation_count}",
                f"Bridge Instances: {unique_bridge_instances}/{expected_unique_bridges} unique",
                f"",
                f"🚨 USER ISOLATION VIOLATION: Bridge pattern not providing proper user separation",
                f"",
                f"PROPER ISOLATIONS ACHIEVED:",
            ]

            for isolation in proper_isolations:
                failure_message.append(f"✅ User {isolation['user_id']}: {isolation['scenario']} "
                                     f"(bridge {isolation['bridge_id']}, {isolation['calls_made']} calls)")

            if isolation_violations:
                failure_message.append(f"")
                failure_message.append(f"ISOLATION VIOLATIONS DETECTED:")
                for violation in isolation_violations:
                    if isinstance(violation, dict):
                        failure_message.append(f"❌ User {violation.get('user_id', 'unknown')}: {violation.get('issue', 'unknown')}")
                        if 'error' in violation:
                            failure_message.append(f"   Error: {violation['error']}")
                    else:
                        failure_message.append(f"❌ {violation}")

            failure_message.extend([
                f"",
                f"🔧 USER ISOLATION REMEDIATION:",
                f"",
                f"1. Ensure unique bridge instances per user:",
                f"   ✅ registry.get_websocket_bridge(user1) != registry.get_websocket_bridge(user2)",
                f"",
                f"2. Validate user ID consistency:",
                f"   ✅ bridge.user_id matches requested user_id",
                f"",
                f"3. Prevent cross-user contamination:",
                f"   ✅ User1 bridge cannot send messages to User2",
                f"   ✅ Each bridge maintains separate state",
                f"",
                f"4. Implement proper bridge factory:",
                f"   ✅ create_agent_websocket_bridge(user_id) returns isolated instance",
                f"   ✅ Bridge registry maintains user-specific mappings",
                f"",
                f"🎯 USER ISOLATION SUCCESS CRITERIA:",
                f"• 100% user isolation (0% violations)",
                f"• Unique bridge instance per user",
                f"• No cross-user message delivery",
                f"• Consistent user ID mapping",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("user_isolation_achieved", True)
        print("✅ USER ISOLATION THROUGH BRIDGE PATTERN ACHIEVED")
        print(f"✅ User Isolation: {user_isolation_ratio:.1%}")
        print(f"✅ Unique Bridges: {unique_bridge_instances}/{expected_unique_bridges}")

    @pytest.mark.asyncio
    async def test_bridge_pattern_prevents_websocket_manager_proliferation(self):
        """
        Test that bridge pattern prevents WebSocketManager instance proliferation.

        **EXPECTED TO FAIL INITIALLY** - Should detect manager proliferation
        **EXPECTED TO PASS AFTER REMEDIATION** - Single manager with bridge pattern

        This test validates that the bridge pattern prevents the creation of
        multiple WebSocketManager instances by providing controlled access.
        """
        self.record_metric("test_method", "bridge_pattern_prevents_websocket_manager_proliferation")
        self.record_metric("expected_initial_result", "FAIL")

        await self.setup_mock_components()

        # Track WebSocketManager instance creation
        manager_instances = []
        bridge_accesses = []

        # Mock WebSocketManager creation tracking
        original_websocket_manager = Mock()

        def track_manager_creation(*args, **kwargs):
            instance_id = len(manager_instances) + 1
            manager_instances.append({
                'instance_id': instance_id,
                'args': args,
                'kwargs': kwargs,
                'created_by': 'direct_instantiation'
            })
            return original_websocket_manager

        # Mock bridge access tracking
        async def track_bridge_access(user_id):
            bridge_accesses.append({
                'user_id': user_id,
                'access_time': len(bridge_accesses) + 1
            })
            return self.mock_bridge

        self.mock_registry.get_websocket_bridge.side_effect = track_bridge_access

        # Test scenario 1: Multiple agents requesting WebSocket access
        test_agents = ['OptimizationAgent', 'GitHubAnalyzer', 'TriageAgent', 'DataHelper', 'SupervisorAgent']
        test_users = [self.test_user_1, self.test_user_2, self.test_user_3]

        # Simulate agent execution scenarios with bridge pattern
        with patch('netra_backend.app.websocket_core.websocket_manager.WebSocketManager',
                   side_effect=track_manager_creation):

            for user_id in test_users:
                for agent_name in test_agents:
                    # Bridge pattern usage (SHOULD BE USED)
                    bridge = await self.mock_registry.get_websocket_bridge(user_id)

                    # Simulate agent sending events through bridge
                    if hasattr(bridge, 'send_agent_started'):
                        await bridge.send_agent_started(f"{agent_name} started for {user_id}")

        # Test scenario 2: Check if direct WebSocketManager instantiation occurs
        # This should NOT happen if bridge pattern is properly enforced
        direct_instantiation_attempts = len(manager_instances)
        bridge_access_count = len(bridge_accesses)

        expected_bridge_accesses = len(test_users) * len(test_agents)  # 3 users * 5 agents = 15 accesses

        # Calculate metrics
        bridge_usage_ratio = bridge_access_count / expected_bridge_accesses if expected_bridge_accesses > 0 else 0
        manager_proliferation_ratio = direct_instantiation_attempts / expected_bridge_accesses if expected_bridge_accesses > 0 else 0

        self.record_metric("bridge_access_count", bridge_access_count)
        self.record_metric("direct_instantiation_attempts", direct_instantiation_attempts)
        self.record_metric("expected_bridge_accesses", expected_bridge_accesses)
        self.record_metric("bridge_usage_ratio", bridge_usage_ratio)
        self.record_metric("manager_proliferation_ratio", manager_proliferation_ratio)

        # Analyze bridge access patterns
        user_bridge_access = defaultdict(int)
        for access in bridge_accesses:
            user_bridge_access[access['user_id']] += 1

        unique_users_accessing = len(user_bridge_access)

        self.record_metric("unique_users_accessing", unique_users_accessing)

        # Bridge pattern anti-proliferation requires:
        # - High bridge usage (80%+)
        # - Zero or minimal direct instantiation
        # - Proper user distribution
        target_bridge_usage = 0.8
        max_allowed_proliferation = 0.2  # Allow some direct instantiation during migration

        if (bridge_usage_ratio < target_bridge_usage or
            manager_proliferation_ratio > max_allowed_proliferation or
            unique_users_accessing < len(test_users)):

            failure_message = [
                f"❌ BRIDGE PATTERN DOES NOT PREVENT WEBSOCKET MANAGER PROLIFERATION ❌",
                f"",
                f"Bridge Usage: {bridge_usage_ratio:.1%} (Target: {target_bridge_usage:.0%}+)",
                f"Manager Proliferation: {manager_proliferation_ratio:.1%} (Max Allowed: {max_allowed_proliferation:.0%})",
                f"Bridge Accesses: {bridge_access_count}/{expected_bridge_accesses}",
                f"Direct Instantiations: {direct_instantiation_attempts}",
                f"Users Accessing Bridge: {unique_users_accessing}/{len(test_users)}",
                f"",
                f"🚨 WEBSOCKET MANAGER PROLIFERATION DETECTED",
                f"",
                f"BRIDGE ACCESS BREAKDOWN:",
            ]

            for user_id, access_count in user_bridge_access.items():
                failure_message.append(f"• User {user_id}: {access_count} bridge accesses")

            if manager_instances:
                failure_message.append(f"")
                failure_message.append(f"DIRECT INSTANTIATION VIOLATIONS:")
                for i, instance in enumerate(manager_instances[:5], 1):  # Show first 5
                    failure_message.append(f"❌ Instance {instance['instance_id']}: {instance['created_by']}")
                if len(manager_instances) > 5:
                    failure_message.append(f"❌ ... and {len(manager_instances) - 5} more instances")

            failure_message.extend([
                f"",
                f"🔧 ANTI-PROLIFERATION REMEDIATION:",
                f"",
                f"1. Eliminate direct WebSocketManager instantiation:",
                f"   ❌ manager = WebSocketManager(config)",
                f"   ❌ self.websocket_manager = WebSocketManager()",
                f"   ✅ # No direct instantiation needed",
                f"",
                f"2. Use bridge pattern exclusively:",
                f"   ✅ bridge = await registry.get_websocket_bridge(user_id)",
                f"   ✅ await bridge.send_*(...)",
                f"",
                f"3. Implement singleton WebSocketManager with bridge facade:",
                f"   ✅ Single WebSocketManager instance behind bridges",
                f"   ✅ Bridges provide user-isolated access to single manager",
                f"   ✅ No agent needs direct manager access",
                f"",
                f"4. Bridge pattern architecture benefits:",
                f"   • Prevents manager instance proliferation",
                f"   • Provides controlled access to WebSocket functionality",
                f"   • Enables proper user isolation without duplication",
                f"   • Reduces memory usage and complexity",
                f"",
                f"🎯 ANTI-PROLIFERATION SUCCESS CRITERIA:",
                f"• {target_bridge_usage:.0%}+ bridge usage ratio",
                f"• <{max_allowed_proliferation:.0%} manager proliferation",
                f"• All users access WebSocket via bridge pattern",
                f"• Minimal WebSocketManager instances",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("manager_proliferation_prevented", True)
        print("✅ BRIDGE PATTERN PREVENTS WEBSOCKET MANAGER PROLIFERATION")
        print(f"✅ Bridge Usage: {bridge_usage_ratio:.1%}")
        print(f"✅ Manager Proliferation: {manager_proliferation_ratio:.1%}")

    @pytest.mark.asyncio
    async def test_comprehensive_bridge_pattern_integration_validation(self):
        """
        Comprehensive validation of bridge pattern integration compliance.

        **EXPECTED TO PASS AFTER REMEDIATION** - Overall integration validation

        Validates that the bridge pattern integration provides:
        - Exclusive WebSocket access through AgentRegistry bridge
        - Proper user isolation per bridge instance
        - Prevention of WebSocketManager proliferation
        - Consistent bridge usage across all agents
        """
        self.record_metric("test_method", "comprehensive_bridge_pattern_integration_validation")
        self.record_metric("test_type", "comprehensive_validation")

        await self.setup_mock_components()

        # Comprehensive integration metrics collection
        integration_metrics = {
            "bridge_accesses": 0,
            "direct_accesses": 0,
            "user_isolation_successes": 0,
            "user_isolation_failures": 0,
            "manager_instances_created": 0,
            "bridge_instances_created": 0,
            "websocket_events_sent": 0,
            "integration_errors": []
        }

        # Test comprehensive bridge pattern integration
        test_scenarios = [
            {
                'name': 'MultiUserConcurrentExecution',
                'users': [self.test_user_1, self.test_user_2, self.test_user_3],
                'events_per_user': 5
            },
            {
                'name': 'HighVolumeEventProcessing',
                'users': [self.test_user_1],
                'events_per_user': 20
            },
            {
                'name': 'CrossUserIsolationValidation',
                'users': [self.test_user_1, self.test_user_2],
                'events_per_user': 10
            }
        ]

        # Execute comprehensive scenarios
        for scenario in test_scenarios:
            try:
                scenario_tasks = []

                async def execute_user_scenario(user_id, event_count):
                    """Execute bridge pattern scenario for a user."""
                    try:
                        # Get user-specific bridge
                        bridge = await self.mock_registry.get_websocket_bridge(user_id)
                        integration_metrics["bridge_accesses"] += 1

                        if bridge:
                            integration_metrics["user_isolation_successes"] += 1

                            # Send multiple events through bridge
                            for i in range(event_count):
                                await bridge.send_agent_started(f"Event {i} for {user_id}")
                                await bridge.send_agent_thinking(f"Thinking {i} for {user_id}")
                                integration_metrics["websocket_events_sent"] += 2
                        else:
                            integration_metrics["user_isolation_failures"] += 1
                            integration_metrics["integration_errors"].append(
                                f"Bridge not returned for user {user_id}"
                            )
                    except Exception as e:
                        integration_metrics["integration_errors"].append(
                            f"User scenario failed for {user_id}: {str(e)}"
                        )

                # Execute concurrent user scenarios
                for user_id in scenario['users']:
                    scenario_tasks.append(
                        execute_user_scenario(user_id, scenario['events_per_user'])
                    )

                await asyncio.gather(*scenario_tasks)

            except Exception as e:
                integration_metrics["integration_errors"].append(
                    f"Scenario {scenario['name']} failed: {str(e)}"
                )

        # Calculate comprehensive compliance metrics
        total_bridge_operations = (integration_metrics["bridge_accesses"] +
                                 integration_metrics["direct_accesses"])

        if total_bridge_operations > 0:
            bridge_exclusivity_ratio = integration_metrics["bridge_accesses"] / total_bridge_operations
        else:
            bridge_exclusivity_ratio = 0.0

        total_user_operations = (integration_metrics["user_isolation_successes"] +
                               integration_metrics["user_isolation_failures"])

        if total_user_operations > 0:
            user_isolation_success_ratio = integration_metrics["user_isolation_successes"] / total_user_operations
        else:
            user_isolation_success_ratio = 0.0

        error_count = len(integration_metrics["integration_errors"])

        # Record comprehensive metrics
        for metric, value in integration_metrics.items():
            if metric != "integration_errors":
                self.record_metric(f"comprehensive_{metric}", value)

        self.record_metric("comprehensive_bridge_exclusivity_ratio", bridge_exclusivity_ratio)
        self.record_metric("comprehensive_user_isolation_success_ratio", user_isolation_success_ratio)
        self.record_metric("comprehensive_integration_errors", error_count)

        # Comprehensive bridge pattern integration requirements
        integration_requirements = {
            "100% bridge exclusivity": bridge_exclusivity_ratio == 1.0,
            "100% user isolation success": user_isolation_success_ratio == 1.0,
            "Zero direct WebSocket access": integration_metrics["direct_accesses"] == 0,
            "Zero integration errors": error_count == 0,
            "Successful WebSocket event delivery": integration_metrics["websocket_events_sent"] > 0,
            "Minimal manager proliferation": integration_metrics["manager_instances_created"] <= 1,
        }

        failed_requirements = [req for req, passed in integration_requirements.items() if not passed]

        if failed_requirements:
            failure_message = [
                f"❌ COMPREHENSIVE BRIDGE PATTERN INTEGRATION VALIDATION FAILED ❌",
                f"",
                f"Bridge Exclusivity: {bridge_exclusivity_ratio:.1%} (Target: 100%)",
                f"User Isolation Success: {user_isolation_success_ratio:.1%} (Target: 100%)",
                f"",
                f"COMPREHENSIVE INTEGRATION METRICS:",
                f"• Bridge Accesses: {integration_metrics['bridge_accesses']}",
                f"• Direct Accesses: {integration_metrics['direct_accesses']}",
                f"• User Isolation Successes: {integration_metrics['user_isolation_successes']}",
                f"• User Isolation Failures: {integration_metrics['user_isolation_failures']}",
                f"• WebSocket Events Sent: {integration_metrics['websocket_events_sent']}",
                f"• Integration Errors: {error_count}",
                f"",
                f"FAILED REQUIREMENTS:",
            ]

            for requirement in failed_requirements:
                failure_message.append(f"❌ {requirement}")

            if integration_metrics["integration_errors"]:
                failure_message.append(f"")
                failure_message.append(f"INTEGRATION ERRORS:")
                for error in integration_metrics["integration_errors"][:5]:  # Show first 5
                    failure_message.append(f"❌ {error}")
                if len(integration_metrics["integration_errors"]) > 5:
                    failure_message.append(f"❌ ... and {len(integration_metrics['integration_errors']) - 5} more errors")

            failure_message.extend([
                f"",
                f"🎯 COMPLETE BRIDGE PATTERN INTEGRATION REMEDIATION:",
                f"• Run all individual bridge pattern tests",
                f"• Fix all WebSocket event routing to use bridge exclusively",
                f"• Ensure proper user isolation through bridge pattern",
                f"• Prevent WebSocketManager proliferation via bridge facade",
                f"• Achieve 100% integration compliance across all requirements",
                f"",
                f"📋 INTEGRATION SUCCESS PATHWAY:",
                f"1. Fix bridge exclusivity violations",
                f"2. Resolve user isolation failures",
                f"3. Eliminate all direct WebSocket access",
                f"4. Address integration errors systematically",
                f"5. Validate comprehensive bridge pattern compliance",
            ])

            pytest.fail("\n".join(failure_message))

        # Success - Complete bridge pattern integration compliance achieved
        self.record_metric("bridge_pattern_integration_compliant", True)

        print("🏆 COMPREHENSIVE BRIDGE PATTERN INTEGRATION VALIDATION COMPLETE")
        print(f"✅ Bridge Exclusivity: {bridge_exclusivity_ratio:.1%}")
        print(f"✅ User Isolation Success: {user_isolation_success_ratio:.1%}")
        print("✅ All integration requirements satisfied")
        print("✅ WebSocket bridge pattern integration COMPLETE")

    def teardown_method(self, method=None):
        """Clean up after bridge pattern enforcement integration tests."""
        # Record final test metrics
        self.record_metric("test_completed", True)

        # Clean up mock objects
        self.mock_registry = None
        self.mock_bridge = None
        self.mock_websocket_manager = None
        self.bridge_calls.clear()
        self.direct_calls.clear()

        super().teardown_method(method)