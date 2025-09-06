"""
Comprehensive Unit Tests for Event Validation Framework

Business Value: Ensures 100% reliability of WebSocket event validation for chat functionality.
Tests all critical validation rules, error recovery, and performance requirements.
"""

import asyncio
import pytest
import time
import uuid
from typing import Dict, List, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.event_validation_framework import (
    EventValidator,
    EventSequenceValidator, 
    EventValidationFramework,
    EventValidationLevel,
    EventType,
    ValidationResult,
    ValidatedEvent,
    EventSequence,
    EventMetrics,
    CircuitBreakerState,
    get_event_validation_framework,
    validate_websocket_event
)


class TestEventValidator:
    """Test suite for EventValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = EventValidator(EventValidationLevel.STRICT)
        self.sample_context = {
            'thread_id': 'test-thread-123',
            'run_id': 'run-456'
        }
    
    def test_init_validation_rules(self):
        """Test validator initializes with all required validation rules."""
        assert len(self.validator.validation_rules) > 0
        
        # Check for critical rules
        rule_names = {rule.name for rule in self.validator.validation_rules}
        assert 'agent_started_required_fields' in rule_names
        assert 'tool_event_pairing' in rule_names
        assert 'event_timing_constraints' in rule_names
    
    def test_validate_agent_started_event_valid(self):
        """Test validation of valid agent_started event."""
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        validated = self.validator.validate_event(event, self.sample_context)
        assert validated.validation_result == ValidationResult.VALID
        assert len(validated.validation_errors) == 0
    
    def test_validate_agent_started_event_missing_fields(self):
        """Test validation fails for agent_started event with missing fields."""
        event = {
            'type': 'agent_started',
            'payload': {
                # Missing agent_name and run_id
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        validated = self.validator.validate_event(event, self.sample_context)
        assert validated.validation_result in [ValidationResult.ERROR, ValidationResult.CRITICAL]
        assert len(validated.validation_errors) > 0
    
    def test_validate_agent_thinking_event_valid(self):
        """Test validation of valid agent_thinking event."""
        event = {
            'type': 'agent_thinking',
            'payload': {
                'thought': 'I am analyzing the user request',
                'agent_name': 'test_agent',
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        validated = self.validator.validate_event(event, self.sample_context)
        assert validated.validation_result == ValidationResult.VALID
        assert len(validated.validation_errors) == 0
    
    def test_validate_agent_thinking_event_empty_thought(self):
        """Test validation warns for agent_thinking event with empty thought."""
        event = {
            'type': 'agent_thinking',
            'payload': {
                'thought': '',  # Empty thought
                'agent_name': 'test_agent',
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        validated = self.validator.validate_event(event, self.sample_context)
        assert validated.validation_result == ValidationResult.ERROR
        assert 'thought content' in str(validated.validation_errors).lower()
    
    def test_validate_tool_executing_event_valid(self):
        """Test validation of valid tool_executing event."""
        event = {
            'type': 'tool_executing',
            'payload': {
                'tool_name': 'web_search',
                'agent_name': 'test_agent',
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        validated = self.validator.validate_event(event, self.sample_context)
        assert validated.validation_result == ValidationResult.VALID
        assert len(validated.validation_errors) == 0
    
    def test_validate_tool_completed_event_valid(self):
        """Test validation of valid tool_completed event."""
        event = {
            'type': 'tool_completed',
            'payload': {
                'tool_name': 'web_search',
                'agent_name': 'test_agent',
                'result': {'status': 'success', 'data': 'search results'},
                'success': True,
                'duration_ms': 1500,
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        validated = self.validator.validate_event(event, self.sample_context)
        assert validated.validation_result == ValidationResult.VALID
        assert len(validated.validation_errors) == 0
    
    def test_validate_agent_completed_event_valid(self):
        """Test validation of valid agent_completed event."""
        event = {
            'type': 'agent_completed',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'result': {'answer': 'Task completed successfully'},
                'duration_ms': 5000,
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        validated = self.validator.validate_event(event, self.sample_context)
        assert validated.validation_result == ValidationResult.VALID
        assert len(validated.validation_errors) == 0
    
    def test_validate_invalid_timestamp(self):
        """Test validation handles invalid timestamps."""
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time() - 7200  # 2 hours in the past
            },
            'thread_id': 'thread-123',
            'timestamp': time.time() - 7200
        }
        
        validated = self.validator.validate_event(event, self.sample_context)
        # Should have warnings about timestamp
        assert len(validated.validation_warnings) > 0 or len(validated.validation_errors) > 0
    
    def test_metrics_update(self):
        """Test that validation updates metrics correctly."""
        initial_total = self.validator.metrics.total_events
        
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        self.validator.validate_event(event, self.sample_context)
        
        assert self.validator.metrics.total_events == initial_total + 1
        assert self.validator.metrics.successful_events > 0


class TestEventSequenceValidator:
    """Test suite for EventSequenceValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_validator = EventValidator(EventValidationLevel.MODERATE)
        self.sequence_validator = EventSequenceValidator(self.event_validator)
        self.thread_id = 'test-thread-123'
        self.run_id = 'run-456'
    
    def test_start_sequence(self):
        """Test starting a new event sequence."""
        sequence = self.sequence_validator.start_sequence(self.thread_id, self.run_id)
        
        assert sequence.thread_id == self.thread_id
        assert sequence.run_id == self.run_id
        assert sequence.start_time is not None
        assert not sequence.is_complete
        assert len(sequence.events) == 0
        
        # Check it's stored in active sequences
        assert self.thread_id in self.sequence_validator.active_sequences
    
    def test_valid_event_sequence(self):
        """Test validation of a complete valid event sequence."""
        events = [
            {
                'type': 'agent_started',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': self.run_id,
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'agent_thinking',
                'payload': {
                    'thought': 'Processing user request',
                    'agent_name': 'test_agent',
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'tool_executing',
                'payload': {
                    'tool_name': 'web_search',
                    'agent_name': 'test_agent',
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'tool_completed',
                'payload': {
                    'tool_name': 'web_search',
                    'agent_name': 'test_agent',
                    'result': {'data': 'results'},
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'agent_completed',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': self.run_id,
                    'result': {'answer': 'Done'},
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            }
        ]
        
        # Add all events to sequence
        validated_events = []
        for event in events:
            validated_event = self.sequence_validator.add_event_to_sequence(self.thread_id, event)
            validated_events.append(validated_event)
            time.sleep(0.01)  # Small delay between events
        
        # Check sequence completion
        sequence_status = self.sequence_validator.get_sequence_status(self.thread_id)
        assert sequence_status is not None
        assert sequence_status['sequence_complete'] is True
        assert sequence_status['required_events_present'] is True
        assert sequence_status['tools_properly_paired'] is True
    
    def test_unpaired_tool_events(self):
        """Test detection of unpaired tool events."""
        events = [
            {
                'type': 'agent_started',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': self.run_id,
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'tool_executing',
                'payload': {
                    'tool_name': 'web_search',
                    'agent_name': 'test_agent',
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            },
            # Missing tool_completed event
            {
                'type': 'agent_completed',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': self.run_id,
                    'result': {'answer': 'Done'},
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            }
        ]
        
        # Add events to sequence
        for event in events:
            validated_event = self.sequence_validator.add_event_to_sequence(self.thread_id, event)
        
        # Check for pairing validation errors
        sequence_status = self.sequence_validator.get_sequence_status(self.thread_id)
        assert sequence_status['tools_properly_paired'] is False
    
    def test_invalid_event_order(self):
        """Test detection of invalid event order."""
        events = [
            # Start with tool_executing instead of agent_started
            {
                'type': 'tool_executing',
                'payload': {
                    'tool_name': 'web_search',
                    'agent_name': 'test_agent',
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'agent_started',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': self.run_id,
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            }
        ]
        
        # Add events to sequence
        for event in events:
            validated_event = self.sequence_validator.add_event_to_sequence(self.thread_id, event)
            # Should have validation errors for invalid order
            if validated_event.event_type == EventType.AGENT_STARTED:
                assert len(validated_event.validation_errors) > 0
    
    def test_sequence_timing_validation(self):
        """Test sequence timing constraint validation."""
        # Create events with large time gaps
        base_time = time.time()
        events = [
            {
                'type': 'agent_started',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': self.run_id,
                    'timestamp': base_time
                },
                'thread_id': self.thread_id,
                'timestamp': base_time
            },
            {
                'type': 'agent_completed',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': self.run_id,
                    'result': {'answer': 'Done'},
                    'timestamp': base_time + 3600  # 1 hour later
                },
                'thread_id': self.thread_id,
                'timestamp': base_time + 3600
            }
        ]
        
        # Add events with large time gap
        for event in events:
            validated_event = self.sequence_validator.add_event_to_sequence(self.thread_id, event)
        
        sequence_status = self.sequence_validator.get_sequence_status(self.thread_id)
        # Should detect timing violations
        assert sequence_status['timing_valid'] is False


class TestEventValidationFramework:
    """Test suite for the main EventValidationFramework class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.framework = EventValidationFramework(EventValidationLevel.STRICT)
        self.thread_id = 'test-thread-123'
        self.context = {'thread_id': self.thread_id, 'run_id': 'run-456'}
    
    @pytest.mark.asyncio
    async def test_validate_event_success(self):
        """Test successful event validation."""
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': self.thread_id,
            'timestamp': time.time()
        }
        
        validated_event = await self.framework.validate_event(event, self.context)
        
        assert validated_event.validation_result == ValidationResult.VALID
        assert len(validated_event.validation_errors) == 0
        
        # Check it's stored in history
        history = self.framework.get_thread_history(self.thread_id)
        assert len(history) == 1
        assert history[0].event_id == validated_event.event_id
    
    @pytest.mark.asyncio
    async def test_validate_event_with_errors(self):
        """Test event validation with errors."""
        event = {
            'type': 'agent_thinking',
            'payload': {
                'thought': '',  # Invalid empty thought
                'agent_name': 'test_agent',
                'timestamp': time.time()
            },
            'thread_id': self.thread_id,
            'timestamp': time.time()
        }
        
        validated_event = await self.framework.validate_event(event, self.context)
        
        assert validated_event.validation_result == ValidationResult.ERROR
        assert len(validated_event.validation_errors) > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker opens on repeated failures."""
        # Create invalid events to trigger failures
        invalid_event = {
            'type': 'agent_started',
            'payload': {
                # Missing required fields
                'timestamp': time.time()
            },
            'thread_id': self.thread_id,
            'timestamp': time.time()
        }
        
        # Send enough invalid events to trigger circuit breaker
        for i in range(self.framework.failure_threshold + 1):
            await self.framework.validate_event(invalid_event, self.context)
        
        # Circuit breaker should be open
        assert self.framework.circuit_breaker_state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        # Trigger circuit breaker
        invalid_event = {
            'type': 'agent_started',
            'payload': {'timestamp': time.time()},
            'thread_id': self.thread_id,
            'timestamp': time.time()
        }
        
        for i in range(self.framework.failure_threshold + 1):
            await self.framework.validate_event(invalid_event, self.context)
        
        assert self.framework.circuit_breaker_state == CircuitBreakerState.OPEN
        
        # Simulate timeout passage
        self.framework.last_failure_time = time.time() - self.framework.recovery_timeout - 1
        
        # Send valid event should trigger half-open state
        valid_event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': self.thread_id,
            'timestamp': time.time()
        }
        
        await self.framework.validate_event(valid_event, self.context)
        
        # Should be closed after successful validation
        assert self.framework.circuit_breaker_state == CircuitBreakerState.CLOSED
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        metrics = self.framework.get_performance_metrics()
        
        assert isinstance(metrics, EventMetrics)
        assert metrics.total_events >= 0
        assert metrics.successful_events >= 0
        assert metrics.failed_events >= 0
    
    def test_event_history_tracking(self):
        """Test event history is properly tracked."""
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': self.thread_id,
            'timestamp': time.time()
        }
        
        # Manually add to history (simulating validation)
        validated_event = self.framework.event_validator.validate_event(event, self.context)
        self.framework.event_history[self.thread_id].append(validated_event)
        
        history = self.framework.get_thread_history(self.thread_id)
        assert len(history) == 1
        assert history[0].thread_id == self.thread_id
    
    def test_detect_silent_failures(self):
        """Test detection of silent failures (missing events)."""
        # Add incomplete sequence (missing required events)
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': self.thread_id,
            'timestamp': time.time()
        }
        
        validated_event = self.framework.event_validator.validate_event(event, self.context)
        self.framework.event_history[self.thread_id].append(validated_event)
        
        failures = self.framework.detect_silent_failures(self.thread_id)
        assert len(failures) > 0
        assert any('missing required events' in failure.lower() for failure in failures)
    
    @pytest.mark.asyncio
    async def test_event_replay(self):
        """Test event replay functionality."""
        # Add some events to history
        events = [
            {
                'type': 'agent_started',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': 'run-123',
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'agent_completed',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': 'run-123',
                    'result': {'answer': 'Done'},
                    'timestamp': time.time()
                },
                'thread_id': self.thread_id,
                'timestamp': time.time()
            }
        ]
        
        for event in events:
            await self.framework.validate_event(event, self.context)
        
        # Replay events
        replayed = await self.framework.replay_events(self.thread_id)
        assert len(replayed) == len(events)
        assert all(e.thread_id == self.thread_id for e in replayed)
    
    def test_validation_report_thread_specific(self):
        """Test generation of thread-specific validation report."""
        # Add event to history
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': self.thread_id,
            'timestamp': time.time()
        }
        
        validated_event = self.framework.event_validator.validate_event(event, self.context)
        self.framework.event_history[self.thread_id].append(validated_event)
        
        report = self.framework.generate_validation_report(self.thread_id)
        
        assert report['thread_id'] == self.thread_id
        assert report['event_count'] == 1
        assert 'validation_summary' in report
        assert 'silent_failures' in report
    
    def test_validation_report_global(self):
        """Test generation of global validation report."""
        report = self.framework.generate_validation_report()
        
        assert 'framework_status' in report
        assert 'performance_metrics' in report
        assert 'active_sequences' in report
        assert 'completed_sequences' in report


