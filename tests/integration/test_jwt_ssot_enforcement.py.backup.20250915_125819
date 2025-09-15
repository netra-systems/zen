"""
JWT SSOT Enforcement Integration Tests - ISSUE #1060

PURPOSE: Detect multiple JWT validation implementations across services
These tests are designed to FAIL initially, proving current SSOT violations exist.

MISSION: Validate WebSocket authentication path fragmentation blocking Golden Path
Business Value: $500K+ ARR Golden Path protection through unified authentication

Expected Initial Behavior: ALL TESTS FAIL - proving JWT SSOT violations exist
After remediation: All tests should PASS confirming single JWT validation authority

Test Strategy:
1. Detect multiple JWT validation paths between backend/auth service
2. Identify WebSocket JWT validation divergence from HTTP
3. Validate frontend JWT decode delegation
4. Confirm unified JWT validation authority across all services

Author: Claude Code Agent - SSOT Validation Test Generator
Date: 2025-09-14
"""
import pytest
import asyncio
import logging
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from unittest.mock import patch
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase, CategoryType
from shared.isolated_environment import get_env
logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestJwtSsotEnforcement(SSotBaseTestCase):
    """
    JWT SSOT Enforcement Tests - Designed to FAIL initially

    Business Value: Platform/Internal - $500K+ ARR Golden Path Authentication
    These tests detect JWT validation duplication that fragments authentication paths.

    EXPECTED RESULT: ALL TESTS FAIL until SSOT remediation complete
    """

    def setup_method(self, method):
        """Initialize test environment for JWT SSOT validation."""
        super().setup_method(method)
        self.logger = logger
        self.test_context = self.get_test_context()
        self.test_context.test_category = CategoryType.INTEGRATION
        self.set_env_var('TEST_JWT_SSOT_ENFORCEMENT', 'true')
        self.set_env_var('DETECT_JWT_VIOLATIONS', 'true')
        self.logger.info(f'Starting JWT SSOT enforcement test: {method.__name__}')

    def test_single_jwt_validation_authority(self):
        """
        Test: Only ONE JWT validation implementation should exist across services

        EXPECTED: FAIL - Multiple JWT validation paths currently exist
        VIOLATION: Backend bypasses auth service for JWT operations
        """
        jwt_validation_implementations = []
        violation_details = []
        project_root = Path(__file__).parent.parent.parent
        backend_jwt_files = self._scan_for_jwt_implementations(project_root / 'netra_backend', 'backend')
        jwt_validation_implementations.extend(backend_jwt_files)
        auth_jwt_files = self._scan_for_jwt_implementations(project_root / 'auth_service', 'auth_service')
        jwt_validation_implementations.extend(auth_jwt_files)
        frontend_jwt_files = self._scan_for_jwt_implementations(project_root / 'frontend', 'frontend')
        jwt_validation_implementations.extend(frontend_jwt_files)
        self.record_metric('jwt_validation_implementations_found', len(jwt_validation_implementations))
        if len(jwt_validation_implementations) > 1:
            violation_details = [f"Multiple JWT validation found in: {impl['service']}/{impl['file']}" for impl in jwt_validation_implementations]
            self.logger.critical(f'JWT SSOT VIOLATION DETECTED: {len(jwt_validation_implementations)} separate JWT validation implementations found: {violation_details}')
            self.assertTrue(False, f'JWT SSOT VIOLATION: Found {len(jwt_validation_implementations)} separate JWT validation implementations. Expected: 1 (auth service only). Violations: {violation_details}')
        else:
            self.logger.info('JWT SSOT COMPLIANCE: Single JWT validation authority confirmed')
            self.assertTrue(len(jwt_validation_implementations) == 1)

    def test_backend_delegates_jwt_to_auth_service(self):
        """
        Test: Backend should delegate ALL JWT operations to auth service

        EXPECTED: FAIL - Backend currently has direct JWT validation
        VIOLATION: Backend bypasses auth service JWT validation authority
        """
        backend_jwt_violations = []
        project_root = Path(__file__).parent.parent.parent
        backend_path = project_root / 'netra_backend'
        direct_jwt_imports = self._scan_for_direct_jwt_imports(backend_path)
        backend_jwt_violations.extend(direct_jwt_imports)
        jwt_operations = self._scan_for_jwt_operations(backend_path)
        backend_jwt_violations.extend(jwt_operations)
        self.record_metric('backend_jwt_violations', len(backend_jwt_violations))
        if backend_jwt_violations:
            violation_details = [f"{violation['type']}: {violation['file']}:{violation['line']}" for violation in backend_jwt_violations]
            self.logger.critical(f'BACKEND JWT DELEGATION VIOLATION: Backend performing direct JWT operations. Violations: {violation_details}')
            self.assertTrue(False, f'BACKEND JWT DELEGATION VIOLATION: Backend should delegate ALL JWT operations to auth service. Found {len(backend_jwt_violations)} violations: {violation_details}')
        else:
            self.logger.info('JWT DELEGATION COMPLIANCE: Backend properly delegates to auth service')
            self.assertTrue(len(backend_jwt_violations) == 0)

    def test_websocket_uses_same_jwt_validation_as_http(self):
        """
        Test: WebSocket and HTTP should use identical JWT validation logic

        EXPECTED: FAIL - WebSocket has different JWT validation path
        VIOLATION: WebSocket authentication diverges from HTTP authentication
        """
        auth_path_differences = []
        project_root = Path(__file__).parent.parent.parent
        backend_path = project_root / 'netra_backend'
        http_jwt_path = self._find_http_jwt_validation_path(backend_path)
        websocket_jwt_path = self._find_websocket_jwt_validation_path(backend_path)
        if http_jwt_path and websocket_jwt_path:
            path_comparison = self._compare_jwt_validation_paths(http_jwt_path, websocket_jwt_path)
            if not path_comparison['identical']:
                auth_path_differences = path_comparison['differences']
                self.logger.critical(f'WEBSOCKET JWT VALIDATION DIVERGENCE: WebSocket uses different JWT validation than HTTP. Differences: {auth_path_differences}')
                self.assertTrue(False, f'WEBSOCKET JWT VALIDATION DIVERGENCE: WebSocket and HTTP must use identical JWT validation. Differences found: {auth_path_differences}')
        self.record_metric('jwt_validation_path_differences', len(auth_path_differences))
        if not auth_path_differences:
            self.logger.info('JWT VALIDATION CONSISTENCY: WebSocket and HTTP use identical validation')
            self.assertTrue(len(auth_path_differences) == 0)

    def test_frontend_delegates_jwt_decode_to_backend(self):
        """
        Test: Frontend should delegate JWT decode operations to backend

        EXPECTED: FAIL - Frontend currently decodes JWTs directly
        VIOLATION: Frontend bypasses backend for JWT decode operations
        """
        frontend_jwt_violations = []
        project_root = Path(__file__).parent.parent.parent
        frontend_path = project_root / 'frontend'
        jwt_imports = self._scan_frontend_jwt_imports(frontend_path)
        frontend_jwt_violations.extend(jwt_imports)
        jwt_decode_ops = self._scan_frontend_jwt_decode_operations(frontend_path)
        frontend_jwt_violations.extend(jwt_decode_ops)
        self.record_metric('frontend_jwt_violations', len(frontend_jwt_violations))
        if frontend_jwt_violations:
            violation_details = [f"{violation['type']}: {violation['file']}" for violation in frontend_jwt_violations]
            self.logger.critical(f'FRONTEND JWT DELEGATION VIOLATION: Frontend performing direct JWT operations. Should delegate to backend. Violations: {violation_details}')
            self.assertTrue(False, f'FRONTEND JWT DELEGATION VIOLATION: Frontend should delegate ALL JWT decode operations to backend. Found {len(frontend_jwt_violations)} violations: {violation_details}')
        else:
            self.logger.info('FRONTEND JWT DELEGATION COMPLIANCE: Frontend properly delegates to backend')
            self.assertTrue(len(frontend_jwt_violations) == 0)

    def _scan_for_jwt_implementations(self, path: Path, service_name: str) -> List[Dict[str, Any]]:
        """Scan for JWT validation implementations in a service."""
        implementations = []
        if not path.exists():
            return implementations
        jwt_patterns = ['jwt.decode', 'jwt.encode', 'JWTValidator', 'TokenValidator', 'verify_token', 'validate_jwt']
        for py_file in path.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                for pattern in jwt_patterns:
                    if pattern in content:
                        implementations.append({'service': service_name, 'file': str(py_file.relative_to(path)), 'pattern': pattern})
                        break
            except Exception as e:
                self.logger.warning(f'Error scanning {py_file}: {e}')
        return implementations

    def _scan_for_direct_jwt_imports(self, path: Path) -> List[Dict[str, Any]]:
        """Scan for direct JWT library imports."""
        violations = []
        if not path.exists():
            return violations
        import_patterns = ['import jwt', 'from jwt import', 'import pyjwt', 'from pyjwt import']
        for py_file in path.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern in import_patterns:
                        if pattern in line.strip():
                            violations.append({'type': 'direct_jwt_import', 'file': str(py_file.relative_to(path)), 'line': line_num, 'content': line.strip()})
            except Exception as e:
                self.logger.warning(f'Error scanning {py_file}: {e}')
        return violations

    def _scan_for_jwt_operations(self, path: Path) -> List[Dict[str, Any]]:
        """Scan for JWT encode/decode operations."""
        violations = []
        if not path.exists():
            return violations
        operation_patterns = ['jwt.decode(', 'jwt.encode(', '.decode_token(', '.encode_token(', 'decode_jwt(', 'encode_jwt(']
        for py_file in path.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern in operation_patterns:
                        if pattern in line:
                            violations.append({'type': 'jwt_operation', 'file': str(py_file.relative_to(path)), 'line': line_num, 'pattern': pattern, 'content': line.strip()})
            except Exception as e:
                self.logger.warning(f'Error scanning {py_file}: {e}')
        return violations

    def _find_http_jwt_validation_path(self, backend_path: Path) -> Optional[Dict[str, Any]]:
        """Find HTTP JWT validation implementation."""
        http_auth_files = []
        for py_file in backend_path.rglob('*.py'):
            if any((keyword in str(py_file) for keyword in ['auth', 'http', 'route', 'middleware'])):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    if any((pattern in content for pattern in ['jwt', 'token', 'authorization'])):
                        http_auth_files.append({'file': str(py_file.relative_to(backend_path)), 'type': 'http_auth'})
                except Exception as e:
                    self.logger.warning(f'Error scanning {py_file}: {e}')
        return http_auth_files[0] if http_auth_files else None

    def _find_websocket_jwt_validation_path(self, backend_path: Path) -> Optional[Dict[str, Any]]:
        """Find WebSocket JWT validation implementation."""
        ws_auth_files = []
        for py_file in backend_path.rglob('*.py'):
            if any((keyword in str(py_file) for keyword in ['websocket', 'ws', 'socket'])):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    if any((pattern in content for pattern in ['jwt', 'token', 'authorization', 'auth'])):
                        ws_auth_files.append({'file': str(py_file.relative_to(backend_path)), 'type': 'websocket_auth'})
                except Exception as e:
                    self.logger.warning(f'Error scanning {py_file}: {e}')
        return ws_auth_files[0] if ws_auth_files else None

    def _compare_jwt_validation_paths(self, http_path: Dict[str, Any], ws_path: Dict[str, Any]) -> Dict[str, Any]:
        """Compare HTTP and WebSocket JWT validation paths."""
        differences = []
        if http_path['file'] != ws_path['file']:
            differences.append(f"Different files: HTTP={http_path['file']}, WebSocket={ws_path['file']}")
        return {'identical': len(differences) == 0, 'differences': differences}

    def _scan_frontend_jwt_imports(self, frontend_path: Path) -> List[Dict[str, Any]]:
        """Scan frontend for JWT library imports."""
        violations = []
        if not frontend_path.exists():
            return violations
        for ext in ['*.ts', '*.tsx', '*.js', '*.jsx']:
            for file in frontend_path.rglob(ext):
                try:
                    content = file.read_text(encoding='utf-8')
                    jwt_imports = ['jsonwebtoken', 'jwt-decode', 'jose', '@auth0/nextjs-auth0']
                    for jwt_lib in jwt_imports:
                        if f'import' in content and jwt_lib in content:
                            violations.append({'type': 'frontend_jwt_import', 'file': str(file.relative_to(frontend_path)), 'library': jwt_lib})
                except Exception as e:
                    self.logger.warning(f'Error scanning {file}: {e}')
        return violations

    def _scan_frontend_jwt_decode_operations(self, frontend_path: Path) -> List[Dict[str, Any]]:
        """Scan frontend for JWT decode operations."""
        violations = []
        if not frontend_path.exists():
            return violations
        decode_patterns = ['jwt_decode(', 'decode(', 'parseJwt(', 'decodeToken(', 'JSON.parse(atob(', 'jwt.decode(']
        for ext in ['*.ts', '*.tsx', '*.js', '*.jsx']:
            for file in frontend_path.rglob(ext):
                try:
                    content = file.read_text(encoding='utf-8')
                    for pattern in decode_patterns:
                        if pattern in content:
                            violations.append({'type': 'frontend_jwt_decode', 'file': str(file.relative_to(frontend_path)), 'pattern': pattern})
                            break
                except Exception as e:
                    self.logger.warning(f'Error scanning {file}: {e}')
        return violations

    def teardown_method(self, method):
        """Cleanup after JWT SSOT enforcement tests."""
        metrics = self.get_all_metrics()
        self.logger.info(f'JWT SSOT test completed: {method.__name__}')
        self.logger.info(f'Test metrics: {metrics}')
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')