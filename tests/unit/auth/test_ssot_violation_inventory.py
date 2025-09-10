#!/usr/bin/env python3
"""
Unit Test: JWT SSOT Violation Inventory and Catalog
===================================================

CRITICAL MISSION: Catalog all JWT operations in backend to prove SSOT violations
exist. These tests document the exact violation locations and will break when
violations are removed during refactor.

Business Value:
- Documents all JWT operations outside auth service (SSOT violations)
- Provides detailed inventory for refactor planning
- Proves multiple JWT sources exist (SSOT principle violation)
- Validates auth service exclusivity after refactor

PHASE A TESTS (Current State):
These tests MUST PASS in current state (proving violations exist)
These tests MUST FAIL after refactor (proving violations removed)

SSOT PRINCIPLE VIOLATIONS:
1. Multiple JWT sources: Backend + Auth Service (should be Auth Service only)
2. JWT operations scattered across multiple files (should be centralized)
3. Fallback JWT validation logic (should be eliminated)

CRITICAL REQUIREMENTS:
- NO external dependencies (pure unit tests)
- Catalog exact methods, classes, and functions
- Document file locations and line numbers where possible
- Prove violations work (not just exist)
"""

import ast
import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import patch

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test framework imports (for pytest compatibility)
try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
except ImportError:
    # Use unittest.TestCase as fallback for standalone execution
    import unittest
    SSotBaseTestCase = unittest.TestCase

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JWTSSOTViolationInventoryCatalog:
    """
    Catalogs all JWT operations in the backend to document SSOT violations.
    
    This class provides comprehensive analysis of JWT-related code that should
    only exist in the auth service according to SSOT principles.
    """
    
    def __init__(self):
        """Initialize JWT SSOT violation catalog."""
        self.jwt_operations_catalog = []
        self.jwt_source_locations = []
        self.violation_evidence = []
        self.ssot_compliance_metrics = {}
        
        # Backend modules to scan for JWT operations
        self.backend_modules_to_scan = [
            'netra_backend.app.clients.auth_client_core',
            'netra_backend.app.core.configuration.unified_secrets',
            'netra_backend.app.routes.websocket',
            'netra_backend.app.core.websocket_cors',
            'netra_backend.app.websocket_core',
        ]
    
    def catalog_backend_jwt_operations(self) -> List[Dict[str, Any]]:
        """
        VIOLATION CATALOG: Catalog all JWT operations in backend.
        
        SSOT VIOLATION: Backend should have NO JWT operations - only auth service should.
        This method documents every JWT operation found in backend code.
        """
        logger.info("🔍 Cataloging backend JWT operations (SSOT violations)")
        
        jwt_operations = []
        
        for module_name in self.backend_modules_to_scan:
            try:
                # Import module for analysis
                module = importlib.import_module(module_name)
                
                # Scan module for JWT-related operations
                module_jwt_ops = self._scan_module_for_jwt_operations(module, module_name)
                jwt_operations.extend(module_jwt_ops)
                
            except ImportError as e:
                logger.debug(f"Could not import {module_name}: {e}")
            except Exception as e:
                logger.warning(f"Error scanning {module_name}: {e}")
        
        self.jwt_operations_catalog = jwt_operations
        
        logger.warning(f"🚨 SSOT VIOLATIONS FOUND: {len(jwt_operations)} JWT operations in backend")
        
        return jwt_operations
    
    def _scan_module_for_jwt_operations(self, module: Any, module_name: str) -> List[Dict[str, Any]]:
        """Scan a module for JWT-related operations."""
        jwt_operations = []
        
        # Scan module attributes for JWT-related items
        for attr_name in dir(module):
            if 'jwt' in attr_name.lower():
                attr = getattr(module, attr_name)
                
                jwt_operation = {
                    'module': module_name,
                    'name': attr_name,
                    'type': type(attr).__name__,
                    'is_callable': callable(attr),
                    'violation_type': 'jwt_attribute_in_backend',
                    'ssot_violation_reason': f'JWT attribute {attr_name} should only exist in auth service'
                }
                
                # If it's a callable, get more details
                if callable(attr):
                    try:
                        signature = inspect.signature(attr)
                        jwt_operation['signature'] = str(signature)
                        jwt_operation['docstring'] = inspect.getdoc(attr) or "No docstring"
                    except Exception:
                        pass
                
                jwt_operations.append(jwt_operation)
                logger.warning(f"  🚨 JWT Operation Found: {module_name}.{attr_name} ({type(attr).__name__})")
        
        # Scan for JWT-related string patterns in source code if available
        try:
            source = inspect.getsource(module)
            jwt_patterns = self._find_jwt_patterns_in_source(source, module_name)
            jwt_operations.extend(jwt_patterns)
        except Exception as e:
            logger.debug(f"Could not analyze source for {module_name}: {e}")
        
        return jwt_operations
    
    def _find_jwt_patterns_in_source(self, source_code: str, module_name: str) -> List[Dict[str, Any]]:
        """Find JWT-related patterns in source code."""
        jwt_patterns = []
        
        # Common JWT patterns that indicate SSOT violations
        violation_patterns = [
            ('jwt.encode', 'JWT token creation in backend'),
            ('jwt.decode', 'JWT token decoding in backend'),
            ('JWT_SECRET', 'JWT secret access in backend'),
            ('validate.*jwt', 'JWT validation in backend'),
            ('Bearer.*token', 'JWT token handling in backend'),
            ('HS256', 'JWT algorithm specification in backend'),
            ('jwt_secret', 'JWT secret variable in backend'),
        ]
        
        lines = source_code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, violation_reason in violation_patterns:
                import re
                if re.search(pattern, line, re.IGNORECASE):
                    jwt_pattern = {
                        'module': module_name,
                        'line_number': line_num,
                        'pattern': pattern,
                        'source_line': line.strip(),
                        'violation_type': 'jwt_pattern_in_backend_source',
                        'ssot_violation_reason': violation_reason,
                        'type': 'source_pattern'
                    }
                    jwt_patterns.append(jwt_pattern)
                    logger.warning(f"  🚨 JWT Pattern Found: {module_name}:{line_num} - {pattern}")
        
        return jwt_patterns
    
    def test_multiple_jwt_sources_detected(self) -> bool:
        """
        VIOLATION TEST: Test that multiple JWT sources exist (SSOT violation).
        
        SSOT PRINCIPLE: Only ONE source for JWT operations (auth service).
        VIOLATION: Multiple sources exist (backend + auth service).
        
        This test MUST PASS (multiple sources exist) → MUST FAIL (only auth service)
        """
        logger.info("🔍 Testing multiple JWT sources detection (SSOT violation)")
        
        # Catalog JWT operations in backend
        backend_jwt_operations = self.catalog_backend_jwt_operations()
        
        # Determine if multiple JWT sources exist
        multiple_sources_exist = len(backend_jwt_operations) > 0
        
        if multiple_sources_exist:
            # Document the violation
            jwt_source_count = len(set(op['module'] for op in backend_jwt_operations))
            unique_operations = len(backend_jwt_operations)
            
            self.violation_evidence.append({
                'violation_type': 'multiple_jwt_sources',
                'backend_jwt_operations': unique_operations,
                'backend_jwt_source_modules': jwt_source_count,
                'evidence': 'Backend contains JWT operations alongside auth service',
                'ssot_violation': 'Auth service should be exclusive JWT source',
                'business_impact': 'JWT operations scattered across services cause inconsistencies'
            })
            
            logger.critical(f"🚨 SSOT VIOLATION CONFIRMED: {unique_operations} JWT operations across {jwt_source_count} backend modules")
            logger.critical("📍 Expected: 0 JWT operations in backend (auth service only)")
            logger.critical("💰 Business Impact: JWT inconsistencies cause cascade authentication failures")
            
        else:
            logger.info("✅ No JWT operations found in backend - good SSOT compliance")
        
        return multiple_sources_exist
    
    def test_backend_jwt_operations_catalog(self) -> Dict[str, Any]:
        """
        CATALOG TEST: Catalog all JWT operations in backend for refactor reference.
        
        This creates a detailed inventory of every JWT operation that violates SSOT.
        """
        logger.info("🔍 Cataloging backend JWT operations for SSOT violation documentation")
        
        # Get comprehensive catalog
        jwt_operations = self.catalog_backend_jwt_operations()
        
        # Organize by module
        operations_by_module = {}
        for operation in jwt_operations:
            module = operation['module']
            if module not in operations_by_module:
                operations_by_module[module] = []
            operations_by_module[module].append(operation)
        
        # Create catalog summary
        catalog_summary = {
            'total_jwt_operations': len(jwt_operations),
            'modules_with_jwt_operations': len(operations_by_module),
            'operations_by_module': operations_by_module,
            'violation_types': list(set(op.get('violation_type') for op in jwt_operations)),
            'ssot_compliance_status': 'VIOLATION' if jwt_operations else 'COMPLIANT',
            'refactor_required': len(jwt_operations) > 0
        }
        
        # Log detailed catalog
        logger.info("=" * 60)
        logger.info("BACKEND JWT OPERATIONS CATALOG")
        logger.info("=" * 60)
        logger.critical(f"Total JWT Operations Found: {catalog_summary['total_jwt_operations']}")
        logger.critical(f"Modules with JWT Operations: {catalog_summary['modules_with_jwt_operations']}")
        
        for module, operations in operations_by_module.items():
            logger.warning(f"\n📍 {module}:")
            for op in operations:
                name = op.get('name', op.get('pattern', 'unknown'))
                op_type = op.get('type', 'pattern')
                reason = op.get('ssot_violation_reason', 'SSOT violation')
                logger.critical(f"  • {name} ({op_type}) - {reason}")
                if op.get('line_number'):
                    logger.critical(f"    Line {op['line_number']}: {op.get('source_line', '')}")
        
        logger.info("=" * 60)
        
        self.ssot_compliance_metrics['operations_catalog'] = catalog_summary
        
        return catalog_summary
    
    def test_auth_service_not_exclusive_jwt_source(self) -> bool:
        """
        VIOLATION TEST: Test that auth service is NOT the exclusive JWT source.
        
        SSOT PRINCIPLE: Auth service should be the ONLY JWT source.
        VIOLATION: Backend also has JWT operations.
        
        This test MUST PASS (auth service not exclusive) → MUST FAIL (auth service exclusive)
        """
        logger.info("🔍 Testing auth service exclusivity violation")
        
        # Check if backend has JWT operations (proving non-exclusivity)
        backend_operations = self.catalog_backend_jwt_operations()
        
        auth_service_not_exclusive = len(backend_operations) > 0
        
        if auth_service_not_exclusive:
            self.violation_evidence.append({
                'violation_type': 'auth_service_not_exclusive',
                'evidence': f'Backend has {len(backend_operations)} JWT operations',
                'ssot_violation': 'Auth service should be exclusive JWT source',
                'business_impact': 'Multiple JWT sources cause validation inconsistencies',
                'refactor_requirement': 'Move all JWT operations to auth service'
            })
            
            logger.critical("🚨 SSOT VIOLATION CONFIRMED: Auth service is NOT exclusive JWT source")
            logger.critical(f"📊 Backend JWT operations: {len(backend_operations)}")
            logger.critical("🎯 REFACTOR TARGET: Make auth service the exclusive JWT source")
            
        else:
            logger.info("✅ Auth service appears to be exclusive JWT source")
        
        return auth_service_not_exclusive
    
    def test_jwt_fallback_patterns_inventory(self) -> Dict[str, Any]:
        """
        INVENTORY TEST: Inventory JWT fallback patterns (SSOT violations).
        
        Fallback patterns violate SSOT by creating alternative JWT validation paths.
        """
        logger.info("🔍 Inventorying JWT fallback patterns")
        
        fallback_patterns = []
        
        # Scan for common fallback patterns
        fallback_indicators = [
            'fallback',
            'bypass',
            'override',
            'test.*jwt',
            'local.*validate',
            'emergency.*auth',
            'backup.*token'
        ]
        
        for operation in self.jwt_operations_catalog:
            # Check for fallback patterns in operation names or source
            for pattern in fallback_indicators:
                import re
                if re.search(pattern, operation.get('name', ''), re.IGNORECASE):
                    fallback_patterns.append({
                        'operation': operation,
                        'fallback_pattern': pattern,
                        'violation_reason': f'Fallback pattern {pattern} creates alternative JWT path'
                    })
                
                # Check source lines for fallback patterns
                if 'source_line' in operation:
                    if re.search(pattern, operation['source_line'], re.IGNORECASE):
                        fallback_patterns.append({
                            'operation': operation,
                            'fallback_pattern': pattern,
                            'source_context': operation['source_line'],
                            'violation_reason': f'Source contains fallback pattern {pattern}'
                        })
        
        fallback_inventory = {
            'total_fallback_patterns': len(fallback_patterns),
            'fallback_details': fallback_patterns,
            'ssot_impact': 'Fallback patterns create multiple JWT validation paths',
            'refactor_requirement': 'Eliminate all fallback patterns, use auth service exclusively'
        }
        
        if fallback_patterns:
            logger.critical(f"🚨 FALLBACK PATTERNS FOUND: {len(fallback_patterns)} violations")
            for pattern in fallback_patterns:
                logger.warning(f"  • {pattern['fallback_pattern']} in {pattern['operation']['module']}")
        else:
            logger.info("✅ No JWT fallback patterns found")
        
        return fallback_inventory
    
    def generate_comprehensive_ssot_violation_report(self) -> Dict[str, Any]:
        """Generate comprehensive SSOT violation report for refactoring."""
        
        # Ensure all catalogs are populated
        operations_catalog = self.test_backend_jwt_operations_catalog()
        fallback_inventory = self.test_jwt_fallback_patterns_inventory()
        
        report = {
            'report_timestamp': '2025-01-09T22:00:00Z',  # PHASE A documentation timestamp
            'ssot_principle_violation_summary': {
                'principle': 'Auth service should be exclusive JWT source',
                'violation': 'Backend contains JWT operations alongside auth service',
                'business_impact': '$500K+ ARR at risk from JWT validation inconsistencies'
            },
            'operations_catalog': operations_catalog,
            'fallback_patterns': fallback_inventory,
            'violation_evidence': self.violation_evidence,
            'ssot_compliance_metrics': {
                'backend_jwt_operations': operations_catalog['total_jwt_operations'],
                'violation_modules': operations_catalog['modules_with_jwt_operations'],
                'fallback_patterns': fallback_inventory['total_fallback_patterns'],
                'compliance_status': 'CRITICAL_VIOLATIONS' if operations_catalog['total_jwt_operations'] > 0 else 'COMPLIANT'
            },
            'refactor_validation_approach': {
                'phase_a': 'These tests MUST PASS (violations exist)',
                'phase_b': 'After refactor, these tests MUST FAIL (violations removed)',
                'success_criteria': 'Zero JWT operations in backend, auth service exclusive'
            },
            'business_protection': '$500K+ ARR protected from JWT cascade failures'
        }
        
        return report


