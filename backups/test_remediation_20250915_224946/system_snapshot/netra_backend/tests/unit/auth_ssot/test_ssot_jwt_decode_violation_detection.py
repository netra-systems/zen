"""
SSOT Authentication Violation Detection Test - ISSUE #814

PURPOSE: This test FAILS when backend code uses jwt.decode() directly instead of SSOT auth service delegation.
EXPECTED: FAIL - Tests demonstrate current JWT bypass violations in backend
TARGET: Identify all direct JWT decode usage that bypasses auth service SSOT pattern

CRITICAL: This test is designed to FAIL until Issue #814 SSOT remediation is complete.
"""
import logging
import pytest
from typing import List
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)

class SSOTJWTDecodeViolationDetectionTests(SSotBaseTestCase):
    """
    Unit test that FAILS when backend uses jwt.decode() directly.
    Validates that backend delegates all JWT operations to auth service.
    """

    def test_no_direct_jwt_decode_in_backend_production_code(self):
        """
        EXPECTED: FAIL - Backend has direct jwt.decode() usage bypassing auth service

        This test scans backend production code for direct jwt.decode() usage
        and FAILS if any violations are found. Success indicates SSOT compliance.
        """
        import os
        import re
        from pathlib import Path

        # Scan backend production code for jwt.decode violations
        backend_app_path = Path(__file__).parents[3] / "app"  # netra_backend/app/
        violations = []

        for py_file in backend_app_path.rglob("*.py"):
            if py_file.is_file():
                try:
                    content = py_file.read_text(encoding='utf-8')
                    # Look for direct jwt.decode usage
                    if re.search(r'jwt\.decode\s*\(', content):
                        violations.append(str(py_file.relative_to(backend_app_path)))
                except Exception as e:
                    logger.warning(f"Could not scan {py_file}: {e}")

        # Log violations for Issue #814 tracking
        if violations:
            logger.error(f"SSOT VIOLATION: Direct jwt.decode() found in {len(violations)} backend files:")
            for violation in violations:
                logger.error(f"  - {violation}")

        # TEST DESIGNED TO FAIL: Demonstrates current SSOT violations
        assert len(violations) == 0, (
            f"SSOT VIOLATION DETECTED: Found {len(violations)} backend files using direct jwt.decode() "
            f"instead of auth service delegation. Files: {violations}. "
            f"All JWT operations must go through auth service SSOT pattern."
        )

    def test_websocket_auth_uses_auth_service_delegation(self):
        """
        EXPECTED: FAIL - WebSocket auth likely bypasses auth service

        Validates WebSocket authentication uses auth service delegation
        instead of direct JWT handling.
        """
        from pathlib import Path
        import re

        # Scan WebSocket auth components
        websocket_paths = [
            Path(__file__).parents[3] / "app" / "websocket_core",
            Path(__file__).parents[3] / "app" / "routes" / "websocket.py"
        ]

        violations = []
        for path in websocket_paths:
            if path.is_file():
                try:
                    content = path.read_text(encoding='utf-8')
                    if re.search(r'jwt\.decode\s*\(', content):
                        violations.append(str(path))
                except Exception:
                    pass
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        if re.search(r'jwt\.decode\s*\(', content):
                            violations.append(str(py_file))
                    except Exception:
                        pass

        # TEST DESIGNED TO FAIL: WebSocket auth likely bypasses SSOT
        assert len(violations) == 0, (
            f"WebSocket authentication SSOT violation: {violations} files use direct jwt.decode(). "
            f"Must delegate to auth service for SSOT compliance."
        )

    def test_message_routes_use_auth_service_delegation(self):
        """
        EXPECTED: FAIL - Message routes likely bypass auth service

        Validates message/chat routes delegate authentication to auth service
        instead of handling JWT directly.
        """
        from pathlib import Path
        import re

        # Scan message/chat route files
        routes_path = Path(__file__).parents[3] / "app" / "routes"
        violations = []

        for py_file in routes_path.rglob("*.py"):
            if py_file.is_file():
                try:
                    content = py_file.read_text(encoding='utf-8')
                    # Look for JWT decode in route handlers
                    if re.search(r'jwt\.decode\s*\(', content):
                        violations.append(str(py_file.relative_to(routes_path)))
                except Exception:
                    pass

        # TEST DESIGNED TO FAIL: Routes likely bypass auth service SSOT
        assert len(violations) == 0, (
            f"Route authentication SSOT violation: {violations} files use direct jwt.decode(). "
            f"All routes must delegate authentication to auth service."
        )

    def test_auth_middleware_delegates_to_auth_service(self):
        """
        EXPECTED: FAIL - Auth middleware likely has direct JWT handling

        Validates auth middleware delegates to auth service instead of
        implementing JWT logic directly.
        """
        from pathlib import Path
        import re

        # Find auth middleware files
        app_path = Path(__file__).parents[3] / "app"
        violations = []

        # Common auth middleware locations
        auth_patterns = ["**/middleware/**/*auth*.py", "**/auth*/**/*.py"]

        for pattern in auth_patterns:
            for py_file in app_path.rglob(pattern):
                if py_file.is_file():
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        if re.search(r'jwt\.decode\s*\(', content):
                            violations.append(str(py_file.relative_to(app_path)))
                    except Exception:
                        pass

        # TEST DESIGNED TO FAIL: Middleware likely bypasses SSOT
        assert len(violations) == 0, (
            f"Auth middleware SSOT violation: {violations} files use direct jwt.decode(). "
            f"Middleware must delegate to auth service for SSOT compliance."
        )