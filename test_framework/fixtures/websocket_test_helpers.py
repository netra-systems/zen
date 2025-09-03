#!/usr/bin/env python
"""
WebSocket Test Helpers - Integration utilities for unified MockWebSocketManager

This module provides pytest fixtures, assertion helpers, and test utilities
to make it easy to migrate existing tests to use the new unified mock.

Business Value: Reduces migration effort and ensures consistent test patterns.
"""

import asyncio
import pytest
import time
from typing import Dict, List, Any, Optional, Callable, Union
from unittest.mock import AsyncMock, MagicMock

from test_framework.fixtures.websocket_manager_mock import (
    MockWebSocketManager,
    MockConfiguration,
    MockBehaviorMode,
    create_basic_mock,
    create_compliance_mock,
    create_performance_mock,
    create_resilience_mock,
    create_concurrency_mock
)


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_websocket_manager():
    """Basic MockWebSocketManager fixture for simple tests."""
    return create_basic_mock()

@pytest.fixture
def mock_websocket_compliance():
    """MockWebSocketManager fixture configured for compliance testing."""
    return create_compliance_mock()

@pytest.fixture
def mock_websocket_performance():
    """MockWebSocketManager fixture configured for performance testing."""
    return create_performance_mock()

@pytest.fixture
def mock_websocket_resilience():
    """MockWebSocketManager fixture configured for resilience testing."""
    return create_resilience_mock()

@pytest.fixture
def mock_websocket_concurrency():
    """MockWebSocketManager fixture configured for concurrency testing.""" 
    return create_concurrency_mock()

@pytest.fixture
def mock_websocket_factory():
    """Factory fixture that can create different mock configurations."""
    def _create_mock(scenario: str = "basic", **kwargs):
        return MockWebSocketManager.create_for_scenario(scenario, **kwargs)
    return _create_mock

@pytest.fixture
async def async_mock_websocket_manager():
    """Async MockWebSocketManager fixture with automatic cleanup."""
    mock = create_basic_mock()
    try:
        yield mock
    finally:
        mock.clear_messages()

@pytest.fixture
def mock_websocket_with_connections(mock_websocket_manager):
    """MockWebSocketManager fixture with pre-configured connections."""
    async def setup():
        # Add some test connections
        await mock_websocket_manager.connect_user("user1", MagicMock(), "thread1")
        await mock_websocket_manager.connect_user("user2", MagicMock(), "thread2")
        await mock_websocket_manager.connect_user("user3", MagicMock(), "thread3")
    
    asyncio.run(setup())
    return mock_websocket_manager


# ============================================================================
# ASSERTION HELPERS
# ============================================================================

class WebSocketAssertions:
    """Helper class for common WebSocket test assertions."""
    
    def __init__(self, mock_manager: MockWebSocketManager):
        self.mock = mock_manager
    
    def assert_event_sent(self, thread_id: str, event_type: str, count: int = 1):
        """Assert that a specific event was sent to a thread."""
        events = self.mock.get_events_for_thread(thread_id)
        matching_events = [e for e in events if e['event_type'] == event_type]
        
        assert len(matching_events) == count, (
            f"Expected {count} '{event_type}' events for thread {thread_id}, "
            f"but found {len(matching_events)}"
        )
    
    def assert_required_events_sent(self, thread_id: str):
        """Assert all 5 required WebSocket events were sent."""
        compliance = self.mock.get_required_event_compliance(thread_id)
        missing_events = [event for event, sent in compliance.items() if not sent]
        
        assert not missing_events, (
            f"Missing required events for thread {thread_id}: {missing_events}. "
            f"This violates business requirements for chat functionality."
        )
    
    def assert_compliance_score(self, thread_id: str, min_score: float = 1.0):
        """Assert minimum compliance score for a thread."""
        score = self.mock.get_compliance_score(thread_id)
        assert score >= min_score, (
            f"Compliance score {score} for thread {thread_id} is below minimum {min_score}"
        )
    
    def assert_event_order(self, thread_id: str, expected_order: List[str]):
        """Assert events were sent in expected order."""
        events = self.mock.get_events_for_thread(thread_id)
        actual_order = [e['event_type'] for e in events]
        
        assert actual_order == expected_order, (
            f"Event order mismatch for thread {thread_id}. "
            f"Expected: {expected_order}, Actual: {actual_order}"
        )
    
    def assert_no_failures(self):
        """Assert no send failures occurred."""
        analysis = self.mock.get_failure_analysis()
        assert analysis['failed_sends'] == 0, (
            f"Unexpected send failures: {analysis['failed_send_types']}"
        )
    
    def assert_performance_threshold(self, max_latency: float = 1.0, min_throughput: float = 10.0):
        """Assert performance meets minimum thresholds."""
        metrics = self.mock.get_performance_metrics()
        
        if 'max_latency' in metrics:
            assert metrics['max_latency'] <= max_latency, (
                f"Max latency {metrics['max_latency']}s exceeds threshold {max_latency}s"
            )
        
        if 'throughput' in metrics:
            throughput = metrics['throughput']['messages_per_second']
            assert throughput >= min_throughput, (
                f"Throughput {throughput} msg/s is below minimum {min_throughput} msg/s"
            )
    
    def assert_connection_established(self, thread_id: str):
        """Assert connection was properly established."""
        assert thread_id in self.mock.connections, f"No connection found for thread {thread_id}"
        assert self.mock.connections[thread_id]['connected'], f"Thread {thread_id} not connected"
    
    def assert_message_count(self, thread_id: str, expected_count: int):
        """Assert expected number of messages for a thread."""
        events = self.mock.get_events_for_thread(thread_id)
        assert len(events) == expected_count, (
            f"Expected {expected_count} messages for thread {thread_id}, "
            f"but found {len(events)}"
        )
    
    def assert_no_race_conditions(self):
        """Assert no race conditions were detected."""
        if hasattr(self.mock, 'race_condition_tracker'):
            for thread_id, events in self.mock.race_condition_tracker.items():
                if len(events) >= 2:
                    time_diffs = [events[i][0] - events[i-1][0] for i in range(1, len(events))]
                    close_events = [diff for diff in time_diffs if diff < 0.001]
                    assert len(close_events) == 0, (
                        f"Potential race conditions detected in thread {thread_id}: "
                        f"{len(close_events)} events within 1ms"
                    )


