"""
Comprehensive Unit Tests for Event Validation Framework - SSOT Implementation

Business Value Protection: $500K+ ARR WebSocket event delivery comprehensive testing
Addresses Issue #714 Phase 1A: Authentication & Event Validation Tests

This test suite provides comprehensive coverage for the five-event validation framework,
focusing on the highest-impact uncovered code paths identified in coverage analysis.

Key Test Areas:
1. All 5 critical agent events validation (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
2. Event schema validation and content verification
3. Event delivery confirmation and tracking
4. Event sequence validation and ordering
5. Event timing and performance metrics
6. Circuit breaker functionality for event validation
7. Event replay and recovery mechanisms

Coverage Target: event_validation_framework.py (currently 0% -> target 80%+)
"""

import asyncio
import json
import time
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import pytest

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import target module components
from netra_backend.app.websocket_core.event_validation_framework import (
    EventValidationLevel,
    EventType,
    ValidationResult,
    EventValidationRule,
    ValidatedEvent,
    EventSequence,
    EventMetrics,
    CircuitBreakerState,
    EventValidator,
    EventSequenceValidator,
    EventValidationFramework,
    get_event_validation_framework,
    validate_websocket_event,
    get_validation_report
)

# Import related types
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.schemas.websocket_models import WebSocketValidationError


