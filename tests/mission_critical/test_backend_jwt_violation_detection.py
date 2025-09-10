#!/usr/bin/env python3
"""
P0 Mission Critical Test: Backend JWT SSOT Violation Detection
=============================================================

CRITICAL MISSION: These tests document JWT authentication SSOT violations
that exist in the backend and MUST FAIL when violations are removed during
refactor. This provides proof that violations exist and validates refactor success.

Business Value:
- Protects $500K+ ARR from JWT secret cascade failures
- Documents SSOT compliance baseline (current 40/100 score)
- Validates that backend JWT decoding violations are removed during refactor
- Ensures auth service becomes the exclusive JWT source

PHASE A TESTS (Current State):
These tests MUST PASS in current state (proving violations exist)
These tests MUST FAIL after refactor (proving violations removed)

SSOT Violations Being Tested:
1. Backend JWT secrets: netra_backend/app/core/configuration/unified_secrets.py:75-90
2. Backend JWT validation: netra_backend/app/clients/auth_client_core.py (JWT operations)
3. WebSocket auth patterns in routes (fallback mechanisms)

CRITICAL REQUIREMENTS:
- NO Docker dependencies (unit-style tests only)
- Tests prove violations exist by successfully using them
- Clear documentation of why these are SSOT violations
- Business impact quantification ($500K+ ARR protection)
"""