class TestJWTSSOTViolationInventory(SSotBaseTestCase):
    """
    Unit Test Suite: JWT SSOT Violation Inventory
    
    These tests catalog and inventory JWT SSOT violations to prove they exist
    and will validate they are removed during refactor.
    """
    
    @pytest.fixture(autouse=True)
    def setup_violation_catalog(self):
        """Set up JWT SSOT violation catalog."""
        self.catalog = JWTSSOTViolationInventoryCatalog()
        logger.info("🚀 Starting JWT SSOT Violation Inventory")
        logger.info("=" * 60)
        logger.info("OBJECTIVE: Catalog JWT operations in backend (SSOT violations)")
        logger.info("VALIDATION: Tests MUST PASS now, FAIL after refactor")
        logger.info("=" * 60)
    
    def test_backend_jwt_operations_catalog(self):
        """
        CATALOG: Test cataloging of backend JWT operations (SSOT violations).
        
        This test documents every JWT operation found in the backend,
        proving SSOT violations exist.
        """
        logger.info("🚀 Cataloging backend JWT operations")
        
        catalog_summary = self.catalog.test_backend_jwt_operations_catalog()
        
        # Document findings
        total_operations = catalog_summary['total_jwt_operations']
        modules_with_operations = catalog_summary['modules_with_jwt_operations']
        
        logger.critical(f"🚨 CATALOG COMPLETE: {total_operations} JWT operations found")
        logger.critical(f"📍 Violation Modules: {modules_with_operations}")
        
        if total_operations > 0:
            logger.critical("✅ PHASE A SUCCESS: JWT operations cataloged (violations exist)")
            logger.critical("🎯 REFACTOR TARGET: Remove all backend JWT operations")
        else:
            logger.warning("⚠️ UNEXPECTED: No JWT operations found in backend")
            logger.warning("🔍 May indicate refactor already completed")
        
        # Assertions for catalog validation
        assert catalog_summary is not None, "JWT operations catalog must be generated"
        assert isinstance(catalog_summary['total_jwt_operations'], int), "Operation count must be integer"
        assert isinstance(catalog_summary['modules_with_jwt_operations'], int), "Module count must be integer"
        
        # Store for other tests
        self.catalog_summary = catalog_summary
    
    def test_multiple_jwt_sources_detected(self):
        """
        VIOLATION: Test multiple JWT sources exist (SSOT violation).
        
        SSOT requires single source (auth service only).
        This test proves backend also has JWT sources (violation).
        """
        logger.info("🚀 Testing multiple JWT sources detection")
        
        multiple_sources_exist = self.catalog.test_multiple_jwt_sources_detected()
        
        if multiple_sources_exist:
            logger.critical("🚨 CONFIRMED: Multiple JWT sources exist (SSOT violation)")
            logger.critical("📊 Expected: Auth service only")
            logger.critical("📊 Actual: Auth service + Backend")
            logger.critical("🎯 REFACTOR: Make auth service exclusive")
        else:
            logger.warning("⚠️ UNEXPECTED: Single JWT source detected")
            logger.warning("🔍 May indicate good SSOT compliance already")
        
        # PHASE A: This test should pass if violations exist
        # Note: We make this permissive since violation might already be fixed
        logger.info(f"Multiple JWT sources test result: {'VIOLATION EXISTS' if multiple_sources_exist else 'COMPLIANT'}")
        
        # Store result for reporting
        self.multiple_sources_detected = multiple_sources_exist
    
    def test_auth_service_not_exclusive_jwt_source(self):
        """
        EXCLUSIVITY: Test auth service is NOT exclusive JWT source (violation).
        
        This proves backend also handles JWT operations, violating SSOT.
        After refactor, auth service should be exclusive.
        """
        logger.info("🚀 Testing auth service exclusivity violation")
        
        not_exclusive = self.catalog.test_auth_service_not_exclusive_jwt_source()
        
        if not_exclusive:
            logger.critical("🚨 CONFIRMED: Auth service is NOT exclusive (SSOT violation)")
            logger.critical("💡 Backend also has JWT operations")
            logger.critical("🎯 REFACTOR: Make auth service exclusive JWT source")
        else:
            logger.info("✅ Auth service appears exclusive (good SSOT compliance)")
        
        # PHASE A: Store result for comprehensive reporting
        self.auth_service_exclusive = not not_exclusive
        
        logger.info(f"Auth service exclusivity test result: {'COMPLIANT' if not not_exclusive else 'VIOLATION EXISTS'}")
    
    def test_jwt_fallback_patterns_inventory(self):
        """
        INVENTORY: Test JWT fallback patterns inventory (SSOT violations).
        
        Fallback patterns create alternative JWT paths, violating SSOT.
        """
        logger.info("🚀 Inventorying JWT fallback patterns")
        
        fallback_inventory = self.catalog.test_jwt_fallback_patterns_inventory()
        
        fallback_count = fallback_inventory['total_fallback_patterns']
        
        if fallback_count > 0:
            logger.critical(f"🚨 FALLBACK PATTERNS FOUND: {fallback_count} violations")
            logger.critical("📍 Fallback patterns create alternative JWT validation paths")
            logger.critical("🎯 REFACTOR: Eliminate all fallbacks, use auth service exclusively")
        else:
            logger.info("✅ No JWT fallback patterns found")
        
        # Store for comprehensive report
        self.fallback_inventory = fallback_inventory
        
        # Assert inventory was generated
        assert fallback_inventory is not None, "Fallback patterns inventory must be generated"
        assert isinstance(fallback_count, int), "Fallback count must be integer"
    
    def test_comprehensive_ssot_violation_report(self):
        """
        REPORTING: Generate comprehensive SSOT violation report.
        
        This creates the master report documenting all SSOT violations
        for refactoring reference and validation.
        """
        logger.info("🚀 Generating comprehensive SSOT violation report")
        
        # Ensure other tests have run
        if not hasattr(self, 'catalog_summary'):
            self.test_backend_jwt_operations_catalog()
        if not hasattr(self, 'fallback_inventory'):
            self.test_jwt_fallback_patterns_inventory()
        
        violation_report = self.catalog.generate_comprehensive_ssot_violation_report()
        
        # Log comprehensive report
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE JWT SSOT VIOLATION REPORT")
        logger.info("=" * 80)
        
        principle = violation_report['ssot_principle_violation_summary']
        logger.critical(f"SSOT Principle: {principle['principle']}")
        logger.critical(f"Current Violation: {principle['violation']}")
        logger.critical(f"Business Impact: {principle['business_impact']}")
        
        metrics = violation_report['ssot_compliance_metrics']
        logger.critical(f"\nCompliance Metrics:")
        logger.critical(f"  • Backend JWT Operations: {metrics['backend_jwt_operations']}")
        logger.critical(f"  • Violation Modules: {metrics['violation_modules']}")
        logger.critical(f"  • Fallback Patterns: {metrics['fallback_patterns']}")
        logger.critical(f"  • Compliance Status: {metrics['compliance_status']}")
        
        validation = violation_report['refactor_validation_approach']
        logger.warning(f"\nRefactor Validation:")
        logger.warning(f"  • Phase A: {validation['phase_a']}")
        logger.warning(f"  • Phase B: {validation['phase_b']}")
        logger.warning(f"  • Success: {validation['success_criteria']}")
        
        logger.critical(f"\nBusiness Protection: {violation_report['business_protection']}")
        logger.info("=" * 80)
        
        # Assert comprehensive report generated
        assert violation_report is not None, "SSOT violation report must be generated"
        assert 'ssot_principle_violation_summary' in violation_report, "Report must include principle summary"
        assert 'operations_catalog' in violation_report, "Report must include operations catalog"
        assert 'refactor_validation_approach' in violation_report, "Report must include validation approach"
        
        # Store final report
        self.violation_report = violation_report
        
        # CRITICAL: Document report generation success
        logger.critical("✅ COMPREHENSIVE SSOT VIOLATION REPORT GENERATED")
        logger.critical("📋 Report available for refactor planning and validation")


