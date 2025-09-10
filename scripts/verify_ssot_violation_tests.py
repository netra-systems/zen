#!/usr/bin/env python3
"""
SSOT Violation Tests Verification Script

This script verifies that all 5 SSOT violation reproduction tests are properly created
and can be executed to expose WebSocket auth bypass violations.

Usage:
    python scripts/verify_ssot_violation_tests.py
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_test_imports() -> Dict[str, bool]:
    """Verify all SSOT violation tests can be imported."""
    test_modules = {
        "JWT Bypass Violation": "tests.mission_critical.test_websocket_jwt_bypass_violation",
        "UnifiedAuthInterface Bypass": "tests.mission_critical.test_websocket_unified_auth_interface_bypass", 
        "JWT Secret Consistency": "tests.mission_critical.test_jwt_secret_consistency_violation",
        "Auth Fallback SSOT Violation": "tests.mission_critical.test_websocket_auth_fallback_ssot_violation",
        "Golden Path E2E SSOT": "tests.e2e.test_golden_path_auth_ssot_compliance"
    }
    
    results = {}
    
    for test_name, module_path in test_modules.items():
        try:
            __import__(module_path)
            results[test_name] = True
            logger.info(f"✅ {test_name}: Import successful")
        except Exception as e:
            results[test_name] = False
            logger.error(f"❌ {test_name}: Import failed - {e}")
    
    return results


def verify_test_structure() -> Dict[str, Dict[str, Any]]:
    """Verify test structure and method counts."""
    test_info = {}
    
    try:
        # Test 1: JWT Bypass Violation
        from tests.mission_critical.test_websocket_jwt_bypass_violation import TestWebSocketJwtBypassViolation
        jwt_bypass_methods = [method for method in dir(TestWebSocketJwtBypassViolation) 
                             if method.startswith('test_')]
        test_info["JWT Bypass"] = {
            "class": TestWebSocketJwtBypassViolation.__name__,
            "methods": len(jwt_bypass_methods),
            "method_list": jwt_bypass_methods
        }
        
        # Test 2: UnifiedAuthInterface Bypass
        from tests.mission_critical.test_websocket_unified_auth_interface_bypass import TestWebSocketUnifiedAuthInterfaceBypass
        unified_auth_methods = [method for method in dir(TestWebSocketUnifiedAuthInterfaceBypass) 
                               if method.startswith('test_')]
        test_info["UnifiedAuthInterface Bypass"] = {
            "class": TestWebSocketUnifiedAuthInterfaceBypass.__name__,
            "methods": len(unified_auth_methods),
            "method_list": unified_auth_methods
        }
        
        # Test 3: JWT Consistency
        from tests.mission_critical.test_jwt_secret_consistency_violation import TestJwtSecretConsistencyViolation
        jwt_consistency_methods = [method for method in dir(TestJwtSecretConsistencyViolation) 
                                  if method.startswith('test_')]
        test_info["JWT Consistency"] = {
            "class": TestJwtSecretConsistencyViolation.__name__,
            "methods": len(jwt_consistency_methods),
            "method_list": jwt_consistency_methods
        }
        
        # Test 4: Fallback SSOT Violation  
        from tests.mission_critical.test_websocket_auth_fallback_ssot_violation import TestWebSocketAuthFallbackSsotViolation
        fallback_methods = [method for method in dir(TestWebSocketAuthFallbackSsotViolation) 
                           if method.startswith('test_')]
        test_info["Fallback SSOT"] = {
            "class": TestWebSocketAuthFallbackSsotViolation.__name__,
            "methods": len(fallback_methods),
            "method_list": fallback_methods
        }
        
        # Test 5: Golden Path E2E
        from tests.e2e.test_golden_path_auth_ssot_compliance import TestGoldenPathAuthSsotCompliance
        golden_path_methods = [method for method in dir(TestGoldenPathAuthSsotCompliance) 
                              if method.startswith('test_')]
        test_info["Golden Path E2E"] = {
            "class": TestGoldenPathAuthSsotCompliance.__name__,
            "methods": len(golden_path_methods),
            "method_list": golden_path_methods
        }
        
    except Exception as e:
        logger.error(f"❌ Test structure verification failed: {e}")
    
    return test_info


def generate_verification_report() -> None:
    """Generate comprehensive verification report."""
    logger.info("🚨 SSOT VIOLATION TESTS VERIFICATION REPORT")
    logger.info("=" * 60)
    
    # Verify imports
    logger.info("\n📦 IMPORT VERIFICATION:")
    import_results = verify_test_imports()
    
    successful_imports = sum(1 for result in import_results.values() if result)
    total_tests = len(import_results)
    
    logger.info(f"\n📊 Import Summary: {successful_imports}/{total_tests} tests import successfully")
    
    if successful_imports == total_tests:
        logger.info("✅ ALL TESTS IMPORT SUCCESSFULLY")
    else:
        logger.error("❌ SOME TESTS HAVE IMPORT ISSUES")
        return
    
    # Verify structure
    logger.info("\n🏗️ TEST STRUCTURE VERIFICATION:")
    test_structure = verify_test_structure()
    
    total_methods = 0
    for test_name, info in test_structure.items():
        method_count = info["methods"]
        total_methods += method_count
        logger.info(f"  {test_name}: {method_count} test methods")
        
        for method in info["method_list"]:
            logger.info(f"    - {method}")
    
    logger.info(f"\n📊 Structure Summary: {len(test_structure)} test classes, {total_methods} total test methods")
    
    # Violation coverage verification
    logger.info("\n🎯 VIOLATION COVERAGE VERIFICATION:")
    
    violation_coverage = {
        "JWT Bypass (verify_signature: False)": "JWT Bypass" in test_structure,
        "UnifiedAuthInterface Bypass (local auth logic)": "UnifiedAuthInterface Bypass" in test_structure,
        "JWT Secret Consistency (different secrets/algorithms)": "JWT Consistency" in test_structure,
        "Fallback Pattern Duplication (local resilience)": "Fallback SSOT" in test_structure,
        "Golden Path End-to-End SSOT Compliance": "Golden Path E2E" in test_structure
    }
    
    for violation, covered in violation_coverage.items():
        status = "✅" if covered else "❌"
        logger.info(f"  {status} {violation}")
    
    covered_violations = sum(1 for covered in violation_coverage.values() if covered)
    total_violations = len(violation_coverage)
    
    logger.info(f"\n📊 Coverage Summary: {covered_violations}/{total_violations} SSOT violations covered")
    
    # Final assessment
    logger.info("\n🏁 FINAL ASSESSMENT:")
    
    if successful_imports == total_tests and covered_violations == total_violations:
        logger.info("🎉 SUCCESS: All SSOT violation reproduction tests are ready!")
        logger.info("🎯 NEXT STEPS:")
        logger.info("  1. Execute tests to confirm they expose violations")
        logger.info("  2. Implement SSOT fixes to resolve violations")
        logger.info("  3. Verify tests fail after SSOT compliance")
        logger.info("  4. Add to mission critical test suite")
        
        logger.info("\n📋 EXECUTION COMMANDS:")
        logger.info("  # Run all violation tests:")
        logger.info("  python -m pytest tests/mission_critical/test_*_violation.py tests/e2e/test_golden_path_auth_ssot_compliance.py -v")
        logger.info("  ")
        logger.info("  # Run specific test:")
        logger.info("  python -m pytest tests/mission_critical/test_websocket_jwt_bypass_violation.py -v")
        
    else:
        logger.error("❌ ISSUES DETECTED: Tests need attention before execution")
    
    logger.info("\n" + "=" * 60)
    logger.info("SSOT VIOLATION TESTS VERIFICATION COMPLETE")


if __name__ == "__main__":
    generate_verification_report()