"""Agent WebSocket Bridge Integration Test Suite

MISSION: Create FAILING integration tests that demonstrate inconsistent WebSocket message
delivery behavior across different agents due to SSOT violations.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Integration Testing
- Business Goal: Chat UX Reliability & SSOT Compliance
- Value Impact: Consistent WebSocket behavior = Reliable chat experience = $500K+ ARR protection
- Strategic Impact: Integration-level violations cause real user-facing inconsistencies in chat

CRITICAL INTEGRATION FAILURES TO DETECT:
1. Different agents using different WebSocket delivery mechanisms
2. Inconsistent event timing and ordering between agent types
3. Message delivery failures when agents switch patterns
4. User isolation violations in multi-user scenarios
5. Event sequence inconsistencies across agent executions

INTEGRATION TEST STRATEGY:
- Test real agent instances (no Docker required)
- Use mock WebSocket connections to capture actual behavior
- Compare message delivery patterns across different agent types
- Focus on user-facing integration issues that affect chat UX
"""
import asyncio
import pytest
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.unified_tool_execution import EnhancedToolExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
from netra_backend.app.factories.websocket_bridge_factory import StandardWebSocketBridge

@dataclass
class WebSocketEventCapture:
    """Capture WebSocket events for analysis."""
    event_type: str
    agent_name: str
    timestamp: datetime
    data: Dict[str, Any]
    delivery_method: str
    user_id: str

