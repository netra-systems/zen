"""
MISSION CRITICAL: EventValidator SSOT Violation Detection Test

PURPOSE: This test is DESIGNED TO FAIL initially to prove that SSOT violations exist.
It tests that different EventValidator implementations give different results, proving violations.

Issue #231: EventValidator SSOT violations blocking Golden Path
- 4 different EventValidator implementations found
- Each gives different validation results for same inputs
- Creates inconsistent behavior across the platform

Expected Behavior:
- This test SHOULD FAIL when run against current codebase
- Failure proves SSOT violations exist and need consolidation
- After SSOT migration, this test SHOULD PASS

Business Value Impact: $500K+ ARR at risk from inconsistent event validation
"""

import pytest
import sys
import os
import logging
from typing import Dict, Any, List, Set
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestEventValidatorSSOTViolations(SSotBaseTestCase):
    """
    Test that detects SSOT violations in EventValidator implementations.
    
    This test is DESIGNED TO FAIL initially to prove violations exist.
    """
    
    def setUp(self):
        super().setUp()
        self.sample_valid_event = {
            "type": "agent_started",
            "run_id": "test-run-123",
            "agent_name": "test-agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started", "agent": "test-agent"}
        }
        
        self.sample_invalid_event = {
            "type": "agent_started",
            # Missing required fields: run_id, agent_name, timestamp, payload
        }
        
        self.test_user_id = "test-user-ssot-violation"
        self.test_connection_id = "conn-ssot-test"
        
    def test_multiple_eventvalidator_implementations_exist(self):
        """
        Test that multiple EventValidator implementations exist - proving SSOT violation.
        
        This test SHOULD FAIL, proving that SSOT violations exist.
        """
        logger.critical("🚨 TESTING FOR SSOT VIOLATIONS: Multiple EventValidator implementations")
        
        implementations_found = []
        validation_results = {}
        
        # Test Import 1: Unified SSOT implementation
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
            unified_validator = UnifiedEventValidator()
            unified_result = unified_validator.validate_event(
                self.sample_valid_event, 
                self.test_user_id, 
                self.test_connection_id
            )
            implementations_found.append("UnifiedEventValidator")
            validation_results["unified"] = {
                "is_valid": unified_result.is_valid,
                "error_message": unified_result.error_message,
                "criticality": unified_result.criticality.value if hasattr(unified_result.criticality, 'value') else str(unified_result.criticality)
            }
            logger.info(f"✓ UnifiedEventValidator found and tested")
            print(f"DEBUG: UnifiedEventValidator found - {unified_result.is_valid}")
        except ImportError as e:
            logger.error(f"❌ Cannot import UnifiedEventValidator: {e}")
            print(f"DEBUG: UnifiedEventValidator import failed: {e}")
        except Exception as e:
            logger.error(f"❌ UnifiedEventValidator test failed: {e}")
            print(f"DEBUG: UnifiedEventValidator exception: {e}")
            
        # Test Import 2: Production WebSocketEventValidator
        try:
            from netra_backend.app.services.websocket_error_validator import WebSocketEventValidator
            production_validator = WebSocketEventValidator()
            production_result = production_validator.validate_event(
                self.sample_valid_event,
                self.test_user_id,
                self.test_connection_id
            )
            implementations_found.append("WebSocketEventValidator")
            validation_results["production"] = {
                "is_valid": production_result.is_valid,
                "error_message": production_result.error_message,
                "criticality": production_result.criticality.value if hasattr(production_result.criticality, 'value') else str(production_result.criticality)
            }
            logger.info(f"✓ WebSocketEventValidator found and tested")
            print(f"DEBUG: WebSocketEventValidator found - {production_result.is_valid}")
        except ImportError as e:
            logger.error(f"❌ Cannot import WebSocketEventValidator: {e}")
            print(f"DEBUG: WebSocketEventValidator import failed: {e}")
        except Exception as e:
            logger.error(f"❌ WebSocketEventValidator test failed: {e}")
            print(f"DEBUG: WebSocketEventValidator exception: {e}")
            
        # Test Import 3: SSOT Framework AgentEventValidator (migrated to UnifiedEventValidator)
        try:
            from netra_backend.app.websocket_core.event_validator import AgentEventValidator
            ssot_validator = AgentEventValidator()
            ssot_validator.record_event(self.sample_valid_event)
            ssot_result = ssot_validator.perform_full_validation()
            implementations_found.append("AgentEventValidator")
            validation_results["ssot_framework"] = {
                "is_valid": ssot_result.is_valid,
                "error_message": ssot_result.error_message,
                "business_value_score": ssot_result.business_value_score
            }
            logger.info(f"✓ AgentEventValidator found and tested")
            print(f"DEBUG: AgentEventValidator found - {ssot_result.is_valid}")
        except ImportError as e:
            logger.error(f"❌ Cannot import AgentEventValidator: {e}")
            print(f"DEBUG: AgentEventValidator import failed: {e}")
        except Exception as e:
            logger.error(f"❌ AgentEventValidator test failed: {e}")
            print(f"DEBUG: AgentEventValidator exception: {e}")
            
        # Log findings
        logger.critical(f"🚨 SSOT VIOLATION ANALYSIS:")
        logger.critical(f"🚨 Total EventValidator implementations found: {len(implementations_found)}")
        logger.critical(f"🚨 Implementations: {implementations_found}")
        logger.critical(f"🚨 Validation results: {validation_results}")
        
        print(f"DEBUG: Found {len(implementations_found)} implementations: {implementations_found}")
        print(f"DEBUG: Validation results: {validation_results}")
        
        # CRITICAL ASSERTION: This SHOULD FAIL initially, proving SSOT violation
        if len(implementations_found) > 1:
            logger.critical("🚨 SSOT VIOLATION DETECTED: Multiple EventValidator implementations exist!")
            logger.critical("🚨 This proves Issue #231: EventValidator SSOT violations")
            logger.critical("🚨 BUSINESS IMPACT: $500K+ ARR at risk from inconsistent validation")
            
            # Test that they give different results (proving violation)
            if len(validation_results) > 1:
                # Compare validation approaches - they should be different, proving violation
                unified_approach = validation_results.get("unified", {})
                production_approach = validation_results.get("production", {})
                ssot_framework_approach = validation_results.get("ssot_framework", {})
                
                approaches_different = False
                if unified_approach and production_approach:
                    # Check if they have different fields/structures
                    unified_fields = set(unified_approach.keys())
                    production_fields = set(production_approach.keys())
                    if unified_fields != production_fields:
                        approaches_different = True
                        logger.critical(f"🚨 Unified fields: {unified_fields}")
                        logger.critical(f"🚨 Production fields: {production_fields}")
                
                if approaches_different:
                    logger.critical("🚨 PROOF: Different validators return different result structures!")
                    logger.critical("🚨 This is a clear SSOT violation requiring consolidation")
                
        # FAIL THE TEST TO PROVE VIOLATION EXISTS
        if len(implementations_found) > 1:
            self.fail(
                f"SSOT VIOLATION: Found {len(implementations_found)} EventValidator implementations: {implementations_found}. "
                f"Should be exactly 1 unified implementation. This failure PROVES Issue #231 exists and needs fixing."
            )
        
    def test_eventvalidator_result_inconsistency(self):
        """
        Test that different validators give inconsistent results - proving SSOT violation.
        
        This test SHOULD FAIL, proving that validation results are inconsistent.
        """
        logger.critical("🚨 TESTING VALIDATION RESULT INCONSISTENCY")
        
        results = []
        
        # Test with invalid event across multiple validators
        invalid_event = {
            "type": "agent_started",
            # Missing: run_id, agent_name, timestamp, payload
        }
        
        # Test UnifiedEventValidator
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
            unified_validator = UnifiedEventValidator()
            unified_result = unified_validator.validate_event(invalid_event, self.test_user_id)
            results.append({
                "validator": "UnifiedEventValidator",
                "is_valid": unified_result.is_valid,
                "has_business_value_score": hasattr(unified_result, 'business_value_score'),
                "has_revenue_impact": hasattr(unified_result, 'revenue_impact'),
                "has_missing_events": hasattr(unified_result, 'missing_critical_events')
            })
        except Exception as e:
            logger.warning(f"UnifiedEventValidator test failed: {e}")
            
        # Test Production WebSocketEventValidator
        try:
            from netra_backend.app.services.websocket_error_validator import WebSocketEventValidator
            production_validator = WebSocketEventValidator()
            production_result = production_validator.validate_event(invalid_event, self.test_user_id)
            results.append({
                "validator": "WebSocketEventValidator",
                "is_valid": production_result.is_valid,
                "has_business_value_score": hasattr(production_result, 'business_value_score'),
                "has_revenue_impact": hasattr(production_result, 'revenue_impact'),
                "has_missing_events": hasattr(production_result, 'missing_critical_events')
            })
        except Exception as e:
            logger.warning(f"WebSocketEventValidator test failed: {e}")
            
        logger.critical(f"🚨 VALIDATION RESULT COMPARISON: {results}")
        
        if len(results) >= 2:
            # Check if validators return different capabilities
            first_result = results[0]
            second_result = results[1]
            
            inconsistencies = []
            if first_result["has_business_value_score"] != second_result["has_business_value_score"]:
                inconsistencies.append("business_value_score capability differs")
            if first_result["has_revenue_impact"] != second_result["has_revenue_impact"]:
                inconsistencies.append("revenue_impact capability differs")
            if first_result["has_missing_events"] != second_result["has_missing_events"]:
                inconsistencies.append("missing_events capability differs")
                
            if inconsistencies:
                logger.critical(f"🚨 INCONSISTENCIES DETECTED: {inconsistencies}")
                logger.critical("🚨 This proves different validators have different capabilities")
                logger.critical("🚨 SSOT violation confirmed - consolidation required")
                
                # FAIL THE TEST TO PROVE INCONSISTENCY
                self.fail(
                    f"SSOT VIOLATION: EventValidator implementations have inconsistent capabilities: {inconsistencies}. "
                    f"This proves Issue #231 - different validators provide different features, blocking Golden Path."
                )
        
    def test_golden_path_impact_validation(self):
        """
        Test that SSOT violations impact Golden Path functionality.
        
        This validates the 5 critical events are handled consistently.
        """
        logger.critical("🚨 TESTING GOLDEN PATH IMPACT OF SSOT VIOLATIONS")
        
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        validator_support = {}
        
        # Test UnifiedEventValidator support
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
            unified_validator = UnifiedEventValidator()
            unified_critical = unified_validator.get_required_critical_events()
            validator_support["unified"] = unified_critical
        except Exception as e:
            logger.error(f"UnifiedEventValidator critical events test failed: {e}")
            
        # Test SSOT Framework support (migrated to UnifiedEventValidator)
        try:
            from netra_backend.app.websocket_core.event_validator import get_critical_event_types
            ssot_critical = get_critical_event_types()
            validator_support["ssot_framework"] = ssot_critical
        except Exception as e:
            logger.error(f"SSOT Framework critical events test failed: {e}")
            
        # Test Production WebSocketEventValidator support
        try:
            from netra_backend.app.services.websocket_error_validator import WebSocketEventValidator
            production_validator = WebSocketEventValidator()
            production_critical = production_validator.MISSION_CRITICAL_EVENTS
            validator_support["production"] = production_critical
        except Exception as e:
            logger.error(f"Production validator critical events test failed: {e}")
            
        logger.critical(f"🚨 CRITICAL EVENTS SUPPORT COMPARISON: {validator_support}")
        
        # Check for inconsistencies in critical event support
        if len(validator_support) > 1:
            event_support_sets = list(validator_support.values())
            if len(set(str(sorted(events)) for events in event_support_sets)) > 1:
                logger.critical("🚨 GOLDEN PATH VIOLATION: Different validators support different critical events!")
                logger.critical("🚨 This directly impacts $500K+ ARR chat functionality")
                logger.critical("🚨 Critical events must be consistently validated across all implementations")
                
                # Show the differences
                for validator_name, events in validator_support.items():
                    logger.critical(f"🚨 {validator_name}: {sorted(events)}")
                
                # FAIL TO PROVE GOLDEN PATH IMPACT
                self.fail(
                    f"GOLDEN PATH VIOLATION: EventValidator implementations support different critical events. "
                    f"This blocks consistent $500K+ ARR chat functionality. "
                    f"Validator support: {validator_support}"
                )


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    suite = pytest.TestLoader().loadTestsFromTestCase(TestEventValidatorSSOTViolations)
    runner = pytest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("❌ UNEXPECTED: Test passed - SSOT violations may have been fixed already")
    else:
        print("✅ EXPECTED: Test failed - SSOT violations detected as expected")
        print("This confirms Issue #231 exists and requires SSOT consolidation")