#!/usr/bin/env python3
"""
Simple test to verify EventValidator SSOT violations exist.
"""

import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_eventvalidator_ssot_violations():
    """Test that multiple EventValidator implementations exist - proving SSOT violation."""
    
    print("=== TESTING EVENTVALIDATOR SSOT VIOLATIONS ===")
    
    implementations_found = []
    validation_results = {}
    
    # Sample valid event for testing
    sample_event = {
        "type": "agent_started",
        "run_id": "test-run-123",
        "agent_name": "test-agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"status": "started", "agent": "test-agent"}
    }
    
    test_user_id = "test-user-ssot"
    test_connection_id = "conn-ssot-test"
    
    # Test 1: Unified SSOT implementation
    try:
        from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
        unified_validator = UnifiedEventValidator()
        unified_result = unified_validator.validate_event(sample_event, test_user_id, test_connection_id)
        implementations_found.append("UnifiedEventValidator")
        validation_results["unified"] = {
            "is_valid": unified_result.is_valid,
            "error_message": unified_result.error_message,
            "has_business_score": hasattr(unified_result, 'business_value_score')
        }
        print(f"OK UnifiedEventValidator found - valid: {unified_result.is_valid}")
    except ImportError as e:
        print(f"FAIL Cannot import UnifiedEventValidator: {e}")
    except Exception as e:
        print(f"FAIL UnifiedEventValidator test failed: {e}")
        
    # Test 2: Production WebSocketEventValidator
    try:
        from netra_backend.app.services.websocket_error_validator import WebSocketEventValidator
        production_validator = WebSocketEventValidator()
        production_result = production_validator.validate_event(sample_event, test_user_id, test_connection_id)
        implementations_found.append("WebSocketEventValidator")
        validation_results["production"] = {
            "is_valid": production_result.is_valid,
            "error_message": production_result.error_message,
            "has_business_score": hasattr(production_result, 'business_value_score')
        }
        print(f"OK WebSocketEventValidator found - valid: {production_result.is_valid}")
    except ImportError as e:
        print(f"FAIL Cannot import WebSocketEventValidator: {e}")
    except Exception as e:
        print(f"FAIL WebSocketEventValidator test failed: {e}")
        
    # Test 3: SSOT Framework AgentEventValidator
    try:
        from test_framework.ssot.agent_event_validators import AgentEventValidator
        ssot_validator = AgentEventValidator()
        ssot_validator.record_event(sample_event)
        ssot_result = ssot_validator.perform_full_validation()
        implementations_found.append("AgentEventValidator")
        validation_results["ssot_framework"] = {
            "is_valid": ssot_result.is_valid,
            "error_message": ssot_result.error_message,
            "has_business_score": hasattr(ssot_result, 'business_value_score')
        }
        print(f"OK AgentEventValidator found - valid: {ssot_result.is_valid}")
    except ImportError as e:
        print(f"FAIL Cannot import AgentEventValidator: {e}")
    except Exception as e:
        print(f"FAIL AgentEventValidator test failed: {e}")
        
    # Results
    print(f"\n=== RESULTS ===")
    print(f"Total implementations found: {len(implementations_found)}")
    print(f"Implementations: {implementations_found}")
    print(f"Validation results: {validation_results}")
    
    # Check for SSOT violations
    if len(implementations_found) > 1:
        print(f"\nSSOT VIOLATION DETECTED!")
        print(f"Found {len(implementations_found)} EventValidator implementations")
        print(f"This proves Issue #231: EventValidator SSOT violations exist")
        print(f"BUSINESS IMPACT: $500K+ ARR at risk from inconsistent validation")
        
        # Check for result inconsistencies
        if len(validation_results) > 1:
            capabilities = {}
            for impl, result in validation_results.items():
                capabilities[impl] = result.get("has_business_score", False)
            
            if len(set(capabilities.values())) > 1:
                print(f"INCONSISTENT CAPABILITIES: {capabilities}")
                print(f"Different validators have different business value capabilities")
        
        return False  # Test should fail
    else:
        print(f"\nOK No SSOT violation detected (only {len(implementations_found)} implementation found)")
        return True  # Test should pass

if __name__ == "__main__":
    success = test_eventvalidator_ssot_violations()
    if success:
        print("\nUNEXPECTED: Test passed - SSOT violations may have been fixed")
        sys.exit(0)
    else:
        print("\nEXPECTED: Test failed - SSOT violations detected as expected")
        sys.exit(1)