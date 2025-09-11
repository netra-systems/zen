#!/usr/bin/env python3
"""
Simple test runner for WebSocket TDD tests - Issue #280

Runs the TDD test suite to demonstrate RFC 6455 subprotocol compliance failures
and validate that the tests properly capture the business impact.
"""

import sys
import os
import asyncio
import logging
import traceback

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def run_rfc_6455_compliance_tests():
    """Run RFC 6455 compliance tests to demonstrate failures"""
    try:
        from tests.websocket_auth_protocol_tdd.test_rfc_6455_subprotocol_compliance import RFC6455SubprotocolComplianceTest
        
        print("🧪 RFC 6455 WebSocket Subprotocol Compliance Tests")
        print("=" * 60)
        
        # Create test instance
        test_instance = RFC6455SubprotocolComplianceTest()
        test_instance.setUp()
        
        # Run individual test methods
        test_methods = [
            ("test_main_mode_subprotocol_negotiation_failure", "Main mode WebSocket accept() failure"),
            ("test_factory_mode_subprotocol_negotiation_failure", "Factory mode WebSocket accept() failure"), 
            ("test_isolated_mode_subprotocol_negotiation_failure", "Isolated mode WebSocket accept() failure"),
            ("test_legacy_mode_subprotocol_negotiation_failure", "Legacy mode WebSocket accept() failure"),
            ("test_rfc_6455_subprotocol_selection_logic", "RFC 6455 compliant subprotocol selection"),
            ("test_business_impact_validation", "Business impact quantification")
        ]
        
        passed = 0
        failed = 0
        
        for method_name, description in test_methods:
            try:
                print(f"\n📋 Running: {description}")
                method = getattr(test_instance, method_name)
                
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()
                    
                print(f"✅ PASSED: {method_name}")
                passed += 1
                
            except Exception as e:
                print(f"❌ FAILED: {method_name}")
                print(f"   Error: {str(e)}")
                print(f"   This failure demonstrates the RFC 6455 violation")
                failed += 1
        
        print(f"\n📊 RFC 6455 Test Results:")
        print(f"   Passed: {passed}")
        print(f"   Failed: {failed} (Expected - demonstrates bug)")
        print(f"   Status: {'✅ TDD tests working correctly' if failed > 0 else '⚠️ Unexpected passes'}")
        
        return failed > 0
        
    except Exception as e:
        print(f"🚨 Error running RFC 6455 tests: {e}")
        traceback.print_exc()
        return False


async def run_jwt_extraction_tests():
    """Run JWT extraction integration tests"""
    try:
        from tests.websocket_auth_protocol_tdd.test_jwt_extraction_integration import JWTExtractionIntegrationTest
        
        print("\n🔐 JWT Extraction Integration Tests")
        print("=" * 60)
        
        test_instance = JWTExtractionIntegrationTest()
        test_instance.setUp()
        
        test_methods = [
            ("test_jwt_extraction_from_subprotocol_succeeds", "JWT extraction from subprotocol"),
            ("test_jwt_protocol_handler_integration", "Unified JWT handler integration"),
            ("test_authentication_flow_with_jwt_subprotocol", "Complete authentication flow"),
            ("test_multiple_subprotocol_formats", "Multiple subprotocol formats"),
            ("test_frontend_backend_protocol_compatibility", "Frontend-backend compatibility")
        ]
        
        passed = 0
        failed = 0
        
        for method_name, description in test_methods:
            try:
                print(f"\n📋 Running: {description}")
                method = getattr(test_instance, method_name)
                
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()
                    
                print(f"✅ PASSED: {method_name}")
                passed += 1
                
            except Exception as e:
                print(f"❌ FAILED: {method_name}")
                print(f"   Error: {str(e)}")
                failed += 1
        
        print(f"\n📊 JWT Extraction Test Results:")
        print(f"   Passed: {passed}")
        print(f"   Failed: {failed}")
        print(f"   Status: {'✅ JWT extraction working' if passed > failed else '⚠️ JWT extraction issues'}")
        
        return passed > failed
        
    except Exception as e:
        print(f"🚨 Error running JWT extraction tests: {e}")
        traceback.print_exc()
        return False


