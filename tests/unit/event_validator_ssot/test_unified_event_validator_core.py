"""
Unit Tests: EventValidator SSOT Core Functionality Validation

PURPOSE: Expose validation inconsistencies across multiple EventValidator implementations
EXPECTATION: Tests should FAIL initially to demonstrate the SSOT consolidation issues

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Revenue Protection - Ensure consistent event validation 
- Value Impact: Protects $500K+ ARR by exposing validation logic conflicts
- Strategic Impact: Validates that SSOT consolidation is truly needed

These tests are designed to FAIL initially, demonstrating:
1. Multiple EventValidator classes with conflicting validation logic
2. Import inconsistencies between implementations  
3. Behavioral differences in validation methods
4. Missing consolidation in event validation patterns

Test Plan Phase 1: Unit Tests (No Docker)
- Test core validation functionality differences
- Test import path inconsistencies  
- Test method signature differences
- Test validation result differences
"""

import pytest
import sys
import unittest
from typing import Dict, Any, List, Optional, Set, Tuple
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase

# CRITICAL: These imports should expose the SSOT inconsistency issue
try:
    # Unified implementation (consolidated SSOT)
    from netra_backend.app.websocket_core.event_validator import (
        UnifiedEventValidator,
        ValidationResult as UnifiedValidationResult,
        EventCriticality as UnifiedEventCriticality,
        CriticalAgentEventType as UnifiedCriticalAgentEventType
    )
    unified_available = True
except ImportError as e:
    unified_available = False
    unified_import_error = str(e)

try:
    # Production implementation (legacy)
    from netra_backend.app.services.websocket_error_validator import (
        WebSocketEventValidator as ProductionEventValidator,
        ValidationResult as ProductionValidationResult,
        EventCriticality as ProductionEventCriticality
    )
    production_available = True
except ImportError as e:
    production_available = False
    production_import_error = str(e)

try:
    # SSOT Framework implementation (legacy)
    from test_framework.ssot.agent_event_validators import (
        AgentEventValidator as SsotFrameworkEventValidator,
        AgentEventValidationResult as SsotFrameworkValidationResult,
        CriticalAgentEventType as SsotFrameworkCriticalAgentEventType
    )
    ssot_framework_available = True
except ImportError as e:
    ssot_framework_available = False
    ssot_framework_import_error = str(e)