def assert_websocket_events(mock_manager: MockWebSocketManager, thread_id: str) -> WebSocketAssertions:
    """Create assertion helper for a specific mock and thread."""
    return WebSocketAssertions(mock_manager)


# ============================================================================
# TEST SCENARIO HELPERS
# ============================================================================

async def simulate_agent_execution_flow(
    mock_manager: MockWebSocketManager,
    thread_id: str,
    include_tools: bool = True,
    tool_count: int = 2
) -> List[Dict]:
    """
    Simulate a complete agent execution flow with proper event sequence.
    
    This helper ensures all required events are sent in the correct order
    for compliance testing.
    """
    events_sent = []
    
    # Required event sequence for business compliance
    await mock_manager.send_to_thread(thread_id, {
        'type': 'agent_started',
        'data': {'agent_id': 'test_agent', 'timestamp': time.time()}
    })
    events_sent.append('agent_started')
    
    await mock_manager.send_to_thread(thread_id, {
        'type': 'agent_thinking', 
        'data': {'status': 'analyzing request', 'timestamp': time.time()}
    })
    events_sent.append('agent_thinking')
    
    if include_tools:
        for i in range(tool_count):
            await mock_manager.send_to_thread(thread_id, {
                'type': 'tool_executing',
                'data': {'tool_name': f'test_tool_{i}', 'timestamp': time.time()}
            })
            events_sent.append('tool_executing')
            
            await mock_manager.send_to_thread(thread_id, {
                'type': 'tool_completed',
                'data': {'tool_name': f'test_tool_{i}', 'result': 'success', 'timestamp': time.time()}
            })
            events_sent.append('tool_completed')
    
    await mock_manager.send_to_thread(thread_id, {
        'type': 'agent_completed',
        'data': {'status': 'success', 'timestamp': time.time()}
    })
    events_sent.append('agent_completed')
    
    return events_sent


