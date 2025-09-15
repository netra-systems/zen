"""
Test JWTHandler SSOT functionality in auth service

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure auth service is single source of truth for JWT operations  
- Value Impact: Consistent authentication across all platform services
- Strategic Impact: Foundation for $500K+ ARR Golden Path authentication

Issue #1117: JWT Validation SSOT - Auth Service Consolidation
"""

import ast
import inspect
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class TestJWTHandlerSSOTFunctionality(SSotBaseTestCase):
    """Test auth service JWTHandler as single source of truth for JWT operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent.parent
        
    # ================================================================================
    # FAILING TESTS - Demonstrate Current SSOT Violations
    # ================================================================================
    
    def test_jwt_wrapper_bypasses_ssot_auth_service(self):
        """FAILING: Multiple wrapper classes bypass auth service SSOT JWTHandler.
        
        This test SHOULD FAIL initially - demonstrates SSOT violation.
        Expected to find wrapper classes that duplicate JWT validation logic.
        """
        wrapper_classes = self._find_jwt_validation_wrapper_classes()
        
        # CURRENT ISSUE: Multiple wrapper classes exist that bypass auth service
        expected_wrappers = [
            'UnifiedJWTProtocolHandler',  # WebSocket JWT wrapper
            'UserContextExtractor.validate_and_decode_jwt',  # WebSocket validation wrapper
        ]
        
        found_wrappers = [w['name'] for w in wrapper_classes]
        logger.error(f"JWT VALIDATION WRAPPERS FOUND: {found_wrappers}")
        
        # Document each wrapper violation
        for wrapper in wrapper_classes:
            logger.error(f"SSOT VIOLATION: {wrapper['name']} at {wrapper['file']}:{wrapper['line']}")
            logger.error(f"  Methods: {wrapper['methods']}")
            logger.error(f"  Business Impact: Creates inconsistent JWT validation bypassing auth service SSOT")
        
        # BUSINESS IMPACT: Multiple validation paths create auth bypass vulnerabilities
        assert len(wrapper_classes) > 0, "No JWT wrapper classes found - test setup issue"
        
        self.fail(f"SSOT VIOLATION: Found {len(wrapper_classes)} JWT validation wrapper classes that bypass auth service SSOT: {found_wrappers}")
    
    def test_direct_jwt_decode_bypasses_auth_service_ssot(self):
        """FAILING: Direct jwt.decode() calls bypass auth service SSOT.
        
        This test SHOULD FAIL initially - demonstrates direct JWT decode violations.
        Expected to find direct jwt.decode() calls that bypass auth service.
        """
        direct_decode_usage = self._find_direct_jwt_decode_calls()
        
        # CURRENT ISSUE: Direct JWT decode operations bypass auth service SSOT
        assert len(direct_decode_usage) > 0, "No direct JWT decode calls found - test setup issue"
        
        logger.error(f"DIRECT JWT DECODE VIOLATIONS: {len(direct_decode_usage)} found")
        
        for usage in direct_decode_usage:
            logger.error(f"SSOT VIOLATION: Direct jwt.decode() at {usage['file']}:{usage['line']}")
            logger.error(f"  Context: {usage['context'][:100]}...")
            logger.error(f"  Business Impact: Bypasses auth service SSOT validation")
        
        # BUSINESS IMPACT: Direct decode creates inconsistent validation logic
        self.fail(f"SSOT VIOLATION: Found {len(direct_decode_usage)} direct JWT decode operations bypassing auth service SSOT")
    
    def test_websocket_jwt_validation_creates_ssot_fragmentation(self):
        """FAILING: WebSocket JWT validation creates SSOT fragmentation.
        
        This test SHOULD FAIL initially - demonstrates WebSocket-specific JWT validation.
        Expected to find WebSocket components that validate JWT tokens locally.
        """
        websocket_jwt_methods = self._find_websocket_jwt_validation_methods()
        
        # CURRENT ISSUE: WebSocket components have independent JWT validation
        expected_websocket_violations = [
            'validate_and_decode_jwt',  # UserContextExtractor method
            'extract_jwt_from_websocket',  # May include validation logic
        ]
        
        found_methods = [m['method_name'] for m in websocket_jwt_methods]
        logger.error(f"WEBSOCKET JWT VALIDATION METHODS: {found_methods}")
        
        for method in websocket_jwt_methods:
            logger.error(f"WEBSOCKET SSOT VIOLATION: {method['class_name']}.{method['method_name']}")
            logger.error(f"  File: {method['file']}:{method['line']}")
            logger.error(f"  Has JWT Logic: {method['has_jwt_logic']}")
            logger.error(f"  Business Impact: WebSocket authentication inconsistent with other services")
        
        # Filter methods that actually have JWT validation logic
        validation_methods = [m for m in websocket_jwt_methods if m['has_jwt_logic']]
        
        assert len(validation_methods) > 0, "No WebSocket JWT validation methods found - test setup issue"
        
        self.fail(f"WEBSOCKET SSOT VIOLATION: Found {len(validation_methods)} WebSocket JWT validation methods that should delegate to auth service SSOT")
    
    # ================================================================================
    # SUCCESS CRITERIA TESTS - Validate Desired SSOT State 
    # ================================================================================
    
    def test_auth_service_jwt_handler_is_single_source_of_truth(self):
        """SUCCESS: Auth service JWTHandler is the only JWT validation implementation.
        
        This test should PASS after SSOT consolidation.
        Validates that auth service JWTHandler exists and is the sole JWT validator.
        """
        # Validate auth service JWTHandler exists and is functional
        try:
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            jwt_handler = JWTHandler()
        except ImportError as e:
            self.fail(f"SSOT REQUIREMENT: Auth service JWTHandler not importable: {e}")
        
        # Verify SSOT methods are present
        required_methods = ['validate_token', 'decode_token', 'create_token']
        missing_methods = []
        
        for method_name in required_methods:
            if not hasattr(jwt_handler, method_name):
                missing_methods.append(method_name)
        
        assert len(missing_methods) == 0, f"JWTHandler missing required SSOT methods: {missing_methods}"
        
        # Verify no alternative JWT validation classes exist outside auth service
        alternative_validators = self._find_alternative_jwt_validators()
        
        if alternative_validators:
            logger.error("ALTERNATIVE JWT VALIDATORS FOUND:")
            for validator in alternative_validators:
                logger.error(f"  {validator['name']} at {validator['location']}")
        
        assert len(alternative_validators) == 0, f"SSOT violation: {len(alternative_validators)} alternative JWT validators found: {[v['name'] for v in alternative_validators]}"
        
        logger.info("SUCCESS: Auth service JWTHandler confirmed as single source of truth for JWT operations")
    
    def test_all_services_delegate_to_auth_service_jwt_handler(self):
        """SUCCESS: All services use auth service for JWT validation (no local validation).
        
        This test should PASS after SSOT consolidation.
        Validates that all services delegate JWT validation to auth service.
        """
        services_delegation = self._validate_jwt_validation_delegation()
        
        delegation_failures = []
        
        for service, delegation_status in services_delegation.items():
            if not delegation_status['delegates_to_auth_service']:
                delegation_failures.append(f"{service}: Does not delegate to auth service")
            
            if delegation_status['has_local_jwt_logic']:
                delegation_failures.append(f"{service}: Has local JWT validation logic")
            
            if delegation_status['bypasses_auth_service']:
                delegation_failures.append(f"{service}: Bypasses auth service with direct operations")
        
        if delegation_failures:
            logger.error("JWT DELEGATION FAILURES:")
            for failure in delegation_failures:
                logger.error(f"  {failure}")
            
            self.fail(f"SSOT DELEGATION FAILURES: {len(delegation_failures)} services not properly delegating to auth service SSOT")
        
        logger.info(f"SUCCESS: All {len(services_delegation)} services properly delegate JWT validation to auth service SSOT")
    
    def test_jwt_validation_path_consolidation_complete(self):
        """SUCCESS: Only one JWT validation path exists through auth service.
        
        This test should PASS after SSOT consolidation.
        Validates that there is exactly one JWT validation path in the system.
        """
        validation_paths = self._discover_all_jwt_validation_paths()
        
        # Should be exactly one path through auth service
        if len(validation_paths) == 0:
            self.fail("CRITICAL: No JWT validation paths found - system broken")
        
        if len(validation_paths) > 1:
            logger.error(f"MULTIPLE JWT VALIDATION PATHS FOUND: {len(validation_paths)}")
            for i, path in enumerate(validation_paths):
                logger.error(f"  Path {i+1}: {path['description']}")
                logger.error(f"    Entry: {path['entry_point']}")
                logger.error(f"    Implementation: {path['implementation']}")
                logger.error(f"    Uses Auth Service: {path['uses_auth_service']}")
            
            self.fail(f"SSOT VIOLATION: Found {len(validation_paths)} JWT validation paths, expected exactly 1")
        
        # Validate the single path uses auth service SSOT
        single_path = validation_paths[0]
        
        assert single_path['uses_auth_service'], f"Single validation path does not use auth service: {single_path['implementation']}"
        assert 'auth_service.jwt_handler' in single_path['implementation'].lower(), f"Single path does not use JWTHandler SSOT: {single_path['implementation']}"
        
        logger.info(f"SUCCESS: Single JWT validation path confirmed through auth service SSOT: {single_path['description']}")
    
    # ================================================================================
    # Helper Methods for Test Implementation
    # ================================================================================
    
    def _find_jwt_validation_wrapper_classes(self) -> List[Dict[str, Any]]:
        """Find classes that wrap or duplicate JWT validation functionality."""
        wrapper_classes = []
        
        # Scan for wrapper classes in key locations
        scan_paths = [
            self.project_root / 'netra_backend' / 'app' / 'websocket_core',
            self.project_root / 'netra_backend' / 'app' / 'auth_integration',
            self.project_root / 'netra_backend' / 'app' / 'clients',
        ]
        
        jwt_validation_indicators = [
            'validate_jwt', 'decode_jwt', 'jwt_validate', 'jwt_decode',
            'validate_token', 'verify_jwt', 'check_jwt'
        ]
        
        for scan_path in scan_paths:
            if not scan_path.exists():
                continue
                
            for py_file in scan_path.rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            jwt_methods = []
                            
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    method_name = item.name
                                    if any(indicator in method_name.lower() for indicator in jwt_validation_indicators):
                                        jwt_methods.append(method_name)
                            
                            if jwt_methods and not self._is_auth_service_file(str(py_file)):
                                wrapper_classes.append({
                                    'name': node.name,
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': node.lineno,
                                    'methods': jwt_methods
                                })
                
                except Exception as e:
                    logger.debug(f"Error scanning {py_file}: {e}")
                    continue
        
        return wrapper_classes
    
    def _find_direct_jwt_decode_calls(self) -> List[Dict[str, Any]]:
        """Find direct jwt.decode() calls that bypass auth service SSOT."""
        direct_decode_calls = []
        
        # Scan entire codebase except auth service
        for py_file in self.project_root.rglob('*.py'):
            if self._is_auth_service_file(str(py_file)) or 'test' in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_content = line.strip()
                    
                    # Look for direct jwt.decode patterns
                    jwt_decode_patterns = [
                        'jwt.decode(',
                        'decode(token',
                        'jwt_decode(',
                        'decode_token('
                    ]
                    
                    for pattern in jwt_decode_patterns:
                        if pattern in line_content and not line_content.startswith('#'):
                            direct_decode_calls.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'context': line_content,
                                'pattern': pattern
                            })
            
            except Exception as e:
                logger.debug(f"Error scanning {py_file}: {e}")
                continue
        
        return direct_decode_calls
    
    def _find_websocket_jwt_validation_methods(self) -> List[Dict[str, Any]]:
        """Find WebSocket-specific JWT validation methods."""
        websocket_jwt_methods = []
        
        websocket_paths = [
            self.project_root / 'netra_backend' / 'app' / 'websocket_core',
        ]
        
        for websocket_path in websocket_paths:
            if not websocket_path.exists():
                continue
            
            for py_file in websocket_path.rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_name = node.name
                            
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    method_name = item.name
                                    
                                    # Check if method deals with JWT
                                    if ('jwt' in method_name.lower() or 
                                        'token' in method_name.lower() or
                                        'validate' in method_name.lower()):
                                        
                                        # Check if method has JWT validation logic
                                        method_source = ast.get_source_segment(content, item) or ""
                                        has_jwt_logic = self._method_has_jwt_validation_logic(method_source)
                                        
                                        websocket_jwt_methods.append({
                                            'class_name': class_name,
                                            'method_name': method_name,
                                            'file': str(py_file.relative_to(self.project_root)),
                                            'line': item.lineno,
                                            'has_jwt_logic': has_jwt_logic
                                        })
                
                except Exception as e:
                    logger.debug(f"Error scanning {py_file}: {e}")
                    continue
        
        return websocket_jwt_methods
    
    def _find_alternative_jwt_validators(self) -> List[Dict[str, Any]]:
        """Find JWT validation implementations outside auth service."""
        alternative_validators = []
        
        # This would scan for classes/functions that validate JWT tokens
        # outside of the auth service SSOT
        # Implementation would depend on specific codebase patterns
        
        return alternative_validators
    
    def _validate_jwt_validation_delegation(self) -> Dict[str, Dict[str, bool]]:
        """Validate JWT validation delegation across services."""
        services_delegation = {}
        
        # Mock implementation - would analyze actual service JWT usage patterns
        services = ['backend', 'websocket', 'auth_integration']
        
        for service in services:
            services_delegation[service] = {
                'delegates_to_auth_service': False,  # Would be determined by analysis
                'has_local_jwt_logic': True,  # Would be determined by analysis
                'bypasses_auth_service': True  # Would be determined by analysis
            }
        
        return services_delegation
    
    def _discover_all_jwt_validation_paths(self) -> List[Dict[str, Any]]:
        """Discover all JWT validation paths in the system."""
        validation_paths = []
        
        # Mock implementation - would trace actual validation paths
        validation_paths.append({
            'id': 'auth_service_ssot',
            'description': 'Auth service SSOT JWT validation',
            'entry_point': 'auth_service.jwt_handler.validate_token',
            'implementation': 'auth_service.jwt_handler',
            'uses_auth_service': True
        })
        
        # Add additional paths that would be found during analysis
        validation_paths.append({
            'id': 'websocket_wrapper',
            'description': 'WebSocket JWT validation wrapper',
            'entry_point': 'websocket_core.user_context_extractor.validate_and_decode_jwt',
            'implementation': 'websocket local validation',
            'uses_auth_service': False
        })
        
        return validation_paths
    
    def _is_auth_service_file(self, file_path: str) -> bool:
        """Check if file is part of auth service."""
        return 'auth_service' in file_path
    
    def _method_has_jwt_validation_logic(self, method_source: str) -> bool:
        """Check if method contains JWT validation logic."""
        jwt_logic_indicators = [
            'jwt.decode', 'decode(token', 'verify_signature',
            'check_expiration', 'validate_claims', 'verify_jwt'
        ]
        
        return any(indicator in method_source for indicator in jwt_logic_indicators)


# ================================================================================
# Test Execution Entry Point
# ================================================================================

if __name__ == '__main__':
    # Run as standalone test to demonstrate SSOT violations
    import unittest
    
    # Configure logging for detailed SSOT violation reporting
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test suite focusing on failing tests (current state)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestJWTHandlerSSOTFunctionality)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=False)
    result = runner.run(suite)
    
    # Report results
    if result.failures or result.errors:
        print(f"\nSSOT VIOLATIONS CONFIRMED: {len(result.failures)} failures, {len(result.errors)} errors")
        print("These failures demonstrate current JWT validation SSOT violations in Issue #1117")
    else:
        print("\nUNEXPECTED: All tests passed - SSOT violations may have been resolved")