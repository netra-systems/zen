"""
WebSocket Event Validator Comprehensive Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Revenue Protection Infrastructure  
- Business Goal: Protect $500K+ ARR through bulletproof event validation
- Value Impact: Prevents silent failures in 5 critical events that deliver 90% of platform value
- Strategic Impact: Ensures chat functionality reliability, preventing revenue loss

Mission: Test all aspects of UnifiedEventValidator to prevent typos, silent failures,
and cross-user leakage in the 5 critical WebSocket events that power user-visible AI responses.

These tests MUST catch the exact brittle points identified in CRITICAL_BRITTLE_POINTS_AUDIT_20250110:
1. Event name typos (agent_started vs "agnt_started")
2. Silent validation failures  
3. User context isolation breaches
4. Performance degradation (>1ms per event)
5. Business value scoring accuracy

CRITICAL: These tests protect revenue by ensuring users see real-time AI value delivery.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
from unittest.mock import Mock, patch, AsyncMock

# SSOT test imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.event_validator import (
    UnifiedEventValidator,
    ValidationResult,
    WebSocketEventMessage, 
    EventCriticality,
    CriticalAgentEventType,
    get_critical_event_types,
    create_mock_critical_events,
    assert_critical_events_received
)
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID


class TestUnifiedEventValidatorUnit(SSotAsyncTestCase):
    """
    Unit tests for UnifiedEventValidator protecting $500K+ ARR.
    
    Focus: Individual method validation, edge cases, performance benchmarks.
    Coverage: All validation modes, error conditions, business value scoring.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Create test user context
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.test_connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Create strongly typed user execution context
        self.user_context = StronglyTypedUserExecutionContext(
            user_id=UserID(self.test_user_id),
            thread_id=ThreadID(self.test_thread_id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}")
        )
        
        # Initialize validators for different modes
        self.realtime_validator = UnifiedEventValidator(
            user_context=self.user_context,
            validation_mode="realtime",
            strict_mode=True
        )
        
        self.sequence_validator = UnifiedEventValidator(
            user_context=self.user_context,
            validation_mode="sequence", 
            strict_mode=True
        )
        
    # === BASIC STRUCTURE VALIDATION TESTS ===
    
    def test_basic_structure_validation_success(self):
        """Test basic event structure validation passes for valid events."""
        valid_event = {
            "type": "agent_started",
            "run_id": "test_run_123",
            "agent_name": "TestAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        result = self.realtime_validator.validate_event(valid_event, self.test_user_id, self.test_connection_id)
        
        self.assertTrue(result.is_valid, f"Valid event should pass validation: {result.error_message}")
        self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
        self.assertIn("agent_started", result.received_events)
        
    def test_basic_structure_validation_fails_non_dict(self):
        """Test validation FAILS LOUDLY for non-dictionary events."""
        invalid_events = [
            "not a dict",
            ["list", "not", "dict"],
            None,
            42,
            True
        ]
        
        for invalid_event in invalid_events:
            result = self.realtime_validator.validate_event(invalid_event, self.test_user_id, self.test_connection_id)
            
            self.assertFalse(result.is_valid, f"Non-dict event should fail validation: {invalid_event}")
            self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
            self.assertIsNotNone(result.error_message, "Should provide error message for invalid structure")
            self.assertIn("not a dictionary", result.error_message.lower())
    
    def test_basic_structure_validation_fails_missing_type(self):
        """Test validation FAILS LOUDLY when event type is missing."""
        events_missing_type = [
            {},  # No type field
            {"data": "some data"},  # Has data but no type
            {"type": None},  # Null type
            {"type": ""},  # Empty type
            {"type": "   "},  # Whitespace only type
        ]
        
        for event in events_missing_type:
            result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
            
            self.assertFalse(result.is_valid, f"Event without valid type should fail: {event}")
            self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
            self.assertIsNotNone(result.error_message)
            self.assertTrue(
                "missing" in result.error_message.lower() or "empty" in result.error_message.lower(),
                f"Error message should mention missing/empty type: {result.error_message}"
            )
    
    # === CRITICAL EVENT TYPO DETECTION TESTS ===
    
    def test_critical_event_typo_detection_agent_started(self):
        """Test LOUD failure for agent_started typos - CRITICAL REVENUE PROTECTION."""
        typo_variations = [
            "agnt_started",  # Missing 'e' 
            "agent_stared",  # Missing 't'
            "agent_start",   # Missing 'ed'
            "agentstarted",  # Missing underscore
            "Agent_Started", # Wrong capitalization
            "agent_starting", # Wrong suffix
        ]
        
        for typo in typo_variations:
            event = {
                "type": typo,
                "run_id": "test_run_123", 
                "agent_name": "TestAgent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"status": "started"}
            }
            
            result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
            
            # The event should still be valid as a basic event but won't be recognized as mission critical
            # The key test is that it doesn't get classified as mission critical
            if result.is_valid:
                # If valid, it should NOT be classified as mission critical
                self.assertNotEqual(result.criticality, EventCriticality.MISSION_CRITICAL,
                                   f"Typo event '{typo}' should NOT be classified as mission critical")
                
                # Business value score should be lower since this isn't a recognized critical event
                self.assertLess(result.business_value_score, 100.0,
                               f"Typo event '{typo}' should have reduced business value score")
    
    def test_critical_event_typo_detection_all_events(self):
        """Test typo detection for ALL 5 critical events - COMPREHENSIVE REVENUE PROTECTION."""
        critical_events_typos = {
            "agent_started": ["agnt_started", "agent_stared", "agentstarted"],
            "agent_thinking": ["agent_thinkng", "agent_thinking", "agentthinking"],  
            "tool_executing": ["tool_executng", "toolexecuting", "tool_execute"],
            "tool_completed": ["tool_completd", "toolcompleted", "tool_complete"],
            "agent_completed": ["agent_completd", "agentcompleted", "agent_complete"]
        }
        
        for correct_event, typos in critical_events_typos.items():
            for typo in typos:
                # Skip the correct event name in test data
                if typo == correct_event:
                    continue
                    
                event = {
                    "type": typo,
                    "run_id": "test_run_123",
                    "agent_name": "TestAgent", 
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"status": "test"}
                }
                
                result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
                
                # Log the typo for auditing
                self.record_metric(f"typo_detected_{correct_event}", typo)
                
                # Verify typo is not classified as mission critical
                if result.is_valid:
                    self.assertNotEqual(result.criticality, EventCriticality.MISSION_CRITICAL,
                                       f"Typo '{typo}' for '{correct_event}' must not be mission critical")
    
    # === MISSION CRITICAL EVENT VALIDATION TESTS ===
    
    def test_mission_critical_event_validation_success(self):
        """Test mission critical event validation success path."""
        critical_events = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        ]
        
        for event_type in critical_events:
            event = {
                "type": event_type,
                "run_id": "test_run_123",
                "agent_name": "TestAgent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"status": "test", "data": "valid"}
            }
            
            result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
            
            self.assertTrue(result.is_valid, f"Mission critical event {event_type} should be valid")
            self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
            self.assertIsNone(result.error_message, f"No error for valid {event_type}")
            
    def test_mission_critical_event_validation_fails_missing_run_id(self):
        """Test mission critical events FAIL LOUDLY without run_id."""
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for event_type in critical_events:
            invalid_run_ids = [None, "", "   ", 123, [], {}]
            
            for invalid_run_id in invalid_run_ids:
                event = {
                    "type": event_type,
                    "agent_name": "TestAgent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"status": "test"}
                }
                
                if invalid_run_id is not None:
                    event["run_id"] = invalid_run_id
                    
                result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
                
                self.assertFalse(result.is_valid, 
                               f"Mission critical event {event_type} should fail without valid run_id")
                self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
                self.assertIn("run_id", result.error_message.lower())
                self.assertIn("chat value lost", result.business_impact.lower())
    
    def test_mission_critical_event_validation_fails_missing_agent_name(self):
        """Test mission critical events FAIL LOUDLY without agent_name."""
        agent_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for event_type in agent_events:
            invalid_agent_names = [None, "", "   ", 123, [], {}]
            
            for invalid_agent_name in invalid_agent_names:
                event = {
                    "type": event_type,
                    "run_id": "test_run_123",
                    "timestamp": datetime.now(timezone.utc).isoformat(), 
                    "payload": {"status": "test"}
                }
                
                if invalid_agent_name is not None:
                    event["agent_name"] = invalid_agent_name
                    
                result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
                
                self.assertFalse(result.is_valid,
                               f"Mission critical event {event_type} should fail without valid agent_name")
                self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
                self.assertIn("agent_name", result.error_message.lower()) 
                self.assertIn("cannot identify", result.business_impact.lower())
    
    # === USER CONTEXT ISOLATION TESTS ===
    
    def test_user_context_validation_success(self):
        """Test user context validation success path."""
        event = {
            "type": "agent_started",
            "run_id": "test_run_123",
            "agent_name": "TestAgent",
            "user_id": self.test_user_id,  # Matching user ID
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
        
        self.assertTrue(result.is_valid, "Event with matching user_id should be valid")
        self.assertIsNone(result.error_message)
        
    def test_user_context_validation_fails_cross_user_leakage(self):
        """Test LOUD failure for cross-user event leakage - CRITICAL SECURITY."""
        different_user_id = f"different_user_{uuid.uuid4().hex[:8]}"
        
        event = {
            "type": "agent_started",
            "run_id": "test_run_123", 
            "agent_name": "TestAgent",
            "user_id": different_user_id,  # Different user ID - SECURITY BREACH
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
        
        self.assertFalse(result.is_valid, "Cross-user event should FAIL validation")
        self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
        self.assertIn("security breach", result.error_message.lower())
        self.assertIn("cross-user", result.error_message.lower()) 
        self.assertIn("event leakage", result.business_impact.lower())
        
    def test_user_context_validation_fails_invalid_user_id(self):
        """Test LOUD failure for invalid user ID in validation."""
        invalid_user_ids = [None, "", "   ", 123, [], {}]
        
        event = {
            "type": "agent_started",
            "run_id": "test_run_123",
            "agent_name": "TestAgent", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        for invalid_user_id in invalid_user_ids:
            result = self.realtime_validator.validate_event(event, invalid_user_id, self.test_connection_id)
            
            self.assertFalse(result.is_valid, f"Should fail for invalid user_id: {invalid_user_id}")
            self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
            self.assertIn("invalid user_id", result.error_message.lower())
            self.assertIn("complete failure", result.business_impact.lower())
    
    # === BUSINESS VALUE SCORING TESTS ===
    
    def test_business_value_scoring_all_critical_events(self):
        """Test business value scoring with all 5 critical events = 100%."""
        critical_events = create_mock_critical_events(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            agent_name="TestAgent"
        )
        
        # Process all critical events through sequence validator
        event_dicts = [event.to_dict() for event in critical_events]
        result = self.sequence_validator.validate_with_mode(event_dicts, self.test_user_id, self.test_connection_id)
        
        self.assertTrue(result.is_valid, "All critical events should result in valid validation")
        self.assertEqual(result.business_value_score, 100.0, "All 5 critical events should give 100% score")
        self.assertEqual(result.revenue_impact, "NONE", "Complete event set should have no revenue impact")
        self.assertEqual(len(result.missing_critical_events), 0, "No events should be missing")
        
    def test_business_value_scoring_partial_critical_events(self):
        """Test business value scoring with partial critical events."""
        partial_test_cases = [
            {"events": ["agent_started"], "expected_score": 20.0, "revenue_impact": "HIGH"},
            {"events": ["agent_started", "agent_thinking"], "expected_score": 40.0, "revenue_impact": "MEDIUM"},
            {"events": ["agent_started", "agent_thinking", "tool_executing"], "expected_score": 60.0, "revenue_impact": "MEDIUM"},
            {"events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed"], 
             "expected_score": 80.0, "revenue_impact": "LOW"}
        ]
        
        for case in partial_test_cases:
            events = []
            for event_type in case["events"]:
                event = {
                    "type": event_type,
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {"agent": "TestAgent", "status": "test"}
                }
                events.append(event)
            
            validator = UnifiedEventValidator(validation_mode="sequence", strict_mode=False)
            result = validator.validate_with_mode(events, self.test_user_id, self.test_connection_id)
            
            self.assertEqual(result.business_value_score, case["expected_score"],
                           f"Expected {case['expected_score']}% for events {case['events']}")
            self.assertEqual(result.revenue_impact, case["revenue_impact"],
                           f"Expected {case['revenue_impact']} revenue impact for events {case['events']}")
    
    def test_business_value_scoring_missing_agent_completed_critical(self):
        """Test missing agent_completed always results in CRITICAL revenue impact."""
        # Include 4 out of 5 critical events but missing agent_completed
        events = []
        for event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed"]:
            event = {
                "type": event_type,
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"agent": "TestAgent", "status": "test"}
            }
            events.append(event)
            
        validator = UnifiedEventValidator(validation_mode="sequence", strict_mode=False)
        result = validator.validate_with_mode(events, self.test_user_id, self.test_connection_id)
        
        self.assertEqual(result.business_value_score, 80.0, "4/5 events should give 80% score")
        self.assertEqual(result.revenue_impact, "CRITICAL", "Missing agent_completed should be CRITICAL")
        self.assertIn("agent_completed", result.missing_critical_events)
        
    # === PERFORMANCE VALIDATION TESTS ===
    
    def test_validation_performance_under_1ms(self):
        """Test validation performance is under 1ms per event - PERFORMANCE SLA."""
        event = {
            "type": "agent_started",
            "run_id": "test_run_123", 
            "agent_name": "TestAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        # Warm up
        for _ in range(5):
            self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
            
        # Performance test
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            result = self.realtime_validator.validate_event(event, self.test_user_id, self.test_connection_id)
            self.assertTrue(result.is_valid)
            
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        self.record_metric("validation_performance_ms", avg_time_ms)
        self.assertLess(avg_time_ms, 1.0, f"Validation should be under 1ms, got {avg_time_ms:.3f}ms")
        
    def test_validation_performance_batch_processing(self):
        """Test batch validation performance for sequence mode."""
        events = create_mock_critical_events(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        event_dicts = [event.to_dict() for event in events]
        
        # Warm up
        for _ in range(5):
            self.sequence_validator.validate_with_mode(event_dicts, self.test_user_id, self.test_connection_id)
            
        # Performance test
        iterations = 50
        start_time = time.time()
        
        for _ in range(iterations):
            result = self.sequence_validator.validate_with_mode(event_dicts, self.test_user_id, self.test_connection_id)
            self.assertTrue(result.is_valid)
            
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        self.record_metric("batch_validation_performance_ms", avg_time_ms)
        self.assertLess(avg_time_ms, 10.0, f"Batch validation should be under 10ms, got {avg_time_ms:.3f}ms")
        
    # === CONNECTION VALIDATION TESTS ===
    
    def test_connection_validation_success(self):
        """Test connection readiness validation success."""
        mock_websocket_manager = Mock()
        mock_websocket_manager.is_connection_active.return_value = True
        
        result = self.realtime_validator.validate_connection_ready(
            self.test_user_id, 
            self.test_connection_id,
            mock_websocket_manager
        )
        
        self.assertTrue(result.is_valid, "Active connection should be valid")
        self.assertIsNone(result.error_message)
        
    def test_connection_validation_fails_inactive_connection(self):
        """Test connection validation fails for inactive connections."""
        mock_websocket_manager = Mock()
        mock_websocket_manager.is_connection_active.return_value = False
        
        result = self.realtime_validator.validate_connection_ready(
            self.test_user_id,
            self.test_connection_id, 
            mock_websocket_manager
        )
        
        self.assertFalse(result.is_valid, "Inactive connection should fail validation")
        self.assertEqual(result.criticality, EventCriticality.BUSINESS_VALUE)
        self.assertIn("not active", result.error_message.lower())
        self.assertIn("real-time updates", result.business_impact.lower())
        
    def test_connection_validation_fails_no_websocket_manager(self):
        """Test connection validation FAILS LOUDLY without WebSocket manager."""
        result = self.realtime_validator.validate_connection_ready(
            self.test_user_id,
            self.test_connection_id,
            None  # No WebSocket manager
        )
        
        self.assertFalse(result.is_valid, "Missing WebSocket manager should fail validation")
        self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL) 
        self.assertIn("websocket manager not available", result.error_message.lower())
        self.assertIn("all events will fail", result.business_impact.lower())
        
    # === VALIDATION MODES TESTS ===
    
    def test_realtime_mode_validation(self):
        """Test realtime validation mode processes single events."""
        event = {
            "type": "agent_started",
            "run_id": "test_run_123",
            "agent_name": "TestAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        result = self.realtime_validator.validate_with_mode(event, self.test_user_id, self.test_connection_id)
        
        self.assertTrue(result.is_valid, "Realtime mode should validate single events")
        self.assertIn("agent_started", result.received_events)
        
    def test_realtime_mode_fails_for_list_input(self):
        """Test realtime mode FAILS LOUDLY for list input."""
        events = [{"type": "agent_started"}, {"type": "agent_thinking"}]
        
        result = self.realtime_validator.validate_with_mode(events, self.test_user_id, self.test_connection_id)
        
        self.assertFalse(result.is_valid, "Realtime mode should reject list input")
        self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
        self.assertIn("single event dict", result.error_message.lower())
        
    def test_sequence_mode_validation(self):
        """Test sequence validation mode processes event lists."""
        events = create_mock_critical_events(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        event_dicts = [event.to_dict() for event in events]
        
        result = self.sequence_validator.validate_with_mode(event_dicts, self.test_user_id, self.test_connection_id)
        
        self.assertTrue(result.is_valid, "Sequence mode should validate event lists")
        self.assertEqual(len(result.received_events), 5, "Should record all 5 events")
        self.assertEqual(result.business_value_score, 100.0, "Complete sequence should give 100% score")
        
    def test_sequence_mode_fails_for_single_event(self):
        """Test sequence mode FAILS LOUDLY for single event input."""  
        event = {"type": "agent_started", "run_id": "test_run"}
        
        result = self.sequence_validator.validate_with_mode(event, self.test_user_id, self.test_connection_id)
        
        self.assertFalse(result.is_valid, "Sequence mode should reject single event input")
        self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
        self.assertIn("list of events", result.error_message.lower())
        
    # === VALIDATION STATISTICS TESTS ===
    
    def test_validation_statistics_tracking(self):
        """Test validation statistics are properly tracked."""
        # Start with fresh stats
        self.realtime_validator.reset_stats()
        
        valid_event = {
            "type": "agent_started",
            "run_id": "test_run_123",
            "agent_name": "TestAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        invalid_event = {
            "type": "agent_started"
            # Missing required fields
        }
        
        # Process valid event
        result1 = self.realtime_validator.validate_event(valid_event, self.test_user_id, self.test_connection_id)
        self.assertTrue(result1.is_valid)
        
        # Process invalid event  
        result2 = self.realtime_validator.validate_event(invalid_event, self.test_user_id, self.test_connection_id)
        self.assertFalse(result2.is_valid)
        
        # Check statistics
        stats = self.realtime_validator.get_validation_stats()
        
        self.assertEqual(stats["total_validations"], 2, "Should track total validations")
        self.assertEqual(stats["failed_validations"], 1, "Should track failed validations")
        self.assertEqual(stats["mission_critical_failures"], 1, "Should track mission critical failures")
        self.assertEqual(stats["success_rate"], 50.0, "Should calculate correct success rate")
        
        # Verify statistics keys
        required_keys = [
            "total_validations", "failed_validations", "mission_critical_failures",
            "success_rate", "uptime_seconds", "last_reset", "business_value_score",
            "critical_events_received", "total_events_received"
        ]
        
        for key in required_keys:
            self.assertIn(key, stats, f"Statistics should include {key}")
            
    # === ERROR HANDLING AND RECOVERY TESTS ===
    
    def test_validation_exception_handling(self):
        """Test validation gracefully handles unexpected exceptions."""
        # Create a validator that will throw an exception
        validator = UnifiedEventValidator()
        
        # Patch a method to throw an exception
        with patch.object(validator, '_validate_basic_structure', side_effect=Exception("Unexpected error")):
            result = validator.validate_event(
                {"type": "test_event"}, 
                self.test_user_id, 
                self.test_connection_id
            )
            
            self.assertFalse(result.is_valid, "Should fail gracefully on exceptions")
            self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
            self.assertIn("validation system failure", result.error_message.lower())
            self.assertIn("all events at risk", result.business_impact.lower())
            
    # === UTILITY FUNCTION TESTS ===
    
    def test_get_critical_event_types(self):
        """Test get_critical_event_types returns correct set."""
        critical_types = get_critical_event_types()
        
        expected_types = {
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        }
        
        self.assertEqual(critical_types, expected_types, "Should return all 5 critical event types")
        self.assertEqual(len(critical_types), 5, "Should return exactly 5 critical event types")
        
    def test_create_mock_critical_events(self):
        """Test create_mock_critical_events generates valid event set."""
        events = create_mock_critical_events(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            agent_name="TestAgent"
        )
        
        self.assertEqual(len(events), 5, "Should create 5 critical events")
        
        event_types = {event.event_type for event in events}
        expected_types = get_critical_event_types()
        
        self.assertEqual(event_types, expected_types, "Should create all critical event types")
        
        # Verify all events have required fields
        for event in events:
            self.assertEqual(event.user_id, self.test_user_id, "Should set correct user_id")
            self.assertEqual(event.thread_id, self.test_thread_id, "Should set correct thread_id")
            self.assertIsNotNone(event.timestamp, "Should have timestamp")
            self.assertIsNotNone(event.message_id, "Should have message_id")
            self.assertIsInstance(event.data, dict, "Should have data dict")
            
    def test_assert_critical_events_received_success(self):
        """Test assert_critical_events_received passes for complete event set."""
        events = create_mock_critical_events(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Should not raise exception
        assert_critical_events_received(events, self.user_context)
        
    def test_assert_critical_events_received_fails_missing_events(self):
        """Test assert_critical_events_received FAILS LOUDLY for incomplete events."""
        # Create incomplete event set (missing agent_completed)
        incomplete_events = create_mock_critical_events()[:-1]  # Remove last event
        
        with self.expect_exception(AssertionError, "CRITICAL AGENT EVENTS VALIDATION FAILED"):
            assert_critical_events_received(incomplete_events, self.user_context)
            
    # === TEARDOWN AND CLEANUP ===
    
    def teardown_method(self, method=None):
        """Cleanup after each test method.""" 
        # Record final metrics
        if hasattr(self, 'realtime_validator'):
            stats = self.realtime_validator.get_validation_stats()
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    self.record_metric(f"final_{key}", value)
                    
        super().teardown_method(method)


# === TEST COLLECTION AND EXECUTION ===

def test_suite():
    """Return test suite for this module."""
    import unittest
    return unittest.TestLoader().loadTestsFromTestCase(TestUnifiedEventValidatorUnit)


if __name__ == "__main__":
    # Allow direct execution for debugging
    import unittest
    unittest.main()