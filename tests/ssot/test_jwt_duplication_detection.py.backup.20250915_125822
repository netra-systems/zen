"""
JWT SSOT Duplication Detection Tests

PURPOSE: These tests FAIL when backend code duplicates JWT operations that should 
only exist in the auth service (SSOT violation). Tests will PASS after SSOT refactor.

MISSION CRITICAL: Protects $500K+ ARR Golden Path by ensuring JWT operations 
are centralized in auth service only.

BUSINESS VALUE: Enterprise/Platform - Security & Compliance
- Prevents JWT validation inconsistencies
- Reduces attack surface 
- Ensures audit trail centralization
- Maintains SSOT architectural compliance

EXPECTED STATUS: FAIL (before SSOT refactor) → PASS (after SSOT refactor)

These tests detect SSOT violations by scanning for:
1. Direct JWT library imports in backend production code
2. JWT decode/verify operations outside auth service
3. JWT secret management duplication
4. WebSocket auth bypassing auth service
"""

import ast
import os
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)

class TestJwtDuplicationDetection(SSotAsyncTestCase):
    """
    SSOT Compliance Tests - JWT Duplication Detection
    
    These tests FAIL when backend violates JWT SSOT principles.
    After SSOT refactor, all tests should PASS.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.backend_path = Path("/Users/anthony/Desktop/netra-apex/netra_backend")
        self.violations = []
        
    def _scan_file_for_jwt_imports(self, file_path: Path) -> List[str]:
        """Scan file for direct JWT library imports (SSOT violation)."""
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for direct JWT imports (should only be in auth service)
            if any(pattern in content for pattern in [
                'import jwt',
                'from jwt import',
                'from PyJWT import',
                'import PyJWT'
            ]):
                violations.append(f"Direct JWT import in {file_path.relative_to(self.backend_path)}")
                
        except Exception as e:
            logger.warning(f"Could not scan {file_path}: {e}")
            
        return violations

    def _scan_file_for_jwt_operations(self, file_path: Path) -> List[str]:
        """Scan file for JWT decode/verify operations (SSOT violation)."""
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for JWT operations (should only be in auth service)
            jwt_operations = [
                'jwt.decode(',
                'jwt.verify(',
                'jwt.encode(',
                'PyJWT.decode(',
                'PyJWT.verify(',
                'PyJWT.encode('
            ]
            
            for operation in jwt_operations:
                if operation in content:
                    violations.append(f"JWT operation '{operation}' in {file_path.relative_to(self.backend_path)}")
                    
        except Exception as e:
            logger.warning(f"Could not scan {file_path}: {e}")
            
        return violations

    def _scan_backend_production_code(self) -> Tuple[List[str], List[str]]:
        """Scan backend production code (not tests) for JWT violations."""
        import_violations = []
        operation_violations = []
        
        # Scan production code directories (excluding tests)
        production_dirs = [
            self.backend_path / "app",
            # Note: excluding tests directory as tests may legitimately use JWT for testing
        ]
        
        for directory in production_dirs:
            if not directory.exists():
                continue
                
            for file_path in directory.rglob("*.py"):
                # Skip __pycache__ and other non-source files
                if "__pycache__" in str(file_path) or file_path.name.startswith("."):
                    continue
                    
                import_violations.extend(self._scan_file_for_jwt_imports(file_path))
                operation_violations.extend(self._scan_file_for_jwt_operations(file_path))
                
        return import_violations, operation_violations

    def test_backend_has_no_direct_jwt_imports(self):
        """
        SSOT Compliance Test: Backend should not import JWT library directly.
        
        EXPECTED: FAIL - Backend currently has direct JWT imports bypassing auth service
        AFTER SSOT: PASS - All JWT operations delegated to auth service
        
        This test scans backend production code for direct JWT imports.
        Only auth service should import JWT library.
        """
        import_violations, _ = self._scan_backend_production_code()
        
        if import_violations:
            violation_summary = "\n".join([f"  - {v}" for v in import_violations])
            logger.error(f"SSOT VIOLATION: Direct JWT imports found in {len(import_violations)} locations:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not import_violations, (
            f"SSOT VIOLATION DETECTED: Found {len(import_violations)} direct JWT imports in backend. "
            f"All JWT operations must be delegated to auth service. Violations:\n{violation_summary}"
        )

    def test_backend_has_no_jwt_decode_operations(self):
        """
        SSOT Compliance Test: Backend should not perform JWT decode operations directly.
        
        EXPECTED: FAIL - Backend currently has jwt.decode() calls bypassing auth service  
        AFTER SSOT: PASS - All JWT decoding delegated to auth service
        
        This test scans backend production code for JWT decode operations.
        Only auth service should decode JWT tokens.
        """
        _, operation_violations = self._scan_backend_production_code()
        
        # Filter for decode/verify operations (encode might be legitimate for test tokens)
        decode_violations = [v for v in operation_violations if any(op in v for op in ['decode', 'verify'])]
        
        if decode_violations:
            violation_summary = "\n".join([f"  - {v}" for v in decode_violations])
            logger.error(f"SSOT VIOLATION: JWT decode operations found in {len(decode_violations)} locations:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not decode_violations, (
            f"SSOT VIOLATION DETECTED: Found {len(decode_violations)} JWT decode operations in backend. "
            f"All JWT validation must be delegated to auth service. Violations:\n{violation_summary}"
        )

    def test_jwt_secret_management_centralization(self):
        """
        SSOT Compliance Test: JWT secrets should only be managed in auth service.
        
        EXPECTED: FAIL - Backend currently manages JWT secrets locally
        AFTER SSOT: PASS - JWT secrets only managed in auth service
        
        This test scans for JWT secret management in backend.
        """
        secret_violations = []
        
        # Scan for JWT secret management patterns
        for file_path in (self.backend_path / "app").rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for JWT secret patterns
                secret_patterns = [
                    'JWT_SECRET',
                    'jwt_secret',
                    'JWT_SECRET_KEY',
                    'jwt_secret_key',
                    'secret.*jwt',
                    'jwt.*secret'
                ]
                
                for pattern in secret_patterns:
                    if pattern.lower() in content.lower():
                        secret_violations.append(f"JWT secret pattern '{pattern}' in {file_path.relative_to(self.backend_path)}")
                        break  # Only report once per file
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        if secret_violations:
            violation_summary = "\n".join([f"  - {v}" for v in secret_violations])
            logger.error(f"SSOT VIOLATION: JWT secret management found in {len(secret_violations)} backend files:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor  
        assert not secret_violations, (
            f"SSOT VIOLATION DETECTED: Found {len(secret_violations)} JWT secret management instances in backend. "
            f"JWT secrets should only be managed in auth service. Violations:\n{violation_summary}"
        )

    def test_websocket_auth_delegates_to_auth_service(self):
        """
        SSOT Compliance Test: WebSocket authentication should delegate to auth service.
        
        EXPECTED: FAIL - WebSocket currently has fallback JWT validation
        AFTER SSOT: PASS - WebSocket delegates all auth to auth service
        
        This test specifically checks WebSocket auth module compliance.
        """
        websocket_auth_violations = []
        websocket_auth_path = self.backend_path / "app" / "websocket_core" / "auth.py"
        
        if websocket_auth_path.exists():
            try:
                with open(websocket_auth_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for local JWT validation patterns in WebSocket auth
                violation_patterns = [
                    'jwt.decode',
                    'jwt.verify',
                    '_decode_token',
                    '_validate_token_locally',
                    'local.*validation',
                    'fallback.*validation',
                    'circuit.*breaker.*open'
                ]
                
                for pattern in violation_patterns:
                    if pattern.lower() in content.lower():
                        websocket_auth_violations.append(f"Local JWT validation pattern '{pattern}' in WebSocket auth")
                        
            except Exception as e:
                logger.warning(f"Could not scan WebSocket auth file: {e}")
        
        if websocket_auth_violations:
            violation_summary = "\n".join([f"  - {v}" for v in websocket_auth_violations])
            logger.error(f"SSOT VIOLATION: WebSocket auth local validation found:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not websocket_auth_violations, (
            f"SSOT VIOLATION DETECTED: WebSocket auth has local JWT validation fallbacks. "
            f"All JWT validation must be delegated to auth service. Violations:\n{violation_summary}"
        )

    def test_no_duplicate_jwt_validation_logic(self):
        """
        SSOT Integration Test: No duplicate JWT validation logic across services.
        
        EXPECTED: FAIL - Multiple JWT validation implementations exist
        AFTER SSOT: PASS - Single JWT validation in auth service only
        
        This test checks for duplicate JWT validation implementations.
        """
        validation_implementations = []
        
        # Scan for JWT validation method patterns
        for file_path in (self.backend_path / "app").rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for validation method patterns
                validation_patterns = [
                    'def.*validate.*jwt',
                    'def.*validate.*token', 
                    'def.*decode.*jwt',
                    'def.*decode.*token',
                    'def.*verify.*jwt',
                    'def.*verify.*token'
                ]
                
                for pattern in validation_patterns:
                    if any(p in content.lower() for p in [pattern.lower()]):
                        validation_implementations.append(f"JWT validation method in {file_path.relative_to(self.backend_path)}")
                        break  # Only report once per file
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        if validation_implementations:
            violation_summary = "\n".join([f"  - {v}" for v in validation_implementations])
            logger.error(f"SSOT VIOLATION: Multiple JWT validation implementations found:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not validation_implementations, (
            f"SSOT VIOLATION DETECTED: Found {len(validation_implementations)} JWT validation implementations in backend. "
            f"Only auth service should implement JWT validation. Violations:\n{violation_summary}"
        )

    def teardown_method(self, method):
        """Clean up after test."""
        super().teardown_method(method)
        if self.violations:
            logger.info(f"JWT SSOT violations detected in {method.__name__}: {len(self.violations)}")