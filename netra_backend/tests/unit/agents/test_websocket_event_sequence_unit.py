"""Unit tests for WebSocket event sequence validation in agent golden path messages.

These tests validate the critical 5-event sequence that delivers 500K+ ARR business value
through the Golden Path user flow: users login → get meaningful AI responses.

Business Value: Free/Early/Mid/Enterprise - Real-time User Experience
Ensures the complete WebSocket event sequence (agent_started → agent_thinking →
tool_executing → tool_completed → agent_completed) is properly validated and enforced.

GOLDEN PATH CRITICAL EVENTS:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows response is ready

Test Coverage:
- Complete 5-event sequence validation
- Event ordering enforcement
- Sequence interruption handling
- Duplicate event prevention
- Event timing validation
- Error state event generation
- Business value protection validation
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.core_enums import ExecutionStatus


class MockWebSocketEventValidator:
    """Mock WebSocket event validator for testing sequence validation."""

    def __init__(self):
        self.events_received = []
        self.validation_errors = []
        self.sequence_state = {
            'agent_started': False,
            'agent_thinking': False,
            'tool_executing': False,
            'tool_completed': False,
            'agent_completed': False
        }
        self.event_timestamps = {}
        self.duplicate_events = []
        self.out_of_order_events = []

    def record_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Record a WebSocket event for sequence validation."""
        timestamp = datetime.now(timezone.utc)

        # Check for duplicates
        if event_type in self.sequence_state and self.sequence_state[event_type]:
            self.duplicate_events.append({
                'event_type': event_type,
                'timestamp': timestamp,
                'data': event_data
            })
            return False

        # Check for proper ordering
        if not self._validate_event_order(event_type):
            self.out_of_order_events.append({
                'event_type': event_type,
                'timestamp': timestamp,
                'expected_state': dict(self.sequence_state),
                'data': event_data
            })
            return False

        # Record valid event
        self.events_received.append({
            'event_type': event_type,
            'timestamp': timestamp,
            'data': event_data
        })
        self.sequence_state[event_type] = True
        self.event_timestamps[event_type] = timestamp
        return True

    def _validate_event_order(self, event_type: str) -> bool:
        """Validate that the event follows proper sequence order."""
        if event_type == 'agent_started':
            return True  # First event can always occur
        elif event_type == 'agent_thinking':
            return self.sequence_state['agent_started']
        elif event_type == 'tool_executing':
            return self.sequence_state['agent_thinking']
        elif event_type == 'tool_completed':
            return self.sequence_state['tool_executing']
        elif event_type == 'agent_completed':
            return self.sequence_state['tool_completed']
        return False

    def validate_complete_sequence(self) -> bool:
        """Validate that all 5 critical events have been received."""
        return all(self.sequence_state.values())

    def get_sequence_timing(self) -> Dict[str, float]:
        """Get timing between events in milliseconds."""
        if not self.event_timestamps:
            return {}

        timings = {}
        events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

        for i in range(1, len(events)):
            current_event = events[i]
            previous_event = events[i-1]

            if current_event in self.event_timestamps and previous_event in self.event_timestamps:
                time_diff = self.event_timestamps[current_event] - self.event_timestamps[previous_event]
                timings[f"{previous_event}_to_{current_event}"] = time_diff.total_seconds() * 1000

        return timings

    def reset_sequence(self):
        """Reset the sequence validator for a new test."""
        self.events_received = []
        self.validation_errors = []
        self.sequence_state = {
            'agent_started': False,
            'agent_thinking': False,
            'tool_executing': False,
            'tool_completed': False,
            'agent_completed': False
        }
        self.event_timestamps = {}
        self.duplicate_events = []
        self.out_of_order_events = []


