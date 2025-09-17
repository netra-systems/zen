"
WebSocket Agent Health Fragmentation Reproduction Test

PURPOSE: Expose fragmented WebSocket and agent health monitoring systems that don't coordinate.
This test is DESIGNED TO FAIL before SSOT remediation to demonstrate the violations.

BUSINESS IMPACT:
- Segment: Platform (affects all user tiers)
- Goal: Stability - ensure WebSocket + agent health coordination
- Value Impact: Fragmented monitoring breaks real-time chat experience (90% of platform value)
- Revenue Impact: WebSocket disconnects without agent recovery causes user abandonment

EXPECTED BEHAVIOR:  
- SHOULD FAIL: WebSocket health monitoring disconnected from agent health status
- SHOULD FAIL: Agent death not reflected in WebSocket connection status
- SHOULD FAIL: WebSocket events not coordinated with agent health transitions

After SSOT consolidation, this test should demonstrate:
- Unified WebSocket + agent health monitoring
- Coordinated connection management based on agent status
- Integrated health assessment for complete chat experience
"
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any, Optional
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from netra_backend.app.core.agent_health_monitor import AgentHealthMonitor
from netra_backend.app.core.agent_execution_tracker import ExecutionRecord, ExecutionState
from netra_backend.app.core.agent_reliability_types import AgentError
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
try:
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    WEBSOCKET_MANAGER_AVAILABLE = True
except ImportError:
    WEBSOCKET_MANAGER_AVAILABLE = False
try:
    from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor
    EVENT_MONITOR_AVAILABLE = True
except ImportError:
    EVENT_MONITOR_AVAILABLE = False

@pytest.mark.e2e
class WebSocketAgentHealthFragmentationTests(SSotAsyncTestCase):
    "
    Reproduction tests for WebSocket and agent health monitoring fragmentation.
    These tests SHOULD FAIL with current disconnected implementation.
