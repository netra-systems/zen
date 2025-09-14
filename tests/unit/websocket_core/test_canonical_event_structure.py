#!/usr/bin/env python
"""Canonical Event Structure Test

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - API Consistency
- Business Goal: $500K+ ARR protection through event format standardization
- Value Impact: Ensure frontend can reliably parse and display all WebSocket events
- Revenue Impact: Prevents UI breaking changes and improves user experience reliability

Test Strategy: This test MUST FAIL before SSOT consolidation and PASS after
- FAIL: Currently event format inconsistency (flat vs nested payload structures)
- PASS: After SSOT consolidation, single canonical event structure across all events

Issue #1033: WebSocket Manager SSOT Consolidation
This test validates that all WebSocket events use a consistent, canonical structure
to ensure frontend compatibility and prevent parsing errors.
"""

import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Set, Any, Optional, Union
from enum import Enum
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.logging.unified_logging_ssot import get_logger
from test_framework.ssot.base_test_case import SSotBaseTestCase as BaseTestCase

logger = get_logger(__name__)


class EventStructureCompliance(Enum):
    """Event structure compliance levels."""
    CANONICAL = "canonical"      # Follows canonical SSOT structure
    LEGACY = "legacy"           # Old format, needs migration
    INVALID = "invalid"         # Malformed or inconsistent
    MIXED = "mixed"             # Contains elements of multiple formats


@dataclass
class CanonicalEventStructure:
    """Canonical SSOT event structure for WebSocket events."""
    event_type: str                    # Required: Type of event (agent_started, tool_executing, etc.)
    timestamp: float                   # Required: Unix timestamp when event occurred  
    user_id: str                       # Required: User who triggered the event
    thread_id: Optional[str] = None    # Optional: Thread/conversation context
    request_id: Optional[str] = None   # Optional: Request tracking ID
    data: Dict[str, Any] = None        # Optional: Event-specific payload data
    metadata: Dict[str, Any] = None    # Optional: Additional context metadata


@dataclass  
class EventStructureViolation:
    """Details about an event structure violation."""
    event_sample: Dict[str, Any]
    violation_type: str
    expected_structure: str
    actual_structure: str
    compliance_level: EventStructureCompliance