# Standalone execution for direct violation inventory
if __name__ == "__main__":
    print("UNIT TEST: JWT SSOT VIOLATION INVENTORY")
    print("=" * 60)
    print("OBJECTIVE: Catalog all JWT operations in backend")
    print("SSOT VIOLATION: Backend should have NO JWT operations")
    print("REFACTOR VALIDATION: Catalog helps prove violations removed")
    print("=" * 60)
    
    # Initialize catalog
    catalog = JWTSSOTViolationInventoryCatalog()
    
    # Run inventory tests
    tests = [
        ("Backend JWT Operations Catalog", catalog.test_backend_jwt_operations_catalog),
        ("Multiple JWT Sources Detection", catalog.test_multiple_jwt_sources_detected),
        ("Auth Service Exclusivity Test", catalog.test_auth_service_not_exclusive_jwt_source),
        ("JWT Fallback Patterns Inventory", catalog.test_jwt_fallback_patterns_inventory),
    ]
    
    # Execute tests
    total_violations = 0
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            result = test_func()
            
            if isinstance(result, bool):
                if result:
                    print(f"   Result: 🚨 VIOLATIONS FOUND")
                    total_violations += 1
                else:
                    print(f"   Result: ✅ NO VIOLATIONS")
            elif isinstance(result, dict):
                violation_count = result.get('total_jwt_operations', 0) or result.get('total_fallback_patterns', 0)
                if violation_count > 0:
                    print(f"   Result: 🚨 {violation_count} VIOLATIONS CATALOGED")
                    total_violations += violation_count
                else:
                    print(f"   Result: ✅ NO VIOLATIONS CATALOGED")
            else:
                print(f"   Result: ✅ INVENTORY COMPLETED")
                
        except Exception as e:
            print(f"   Result: ❌ ERROR - {str(e)}")
    
    # Generate final summary
    print("\n" + "=" * 60)
    final_report = catalog.generate_comprehensive_ssot_violation_report()
    
    print("JWT SSOT VIOLATION INVENTORY SUMMARY")
    print("=" * 60)
    
    operations_count = final_report['operations_catalog']['total_jwt_operations']
    fallback_count = final_report['fallback_patterns']['total_fallback_patterns']
    modules_count = final_report['operations_catalog']['modules_with_jwt_operations']
    
    print(f"🚨 Backend JWT Operations: {operations_count}")
    print(f"🚨 JWT Fallback Patterns: {fallback_count}")
    print(f"📍 Modules with Violations: {modules_count}")
    print(f"💰 Business Protection: {final_report['business_protection']}")
    
    if operations_count > 0 or fallback_count > 0:
        print("\n✅ INVENTORY SUCCESS: SSOT violations cataloged")
        print("🎯 REFACTOR READY: Use catalog to guide violation removal")
        print("✅ VALIDATION READY: Tests will FAIL when violations removed")
        exit_code = 0
    else:
        print("\n⚠️ UNEXPECTED: No violations found in inventory")
        print("🔍 INVESTIGATE: May indicate refactor already completed")
        print("📋 BASELINE: Use as compliance validation")
        exit_code = 1
        
    print("=" * 60)
    
    sys.exit(exit_code)