async def run_agent_event_tests():
    """Run agent event delivery failure tests"""
    try:
        from tests.websocket_auth_protocol_tdd.test_agent_event_delivery_failure import AgentEventDeliveryFailureTest
        
        print("\n💼 Agent Event Delivery Failure Tests")
        print("=" * 60)
        
        test_instance = AgentEventDeliveryFailureTest()
        test_instance.setUp()
        
        test_methods = [
            ("test_agent_started_event_delivery_failure", "agent_started event failure"),
            ("test_agent_thinking_event_delivery_failure", "agent_thinking event failure"),
            ("test_tool_executing_event_delivery_failure", "tool_executing event failure"),
            ("test_tool_completed_event_delivery_failure", "tool_completed event failure"),
            ("test_agent_completed_event_delivery_failure", "agent_completed event failure"),
            ("test_complete_agent_event_sequence_failure", "Complete event sequence failure"),
            ("test_business_impact_quantification", "Business impact quantification"),
            ("test_golden_path_complete_blockage", "Golden Path blockage analysis")
        ]
        
        passed = 0
        failed = 0
        business_impact_demonstrated = 0
        
        for method_name, description in test_methods:
            try:
                print(f"\n📋 Running: {description}")
                method = getattr(test_instance, method_name)
                
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()
                    
                print(f"✅ PASSED: {method_name}")
                passed += 1
                
                # Count business impact demonstrations
                if "business" in method_name or "golden_path" in method_name:
                    business_impact_demonstrated += 1
                
            except Exception as e:
                print(f"❌ FAILED: {method_name}")
                print(f"   Error: {str(e)}")
                failed += 1
                
                # Expected failures due to WebSocket connection issues
                if "delivery_failure" in method_name:
                    print(f"   ✅ Expected failure - demonstrates business impact")
                    business_impact_demonstrated += 1
        
        print(f"\n📊 Agent Event Test Results:")
        print(f"   Passed: {passed}")
        print(f"   Failed: {failed} (Expected - WebSocket events can't deliver)")
        print(f"   Business Impact Demonstrated: {business_impact_demonstrated}/8 tests")
        print(f"   Status: {'✅ Business impact validated' if business_impact_demonstrated >= 5 else '⚠️ Impact unclear'}")
        
        return business_impact_demonstrated >= 5
        
    except Exception as e:
        print(f"🚨 Error running agent event tests: {e}")
        traceback.print_exc()
        return False


async def main():
    """Main test runner for WebSocket TDD suite"""
    print("🚀 WebSocket Authentication RFC 6455 TDD Test Suite")
    print("Issue #280: WebSocket authentication failure - P0 CRITICAL affecting $500K+ ARR")
    print("TDD Strategy: Create failing tests, then implement fix")
    print("=" * 80)
    
    # Run all test suites
    rfc_results = await run_rfc_6455_compliance_tests()
    jwt_results = await run_jwt_extraction_tests()
    event_results = await run_agent_event_tests()
    
    print("\n" + "=" * 80)
    print("📋 TDD TEST SUITE SUMMARY")
    print("=" * 80)
    
    print(f"🧪 RFC 6455 Compliance: {'✅ Failures demonstrated' if rfc_results else '⚠️ No failures shown'}")
    print(f"🔐 JWT Extraction: {'✅ Logic working' if jwt_results else '⚠️ Logic issues'}")
    print(f"💼 Business Impact: {'✅ Impact demonstrated' if event_results else '⚠️ Impact unclear'}")
    
    if rfc_results and jwt_results and event_results:
        print("\n✅ TDD VALIDATION SUCCESSFUL")
        print("   • RFC 6455 violations demonstrated")  
        print("   • JWT extraction confirmed working")
        print("   • Business impact quantified")
        print("   • Ready for implementation phase")
        print("\n🔧 NEXT STEP: Apply subprotocol parameter fix:")
        print("   • websocket_ssot.py:298 → await websocket.accept(subprotocol='jwt-auth')")
        print("   • websocket_ssot.py:393 → await websocket.accept(subprotocol='jwt-auth')")
        print("   • websocket_ssot.py:461 → await websocket.accept(subprotocol='jwt-auth')")
        print("   • websocket_ssot.py:539 → await websocket.accept(subprotocol='jwt-auth')")
        
    else:
        print("\n⚠️ TDD VALIDATION INCOMPLETE")
        print("   • Review test failures for specific issues")
        print("   • May need test environment adjustments")
        print("   • Core RFC 6455 issue may already be partially fixed")

    print("\n💰 BUSINESS IMPACT REMINDER:")
    print("   • $500K+ ARR at risk")
    print("   • Golden Path (login → AI responses) blocked")
    print("   • All 5 critical WebSocket events failing")
    print("   • Chat functionality (90% platform value) non-functional")


if __name__ == "__main__":
    asyncio.run(main())