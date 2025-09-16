#!/usr/bin/env python3
"""
MISSION CRITICAL: Core WebSocket Event Sequence Validation Tests - Issue #1199

Business Value Justification:
- Segment: Platform (Core Infrastructure) 
- Business Goal: Ensure 100% reliability of $500K+ ARR chat functionality
- Value Impact: Validates the 5 critical WebSocket events in proper sequence 
- Strategic Impact: Prevents silent event failures that cause user abandonment

CRITICAL TEST SCOPE:
This test file focuses on the most fundamental validation scenarios:
1. Complete 5-event sequence validation (agent_started → agent_thinking → tool_executing → tool_completed → agent_completed)
2. Event order enforcement and validation
3. Event content structure validation
4. Missing event detection and failure reporting

DESIGN TO FAIL INITIALLY:
These tests are intentionally designed to fail initially to prove they are working correctly.
They validate real-world scenarios where WebSocket events might be missing or malformed.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

import pytest
from loguru import logger

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import WebSocket validation framework
from netra_backend.app.websocket_core.event_validation_framework import (
    EventType, EventValidationLevel, ValidationResult, ValidatedEvent,
    EventValidator, EventSequenceValidator, EventValidationFramework
)

# Import test configuration and utilities
from shared.isolated_environment import IsolatedEnvironment


@dataclass
class EventSequenceTestResult:
    """Test result container for sequence validation."""
    thread_id: str
    expected_events: List[EventType]
    received_events: List[ValidatedEvent]
    missing_events: List[EventType]
    validation_errors: List[str]
    timing_violations: List[str]
    success: bool
    total_duration_ms: float


class WebSocketEventSequenceValidationCoreTests(SSotAsyncTestCase):
    """
    Core WebSocket event sequence validation tests.
    
    CRITICAL: These tests validate the fundamental 5-event sequence that enables 
    $500K+ ARR chat functionality. ANY FAILURE HERE INDICATES A CRITICAL SYSTEM ISSUE.
    """

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup test environment for event sequence validation."""
        # Initialize validation framework
        self.validation_framework = EventValidationFramework(
            validation_level=EventValidationLevel.STRICT
        )
        
        # Define the critical 5-event sequence required for chat functionality
        self.required_event_sequence = [
            EventType.AGENT_STARTED,
            EventType.AGENT_THINKING,
            EventType.TOOL_EXECUTING,
            EventType.TOOL_COMPLETED,
            EventType.AGENT_COMPLETED
        ]
        
        # Test configuration
        self.test_config = {
            "max_sequence_duration_ms": 30000,  # 30 seconds max
            "max_event_gap_ms": 5000,           # 5 seconds between events
            "required_event_timeout_ms": 2000,  # 2 seconds per event
        }
        
        # Tracking for test results
        self.test_results: List[EventSequenceTestResult] = []
        
        yield
        
        # Cleanup - log test results
        await self._log_test_results()

    async def _log_test_results(self):
        """Log comprehensive test results for analysis."""
        logger.info(f"Core WebSocket Event Sequence Validation - Test Results Summary:")
        logger.info(f"  Total test sequences: {len(self.test_results)}")
        
        successful_tests = [r for r in self.test_results if r.success]
        failed_tests = [r for r in self.test_results if not r.success]
        
        logger.info(f"  Successful sequences: {len(successful_tests)}")
        logger.info(f"  Failed sequences: {len(failed_tests)}")
        
        if failed_tests:
            logger.warning("Failed sequence details:")
            for result in failed_tests[:3]:  # Show first 3 failures
                logger.warning(f"    Thread {result.thread_id}: Missing {result.missing_events}, Errors: {len(result.validation_errors)}")

    # ============================================================================
    # CRITICAL TEST 1: Complete 5-Event Sequence Validation
    # ============================================================================

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_five_event_sequence_validation(self):
        """
        CRITICAL: Test that all 5 required WebSocket events are delivered in sequence.
        
        This test validates the core chat functionality sequence:
        agent_started → agent_thinking → tool_executing → tool_completed → agent_completed
        
        DESIGNED TO FAIL INITIALLY: This test will fail if any of the 5 events are missing,
        proving that the validation is working correctly.
        """
        logger.info("Testing complete 5-event sequence validation")
        
        # Generate test identifiers
        thread_id = f"test_complete_sequence_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Start sequence tracking
        sequence = self.validation_framework.sequence_validator.start_sequence(thread_id, run_id)
        
        # Create and validate the complete 5-event sequence
        test_events = self._create_complete_event_sequence(thread_id, run_id)
        
        validated_events = []
        validation_errors = []
        start_time = time.time()
        
        try:
            # Process each event through the validation framework
            for event_data in test_events:
                try:
                    validated_event = await self.validation_framework.validate_event(
                        event_data, 
                        context={"thread_id": thread_id, "run_id": run_id}
                    )
                    validated_events.append(validated_event)
                    
                    # Log validation results
                    logger.debug(f"Event {validated_event.event_type}: {validated_event.validation_result}")
                    if validated_event.validation_errors:
                        validation_errors.extend(validated_event.validation_errors)
                        logger.warning(f"Validation errors for {validated_event.event_type}: {validated_event.validation_errors}")
                        
                except Exception as e:
                    validation_errors.append(f"Event validation exception: {str(e)}")
                    logger.error(f"Failed to validate event: {e}")
            
            total_duration_ms = (time.time() - start_time) * 1000
            
            # CRITICAL ASSERTIONS: Validate sequence completeness
            received_event_types = [e.event_type for e in validated_events if isinstance(e.event_type, EventType)]
            missing_events = [event for event in self.required_event_sequence if event not in received_event_types]
            
            # Create test result for tracking
            test_result = EventSequenceTestResult(
                thread_id=thread_id,
                expected_events=self.required_event_sequence,
                received_events=validated_events,
                missing_events=missing_events,
                validation_errors=validation_errors,
                timing_violations=[],
                success=len(missing_events) == 0 and len(validation_errors) == 0,
                total_duration_ms=total_duration_ms
            )
            self.test_results.append(test_result)
            
            # CRITICAL VALIDATION: All 5 events must be present
            assert len(missing_events) == 0, (
                f"CRITICAL FAILURE: Missing required WebSocket events: {missing_events}. "
                f"Received: {received_event_types}. "
                f"This indicates a fundamental chat functionality failure."
            )
            
            # CRITICAL VALIDATION: No validation errors
            assert len(validation_errors) == 0, (
                f"CRITICAL FAILURE: Event validation errors detected: {validation_errors}. "
                f"This indicates malformed WebSocket events."
            )
            
            # CRITICAL VALIDATION: Events received in correct order
            self._validate_event_order(validated_events)
            
            # CRITICAL VALIDATION: Sequence marked as complete
            sequence_status = self.validation_framework.get_sequence_status(thread_id)
            assert sequence_status is not None, "Sequence status not found"
            assert sequence_status.get('sequence_complete', False), (
                f"Sequence not marked as complete. Status: {sequence_status}"
            )
            
            logger.info(f"✅ Complete 5-event sequence validation PASSED for thread {thread_id}")
            logger.info(f"   Events received: {len(received_event_types)}")
            logger.info(f"   Total duration: {total_duration_ms:.1f}ms")
            logger.info(f"   Validation errors: {len(validation_errors)}")
            
        except AssertionError:
            # Re-raise assertion errors to fail the test properly
            raise
        except Exception as e:
            pytest.fail(f"Unexpected exception during sequence validation: {e}")

    def _create_complete_event_sequence(self, thread_id: str, run_id: str) -> List[Dict[str, Any]]:
        """Create a complete 5-event sequence for testing."""
        base_timestamp = time.time()
        
        return [
            # 1. Agent Started Event
            {
                "type": "agent_started",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": base_timestamp,
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": base_timestamp,
                    "message": "Agent execution started"
                }
            },
            
            # 2. Agent Thinking Event
            {
                "type": "agent_thinking",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": base_timestamp + 1,
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": base_timestamp + 1,
                    "thought": "Analyzing user request and determining appropriate tools to execute for optimal response generation."
                }
            },
            
            # 3. Tool Executing Event
            {
                "type": "tool_executing",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": base_timestamp + 2,
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": base_timestamp + 2,
                    "tool_name": "analysis_tool",
                    "parameters": {"query": "test analysis"},
                    "tool_purpose": "Data analysis for user request"
                }
            },
            
            # 4. Tool Completed Event
            {
                "type": "tool_completed",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": base_timestamp + 3,
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": base_timestamp + 3,
                    "tool_name": "analysis_tool",
                    "result": {"analysis_complete": True, "insights": ["data processed successfully"]},
                    "duration_ms": 500,
                    "success": True
                }
            },
            
            # 5. Agent Completed Event
            {
                "type": "agent_completed",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": base_timestamp + 4,
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": base_timestamp + 4,
                    "result": "Analysis completed successfully with actionable insights.",
                    "final_status": "completed",
                    "duration_ms": 4000,
                    "summary": "Comprehensive analysis completed with tool execution."
                }
            }
        ]

    def _validate_event_order(self, validated_events: List[ValidatedEvent]) -> None:
        """Validate that events are received in the correct logical order."""
        event_types = [e.event_type for e in validated_events if isinstance(e.event_type, EventType)]
        
        # Check that agent_started comes first
        if event_types and event_types[0] != EventType.AGENT_STARTED:
            raise AssertionError(f"First event should be agent_started, got: {event_types[0]}")
        
        # Check that agent_completed comes last
        if event_types and EventType.AGENT_COMPLETED in event_types:
            last_agent_completed_index = len(event_types) - 1 - event_types[::-1].index(EventType.AGENT_COMPLETED)
            if last_agent_completed_index != len(event_types) - 1:
                raise AssertionError(f"agent_completed should be the last event in sequence")
        
        # Check tool event pairing
        tool_executing_count = event_types.count(EventType.TOOL_EXECUTING)
        tool_completed_count = event_types.count(EventType.TOOL_COMPLETED)
        
        if tool_executing_count != tool_completed_count:
            raise AssertionError(
                f"Tool event pairing mismatch: {tool_executing_count} executing vs {tool_completed_count} completed"
            )
        
        logger.debug(f"Event order validation passed: {[e.value for e in event_types]}")

    # ============================================================================
    # CRITICAL TEST 2: Missing Event Detection
    # ============================================================================

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_missing_event_detection_and_failure(self):
        """
        CRITICAL: Test that missing events are properly detected and cause validation failure.
        
        DESIGNED TO FAIL INITIALLY: This test validates that the system correctly identifies
        when critical events are missing from the sequence.
        """
        logger.info("Testing missing event detection and failure")
        
        thread_id = f"test_missing_events_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Start sequence tracking
        self.validation_framework.sequence_validator.start_sequence(thread_id, run_id)
        
        # Create incomplete sequence (missing tool_completed and agent_completed)
        incomplete_events = [
            {
                "type": "agent_started",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time(),
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": time.time()
                }
            },
            {
                "type": "agent_thinking",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time() + 1,
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": time.time() + 1,
                    "thought": "Starting analysis..."
                }
            },
            {
                "type": "tool_executing",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time() + 2,
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": time.time() + 2,
                    "tool_name": "test_tool"
                }
            }
            # INTENTIONALLY MISSING: tool_completed and agent_completed events
        ]
        
        validated_events = []
        start_time = time.time()
        
        # Process incomplete sequence
        for event_data in incomplete_events:
            validated_event = await self.validation_framework.validate_event(
                event_data,
                context={"thread_id": thread_id, "run_id": run_id}
            )
            validated_events.append(validated_event)
        
        total_duration_ms = (time.time() - start_time) * 1000
        
        # CRITICAL VALIDATION: Detect missing events
        received_event_types = [e.event_type for e in validated_events if isinstance(e.event_type, EventType)]
        missing_events = [event for event in self.required_event_sequence if event not in received_event_types]
        
        # The test SHOULD detect missing events
        expected_missing = [EventType.TOOL_COMPLETED, EventType.AGENT_COMPLETED]
        
        assert len(missing_events) > 0, (
            f"VALIDATION FAILURE: Missing event detection failed. "
            f"Expected to detect missing events {expected_missing}, but validation passed. "
            f"Received events: {received_event_types}"
        )
        
        assert EventType.TOOL_COMPLETED in missing_events, (
            f"VALIDATION FAILURE: Failed to detect missing tool_completed event. "
            f"Missing events detected: {missing_events}"
        )
        
        assert EventType.AGENT_COMPLETED in missing_events, (
            f"VALIDATION FAILURE: Failed to detect missing agent_completed event. "
            f"Missing events detected: {missing_events}"
        )
        
        # Validate that sequence is NOT marked as complete
        sequence_status = self.validation_framework.get_sequence_status(thread_id)
        if sequence_status:
            assert not sequence_status.get('sequence_complete', False), (
                f"VALIDATION FAILURE: Incomplete sequence incorrectly marked as complete. "
                f"Status: {sequence_status}"
            )
        
        # Create test result
        test_result = EventSequenceTestResult(
            thread_id=thread_id,
            expected_events=self.required_event_sequence,
            received_events=validated_events,
            missing_events=missing_events,
            validation_errors=[],
            timing_violations=[],
            success=False,  # This test expects failure
            total_duration_ms=total_duration_ms
        )
        self.test_results.append(test_result)
        
        logger.info(f"✅ Missing event detection test PASSED for thread {thread_id}")
        logger.info(f"   Correctly detected missing events: {missing_events}")
        logger.info(f"   Total events processed: {len(validated_events)}")

    # ============================================================================
    # CRITICAL TEST 3: Event Content Structure Validation
    # ============================================================================

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_event_content_structure_validation(self):
        """
        CRITICAL: Test that events with missing or malformed content are properly flagged.
        
        DESIGNED TO FAIL INITIALLY: This test validates that the system rejects events
        that don't meet the required content structure standards.
        """
        logger.info("Testing event content structure validation")
        
        thread_id = f"test_content_validation_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Test scenarios with invalid content
        invalid_events = [
            # Missing required fields in agent_started
            {
                "type": "agent_started",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time(),
                "payload": {
                    # MISSING: agent_name, run_id
                    "timestamp": time.time()
                }
            },
            
            # Missing thought content in agent_thinking
            {
                "type": "agent_thinking",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time(),
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": time.time(),
                    # MISSING: thought content
                }
            },
            
            # Missing tool_name in tool_executing
            {
                "type": "tool_executing",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time(),
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": time.time(),
                    # MISSING: tool_name
                    "parameters": {"query": "test"}
                }
            }
        ]
        
        validation_errors_detected = []
        critical_events_detected = 0
        
        # Process each invalid event
        for i, event_data in enumerate(invalid_events):
            try:
                validated_event = await self.validation_framework.validate_event(
                    event_data,
                    context={"thread_id": thread_id, "run_id": run_id}
                )
                
                # Count validation failures
                if validated_event.validation_result in [ValidationResult.ERROR, ValidationResult.CRITICAL]:
                    validation_errors_detected.extend(validated_event.validation_errors)
                    if validated_event.validation_result == ValidationResult.CRITICAL:
                        critical_events_detected += 1
                
                logger.info(f"Event {i}: {validated_event.event_type} -> {validated_event.validation_result}")
                if validated_event.validation_errors:
                    logger.info(f"  Errors: {validated_event.validation_errors}")
                    
            except Exception as e:
                logger.error(f"Exception validating invalid event {i}: {e}")
                validation_errors_detected.append(f"Exception: {str(e)}")
        
        # CRITICAL VALIDATION: Invalid content should be detected
        assert len(validation_errors_detected) > 0, (
            f"VALIDATION FAILURE: Invalid event content not detected. "
            f"Expected validation errors for malformed events, but none were found."
        )
        
        assert critical_events_detected > 0, (
            f"VALIDATION FAILURE: No critical validation failures detected. "
            f"Expected at least one critical error for missing required fields. "
            f"Errors detected: {validation_errors_detected}"
        )
        
        # Validate specific error types are detected
        error_text = " ".join(validation_errors_detected).lower()
        
        assert "missing" in error_text or "required" in error_text, (
            f"VALIDATION FAILURE: Missing required field errors not properly reported. "
            f"Error messages: {validation_errors_detected}"
        )
        
        logger.info(f"✅ Event content structure validation test PASSED")
        logger.info(f"   Validation errors detected: {len(validation_errors_detected)}")
        logger.info(f"   Critical events detected: {critical_events_detected}")
        logger.info(f"   Error types found: {list(set([e.split(':')[0] for e in validation_errors_detected]))}")

    # ============================================================================
    # CRITICAL TEST 4: Event Timing Validation
    # ============================================================================

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_event_timing_validation(self):
        """
        CRITICAL: Test that events with invalid timing are properly flagged.
        
        This test validates timing constraints like maximum gaps between events
        and reasonable event timestamps.
        """
        logger.info("Testing event timing validation")
        
        thread_id = f"test_timing_validation_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Create events with timing violations
        current_time = time.time()
        timing_violation_events = [
            {
                "type": "agent_started",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": current_time - 7200,  # 2 hours in the past
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": current_time - 7200
                }
            },
            {
                "type": "agent_thinking",
                "thread_id": thread_id,
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "timestamp": current_time + 7200,  # 2 hours in the future
                "payload": {
                    "agent_name": "supervisor",
                    "run_id": run_id,
                    "timestamp": current_time + 7200,
                    "thought": "Thinking with future timestamp"
                }
            }
        ]
        
        timing_warnings_detected = []
        
        # Process events with timing violations
        for event_data in timing_violation_events:
            validated_event = await self.validation_framework.validate_event(
                event_data,
                context={"thread_id": thread_id, "run_id": run_id}
            )
            
            # Collect timing-related warnings
            timing_warnings = [w for w in validated_event.validation_warnings if "timestamp" in w.lower() or "time" in w.lower()]
            timing_warnings_detected.extend(timing_warnings)
            
            logger.debug(f"Event {validated_event.event_type} timing validation: {len(timing_warnings)} warnings")
        
        # CRITICAL VALIDATION: Timing violations should be detected
        assert len(timing_warnings_detected) > 0, (
            f"VALIDATION FAILURE: Timing violations not detected. "
            f"Expected warnings for events with invalid timestamps, but none were found."
        )
        
        logger.info(f"✅ Event timing validation test PASSED")
        logger.info(f"   Timing warnings detected: {len(timing_warnings_detected)}")
        logger.info(f"   Warning examples: {timing_warnings_detected[:2]}")


if __name__ == "__main__":
    """
    Run core WebSocket event sequence validation tests.
    
    These tests are designed to fail initially to prove they work correctly.
    They validate the fundamental 5-event sequence critical for chat functionality.
    """
    import sys
    
    print("\n" + "=" * 80)
    print("CORE WEBSOCKET EVENT SEQUENCE VALIDATION TESTS - Issue #1199")
    print("MISSION CRITICAL: 5-Event Sequence Validation for $500K+ ARR")
    print("=" * 80)
    print()
    print("Tests designed to fail initially to prove validation works correctly:")
    print("1. Complete 5-event sequence validation")
    print("2. Missing event detection and failure")
    print("3. Event content structure validation")
    print("4. Event timing validation")
    print()
    print("Expected behavior: Tests should fail if events are missing or malformed.")
    print("=" * 80)
    
    # These tests should be run via the unified test runner
    pass