async def simulate_concurrent_agents(
    mock_manager: MockWebSocketManager,
    thread_count: int = 3,
    messages_per_thread: int = 5
) -> Dict[str, List[Dict]]:
    """
    Simulate concurrent agent executions for concurrency testing.
    """
    async def run_agent_thread(thread_id: str):
        events = []
        for i in range(messages_per_thread):
            event = {
                'type': f'test_event_{i}',
                'data': {'thread_id': thread_id, 'sequence': i, 'timestamp': time.time()}
            }
            await mock_manager.send_to_thread(thread_id, event)
            events.append(event)
            # Small delay to create interleaving
            await asyncio.sleep(0.01)
        return events
    
    # Run all threads concurrently
    tasks = [
        run_agent_thread(f"thread_{i}")
        for i in range(thread_count)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Return results keyed by thread ID
    return {f"thread_{i}": results[i] for i in range(thread_count)}


async def simulate_network_issues(
    mock_manager: MockWebSocketManager,
    thread_id: str,
    issue_type: str = "partition"
) -> Dict[str, Any]:
    """
    Simulate various network issues for resilience testing.
    """
    results = {'events_sent': [], 'failures': [], 'recoveries': []}
    
    if issue_type == "partition":
        # Enable network partition
        mock_manager.enable_partition()
        
        # Try to send messages during partition
        for i in range(3):
            success = await mock_manager.send_to_thread(thread_id, {
                'type': 'test_message',
                'data': {'sequence': i, 'during_partition': True}
            })
            if success:
                results['events_sent'].append(i)
            else:
                results['failures'].append(i)
        
        # Recover from partition
        mock_manager.disable_partition()
        mock_manager.simulate_recovery()
        
        # Send messages after recovery
        for i in range(3, 6):
            success = await mock_manager.send_to_thread(thread_id, {
                'type': 'test_message',
                'data': {'sequence': i, 'after_recovery': True}
            })
            if success:
                results['recoveries'].append(i)
    
    elif issue_type == "timeout":
        # Configure for high timeout probability
        original_timeout_prob = mock_manager.config.timeout_probability
        mock_manager.config.timeout_probability = 0.8
        
        for i in range(5):
            success = await mock_manager.send_to_thread(thread_id, {
                'type': 'timeout_test',
                'data': {'sequence': i}
            })
            if success:
                results['events_sent'].append(i)
            else:
                results['failures'].append(i)
        
        # Restore original configuration
        mock_manager.config.timeout_probability = original_timeout_prob
    
    return results


def create_test_message(
    message_type: str = "test_message",
    data: Optional[Dict[str, Any]] = None,
    thread_id: str = "test_thread"
) -> Dict[str, Any]:
    """Create a standardized test message."""
    return {
        'type': message_type,
        'data': data or {'timestamp': time.time()},
        'thread_id': thread_id,
        'test_id': f"test_{int(time.time() * 1000)}"
    }


# ============================================================================
# MIGRATION HELPERS
# ============================================================================

def migrate_legacy_mock_usage(legacy_mock_code: str) -> str:
    """
    Helper to migrate legacy mock usage to new unified mock.
    
    This is a simple string replacement helper for common patterns.
    More complex migrations should be done manually.
    """
    replacements = [
        # Class name changes
        ("class MockWebSocketManager:", "# Use unified MockWebSocketManager\nfrom test_framework.fixtures.websocket_manager_mock import MockWebSocketManager"),
        
        # Import changes  
        ("from tests.mission_critical.conftest_websocket_fixtures import MockWebSocketManager",
         "from test_framework.fixtures.websocket_manager_mock import create_basic_mock as MockWebSocketManager"),
        
        # Constructor patterns
        ("MockWebSocketManager()", "create_basic_mock()"),
        ("MockWebSocketManager(strict_mode=True)", "create_compliance_mock()"),
        
        # Method name changes
        (".record(", ".send_to_thread(thread_id, "),
        (".get_events_for_thread(", ".get_events_for_thread("),
    ]
    
    migrated_code = legacy_mock_code
    for old, new in replacements:
        migrated_code = migrated_code.replace(old, new)
    
    return migrated_code


class MockMigrationHelper:
    """Helper class for migrating tests to use the unified mock."""
    
    def __init__(self, test_file_path: str):
        self.test_file_path = test_file_path
        self.migration_report = []
    
    def analyze_mock_usage(self) -> Dict[str, Any]:
        """Analyze current mock usage patterns in a test file."""
        with open(self.test_file_path, 'r') as f:
            content = f.read()
        
        patterns = {
            'mock_classes': content.count('class MockWebSocketManager'),
            'mock_imports': content.count('MockWebSocketManager'),
            'send_to_thread_calls': content.count('send_to_thread'),
            'get_events_calls': content.count('get_events_for_thread'),
            'compliance_checks': content.count('required_event'),
        }
        
        return patterns
    
    def suggest_migration_strategy(self) -> List[str]:
        """Suggest migration strategy based on usage patterns."""
        analysis = self.analyze_mock_usage()
        suggestions = []
        
        if analysis['mock_classes'] > 0:
            suggestions.append("Remove local MockWebSocketManager class and import unified mock")
        
        if analysis['compliance_checks'] > 0:
            suggestions.append("Use create_compliance_mock() for tests checking required events")
        
        if analysis['mock_imports'] > 1:
            suggestions.append("Consolidate to single mock import with appropriate factory method")
        
        return suggestions


# ============================================================================
# COMPATIBILITY FIXTURES FOR LEGACY TESTS
# ============================================================================

@pytest.fixture
def legacy_mock_websocket_manager():
    """Legacy compatibility fixture - redirects to unified mock."""
    return create_basic_mock()

@pytest.fixture  
def strict_mock_websocket_manager():
    """Legacy compatibility fixture for strict mode - redirects to compliance mock."""
    return create_compliance_mock()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_compliance_test(mock_manager: MockWebSocketManager, thread_id: str) -> bool:
    """Quick check if all required events were sent."""
    compliance = mock_manager.get_required_event_compliance(thread_id)
    return all(compliance.values())

def quick_performance_check(mock_manager: MockWebSocketManager) -> Dict[str, Any]:
    """Quick performance metrics summary."""
    metrics = mock_manager.get_performance_metrics()
    return {
        'total_messages': metrics.get('messages_sent', 0),
        'avg_latency': metrics.get('average_latency', 0.0),
        'throughput': metrics.get('throughput', {}).get('messages_per_second', 0.0)
    }

def reset_mock_for_test(mock_manager: MockWebSocketManager):
    """Reset mock state for a fresh test."""
    mock_manager.clear_messages()
    mock_manager.reset_behavior_state()


# Export main functions and classes
__all__ = [
    'WebSocketAssertions',
    'assert_websocket_events', 
    'simulate_agent_execution_flow',
    'simulate_concurrent_agents',
    'simulate_network_issues',
    'create_test_message',
    'migrate_legacy_mock_usage',
    'MockMigrationHelper',
    'quick_compliance_test',
    'quick_performance_check',
    'reset_mock_for_test'
]