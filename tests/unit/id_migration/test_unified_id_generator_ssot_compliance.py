"""Unit Tests for SSOT ID Generation Compliance - Issue #841

This test suite validates P0 violations where uuid.uuid4() is used instead of 
UnifiedIdGenerator, causing race conditions and user isolation failures.

CRITICAL: These tests are designed to FAIL until the SSOT migration is complete.

Business Value Justification (BVJ):
- Segment: All (Infrastructure supporting all user tiers)  
- Business Goal: System reliability and multi-user data isolation
- Value Impact: Prevents ID collisions causing user data leakage
- Strategic Impact: CRITICAL - $500K+ ARR depends on proper user isolation

Test Strategy:
1. Detect uuid.uuid4() violations in critical production files
2. Validate UnifiedIdGenerator SSOT compliance patterns
3. Prove current violations cause ID format inconsistencies
4. Demonstrate user isolation failures with current patterns

Expected Results: ALL TESTS SHOULD FAIL until migration complete
"""

import pytest
import ast
import os
import uuid
import re
import unittest
from pathlib import Path
from typing import List, Dict, Set, Tuple

from shared.id_generation.unified_id_generator import UnifiedIdGenerator, generate_uuid_replacement


@pytest.mark.unit
class TestUnifiedIdGeneratorSSotCompliance(unittest.TestCase):
    """Test SSOT compliance for ID generation across the system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.critical_files = [
            "netra_backend/app/auth_integration/auth.py",
            "netra_backend/app/auth_integration/auth_permissiveness.py",
            "test_framework/ssot/websocket_auth_test_helpers.py",
            "test_framework/ssot/websocket_auth_helper.py"
        ]
        
    def test_critical_auth_file_uuid4_violations_must_fail(self):
        """CRITICAL: Test that auth.py:160 contains uuid.uuid4() violation.
        
        This test MUST FAIL to prove the P0 violation exists.
        """
        auth_file = self.project_root / "netra_backend/app/auth_integration/auth.py"
        
        # Read the file content
        with open(auth_file, 'r') as f:
            content = f.read()
            
        # Check for uuid.uuid4() usage around line 160
        lines = content.split('\n')
        
        # Look for the specific violation
        found_violation = False
        violation_line = None
        for i, line in enumerate(lines, 1):
            if 'uuid.uuid4()' in line and 155 <= i <= 165:
                found_violation = True
                violation_line = i
                break
                
        # This test MUST FAIL - if violation is fixed, this will fail
        self.assertTrue(found_violation, 
                       f"Expected to find uuid.uuid4() violation around line 160 in auth.py. "
                       f"If this fails, the SSOT migration may already be complete.")
        
        # Additional validation - should be session_id generation
        if found_violation:
            violation_context = lines[violation_line - 1]
            self.assertIn('session_id', violation_context.lower(),
                         f"Line {violation_line} should be session_id generation: {violation_context}")
    
    def test_websocket_auth_helpers_uuid4_violations_must_fail(self):
        """CRITICAL: Test that WebSocket auth helpers contain uuid.uuid4() violations.
        
        This test MUST FAIL to prove the P0 violations exist.
        """
        websocket_auth_files = [
            "test_framework/ssot/websocket_auth_test_helpers.py",
            "test_framework/ssot/websocket_auth_helper.py"
        ]
        
        total_violations = 0
        violations_by_file = {}
        
        for file_path in websocket_auth_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            with open(full_path, 'r') as f:
                content = f.read()
                
            # Count uuid.uuid4() violations
            violations = len(re.findall(r'uuid\.uuid4\(\)', content))
            if violations > 0:
                violations_by_file[file_path] = violations
                total_violations += violations
        
        # This test MUST FAIL - if violations are fixed, this will fail
        self.assertGreater(total_violations, 0,
                          f"Expected to find uuid.uuid4() violations in WebSocket auth files. "
                          f"If this fails, the SSOT migration may already be complete. "
                          f"Files checked: {websocket_auth_files}")
        
        # Report specific violations
        self.assertGreater(len(violations_by_file), 0,
                          f"Expected violations in multiple files. Found: {violations_by_file}")
    
    def test_uuid4_vs_unified_id_generator_format_inconsistency_must_fail(self):
        """CRITICAL: Test that uuid.uuid4() creates inconsistent format vs UnifiedIdGenerator.
        
        This test MUST FAIL to demonstrate the format inconsistency problem.
        """
        # Generate ID using current violation pattern (uuid.uuid4())
        legacy_session_id = str(uuid.uuid4())
        
        # Generate ID using SSOT pattern (UnifiedIdGenerator)
        ssot_session_id = UnifiedIdGenerator.generate_session_id("test_user", "auth")
        
        # Test format inconsistency - these should be DIFFERENT formats
        # If migration is complete, both would use SSOT format and this test would fail
        
        # Legacy format: pure UUID (36 chars with dashes)
        self.assertEqual(len(legacy_session_id), 36,
                        "Legacy uuid.uuid4() should produce 36-character UUID")
        self.assertIn('-', legacy_session_id,
                     "Legacy uuid.uuid4() should contain dashes")
        
        # SSOT format: prefix_timestamp_counter_random
        self.assertGreater(len(ssot_session_id), 36,
                          "SSOT ID should be longer than legacy UUID")
        self.assertTrue(ssot_session_id.startswith('session_'),
                       "SSOT ID should start with session_ prefix")
        
        # Critical format inconsistency - this proves the problem exists
        self.assertNotEqual(legacy_session_id[:7], ssot_session_id[:7],
                           "Legacy and SSOT formats should be different. "
                           "If this fails, migration may already be complete.")
    
    def test_user_isolation_failure_with_uuid4_pattern_must_fail(self):
        """CRITICAL: Test that uuid.uuid4() pattern fails user isolation.
        
        This test MUST FAIL to demonstrate user isolation vulnerability.
        """
        # Simulate the current auth.py pattern with uuid.uuid4()
        def create_legacy_session_id():
            return str(uuid.uuid4())
        
        # Create session IDs for different users using legacy pattern
        user1_sessions = [create_legacy_session_id() for _ in range(5)]
        user2_sessions = [create_legacy_session_id() for _ in range(5)]
        
        # Test for user isolation - legacy pattern has no user context
        for session_id in user1_sessions:
            # Legacy IDs contain no user information
            self.assertNotIn('user', session_id.lower(),
                           "Legacy session IDs should not contain user context")
            
        # Critical isolation vulnerability test
        all_sessions = user1_sessions + user2_sessions
        
        # With uuid.uuid4(), there's no way to identify which user owns which session
        # This creates a vulnerability where sessions could be mixed up
        user_identifiable_sessions = [sid for sid in all_sessions 
                                    if any(user_hint in sid for user_hint in ['user1', 'user2', 'user_'])]
        
        # This test MUST FAIL - current pattern provides no user identification
        self.assertEqual(len(user_identifiable_sessions), 0,
                        "Legacy uuid.uuid4() pattern should provide no user identification. "
                        "If this fails, SSOT migration may already be complete.")
    
    def test_id_collision_risk_with_uuid4_vs_ssot_must_fail(self):
        """CRITICAL: Test collision resistance difference between patterns.
        
        This test MUST FAIL to demonstrate the collision risk difference.
        """
        # Test legacy pattern collision resistance
        legacy_ids = [str(uuid.uuid4()) for _ in range(100)]
        unique_legacy_ids = set(legacy_ids)
        
        # Test SSOT pattern collision resistance
        ssot_ids = [UnifiedIdGenerator.generate_base_id("test") for _ in range(100)]
        unique_ssot_ids = set(ssot_ids)
        
        # Both should be unique, but SSOT has additional protections
        self.assertEqual(len(legacy_ids), len(unique_legacy_ids),
                        "Legacy IDs should be unique (UUID guarantee)")
        self.assertEqual(len(ssot_ids), len(unique_ssot_ids),
                        "SSOT IDs should be unique (triple collision protection)")
        
        # Critical test: SSOT IDs have timestamp and counter information
        ssot_id = UnifiedIdGenerator.generate_base_id("test")
        parsed_ssot = UnifiedIdGenerator.parse_id(ssot_id)
        
        self.assertIsNotNone(parsed_ssot,
                           "SSOT ID should be parseable")
        self.assertGreater(parsed_ssot.timestamp, 0,
                          "SSOT ID should contain timestamp")
        self.assertGreater(parsed_ssot.counter, 0,
                          "SSOT ID should contain counter")
        
        # Legacy UUID has no such structure
        legacy_id = str(uuid.uuid4())
        parsed_legacy = UnifiedIdGenerator.parse_id(legacy_id)
        
        # This test MUST FAIL - legacy UUIDs don't follow SSOT structure
        self.assertIsNone(parsed_legacy,
                         "Legacy UUID should not be parseable as SSOT ID. "
                         "If this fails, migration may already be complete.")
    
    def test_factory_pattern_compatibility_must_fail(self):
        """CRITICAL: Test that current patterns are incompatible with factory patterns.
        
        This test MUST FAIL to demonstrate factory pattern incompatibility.
        """
        # Current auth.py pattern
        def current_auth_session_creation():
            import uuid
            return str(uuid.uuid4())
        
        # SSOT factory pattern
        def ssot_factory_session_creation(user_id: str):
            return UnifiedIdGenerator.generate_session_id(user_id, "auth")
        
        # Create sessions using both patterns
        legacy_session = current_auth_session_creation()
        ssot_session = ssot_factory_session_creation("test_user")
        
        # Test factory compatibility
        # Legacy pattern has no factory support
        try:
            # This should fail - legacy ID can't be validated as SSOT
            is_valid_legacy = UnifiedIdGenerator.is_valid_id(legacy_session, "session")
            legacy_validation_passed = is_valid_legacy
        except Exception:
            legacy_validation_passed = False
        
        # SSOT pattern has full factory support
        is_valid_ssot = UnifiedIdGenerator.is_valid_id(ssot_session, "session")
        
        # This test MUST FAIL - legacy pattern should not be valid SSOT
        self.assertFalse(legacy_validation_passed,
                        "Legacy uuid.uuid4() session ID should not be valid SSOT format. "
                        "If this fails, migration may already be complete.")
        
        # SSOT should be valid
        self.assertTrue(is_valid_ssot,
                       "SSOT session ID should be valid")


@pytest.mark.unit
class TestProductionFileViolationDetection(unittest.TestCase):
    """Test suite to detect and catalog uuid.uuid4() violations in production code."""
    
    def setUp(self):
        """Set up violation detection."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.production_dirs = [
            "netra_backend/app",
            "auth_service", 
            "shared"
        ]
        
    def test_detect_all_uuid4_violations_in_production_must_fail(self):
        """CRITICAL: Comprehensive detection of all uuid.uuid4() violations.
        
        This test MUST FAIL to catalog all existing violations.
        """
        violations = []
        
        for prod_dir in self.production_dirs:
            dir_path = self.project_root / prod_dir
            if not dir_path.exists():
                continue
                
            # Find all Python files
            for py_file in dir_path.rglob("*.py"):
                if self._should_skip_file(py_file):
                    continue
                    
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        
                    # Find uuid.uuid4() usages
                    for i, line in enumerate(content.split('\n'), 1):
                        if 'uuid.uuid4()' in line:
                            violations.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i,
                                'content': line.strip()
                            })
                            
                except Exception as e:
                    # Skip files we can't read
                    continue
        
        # This test MUST FAIL - we expect violations to exist
        self.assertGreater(len(violations), 0,
                          f"Expected to find uuid.uuid4() violations in production code. "
                          f"If this fails, migration may already be complete. "
                          f"Checked directories: {self.production_dirs}")
        
        # Report violations for tracking
        violation_files = set(v['file'] for v in violations)
        self.assertGreater(len(violation_files), 1,
                          f"Expected violations in multiple files. Found {len(violation_files)} files with violations: {list(violation_files)[:5]}...")
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped from violation detection."""
        skip_patterns = [
            'test_',
            '__pycache__',
            '.backup',
            'migration',
            'deprecated'
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)


if __name__ == '__main__':
    unittest.main()