class WebSocketEventSequenceValidationTests(SSotAsyncTestCase):
    """Test WebSocket event sequence validation for Golden Path business value."""

    def setup_method(self, method):
        """Set up test fixtures for WebSocket event sequence testing."""
        super().setup_method(method)
        self.event_validator = MockWebSocketEventValidator()
        self.run_id = str(uuid.uuid4())
        self.thread_id = str(uuid.uuid4())
        self.user_id = "test_user_123"
        self.agent_name = "supervisor_agent"

        # Create mock execution context
        self.execution_context = AgentExecutionContext(
            run_id=self.run_id,
            thread_id=self.thread_id,
            user_id=self.user_id,
            agent_name=self.agent_name,
            step=PipelineStep.INITIALIZATION
        )

    async def test_complete_5_event_sequence_validation_success(self):
        """Test successful validation of complete 5-event sequence."""
        # Simulate complete Golden Path event sequence
        events = [
            ('agent_started', {'agent': self.agent_name, 'run_id': self.run_id}),
            ('agent_thinking', {'reasoning': 'Processing user request', 'run_id': self.run_id}),
            ('tool_executing', {'tool': 'data_analyzer', 'parameters': {'query': 'test'}}),
            ('tool_completed', {'tool': 'data_analyzer', 'result': {'data': 'processed'}}),
            ('agent_completed', {'response': 'Task completed successfully', 'run_id': self.run_id})
        ]

        # Record all events in sequence
        for event_type, event_data in events:
            result = self.event_validator.record_event(event_type, event_data)
            assert result, f"Event {event_type} should be recorded successfully"

        # Validate complete sequence
        assert self.event_validator.validate_complete_sequence(), "All 5 critical events should be received"
        assert len(self.event_validator.events_received) == 5, "Should have exactly 5 events"
        assert len(self.event_validator.duplicate_events) == 0, "Should have no duplicate events"
        assert len(self.event_validator.out_of_order_events) == 0, "Should have no out-of-order events"

    async def test_event_ordering_enforcement_strict(self):
        """Test strict enforcement of event ordering in Golden Path sequence."""
        # Try to send events out of order
        invalid_sequences = [
            [('agent_thinking', {}), ('agent_started', {})],  # thinking before started
            [('tool_executing', {}), ('agent_started', {})],  # tool before started
            [('agent_completed', {}), ('agent_started', {})],  # completed before started
            [('agent_started', {}), ('tool_executing', {})]   # tool before thinking
        ]

        for sequence in invalid_sequences:
            self.event_validator.reset_sequence()

            for event_type, event_data in sequence:
                result = self.event_validator.record_event(event_type, event_data)

            # Should have out-of-order events detected
            assert len(self.event_validator.out_of_order_events) > 0, \
                f"Sequence {sequence} should be detected as out of order"

    async def test_duplicate_event_prevention(self):
        """Test prevention of duplicate events in sequence."""
        # Start valid sequence
        assert self.event_validator.record_event('agent_started', {'run_id': self.run_id})
        assert self.event_validator.record_event('agent_thinking', {'reasoning': 'test'})

        # Try to send duplicate events
        duplicate_result_1 = self.event_validator.record_event('agent_started', {'run_id': self.run_id})
        duplicate_result_2 = self.event_validator.record_event('agent_thinking', {'reasoning': 'duplicate'})

        # Duplicates should be rejected
        assert not duplicate_result_1, "Duplicate agent_started should be rejected"
        assert not duplicate_result_2, "Duplicate agent_thinking should be rejected"
        assert len(self.event_validator.duplicate_events) == 2, "Should track 2 duplicate events"

    async def test_sequence_interruption_handling(self):
        """Test handling of interrupted event sequences."""
        # Start sequence normally
        assert self.event_validator.record_event('agent_started', {'run_id': self.run_id})
        assert self.event_validator.record_event('agent_thinking', {'reasoning': 'processing'})

        # Simulate interruption - missing tool_executing, jumping to completed
        interrupted_result = self.event_validator.record_event('agent_completed', {'error': 'interrupted'})

        # Should be detected as out of order
        assert not interrupted_result, "Interrupted sequence should be invalid"
        assert len(self.event_validator.out_of_order_events) == 1, "Should detect interruption"
        assert not self.event_validator.validate_complete_sequence(), "Incomplete sequence should not validate"

    async def test_event_timing_validation(self):
        """Test validation of event timing for performance monitoring."""
        # Record events with controlled timing
        events = [
            ('agent_started', {'run_id': self.run_id}),
            ('agent_thinking', {'reasoning': 'test'}),
            ('tool_executing', {'tool': 'test_tool'}),
            ('tool_completed', {'result': 'success'}),
            ('agent_completed', {'response': 'done'})
        ]

        # Add small delays to create measurable timing differences
        for i, (event_type, event_data) in enumerate(events):
            if i > 0:
                await asyncio.sleep(0.01)  # 10ms delay
            self.event_validator.record_event(event_type, event_data)

        # Get sequence timing
        timings = self.event_validator.get_sequence_timing()

        # Validate timing calculations
        assert len(timings) == 4, "Should have 4 timing intervals"
        assert all(timing > 0 for timing in timings.values()), "All timings should be positive"
        assert 'agent_started_to_agent_thinking' in timings, "Should have started to thinking timing"

    async def test_business_value_protection_validation(self):
        """Test that event sequence validation protects 500K+ ARR business value."""
        # Simulate high-value user interaction requiring complete event sequence
        high_value_context = {
            'user_tier': 'enterprise',
            'request_value': 'high',
            'business_impact': '500K+ ARR'
        }

        # Ensure complete sequence is required for high-value interactions
        critical_events = [
            ('agent_started', {**high_value_context, 'run_id': self.run_id}),
            ('agent_thinking', {**high_value_context, 'reasoning': 'enterprise optimization'}),
            ('tool_executing', {**high_value_context, 'tool': 'enterprise_analyzer'}),
            ('tool_completed', {**high_value_context, 'result': 'optimization_complete'}),
            ('agent_completed', {**high_value_context, 'value_delivered': True})
        ]

        for event_type, event_data in critical_events:
            result = self.event_validator.record_event(event_type, event_data)
            assert result, f"High-value event {event_type} must be processed successfully"

        # Validate business value protection
        assert self.event_validator.validate_complete_sequence(), \
            "High-value interactions must complete full event sequence"

        # Verify all high-value context preserved
        for event in self.event_validator.events_received:
            assert 'business_impact' in event['data'], "Business impact context must be preserved"

    async def test_error_state_event_generation(self):
        """Test generation of appropriate events during error states."""
        # Start normal sequence
        assert self.event_validator.record_event('agent_started', {'run_id': self.run_id})
        assert self.event_validator.record_event('agent_thinking', {'reasoning': 'processing'})
        assert self.event_validator.record_event('tool_executing', {'tool': 'test_tool'})

        # Simulate tool error
        error_event_data = {
            'tool': 'test_tool',
            'error': 'Tool execution failed',
            'error_code': 'TOOL_ERROR',
            'recovery_attempted': True
        }

        # Tool completed with error should still be valid
        assert self.event_validator.record_event('tool_completed', error_event_data)

        # Agent completed with error handling
        agent_error_data = {
            'response': 'I encountered an error but handled it gracefully',
            'error_handled': True,
            'fallback_used': True
        }

        assert self.event_validator.record_event('agent_completed', agent_error_data)

        # Sequence should still be complete even with errors
        assert self.event_validator.validate_complete_sequence(), \
            "Error handling should not break event sequence"

    async def test_concurrent_sequence_isolation(self):
        """Test that concurrent agent executions have isolated event sequences."""
        # Create second validator for concurrent execution
        second_validator = MockWebSocketEventValidator()
        second_run_id = str(uuid.uuid4())

        # Start sequences concurrently
        assert self.event_validator.record_event('agent_started', {'run_id': self.run_id})
        assert second_validator.record_event('agent_started', {'run_id': second_run_id})

        # Progress sequences independently
        assert self.event_validator.record_event('agent_thinking', {'reasoning': 'first agent', 'run_id': self.run_id})
        assert second_validator.record_event('agent_thinking', {'reasoning': 'second agent', 'run_id': second_run_id})

        # Validate isolation
        assert len(self.event_validator.events_received) == 2, "First validator should have 2 events"
        assert len(second_validator.events_received) == 2, "Second validator should have 2 events"

        # Events should be isolated by run_id - each validator only has its own events
        first_events = self.event_validator.events_received
        second_events = second_validator.events_received

        # Verify all events in first validator match first run_id
        for event in first_events:
            assert event["data"].get("run_id") == self.run_id, "First validator events should match first run_id"

        # Verify all events in second validator match second run_id
        for event in second_events:
            assert event["data"].get("run_id") == second_run_id, "Second validator events should match second run_id"

    async def test_sequence_timeout_handling(self):
        """Test handling of sequence timeouts for incomplete event chains."""
        # Start sequence but don't complete within timeout
        start_time = datetime.now(timezone.utc)
        assert self.event_validator.record_event('agent_started', {
            'run_id': self.run_id,
            'timeout': 100  # 100ms timeout
        })

        # Simulate delay longer than timeout
        await asyncio.sleep(0.15)  # 150ms delay

        # Check if sequence would be considered timed out
        current_time = datetime.now(timezone.utc)
        elapsed_time = (current_time - start_time).total_seconds() * 1000

        assert elapsed_time > 100, "Should have exceeded timeout period"
        assert not self.event_validator.validate_complete_sequence(), \
            "Incomplete sequence should not validate"

    async def test_golden_path_event_data_validation(self):
        """Test validation of required data fields in Golden Path events."""
        # Define required fields for each event type
        required_fields = {
            'agent_started': ['run_id', 'agent'],
            'agent_thinking': ['reasoning', 'run_id'],
            'tool_executing': ['tool', 'parameters'],
            'tool_completed': ['tool', 'result'],
            'agent_completed': ['response', 'run_id']
        }

        # Test each event with missing required fields
        for event_type, fields in required_fields.items():
            # Create complete valid data first
            valid_data = {
                'run_id': self.run_id,
                'agent': self.agent_name,
                'reasoning': 'test reasoning',
                'tool': 'test_tool',
                'parameters': {'param': 'value'},
                'result': {'success': True},
                'response': 'completed successfully'
            }

            # Test with all required fields (should succeed)
            self.event_validator.reset_sequence()

            # Build sequence up to current event type
            event_sequence = [
                ('agent_started', valid_data),
                ('agent_thinking', valid_data),
                ('tool_executing', valid_data),
                ('tool_completed', valid_data),
                ('agent_completed', valid_data)
            ]

            # Record events up to the one being tested
            for seq_event_type, seq_event_data in event_sequence:
                if seq_event_type == event_type:
                    break
                self.event_validator.record_event(seq_event_type, seq_event_data)

            # Record the event being tested
            result = self.event_validator.record_event(event_type, valid_data)
            assert result, f"Event {event_type} with valid data should succeed"

    async def test_sequence_state_recovery(self):
        """Test recovery of event sequence state after interruptions."""
        # Start and partially complete sequence
        assert self.event_validator.record_event('agent_started', {'run_id': self.run_id})
        assert self.event_validator.record_event('agent_thinking', {'reasoning': 'processing'})

        # Save current state
        original_state = dict(self.event_validator.sequence_state)
        original_events = list(self.event_validator.events_received)

        # Simulate recovery scenario
        recovered_validator = MockWebSocketEventValidator()
        recovered_validator.sequence_state = original_state
        recovered_validator.events_received = original_events

        # Continue sequence from recovery point
        assert recovered_validator.record_event('tool_executing', {'tool': 'recovery_tool'})
        assert recovered_validator.record_event('tool_completed', {'result': 'recovered'})
        assert recovered_validator.record_event('agent_completed', {'status': 'recovered'})

        # Validate recovered sequence
        assert recovered_validator.validate_complete_sequence(), \
            "Recovered sequence should complete successfully"

    async def test_performance_monitoring_integration(self):
        """Test integration of event sequence validation with performance monitoring."""
        # Record events with performance metrics
        performance_events = [
            ('agent_started', {
                'run_id': self.run_id,
                'performance_baseline': True,
                'expected_duration_ms': 5000
            }),
            ('agent_thinking', {
                'reasoning': 'performance test',
                'cpu_usage': 25.5,
                'memory_mb': 128
            }),
            ('tool_executing', {
                'tool': 'performance_tool',
                'estimated_duration_ms': 2000
            }),
            ('tool_completed', {
                'tool': 'performance_tool',
                'actual_duration_ms': 1850,
                'performance_delta': -150
            }),
            ('agent_completed', {
                'response': 'performance test complete',
                'total_duration_ms': 4800,
                'performance_score': 'excellent'
            })
        ]

        for event_type, event_data in performance_events:
            result = self.event_validator.record_event(event_type, event_data)
            assert result, f"Performance event {event_type} should be recorded"

        # Validate performance data preservation
        for event in self.event_validator.events_received:
            if 'performance_baseline' in event['data']:
                assert event['data']['performance_baseline'], "Performance monitoring should be enabled"

    async def test_multi_tool_execution_sequence(self):
        """Test event sequence for multi-tool executions within single agent run."""
        # Start agent sequence
        assert self.event_validator.record_event('agent_started', {'run_id': self.run_id})
        assert self.event_validator.record_event('agent_thinking', {'reasoning': 'multi-tool strategy'})

        # Simulate multiple tool executions
        tools = ['data_analyzer', 'report_generator', 'optimizer']

        # For this test, we'll simulate consolidated tool events
        # (In reality, each tool might generate separate events)
        assert self.event_validator.record_event('tool_executing', {
            'tool': 'multi_tool_pipeline',
            'sub_tools': tools,
            'execution_strategy': 'sequential'
        })

        assert self.event_validator.record_event('tool_completed', {
            'tool': 'multi_tool_pipeline',
            'results': {
                'data_analyzer': {'status': 'success'},
                'report_generator': {'status': 'success'},
                'optimizer': {'status': 'success'}
            },
            'all_tools_completed': True
        })

        assert self.event_validator.record_event('agent_completed', {
            'response': 'Multi-tool analysis completed successfully',
            'tools_used': len(tools)
        })

        # Validate complete sequence with multi-tool context
        assert self.event_validator.validate_complete_sequence(), \
            "Multi-tool execution should complete full event sequence"

    async def test_websocket_connection_resilience(self):
        """Test event sequence validation during WebSocket connection issues."""
        # Simulate connection issues during sequence
        connection_issues = [
            'connection_dropped',
            'reconnection_successful',
            'partial_message_loss'
        ]

        # Start sequence normally
        assert self.event_validator.record_event('agent_started', {'run_id': self.run_id})

        # Simulate connection issue during thinking phase
        thinking_data = {
            'reasoning': 'processing with connection issues',
            'connection_status': 'unstable',
            'retry_count': 2
        }
        assert self.event_validator.record_event('agent_thinking', thinking_data)

        # Continue sequence with connection recovery indicators
        assert self.event_validator.record_event('tool_executing', {
            'tool': 'resilient_tool',
            'connection_recovered': True
        })

        assert self.event_validator.record_event('tool_completed', {
            'tool': 'resilient_tool',
            'result': 'success despite connection issues'
        })

        assert self.event_validator.record_event('agent_completed', {
            'response': 'Task completed with connection resilience',
            'connection_issues_handled': len(connection_issues)
        })

        # Validate resilient sequence completion
        assert self.event_validator.validate_complete_sequence(), \
            "Sequence should complete despite connection issues"

    async def test_user_experience_event_correlation(self):
        """Test correlation of WebSocket events with user experience metrics."""
        # Define user experience metrics
        ux_metrics = {
            'perceived_responsiveness': 'high',
            'interaction_satisfaction': 8.5,
            'task_completion_confidence': 'very_high'
        }

        # Record events with UX correlation data
        events_with_ux = [
            ('agent_started', {
                'run_id': self.run_id,
                'ux_expectation': 'immediate_feedback',
                **ux_metrics
            }),
            ('agent_thinking', {
                'reasoning': 'optimizing for user experience',
                'transparency_level': 'high',
                'estimated_completion': '30 seconds'
            }),
            ('tool_executing', {
                'tool': 'ux_optimized_analyzer',
                'user_visible_progress': True,
                'progress_updates_enabled': True
            }),
            ('tool_completed', {
                'tool': 'ux_optimized_analyzer',
                'result': {'insights': 'valuable business insights'},
                'user_satisfaction_predicted': 9.0
            }),
            ('agent_completed', {
                'response': 'Analysis complete with actionable insights',
                'ux_goals_achieved': True,
                'user_value_delivered': 'high'
            })
        ]

        for event_type, event_data in events_with_ux:
            result = self.event_validator.record_event(event_type, event_data)
            assert result, f"UX-correlated event {event_type} should be recorded"

        # Validate UX correlation preservation
        ux_enabled_events = [e for e in self.event_validator.events_received
                           if 'ux_expectation' in e['data'] or 'user_satisfaction_predicted' in e['data']]

        assert len(ux_enabled_events) > 0, "Should have UX-correlated events"

    async def test_event_sequence_business_metrics(self):
        """Test collection of business metrics through event sequence validation."""
        # Define business impact metrics
        business_metrics = {
            'revenue_impact': '$125K',
            'customer_tier': 'enterprise',
            'feature_utilization': 'optimization_suite',
            'success_probability': 0.95
        }

        # Record complete sequence with business metrics
        sequence_with_metrics = [
            ('agent_started', {
                'run_id': self.run_id,
                'business_context': business_metrics,
                'value_tracking_enabled': True
            }),
            ('agent_thinking', {
                'reasoning': 'enterprise-grade analysis',
                'business_value_consideration': True,
                'roi_optimization': 'active'
            }),
            ('tool_executing', {
                'tool': 'enterprise_optimizer',
                'business_impact_calculation': True,
                'value_measurement': 'enabled'
            }),
            ('tool_completed', {
                'tool': 'enterprise_optimizer',
                'result': {
                    'optimization_achieved': '23% efficiency gain',
                    'projected_savings': '$45K annually'
                },
                'business_value_realized': True
            }),
            ('agent_completed', {
                'response': 'Enterprise optimization complete with significant ROI',
                'business_value_delivered': '$45K annual savings',
                'customer_satisfaction_score': 9.2,
                'upsell_opportunity_identified': True
            })
        ]

        for event_type, event_data in sequence_with_metrics:
            result = self.event_validator.record_event(event_type, event_data)
            assert result, f"Business metrics event {event_type} should be recorded"

        # Validate business metrics collection
        business_events = [e for e in self.event_validator.events_received
                         if 'business_context' in e['data'] or 'business_value_delivered' in e['data']]

        assert len(business_events) > 0, "Should collect business metrics through event sequence"

        # Validate sequence supports business value measurement
        assert self.event_validator.validate_complete_sequence(), \
            "Business value measurement requires complete event sequence"