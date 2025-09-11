"""
INTEGRATION TEST: Unified EventValidator SSOT Functionality Validation

PURPOSE: This test validates that the unified SSOT EventValidator works correctly.
It should PASS to prove the unified implementation preserves all functionality.

Issue #231: EventValidator SSOT violations blocking Golden Path
- Tests the consolidated UnifiedEventValidator implementation
- Validates all 5 critical WebSocket events are properly validated
- Ensures backward compatibility with existing APIs

Expected Behavior:
- This test SHOULD PASS when run against unified implementation
- Validates that SSOT consolidation preserves all functionality
- Proves unified validator can replace multiple implementations

Business Value Impact: Protects $500K+ ARR through consistent event validation
"""

import pytest
import sys
import os
import time
import logging
from typing import Dict, Any, List, Set
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestUnifiedEventValidatorFunctionality(SSotBaseTestCase):
    """
    Test unified EventValidator SSOT implementation functionality.
    
    This test validates the consolidated implementation works correctly.
    """
    
    def setUp(self):
        super().setUp()
        
        # Import unified validator
        from netra_backend.app.websocket_core.event_validator import (
            UnifiedEventValidator, 
            ValidationResult,
            WebSocketEventMessage,
            CriticalAgentEventType,
            EventCriticality
        )
        
        self.UnifiedEventValidator = UnifiedEventValidator
        self.ValidationResult = ValidationResult
        self.WebSocketEventMessage = WebSocketEventMessage
        self.CriticalAgentEventType = CriticalAgentEventType
        self.EventCriticality = EventCriticality
        
        # Test data
        self.test_user_id = "test-user-unified"
        self.test_connection_id = "conn-unified-test"
        self.test_thread_id = "thread-unified-test"
        self.test_run_id = "run-unified-test"
        
        # Create valid test events
        self.valid_agent_started = {
            "type": "agent_started",
            "run_id": self.test_run_id,
            "agent_name": "test-agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started", "agent": "test-agent"}
        }
        
        self.valid_tool_executing = {
            "type": "tool_executing",
            "run_id": self.test_run_id,
            "agent_name": "test-agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"tool": "test-tool", "status": "executing"}
        }
        
        self.invalid_event = {
            "type": "agent_started",
            # Missing required fields
        }
        
    def test_unified_validator_initialization(self):
        """Test that UnifiedEventValidator initializes correctly."""
        logger.info("🧪 Testing UnifiedEventValidator initialization")
        
        # Test default initialization
        validator = self.UnifiedEventValidator()
        self.assertIsInstance(validator, self.UnifiedEventValidator)
        self.assertTrue(validator.strict_mode)
        self.assertEqual(validator.timeout_seconds, 30.0)
        
        # Test custom initialization
        validator_custom = self.UnifiedEventValidator(
            strict_mode=False,
            timeout_seconds=60.0
        )
        self.assertFalse(validator_custom.strict_mode)
        self.assertEqual(validator_custom.timeout_seconds, 60.0)
        
        logger.success("✅ UnifiedEventValidator initialization test passed")
        
    def test_critical_events_validation(self):
        """Test validation of all 5 critical WebSocket events."""
        logger.info("🧪 Testing critical events validation")
        
        validator = self.UnifiedEventValidator()
        
        # Test all 5 critical events
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        for event_type in critical_events:
            valid_event = {
                "type": event_type,
                "run_id": self.test_run_id,
                "agent_name": "test-agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"status": "test", "agent": "test-agent"}
            }
            
            result = validator.validate_event(valid_event, self.test_user_id, self.test_connection_id)
            
            self.assertTrue(result.is_valid, f"Critical event {event_type} should be valid")
            self.assertEqual(result.criticality, self.EventCriticality.MISSION_CRITICAL)
            
        logger.success("✅ All 5 critical events validation test passed")
        
    def test_business_value_scoring(self):
        """Test business value scoring functionality."""
        logger.info("🧪 Testing business value scoring")
        
        validator = self.UnifiedEventValidator()
        
        # Create complete set of critical events
        complete_events = [
            {"type": "agent_started", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}},
            {"type": "agent_thinking", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}},
            {"type": "tool_executing", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}},
            {"type": "tool_completed", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}},
            {"type": "agent_completed", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}}
        ]
        
        # Record all events
        for event in complete_events:
            validator.record_event(event)
            
        # Perform validation
        result = validator.perform_full_validation()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.business_value_score, 100.0)
        self.assertEqual(result.revenue_impact, "NONE")
        self.assertEqual(len(result.missing_critical_events), 0)
        
        logger.success("✅ Business value scoring test passed")
        
    def test_event_sequence_validation(self):
        """Test event sequence validation logic."""
        logger.info("🧪 Testing event sequence validation")
        
        validator = self.UnifiedEventValidator()
        
        # Test correct sequence
        correct_sequence = [
            {"type": "agent_started", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}},
            {"type": "agent_thinking", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}},
            {"type": "tool_executing", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}},
            {"type": "tool_completed", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}},
            {"type": "agent_completed", "run_id": self.test_run_id, "agent_name": "test-agent", "timestamp": datetime.now(timezone.utc).isoformat(), "payload": {}}
        ]
        
        for event in correct_sequence:
            validator.record_event(event)
            
        sequence_valid, sequence_errors = validator.validate_event_sequence()
        self.assertTrue(sequence_valid, f"Correct sequence should be valid. Errors: {sequence_errors}")
        
        logger.success("✅ Event sequence validation test passed")
        
    def test_connection_readiness_validation(self):
        """Test connection readiness validation."""
        logger.info("🧪 Testing connection readiness validation")
        
        validator = self.UnifiedEventValidator()
        
        # Test valid parameters
        result = validator.validate_connection_ready(
            self.test_user_id, 
            self.test_connection_id
        )
        # Note: This should fail because websocket_manager is None, but that's expected behavior
        self.assertFalse(result.is_valid)
        self.assertIn("WebSocket manager not available", result.error_message)
        
        # Test invalid user_id
        result = validator.validate_connection_ready("", self.test_connection_id)
        self.assertFalse(result.is_valid)
        self.assertIn("user_id", result.error_message)
        
        # Test invalid connection_id
        result = validator.validate_connection_ready(self.test_user_id, "")
        self.assertFalse(result.is_valid)
        self.assertIn("connection_id", result.error_message)
        
        logger.success("✅ Connection readiness validation test passed")
        
    def test_backward_compatibility_functions(self):
        """Test backward compatibility functions work correctly."""
        logger.info("🧪 Testing backward compatibility functions")
        
        # Test global validator functions
        from netra_backend.app.websocket_core.event_validator import (
            get_websocket_validator,
            reset_websocket_validator,
            validate_agent_events,
            assert_critical_events_received,
            get_critical_event_types,
            create_mock_critical_events
        )
        
        # Test global validator
        global_validator = get_websocket_validator()
        self.assertIsInstance(global_validator, self.UnifiedEventValidator)
        
        # Test reset
        reset_websocket_validator()
        new_validator = get_websocket_validator()
        self.assertIsInstance(new_validator, self.UnifiedEventValidator)
        
        # Test critical event types
        critical_types = get_critical_event_types()
        expected_types = {
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        }
        self.assertEqual(critical_types, expected_types)
        
        # Test mock event creation
        mock_events = create_mock_critical_events()
        self.assertEqual(len(mock_events), 5)
        for event in mock_events:
            self.assertIsInstance(event, self.WebSocketEventMessage)
            
        # Test validation function
        result = validate_agent_events(mock_events, strict_mode=True)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.business_value_score, 100.0)
        
        logger.success("✅ Backward compatibility functions test passed")
        
    def test_loud_failure_patterns(self):
        """Test that validation failures are logged loudly."""
        logger.info("🧪 Testing loud failure patterns")
        
        validator = self.UnifiedEventValidator()
        
        # Test with invalid event that should trigger loud logging
        invalid_event = {
            "type": "agent_started",
            # Missing all required fields
        }
        
        # Capture log output (this would normally go to central_logger)
        result = validator.validate_event(invalid_event, self.test_user_id, self.test_connection_id)
        
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.error_message)
        self.assertEqual(result.criticality, self.EventCriticality.MISSION_CRITICAL)
        
        # Verify validation stats updated
        stats = validator.get_validation_stats()
        self.assertGreater(stats["total_validations"], 0)
        self.assertGreater(stats["failed_validations"], 0)
        
        logger.success("✅ Loud failure patterns test passed")
        
    def test_websocket_event_message_functionality(self):
        """Test WebSocketEventMessage dataclass functionality."""
        logger.info("🧪 Testing WebSocketEventMessage functionality")
        
        # Test creation from dict
        event_dict = {
            "type": "agent_started",
            "user_id": self.test_user_id,
            "thread_id": self.test_thread_id,
            "run_id": self.test_run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"test": "data"}
        }
        
        event_msg = self.WebSocketEventMessage.from_dict(event_dict)
        self.assertEqual(event_msg.event_type, "agent_started")
        self.assertEqual(event_msg.user_id, self.test_user_id)
        self.assertIsNotNone(event_msg.timestamp)
        self.assertIsNotNone(event_msg.message_id)
        
        # Test conversion back to dict
        converted_dict = event_msg.to_dict()
        self.assertEqual(converted_dict["type"], "agent_started")
        self.assertEqual(converted_dict["user_id"], self.test_user_id)
        
        logger.success("✅ WebSocketEventMessage functionality test passed")
        
    def test_validation_result_business_metrics(self):
        """Test ValidationResult business metrics calculation."""
        logger.info("🧪 Testing ValidationResult business metrics")
        
        # Test with missing critical events
        missing_events = {"agent_completed"}
        received_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed"]
        
        result = self.ValidationResult(
            is_valid=False,
            missing_critical_events=missing_events,
            received_events=received_events
        )
        
        # Check business value calculation
        self.assertEqual(result.business_value_score, 80.0)  # 4/5 events = 80%
        self.assertEqual(result.revenue_impact, "CRITICAL")  # agent_completed missing = critical
        
        # Test with no missing events
        result_complete = self.ValidationResult(
            is_valid=True,
            missing_critical_events=set(),
            received_events=["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        )
        
        self.assertEqual(result_complete.business_value_score, 100.0)
        self.assertEqual(result_complete.revenue_impact, "NONE")
        
        logger.success("✅ ValidationResult business metrics test passed")
        
    def test_golden_path_protection(self):
        """Test that unified validator protects Golden Path functionality."""
        logger.info("🧪 Testing Golden Path protection")
        
        validator = self.UnifiedEventValidator()
        
        # Verify all 5 critical events are supported
        required_events = validator.get_required_critical_events()
        expected_events = {
            "agent_started", "agent_thinking", "tool_executing",
            "tool_completed", "agent_completed"
        }
        self.assertEqual(required_events, expected_events)
        
        # Test mission critical event detection
        self.assertTrue("agent_started" in validator.MISSION_CRITICAL_EVENTS)
        self.assertTrue("agent_completed" in validator.MISSION_CRITICAL_EVENTS)
        
        # Test event schema validation
        required_schema = validator.EVENT_SCHEMAS.get("agent_started")
        expected_fields = {"run_id", "agent_name", "timestamp", "payload"}
        self.assertEqual(required_schema, expected_fields)
        
        logger.success("✅ Golden Path protection test passed")


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    suite = pytest.TestLoader().loadTestsFromTestCase(TestUnifiedEventValidatorFunctionality)
    runner = pytest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("✅ SUCCESS: Unified EventValidator functionality validated")
        print("This proves the SSOT consolidation preserves all functionality")
    else:
        print("❌ FAILURE: Unified EventValidator has issues")
        print("SSOT consolidation may have broken functionality")