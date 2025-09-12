"""
SSOT WebSocket JWT Consolidation Validation Tests

MISSION CRITICAL: These tests validate SSOT compliance for WebSocket JWT validation.
They are designed to FAIL initially to prove SSOT violations exist, then PASS after consolidation.

SSOT VIOLATION DETECTION:
- Multiple JWT validation paths in UserContextExtractor (VIOLATION)  
- Multiple JWT validation paths in UnifiedWebSocketAuth (VIOLATION)
- Direct JWT decoding bypassing JWTHandler.validate_token() (VIOLATION)

SSOT COMPLIANCE TARGET: 
- ALL JWT validation MUST delegate to auth_service/auth_core/core/jwt_handler.py:JWTHandler.validate_token()
- NO direct jwt.decode() calls outside of SSOT
- NO fallback validation methods
"""

import asyncio
import pytest
import jwt
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketJWTSSOTCompliance(SSotBaseTestCase):
    """
    Tests that validate SSOT compliance for WebSocket JWT validation.
    These tests are designed to FAIL initially to prove violations exist.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMH0.test_signature"
        self.mock_websocket = Mock()
        self.mock_websocket.headers = {"authorization": f"Bearer {self.test_jwt_token}"}

    def test_ssot_violation_detection_user_context_extractor(self):
        """
        TEST DESIGNED TO FAIL: Detect SSOT violations in UserContextExtractor.
        
        This test should FAIL initially because UserContextExtractor has multiple JWT validation paths:
        1. UnifiedAuthInterface validation (SSOT compliant)
        2. auth_client_core fallback validation (SSOT violation)  
        3. Removed but commented _resilient_validation_fallback (SSOT violation evidence)
        4. Removed but commented _legacy_jwt_validation (SSOT violation evidence)
        
        Expected: FAILURE - Multiple validation paths detected
        After Fix: PASS - Single SSOT path only
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        extractor = UserContextExtractor()
        
        # Check for SSOT violations by inspecting the validation method
        validation_method = extractor.validate_and_decode_jwt
        
        # Get the source code to detect multiple validation paths
        import inspect
        source_code = inspect.getsource(validation_method)
        
        # SSOT VIOLATION CHECKS - These should FAIL initially
        ssot_violations_detected = []
        
        # Violation 1: Check for auth_client_core fallback path
        if "auth_client_core" in source_code:
            ssot_violations_detected.append("auth_client_core fallback validation path")
        
        # Violation 2: Check for UnifiedAuthInterface conditional usage
        if "if get_unified_auth:" in source_code:
            ssot_violations_detected.append("conditional UnifiedAuthInterface usage creates dual paths")
        
        # Violation 3: Check for validation result building (fallback pattern)
        if "Build payload from validation result" in source_code:
            ssot_violations_detected.append("fallback payload building indicates dual validation")
        
        # Violation 4: Check for removed method comments (evidence of violations)
        if "SSOT COMPLIANCE:" in source_code and "REMOVED" in source_code:
            ssot_violations_detected.append("commented evidence of removed fallback methods")
        
        # ASSERTION: This should FAIL initially due to SSOT violations
        self.assertEqual(
            len(ssot_violations_detected), 0,
            f"SSOT VIOLATIONS DETECTED in UserContextExtractor: {ssot_violations_detected}. "
            f"All JWT validation must go through single SSOT path: JWTHandler.validate_token()"
        )

    def test_ssot_violation_detection_unified_websocket_auth(self):
        """
        TEST DESIGNED TO FAIL: Detect SSOT violations in UnifiedWebSocketAuth.
        
        This test should FAIL initially because UnifiedWebSocketAuth has multiple code paths:
        1. auth_service remediation path (Issue #372)
        2. SSOT authentication service path  
        3. Demo mode bypass path
        4. E2E context bypass path
        
        Expected: FAILURE - Multiple authentication paths detected
        After Fix: PASS - Single SSOT path only
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        # Get source code to detect multiple authentication paths
        import inspect
        source_code = inspect.getsource(authenticate_websocket_ssot)
        
        # SSOT VIOLATION CHECKS - These should FAIL initially
        ssot_violations_detected = []
        
        # Violation 1: Check for remediation authentication fallback
        if "authenticate_websocket_with_remediation" in source_code:
            ssot_violations_detected.append("remediation authentication path bypasses SSOT")
        
        # Violation 2: Check for legacy authentication fallback
        if "Legacy SSOT authentication fallback" in source_code:
            ssot_violations_detected.append("legacy authentication fallback violates SSOT")
        
        # Violation 3: Check for dual authentication paths
        if "try:" in source_code and "except ImportError:" in source_code:
            ssot_violations_detected.append("import-based dual authentication paths")
        
        # Violation 4: Check for _extract_token_from_websocket (should use SSOT extractor)
        if "_extract_token_from_websocket" in source_code:
            ssot_violations_detected.append("custom token extraction bypasses SSOT UserContextExtractor")
        
        # ASSERTION: This should FAIL initially due to SSOT violations  
        self.assertEqual(
            len(ssot_violations_detected), 0,
            f"SSOT VIOLATIONS DETECTED in UnifiedWebSocketAuth: {ssot_violations_detected}. "
            f"All JWT validation must go through single SSOT path: UnifiedAuthenticationService"
        )

    @pytest.mark.asyncio
    async def test_ssot_violation_jwt_direct_decode_detection(self):
        """
        TEST DESIGNED TO FAIL: Detect direct jwt.decode() calls bypassing SSOT.
        
        This test scans the codebase for direct jwt.decode() usage outside of JWTHandler.
        Direct jwt.decode() calls violate SSOT architecture.
        
        Expected: FAILURE - Direct jwt.decode() calls found outside SSOT
        After Fix: PASS - All jwt.decode() calls consolidated to JWTHandler
        """
        import os
        import re
        from pathlib import Path
        
        # Scan WebSocket core files for direct jwt.decode usage
        websocket_core_path = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "websocket_core"
        
        direct_jwt_decode_violations = []
        
        if websocket_core_path.exists():
            for py_file in websocket_core_path.glob("*.py"):
                if py_file.name in ["__init__.py", "test_*.py"]:
                    continue
                    
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for direct jwt.decode calls
                    jwt_decode_pattern = r'jwt\.decode\s*\('
                    matches = re.finditer(jwt_decode_pattern, content)
                    
                    for match in matches:
                        # Get surrounding context to determine if this is SSOT compliant
                        start_pos = max(0, match.start() - 100)
                        end_pos = min(len(content), match.end() + 100) 
                        context = content[start_pos:end_pos]
                        
                        # Skip if this is in JWTHandler (SSOT allowed)
                        if "JWTHandler" in context or "jwt_handler.py" in str(py_file):
                            continue
                            
                        # Skip if this is a comment or docstring
                        if context.strip().startswith('#') or '"""' in context:
                            continue
                            
                        direct_jwt_decode_violations.append(f"{py_file.name}:{self._get_line_number(content, match.start())}")
                        
                except Exception as e:
                    self.logger.warning(f"Could not scan {py_file}: {e}")
        
        # ASSERTION: This should FAIL initially due to direct jwt.decode() usage
        self.assertEqual(
            len(direct_jwt_decode_violations), 0,
            f"DIRECT JWT.DECODE() VIOLATIONS DETECTED: {direct_jwt_decode_violations}. "
            f"All JWT decoding must use JWTHandler.validate_token() SSOT method"
        )
    
    def test_ssot_enforcement_single_jwt_handler_import(self):
        """
        TEST DESIGNED TO FAIL: Verify all JWT operations import from single SSOT source.
        
        This test ensures that JWT operations only import from the SSOT JWTHandler.
        Multiple JWT import sources violate SSOT architecture.
        
        Expected: FAILURE - Multiple JWT import sources detected
        After Fix: PASS - Single SSOT JWT import source only
        """
        from pathlib import Path
        import ast
        import inspect
        
        # Files to check for JWT imports
        files_to_check = [
            "netra_backend/app/websocket_core/user_context_extractor.py",
            "netra_backend/app/websocket_core/unified_websocket_auth.py"
        ]
        
        jwt_import_violations = []
        
        for file_path in files_to_check:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse AST to find imports
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if "jwt" in alias.name.lower():
                                # Check if this is SSOT compliant import
                                if "auth_service.auth_core" not in alias.name:
                                    jwt_import_violations.append(f"{file_path}:{node.lineno} - {alias.name}")
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and "jwt" in node.module.lower():
                            # Check if this is SSOT compliant import
                            if "auth_service.auth_core" not in node.module:
                                for alias in node.names:
                                    jwt_import_violations.append(f"{file_path}:{node.lineno} - from {node.module} import {alias.name}")
                                    
            except Exception as e:
                self.logger.warning(f"Could not parse {file_path}: {e}")
        
        # ASSERTION: This should FAIL initially due to non-SSOT JWT imports
        self.assertEqual(
            len(jwt_import_violations), 0,
            f"NON-SSOT JWT IMPORT VIOLATIONS DETECTED: {jwt_import_violations}. "
            f"All JWT imports must be from auth_service.auth_core.core.jwt_handler SSOT source"
        )

    def _get_line_number(self, content: str, position: int) -> int:
        """Get line number from character position in content."""
        return content[:position].count('\n') + 1

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])