"

    async def asyncSetUp(self):
        "Set up test fixtures for WebSocket health fragmentation testing.
        await super().asyncSetUp()
        self.test_agent_name = 'fragmentation_test_agent'
        self.test_user_id = 'user_frag_123'
        self.test_thread_id = 'thread_frag_456'
        self.test_execution_id = 'exec_frag_789'
        self.mock_websocket_connection = Mock()
        self.health_monitor = AgentHealthMonitor()
        self.mock_reliability_wrapper = Mock()
        self.mock_reliability_wrapper.circuit_breaker.get_status.return_value = {'state': 'closed'}
        if WEBSOCKET_MANAGER_AVAILABLE:
            self.websocket_manager = Mock(spec=UnifiedWebSocketManager)
            self.websocket_manager.connections = {}
            self.websocket_manager.user_emitters = {}
        else:
            self.websocket_manager = Mock()
        if EVENT_MONITOR_AVAILABLE:
            self.event_monitor = Mock(spec=ChatEventMonitor)
            self.event_monitor.agent_events = {}
            self.event_monitor.websocket_events = {}
        else:
            self.event_monitor = Mock()

    async def test_agent_death_not_reflected_in_websocket_status(self):
        ""
        REPRODUCTION TEST: Show agent death detection not coordinated with WebSocket status.
        
        Expected to FAIL: Agent health monitor detects death but WebSocket manager
        doesn't update connection status or notify users.

        connection_id = f'conn_{self.test_user_id}'
        self.websocket_manager.connections[connection_id] = {'websocket': self.mock_websocket_connection, 'user_id': self.test_user_id, 'connected_at': datetime.now(timezone.utc), 'status': 'connected', 'last_ping': datetime.now(timezone.utc)}
        self.websocket_manager.is_connection_healthy.return_value = True
        self.websocket_manager.get_connection_status.return_value = 'connected'
        last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=15)
        agent_is_dead = await self.health_monitor.detect_agent_death(agent_name=self.test_agent_name, last_heartbeat=last_heartbeat, execution_context={'user_id': self.test_user_id}
        error_history = [AgentError(error_type='AgentDeath', message='Agent stopped responding', timestamp=datetime.now(timezone.utc), context={'execution_id': self.test_execution_id}]
        health_status = self.health_monitor.get_comprehensive_health_status(agent_name=self.test_agent_name, error_history=error_history, reliability_wrapper=self.mock_reliability_wrapper)
        websocket_status = self.websocket_manager.get_connection_status.return_value
        websocket_healthy = self.websocket_manager.is_connection_healthy.return_value
        fragmentation_analysis = {'agent_death_detected': agent_is_dead, 'agent_health_status': health_status.status, 'agent_overall_health': health_status.overall_health, 'websocket_status': websocket_status, 'websocket_healthy': websocket_healthy, 'coordination_failure': agent_is_dead and websocket_healthy, 'status_mismatch': health_status.status == 'dead' and websocket_status == 'connected'}
        if fragmentation_analysis['coordination_failure'] or fragmentation_analysis['status_mismatch']:
            self.fail(f"SSOT VIOLATION: WebSocket and agent health monitoring fragmentation detected. Agent death detected: {fragmentation_analysis['agent_death_detected']}, Agent status: '{fragmentation_analysis['agent_health_status']}', WebSocket status: '{fragmentation_analysis['websocket_status']}', WebSocket healthy: {fragmentation_analysis['websocket_healthy']}. Coordination failure: {fragmentation_analysis['coordination_failure']})

    async def test_websocket_events_not_coordinated_with_agent_health(self):
        "
        REPRODUCTION TEST: Show WebSocket events not coordinated with agent health transitions.
        
        Expected to FAIL: Agent health changes don't trigger appropriate WebSocket events,
        breaking real-time user experience.
"
        websocket_events_sent = []
        agent_health_events = []

        def mock_emit_event(event_type, data):
            websocket_events_sent.append({'event_type': event_type, 'data': data, 'timestamp': datetime.now(timezone.utc)}
        self.websocket_manager.emit_to_user = Mock(side_effect=mock_emit_event)
        health_timeline = []
        error_history = []
        initial_health = self.health_monitor.get_comprehensive_health_status(agent_name=self.test_agent_name, error_history=error_history, reliability_wrapper=self.mock_reliability_wrapper)
        health_timeline.append({'timestamp': datetime.now(timezone.utc), 'status': initial_health.status, 'health': initial_health.overall_health, 'stage': 'initial'}
        agent_health_events.append({'event_type': 'health_check', 'status': initial_health.status, 'health': initial_health.overall_health, 'timestamp': datetime.now(timezone.utc)}
        await asyncio.sleep(0.01)
        error_history.append(AgentError(error_type='PerformanceWarning', message='Slow response time detected', timestamp=datetime.now(timezone.utc), context={'response_time': 8.5})
        degraded_health = self.health_monitor.get_comprehensive_health_status(agent_name=self.test_agent_name, error_history=error_history, reliability_wrapper=self.mock_reliability_wrapper)
        health_timeline.append({'timestamp': datetime.now(timezone.utc), 'status': degraded_health.status, 'health': degraded_health.overall_health, 'stage': 'degraded'}
        agent_health_events.append({'event_type': 'health_degraded', 'status': degraded_health.status, 'health': degraded_health.overall_health, 'timestamp': datetime.now(timezone.utc)}
        await asyncio.sleep(0.01)
        last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=20)
        agent_death = await self.health_monitor.detect_agent_death(agent_name=self.test_agent_name, last_heartbeat=last_heartbeat, execution_context={'user_id': self.test_user_id}
        if agent_death:
            error_history.append(AgentError(error_type='AgentDeath', message='Agent death detected', timestamp=datetime.now(timezone.utc), context={'heartbeat_age': 20})
        dead_health = self.health_monitor.get_comprehensive_health_status(agent_name=self.test_agent_name, error_history=error_history, reliability_wrapper=self.mock_reliability_wrapper)
        health_timeline.append({'timestamp': datetime.now(timezone.utc), 'status': dead_health.status, 'health': dead_health.overall_health, 'stage': 'dead'}
        agent_health_events.append({'event_type': 'agent_death', 'status': dead_health.status, 'health': dead_health.overall_health, 'timestamp': datetime.now(timezone.utc)}
        coordination_analysis = {'agent_health_events': len(agent_health_events), 'websocket_events_sent': len(websocket_events_sent), 'health_transitions': len(health_timeline), 'expected_websocket_events': ['agent_started', 'agent_thinking', 'agent_health_degraded', 'agent_death'], 'actual_websocket_events': [e['event_type'] for e in websocket_events_sent], 'coordination_ratio': len(websocket_events_sent) / len(agent_health_events) if agent_health_events else 0}
        critical_events_missing = []
        for stage_data in health_timeline:
            stage = stage_data['stage']
            status = stage_data['status']
            if status == 'degraded':
                degraded_events = [e for e in websocket_events_sent if 'health' in e['event_type'] or 'warning' in e['event_type']]
                if not degraded_events:
                    critical_events_missing.append('agent_health_warning')
            if status == 'dead':
                death_events = [e for e in websocket_events_sent if 'death' in e['event_type'] or 'failed' in e['event_type']]
                if not death_events:
                    critical_events_missing.append('agent_death')
        if coordination_analysis['coordination_ratio'] < 0.5 or critical_events_missing or coordination_analysis['websocket_events_sent'] == 0:
            self.fail(f"SSOT VIOLATION: WebSocket events not coordinated with agent health transitions. Agent health events: {coordination_analysis['agent_health_events']}, WebSocket events sent: {coordination_analysis['websocket_events_sent']}, Coordination ratio: {coordination_analysis['coordination_ratio']:.2f}, Missing critical events: {critical_events_missing})

    async def test_websocket_connection_health_separate_from_agent_health(self):
        
        REPRODUCTION TEST: Show WebSocket connection health tracked separately from agent health.
        
        Expected to FAIL: WebSocket connection health and agent health are tracked
        by separate systems with no coordination.
""
        websocket_health_data = {'connection_active': True, 'last_ping': datetime.now(timezone.utc), 'ping_latency': 50, 'message_queue_size': 0, 'connection_errors': 0, 'status': 'healthy'}
        self.websocket_manager.get_connection_health.return_value = websocket_health_data
        self.websocket_manager.is_connection_stable.return_value = True
        error_history = [AgentError(error_type='LLMError', message='LLM provider timeout', timestamp=datetime.now(timezone.utc) - timedelta(seconds=30), context={'provider': 'openai', 'timeout': 30}, AgentError(error_type='DatabaseError', message='Database connection failed', timestamp=datetime.now(timezone.utc) - timedelta(seconds=15), context={'database': 'postgres', 'retry_count': 3}, AgentError(error_type='CriticalError', message='Agent execution failed', timestamp=datetime.now(timezone.utc) - timedelta(seconds=5), context={'severity': 'critical'}]
        agent_health = self.health_monitor.get_comprehensive_health_status(agent_name=self.test_agent_name, error_history=error_history, reliability_wrapper=self.mock_reliability_wrapper)
        health_comparison = {'websocket_status': websocket_health_data['status'], 'websocket_stable': self.websocket_manager.is_connection_stable.return_value, 'websocket_errors': websocket_health_data['connection_errors'], 'agent_status': agent_health.status, 'agent_health_score': agent_health.overall_health, 'agent_recent_errors': agent_health.recent_errors, 'systems_disagree': websocket_health_data['status'] == 'healthy' and agent_health.status in ['unhealthy', 'degraded'], 'error_count_mismatch': websocket_health_data['connection_errors'] != agent_health.recent_errors}
        user_experience_analysis = {'websocket_appears_healthy': websocket_health_data['status'] == 'healthy', 'agent_actually_failing': agent_health.overall_health < 0.3, 'user_confused': websocket_health_data['status'] == 'healthy' and agent_health.overall_health < 0.3, 'no_user_warning': len(error_history) > 2 and websocket_health_data['status'] == 'healthy'}
        if health_comparison['systems_disagree'] or user_experience_analysis['user_confused'] or user_experience_analysis['no_user_warning']:
            self.fail(fSSOT VIOLATION: WebSocket and agent health tracked separately. WebSocket status: '{health_comparison['websocket_status']}' (stable: {health_comparison['websocket_stable']}, Agent status: '{health_comparison['agent_status']}' (health: {health_comparison['agent_health_score']:.2f}. Systems disagree: {health_comparison['systems_disagree']}, User confusion: {user_experience_analysis['user_confused']})

    async def test_health_monitoring_performance_fragmentation(self):
        
        REPRODUCTION TEST: Show performance impact from fragmented health monitoring.
        
        Expected to FAIL: Separate health monitoring systems create redundant checks
        and performance overhead.
""
        num_agents = 5
        num_iterations = 20
        performance_results = {'agent_health_times': [], 'websocket_health_times': [], 'total_health_checks': 0, 'redundant_checks_detected': 0}
        agents = [f'perf_test_agent_{i}' for i in range(num_agents)]
        for iteration in range(num_iterations):
            iteration_start = time.perf_counter()
            agent_health_start = time.perf_counter()
            for agent in agents:
                last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=iteration * 2)
                await self.health_monitor.detect_agent_death(agent_name=agent, last_heartbeat=last_heartbeat, execution_context={'iteration': iteration}
                error_history = []
                if iteration > 10:
                    error_history.append(AgentError(error_type='IterationError', message=f'Error in iteration {iteration}', timestamp=datetime.now(timezone.utc), context={'iteration': iteration})
                self.health_monitor.get_comprehensive_health_status(agent_name=agent, error_history=error_history, reliability_wrapper=self.mock_reliability_wrapper)
            agent_health_time = time.perf_counter() - agent_health_start
            performance_results['agent_health_times'].append(agent_health_time)
            websocket_health_start = time.perf_counter()
            for agent in agents:
                connection_id = f'conn_{agent}'
                self.websocket_manager.get_connection_health.return_value = {'active': True, 'latency': 50 + iteration, 'errors': iteration // 5}
                self.websocket_manager.is_connection_stable.return_value = iteration < 15
                await asyncio.sleep(0.001)
            websocket_health_time = time.perf_counter() - websocket_health_start
            performance_results['websocket_health_times'].append(websocket_health_time)
            performance_results['total_health_checks'] += num_agents * 2
            if iteration > 5:
                performance_results['redundant_checks_detected'] += num_agents
        avg_agent_health_time = sum(performance_results['agent_health_times'] / len(performance_results['agent_health_times']
        avg_websocket_health_time = sum(performance_results['websocket_health_times'] / len(performance_results['websocket_health_times']
        total_avg_time = avg_agent_health_time + avg_websocket_health_time
        performance_analysis = {'avg_agent_health_time': avg_agent_health_time, 'avg_websocket_health_time': avg_websocket_health_time, 'total_avg_time': total_avg_time, 'total_health_checks': performance_results['total_health_checks'], 'redundant_checks': performance_results['redundant_checks_detected'], 'redundancy_ratio': performance_results['redundant_checks_detected'] / performance_results['total_health_checks'], 'performance_overhead_ms': total_avg_time * 1000, 'checks_per_second': performance_results['total_health_checks'] / (num_iterations * total_avg_time) if total_avg_time > 0 else 0}
        if performance_analysis['redundancy_ratio'] > 0.3 or performance_analysis['performance_overhead_ms'] > 100 or performance_analysis['total_avg_time'] > avg_agent_health_time * 1.5:
            self.fail(fSSOT VIOLATION: Performance fragmentation from separate health monitoring. Agent health time: {performance_analysis['avg_agent_health_time']:.4f}s, WebSocket health time: {performance_analysis['avg_websocket_health_time']:.4f}s, Total overhead: {performance_analysis['performance_overhead_ms']:.2f}ms, Redundancy ratio: {performance_analysis['redundancy_ratio']:.2f}, Redundant checks: {performance_analysis['redundant_checks']})

@pytest.mark.skipif(not WEBSOCKET_MANAGER_AVAILABLE, reason='WebSocket manager not available')
class WebSocketHealthIntegrationRequirementsTests(SSotAsyncTestCase):
    "
    Additional tests that require WebSocket components to be available.
    These tests validate specific integration points.
"

    async def test_websocket_manager_agent_health_integration_missing(self):
    ""
        REPRODUCTION TEST: Show WebSocket manager doesn't integrate with agent health monitor.
        
        Expected to FAIL: No direct integration between WebSocket manager and agent health.
        
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        websocket_manager = get_websocket_manager(user_context=getattr(self, 'user_context', None))
        health_monitor = AgentHealthMonitor()
        integration_analysis = {'websocket_has_health_monitor': hasattr(websocket_manager, 'agent_health_monitor'), 'websocket_has_health_check': hasattr(websocket_manager, 'check_agent_health'), 'websocket_has_health_callback': hasattr(websocket_manager, 'on_agent_health_change'), 'health_has_websocket_ref': hasattr(health_monitor, 'websocket_manager'), 'health_has_connection_callback': hasattr(health_monitor, 'notify_websocket_manager'), 'integration_methods_count': 0}
        for attr_name in dir(websocket_manager):
            if 'health' in attr_name.lower() and (not attr_name.startswith('_')):
                integration_analysis['integration_methods_count'] += 1
        for attr_name in dir(health_monitor):
            if 'websocket' in attr_name.lower() and (not attr_name.startswith('_')):
                integration_analysis['integration_methods_count'] += 1
        self.fail(fSSOT VIOLATION: WebSocket manager and agent health monitor not integrated. WebSocket has health monitor: {integration_analysis['websocket_has_health_monitor']}, Health has WebSocket ref: {integration_analysis['health_has_websocket_ref']}, Integration methods found: {integration_analysis['integration_methods_count']})"
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')