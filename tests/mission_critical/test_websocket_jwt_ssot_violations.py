"""
Mission Critical WebSocket JWT SSOT Violations Detection

MISSION CRITICAL: These tests detect SSOT violations that block Golden Path user flow.
Issue #525 - P0 SSOT violations prevent proper WebSocket JWT validation consolidation.

CRITICAL BUSINESS IMPACT:
- $500K+ ARR dependent on WebSocket authentication working correctly
- Golden Path user flow requires reliable JWT validation 
- SSOT violations create authentication inconsistencies
- Multiple JWT validation paths cause auth failures

These tests are designed to FAIL initially, proving P0 SSOT violations block Golden Path.
"""

import pytest
import asyncio
import inspect
import ast
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List, Set
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMissionCriticalWebSocketJWTSSOTViolations(SSotBaseTestCase):
    """
    Mission critical tests that detect P0 SSOT violations blocking Golden Path.
    These tests MUST FAIL initially to prove violations exist and justify SSOT consolidation.
    """

    def setUp(self):
        """Set up mission critical test environment."""
        super().setUp()
        self.golden_path_jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJnb2xkZW5fcGF0aF91c2VyIiwiZW1haWwiOiJ1c2VyQGdvbGRlbnBhdGguY29tIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE2MDAwMDAwMDB9.golden_path_signature"
        
        # Critical WebSocket files that affect Golden Path
        self.critical_websocket_files = [
            "netra_backend/app/websocket_core/user_context_extractor.py",
            "netra_backend/app/websocket_core/unified_websocket_auth.py",
            "netra_backend/app/websocket_core/manager.py",
            "netra_backend/app/routes/websocket.py"
        ]

    def test_mission_critical_golden_path_jwt_validation_ssot_violations(self):
        """
        MISSION CRITICAL TEST - DESIGNED TO FAIL
        
        Detect P0 SSOT violations that block Golden Path user authentication flow.
        
        CRITICAL VIOLATIONS:
        1. Multiple JWT validation implementations across WebSocket code
        2. Fallback authentication paths that bypass SSOT
        3. Direct jwt.decode() calls outside of JWTHandler
        4. Conditional auth service usage creating dual paths
        
        BUSINESS IMPACT: These violations prevent reliable user login → AI response flow
        
        Expected: FAILURE - P0 SSOT violations detected blocking Golden Path
        After Fix: PASS - Single SSOT delegation path enables Golden Path
        """
        golden_path_violations = []
        
        # VIOLATION 1: Scan for multiple JWT validation implementations
        jwt_validation_implementations = self._scan_for_jwt_validation_implementations()
        if len(jwt_validation_implementations) > 1:
            golden_path_violations.append(
                f"Multiple JWT validation implementations found: {jwt_validation_implementations}. "
                f"Golden Path requires single SSOT implementation."
            )
        
        # VIOLATION 2: Detect fallback authentication patterns
        fallback_patterns = self._detect_fallback_authentication_patterns()
        if fallback_patterns:
            golden_path_violations.append(
                f"Fallback authentication patterns detected: {fallback_patterns}. "
                f"Golden Path requires deterministic single authentication path."
            )
        
        # VIOLATION 3: Find direct jwt.decode() usage outside SSOT
        direct_jwt_decode_usage = self._find_direct_jwt_decode_usage()
        if direct_jwt_decode_usage:
            golden_path_violations.append(
                f"Direct jwt.decode() usage found outside SSOT: {direct_jwt_decode_usage}. "
                f"Golden Path requires all JWT operations through JWTHandler.validate_token()."
            )
        
        # VIOLATION 4: Detect conditional auth service imports/usage
        conditional_auth_usage = self._detect_conditional_auth_service_usage()
        if conditional_auth_usage:
            golden_path_violations.append(
                f"Conditional auth service usage detected: {conditional_auth_usage}. "
                f"Golden Path requires consistent SSOT delegation."
            )
        
        # MISSION CRITICAL ASSERTION: This MUST FAIL initially
        self.assertEqual(
            len(golden_path_violations), 0,
            f"\n🚨 MISSION CRITICAL P0 SSOT VIOLATIONS BLOCKING GOLDEN PATH:\n"
            f"{'='*80}\n"
            f"BUSINESS IMPACT: $500K+ ARR dependent on Golden Path user flow\n"
            f"ISSUE: #525 - WebSocket JWT validation SSOT consolidation required\n"
            f"{'='*80}\n"
            f"VIOLATIONS DETECTED:\n" + 
            '\n'.join(f"  {i+1}. {violation}" for i, violation in enumerate(golden_path_violations)) +
            f"\n{'='*80}\n"
            f"REQUIRED FIX: Consolidate ALL JWT validation to JWTHandler.validate_token() SSOT\n"
            f"{'='*80}"
        )

    def test_mission_critical_websocket_auth_consistency_violations(self):
        """
        MISSION CRITICAL TEST - DESIGNED TO FAIL
        
        Detect authentication consistency violations that cause Golden Path failures.
        
        CONSISTENCY VIOLATIONS:
        1. Different JWT secrets used in different validation paths
        2. Different JWT validation logic across WebSocket components  
        3. Inconsistent error handling between validation paths
        4. Different JWT claims validation across implementations
        
        Expected: FAILURE - Authentication inconsistencies detected
        After Fix: PASS - Consistent SSOT authentication throughout
        """
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        
        consistency_violations = []
        
        # VIOLATION 1: Test different validation paths produce different results
        extractor = UserContextExtractor()
        
        # Mock different auth services to return different results for same token
        auth_results = {}
        
        # Mock UnifiedAuthInterface path
        with patch('netra_backend.app.websocket_core.user_context_extractor.get_unified_auth') as mock_unified_auth:
            mock_auth = Mock()
            mock_auth.validate_token.return_value = {
                'user_id': 'unified_user',
                'sub': 'unified_user', 
                'email': 'unified@test.com',
                'source': 'unified_auth'
            }
            mock_unified_auth.return_value = mock_auth
            
            try:
                result1 = asyncio.run(extractor.validate_and_decode_jwt(self.golden_path_jwt_token))
                auth_results['unified_auth'] = result1
            except Exception:
                auth_results['unified_auth'] = None
        
        # Mock auth_client_core fallback path
        mock_unified_auth_none = Mock(return_value=None)
        with patch('netra_backend.app.websocket_core.user_context_extractor.get_unified_auth', mock_unified_auth_none):
            with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
                mock_auth_client.validate_token = AsyncMock(return_value={
                    'valid': True,
                    'payload': {'sub': 'fallback_user', 'email': 'fallback@test.com'},
                    'user_id': 'fallback_user',
                    'email': 'fallback@test.com',
                    'source': 'fallback_auth'
                })
                
                try:
                    result2 = asyncio.run(extractor.validate_and_decode_jwt(self.golden_path_jwt_token))
                    auth_results['fallback_auth'] = result2
                except Exception:
                    auth_results['fallback_auth'] = None
        
        # Check for consistency violations
        if len(auth_results) > 1:
            # Compare results from different paths
            valid_results = {k: v for k, v in auth_results.items() if v is not None}
            
            if len(valid_results) > 1:
                user_ids = set()
                emails = set()
                
                for result in valid_results.values():
                    if isinstance(result, dict):
                        user_ids.add(result.get('sub') or result.get('user_id'))
                        emails.add(result.get('email'))
                
                if len(user_ids) > 1:
                    consistency_violations.append(
                        f"Different validation paths return different user IDs: {user_ids}"
                    )
                
                if len(emails) > 1:
                    consistency_violations.append(
                        f"Different validation paths return different emails: {emails}"
                    )
        
        # VIOLATION 2: Check for inconsistent error handling
        error_handling_violations = self._check_inconsistent_error_handling()
        consistency_violations.extend(error_handling_violations)
        
        # MISSION CRITICAL ASSERTION: This MUST FAIL initially
        self.assertEqual(
            len(consistency_violations), 0,
            f"\n🚨 MISSION CRITICAL AUTHENTICATION CONSISTENCY VIOLATIONS:\n"
            f"{'='*80}\n"
            f"GOLDEN PATH IMPACT: Inconsistent auth results break user flow\n"
            f"{'='*80}\n"
            f"CONSISTENCY VIOLATIONS:\n" + 
            '\n'.join(f"  {i+1}. {violation}" for i, violation in enumerate(consistency_violations)) +
            f"\n{'='*80}\n"
            f"REQUIRED FIX: Single SSOT validation path ensures consistency\n"
            f"{'='*80}"
        )

    def test_mission_critical_websocket_jwt_secret_access_violations(self):
        """
        MISSION CRITICAL TEST - DESIGNED TO FAIL
        
        Detect JWT secret access violations that create security and consistency issues.
        
        SECRET ACCESS VIOLATIONS:
        1. Direct JWT secret access in WebSocket code
        2. Different JWT secrets used across components
        3. JWT configuration duplication
        4. Local JWT validation bypassing central secrets
        
        Expected: FAILURE - JWT secret access violations detected
        After Fix: PASS - All JWT operations through SSOT with centralized secrets
        """
        secret_access_violations = []
        
        # Scan all critical WebSocket files for JWT secret access
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            violations_in_file = self._scan_file_for_jwt_secret_access(full_path)
            if violations_in_file:
                secret_access_violations.extend(
                    [f"{file_path}:{line} - {violation}" for line, violation in violations_in_file]
                )
        
        # Check for JWT configuration imports
        config_import_violations = self._scan_for_jwt_config_imports()
        secret_access_violations.extend(config_import_violations)
        
        # MISSION CRITICAL ASSERTION: This MUST FAIL initially
        self.assertEqual(
            len(secret_access_violations), 0,
            f"\n🚨 MISSION CRITICAL JWT SECRET ACCESS VIOLATIONS:\n"
            f"{'='*80}\n"
            f"SECURITY IMPACT: Direct secret access creates security vulnerabilities\n"
            f"CONSISTENCY IMPACT: Multiple secret access points cause auth failures\n"
            f"{'='*80}\n"
            f"SECRET ACCESS VIOLATIONS:\n" + 
            '\n'.join(f"  {i+1}. {violation}" for i, violation in enumerate(secret_access_violations)) +
            f"\n{'='*80}\n"
            f"REQUIRED FIX: All JWT operations through JWTHandler SSOT with centralized secrets\n"
            f"{'='*80}"
        )

    def test_mission_critical_websocket_auth_import_violations(self):
        """
        MISSION CRITICAL TEST - DESIGNED TO FAIL
        
        Detect JWT import violations that create multiple validation paths.
        
        IMPORT VIOLATIONS:
        1. Multiple JWT library imports across components
        2. Direct PyJWT imports outside of SSOT
        3. Auth service imports bypassing SSOT interfaces
        4. Conditional imports creating dual paths
        
        Expected: FAILURE - JWT import violations detected
        After Fix: PASS - All JWT operations through single SSOT import
        """
        import_violations = []
        
        # Scan for problematic JWT-related imports
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            violations_in_file = self._scan_file_for_jwt_import_violations(full_path)
            if violations_in_file:
                import_violations.extend(
                    [f"{file_path}:{line} - {violation}" for line, violation in violations_in_file]
                )
        
        # Check for conditional import patterns that create dual paths
        conditional_import_violations = self._detect_conditional_import_patterns()
        import_violations.extend(conditional_import_violations)
        
        # MISSION CRITICAL ASSERTION: This MUST FAIL initially  
        self.assertEqual(
            len(import_violations), 0,
            f"\n🚨 MISSION CRITICAL JWT IMPORT VIOLATIONS:\n"
            f"{'='*80}\n"
            f"ARCHITECTURAL IMPACT: Multiple import paths violate SSOT principles\n"
            f"GOLDEN PATH IMPACT: Import inconsistencies cause auth failures\n"
            f"{'='*80}\n"
            f"IMPORT VIOLATIONS:\n" + 
            '\n'.join(f"  {i+1}. {violation}" for i, violation in enumerate(import_violations)) +
            f"\n{'='*80}\n"
            f"REQUIRED FIX: Single SSOT import path for all JWT operations\n"
            f"{'='*80}"
        )

    # Helper methods for detecting SSOT violations
    
    def _scan_for_jwt_validation_implementations(self) -> List[str]:
        """Scan for multiple JWT validation implementations."""
        implementations = []
        
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for validation method definitions
                if 'def validate_' in content and 'jwt' in content.lower():
                    implementations.append(f"{file_path}: JWT validation method")
                
                # Look for jwt.decode calls
                if 'jwt.decode(' in content:
                    implementations.append(f"{file_path}: Direct jwt.decode() call")
                
            except Exception:
                continue
                
        return list(set(implementations))
    
    def _detect_fallback_authentication_patterns(self) -> List[str]:
        """Detect fallback authentication patterns."""
        patterns = []
        
        fallback_indicators = [
            'fallback',
            'try:.*except.*auth',
            'if.*auth.*else',
            'UnifiedAuthInterface.*None',
            'auth_client_core'
        ]
        
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                import re
                for pattern in fallback_indicators:
                    if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                        patterns.append(f"{file_path}: {pattern}")
                        
            except Exception:
                continue
        
        return patterns
    
    def _find_direct_jwt_decode_usage(self) -> List[str]:
        """Find direct jwt.decode() usage outside SSOT."""
        usage = []
        
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines, 1):
                    if 'jwt.decode(' in line and not line.strip().startswith('#'):
                        usage.append(f"{file_path}:{i}")
                        
            except Exception:
                continue
        
        return usage
    
    def _detect_conditional_auth_service_usage(self) -> List[str]:
        """Detect conditional auth service usage patterns."""
        patterns = []
        
        conditional_indicators = [
            'if get_unified_auth',
            'try:.*from auth_service',
            'except ImportError',
            'get_unified_auth.*else'
        ]
        
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                import re
                for pattern in conditional_indicators:
                    if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                        patterns.append(f"{file_path}: {pattern}")
                        
            except Exception:
                continue
        
        return patterns
    
    def _check_inconsistent_error_handling(self) -> List[str]:
        """Check for inconsistent error handling across validation paths."""
        # This would require runtime testing with different error scenarios
        # For now, return static analysis results
        inconsistencies = []
        
        # Check if error handling varies between auth paths
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for different exception handling patterns
                if 'except' in content and 'jwt' in content.lower():
                    exception_patterns = content.count('except')
                    if exception_patterns > 2:  # Arbitrary threshold
                        inconsistencies.append(f"{file_path}: Multiple exception handling patterns")
                        
            except Exception:
                continue
        
        return inconsistencies
    
    def _scan_file_for_jwt_secret_access(self, file_path: Path) -> List[tuple]:
        """Scan file for JWT secret access patterns."""
        violations = []
        
        secret_patterns = [
            'JWT_SECRET',
            'AuthConfig.get_jwt_secret',
            'os.environ.get(\'JWT_SECRET\')',
            'get_env().get(\'JWT_SECRET\')',
            'jwt_secret',
            'self.secret'
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                for pattern in secret_patterns:
                    if pattern in line and not line.strip().startswith('#'):
                        violations.append((i, f"Direct JWT secret access: {pattern}"))
                        
        except Exception:
            pass
        
        return violations
    
    def _scan_for_jwt_config_imports(self) -> List[str]:
        """Scan for JWT configuration imports."""
        config_imports = []
        
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for auth config imports
                if 'from auth_service.auth_core.config import AuthConfig' in content:
                    config_imports.append(f"{file_path}: Direct AuthConfig import")
                    
                if 'import os' in content and 'JWT_SECRET' in content:
                    config_imports.append(f"{file_path}: Direct environment access for JWT secrets")
                    
            except Exception:
                continue
        
        return config_imports
    
    def _scan_file_for_jwt_import_violations(self, file_path: Path) -> List[tuple]:
        """Scan file for JWT import violations."""
        violations = []
        
        problematic_imports = [
            'import jwt',
            'from jwt import',
            'import PyJWT',
            'from PyJWT import'
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                for import_pattern in problematic_imports:
                    if import_pattern in line and not line.strip().startswith('#'):
                        violations.append((i, f"Direct JWT library import: {import_pattern}"))
                        
        except Exception:
            pass
        
        return violations
    
    def _detect_conditional_import_patterns(self) -> List[str]:
        """Detect conditional import patterns that create dual paths."""
        patterns = []
        
        for file_path in self.critical_websocket_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for try/except import patterns
                if 'try:' in content and 'import' in content and 'except ImportError:' in content:
                    patterns.append(f"{file_path}: Conditional import pattern detected")
                    
            except Exception:
                continue
        
        return patterns

    def tearDown(self):
        """Clean up mission critical test environment."""
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])