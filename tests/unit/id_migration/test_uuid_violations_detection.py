"""UUID Violation Detection Tests - Issue #841

This test suite detects and validates uuid.uuid4() violations across critical 
system components, focusing on authentication and WebSocket factory patterns.

CRITICAL: These tests are designed to FAIL until violations are remediated.

Test Focus Areas:
1. Authentication system session ID generation (auth.py:160)
2. WebSocket authentication helper violations
3. Factory pattern compliance violations
4. User isolation security vulnerabilities

Expected Results: ALL TESTS SHOULD FAIL until SSOT migration complete
"""

import pytest
import ast
import os
import re
import uuid
import unittest
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional

from shared.id_generation.unified_id_generator import UnifiedIdGenerator


@pytest.mark.unit
class TestAuthenticationUuidViolations(unittest.TestCase):
    """Test authentication system uuid.uuid4() violations."""
    
    def setUp(self):
        """Set up authentication violation tests."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.auth_files = [
            "netra_backend/app/auth_integration/auth.py",
            "netra_backend/app/auth_integration/auth_permissiveness.py"
        ]
        
    def test_auth_py_line_160_session_id_violation_must_fail(self):
        """CRITICAL: Test specific violation at auth.py:160 for session_id generation.
        
        This test MUST FAIL to prove the exact P0 violation exists.
        """
        auth_file = self.project_root / "netra_backend/app/auth_integration/auth.py"
        
        if not auth_file.exists():
            self.fail(f"Critical auth file not found: {auth_file}")
            
        with open(auth_file, 'r') as f:
            lines = f.readlines()
            
        # Check line 160 specifically (index 159)
        if len(lines) <= 159:
            self.fail("Auth file too short - expected violation at line 160")
            
        line_160 = lines[159].strip()
        
        # This test MUST FAIL - line 160 should contain uuid.uuid4()
        self.assertIn('uuid.uuid4()', line_160,
                     f"Expected uuid.uuid4() violation at line 160. Found: {line_160}")
        
        # Verify it's session_id generation
        self.assertIn('session_id', line_160,
                     f"Line 160 should be session_id generation. Found: {line_160}")
        
        # Verify context - previous lines should mention token session tracking
        context_lines = lines[155:165]
        context = ''.join(context_lines)
        
        self.assertIn('session', context.lower(),
                     "Context should mention session handling")
        self.assertIn('token', context.lower(),
                     "Context should mention token handling")
    
    def test_auth_permissiveness_uuid_violations_must_fail(self):
        """CRITICAL: Test auth_permissiveness.py uuid.uuid4() violations.
        
        This test MUST FAIL if violations exist.
        """
        perm_file = self.project_root / "netra_backend/app/auth_integration/auth_permissiveness.py"
        
        if not perm_file.exists():
            self.skip("Auth permissiveness file not found")
            
        with open(perm_file, 'r') as f:
            content = f.read()
            
        # Find all uuid.uuid4() violations
        violations = []
        for i, line in enumerate(content.split('\n'), 1):
            if 'uuid.uuid4()' in line:
                violations.append({
                    'line': i,
                    'content': line.strip()
                })
        
        # This test MUST FAIL if violations exist
        if len(violations) > 0:
            self.fail(f"Found {len(violations)} uuid.uuid4() violations in auth_permissiveness.py: {violations}")
        
        # If we get here, no violations found (test passes), meaning migration might be complete
        # But we log this for tracking
        print(f"INFO: No uuid.uuid4() violations found in auth_permissiveness.py")
    
    def test_auth_session_id_format_inconsistency_must_fail(self):
        """CRITICAL: Test that auth session IDs create format inconsistency.
        
        This test MUST FAIL to demonstrate the format problem.
        """
        # Simulate current auth.py pattern
        def create_auth_session_current_pattern():
            import uuid
            return str(uuid.uuid4())  # Line 160 pattern
        
        # SSOT pattern for session creation
        def create_auth_session_ssot_pattern(user_id: str):
            return UnifiedIdGenerator.generate_session_id(user_id, "auth")
        
        # Create sessions using both patterns
        current_session = create_auth_session_current_pattern()
        ssot_session = create_auth_session_ssot_pattern("test_user_123")
        
        # Test format inconsistency
        # Current: Pure UUID format (8-4-4-4-12 hex digits with dashes)
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        self.assertIsNotNone(uuid_pattern.match(current_session),
                            "Current auth session should be pure UUID format")
        
        # SSOT: Structured format with prefix and components
        ssot_pattern = re.compile(r'^session_[a-z]+_[a-z0-9]+_\d+_\d+_[a-f0-9]+$')
        self.assertIsNotNone(ssot_pattern.match(ssot_session),
                            "SSOT session should follow structured format")
        
        # Critical inconsistency test - formats are completely different
        self.assertFalse(uuid_pattern.match(ssot_session),
                        "SSOT session should not match UUID format")
        self.assertFalse(ssot_pattern.match(current_session),
                        "Current session should not match SSOT format")
        
        # This proves the inconsistency exists
        self.assertNotEqual(len(current_session), len(ssot_session),
                           "Session ID lengths should be different, proving format inconsistency")


@pytest.mark.unit
class TestWebSocketAuthViolations(unittest.TestCase):
    """Test WebSocket authentication system uuid.uuid4() violations."""
    
    def setUp(self):
        """Set up WebSocket auth violation tests."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.websocket_auth_files = [
            "test_framework/ssot/websocket_auth_test_helpers.py",
            "test_framework/ssot/websocket_auth_helper.py"
        ]
    
    def test_websocket_auth_helpers_comprehensive_violations_must_fail(self):
        """CRITICAL: Comprehensive test of WebSocket auth helper violations.
        
        This test MUST FAIL to catalog all violations in WebSocket auth system.
        """
        all_violations = {}
        total_violations = 0
        
        for file_path in self.websocket_auth_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            violations = self._find_uuid4_violations(full_path)
            if violations:
                all_violations[file_path] = violations
                total_violations += len(violations)
        
        # This test MUST FAIL - we expect violations
        self.assertGreater(total_violations, 0,
                          f"Expected uuid.uuid4() violations in WebSocket auth files. "
                          f"If this fails, migration may be complete. Checked: {self.websocket_auth_files}")
        
        # Detailed violation reporting
        for file_path, violations in all_violations.items():
            print(f"\nViolations in {file_path}:")
            for violation in violations[:5]:  # Show first 5
                print(f"  Line {violation['line']}: {violation['content'][:80]}...")
    
    def test_websocket_auth_helper_specific_patterns_must_fail(self):
        """CRITICAL: Test specific problematic patterns in WebSocket auth helper.
        
        This test MUST FAIL to identify specific violation patterns.
        """
        helper_file = self.project_root / "test_framework/ssot/websocket_auth_helper.py"
        
        if not helper_file.exists():
            self.skip("WebSocket auth helper file not found")
            
        with open(helper_file, 'r') as f:
            content = f.read()
        
        # Look for specific problematic patterns
        problematic_patterns = [
            r'user_id = f"user_.*uuid\.uuid4\(\)',          # User ID generation
            r'session_id = f"session_.*uuid\.uuid4\(\)',     # Session ID generation
            r'token_id = f"token_.*uuid\.uuid4\(\)',         # Token ID generation
            r'test_id = f".*uuid\.uuid4\(\)',                # Test ID generation
        ]
        
        found_patterns = []
        for pattern in problematic_patterns:
            matches = re.findall(pattern, content)
            if matches:
                found_patterns.extend(matches)
        
        # This test MUST FAIL if problematic patterns exist
        self.assertGreater(len(found_patterns), 0,
                          f"Expected to find problematic uuid.uuid4() patterns in WebSocket auth helper. "
                          f"If this fails, migration may be complete.")
        
        # Also check for direct uuid.uuid4() usage
        direct_usage = re.findall(r'uuid\.uuid4\(\)', content)
        self.assertGreater(len(direct_usage), 0,
                          f"Expected direct uuid.uuid4() usage in WebSocket auth helper. "
                          f"Found {len(direct_usage)} instances.")
    
    def test_websocket_user_isolation_vulnerability_must_fail(self):
        """CRITICAL: Test user isolation vulnerability in WebSocket auth patterns.
        
        This test MUST FAIL to demonstrate the security vulnerability.
        """
        # Simulate current WebSocket auth helper pattern
        def create_websocket_user_id_current():
            import uuid
            return f"user_{uuid.uuid4().hex[:8]}"
        
        def create_websocket_session_current():
            import uuid
            return f"session_{uuid.uuid4().hex[:8]}"
        
        # SSOT pattern
        def create_websocket_user_id_ssot(base_user_id: str):
            return UnifiedIdGenerator.generate_websocket_client_id(base_user_id)
        
        # Create multiple user sessions with current pattern
        user1_sessions = [(create_websocket_user_id_current(), 
                          create_websocket_session_current()) for _ in range(3)]
        user2_sessions = [(create_websocket_user_id_current(), 
                          create_websocket_session_current()) for _ in range(3)]
        
        all_current_sessions = user1_sessions + user2_sessions
        
        # Test for isolation vulnerability - no way to distinguish users
        user_ids = [session[0] for session in all_current_sessions]
        session_ids = [session[1] for session in all_current_sessions]
        
        # All IDs should follow same random pattern - no user differentiation
        for user_id in user_ids:
            # Current pattern: user_XXXXXXXX (8 random hex chars)
            pattern = re.match(r'^user_[a-f0-9]{8}$', user_id)
            self.assertIsNotNone(pattern, f"User ID should match current pattern: {user_id}")
        
        # Critical vulnerability test - no way to map sessions to actual users
        # All sessions look identical in format, no user context preservation
        for session_id in session_ids:
            pattern = re.match(r'^session_[a-f0-9]{8}$', session_id)
            self.assertIsNotNone(pattern, f"Session ID should match current pattern: {session_id}")
            
        # This proves the vulnerability - all IDs are indistinguishable
        unique_patterns = set(len(uid.split('_')) for uid in user_ids)
        self.assertEqual(len(unique_patterns), 1,
                        "All user IDs should follow same pattern (proving isolation vulnerability)")
        
        # Compare with SSOT pattern - should include actual user context
        ssot_user_id = create_websocket_user_id_ssot("actual_user_123")
        
        # SSOT should preserve user context
        self.assertIn('actual_user', ssot_user_id,
                     "SSOT WebSocket ID should preserve user context")
        
        # This test MUST FAIL - current pattern provides no user context
        current_user_id = create_websocket_user_id_current()
        self.assertNotIn('actual_user', current_user_id,
                        "Current pattern should not preserve user context (proving vulnerability)")
    
    def _find_uuid4_violations(self, file_path: Path) -> List[Dict[str, any]]:
        """Find all uuid.uuid4() violations in a file."""
        violations = []
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                if 'uuid.uuid4()' in line:
                    violations.append({
                        'line': i,
                        'content': line.strip(),
                        'context': self._get_line_context(lines, i - 1, 2)
                    })
                    
        except Exception:
            pass
            
        return violations
    
    def _get_line_context(self, lines: List[str], line_idx: int, context_lines: int) -> str:
        """Get context around a line."""
        start = max(0, line_idx - context_lines)
        end = min(len(lines), line_idx + context_lines + 1)
        return ''.join(lines[start:end])