class TestUnifiedEventValidatorCore(SSotBaseTestCase, unittest.TestCase):
    """
    Unit tests for EventValidator SSOT core functionality.
    
    DESIGNED TO FAIL: These tests expose the EventValidator consolidation issues
    by demonstrating conflicts between multiple implementations.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        # Track import availability for analysis
        self.import_status = {
            "unified": unified_available,
            "production": production_available, 
            "ssot_framework": ssot_framework_available
        }
        
        # Sample event data for testing
        self.sample_critical_event = {
            "type": "agent_started",
            "run_id": "test-run-123",
            "agent_name": "test-agent",
            "timestamp": "2025-01-09T10:00:00Z",
            "payload": {"status": "started", "agent": "test-agent"}
        }
        
        self.sample_user_id = "test-user-456"
        self.sample_connection_id = "ws-conn-789"
    
    def test_import_availability_exposes_multiple_implementations(self):
        """
        TEST DESIGNED TO FAIL: Should expose that multiple EventValidator implementations exist.
        
        Expected failure: Multiple implementations should be available simultaneously,
        demonstrating the SSOT consolidation issue.
        """
        # Count available implementations
        available_implementations = sum([
            self.import_status["unified"],
            self.import_status["production"], 
            self.import_status["ssot_framework"]
        ])
        
        # This should FAIL initially - we expect multiple implementations
        self.assertEqual(
            available_implementations, 1,
            f"SSOT VIOLATION: Found {available_implementations} EventValidator implementations. "
            f"Expected exactly 1 unified implementation. "
            f"Import status: {self.import_status}. "
            f"This demonstrates the SSOT consolidation issue - multiple validators exist!"
        )
    
    @pytest.mark.skipif(not unified_available, reason="UnifiedEventValidator not available")
    def test_unified_event_validator_initialization(self):
        """Test unified validator initialization works correctly."""
        validator = UnifiedEventValidator(strict_mode=True, timeout_seconds=30.0)
        
        self.assertIsNotNone(validator)
        self.assertTrue(validator.strict_mode)
        self.assertEqual(validator.timeout_seconds, 30.0)
        self.assertEqual(len(validator.received_events), 0)
        self.assertEqual(len(validator.critical_events_received), 0)
    
    @pytest.mark.skipif(not production_available, reason="Production EventValidator not available")
    def test_production_event_validator_initialization(self):
        """Test production validator initialization works correctly."""
        validator = ProductionEventValidator()
        
        self.assertIsNotNone(validator)
        self.assertIn("total_validations", validator.validation_stats)
        self.assertEqual(validator.validation_stats["total_validations"], 0)
    
    @pytest.mark.skipif(not ssot_framework_available, reason="SSOT Framework EventValidator not available")
    def test_ssot_framework_event_validator_initialization(self):
        """Test SSOT framework validator initialization works correctly."""
        validator = SsotFrameworkEventValidator(strict_mode=True, timeout_seconds=30.0)
        
        self.assertIsNotNone(validator)
        self.assertTrue(validator.strict_mode)
        self.assertEqual(validator.timeout_seconds, 30.0)
        self.assertEqual(len(validator.received_events), 0)
    
    def test_validation_method_signature_consistency_across_implementations(self):
        """
        TEST DESIGNED TO FAIL: Should expose method signature inconsistencies.
        
        Expected failure: Different implementations may have different method signatures
        for validate_event, demonstrating the need for SSOT consolidation.
        """
        validation_methods = {}
        
        # Collect validate_event method signatures from available implementations
        if unified_available:
            validator = UnifiedEventValidator()
            validation_methods["unified"] = {
                "has_validate_event": hasattr(validator, "validate_event"),
                "validate_event_params": self._get_method_params(validator.validate_event) if hasattr(validator, "validate_event") else None,
                "has_record_event": hasattr(validator, "record_event"),
                "has_perform_full_validation": hasattr(validator, "perform_full_validation")
            }
        
        if production_available:
            validator = ProductionEventValidator()
            validation_methods["production"] = {
                "has_validate_event": hasattr(validator, "validate_event"),
                "validate_event_params": self._get_method_params(validator.validate_event) if hasattr(validator, "validate_event") else None,
                "has_record_event": hasattr(validator, "record_event"),
                "has_perform_full_validation": hasattr(validator, "perform_full_validation")
            }
        
        if ssot_framework_available:
            validator = SsotFrameworkEventValidator()
            validation_methods["ssot_framework"] = {
                "has_validate_event": hasattr(validator, "validate_event"),
                "validate_event_params": self._get_method_params(validator.validate_event) if hasattr(validator, "validate_event") else None,
                "has_record_event": hasattr(validator, "record_event"),
                "has_perform_full_validation": hasattr(validator, "perform_full_validation")
            }
        
        # Check for method consistency - this should FAIL initially
        method_signatures = [methods.get("validate_event_params") for methods in validation_methods.values() if methods.get("validate_event_params")]
        
        if len(method_signatures) > 1:
            # Compare signatures - they should be identical for true SSOT
            first_signature = method_signatures[0]
            for i, signature in enumerate(method_signatures[1:], 1):
                self.assertEqual(
                    first_signature, signature,
                    f"SSOT VIOLATION: validate_event method signatures differ between implementations. "
                    f"First: {first_signature}, Implementation {i}: {signature}. "
                    f"This demonstrates inconsistent APIs across EventValidator implementations!"
                )
        
        # Check for method availability consistency
        method_availability = {}
        for impl_name, methods in validation_methods.items():
            for method_name, has_method in methods.items():
                if method_name not in method_availability:
                    method_availability[method_name] = []
                method_availability[method_name].append((impl_name, has_method))
        
        # All implementations should have the same methods
        for method_name, availability_list in method_availability.items():
            has_method_values = [has_method for _, has_method in availability_list]
            
            if len(set(has_method_values)) > 1:
                availability_details = {impl: has_method for impl, has_method in availability_list}
                self.fail(
                    f"SSOT VIOLATION: Method '{method_name}' availability differs across implementations: "
                    f"{availability_details}. This demonstrates inconsistent interfaces!"
                )
    
    def test_validation_result_type_consistency_across_implementations(self):
        """
        TEST DESIGNED TO FAIL: Should expose ValidationResult type inconsistencies.
        
        Expected failure: Different implementations may return different ValidationResult types,
        demonstrating the need for SSOT consolidation.
        """
        validation_result_types = {}
        
        # Test validation and collect result types
        if unified_available:
            validator = UnifiedEventValidator()
            try:
                result = validator.validate_event(self.sample_critical_event, self.sample_user_id)
                validation_result_types["unified"] = {
                    "type": type(result).__name__,
                    "module": type(result).__module__,
                    "has_is_valid": hasattr(result, "is_valid"),
                    "has_error_message": hasattr(result, "error_message"),
                    "has_business_value_score": hasattr(result, "business_value_score"),
                    "has_revenue_impact": hasattr(result, "revenue_impact")
                }
            except Exception as e:
                validation_result_types["unified"] = {"error": str(e)}
        
        if production_available:
            validator = ProductionEventValidator()
            try:
                result = validator.validate_event(self.sample_critical_event, self.sample_user_id)
                validation_result_types["production"] = {
                    "type": type(result).__name__,
                    "module": type(result).__module__,
                    "has_is_valid": hasattr(result, "is_valid"),
                    "has_error_message": hasattr(result, "error_message"),
                    "has_business_value_score": hasattr(result, "business_value_score"),
                    "has_revenue_impact": hasattr(result, "revenue_impact")
                }
            except Exception as e:
                validation_result_types["production"] = {"error": str(e)}
        
        # Check ValidationResult type consistency - this should FAIL initially
        result_type_names = [info.get("type") for info in validation_result_types.values() if "type" in info]
        result_modules = [info.get("module") for info in validation_result_types.values() if "module" in info]
        
        if len(set(result_type_names)) > 1:
            self.fail(
                f"SSOT VIOLATION: ValidationResult types differ across implementations: "
                f"Types: {set(result_type_names)}, Modules: {set(result_modules)}. "
                f"Full details: {validation_result_types}. "
                f"This demonstrates inconsistent return types!"
            )
        
        # Check field availability consistency
        field_availability = {}
        for impl_name, info in validation_result_types.items():
            if "error" not in info:
                for field_name, has_field in info.items():
                    if field_name.startswith("has_"):
                        clean_field_name = field_name[4:]  # Remove "has_" prefix
                        if clean_field_name not in field_availability:
                            field_availability[clean_field_name] = []
                        field_availability[clean_field_name].append((impl_name, has_field))
        
        # All implementations should have the same fields
        for field_name, availability_list in field_availability.items():
            has_field_values = [has_field for _, has_field in availability_list]
            
            if len(set(has_field_values)) > 1:
                availability_details = {impl: has_field for impl, has_field in availability_list}
                self.fail(
                    f"SSOT VIOLATION: ValidationResult field '{field_name}' availability differs: "
                    f"{availability_details}. This demonstrates inconsistent ValidationResult schemas!"
                )
    
    def test_critical_event_type_definitions_consistency(self):
        """
        TEST DESIGNED TO FAIL: Should expose CriticalAgentEventType inconsistencies.
        
        Expected failure: Different implementations may define critical events differently,
        demonstrating the need for SSOT consolidation.
        """
        critical_event_definitions = {}
        
        # Collect critical event definitions from available implementations
        if unified_available:
            critical_events = set()
            try:
                if hasattr(UnifiedCriticalAgentEventType, "AGENT_STARTED"):
                    critical_events.add(UnifiedCriticalAgentEventType.AGENT_STARTED.value)
                if hasattr(UnifiedCriticalAgentEventType, "AGENT_THINKING"):
                    critical_events.add(UnifiedCriticalAgentEventType.AGENT_THINKING.value)
                if hasattr(UnifiedCriticalAgentEventType, "TOOL_EXECUTING"):
                    critical_events.add(UnifiedCriticalAgentEventType.TOOL_EXECUTING.value)
                if hasattr(UnifiedCriticalAgentEventType, "TOOL_COMPLETED"):
                    critical_events.add(UnifiedCriticalAgentEventType.TOOL_COMPLETED.value)
                if hasattr(UnifiedCriticalAgentEventType, "AGENT_COMPLETED"):
                    critical_events.add(UnifiedCriticalAgentEventType.AGENT_COMPLETED.value)
                critical_event_definitions["unified"] = critical_events
            except Exception as e:
                critical_event_definitions["unified"] = {"error": str(e)}
        
        if production_available:
            validator = ProductionEventValidator()
            try:
                critical_events = getattr(validator, "MISSION_CRITICAL_EVENTS", set())
                critical_event_definitions["production"] = critical_events
            except Exception as e:
                critical_event_definitions["production"] = {"error": str(e)}
        
        if ssot_framework_available:
            critical_events = set()
            try:
                if hasattr(SsotFrameworkCriticalAgentEventType, "AGENT_STARTED"):
                    critical_events.add(SsotFrameworkCriticalAgentEventType.AGENT_STARTED.value)
                if hasattr(SsotFrameworkCriticalAgentEventType, "AGENT_THINKING"):
                    critical_events.add(SsotFrameworkCriticalAgentEventType.AGENT_THINKING.value)
                if hasattr(SsotFrameworkCriticalAgentEventType, "TOOL_EXECUTING"):
                    critical_events.add(SsotFrameworkCriticalAgentEventType.TOOL_EXECUTING.value)
                if hasattr(SsotFrameworkCriticalAgentEventType, "TOOL_COMPLETED"):
                    critical_events.add(SsotFrameworkCriticalAgentEventType.TOOL_COMPLETED.value)
                if hasattr(SsotFrameworkCriticalAgentEventType, "AGENT_COMPLETED"):
                    critical_events.add(SsotFrameworkCriticalAgentEventType.AGENT_COMPLETED.value)
                critical_event_definitions["ssot_framework"] = critical_events
            except Exception as e:
                critical_event_definitions["ssot_framework"] = {"error": str(e)}
        
        # Check for critical event definition consistency - this should FAIL initially
        valid_definitions = [events for events in critical_event_definitions.values() if not isinstance(events, dict) or "error" not in events]
        
        if len(valid_definitions) > 1:
            first_definition = valid_definitions[0]
            for i, definition in enumerate(valid_definitions[1:], 1):
                self.assertEqual(
                    first_definition, definition,
                    f"SSOT VIOLATION: Critical event definitions differ between implementations. "
                    f"First: {first_definition}, Implementation {i}: {definition}. "
                    f"All definitions: {critical_event_definitions}. "
                    f"This demonstrates inconsistent critical event definitions!"
                )
    
    def test_validation_behavior_consistency_for_same_input(self):
        """
        TEST DESIGNED TO FAIL: Should expose behavioral differences in validation logic.
        
        Expected failure: Same input may produce different validation results across implementations,
        demonstrating the need for SSOT consolidation.
        """
        test_cases = [
            # Valid critical event
            {
                "name": "valid_agent_started",
                "event": self.sample_critical_event,
                "user_id": self.sample_user_id,
                "expected_valid": True
            },
            # Invalid event - missing required field
            {
                "name": "missing_run_id",
                "event": {
                    "type": "agent_started",
                    "agent_name": "test-agent",
                    "timestamp": "2025-01-09T10:00:00Z",
                    "payload": {"status": "started"}
                },
                "user_id": self.sample_user_id,
                "expected_valid": False
            },
            # Invalid event - malformed
            {
                "name": "malformed_event",
                "event": {"invalid": "structure"},
                "user_id": self.sample_user_id,
                "expected_valid": False
            }
        ]
        
        validation_behaviors = {}
        
        for test_case in test_cases:
            case_name = test_case["name"]
            event = test_case["event"]
            user_id = test_case["user_id"]
            
            case_results = {}
            
            # Test unified implementation
            if unified_available:
                try:
                    validator = UnifiedEventValidator()
                    result = validator.validate_event(event, user_id)
                    case_results["unified"] = {
                        "is_valid": result.is_valid,
                        "error_message": result.error_message,
                        "criticality": getattr(result, "criticality", None)
                    }
                except Exception as e:
                    case_results["unified"] = {"error": str(e)}
            
            # Test production implementation
            if production_available:
                try:
                    validator = ProductionEventValidator()
                    result = validator.validate_event(event, user_id)
                    case_results["production"] = {
                        "is_valid": result.is_valid,
                        "error_message": result.error_message,
                        "criticality": getattr(result, "criticality", None)
                    }
                except Exception as e:
                    case_results["production"] = {"error": str(e)}
            
            validation_behaviors[case_name] = case_results
            
            # Check for behavioral consistency - this should FAIL initially
            valid_results = [result for result in case_results.values() if "error" not in result]
            
            if len(valid_results) > 1:
                is_valid_values = [result["is_valid"] for result in valid_results]
                
                if len(set(is_valid_values)) > 1:
                    self.fail(
                        f"SSOT VIOLATION: Validation behavior differs for test case '{case_name}'. "
                        f"is_valid results: {is_valid_values}. "
                        f"Full results: {case_results}. "
                        f"Same input should produce same validation outcome across implementations!"
                    )
    
    def _get_method_params(self, method) -> List[str]:
        """Helper to extract method parameter names."""
        import inspect
        try:
            signature = inspect.signature(method)
            return list(signature.parameters.keys())
        except Exception:
            return ["unable_to_inspect"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])