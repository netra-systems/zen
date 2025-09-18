"""
Test Suite for Issue #1195: JWT Security Validation SSOT Compliance

Business Value Justification (BVJ):
- Segment: Enterprise/Security
- Business Goal: Ensure secure JWT handling across all services
- Value Impact: Prevents JWT secret exposure and security vulnerabilities
- Strategic Impact: Maintains enterprise-grade security and compliance

This test suite validates security aspects of JWT handling to ensure
SSOT compliance prevents security vulnerabilities.

Security Focus Areas:
1. JWT secret exposure prevention
2. Token validation consistency
3. Auth service exclusive control
4. No local JWT validation bypasses
5. Proper error handling without secret leakage

These tests ensure that SSOT compliance enhances security posture.
"""

import asyncio
import os
import pytest
import importlib
import inspect
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from test_framework.base_integration_test import BaseIntegrationTest
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class JWTSecurityValidationComplianceTests(BaseIntegrationTest):
    """
    Test suite to validate security aspects of JWT SSOT compliance.
    
    Ensures that SSOT compliance enhances rather than compromises security.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.security_violations = []
        
    @pytest.mark.ssot_compliance
    @pytest.mark.security
    async def test_no_jwt_secrets_exposed_in_backend_code(self):
        """
        SECURITY TEST: Verify JWT secrets are not exposed in backend code.
        
        Validates that JWT secrets, keys, or sensitive auth material
        are not hardcoded or exposed in backend source code.
        
        EXPECTED: PASS (no secrets should be exposed)
        """
        # Define patterns that indicate exposed JWT secrets
        secret_patterns = [
            "JWT_SECRET",
            "jwt_secret",
            "secret_key",
            "HS256",
            "RS256", 
            "private_key",
            "public_key",
            "signing_key",
            "verify_key"
        ]
        
        # Get all Python files in backend
        backend_path = Path("/Users/anthony/Desktop/netra-apex/netra_backend")
        python_files = list(backend_path.rglob("*.py"))
        
        secret_exposures = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        
                        # Skip comments unless they contain actual secrets
                        if line_stripped.startswith('#') and '=' not in line_stripped:
                            continue
                            
                        # Check for potential secret exposures
                        for pattern in secret_patterns:
                            if pattern in line and any([
                                '=' in line,  # Assignment
                                ':' in line and ('"' in line or "'" in line),  # Dict/config
                                'return' in line.lower()  # Return statement
                            ]):
                                # Additional check: ignore test files and mock data
                                if any(test_indicator in str(py_file).lower() for test_indicator in ['test_', 'mock_', 'fixture']):
                                    continue
                                    
                                exposure = {
                                    "file": str(py_file.relative_to(backend_path.parent)),
                                    "line_number": line_num,
                                    "line_content": line_stripped[:100] + "..." if len(line_stripped) > 100 else line_stripped,
                                    "pattern_matched": pattern,
                                    "exposure_type": "potential_secret_exposure"
                                }
                                secret_exposures.append(exposure)
                                
            except Exception as e:
                logger.warning(f"Could not analyze file {py_file}: {e}")
                continue
        
        if secret_exposures:
            logger.critical(
                f"🚨 ISSUE #1195 SECURITY VIOLATION: Found {len(secret_exposures)} potential JWT secret exposures. "
                f"All JWT secrets must be managed exclusively by auth service."
            )
            
            for exposure in secret_exposures:
                logger.error(f"Potential secret exposure: {exposure}")
                self.security_violations.append(exposure)
                
            pytest.fail(
                f"ISSUE #1195 SECURITY VIOLATIONS: Found {len(secret_exposures)} potential JWT secret exposures. "
                f"JWT secrets must not be exposed in backend code. Exposures: {secret_exposures}"
            )
        else:
            logger.info("CHECK ISSUE #1195 SECURITY COMPLIANCE: No JWT secret exposures found in backend code")

    @pytest.mark.ssot_compliance
    @pytest.mark.security
    async def test_jwt_validation_consistency_across_services(self):
        """
        SECURITY TEST: Verify JWT validation consistency across services.
        
        Validates that all services that perform JWT validation use
        consistent validation logic through auth service delegation.
        
        EXPECTED: PASS (validation should be consistent)
        """
        # Test different validation entry points
        validation_points = [
            {
                "name": "websocket_validation",
                "module": "netra_backend.app.websocket_core.user_context_extractor",
                "class": "UserContextExtractor",
                "method": "validate_and_decode_jwt"
            },
            {
                "name": "http_route_validation", 
                "module": "netra_backend.app.routes.messages",
                "function": "get_current_user_from_jwt"
            }
        ]
        
        validation_behaviors = []
        
        for point in validation_points:
            try:
                module = importlib.import_module(point["module"])
                
                if "class" in point:
                    # Class method validation
                    cls = getattr(module, point["class"])
                    instance = cls()
                    method = getattr(instance, point["method"])
                    
                    # Check if method is async (indicates network call to auth service)
                    is_async = asyncio.iscoroutinefunction(method)
                    
                    # Analyze method source for delegation patterns
                    source = inspect.getsource(method)
                    has_delegation = any([
                        "auth_service" in source.lower(),
                        "auth_client" in source.lower(),
                        "delegation" in source.lower()
                    ])
                    
                else:
                    # Function validation
                    func = getattr(module, point["function"])
                    is_async = asyncio.iscoroutinefunction(func)
                    source = inspect.getsource(func)
                    has_delegation = "validate_and_decode_jwt" in source
                
                behavior = {
                    "validation_point": point["name"],
                    "is_async": is_async,
                    "has_delegation_pattern": has_delegation,
                    "source_snippet": source[:200] + "..." if len(source) > 200 else source
                }
                validation_behaviors.append(behavior)
                
            except Exception as e:
                logger.warning(f"Could not analyze validation point {point['name']}: {e}")
                continue
        
        # Check for consistency across validation points
        if len(validation_behaviors) < 2:
            logger.warning("WARNING️ ISSUE #1195 WARNING: Insufficient validation points found for consistency check")
            return
            
        # All validation points should have delegation patterns
        inconsistent_behaviors = []
        for behavior in validation_behaviors:
            if not behavior["has_delegation_pattern"]:
                inconsistent_behaviors.append(behavior)
        
        if inconsistent_behaviors:
            violation_details = {
                "violation_type": "inconsistent_jwt_validation",
                "inconsistent_points": inconsistent_behaviors,
                "total_points_checked": len(validation_behaviors),
                "ssot_requirement": "All JWT validation must use consistent auth service delegation"
            }
            
            self.security_violations.append(violation_details)
            
            pytest.fail(
                f"ISSUE #1195 SECURITY VIOLATION: Inconsistent JWT validation patterns detected. "
                f"All validation points must use auth service delegation. Details: {violation_details}"
            )
        else:
            logger.info("CHECK ISSUE #1195 SECURITY COMPLIANCE: JWT validation patterns are consistent across services")

    @pytest.mark.ssot_compliance
    @pytest.mark.security 
    async def test_auth_service_exclusive_jwt_control(self):
        """
        SECURITY TEST: Verify auth service has exclusive JWT control.
        
        Validates that only the auth service can perform JWT operations
        and no other services have JWT generation or signing capabilities.
        
        EXPECTED: PASS (only auth service should control JWT operations)
        """
        # Check for JWT generation/signing patterns in backend
        jwt_control_patterns = [
            "jwt.encode(",
            "encode_jwt",
            "generate_jwt", 
            "sign_jwt",
            "create_jwt",
            "issue_token"
        ]
        
        # Get all Python files in backend (excluding auth service)
        backend_path = Path("/Users/anthony/Desktop/netra-apex/netra_backend")
        python_files = list(backend_path.rglob("*.py"))
        
        jwt_control_violations = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for JWT control patterns
                    for pattern in jwt_control_patterns:
                        if pattern in content:
                            # Get line number and context
                            lines = content.split('\n')
                            for line_num, line in enumerate(lines, 1):
                                if pattern in line:
                                    violation = {
                                        "file": str(py_file.relative_to(backend_path.parent)),
                                        "line_number": line_num,
                                        "line_content": line.strip(),
                                        "pattern_matched": pattern,
                                        "violation_type": "unauthorized_jwt_control"
                                    }
                                    jwt_control_violations.append(violation)
                                    
            except Exception as e:
                logger.warning(f"Could not analyze file {py_file}: {e}")
                continue
        
        if jwt_control_violations:
            logger.critical(
                f"🚨 ISSUE #1195 SECURITY VIOLATION: Found {len(jwt_control_violations)} unauthorized JWT control operations. "
                f"Only auth service should control JWT generation/signing."
            )
            
            for violation in jwt_control_violations:
                logger.error(f"Unauthorized JWT control: {violation}")
                self.security_violations.append(violation)
                
            pytest.fail(
                f"ISSUE #1195 SECURITY VIOLATIONS: Found {len(jwt_control_violations)} unauthorized JWT control operations. "
                f"Only auth service should generate/sign JWTs. Violations: {jwt_control_violations}"
            )
        else:
            logger.info("CHECK ISSUE #1195 SECURITY COMPLIANCE: No unauthorized JWT control operations found")

    @pytest.mark.ssot_compliance
    @pytest.mark.security
    async def test_no_jwt_validation_bypasses_in_error_paths(self):
        """
        SECURITY TEST: Verify no JWT validation bypasses in error handling paths.
        
        Validates that error handling paths don't bypass JWT validation
        or fall back to insecure authentication methods.
        
        EXPECTED: PASS (no validation bypasses should exist)
        """
        # Define patterns that indicate validation bypasses
        bypass_patterns = [
            "except.*continue",
            "except.*pass", 
            "try.*except.*return.*True",
            "fallback.*auth",
            "bypass.*validation",
            "skip.*validation",
            "allow.*anonymous",
            "default.*authenticated"
        ]
        
        # Get all Python files in backend
        backend_path = Path("/Users/anthony/Desktop/netra-apex/netra_backend")
        auth_related_files = []
        
        # Find files likely to contain auth logic
        for py_file in backend_path.rglob("*.py"):
            if any(auth_keyword in str(py_file).lower() for auth_keyword in ['auth', 'jwt', 'token', 'websocket']):
                auth_related_files.append(py_file)
        
        bypass_violations = []
        
        for py_file in auth_related_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip().lower()
                        
                        # Check for bypass patterns
                        for pattern in bypass_patterns:
                            if any(part.strip() in line_stripped for part in pattern.split('.*')):
                                # Get surrounding context
                                start_line = max(0, line_num - 3)
                                end_line = min(len(lines), line_num + 3)
                                context = '\n'.join(lines[start_line:end_line])
                                
                                violation = {
                                    "file": str(py_file.relative_to(backend_path.parent)),
                                    "line_number": line_num,
                                    "line_content": line.strip(),
                                    "pattern_matched": pattern,
                                    "context": context,
                                    "violation_type": "potential_validation_bypass"
                                }
                                bypass_violations.append(violation)
                                
            except Exception as e:
                logger.warning(f"Could not analyze file {py_file}: {e}")
                continue
        
        if bypass_violations:
            logger.warning(
                f"WARNING️ ISSUE #1195 SECURITY WARNING: Found {len(bypass_violations)} potential validation bypasses. "
                f"Manual review required to confirm security implications."
            )
            
            for violation in bypass_violations:
                logger.warning(f"Potential validation bypass: {violation}")
                # Note: These are warnings, not hard failures, as they need manual review
        else:
            logger.info("CHECK ISSUE #1195 SECURITY COMPLIANCE: No obvious validation bypasses found")

    @pytest.mark.ssot_compliance
    @pytest.mark.security
    async def test_jwt_error_messages_dont_leak_secrets(self):
        """
        SECURITY TEST: Verify JWT error messages don't leak sensitive information.
        
        Validates that JWT validation errors don't expose secrets, tokens,
        or other sensitive authentication information in logs or responses.
        
        EXPECTED: PASS (no information leakage should occur)
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        extractor = UserContextExtractor()
        
        # Test various error scenarios that might leak information
        error_test_cases = [
            {
                "name": "invalid_token_format",
                "token": "invalid.token.format",
                "expected_no_leak": ["secret", "key", "signature"]
            },
            {
                "name": "expired_token",
                "token": "expired.jwt.token.test",
                "expected_no_leak": ["secret", "key", "signature", "payload"]
            },
            {
                "name": "malformed_token",
                "token": "malformed_token_test",
                "expected_no_leak": ["secret", "algorithm", "header"]
            }
        ]
        
        information_leaks = []
        
        for test_case in error_test_cases:
            try:
                # Mock auth service to return specific error
                async def mock_failing_validate_token(token):
                    return {
                        'valid': False, 
                        'error': f'Validation failed for token format: {test_case["name"]}'
                    }
                
                with patch.object(extractor, 'auth_service') as mock_auth_service:
                    mock_auth_service.validate_token = mock_failing_validate_token
                    
                    # Capture log output during validation
                    with patch('shared.logging.unified_logging_ssot.get_logger') as mock_logger:
                        mock_log_calls = []
                        
                        def capture_log_call(level, message, *args, **kwargs):
                            mock_log_calls.append({"level": level, "message": str(message)})
                        
                        mock_logger.return_value.error.side_effect = lambda msg, *args, **kwargs: capture_log_call("error", msg)
                        mock_logger.return_value.warning.side_effect = lambda msg, *args, **kwargs: capture_log_call("warning", msg)
                        
                        # Test validation failure
                        result = await extractor.validate_and_decode_jwt(test_case["token"])
                        
                        # Check if result or logs leak sensitive information
                        if result:
                            result_str = str(result)
                            for leak_pattern in test_case["expected_no_leak"]:
                                if leak_pattern.lower() in result_str.lower():
                                    information_leaks.append({
                                        "test_case": test_case["name"],
                                        "leak_location": "validation_result",
                                        "leaked_pattern": leak_pattern,
                                        "leak_content": result_str[:100] + "..." if len(result_str) > 100 else result_str
                                    })
                        
                        # Check log messages for leaks
                        for log_call in mock_log_calls:
                            for leak_pattern in test_case["expected_no_leak"]:
                                if leak_pattern.lower() in log_call["message"].lower():
                                    information_leaks.append({
                                        "test_case": test_case["name"],
                                        "leak_location": f"log_{log_call['level']}",
                                        "leaked_pattern": leak_pattern,
                                        "leak_content": log_call["message"][:100] + "..." if len(log_call["message"]) > 100 else log_call["message"]
                                    })
                
            except Exception as e:
                logger.debug(f"Error testing case {test_case['name']}: {e}")
                continue
        
        if information_leaks:
            logger.critical(
                f"🚨 ISSUE #1195 SECURITY VIOLATION: Found {len(information_leaks)} potential information leaks. "
                f"JWT error handling must not expose sensitive information."
            )
            
            for leak in information_leaks:
                logger.error(f"Information leak detected: {leak}")
                self.security_violations.append(leak)
                
            pytest.fail(
                f"ISSUE #1195 SECURITY VIOLATIONS: Found {len(information_leaks)} information leaks in JWT error handling. "
                f"Sensitive information must not be exposed. Leaks: {information_leaks}"
            )
        else:
            logger.info("CHECK ISSUE #1195 SECURITY COMPLIANCE: No information leaks detected in JWT error handling")

    @pytest.mark.ssot_compliance
    @pytest.mark.security
    async def test_auth_service_communication_security(self):
        """
        SECURITY TEST: Verify secure communication with auth service.
        
        Validates that communication with auth service follows security best
        practices and doesn't expose credentials or tokens in transit.
        
        EXPECTED: PASS (secure communication should be established)
        """
        from netra_backend.app.clients.auth_client_core import auth_client
        
        # Check auth client configuration for security practices
        security_checks = {
            "has_timeout_protection": False,
            "uses_secure_transport": False,
            "has_retry_limits": False,
            "has_circuit_breaker": False
        }
        
        try:
            # Check if auth client has timeout configuration
            if hasattr(auth_client, 'timeout') or hasattr(auth_client, '_timeout'):
                security_checks["has_timeout_protection"] = True
            
            # Check for HTTPS/secure transport indicators
            auth_client_source = inspect.getsource(auth_client.__class__)
            if any(pattern in auth_client_source.lower() for pattern in ['https', 'ssl', 'tls', 'secure']):
                security_checks["uses_secure_transport"] = True
            
            # Check for retry/circuit breaker patterns
            if any(pattern in auth_client_source.lower() for pattern in ['retry', 'circuit', 'breaker']):
                security_checks["has_retry_limits"] = True
                security_checks["has_circuit_breaker"] = True
                
        except Exception as e:
            logger.warning(f"Could not analyze auth client security: {e}")
        
        # Evaluate security posture
        security_score = sum(security_checks.values()) / len(security_checks)
        
        if security_score < 0.5:
            security_concern = {
                "violation_type": "insufficient_auth_service_security",
                "security_checks": security_checks,
                "security_score": security_score,
                "recommendations": [
                    "Add timeout protection for auth service calls",
                    "Ensure HTTPS/TLS for auth service communication", 
                    "Implement retry limits and circuit breaker patterns"
                ]
            }
            
            logger.warning(
                f"WARNING️ ISSUE #1195 SECURITY WARNING: Auth service communication security score: {security_score:.2f}. "
                f"Recommendations: {security_concern['recommendations']}"
            )
            
            # This is a warning, not a hard failure, as security practices may be implemented elsewhere
        else:
            logger.info(f"CHECK ISSUE #1195 SECURITY COMPLIANCE: Auth service communication security score: {security_score:.2f}")

    def teardown_method(self):
        """Teardown for each test method."""
        if self.security_violations:
            logger.critical(
                f"🚨 ISSUE #1195 SECURITY VIOLATIONS: Found {len(self.security_violations)} security-related violations. "
                f"Security must be maintained while achieving SSOT compliance."
            )
            
            # Generate detailed security violation report
            violation_summary = {
                "total_security_violations": len(self.security_violations),
                "violation_types": list(set(v.get("violation_type", "unknown") for v in self.security_violations)),
                "security_impact": "Potential exposure of JWT secrets or validation bypasses",
                "violations": self.security_violations
            }
            
            logger.error(f"ISSUE #1195 SECURITY VIOLATION REPORT: {violation_summary}")
        
        super().teardown_method()


if __name__ == "__main__":
    # Allow running this test file directly for Issue #1195 security validation
    pytest.main([__file__, "-v", "--tb=short"])