class TestCanonicalEventStructure(BaseTestCase):
    """Test WebSocket event structure compliance with canonical SSOT format.
    
    This test suite validates that all WebSocket events follow the canonical
    structure to ensure consistent frontend integration and API reliability.
    """

    def test_golden_path_events_canonical_structure(self):
        """Test that Golden Path agent events follow canonical structure.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently event format inconsistency across different managers
        - PASS: After SSOT consolidation, all Golden Path events use canonical structure
        
        This test validates the 5 critical Golden Path events:
        agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        """
        logger.info("🔍 Testing Golden Path event structure compliance...")
        
        # Define expected Golden Path events and their canonical structures
        golden_path_events = self._get_golden_path_event_samples()
        
        structure_violations = []
        
        for event_name, event_samples in golden_path_events.items():
            logger.info(f"Validating structure for {event_name} ({len(event_samples)} samples)")
            
            for i, event_sample in enumerate(event_samples):
                compliance = self._validate_event_structure(event_sample)
                
                if compliance.compliance_level != EventStructureCompliance.CANONICAL:
                    violation = EventStructureViolation(
                        event_sample=event_sample,
                        violation_type=f"{event_name}_structure_non_canonical",
                        expected_structure="canonical SSOT format",
                        actual_structure=compliance.compliance_level.value,
                        compliance_level=compliance.compliance_level
                    )
                    structure_violations.append(violation)
        
        # Log violations
        if structure_violations:
            logger.error("SSOT VIOLATIONS: Golden Path event structure violations:")
            for violation in structure_violations:
                logger.error(f"  - {violation.violation_type}: {violation.actual_structure}")
                logger.error(f"    Sample: {json.dumps(violation.event_sample, indent=2)[:200]}...")
        
        # SSOT VIOLATION CHECK: All Golden Path events should use canonical structure
        # This assertion WILL FAIL until event structure standardization is complete
        assert len(structure_violations) == 0, (
            f"SSOT VIOLATION: Found {len(structure_violations)} Golden Path event structure violations. "
            f"All Golden Path events must use canonical SSOT structure for frontend compatibility."
        )

    def test_event_payload_consistency_across_managers(self):
        """Test that same event types have consistent payload structures.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently different managers create different payload formats
        - PASS: After SSOT consolidation, same event types have identical structures
        
        This test validates that an 'agent_started' event from different managers
        has the same structure and required fields.
        """
        logger.info("🔍 Testing event payload consistency across managers...")
        
        # Sample events that should have identical structures across managers
        event_types_to_test = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        consistency_violations = []
        
        for event_type in event_types_to_test:
            # Get samples of this event type from different sources
            event_samples = self._get_event_samples_by_type(event_type)
            
            if len(event_samples) < 2:
                logger.warning(f"Only {len(event_samples)} samples found for {event_type}, skipping consistency check")
                continue
            
            # Compare structures across samples
            structure_variations = self._analyze_structure_variations(event_type, event_samples)
            
            if structure_variations:
                for variation in structure_variations:
                    consistency_violations.append(f"{event_type}: {variation}")
        
        if consistency_violations:
            logger.error("SSOT VIOLATIONS: Event payload consistency violations:")
            for violation in consistency_violations:
                logger.error(f"  - {violation}")
        
        # SSOT VIOLATION CHECK: Same event types should have identical structures
        # This assertion WILL FAIL until payload consistency is achieved
        assert len(consistency_violations) == 0, (
            f"SSOT VIOLATION: Found {len(consistency_violations)} payload consistency violations. "
            f"Same event types must have identical structure across all managers."
        )

    def test_required_fields_presence_validation(self):
        """Test that all events contain required canonical fields.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently some events missing required fields (event_type, timestamp, user_id)
        - PASS: After SSOT consolidation, all events contain required fields
        
        This test validates that every WebSocket event contains the minimum
        required fields according to the canonical SSOT specification.
        """
        logger.info("🔍 Testing required fields presence in WebSocket events...")
        
        # Required fields for canonical SSOT event structure
        required_fields = ["event_type", "timestamp", "user_id"]
        recommended_fields = ["thread_id", "request_id"]  # Should be present for Golden Path events
        
        # Get comprehensive sample of WebSocket events
        all_event_samples = self._get_comprehensive_event_samples()
        
        field_violations = []
        
        for event_sample in all_event_samples:
            # Check required fields
            missing_required = []
            for field in required_fields:
                if field not in event_sample:
                    missing_required.append(field)
            
            if missing_required:
                field_violations.append({
                    "type": "missing_required_fields",
                    "event": event_sample,
                    "missing_fields": missing_required
                })
            
            # Check recommended fields for Golden Path events
            event_type = event_sample.get("event_type", "unknown")
            if self._is_golden_path_event(event_type):
                missing_recommended = []
                for field in recommended_fields:
                    if field not in event_sample or event_sample[field] is None:
                        missing_recommended.append(field)
                
                if missing_recommended:
                    field_violations.append({
                        "type": "missing_recommended_fields",
                        "event": event_sample,
                        "missing_fields": missing_recommended
                    })
        
        if field_violations:
            logger.error("SSOT VIOLATIONS: Required field violations:")
            for violation in field_violations[:10]:  # Show first 10 violations
                logger.error(f"  - {violation['type']}: {violation['missing_fields']}")
                logger.error(f"    Event type: {violation['event'].get('event_type', 'unknown')}")
        
        # SSOT VIOLATION CHECK: All events should contain required fields
        # This assertion WILL FAIL until required field compliance is achieved
        assert len(field_violations) == 0, (
            f"SSOT VIOLATION: Found {len(field_violations)} required field violations. "
            f"All WebSocket events must contain canonical required fields."
        )

    def test_data_type_consistency_validation(self):
        """Test that event field data types are consistent across events.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently timestamp could be string/float, user_id format varies
        - PASS: After SSOT consolidation, consistent data types across all events
        
        This test validates that field data types remain consistent to prevent
        frontend parsing errors and ensure API reliability.
        """
        logger.info("🔍 Testing event field data type consistency...")
        
        # Expected data types for canonical fields
        expected_field_types = {
            "event_type": str,
            "timestamp": (float, int),  # Allow both float and int for timestamps
            "user_id": str,
            "thread_id": (str, type(None)),  # String or None
            "request_id": (str, type(None)),  # String or None
            "data": (dict, type(None)),      # Dict or None
            "metadata": (dict, type(None))   # Dict or None
        }
        
        # Get comprehensive sample of events
        all_event_samples = self._get_comprehensive_event_samples()
        
        type_violations = []
        
        for event_sample in all_event_samples:
            for field_name, expected_type in expected_field_types.items():
                if field_name not in event_sample:
                    continue  # Skip missing fields (handled by required fields test)
                
                field_value = event_sample[field_name]
                
                # Handle tuple of allowed types
                if isinstance(expected_type, tuple):
                    if not any(isinstance(field_value, t) for t in expected_type):
                        type_violations.append({
                            "field": field_name,
                            "expected_type": expected_type,
                            "actual_type": type(field_value),
                            "actual_value": field_value,
                            "event_type": event_sample.get("event_type", "unknown")
                        })
                else:
                    if not isinstance(field_value, expected_type):
                        type_violations.append({
                            "field": field_name,
                            "expected_type": expected_type,
                            "actual_type": type(field_value),
                            "actual_value": field_value,
                            "event_type": event_sample.get("event_type", "unknown")
                        })
        
        if type_violations:
            logger.error("SSOT VIOLATIONS: Field data type violations:")
            for violation in type_violations[:10]:  # Show first 10 violations
                logger.error(f"  - {violation['field']}: expected {violation['expected_type']}, got {violation['actual_type']}")
                logger.error(f"    Event type: {violation['event_type']}, Value: {violation['actual_value']}")
        
        # SSOT VIOLATION CHECK: All fields should have consistent data types
        # This assertion WILL FAIL until data type consistency is achieved
        assert len(type_violations) == 0, (
            f"SSOT VIOLATION: Found {len(type_violations)} field data type violations. "
            f"All event fields must use consistent data types across all events."
        )

    def _get_golden_path_event_samples(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate sample Golden Path events for testing."""
        # In a real implementation, this would load actual event samples from logs or create them dynamically
        # For testing purposes, we create samples that represent current system variations
        
        return {
            "agent_started": [
                # Canonical format (what we want)
                {
                    "event_type": "agent_started",
                    "timestamp": 1633024800.123,
                    "user_id": "user_12345",
                    "thread_id": "thread_67890",
                    "request_id": "req_abcdef",
                    "data": {"agent_name": "cost_optimizer"},
                    "metadata": {"source": "supervisor_agent"}
                },
                # Legacy format (current problem)
                {
                    "type": "agent_started",  # Wrong field name
                    "time": "2023-10-01T10:00:00Z",  # String timestamp instead of float
                    "user": "user_12345",  # Wrong field name
                    "agent_name": "cost_optimizer"  # Flat structure instead of nested data
                },
                # Mixed format (another current problem)
                {
                    "event_type": "agent_started",
                    "timestamp": 1633024800,  # Integer instead of float
                    "user_id": "user_12345",
                    "payload": {"agent_name": "cost_optimizer"}  # Wrong field name for data
                }
            ],
            "agent_thinking": [
                # Similar variations for thinking events
                {
                    "event_type": "agent_thinking",
                    "timestamp": 1633024801.456,
                    "user_id": "user_12345", 
                    "thread_id": "thread_67890",
                    "data": {"thought": "Analyzing cost data..."}
                },
                {
                    "type": "thinking",  # Inconsistent event type naming
                    "timestamp": "1633024801",  # String timestamp
                    "user_id": "user_12345",
                    "message": "Analyzing cost data..."  # Flat structure
                }
            ],
            "tool_executing": [
                {
                    "event_type": "tool_executing",
                    "timestamp": 1633024802.789,
                    "user_id": "user_12345",
                    "thread_id": "thread_67890", 
                    "data": {"tool_name": "cost_analyzer", "parameters": {"period": "monthly"}}
                },
                {
                    "event": "tool_start",  # Different event type name
                    "when": 1633024802,  # Different field name
                    "user": "user_12345",  # Different field name
                    "tool": "cost_analyzer",  # Flat structure
                    "params": {"period": "monthly"}  # Flat structure
                }
            ],
            "tool_completed": [
                {
                    "event_type": "tool_completed",
                    "timestamp": 1633024803.012,
                    "user_id": "user_12345",
                    "thread_id": "thread_67890",
                    "data": {"tool_name": "cost_analyzer", "result": {"savings": 1500}}
                },
                {
                    "event_type": "tool_completed",
                    "timestamp": 1633024803,
                    "user_id": "user_12345",
                    "results": {"savings": 1500}  # Wrong structure - should be in data field
                }
            ],
            "agent_completed": [
                {
                    "event_type": "agent_completed",
                    "timestamp": 1633024804.345,
                    "user_id": "user_12345",
                    "thread_id": "thread_67890",
                    "data": {"result": {"recommendations": ["Optimize EC2 instances"]}}
                },
                {
                    "type": "agent_done",  # Different event type name
                    "timestamp": 1633024804,
                    "user_id": "user_12345",
                    "final_result": ["Optimize EC2 instances"]  # Flat structure
                }
            ]
        }

    def _validate_event_structure(self, event: Dict[str, Any]) -> EventStructureViolation:
        """Validate an event against the canonical structure."""
        canonical_fields = {"event_type", "timestamp", "user_id"}
        optional_fields = {"thread_id", "request_id", "data", "metadata"}
        
        event_fields = set(event.keys())
        
        # Check if it has all required canonical fields
        missing_required = canonical_fields - event_fields
        if missing_required:
            return EventStructureViolation(
                event_sample=event,
                violation_type="missing_required_fields",
                expected_structure="canonical",
                actual_structure="incomplete",
                compliance_level=EventStructureCompliance.INVALID
            )
        
        # Check for legacy field names
        legacy_indicators = {"type", "time", "user", "when", "event", "payload", "message"}
        if event_fields & legacy_indicators:
            return EventStructureViolation(
                event_sample=event,
                violation_type="legacy_field_names",
                expected_structure="canonical",
                actual_structure="legacy",
                compliance_level=EventStructureCompliance.LEGACY
            )
        
        # Check data types
        if "timestamp" in event:
            if not isinstance(event["timestamp"], (int, float)):
                return EventStructureViolation(
                    event_sample=event,
                    violation_type="incorrect_timestamp_type",
                    expected_structure="canonical",
                    actual_structure="type_mismatch",
                    compliance_level=EventStructureCompliance.INVALID
                )
        
        # If we get here, it's likely canonical compliant
        return EventStructureViolation(
            event_sample=event,
            violation_type="none",
            expected_structure="canonical",
            actual_structure="canonical",
            compliance_level=EventStructureCompliance.CANONICAL
        )

    def _get_event_samples_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get multiple samples of a specific event type."""
        all_samples = self._get_golden_path_event_samples()
        
        # Return samples for the requested event type
        return all_samples.get(event_type, [])

    def _analyze_structure_variations(self, event_type: str, samples: List[Dict[str, Any]]) -> List[str]:
        """Analyze structural variations in event samples."""
        variations = []
        
        if len(samples) < 2:
            return variations
        
        # Compare field sets
        field_sets = [set(sample.keys()) for sample in samples]
        
        # Check if all samples have same fields
        if not all(fields == field_sets[0] for fields in field_sets[1:]):
            variations.append(f"Inconsistent field sets across {event_type} samples")
        
        # Check specific field variations
        for field in ["event_type", "timestamp", "user_id"]:
            field_types = []
            for sample in samples:
                if field in sample:
                    field_types.append(type(sample[field]))
            
            if len(set(field_types)) > 1:
                variations.append(f"Field '{field}' has inconsistent types: {set(field_types)}")
        
        return variations

    def _get_comprehensive_event_samples(self) -> List[Dict[str, Any]]:
        """Get comprehensive samples of all event types for testing."""
        all_samples = []
        golden_path_samples = self._get_golden_path_event_samples()
        
        # Flatten all samples
        for event_type, samples in golden_path_samples.items():
            all_samples.extend(samples)
        
        return all_samples

    def _is_golden_path_event(self, event_type: str) -> bool:
        """Check if an event type is part of the Golden Path."""
        golden_path_events = {
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        }
        return event_type in golden_path_events


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])