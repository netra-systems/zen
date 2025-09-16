"""
Test Suite for Issue #1195: JWT Delegation SSOT Compliance Validation

Business Value Justification (BVJ):
- Segment: Platform/Security
- Business Goal: Ensure SSOT compliance for JWT operations
- Value Impact: Prevents JWT secret mismatches and auth inconsistencies
- Strategic Impact: Eliminates security vulnerabilities from competing JWT implementations

This test suite identifies and validates the removal of competing JWT implementations
that violate SSOT principles. All JWT operations must delegate to the auth service.

Target Violations for Issue #1195:
1. gcp_auth_context_middleware.py:106 - _decode_jwt_context() method (ACTUAL VIOLATION)
2. messages.py:72 - validate_and_decode_jwt() call (INVESTIGATION NEEDED)
3. user_context_extractor.py:149 - Claims delegation verification (INVESTIGATION NEEDED)

These tests will FAIL initially (proving violations exist) and PASS after remediation.
"""

import asyncio
import inspect
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock

from test_framework.base_integration_test import BaseIntegrationTest
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class JWTDelegationSSoTComplianceTests(BaseIntegrationTest):
    """
    Test suite to validate SSOT compliance for JWT operations.
    
    This suite identifies competing JWT implementations that violate the principle
    that ALL JWT operations must delegate to the auth service SSOT.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.violations_found = []
        
    @pytest.mark.ssot_compliance
    @pytest.mark.jwt_delegation
    async def test_gcp_auth_middleware_violates_jwt_ssot(self):
        """
        FAILING TEST: Proves GCP auth middleware violates JWT SSOT.
        
        This test identifies the _decode_jwt_context() method that performs
        local JWT decoding instead of delegating to auth service.
        
        EXPECTED: FAIL initially (proves violation exists)
        EXPECTED: PASS after remediation (violation removed)
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        # Instantiate the middleware
        middleware = GCPAuthContextMiddleware(None)
        
        # VIOLATION CHECK: Verify _decode_jwt_context method exists (should NOT exist after remediation)
        has_decode_method = hasattr(middleware, '_decode_jwt_context')
        
        if has_decode_method:
            # Get the method source code to analyze JWT operations
            decode_method = getattr(middleware, '_decode_jwt_context')
            source_code = inspect.getsource(decode_method)
            
            # Log the violation for Issue #1195 tracking
            logger.critical(
                f"🚨 ISSUE #1195 VIOLATION DETECTED: "
                f"GCPAuthContextMiddleware._decode_jwt_context() method exists and performs local JWT operations. "
                f"This violates SSOT principles - ALL JWT operations must delegate to auth service."
            )
            
            # Document the violation details
            violation_details = {
                "file": "netra_backend/app/middleware/gcp_auth_context_middleware.py",
                "method": "_decode_jwt_context",
                "line_reference": "~106",
                "violation_type": "local_jwt_decoding", 
                "ssot_requirement": "All JWT operations must delegate to auth service",
                "source_snippet": source_code[:200] + "..." if len(source_code) > 200 else source_code
            }
            
            self.violations_found.append(violation_details)
            
            # FAILING ASSERTION: This will fail until the violation is fixed
            pytest.fail(
                f"ISSUE #1195 JWT SSOT VIOLATION: GCPAuthContextMiddleware contains _decode_jwt_context() method "
                f"that performs local JWT decoding. This method must be removed and JWT operations "
                f"must delegate to auth service. Violation details: {violation_details}"
            )
        
        # SUCCESS CASE: Method doesn't exist (SSOT compliant)
        logger.info(
            "✅ ISSUE #1195 COMPLIANCE: GCPAuthContextMiddleware._decode_jwt_context() method not found - SSOT compliant"
        )

    @pytest.mark.ssot_compliance
    @pytest.mark.jwt_delegation
    async def test_messages_route_jwt_delegation_compliance(self):
        """
        INVESTIGATION TEST: Verify messages route JWT operations delegate to auth service.
        
        Investigates whether the validate_and_decode_jwt() call in messages.py:72
        properly delegates to auth service or performs local JWT operations.
        
        EXPECTED: May pass (if properly delegating) or fail (if violating)
        """
        from netra_backend.app.routes.messages import get_current_user_from_jwt
        from netra_backend.app.websocket_core.user_context_extractor import get_user_context_extractor
        
        # Get the user context extractor used by messages route
        extractor = get_user_context_extractor()
        
        # Verify the validate_and_decode_jwt method delegates to auth service
        validate_method = getattr(extractor, 'validate_and_decode_jwt', None)
        
        if validate_method is None:
            pytest.fail(
                "ISSUE #1195 INVESTIGATION: validate_and_decode_jwt method not found in user context extractor"
            )
            
        # Analyze the method source code for auth service delegation
        source_code = inspect.getsource(validate_method)
        
        # Check for SSOT compliance indicators
        has_auth_service_delegation = any([
            "auth_service" in source_code.lower(),
            "auth_client" in source_code.lower(), 
            ".validate_token(" in source_code,
            "delegation" in source_code.lower()
        ])
        
        # Check for SSOT violation indicators  
        has_local_jwt_operations = any([
            "jwt.decode(" in source_code,
            "decode(" in source_code and "jwt" in source_code.lower(),
            "secret" in source_code.lower() and "jwt" in source_code.lower(),
            "PyJWT" in source_code,
            "jose" in source_code.lower()
        ])
        
        # Document the analysis
        analysis_result = {
            "file": "netra_backend/app/routes/messages.py",
            "method_location": "get_current_user_from_jwt -> extractor.validate_and_decode_jwt",
            "line_reference": "~72",
            "has_auth_service_delegation": has_auth_service_delegation,
            "has_local_jwt_operations": has_local_jwt_operations,
            "source_snippet": source_code[:300] + "..." if len(source_code) > 300 else source_code
        }
        
        logger.info(f"📊 ISSUE #1195 ANALYSIS: Messages route JWT delegation analysis: {analysis_result}")
        
        if has_local_jwt_operations and not has_auth_service_delegation:
            # VIOLATION: Local JWT operations without auth service delegation
            violation_details = {
                **analysis_result,
                "violation_type": "local_jwt_operations_without_delegation",
                "ssot_requirement": "JWT validation must delegate to auth service"
            }
            
            self.violations_found.append(violation_details)
            
            pytest.fail(
                f"ISSUE #1195 JWT SSOT VIOLATION: Messages route JWT validation performs local operations "
                f"without proper auth service delegation. Details: {violation_details}"
            )
        elif not has_auth_service_delegation:
            # WARNING: Unclear delegation pattern
            logger.warning(
                f"⚠️ ISSUE #1195 WARNING: Messages route JWT validation delegation pattern unclear. "
                f"Manual verification recommended. Analysis: {analysis_result}"
            )
        else:
            # SUCCESS: Proper delegation detected
            logger.info(
                f"✅ ISSUE #1195 COMPLIANCE: Messages route JWT validation appears to delegate to auth service properly"
            )

    @pytest.mark.ssot_compliance
    @pytest.mark.jwt_delegation
    async def test_websocket_context_extractor_delegation_compliance(self):
        """
        INVESTIGATION TEST: Verify WebSocket context extractor JWT operations delegate to auth service.
        
        Investigates the validate_and_decode_jwt() method in user_context_extractor.py:149
        to ensure it properly delegates to auth service without local JWT operations.
        
        EXPECTED: Should pass (already shows delegation in source code analysis)
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        # Instantiate the extractor
        extractor = UserContextExtractor()
        
        # Verify the validate_and_decode_jwt method exists and delegates properly
        validate_method = getattr(extractor, 'validate_and_decode_jwt', None)
        
        if validate_method is None:
            pytest.fail(
                "ISSUE #1195 INVESTIGATION: validate_and_decode_jwt method not found in UserContextExtractor"
            )
        
        # Analyze the method source code for SSOT compliance
        source_code = inspect.getsource(validate_method)
        
        # Check for explicit auth service delegation patterns
        auth_service_patterns = [
            "self.auth_service.validate_token",
            "auth_client.validate_token", 
            "SSOT COMPLIANCE: Pure delegation",
            "auth service client",
            "validation_result = await self.auth_service"
        ]
        
        # Check for SSOT violation patterns
        local_jwt_patterns = [
            "jwt.decode(",
            "decode_token_locally",
            "PyJWT.decode",
            "fallback.*jwt",
            "local.*validation"
        ]
        
        has_explicit_delegation = any(pattern.lower() in source_code.lower() for pattern in auth_service_patterns)
        has_local_operations = any(pattern.lower() in source_code.lower() for pattern in local_jwt_patterns)
        
        # Document the analysis
        analysis_result = {
            "file": "netra_backend/app/websocket_core/user_context_extractor.py", 
            "method": "validate_and_decode_jwt",
            "line_reference": "~149",
            "has_explicit_delegation": has_explicit_delegation,
            "has_local_operations": has_local_operations,
            "auth_service_patterns_found": [p for p in auth_service_patterns if p.lower() in source_code.lower()],
            "local_patterns_found": [p for p in local_jwt_patterns if p.lower() in source_code.lower()],
            "source_snippet": source_code[:400] + "..." if len(source_code) > 400 else source_code
        }
        
        logger.info(f"📊 ISSUE #1195 ANALYSIS: WebSocket context extractor analysis: {analysis_result}")
        
        if has_local_operations:
            # VIOLATION: Contains local JWT operations
            violation_details = {
                **analysis_result,
                "violation_type": "local_jwt_operations_present",
                "ssot_requirement": "No local JWT operations - pure delegation only"
            }
            
            self.violations_found.append(violation_details)
            
            pytest.fail(
                f"ISSUE #1195 JWT SSOT VIOLATION: WebSocket context extractor contains local JWT operations. "
                f"Details: {violation_details}"
            )
        elif not has_explicit_delegation:
            # WARNING: Delegation not clearly visible 
            logger.warning(
                f"⚠️ ISSUE #1195 WARNING: WebSocket context extractor delegation patterns not clearly visible. "
                f"Manual verification recommended. Analysis: {analysis_result}"
            )
        else:
            # SUCCESS: Explicit delegation found, no local operations
            logger.info(
                f"✅ ISSUE #1195 COMPLIANCE: WebSocket context extractor shows explicit auth service delegation"
            )

    @pytest.mark.ssot_compliance
    @pytest.mark.jwt_delegation
    async def test_no_jwt_secrets_in_backend_configuration(self):
        """
        SSOT COMPLIANCE TEST: Verify backend doesn't manage JWT secrets directly.
        
        Validates that JWT secret management is properly centralized and backend
        services don't contain JWT secret handling logic.
        
        EXPECTED: PASS (JWT secrets should be managed centrally)
        """
        try:
            # Check if backend tries to access JWT secrets directly
            from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretsConfig
            
            secrets_config = UnifiedSecretsConfig()
            
            # Get all available methods to check for JWT secret management
            config_methods = [method for method in dir(secrets_config) if not method.startswith('_')]
            jwt_related_methods = [method for method in config_methods if 'jwt' in method.lower()]
            
            if jwt_related_methods:
                # VIOLATION: Backend managing JWT secrets directly
                violation_details = {
                    "file": "netra_backend/app/core/configuration/unified_secrets.py",
                    "violation_type": "backend_jwt_secret_management",
                    "jwt_methods_found": jwt_related_methods,
                    "ssot_requirement": "JWT secrets must be managed only by auth service"
                }
                
                self.violations_found.append(violation_details)
                
                logger.critical(
                    f"🚨 ISSUE #1195 VIOLATION: Backend contains JWT secret management methods: {jwt_related_methods}. "
                    f"JWT secrets must be managed exclusively by auth service."
                )
                
                pytest.fail(
                    f"ISSUE #1195 JWT SSOT VIOLATION: Backend manages JWT secrets directly. "
                    f"Methods found: {jwt_related_methods}. JWT secrets must be auth service exclusive."
                )
            else:
                logger.info("✅ ISSUE #1195 COMPLIANCE: Backend does not manage JWT secrets directly")
                
        except ImportError as e:
            # Expected: Backend shouldn't have JWT secret management
            logger.info(f"✅ ISSUE #1195 COMPLIANCE: Backend JWT secret management not found (ImportError: {e})")

    @pytest.mark.ssot_compliance 
    @pytest.mark.jwt_delegation
    async def test_auth_service_is_single_source_of_truth(self):
        """
        SSOT VALIDATION TEST: Verify auth service is the single source of truth for JWT operations.
        
        Validates that the auth service properly implements JWT operations and
        other services delegate to it correctly.
        
        EXPECTED: PASS (auth service should be properly configured as SSOT)
        """
        try:
            # Verify auth service JWT capabilities
            from netra_backend.app.clients.auth_client_core import auth_client
            
            # Check auth client methods for proper delegation patterns
            auth_methods = [method for method in dir(auth_client) if not method.startswith('_')]
            jwt_delegation_methods = [
                method for method in auth_methods 
                if any(pattern in method.lower() for pattern in ['validate', 'token', 'jwt', 'auth'])
            ]
            
            # Verify essential JWT delegation methods exist
            essential_methods = ['validate_token']
            missing_methods = [method for method in essential_methods if not hasattr(auth_client, method)]
            
            if missing_methods:
                pytest.fail(
                    f"ISSUE #1195 AUTH SERVICE INCOMPLETE: Auth client missing essential JWT delegation methods: "
                    f"{missing_methods}. Auth service must provide complete JWT operations."
                )
            
            # Check that auth client properly delegates (doesn't perform local operations)
            if hasattr(auth_client, 'validate_token'):
                validate_method = getattr(auth_client, 'validate_token')
                if asyncio.iscoroutinefunction(validate_method):
                    # Good: Async method suggests network call to auth service
                    logger.info("✅ ISSUE #1195 COMPLIANCE: Auth client validate_token is async (suggests service delegation)")
                else:
                    logger.warning("⚠️ ISSUE #1195 WARNING: Auth client validate_token is sync (may indicate local operations)")
            
            analysis_result = {
                "auth_client_available": True,
                "jwt_delegation_methods": jwt_delegation_methods,
                "essential_methods_present": [method for method in essential_methods if hasattr(auth_client, method)],
                "missing_essential_methods": missing_methods
            }
            
            logger.info(f"📊 ISSUE #1195 ANALYSIS: Auth service SSOT analysis: {analysis_result}")
            
            if not missing_methods:
                logger.info("✅ ISSUE #1195 COMPLIANCE: Auth service provides complete JWT delegation interface")
            
        except ImportError as e:
            pytest.fail(
                f"ISSUE #1195 AUTH SERVICE UNAVAILABLE: Cannot import auth client: {e}. "
                f"Auth service must be available for JWT delegation."
            )

    @pytest.mark.ssot_compliance
    @pytest.mark.jwt_delegation
    async def test_no_direct_jwt_library_imports_in_backend(self):
        """
        SSOT COMPLIANCE TEST: Verify backend doesn't import JWT libraries directly.
        
        Validates that backend services don't import JWT libraries like PyJWT
        directly, ensuring all JWT operations go through auth service delegation.
        
        EXPECTED: FAIL initially if direct imports exist, PASS after remediation
        """
        import sys
        import importlib.util
        from pathlib import Path
        
        # Define JWT library patterns to check for
        jwt_library_patterns = [
            'jwt',
            'PyJWT', 
            'python-jose',
            'authlib',
            'cryptography.jwt'
        ]
        
        # Get all Python files in the backend
        backend_path = Path("/Users/anthony/Desktop/netra-apex/netra_backend")
        python_files = list(backend_path.rglob("*.py"))
        
        violations = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for direct JWT library imports
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Skip comments
                    if line_stripped.startswith('#'):
                        continue
                        
                    # Check for import statements with JWT libraries
                    for jwt_lib in jwt_library_patterns:
                        if any([
                            f"import {jwt_lib}" in line_stripped,
                            f"from {jwt_lib}" in line_stripped,
                            f"import {jwt_lib}." in line_stripped,
                            f"from {jwt_lib}." in line_stripped
                        ]):
                            violation = {
                                "file": str(py_file.relative_to(backend_path.parent)),
                                "line_number": line_num,
                                "line_content": line_stripped,
                                "jwt_library": jwt_lib,
                                "violation_type": "direct_jwt_library_import"
                            }
                            violations.append(violation)
                            
            except Exception as e:
                logger.warning(f"Could not analyze file {py_file}: {e}")
                continue
        
        if violations:
            # VIOLATION: Direct JWT library imports found
            logger.critical(
                f"🚨 ISSUE #1195 VIOLATIONS: Found {len(violations)} direct JWT library imports in backend. "
                f"All JWT operations must delegate to auth service."
            )
            
            for violation in violations:
                logger.error(f"JWT IMPORT VIOLATION: {violation}")
                self.violations_found.append(violation)
                
            pytest.fail(
                f"ISSUE #1195 JWT SSOT VIOLATIONS: Found {len(violations)} direct JWT library imports. "
                f"Backend must not import JWT libraries directly. Violations: {violations}"
            )
        else:
            logger.info("✅ ISSUE #1195 COMPLIANCE: No direct JWT library imports found in backend")

    def teardown_method(self):
        """Teardown for each test method."""
        if self.violations_found:
            logger.critical(
                f"🚨 ISSUE #1195 SUMMARY: Found {len(self.violations_found)} JWT SSOT violations. "
                f"All violations must be remediated before Issue #1195 can be considered complete."
            )
            
            # Generate detailed violation report
            violation_summary = {
                "total_violations": len(self.violations_found),
                "violation_types": list(set(v.get("violation_type", "unknown") for v in self.violations_found)),
                "files_affected": list(set(v.get("file", "unknown") for v in self.violations_found)),
                "violations": self.violations_found
            }
            
            logger.error(f"ISSUE #1195 VIOLATION REPORT: {violation_summary}")
        
        super().teardown_method()


if __name__ == "__main__":
    # Allow running this test file directly for Issue #1195 validation
    pytest.main([__file__, "-v", "--tb=short"])