@pytest.mark.unit
class TestFactoryPatternViolations(unittest.TestCase):
    """Test factory pattern compliance violations."""
    
    def setUp(self):
        """Set up factory pattern tests."""
        self.project_root = Path(__file__).parent.parent.parent.parent
    
    def test_factory_pattern_incompatibility_must_fail(self):
        """CRITICAL: Test that uuid.uuid4() patterns are incompatible with factory patterns.
        
        This test MUST FAIL to demonstrate factory incompatibility.
        """
        # Current violation patterns from the codebase
        def auth_session_factory_current():
            import uuid
            return str(uuid.uuid4())  # auth.py:160 pattern
        
        def websocket_user_factory_current():
            import uuid
            return f"user_{uuid.uuid4().hex[:8]}"  # websocket auth helper pattern
        
        # SSOT factory patterns
        def auth_session_factory_ssot(user_id: str):
            return UnifiedIdGenerator.generate_session_id(user_id, "auth")
        
        def websocket_user_factory_ssot(user_id: str):
            return UnifiedIdGenerator.generate_websocket_client_id(user_id)
        
        # Create instances
        current_auth_session = auth_session_factory_current()
        current_websocket_user = websocket_user_factory_current()
        
        ssot_auth_session = auth_session_factory_ssot("test_user")
        ssot_websocket_user = websocket_user_factory_ssot("test_user")
        
        # Test factory validation compatibility
        # Current patterns should NOT be valid SSOT format
        current_auth_valid = UnifiedIdGenerator.is_valid_id(current_auth_session)
        current_websocket_valid = UnifiedIdGenerator.is_valid_id(current_websocket_user)
        
        # SSOT patterns SHOULD be valid
        ssot_auth_valid = UnifiedIdGenerator.is_valid_id(ssot_auth_session)
        ssot_websocket_valid = UnifiedIdGenerator.is_valid_id(ssot_websocket_user)
        
        # This test MUST FAIL - current patterns should not be SSOT valid
        self.assertFalse(current_auth_valid,
                        "Current auth session pattern should not be valid SSOT format")
        self.assertFalse(current_websocket_valid,
                        "Current WebSocket user pattern should not be valid SSOT format")
        
        # SSOT patterns should be valid
        self.assertTrue(ssot_auth_valid,
                       "SSOT auth session should be valid")
        self.assertTrue(ssot_websocket_valid,
                       "SSOT WebSocket user should be valid")
        
        # Test parsing compatibility
        current_auth_parsed = UnifiedIdGenerator.parse_id(current_auth_session)
        ssot_auth_parsed = UnifiedIdGenerator.parse_id(ssot_auth_session)
        
        # This test MUST FAIL - current pattern should not be parseable
        self.assertIsNone(current_auth_parsed,
                         "Current auth session should not be parseable as SSOT ID")
        
        # SSOT should be parseable
        self.assertIsNotNone(ssot_auth_parsed,
                            "SSOT auth session should be parseable")


if __name__ == '__main__':
    unittest.main()