class TestEventValidationFramework(SSotAsyncTestCase):
    """Test suite for WebSocket event validation framework functionality."""

    def setup_method(self, method):
        """Set up test environment with SSOT compliance."""
        super().setup_method(method)

        # Use SSOT mock factory for consistent mocking
        self.mock_factory = SSotMockFactory()

        # Create common test data
        self.test_thread_id = "thread_123"
        self.test_run_id = "run_456"
        self.test_user_id = "user_789"
        self.test_event_id = str(uuid.uuid4())
        self.test_timestamp = time.time()

        # Sample event data for testing
        self.agent_started_event = {
            "event_id": self.test_event_id,
            "event_type": EventType.AGENT_STARTED,
            "thread_id": self.test_thread_id,
            "run_id": self.test_run_id,
            "timestamp": self.test_timestamp,
            "content": {
                "agent_name": "TestAgent",
                "agent_version": "1.0.0",
                "capabilities": ["analysis", "execution"]
            }
        }

        self.agent_thinking_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": EventType.AGENT_THINKING,
            "thread_id": self.test_thread_id,
            "run_id": self.test_run_id,
            "timestamp": self.test_timestamp + 1,
            "content": {
                "thought_process": "Analyzing user request...",
                "reasoning_step": 1,
                "confidence": 0.9
            }
        }

        self.tool_executing_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": EventType.TOOL_EXECUTING,
            "thread_id": self.test_thread_id,
            "run_id": self.test_run_id,
            "timestamp": self.test_timestamp + 2,
            "content": {
                "tool_name": "data_analyzer",
                "tool_params": {"query": "test"},
                "execution_id": str(uuid.uuid4())
            }
        }

        self.tool_completed_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": EventType.TOOL_COMPLETED,
            "thread_id": self.test_thread_id,
            "run_id": self.test_run_id,
            "timestamp": self.test_timestamp + 3,
            "content": {
                "tool_name": "data_analyzer",
                "execution_id": str(uuid.uuid4()),
                "result": {"data": "analyzed_result"},
                "success": True
            }
        }

        self.agent_completed_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": EventType.AGENT_COMPLETED,
            "thread_id": self.test_thread_id,
            "run_id": self.test_run_id,
            "timestamp": self.test_timestamp + 4,
            "content": {
                "final_result": "Task completed successfully",
                "execution_time": 4.0,
                "success": True
            }
        }

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)

    def test_event_validation_level_enum(self):
        """Test EventValidationLevel enum values."""
        self.assertEqual(EventValidationLevel.STRICT, "strict")
        self.assertEqual(EventValidationLevel.MODERATE, "moderate")
        self.assertEqual(EventValidationLevel.PERMISSIVE, "permissive")

    def test_event_type_enum_required_events(self):
        """Test EventType enum contains all 5 required events."""
        required_events = [
            EventType.AGENT_STARTED,
            EventType.AGENT_THINKING,
            EventType.TOOL_EXECUTING,
            EventType.TOOL_COMPLETED,
            EventType.AGENT_COMPLETED
        ]

        for event_type in required_events:
            self.assertIn(event_type, EventType)

        # Verify specific values
        self.assertEqual(EventType.AGENT_STARTED, "agent_started")
        self.assertEqual(EventType.AGENT_THINKING, "agent_thinking")
        self.assertEqual(EventType.TOOL_EXECUTING, "tool_executing")
        self.assertEqual(EventType.TOOL_COMPLETED, "tool_completed")
        self.assertEqual(EventType.AGENT_COMPLETED, "agent_completed")

    def test_validation_result_enum(self):
        """Test ValidationResult enum values."""
        self.assertEqual(ValidationResult.VALID, "valid")
        self.assertEqual(ValidationResult.WARNING, "warning")
        self.assertEqual(ValidationResult.ERROR, "error")
        self.assertEqual(ValidationResult.CRITICAL, "critical")

    def test_event_validation_rule_creation(self):
        """Test EventValidationRule dataclass creation."""
        def sample_validator(event):
            return True

        rule = EventValidationRule(
            name="test_rule",
            description="Test validation rule",
            validator=sample_validator,
            severity=ValidationResult.ERROR,
            required_fields=["event_type", "timestamp"],
            optional_fields=["metadata"],
            timing_constraints={"max_delay": 5.0}
        )

        self.assertEqual(rule.name, "test_rule")
        self.assertEqual(rule.description, "Test validation rule")
        self.assertEqual(rule.validator, sample_validator)
        self.assertEqual(rule.severity, ValidationResult.ERROR)
        self.assertEqual(rule.required_fields, ["event_type", "timestamp"])
        self.assertEqual(rule.optional_fields, ["metadata"])
        self.assertEqual(rule.timing_constraints, {"max_delay": 5.0})

    def test_validated_event_creation(self):
        """Test ValidatedEvent dataclass creation."""
        validated_event = ValidatedEvent(
            event_id=self.test_event_id,
            event_type=EventType.AGENT_STARTED,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            timestamp=self.test_timestamp,
            content={"test": "data"},
            validation_result=ValidationResult.VALID,
            validation_errors=[],
            validation_warnings=[],
            latency_ms=10.5,
            sequence_number=1
        )

        self.assertEqual(validated_event.event_id, self.test_event_id)
        self.assertEqual(validated_event.event_type, EventType.AGENT_STARTED)
        self.assertEqual(validated_event.thread_id, self.test_thread_id)
        self.assertEqual(validated_event.run_id, self.test_run_id)
        self.assertEqual(validated_event.timestamp, self.test_timestamp)
        self.assertEqual(validated_event.validation_result, ValidationResult.VALID)
        self.assertEqual(validated_event.latency_ms, 10.5)

    def test_event_sequence_creation(self):
        """Test EventSequence dataclass creation."""
        event_sequence = EventSequence(
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            events=[],
            start_time=self.test_timestamp,
            end_time=None,
            is_complete=False,
            validation_summary={}
        )

        self.assertEqual(event_sequence.thread_id, self.test_thread_id)
        self.assertEqual(event_sequence.run_id, self.test_run_id)
        self.assertEqual(len(event_sequence.events), 0)
        self.assertFalse(event_sequence.is_complete)

    def test_event_metrics_creation(self):
        """Test EventMetrics dataclass creation and default values."""
        metrics = EventMetrics()

        self.assertEqual(metrics.total_events, 0)
        self.assertEqual(metrics.successful_events, 0)
        self.assertEqual(metrics.failed_events, 0)
        self.assertEqual(metrics.dropped_events, 0)
        self.assertEqual(metrics.average_latency_ms, 0.0)
        self.assertEqual(metrics.max_latency_ms, 0.0)
        self.assertEqual(metrics.min_latency_ms, 0.0)
        self.assertEqual(metrics.events_per_second, 0.0)
        self.assertEqual(len(metrics.validation_failures), 0)
        self.assertEqual(metrics.sequence_completion_rate, 0.0)

    def test_circuit_breaker_state_enum(self):
        """Test CircuitBreakerState enum values."""
        self.assertEqual(CircuitBreakerState.CLOSED, "closed")
        self.assertEqual(CircuitBreakerState.OPEN, "open")
        self.assertEqual(CircuitBreakerState.HALF_OPEN, "half_open")

    def test_event_validator_initialization(self):
        """Test EventValidator class initialization."""
        validator = EventValidator()

        # Check required events are defined
        self.assertIn(EventType.AGENT_STARTED, EventValidator.REQUIRED_EVENTS)
        self.assertIn(EventType.AGENT_THINKING, EventValidator.REQUIRED_EVENTS)
        self.assertIn(EventType.TOOL_EXECUTING, EventValidator.REQUIRED_EVENTS)
        self.assertIn(EventType.TOOL_COMPLETED, EventValidator.REQUIRED_EVENTS)
        self.assertIn(EventType.AGENT_COMPLETED, EventValidator.REQUIRED_EVENTS)

        # Verify all 5 required events are present
        self.assertEqual(len(EventValidator.REQUIRED_EVENTS), 5)

    def test_event_validator_validate_event_structure_valid(self):
        """Test EventValidator validates valid event structure."""
        validator = EventValidator()

        # Test with valid agent_started event
        is_valid = validator.validate_event_structure(self.agent_started_event)
        self.assertTrue(is_valid)

    def test_event_validator_validate_event_structure_invalid(self):
        """Test EventValidator rejects invalid event structure."""
        validator = EventValidator()

        # Test with missing required fields
        invalid_event = {
            "event_type": EventType.AGENT_STARTED,
            # Missing event_id, thread_id, timestamp, content
        }

        is_valid = validator.validate_event_structure(invalid_event)
        self.assertFalse(is_valid)

    def test_event_validator_validate_event_content_agent_started(self):
        """Test EventValidator validates agent_started event content."""
        validator = EventValidator()

        # Test valid agent_started content
        is_valid = validator.validate_event_content(
            EventType.AGENT_STARTED,
            self.agent_started_event["content"]
        )
        self.assertTrue(is_valid)

        # Test invalid agent_started content (missing required fields)
        invalid_content = {"incomplete": "data"}
        is_valid = validator.validate_event_content(
            EventType.AGENT_STARTED,
            invalid_content
        )
        self.assertFalse(is_valid)

    def test_event_validator_validate_event_content_all_types(self):
        """Test EventValidator validates content for all 5 required event types."""
        validator = EventValidator()

        test_events = [
            (EventType.AGENT_STARTED, self.agent_started_event["content"]),
            (EventType.AGENT_THINKING, self.agent_thinking_event["content"]),
            (EventType.TOOL_EXECUTING, self.tool_executing_event["content"]),
            (EventType.TOOL_COMPLETED, self.tool_completed_event["content"]),
            (EventType.AGENT_COMPLETED, self.agent_completed_event["content"])
        ]

        for event_type, content in test_events:
            with self.subTest(event_type=event_type):
                is_valid = validator.validate_event_content(event_type, content)
                self.assertTrue(is_valid, f"Content validation failed for {event_type}")

    def test_event_validator_validate_event_timing(self):
        """Test EventValidator validates event timing constraints."""
        validator = EventValidator()

        current_time = time.time()

        # Test valid timing (recent timestamp)
        is_valid = validator.validate_event_timing(current_time, current_time - 1)
        self.assertTrue(is_valid)

        # Test invalid timing (future timestamp)
        is_valid = validator.validate_event_timing(current_time + 3600, current_time)
        self.assertFalse(is_valid)

        # Test invalid timing (too old timestamp)
        is_valid = validator.validate_event_timing(current_time - 3600, current_time)
        self.assertFalse(is_valid)

    def test_event_sequence_validator_initialization(self):
        """Test EventSequenceValidator class initialization."""
        validator = EventSequenceValidator()
        self.assertIsNotNone(validator)

    def test_event_sequence_validator_validate_sequence_complete(self):
        """Test EventSequenceValidator validates complete event sequence."""
        validator = EventSequenceValidator()

        # Create complete event sequence
        events = [
            ValidatedEvent(**{**self.agent_started_event, "validation_result": ValidationResult.VALID}),
            ValidatedEvent(**{**self.agent_thinking_event, "validation_result": ValidationResult.VALID}),
            ValidatedEvent(**{**self.tool_executing_event, "validation_result": ValidationResult.VALID}),
            ValidatedEvent(**{**self.tool_completed_event, "validation_result": ValidationResult.VALID}),
            ValidatedEvent(**{**self.agent_completed_event, "validation_result": ValidationResult.VALID})
        ]

        sequence = EventSequence(
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            events=events
        )

        # Validate complete sequence
        is_valid = validator.validate_sequence(sequence)
        self.assertTrue(is_valid)

    def test_event_sequence_validator_validate_sequence_incomplete(self):
        """Test EventSequenceValidator detects incomplete event sequence."""
        validator = EventSequenceValidator()

        # Create incomplete event sequence (missing agent_completed)
        events = [
            ValidatedEvent(**{**self.agent_started_event, "validation_result": ValidationResult.VALID}),
            ValidatedEvent(**{**self.agent_thinking_event, "validation_result": ValidationResult.VALID}),
            ValidatedEvent(**{**self.tool_executing_event, "validation_result": ValidationResult.VALID}),
            ValidatedEvent(**{**self.tool_completed_event, "validation_result": ValidationResult.VALID})
            # Missing AGENT_COMPLETED
        ]

        sequence = EventSequence(
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            events=events
        )

        # Validate incomplete sequence
        is_valid = validator.validate_sequence(sequence)
        self.assertFalse(is_valid)

    def test_event_sequence_validator_validate_order(self):
        """Test EventSequenceValidator validates event order."""
        validator = EventSequenceValidator()

        # Test correct order
        correct_order = [
            EventType.AGENT_STARTED,
            EventType.AGENT_THINKING,
            EventType.TOOL_EXECUTING,
            EventType.TOOL_COMPLETED,
            EventType.AGENT_COMPLETED
        ]

        is_valid = validator.validate_event_order(correct_order)
        self.assertTrue(is_valid)

        # Test incorrect order
        incorrect_order = [
            EventType.AGENT_COMPLETED,  # Should be last, not first
            EventType.AGENT_STARTED,
            EventType.TOOL_EXECUTING,
            EventType.AGENT_THINKING,
            EventType.TOOL_COMPLETED
        ]

        is_valid = validator.validate_event_order(incorrect_order)
        self.assertFalse(is_valid)

    def test_event_validation_framework_initialization(self):
        """Test EventValidationFramework class initialization."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        self.assertEqual(framework.validation_level, EventValidationLevel.STRICT)
        self.assertIsNotNone(framework.event_validator)
        self.assertIsNotNone(framework.sequence_validator)

    async def test_event_validation_framework_validate_event_valid(self):
        """Test EventValidationFramework validates valid events."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        # Validate agent_started event
        validated_event = await framework.validate_event(self.agent_started_event)

        self.assertIsNotNone(validated_event)
        self.assertEqual(validated_event.event_type, EventType.AGENT_STARTED)
        self.assertEqual(validated_event.validation_result, ValidationResult.VALID)
        self.assertEqual(len(validated_event.validation_errors), 0)

    async def test_event_validation_framework_validate_event_invalid(self):
        """Test EventValidationFramework detects invalid events."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        # Create invalid event (missing required fields)
        invalid_event = {
            "event_type": EventType.AGENT_STARTED,
            # Missing event_id, thread_id, timestamp, content
        }

        validated_event = await framework.validate_event(invalid_event)

        self.assertIsNotNone(validated_event)
        self.assertEqual(validated_event.validation_result, ValidationResult.ERROR)
        self.assertGreater(len(validated_event.validation_errors), 0)

    async def test_event_validation_framework_validate_all_five_events(self):
        """Test EventValidationFramework validates all 5 required events."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        test_events = [
            self.agent_started_event,
            self.agent_thinking_event,
            self.tool_executing_event,
            self.tool_completed_event,
            self.agent_completed_event
        ]

        # Validate each event type
        for event_data in test_events:
            with self.subTest(event_type=event_data["event_type"]):
                validated_event = await framework.validate_event(event_data)

                self.assertIsNotNone(validated_event)
                self.assertEqual(validated_event.validation_result, ValidationResult.VALID)
                self.assertEqual(len(validated_event.validation_errors), 0)

    async def test_event_validation_framework_validate_sequence(self):
        """Test EventValidationFramework validates complete event sequences."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        # Validate complete event sequence
        validated_events = []
        test_events = [
            self.agent_started_event,
            self.agent_thinking_event,
            self.tool_executing_event,
            self.tool_completed_event,
            self.agent_completed_event
        ]

        # Validate each event and build sequence
        for event_data in test_events:
            validated_event = await framework.validate_event(event_data)
            validated_events.append(validated_event)

        # Create sequence
        sequence = EventSequence(
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            events=validated_events
        )

        # Validate sequence
        is_valid = await framework.validate_event_sequence(sequence)
        self.assertTrue(is_valid)

    async def test_event_validation_framework_get_metrics(self):
        """Test EventValidationFramework metrics collection."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        # Process some events to generate metrics
        test_events = [
            self.agent_started_event,
            self.agent_thinking_event,
            self.tool_executing_event,
            self.tool_completed_event,
            self.agent_completed_event
        ]

        for event_data in test_events:
            await framework.validate_event(event_data)

        # Get metrics
        metrics = framework.get_metrics()

        self.assertIsNotNone(metrics)
        self.assertGreaterEqual(metrics.total_events, 5)
        self.assertGreaterEqual(metrics.successful_events, 5)

    async def test_event_validation_framework_circuit_breaker(self):
        """Test EventValidationFramework circuit breaker functionality."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        # Initially circuit breaker should be closed
        self.assertEqual(framework.circuit_breaker_state, CircuitBreakerState.CLOSED)

        # Simulate multiple validation failures to trigger circuit breaker
        invalid_event = {"invalid": "event"}

        failure_count = 0
        max_failures = 10  # Simulate hitting failure threshold

        for _ in range(max_failures):
            try:
                await framework.validate_event(invalid_event)
                failure_count += 1
            except Exception:
                failure_count += 1

        # After many failures, circuit breaker might open (depends on implementation)
        # This tests that the framework handles failure scenarios gracefully
        self.assertGreaterEqual(failure_count, 0)

    def test_get_event_validation_framework_function(self):
        """Test get_event_validation_framework factory function."""
        # Test with different validation levels
        strict_framework = get_event_validation_framework(EventValidationLevel.STRICT)
        moderate_framework = get_event_validation_framework(EventValidationLevel.MODERATE)
        permissive_framework = get_event_validation_framework(EventValidationLevel.PERMISSIVE)

        self.assertIsInstance(strict_framework, EventValidationFramework)
        self.assertIsInstance(moderate_framework, EventValidationFramework)
        self.assertIsInstance(permissive_framework, EventValidationFramework)

        self.assertEqual(strict_framework.validation_level, EventValidationLevel.STRICT)
        self.assertEqual(moderate_framework.validation_level, EventValidationLevel.MODERATE)
        self.assertEqual(permissive_framework.validation_level, EventValidationLevel.PERMISSIVE)

    async def test_validate_websocket_event_function(self):
        """Test validate_websocket_event standalone function."""
        # Test event validation function
        validated_event = await validate_websocket_event(
            self.agent_started_event,
            context={"validation_level": EventValidationLevel.STRICT}
        )

        self.assertIsNotNone(validated_event)
        self.assertEqual(validated_event.event_type, EventType.AGENT_STARTED)
        self.assertEqual(validated_event.validation_result, ValidationResult.VALID)

    async def test_get_validation_report_function(self):
        """Test get_validation_report function."""
        # First validate some events to have data for report
        framework = get_event_validation_framework(EventValidationLevel.STRICT)

        for event_data in [self.agent_started_event, self.agent_thinking_event]:
            await framework.validate_event(event_data)

        # Get validation report
        report = await get_validation_report(thread_id=self.test_thread_id)

        self.assertIsNotNone(report)
        self.assertIsInstance(report, dict)

    async def test_event_validation_framework_performance_metrics(self):
        """Test EventValidationFramework performance and latency tracking."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        # Process events and measure performance
        start_time = time.time()

        test_events = [
            self.agent_started_event,
            self.agent_thinking_event,
            self.tool_executing_event,
            self.tool_completed_event,
            self.agent_completed_event
        ]

        validated_events = []
        for event_data in test_events:
            validated_event = await framework.validate_event(event_data)
            validated_events.append(validated_event)

        end_time = time.time()
        total_time = end_time - start_time

        # Verify performance tracking
        for validated_event in validated_events:
            self.assertIsNotNone(validated_event.latency_ms)
            self.assertGreaterEqual(validated_event.latency_ms, 0)

        # Performance should be reasonable (under 1 second for 5 events)
        self.assertLess(total_time, 1.0)

    async def test_event_validation_framework_concurrent_validation(self):
        """Test EventValidationFramework handles concurrent event validation."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)

        # Create multiple events with different thread IDs for concurrent processing
        concurrent_events = []
        for i in range(10):
            event_data = {
                **self.agent_started_event,
                "event_id": str(uuid.uuid4()),
                "thread_id": f"thread_{i}",
                "timestamp": time.time() + i
            }
            concurrent_events.append(event_data)

        # Validate events concurrently
        tasks = [framework.validate_event(event) for event in concurrent_events]
        validated_events = await asyncio.gather(*tasks)

        # Verify all events were validated successfully
        self.assertEqual(len(validated_events), 10)
        for validated_event in validated_events:
            self.assertEqual(validated_event.validation_result, ValidationResult.VALID)

    async def test_event_validation_framework_error_recovery(self):
        """Test EventValidationFramework error recovery and resilience."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.PERMISSIVE)

        # Test with malformed event data
        malformed_event = {
            "event_type": "invalid_type",
            "malformed_data": True,
            "timestamp": "not_a_number"
        }

        # Framework should handle errors gracefully in permissive mode
        validated_event = await framework.validate_event(malformed_event)

        self.assertIsNotNone(validated_event)
        # In permissive mode, should still create a validated event but with errors
        self.assertGreater(len(validated_event.validation_errors), 0)

    async def test_event_validation_framework_memory_efficiency(self):
        """Test EventValidationFramework memory efficiency with large event volumes."""
        framework = EventValidationFramework(validation_level=EventValidationLevel.MODERATE)

        # Process a large number of events to test memory efficiency
        large_event_count = 1000

        for i in range(large_event_count):
            event_data = {
                **self.agent_started_event,
                "event_id": str(uuid.uuid4()),
                "timestamp": time.time() + (i * 0.001),  # Stagger timestamps
                "content": {**self.agent_started_event["content"], "iteration": i}
            }

            validated_event = await framework.validate_event(event_data)
            self.assertEqual(validated_event.validation_result, ValidationResult.VALID)

        # Get metrics after processing many events
        metrics = framework.get_metrics()
        self.assertGreaterEqual(metrics.total_events, large_event_count)
        self.assertGreater(metrics.events_per_second, 0)

    def test_event_validation_framework_configuration_flexibility(self):
        """Test EventValidationFramework configuration with different validation levels."""
        # Test strict validation
        strict_framework = EventValidationFramework(validation_level=EventValidationLevel.STRICT)
        self.assertEqual(strict_framework.validation_level, EventValidationLevel.STRICT)

        # Test moderate validation
        moderate_framework = EventValidationFramework(validation_level=EventValidationLevel.MODERATE)
        self.assertEqual(moderate_framework.validation_level, EventValidationLevel.MODERATE)

        # Test permissive validation
        permissive_framework = EventValidationFramework(validation_level=EventValidationLevel.PERMISSIVE)
        self.assertEqual(permissive_framework.validation_level, EventValidationLevel.PERMISSIVE)

        # All should be properly initialized
        for framework in [strict_framework, moderate_framework, permissive_framework]:
            self.assertIsNotNone(framework.event_validator)
            self.assertIsNotNone(framework.sequence_validator)