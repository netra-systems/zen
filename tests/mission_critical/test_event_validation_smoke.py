#!/usr/bin/env python
"""
MISSION CRITICAL SMOKE TEST: Event Validation Infrastructure
============================================================

Business Value: Quick validation that event validation infrastructure works
properly and can detect when business value is compromised.

SMOKE TEST COVERAGE:
- Event validation infrastructure initialization
- Business value compromise detection
- Critical event sequence validation
- Content quality validation
- Timing performance validation  
- Integration with WebSocket events

This test serves as a quick sanity check that the validation infrastructure
is functioning correctly before running comprehensive tests.
"""

import os
import sys
import time
from datetime import datetime, timezone

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

from test_framework.validation import (
    EventSequenceValidator,
    ContentQualityValidator,
    TimingValidator, 
    BusinessValueValidator,
    validate_agent_execution_sequence,
    create_test_event_sequence
)

from test_framework.ssot.real_websocket_test_client import WebSocketEvent


def create_mock_websocket_event(event_type: str, data: dict) -> WebSocketEvent:
    """Create a mock WebSocket event for testing."""
    event_data = {
        **data,
        "user_id": "test_user",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Create event using the correct constructor from WebSocketEvent.from_message
    import json
    message = json.dumps({"type": event_type, **event_data})
    return WebSocketEvent.from_message(message)


class TestEventValidationSmoke:
    """Smoke tests for event validation infrastructure."""
    
    def test_event_sequence_validator_initialization(self):
        """Test EventSequenceValidator initializes correctly."""
        validator = EventSequenceValidator("test_user", "test_session")
        
        assert validator.user_id == "test_user"
        assert validator.session_id == "test_session"
        assert len(validator.CRITICAL_BUSINESS_SEQUENCES) >= 3
        assert validator.received_events == []
    
    def test_content_quality_validator_initialization(self):
        """Test ContentQualityValidator initializes correctly."""
        validator = ContentQualityValidator("test_user", "test_session", strict_mode=True)
        
        assert validator.user_id == "test_user"
        assert validator.session_id == "test_session"
        assert validator.strict_mode is True
        assert validator.validated_events == 0
    
    def test_timing_validator_initialization(self):
        """Test TimingValidator initializes correctly."""
        validator = TimingValidator("test_user", "test_session")
        
        assert validator.user_id == "test_user"
        assert validator.session_id == "test_session"
        assert len(validator.BUSINESS_TIMING_REQUIREMENTS) >= 5
        assert validator.event_timings == []
    
    def test_business_value_validator_initialization(self):
        """Test BusinessValueValidator initializes correctly."""
        validator = BusinessValueValidator("test_user", "test_session", "free")
        
        assert validator.user_id == "test_user"
        assert validator.session_id == "test_session"
        assert validator.user_segment == "free"
        assert validator.events_processed == 0
    
    def test_good_event_sequence_validation(self):
        """Test that good event sequence passes validation."""
        validator = EventSequenceValidator("test_user", "test_session")
        
        # Create good event sequence
        good_events = [
            create_mock_websocket_event("agent_started", {"agent_id": "test", "task": "Good test"}),
            create_mock_websocket_event("agent_thinking", {"content": "Analyzing your request thoroughly"}), 
            create_mock_websocket_event("tool_executing", {"tool_name": "analyzer", "context": "Processing data"}),
            create_mock_websocket_event("tool_completed", {"tool_name": "analyzer", "result": {"insights": ["Found patterns"]}}),
            create_mock_websocket_event("agent_completed", {"result": {"status": "success"}, "summary": "Analysis complete"})
        ]
        
        # Add events to validator
        for event in good_events:
            violations = validator.add_event(event)
            # Should have minimal violations for good sequence
        
        # Should pass business value validation
        validator.assert_business_value_preserved()
        validator.assert_critical_events_received()
        
        # Get summary
        summary = validator.get_validation_summary()
        assert summary["total_events_received"] == 5
    
    def test_bad_event_sequence_detection(self):
        """Test that bad event sequence is detected and fails validation."""
        validator = EventSequenceValidator("test_user", "test_session")
        
        # Create bad event sequence (out of order, missing events)
        bad_events = [
            create_mock_websocket_event("tool_executing", {"tool_name": "unknown"}),  # No agent_started first
            create_mock_websocket_event("agent_thinking", {"content": "thinking..."}),  # Generic content
            # Missing agent_completed
        ]
        
        # Add bad events
        for event in bad_events:
            violations = validator.add_event(event)
            # Should have violations
        
        # Should fail business value validation
        with pytest.raises(AssertionError) as excinfo:
            validator.assert_business_value_preserved()
        
        assert "BUSINESS VALUE COMPROMISED" in str(excinfo.value)
        
        # Should fail critical events check
        with pytest.raises(AssertionError) as excinfo:
            validator.assert_critical_events_received()
        
        assert "CRITICAL EVENTS MISSING" in str(excinfo.value)
    
    def test_content_quality_validation(self):
        """Test content quality validation works."""
        validator = ContentQualityValidator("test_user", "test_session", strict_mode=True)
        
        # Test high-quality content
        good_event = create_mock_websocket_event("agent_completed", {
            "result": {"insights": ["Key trend identified", "User behavior analyzed"], "confidence": 0.9},
            "summary": "Successfully analyzed your data and provided actionable recommendations",
            "next_steps": "Review insights and implement recommended changes"
        })
        
        result = validator.validate_event_content(good_event)
        assert result.business_value_score >= 0.6
        assert result.quality_level.value in ["acceptable", "good", "excellent"]  # Allow acceptable for business value
        
        # Test low-quality content  
        bad_event = create_mock_websocket_event("agent_completed", {
            "result": {},  # Empty result
            "summary": "done"  # Generic
        })
        
        bad_result = validator.validate_event_content(bad_event)
        assert bad_result.business_value_score < 0.5
        assert len(bad_result.violations) > 0
        
        # Should fail business value assertion
        with pytest.raises(AssertionError):
            validator.assert_business_value_preserved()
    
    def test_timing_validation(self):
        """Test timing validation works."""
        validator = TimingValidator("test_user", "test_session")
        
        # Test good timing
        good_event = create_mock_websocket_event("agent_started", {"agent_id": "test", "task": "Fast test"})
        
        # Simulate fast processing
        processing_start = time.time() - 0.1  # 100ms ago
        violations = validator.record_event(good_event, processing_start)
        
        # Should have few/no violations for fast processing
        critical_violations = [v for v in violations if v.criticality.value == "critical"]
        assert len(critical_violations) == 0
        
        # Should pass performance standards
        result = validator.validate_overall_timing()
        assert result.performance_score >= 0.7
        
        # Test slow timing
        slow_validator = TimingValidator("test_user", "test_session_slow")
        slow_event = create_mock_websocket_event("agent_started", {"agent_id": "slow_test"})
        
        # Simulate very slow processing  
        slow_processing_start = time.time() - 35.0  # 35 seconds ago
        slow_violations = slow_validator.record_event(slow_event, slow_processing_start)
        
        # Should have critical violations for slow processing
        slow_critical_violations = [v for v in slow_violations if v.criticality.value == "critical"]
        assert len(slow_critical_violations) > 0
        
        # Should fail performance standards
        with pytest.raises(AssertionError):
            slow_validator.assert_performance_standards_met()
    
    def test_business_value_validation(self):
        """Test business value validation works."""
        validator = BusinessValueValidator("test_user", "test_session", "free", strict_mode=True)
        
        # Test high business value event
        high_value_event = create_mock_websocket_event("agent_completed", {
            "result": {
                "recommendations": ["Increase marketing spend by 20%", "Focus on mobile users"],
                "insights": ["Market trend shows 15% growth opportunity", "User engagement up 23%"],
                "expected_impact": "Estimated 20% revenue increase"
            },
            "summary": "Completed comprehensive analysis and provided actionable business recommendations"
        })
        
        result = validator.validate_event_business_value(high_value_event)
        assert result.business_value_score >= 0.7
        assert result.conversion_potential.probability >= 0.3
        
        # Test low business value event
        low_value_event = create_mock_websocket_event("agent_completed", {
            "result": {},
            "summary": "task completed"  # Generic, no value
        })
        
        low_result = validator.validate_event_business_value(low_value_event)
        assert low_result.business_value_score < 0.5
        assert len(low_result.violations) > 0
        
        # Should pass standards for high value
        validator.assert_business_value_standards_met()
        
        # Should fail standards for low value validator
        low_validator = BusinessValueValidator("test_user", "test_session_low", "free")
        low_validator.validate_event_business_value(low_value_event)
        
        with pytest.raises(AssertionError):
            low_validator.assert_business_value_standards_met()
    
    def test_convenience_functions(self):
        """Test convenience functions work correctly."""
        # Test create_test_event_sequence
        test_events = create_test_event_sequence()
        assert len(test_events) == 5
        
        expected_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        actual_types = [event.event_type for event in test_events]
        assert actual_types == expected_types
        
        # Test validate_agent_execution_sequence
        validator = validate_agent_execution_sequence(test_events)
        assert validator.user_id == "test_user"
        
        # Should pass validation for good test sequence
        summary = validator.get_validation_summary()
        assert summary["total_events_received"] == 5
    
    def test_comprehensive_validation_integration(self):
        """Test that all validators work together correctly."""
        user_id = "integration_test_user"
        session_id = "integration_test_session"
        
        # Initialize all validators
        sequence_validator = EventSequenceValidator(user_id, session_id)
        content_validator = ContentQualityValidator(user_id, session_id, strict_mode=True)
        timing_validator = TimingValidator(user_id, session_id)
        business_validator = BusinessValueValidator(user_id, session_id, "free")
        
        # Create comprehensive event sequence
        events = [
            create_mock_websocket_event("agent_started", {
                "agent_id": "integration_agent",
                "task_description": "Comprehensive integration test with business value analysis"
            }),
            create_mock_websocket_event("agent_thinking", {
                "content": "Analyzing your request using advanced algorithms to identify optimal solutions",
                "progress": {"step": 1, "total": 3}
            }),
            create_mock_websocket_event("tool_executing", {
                "tool_name": "data_processor",
                "execution_context": "Processing comprehensive dataset for insights"
            }),
            create_mock_websocket_event("tool_completed", {
                "tool_name": "data_processor",
                "result": {"insights": ["15% efficiency gain identified", "3 optimization opportunities"], "confidence": 0.87},
                "summary": "Successfully processed data and identified key improvement opportunities"
            }),
            create_mock_websocket_event("agent_completed", {
                "result": {
                    "recommendations": ["Implement efficiency improvements", "Optimize workflow processes"],
                    "expected_benefits": "15% efficiency gain, estimated $50K annual savings"
                },
                "summary": "Completed comprehensive analysis with actionable recommendations for significant business impact"
            })
        ]
        
        # Validate events with all validators
        for event in events:
            processing_start = time.time() - 0.5  # 500ms ago (good timing)
            
            # Validate with each validator
            sequence_violations = sequence_validator.add_event(event)
            content_result = content_validator.validate_event_content(event)
            timing_violations = timing_validator.record_event(event, processing_start)
            business_result = business_validator.validate_event_business_value(event)
            
            # All should show good results for well-crafted events
            assert len([v for v in sequence_violations if v.business_impact.value == "critical"]) == 0
            assert content_result.business_value_score >= 0.5
            assert len([v for v in timing_violations if v.criticality.value == "critical"]) == 0
            assert business_result.business_value_score >= 0.5
        
        # All validators should pass their assertions
        sequence_validator.assert_business_value_preserved()
        sequence_validator.assert_critical_events_received()
        content_validator.assert_business_value_preserved()
        timing_validator.assert_performance_standards_met()
        business_validator.assert_business_value_standards_met()
        
        # Get summaries
        sequence_summary = sequence_validator.get_validation_summary()
        content_summary = content_validator.get_validation_summary()
        timing_summary = timing_validator.get_performance_summary()
        business_summary = business_validator.get_business_value_summary()
        
        # Verify summaries show successful validation
        assert sequence_summary["total_events_received"] == 5
        assert content_summary["average_business_value_score"] >= 0.6
        assert timing_summary["user_engagement_preserved"] is True
        assert business_summary["conversion_probability"] >= 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])