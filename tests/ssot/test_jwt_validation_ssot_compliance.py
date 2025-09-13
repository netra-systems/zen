"""
SSOT Compliance Tests for JWT Validation Consolidation

This test suite validates that all JWT validation operations go through the auth service
as the Single Source of Truth (SSOT). These tests are designed to FAIL in the current
state where JWT validation is scattered across services and PASS after SSOT consolidation.

MISSION: Issue #670 - JWT validation scattered across services
GOAL: Consolidate JWT validation in auth service as SSOT
REMOVE: JWT validation logic from netra_backend/app/core/unified/jwt_validator.py

Business Value: Platform/Internal - Security consistency and maintenance reduction
Segment: All (Free -> Enterprise) - Security affects all users
Value Impact: Eliminates JWT security bugs, ensures single auth source
Strategic Impact: Improved security posture and compliance

Test Strategy: These tests should FAIL before SSOT remediation and PASS after
"""

import asyncio
import ast
import os
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Set
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestJWTValidationSSOTCompliance(SSotAsyncTestCase):
    """SSOT compliance tests for JWT validation consolidation."""

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Define critical files for JWT validation
        self.backend_jwt_validator_file = "netra_backend/app/core/unified/jwt_validator.py"
        self.auth_service_jwt_handler = "auth_service/auth_core/core/jwt_handler.py"
        self.websocket_auth_file = "netra_backend/app/websocket_core/auth.py"
        self.shared_jwt_files = [
            "shared/jwt_secret_validator.py",
            "shared/jwt_secret_manager.py",
            "shared/jwt_secret_consistency_validator.py",
        ]

        # Define SSOT violation patterns
        self.forbidden_jwt_patterns = [
            "jwt.decode(",
            "jwt.encode(",
            "PyJWT",
            "import jwt",
            "from jwt import",
        ]

        # Define allowed auth service delegation patterns
        self.allowed_delegation_patterns = [
            "auth_client.",
            "await auth_client.",
            "auth_service",
            "# Delegate to auth service",
            "# ALL JWT operations go through auth service",
        ]

    def test_backend_jwt_validator_delegates_to_auth_service(self):
        """
        Test that backend JWT validator only delegates to auth service.

        SSOT Requirement: netra_backend/app/core/unified/jwt_validator.py should only
        contain delegation logic to auth service, NO direct JWT operations.

        Should FAIL before SSOT consolidation (contains jwt.decode/encode)
        Should PASS after SSOT consolidation (only delegation)
        """
        project_root = Path(self.get_env_var("PWD", os.getcwd()))
        jwt_validator_path = project_root / self.backend_jwt_validator_file

        self.assertTrue(
            jwt_validator_path.exists(),
            f"JWT validator file not found: {jwt_validator_path}"
        )

        # Read file content
        with open(jwt_validator_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Record metrics
        self.record_metric("jwt_validator_file_lines", len(content.splitlines()))

        # Check for forbidden direct JWT operations
        jwt_violations = []
        for pattern in self.forbidden_jwt_patterns:
            if pattern in content:
                # Find line numbers for better debugging
                for line_num, line in enumerate(content.splitlines(), 1):
                    if pattern in line and not line.strip().startswith("#"):
                        jwt_violations.append(f"Line {line_num}: {line.strip()}")

        # Check for required delegation patterns
        delegation_found = any(pattern in content for pattern in self.allowed_delegation_patterns)

        # Record SSOT compliance metrics
        self.record_metric("jwt_violations_found", len(jwt_violations))
        self.record_metric("delegation_patterns_found", delegation_found)

        # SSOT Compliance Check: Should have NO direct JWT operations
        if jwt_violations:
            self.record_metric("ssot_violation_detected", True)
            # Expected to FAIL before SSOT consolidation
            self.fail(
                f"SSOT VIOLATION: Backend JWT validator contains direct JWT operations. "
                f"Found {len(jwt_violations)} violations:\n" +
                "\n".join(jwt_violations[:5]) +
                f"\n... (showing first 5 of {len(jwt_violations)} violations)"
            )

        # Should have delegation to auth service
        self.assertTrue(
            delegation_found,
            "Backend JWT validator must delegate all operations to auth service"
        )

        self.record_metric("ssot_compliance_backend_jwt", True)

    def test_no_duplicate_jwt_validation_logic_exists(self):
        """
        Test that no duplicate JWT validation implementations exist.

        SSOT Requirement: Only auth service should contain JWT validation logic.
        All other services should delegate to auth service.

        Should FAIL before SSOT consolidation (multiple implementations)
        Should PASS after SSOT consolidation (single implementation in auth service)
        """
        project_root = Path(self.get_env_var("PWD", os.getcwd()))

        # Scan for JWT implementations across the codebase
        jwt_implementations = self._scan_for_jwt_implementations(project_root)

        # Record metrics
        self.record_metric("jwt_implementations_found", len(jwt_implementations))

        # Only auth service should have JWT implementation
        allowed_jwt_files = {
            "auth_service/auth_core/core/jwt_handler.py",
            "auth_service/services/jwt_service.py",
            "auth_service/auth_core/api/jwt_validation.py",
        }

        unauthorized_implementations = []
        for file_path, violations in jwt_implementations.items():
            relative_path = str(file_path.relative_to(project_root))
            if relative_path not in allowed_jwt_files:
                unauthorized_implementations.append({
                    "file": relative_path,
                    "violations": violations
                })

        # Record SSOT compliance metrics
        self.record_metric("unauthorized_jwt_implementations", len(unauthorized_implementations))

        if unauthorized_implementations:
            self.record_metric("ssot_violation_detected", True)
            violation_summary = []
            for impl in unauthorized_implementations[:3]:  # Show first 3
                violation_summary.append(
                    f"File: {impl['file']} - {len(impl['violations'])} violations"
                )

            # Expected to FAIL before SSOT consolidation
            self.fail(
                f"SSOT VIOLATION: Found {len(unauthorized_implementations)} files with "
                f"unauthorized JWT implementations:\n" +
                "\n".join(violation_summary) +
                f"\n... (showing first 3 of {len(unauthorized_implementations)} files)"
            )

        self.record_metric("ssot_compliance_no_duplicates", True)

    async def test_websocket_auth_uses_ssot_jwt_validation(self):
        """
        Test that WebSocket auth uses SSOT JWT validation only.

        SSOT Requirement: WebSocket authentication must delegate to auth service
        for all JWT operations.

        Should FAIL before SSOT consolidation (direct JWT operations)
        Should PASS after SSOT consolidation (auth service delegation)
        """
        project_root = Path(self.get_env_var("PWD", os.getcwd()))
        websocket_auth_path = project_root / self.websocket_auth_file

        if not websocket_auth_path.exists():
            # If file doesn't exist, check for alternative locations
            possible_paths = [
                "netra_backend/app/websocket_core/unified_jwt_protocol_handler.py",
                "netra_backend/app/auth_integration/auth.py",
                "netra_backend/app/websocket_core/manager.py",
            ]

            for alt_path in possible_paths:
                alt_file_path = project_root / alt_path
                if alt_file_path.exists():
                    websocket_auth_path = alt_file_path
                    break

        if not websocket_auth_path.exists():
            self.fail(f"WebSocket auth file not found at any expected location")

        # Read WebSocket auth file
        with open(websocket_auth_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Record metrics
        self.record_metric("websocket_auth_file_lines", len(content.splitlines()))

        # Check for direct JWT operations in WebSocket auth
        jwt_violations = []
        for pattern in self.forbidden_jwt_patterns:
            if pattern in content:
                for line_num, line in enumerate(content.splitlines(), 1):
                    if pattern in line and not line.strip().startswith("#"):
                        jwt_violations.append(f"Line {line_num}: {line.strip()}")

        # Check for auth service delegation
        delegation_patterns = [
            "auth_client",
            "validate_token_jwt",
            "auth_service",
        ]
        delegation_found = any(pattern in content for pattern in delegation_patterns)

        # Record SSOT compliance metrics
        self.record_metric("websocket_jwt_violations", len(jwt_violations))
        self.record_metric("websocket_auth_delegation", delegation_found)

        if jwt_violations:
            self.record_metric("ssot_violation_detected", True)
            # Expected to FAIL before SSOT consolidation
            self.fail(
                f"SSOT VIOLATION: WebSocket auth contains direct JWT operations. "
                f"Found {len(jwt_violations)} violations:\n" +
                "\n".join(jwt_violations[:3])
            )

        # Should delegate to auth service
        self.assertTrue(
            delegation_found,
            "WebSocket auth must delegate JWT operations to auth service"
        )

        self.record_metric("ssot_compliance_websocket_auth", True)

    def test_shared_jwt_utilities_consolidated_in_auth_service(self):
        """
        Test that shared JWT utilities are consolidated in auth service.

        SSOT Requirement: No shared JWT utilities should exist outside auth service.
        All JWT functionality should be centralized.

        Should FAIL before SSOT consolidation (shared JWT utilities exist)
        Should PASS after SSOT consolidation (utilities moved to auth service)
        """
        project_root = Path(self.get_env_var("PWD", os.getcwd()))

        # Check shared JWT files for violations
        shared_jwt_violations = []

        for shared_file in self.shared_jwt_files:
            shared_path = project_root / shared_file
            if shared_path.exists():
                with open(shared_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for actual JWT operations (not just configuration)
                jwt_operations = []
                for pattern in ["jwt.decode(", "jwt.encode(", "JWT.decode", "JWT.encode"]:
                    if pattern in content:
                        for line_num, line in enumerate(content.splitlines(), 1):
                            if pattern in line and not line.strip().startswith("#"):
                                jwt_operations.append(f"Line {line_num}: {line.strip()}")

                if jwt_operations:
                    shared_jwt_violations.append({
                        "file": shared_file,
                        "operations": jwt_operations
                    })

        # Record metrics
        self.record_metric("shared_jwt_files_with_violations", len(shared_jwt_violations))

        if shared_jwt_violations:
            self.record_metric("ssot_violation_detected", True)
            violation_summary = []
            for violation in shared_jwt_violations:
                violation_summary.append(
                    f"File: {violation['file']} - {len(violation['operations'])} operations"
                )

            # Expected to FAIL before SSOT consolidation
            self.fail(
                f"SSOT VIOLATION: Found JWT operations in shared utilities. "
                f"All JWT operations must be in auth service:\n" +
                "\n".join(violation_summary)
            )

        self.record_metric("ssot_compliance_shared_utilities", True)

    async def test_auth_service_is_single_jwt_authority(self):
        """
        Test that auth service is the single JWT authority.

        SSOT Requirement: Auth service should be the only service that
        performs actual JWT encode/decode operations.

        Should PASS always (validates auth service has JWT capabilities)
        """
        project_root = Path(self.get_env_var("PWD", os.getcwd()))
        auth_handler_path = project_root / self.auth_service_jwt_handler

        self.assertTrue(
            auth_handler_path.exists(),
            f"Auth service JWT handler not found: {auth_handler_path}"
        )

        # Read auth service JWT handler
        with open(auth_handler_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify auth service has proper JWT capabilities
        required_jwt_methods = [
            "validate_token",
            "create_access_token",
            "create_refresh_token",
            "jwt.decode",
            "jwt.encode",
        ]

        missing_methods = []
        for method in required_jwt_methods:
            if method not in content:
                missing_methods.append(method)

        # Record metrics
        self.record_metric("auth_service_jwt_methods_found", len(required_jwt_methods) - len(missing_methods))
        self.record_metric("auth_service_jwt_methods_missing", len(missing_methods))

        self.assertEmpty(
            missing_methods,
            f"Auth service missing required JWT methods: {missing_methods}"
        )

        # Verify JWTHandler class exists
        self.assertIn("class JWTHandler", content, "JWTHandler class not found in auth service")

        self.record_metric("ssot_compliance_auth_service_authority", True)

    async def test_no_jwt_imports_outside_auth_service(self):
        """
        Test that no direct JWT library imports exist outside auth service.

        SSOT Requirement: Only auth service should import JWT libraries directly.
        Other services should use auth service client.

        Should FAIL before SSOT consolidation (JWT imports scattered)
        Should PASS after SSOT consolidation (only in auth service)
        """
        project_root = Path(self.get_env_var("PWD", os.getcwd()))

        # Scan for JWT imports outside auth service
        unauthorized_jwt_imports = []

        # Define allowed files for JWT imports
        allowed_jwt_import_files = {
            "auth_service/auth_core/core/jwt_handler.py",
            "auth_service/services/jwt_service.py",
            "auth_service/auth_core/api/jwt_validation.py",
            "auth_service/auth_core/performance/jwt_performance.py",
        }

        # Scan Python files for JWT imports
        for py_file in project_root.rglob("*.py"):
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue

            relative_path = str(py_file.relative_to(project_root))

            # Skip allowed files
            if relative_path in allowed_jwt_import_files:
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for JWT imports
                jwt_import_lines = []
                for line_num, line in enumerate(content.splitlines(), 1):
                    line_stripped = line.strip()
                    if (line_stripped.startswith("import jwt") or
                        line_stripped.startswith("from jwt") or
                        "import PyJWT" in line_stripped):
                        jwt_import_lines.append(f"Line {line_num}: {line_stripped}")

                if jwt_import_lines:
                    unauthorized_jwt_imports.append({
                        "file": relative_path,
                        "imports": jwt_import_lines
                    })

            except (UnicodeDecodeError, PermissionError):
                continue  # Skip files that can't be read

        # Record metrics
        self.record_metric("unauthorized_jwt_imports_found", len(unauthorized_jwt_imports))

        if unauthorized_jwt_imports:
            self.record_metric("ssot_violation_detected", True)
            violation_summary = []
            for violation in unauthorized_jwt_imports[:5]:  # Show first 5
                violation_summary.append(
                    f"File: {violation['file']} - {len(violation['imports'])} imports"
                )

            # Expected to FAIL before SSOT consolidation
            self.fail(
                f"SSOT VIOLATION: Found {len(unauthorized_jwt_imports)} files with "
                f"unauthorized JWT imports:\n" +
                "\n".join(violation_summary) +
                f"\n... (showing first 5 of {len(unauthorized_jwt_imports)} files)"
            )

        self.record_metric("ssot_compliance_no_jwt_imports", True)

    def _scan_for_jwt_implementations(self, project_root: Path) -> Dict[Path, List[str]]:
        """
        Scan codebase for JWT implementation patterns.

        Returns:
            Dict mapping file paths to lists of JWT violations found
        """
        jwt_implementations = {}

        # Patterns that indicate JWT implementation (not just usage)
        implementation_patterns = [
            "jwt.decode(",
            "jwt.encode(",
            "JWT.decode(",
            "JWT.encode(",
            "class.*JWT.*Handler",
            "def.*validate.*jwt",
            "def.*create.*token",
            "def.*encode.*token",
            "def.*decode.*token",
        ]

        for py_file in project_root.rglob("*.py"):
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                violations = []
                for pattern in implementation_patterns:
                    if pattern in content:
                        for line_num, line in enumerate(content.splitlines(), 1):
                            if pattern.replace("(", "").replace(".*", "") in line and not line.strip().startswith("#"):
                                violations.append(f"Line {line_num}: {pattern}")

                if violations:
                    jwt_implementations[py_file] = violations

            except (UnicodeDecodeError, PermissionError):
                continue

        return jwt_implementations

    # Custom assertion for empty collections
    def assertEmpty(self, collection, msg=None):
        """Assert that a collection is empty."""
        assert len(collection) == 0, msg or f"Expected empty collection, got {len(collection)} items: {list(collection)[:5]}"


class TestJWTValidationSSOTIntegration(SSotAsyncTestCase):
    """Integration tests for JWT SSOT compliance across services."""

    def setup_method(self, method):
        """Setup for integration tests."""
        super().setup_method(method)
        self.set_env_var("TESTING", "true")
        self.set_env_var("ENVIRONMENT", "test")

    async def test_cross_service_jwt_delegation_chain(self):
        """
        Test that JWT validation follows proper delegation chain.

        Expected flow: Frontend -> Backend -> Auth Service
        Should FAIL before SSOT (multiple JWT handlers)
        Should PASS after SSOT (single delegation chain)
        """
        # Mock the services to test delegation chain
        with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value={
                "valid": True,
                "user_id": "test_user",
                "email": "test@example.com"
            })

            # Import and test the backend JWT validator
            try:
                from netra_backend.app.core.unified.jwt_validator import jwt_validator

                # Test that it delegates to auth service
                test_token = "test.jwt.token"
                result = await jwt_validator.validate_token_jwt(test_token)

                # Should call auth service
                mock_auth_client.validate_token_jwt.assert_called_once_with(test_token)

                # Should return auth service result
                self.assertIsNotNone(result)
                self.assertTrue(result.valid)

                self.record_metric("delegation_chain_working", True)

            except ImportError as e:
                self.fail(f"Cannot test JWT delegation chain: {e}")

    async def test_jwt_validation_consistency_across_services(self):
        """
        Test that JWT validation is consistent across all services.

        All services should use the same validation logic (from auth service).
        Should FAIL before SSOT (inconsistent validation)
        Should PASS after SSOT (consistent validation via auth service)
        """
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJpYXQiOjE2MjM5NjQ4MDAsImV4cCI6MTYyMzk2ODQwMCwidG9rZW5fdHlwZSI6ImFjY2VzcyJ9.test_signature"

        # Mock auth service response
        expected_response = {
            "valid": True,
            "user_id": "test_user",
            "email": "test@example.com",
            "permissions": ["read"]
        }

        with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=expected_response)

            # Test backend JWT validator
            try:
                from netra_backend.app.core.unified.jwt_validator import jwt_validator
                backend_result = await jwt_validator.validate_token_jwt(test_token)

                # Verify auth service was called
                mock_auth_client.validate_token_jwt.assert_called_with(test_token)

                # Verify consistent response format
                self.assertTrue(backend_result.valid)
                self.assertEqual(backend_result.user_id, "test_user")

                self.record_metric("jwt_validation_consistency", True)

            except ImportError:
                self.record_metric("jwt_validation_consistency", False)
                self.fail("Backend JWT validator not accessible for consistency test")

    def test_ssot_compliance_summary_metrics(self):
        """
        Generate summary metrics for SSOT compliance.

        This test always runs and provides compliance metrics for monitoring.
        """
        # Calculate compliance score based on previous test metrics
        compliance_metrics = [
            "ssot_compliance_backend_jwt",
            "ssot_compliance_no_duplicates",
            "ssot_compliance_websocket_auth",
            "ssot_compliance_shared_utilities",
            "ssot_compliance_auth_service_authority",
            "ssot_compliance_no_jwt_imports",
        ]

        passed_metrics = sum(1 for metric in compliance_metrics
                           if self.get_metric(metric, False))
        total_metrics = len(compliance_metrics)
        compliance_score = (passed_metrics / total_metrics) * 100

        # Record summary metrics
        self.record_metric("ssot_compliance_score", compliance_score)
        self.record_metric("ssot_metrics_passed", passed_metrics)
        self.record_metric("ssot_metrics_total", total_metrics)

        # Check if any violations were detected
        violations_detected = self.get_metric("ssot_violation_detected", False)
        self.record_metric("ssot_violations_detected", violations_detected)

        # Log compliance status
        if compliance_score == 100:
            self.record_metric("ssot_status", "COMPLIANT")
        elif compliance_score >= 50:
            self.record_metric("ssot_status", "PARTIAL_COMPLIANCE")
        else:
            self.record_metric("ssot_status", "NON_COMPLIANT")

        # This test documents current state but doesn't fail
        # (allows monitoring without blocking development)
        if violations_detected:
            print(f"SSOT Compliance: {compliance_score:.1f}% ({passed_metrics}/{total_metrics} checks passed)")
            print("SSOT violations detected - see other test failures for details")
        else:
            print(f"SSOT Compliance: {compliance_score:.1f}% - No violations detected")