class TestConvenienceFunctions:
    """Test suite for convenience functions and global framework access."""
    
    @pytest.mark.asyncio
    async def test_validate_websocket_event_function(self):
        """Test the convenience validate_websocket_event function."""
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': 'test-thread',
            'timestamp': time.time()
        }
        
        validated_event = await validate_websocket_event(event)
        
        assert isinstance(validated_event, ValidatedEvent)
        assert validated_event.event_type == EventType.AGENT_STARTED
    
    def test_get_event_validation_framework_singleton(self):
        """Test that get_event_validation_framework returns singleton."""
        framework1 = get_event_validation_framework()
        framework2 = get_event_validation_framework()
        
        assert framework1 is framework2
    
    @pytest.mark.asyncio
    async def test_get_validation_report_function(self):
        """Test the convenience get_validation_report function."""
        from netra_backend.app.websocket_core.event_validation_framework import get_validation_report
        
        # Global report
        global_report = await get_validation_report()
        assert 'framework_status' in global_report
        assert 'performance_metrics' in global_report
        
        # Thread-specific report
        thread_report = await get_validation_report('test-thread')
        assert 'thread_id' in thread_report


@pytest.mark.asyncio
async def test_concurrent_validation():
    """Test framework handles concurrent validation requests."""
    framework = EventValidationFramework(EventValidationLevel.MODERATE)
    
    # Create multiple concurrent validation tasks
    events = []
    for i in range(10):
        event = {
            'type': 'agent_started',
            'payload': {
                'agent_name': f'agent_{i}',
                'run_id': f'run_{i}',
                'timestamp': time.time()
            },
            'thread_id': f'thread_{i}',
            'timestamp': time.time()
        }
        events.append(event)
    
    # Run validations concurrently
    tasks = [framework.validate_event(event) for event in events]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 10
    assert all(isinstance(result, ValidatedEvent) for result in results)
    assert all(result.validation_result == ValidationResult.VALID for result in results)


@pytest.mark.asyncio
async def test_validation_callback_system():
    """Test validation callback registration and notification."""
    framework = EventValidationFramework(EventValidationLevel.MODERATE)
    
    # Track callback invocations
    callback_calls = []
    error_calls = []
    
    async def validation_callback(validated_event):
        callback_calls.append(validated_event)
    
    async def error_callback(validated_event):
        error_calls.append(validated_event)
    
    # Register callbacks
    framework.register_validation_callback(validation_callback)
    framework.register_error_callback(error_callback)
    
    # Valid event should trigger validation callback
    valid_event = {
        'type': 'agent_started',
        'payload': {
            'agent_name': 'test_agent',
            'run_id': 'run-123',
            'timestamp': time.time()
        },
        'thread_id': 'test-thread',
        'timestamp': time.time()
    }
    
    await framework.validate_event(valid_event)
    
    assert len(callback_calls) == 1
    
    # Invalid event should trigger error callback
    invalid_event = {
        'type': 'agent_started',
        'payload': {
            # Missing required fields
            'timestamp': time.time()
        },
        'thread_id': 'test-thread',
        'timestamp': time.time()
    }
    
    await framework.validate_event(invalid_event)
    
    assert len(error_calls) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])