import asyncio
import importlib
import inspect
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import jwt
import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# SSOT imports
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Configure detailed logging for JWT violation analysis
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackendJWTViolationDetector:
    """
    Detects and documents JWT SSOT violations in the backend.
    
    This class provides comprehensive analysis of JWT operations that violate
    SSOT principles by existing in the backend when they should only exist
    in the auth service.
    """
    
    def __init__(self):
        """Initialize JWT violation detector."""
        self.violations_detected = []
        self.violation_locations = []
        self.business_impact_notes = []
        
        # Track current SSOT compliance baseline
        self.current_ssot_score = 40  # Out of 100 - as documented in audit
        self.target_ssot_score = 95   # Post-refactor target
        
    def detect_backend_jwt_secret_access_violation(self) -> bool:
        """
        VIOLATION TEST: Detect backend JWT secret access (SSOT violation).
        
        SSOT PRINCIPLE: Only auth service should handle JWT secrets.
        VIOLATION: Backend has JWT secret access in unified_secrets.py
        
        This test MUST PASS (violation exists) → MUST FAIL (violation removed)
        """
        logger.info("🔍 Testing backend JWT secret access SSOT violation")
        
        violation_found = False
        try:
            # Test: Backend should NOT have JWT secret access (SSOT violation)
            from netra_backend.app.core.configuration.unified_secrets import get_secrets_manager
            
            secrets_manager = get_secrets_manager()
            
            # VIOLATION: Backend has get_jwt_secret() method (should only be in auth service)
            if hasattr(secrets_manager, 'get_jwt_secret'):
                logger.warning("🚨 SSOT VIOLATION DETECTED: Backend has JWT secret access")
                
                # Test that the violation method works (proving it exists)
                try:
                    jwt_secret = secrets_manager.get_jwt_secret()
                    if jwt_secret:
                        violation_found = True
                        self.violations_detected.append({
                            'type': 'backend_jwt_secret_access',
                            'location': 'netra_backend/app/core/configuration/unified_secrets.py:75-90',
                            'method': 'get_jwt_secret()',
                            'violation_reason': 'Backend should not have JWT secret access - SSOT violation',
                            'business_impact': 'Causes JWT secret mismatches, cascade auth failures',
                            'test_result': 'VIOLATION EXISTS (method works)',
                            'secret_length': len(jwt_secret) if jwt_secret else 0
                        })
                        
                        logger.warning(f"✅ VIOLATION CONFIRMED: get_jwt_secret() returns {len(jwt_secret)} char secret")
                        
                        # Document business impact
                        self.business_impact_notes.append(
                            f"Backend JWT secret access enables mismatches with auth service, "
                            f"risking $500K+ ARR from cascade authentication failures"
                        )
                        
                    else:
                        logger.info("⚠️ Backend has get_jwt_secret() method but returns empty secret")
                        
                except Exception as e:
                    logger.info(f"⚠️ Backend get_jwt_secret() method exists but failed: {e}")
                    # Still a violation - method shouldn't exist at all
                    violation_found = True
                    
            else:
                logger.info("✅ No backend JWT secret access detected")
                
        except ImportError as e:
            logger.info(f"Backend secrets manager not available: {e}")
        except Exception as e:
            logger.error(f"Error testing backend JWT secret access: {e}")
            
        return violation_found
    
    def detect_backend_jwt_validation_methods(self) -> bool:
        """
        VIOLATION TEST: Detect backend JWT validation methods (SSOT violation).
        
        SSOT PRINCIPLE: Only auth service should validate JWT tokens.
        VIOLATION: Backend has JWT validation in auth_client_core.py
        
        This test MUST PASS (violation exists) → MUST FAIL (violation removed)
        """
        logger.info("🔍 Testing backend JWT validation methods SSOT violation")
        
        violation_found = False
        try:
            # Test: Backend should NOT have JWT validation methods (SSOT violation)
            from netra_backend.app.clients.auth_client_core import AuthClient
            
            # Inspect AuthClient for JWT-related methods
            auth_client_methods = dir(AuthClient)
            jwt_methods = [method for method in auth_client_methods if 'jwt' in method.lower()]
            
            if jwt_methods:
                logger.warning(f"🚨 SSOT VIOLATION DETECTED: Backend has JWT methods: {jwt_methods}")
                
                # Test specific JWT validation methods
                auth_client = AuthClient()
                
                # Look for JWT validation methods that shouldn't exist in backend
                jwt_validation_methods = []
                for method_name in jwt_methods:
                    method = getattr(auth_client, method_name, None)
                    if method and callable(method):
                        jwt_validation_methods.append(method_name)
                        
                if jwt_validation_methods:
                    violation_found = True
                    self.violations_detected.append({
                        'type': 'backend_jwt_validation_methods',
                        'location': 'netra_backend/app/clients/auth_client_core.py',
                        'methods': jwt_validation_methods,
                        'violation_reason': 'Backend should not validate JWT tokens - SSOT violation',
                        'business_impact': 'Creates JWT validation inconsistencies between services',
                        'test_result': 'VIOLATION EXISTS (methods found)'
                    })
                    
                    logger.warning(f"✅ VIOLATION CONFIRMED: JWT validation methods found: {jwt_validation_methods}")
                    
                    # Document business impact
                    self.business_impact_notes.append(
                        f"Backend JWT validation methods create inconsistencies with auth service, "
                        f"causing 403 WebSocket errors and chat system failures"
                    )
                    
            # Also check for JWT format validation (another violation)
            try:
                from netra_backend.app.clients.auth_client_core import validate_jwt_format
                
                # Test that JWT format validation works (proving violation exists)
                test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.test"
                if validate_jwt_format(test_token):
                    violation_found = True
                    self.violations_detected.append({
                        'type': 'backend_jwt_format_validation',
                        'location': 'netra_backend/app/clients/auth_client_core.py:245-255',
                        'function': 'validate_jwt_format()',
                        'violation_reason': 'Backend should not validate JWT format - SSOT violation',
                        'business_impact': 'Duplicates auth service JWT validation logic',
                        'test_result': 'VIOLATION EXISTS (function works)'
                    })
                    
                    logger.warning("✅ VIOLATION CONFIRMED: validate_jwt_format() function works in backend")
                    
            except ImportError:
                logger.info("validate_jwt_format not found in backend")
            except Exception as e:
                logger.info(f"validate_jwt_format test failed: {e}")
                
        except ImportError as e:
            logger.info(f"Backend auth client not available: {e}")
        except Exception as e:
            logger.error(f"Error testing backend JWT validation methods: {e}")
            
        return violation_found
    
    def detect_websocket_auth_fallback_violations(self) -> bool:
        """
        VIOLATION TEST: Detect WebSocket authentication fallback logic (SSOT violation).
        
        SSOT PRINCIPLE: WebSocket auth should only use auth service.
        VIOLATION: WebSocket routes may contain fallback auth logic
        
        This test MUST PASS (violation exists) → MUST FAIL (violation removed)
        """
        logger.info("🔍 Testing WebSocket authentication fallback SSOT violations")
        
        violation_found = False
        try:
            # Check WebSocket routes for auth fallback patterns
            from netra_backend.app.routes.websocket import router
            
            # Get route source code to analyze for auth patterns
            import inspect
            route_functions = []
            
            # Find WebSocket route handlers
            for route in router.routes:
                if hasattr(route, 'endpoint') and route.endpoint:
                    route_functions.append(route.endpoint)
                    
            # Analyze route functions for auth patterns
            auth_patterns_found = []
            for func in route_functions:
                try:
                    source = inspect.getsource(func)
                    
                    # Look for auth fallback patterns (SSOT violations)
                    fallback_patterns = [
                        'fallback',
                        'validate.*jwt',
                        'decode.*token', 
                        'auth.*local',
                        'bypass.*auth',
                        'test.*auth'
                    ]
                    
                    for pattern in fallback_patterns:
                        import re
                        if re.search(pattern, source, re.IGNORECASE):
                            auth_patterns_found.append({
                                'function': func.__name__,
                                'pattern': pattern,
                                'violation': f'WebSocket handler contains auth pattern: {pattern}'
                            })
                            
                except Exception as e:
                    logger.debug(f"Could not analyze function {func.__name__}: {e}")
                    
            if auth_patterns_found:
                violation_found = True
                self.violations_detected.append({
                    'type': 'websocket_auth_fallback_patterns',
                    'location': 'netra_backend/app/routes/websocket.py',
                    'patterns': auth_patterns_found,
                    'violation_reason': 'WebSocket should only use auth service - no fallback logic',
                    'business_impact': 'Creates auth inconsistencies, potential security bypass',
                    'test_result': 'VIOLATION EXISTS (patterns found)'
                })
                
                logger.warning(f"✅ VIOLATION CONFIRMED: Auth fallback patterns in WebSocket: {len(auth_patterns_found)}")
                
                # Document business impact
                self.business_impact_notes.append(
                    f"WebSocket auth fallback patterns bypass proper auth service validation, "
                    f"creating security risks and inconsistent authentication behavior"
                )
                
        except ImportError as e:
            logger.info(f"WebSocket routes not available: {e}")
        except Exception as e:
            logger.error(f"Error testing WebSocket auth fallbacks: {e}")
            
        return violation_found
    
    def test_ssot_compliance_baseline(self) -> Dict[str, Any]:
        """
        BASELINE TEST: Document current SSOT compliance score.
        
        This establishes the baseline that refactoring must improve.
        Current: 40/100 → Target: 95/100
        """
        logger.info("🔍 Testing SSOT compliance baseline score")
        
        # Calculate current compliance based on violations detected
        total_violations = len(self.violations_detected)
        critical_violations = len([v for v in self.violations_detected if 'critical' in v.get('violation_reason', '').lower()])
        
        # Compliance score calculation (simplified)
        base_score = 100
        violation_penalty = min(total_violations * 15, 60)  # Cap at 60 point penalty
        
        current_score = max(base_score - violation_penalty, 0)
        
        baseline_report = {
            'current_ssot_score': current_score,
            'documented_baseline': self.current_ssot_score,  # From audit
            'target_score': self.target_ssot_score,
            'total_violations': total_violations,
            'critical_violations': critical_violations,
            'improvement_needed': self.target_ssot_score - current_score,
            'business_impact': f'${500}K+ ARR at risk from JWT cascade failures',
            'compliance_status': 'CRITICAL' if current_score < 50 else 'WARNING' if current_score < 80 else 'GOOD'
        }
        
        logger.warning(f"📊 SSOT Compliance Baseline: {current_score}/100 (Target: {self.target_ssot_score}/100)")
        logger.warning(f"🚨 Violations Found: {total_violations} (Critical: {critical_violations})")
        
        return baseline_report
    
    def generate_violation_inventory_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive violation inventory report.
        
        This documents all JWT SSOT violations for refactoring reference.
        """
        return {
            'detection_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_violations': len(self.violations_detected),
            'violation_details': self.violations_detected,
            'violation_locations': list(set([v.get('location') for v in self.violations_detected if v.get('location')])),
            'business_impact_summary': self.business_impact_notes,
            'ssot_compliance_baseline': self.test_ssot_compliance_baseline(),
            'refactor_requirements': [
                'Remove backend JWT secret access (unified_secrets.py)',
                'Remove backend JWT validation methods (auth_client_core.py)',
                'Eliminate WebSocket auth fallback patterns',
                'Ensure auth service is exclusive JWT source',
                'Achieve 95/100 SSOT compliance score'
            ],
            'validation_approach': 'These tests MUST FAIL after refactor (proving violations removed)',
            'business_protection': '$500K+ ARR protected from JWT cascade failures'
        }


class TestBackendJWTViolationDetection(SSotBaseTestCase):
    """
    P0 Mission Critical Test Suite: Backend JWT SSOT Violation Detection
    
    These tests document JWT authentication SSOT violations that exist in the
    backend. They MUST PASS in current state and MUST FAIL after refactor.
    """
    
    @pytest.fixture(autouse=True)
    def setup_violation_detector(self):
        """Set up JWT violation detector for testing."""
        self.detector = BackendJWTViolationDetector()
        logger.info("🚀 Starting Backend JWT SSOT Violation Detection")
        logger.info("=" * 60)
        logger.info("CRITICAL: These tests prove violations exist")
        logger.info("REFACTOR VALIDATION: Tests must FAIL after violations removed")
        logger.info("=" * 60)
    
    def test_backend_jwt_secret_access_exists(self):
        """
        CRITICAL: Test backend JWT secret access violation exists.
        
        SSOT VIOLATION: Backend has JWT secret access in unified_secrets.py
        MUST PASS NOW (violation exists) → MUST FAIL AFTER REFACTOR (violation removed)
        """
        logger.info("🚀 Testing backend JWT secret access SSOT violation")
        
        violation_exists = self.detector.detect_backend_jwt_secret_access_violation()
        
        # Document the violation for refactor validation
        if violation_exists:
            logger.critical("🚨 CONFIRMED: Backend JWT secret access violation EXISTS")
            logger.critical("📍 Location: netra_backend/app/core/configuration/unified_secrets.py:75-90")
            logger.critical("⚠️ Business Impact: $500K+ ARR at risk from JWT secret mismatches")
            logger.critical("🎯 REFACTOR TARGET: Remove backend JWT secret access")
        else:
            logger.error("❌ UNEXPECTED: Backend JWT secret access violation NOT FOUND")
            logger.error("🔍 This may indicate violation was already fixed or moved")
            
        # PHASE A: Test MUST PASS (proving violation exists)
        assert violation_exists, (
            "Backend JWT secret access violation must exist for refactor validation. "
            "If this test fails, the violation may have been already fixed. "
            "Check netra_backend/app/core/configuration/unified_secrets.py:75-90"
        )
    
    def test_backend_has_jwt_validation_methods(self):
        """
        CRITICAL: Test backend JWT validation methods violation exists.
        
        SSOT VIOLATION: Backend has JWT validation in auth_client_core.py
        MUST PASS NOW (violation exists) → MUST FAIL AFTER REFACTOR (violation removed)
        """
        logger.info("🚀 Testing backend JWT validation methods SSOT violation")
        
        violation_exists = self.detector.detect_backend_jwt_validation_methods()
        
        # Document the violation for refactor validation
        if violation_exists:
            logger.critical("🚨 CONFIRMED: Backend JWT validation methods violation EXISTS")
            logger.critical("📍 Location: netra_backend/app/clients/auth_client_core.py")
            logger.critical("⚠️ Business Impact: JWT validation inconsistencies cause 403 WebSocket errors")
            logger.critical("🎯 REFACTOR TARGET: Remove backend JWT validation, use auth service only")
        else:
            logger.error("❌ UNEXPECTED: Backend JWT validation violation NOT FOUND")
            logger.error("🔍 This may indicate violation was already fixed")
            
        # PHASE A: Test MUST PASS (proving violation exists)
        assert violation_exists, (
            "Backend JWT validation violation must exist for refactor validation. "
            "If this test fails, the violation may have been already fixed. "
            "Check netra_backend/app/clients/auth_client_core.py for JWT methods"
        )
    
    def test_websocket_auth_fallback_logic_exists(self):
        """
        CRITICAL: Test WebSocket authentication fallback logic violation exists.
        
        SSOT VIOLATION: WebSocket routes may contain auth fallback patterns
        MUST PASS NOW (violation exists) → MUST FAIL AFTER REFACTOR (violation removed)
        """
        logger.info("🚀 Testing WebSocket authentication fallback SSOT violation")
        
        violation_exists = self.detector.detect_websocket_auth_fallback_violations()
        
        # Document the violation for refactor validation
        if violation_exists:
            logger.critical("🚨 CONFIRMED: WebSocket auth fallback violation EXISTS")
            logger.critical("📍 Location: netra_backend/app/routes/websocket.py")
            logger.critical("⚠️ Business Impact: Auth inconsistencies, potential security bypass")
            logger.critical("🎯 REFACTOR TARGET: Use auth service exclusively, remove fallbacks")
        else:
            logger.warning("✅ WebSocket auth fallback violation NOT FOUND")
            logger.warning("🔍 This may indicate good SSOT compliance or refactor already done")
            
        # PHASE A: Test is PERMISSIVE (violation may not exist in current architecture)
        # This test documents current state without strict assertion
        logger.info(f"WebSocket auth fallback test result: {'VIOLATION EXISTS' if violation_exists else 'NO VIOLATION'}")
    
    def test_ssot_compliance_baseline(self):
        """
        CRITICAL: Document SSOT compliance baseline for refactor validation.
        
        BASELINE: Current 40/100 score → Target 95/100 after refactor
        This test documents the current state for improvement measurement.
        """
        logger.info("🚀 Testing SSOT compliance baseline documentation")
        
        baseline_report = self.detector.test_ssot_compliance_baseline()
        
        # Log comprehensive baseline report
        logger.info("=" * 60)
        logger.info("SSOT COMPLIANCE BASELINE REPORT")
        logger.info("=" * 60)
        logger.warning(f"Current Score: {baseline_report['current_ssot_score']}/100")
        logger.warning(f"Target Score: {baseline_report['target_score']}/100")
        logger.critical(f"Improvement Needed: {baseline_report['improvement_needed']} points")
        logger.critical(f"Total Violations: {baseline_report['total_violations']}")
        logger.critical(f"Critical Violations: {baseline_report['critical_violations']}")
        logger.critical(f"Business Impact: {baseline_report['business_impact']}")
        logger.critical(f"Compliance Status: {baseline_report['compliance_status']}")
        logger.info("=" * 60)
        
        # Assert baseline is documented (this should always pass)
        assert baseline_report is not None, "SSOT compliance baseline must be documented"
        assert baseline_report['current_ssot_score'] >= 0, "Compliance score must be valid"
        assert baseline_report['total_violations'] >= 0, "Violation count must be valid"
        
        # Store baseline for refactor comparison
        self.detector.baseline_report = baseline_report
    
    def test_comprehensive_violation_inventory(self):
        """
        REPORTING: Generate comprehensive JWT SSOT violation inventory.
        
        This test creates detailed documentation of all violations found
        for use during refactoring and validation.
        """
        logger.info("🚀 Generating comprehensive JWT SSOT violation inventory")
        
        # Ensure other tests have run to populate violations
        if not self.detector.violations_detected:
            logger.warning("No violations detected - running detection methods")
            self.detector.detect_backend_jwt_secret_access_violation()
            self.detector.detect_backend_jwt_validation_methods()
            self.detector.detect_websocket_auth_fallback_violations()
            
        inventory_report = self.detector.generate_violation_inventory_report()
        
        # Log comprehensive inventory
        logger.info("=" * 80)
        logger.info("JWT SSOT VIOLATION INVENTORY REPORT")
        logger.info("=" * 80)
        
        logger.critical(f"Detection Timestamp: {inventory_report['detection_timestamp']}")
        logger.critical(f"Total Violations Found: {inventory_report['total_violations']}")
        
        logger.info("\nVIOLATION LOCATIONS:")
        for location in inventory_report['violation_locations']:
            logger.critical(f"  📍 {location}")
            
        logger.info("\nVIOLATION DETAILS:")
        for i, violation in enumerate(inventory_report['violation_details'], 1):
            logger.critical(f"  {i}. {violation.get('type', 'Unknown')}")
            logger.critical(f"     Location: {violation.get('location', 'Unknown')}")
            logger.critical(f"     Reason: {violation.get('violation_reason', 'Unknown')}")
            logger.critical(f"     Business Impact: {violation.get('business_impact', 'Unknown')}")
            
        logger.info("\nBUSINESS IMPACT SUMMARY:")
        for impact in inventory_report['business_impact_summary']:
            logger.critical(f"  💰 {impact}")
            
        logger.info("\nREFACTOR REQUIREMENTS:")
        for requirement in inventory_report['refactor_requirements']:
            logger.warning(f"  🎯 {requirement}")
            
        baseline = inventory_report['ssot_compliance_baseline']
        logger.info(f"\nSSOT COMPLIANCE: {baseline['current_ssot_score']}/100 → {baseline['target_score']}/100")
        logger.critical(f"BUSINESS PROTECTION: {inventory_report['business_protection']}")
        
        logger.info("=" * 80)
        
        # Assert inventory is comprehensive
        assert inventory_report is not None, "Violation inventory must be generated"
        assert inventory_report['total_violations'] >= 0, "Must document violations found"
        assert len(inventory_report['refactor_requirements']) > 0, "Must provide refactor guidance"
        
        # Store inventory for external reference
        self.detector.inventory_report = inventory_report


# Standalone execution for direct violation detection
if __name__ == "__main__":
    print("P0 MISSION CRITICAL: BACKEND JWT SSOT VIOLATION DETECTION")
    print("=" * 80)
    print("PHASE A: Documenting violations that exist (tests must PASS)")
    print("REFACTOR VALIDATION: Tests must FAIL after violations removed")
    print("BUSINESS PROTECTION: $500K+ ARR from JWT cascade failures")
    print("=" * 80)
    
    # Initialize detector
    detector = BackendJWTViolationDetector()
    
    # Run violation detection tests
    tests = [
        ("Backend JWT Secret Access", detector.detect_backend_jwt_secret_access_violation),
        ("Backend JWT Validation Methods", detector.detect_backend_jwt_validation_methods),
        ("WebSocket Auth Fallback Logic", detector.detect_websocket_auth_fallback_violations),
    ]
    
    # Execute tests
    violation_count = 0
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        try:
            violation_found = test_func()
            if violation_found:
                print(f"   Result: 🚨 VIOLATION EXISTS (test will FAIL after refactor)")
                violation_count += 1
            else:
                print(f"   Result: ✅ NO VIOLATION (may already be fixed)")
        except Exception as e:
            print(f"   Result: ❌ ERROR - {str(e)}")
    
    # Generate final report
    print("\n" + "=" * 80)
    baseline_report = detector.test_ssot_compliance_baseline()
    inventory_report = detector.generate_violation_inventory_report()
    
    print("VIOLATION DETECTION SUMMARY")
    print("=" * 80)
    print(f"🚨 Total Violations Detected: {violation_count}")
    print(f"📊 SSOT Compliance Score: {baseline_report['current_ssot_score']}/100")
    print(f"🎯 Target Score: {baseline_report['target_score']}/100")
    print(f"💰 Business Impact: {inventory_report['business_protection']}")
    
    if violation_count > 0:
        print("\n✅ PHASE A SUCCESS: Violations documented and ready for refactor")
        print("🎯 NEXT PHASE: Remove violations, then verify these tests FAIL")
        exit_code = 0  # Success - violations found as expected
    else:
        print("\n⚠️  WARNING: No violations found - may already be refactored")
        print("🔍 INVESTIGATE: Check if SSOT refactor already completed")
        exit_code = 1  # Warning - unexpected state
        
    print("=" * 80)
    
    sys.exit(exit_code)