class AgentWebSocketBridgeIntegrationTests(SSotAsyncTestCase):
    """Integration tests for WebSocket bridge patterns - MUST FAIL initially."""

    def setup_method(self, method):
        """Set up integration test fixtures."""
        super().setup_method(method)
        self.captured_events: List[WebSocketEventCapture] = []
        self.event_patterns: Dict[str, Set[str]] = {}
        self.delivery_inconsistencies: List[Dict] = []
        self.mock_websocket_manager = AsyncMock(spec=UnifiedWebSocketManager)
        self.mock_websocket_manager.send_event = AsyncMock(side_effect=self._capture_websocket_event)
        self.test_user_1 = self._create_test_user_context('user_1')
        self.test_user_2 = self._create_test_user_context('user_2')

    def teardown_method(self, method):
        """Clean up integration test fixtures."""
        super().teardown_method(method)

    def _create_test_user_context(self, user_id: str) -> UserExecutionContext:
        """Create test user execution context."""
        context = UserExecutionContext(user_id=user_id, thread_id=f'thread_{user_id}', run_id=f'run_{user_id}_{int(time.time())}', agent_context={'agent_name': 'test_agent'}, audit_metadata={})
        return context

    async def _capture_websocket_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Capture WebSocket events for analysis."""
        import traceback
        stack = traceback.format_stack()
        delivery_method = 'unknown'
        agent_name = data.get('agent_name', 'unknown')
        user_id = data.get('user_id', 'unknown')
        stack_str = ''.join(stack)
        if '_websocket_adapter.emit_' in stack_str:
            delivery_method = 'websocket_adapter'
        elif '_emit_websocket_event' in stack_str:
            delivery_method = 'direct_event'
        elif 'context.websocket_manager' in stack_str:
            delivery_method = 'context_manager'
        elif 'user_emitter.notify_' in stack_str:
            delivery_method = 'user_emitter'
        event = WebSocketEventCapture(event_type=event_type, agent_name=agent_name, timestamp=datetime.now(timezone.utc), data=data.copy(), delivery_method=delivery_method, user_id=user_id)
        self.captured_events.append(event)
        if agent_name not in self.event_patterns:
            self.event_patterns[agent_name] = set()
        self.event_patterns[agent_name].add(delivery_method)

    async def _create_base_agent_with_websocket(self, user_context: UserExecutionContext) -> BaseAgent:
        """Create BaseAgent instance with WebSocket bridge configured."""
        agent = BaseAgent()
        bridge = StandardWebSocketBridge(user_context)
        bridge.set_websocket_manager(self.mock_websocket_manager)
        agent._websocket_adapter = bridge
        agent._execution_context = user_context
        return agent

    async def _create_data_agent_with_websocket(self, user_context: UserExecutionContext) -> UnifiedDataAgent:
        """Create UnifiedDataAgent instance with WebSocket configured."""
        agent = UnifiedDataAgent()
        original_emit = agent._emit_websocket_event if hasattr(agent, '_emit_websocket_event') else None
        if original_emit:

            async def patched_emit(context, event_type, data):
                await self._capture_websocket_event(event_type, {**data, 'user_id': context.user_id, 'agent_name': 'UnifiedDataAgent'})
                return await original_emit(context, event_type, data)
            agent._emit_websocket_event = patched_emit
        return agent

    def test_detect_websocket_pattern_inconsistencies_across_agents(self):
        """TEST MUST FAIL: Detect inconsistent WebSocket patterns between agent types.

        Integration test that demonstrates different agents use different WebSocket
        delivery patterns, causing inconsistent behavior in chat UX.
        """

        async def run_integration_test():
            inconsistencies_detected = []
            try:
                base_agent = await self._create_base_agent_with_websocket(self.test_user_1)
                await base_agent.emit_agent_started('BaseAgent started')
                await base_agent.emit_thinking('BaseAgent thinking')
                await base_agent.emit_agent_completed({'result': 'BaseAgent completed'})
                data_agent = await self._create_data_agent_with_websocket(self.test_user_1)
                if hasattr(data_agent, '_emit_websocket_event'):
                    await data_agent._emit_websocket_event(self.test_user_1, 'agent_started', {'message': 'DataAgent started'})
                    await data_agent._emit_websocket_event(self.test_user_1, 'agent_thinking', {'thought': 'DataAgent thinking'})
                await asyncio.sleep(0.1)
                base_agent_patterns = self.event_patterns.get('unknown', set())
                data_agent_patterns = self.event_patterns.get('UnifiedDataAgent', set())
                all_patterns = set()
                for patterns in self.event_patterns.values():
                    all_patterns.update(patterns)
                if len(all_patterns) > 1:
                    inconsistencies_detected.append({'type': 'multiple_patterns', 'patterns_found': list(all_patterns), 'agent_patterns': dict(self.event_patterns)})
                if len(self.captured_events) > 1:
                    timing_gaps = []
                    for i in range(1, len(self.captured_events)):
                        gap_ms = (self.captured_events[i].timestamp - self.captured_events[i - 1].timestamp).total_seconds() * 1000
                        timing_gaps.append(gap_ms)
                    if max(timing_gaps) - min(timing_gaps) > 50:
                        inconsistencies_detected.append({'type': 'timing_inconsistency', 'timing_gaps': timing_gaps, 'events': [e.event_type for e in self.captured_events]})
            except Exception as e:
                inconsistencies_detected.append({'type': 'integration_failure', 'error': str(e)})
            return inconsistencies_detected
        inconsistencies = asyncio.run(run_integration_test())
        assert len(inconsistencies) == 0, f'WEBSOCKET INTEGRATION INCONSISTENCIES DETECTED: Found {len(inconsistencies)} integration-level inconsistencies between agent WebSocket patterns. Inconsistencies: {inconsistencies}. Captured events: {len(self.captured_events)}. Event patterns by agent: {dict(self.event_patterns)}. REMEDIATION REQUIRED: Standardize all agents to use consistent WebSocket pattern.'

    def test_detect_multi_user_websocket_isolation_violations(self):
        """TEST MUST FAIL: Detect WebSocket isolation violations in multi-user scenarios.

        Integration test that demonstrates user isolation failures when different
        agents use different WebSocket patterns for the same users.
        """

        async def run_multi_user_test():
            isolation_violations = []
            try:
                user1_base_agent = await self._create_base_agent_with_websocket(self.test_user_1)
                user2_base_agent = await self._create_base_agent_with_websocket(self.test_user_2)
                await asyncio.gather(user1_base_agent.emit_agent_started('User1 BaseAgent started'), user2_base_agent.emit_agent_started('User2 BaseAgent started'), user1_base_agent.emit_thinking('User1 BaseAgent thinking'), user2_base_agent.emit_thinking('User2 BaseAgent thinking'))
                await asyncio.sleep(0.1)
                user1_events = [e for e in self.captured_events if e.user_id == 'user_1']
                user2_events = [e for e in self.captured_events if e.user_id == 'user_2']
                if len(user1_events) == 0 or len(user2_events) == 0:
                    isolation_violations.append({'type': 'missing_user_events', 'user1_events': len(user1_events), 'user2_events': len(user2_events)})
                user1_patterns = set((e.delivery_method for e in user1_events))
                user2_patterns = set((e.delivery_method for e in user2_events))
                if user1_patterns != user2_patterns:
                    isolation_violations.append({'type': 'inconsistent_user_patterns', 'user1_patterns': list(user1_patterns), 'user2_patterns': list(user2_patterns)})
                user1_times = [e.timestamp for e in user1_events]
                user2_times = [e.timestamp for e in user2_events]
                if len(user1_times) > 0 and len(user2_times) > 0:
                    min_time_diff = min((abs((t1 - t2).total_seconds()) for t1 in user1_times for t2 in user2_times))
                    if min_time_diff < 0.001:
                        isolation_violations.append({'type': 'timing_synchronization_violation', 'min_time_diff_ms': min_time_diff * 1000})
            except Exception as e:
                isolation_violations.append({'type': 'multi_user_test_failure', 'error': str(e)})
            return isolation_violations
        violations = asyncio.run(run_multi_user_test())
        assert len(violations) == 0, f'MULTI-USER WEBSOCKET ISOLATION VIOLATIONS DETECTED: Found {len(violations)} user isolation violations in WebSocket event delivery. Violations: {violations}. Total events captured: {len(self.captured_events)}. REMEDIATION REQUIRED: Ensure WebSocket patterns maintain proper user isolation.'

    def test_detect_websocket_event_ordering_violations(self):
        """TEST MUST FAIL: Detect WebSocket event ordering violations between patterns.

        Integration test that demonstrates different WebSocket patterns deliver
        events in different orders, causing inconsistent chat UX.
        """

        async def run_event_ordering_test():
            ordering_violations = []
            try:
                base_agent = await self._create_base_agent_with_websocket(self.test_user_1)
                start_time = time.time()
                await base_agent.emit_agent_started('Agent started')
                await asyncio.sleep(0.01)
                await base_agent.emit_thinking('Agent thinking')
                await asyncio.sleep(0.01)
                await base_agent.emit_tool_executing('test_tool', {'param': 'value'})
                await asyncio.sleep(0.01)
                await base_agent.emit_tool_completed('test_tool', {'result': 'success'})
                await asyncio.sleep(0.01)
                await base_agent.emit_agent_completed({'final': 'result'})
                await asyncio.sleep(0.1)
                events = sorted(self.captured_events, key=lambda e: e.timestamp)
                expected_order = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                actual_order = [e.event_type for e in events]
                if actual_order != expected_order:
                    ordering_violations.append({'type': 'event_order_violation', 'expected_order': expected_order, 'actual_order': actual_order, 'events': [{'type': e.event_type, 'method': e.delivery_method} for e in events]})
                event_counts = {}
                for event in events:
                    key = event.event_type
                    event_counts[key] = event_counts.get(key, 0) + 1
                duplicates = {k: v for k, v in event_counts.items() if v > 1}
                if duplicates:
                    ordering_violations.append({'type': 'duplicate_events', 'duplicates': duplicates, 'total_events': len(events)})
                missing_events = set(expected_order) - set(actual_order)
                if missing_events:
                    ordering_violations.append({'type': 'missing_events', 'missing': list(missing_events), 'captured': actual_order})
            except Exception as e:
                ordering_violations.append({'type': 'event_ordering_test_failure', 'error': str(e)})
            return ordering_violations
        violations = asyncio.run(run_event_ordering_test())
        assert len(violations) == 0, f'WEBSOCKET EVENT ORDERING VIOLATIONS DETECTED: Found {len(violations)} event ordering violations in WebSocket delivery patterns. Violations: {violations}. REMEDIATION REQUIRED: Ensure consistent event ordering across all WebSocket patterns.'

    def test_detect_websocket_bridge_factory_integration_violations(self):
        """TEST MUST FAIL: Detect WebSocket bridge factory integration violations.

        Integration test that demonstrates problems when StandardWebSocketBridge
        switches between multiple adapter types during execution.
        """

        async def run_bridge_factory_test():
            factory_violations = []
            try:
                bridge = StandardWebSocketBridge(self.test_user_1)
                mock_agent_bridge = AsyncMock()
                mock_emitter = AsyncMock()
                bridge.set_websocket_manager(self.mock_websocket_manager)
                adapter_type_1 = bridge.get_active_adapter_type()
                bridge.set_agent_bridge(mock_agent_bridge)
                adapter_type_2 = bridge.get_active_adapter_type()
                bridge.set_websocket_emitter(mock_emitter)
                adapter_type_3 = bridge.get_active_adapter_type()
                unique_types = {adapter_type_1, adapter_type_2, adapter_type_3}
                unique_types.discard(None)
                if len(unique_types) > 1:
                    factory_violations.append({'type': 'multiple_adapter_types', 'adapter_types': list(unique_types), 'switches': 3})
                await bridge.notify_agent_started('test_run', 'test_agent', {'test': 'data'})
                if len(self.captured_events) == 0:
                    factory_violations.append({'type': 'adapter_switching_delivery_failure', 'final_adapter_type': bridge.get_active_adapter_type()})
            except Exception as e:
                factory_violations.append({'type': 'bridge_factory_test_failure', 'error': str(e)})
            return factory_violations
        violations = asyncio.run(run_bridge_factory_test())
        assert len(violations) == 0, f'WEBSOCKET BRIDGE FACTORY VIOLATIONS DETECTED: Found {len(violations)} integration violations in WebSocket bridge factory adapter switching. Violations: {violations}. REMEDIATION REQUIRED: Eliminate multiple adapter types from StandardWebSocketBridge.'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')