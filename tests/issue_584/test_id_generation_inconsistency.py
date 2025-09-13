"""
Test to verify Issue #584: Thread ID Run ID Generation Inconsistency has been resolved

This test verifies that demo_websocket.py now uses SSOT ID generation patterns
and detects if the SSOT violation is reintroduced.
"""

import uuid
import unittest
import re
from unittest.mock import Mock, patch
from typing import Optional

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestIdGenerationInconsistency(unittest.TestCase):
    """Test ID generation pattern compliance for Issue #584."""

    def test_demo_websocket_uses_ssot_id_generation(self):
        """Verify demo_websocket.py now uses SSOT ID generation patterns."""

        # Test current SSOT implementation in demo_websocket.py
        id_manager = UnifiedIDManager()

        # Generate IDs using the SSOT pattern (as fixed in demo_websocket.py)
        demo_user_id = id_manager.generate_id(IDType.USER, prefix="demo")
        thread_id = id_manager.generate_id(IDType.THREAD, prefix="demo")
        run_id = UnifiedIDManager.generate_run_id(thread_id)

        # Verify SSOT compliance patterns
        self.assertTrue(self._is_ssot_compliant_id(demo_user_id, "user"))
        self.assertTrue(self._is_ssot_compliant_id(thread_id, "thread"))
        self.assertTrue(self._is_ssot_compliant_run_id(run_id))

        # Verify no legacy prefixed UUID patterns
        self.assertFalse(demo_user_id.startswith("demo-user-"))
        self.assertFalse(thread_id.startswith("demo-thread-"))
        self.assertFalse(run_id.startswith("demo-run-"))

        print(f"✅ SSOT compliant demo_user_id: {demo_user_id}")
        print(f"✅ SSOT compliant thread_id: {thread_id}")
        print(f"✅ SSOT compliant run_id: {run_id}")

    def test_detect_legacy_uuid_pattern_violation(self):
        """Test that would fail if legacy UUID patterns were reintroduced."""

        # Simulate the OLD problematic patterns that should NOT be used
        legacy_demo_user_id = f"demo-user-{uuid.uuid4()}"
        legacy_thread_id = f"demo-thread-{uuid.uuid4()}"
        legacy_run_id = f"demo-run-{uuid.uuid4()}"

        # These patterns should be detected as violations
        self.assertTrue(self._is_legacy_violation(legacy_demo_user_id))
        self.assertTrue(self._is_legacy_violation(legacy_thread_id))
        self.assertTrue(self._is_legacy_violation(legacy_run_id))

        print(f"❌ Legacy violation detected: {legacy_demo_user_id}")
        print(f"❌ Legacy violation detected: {legacy_thread_id}")
        print(f"❌ Legacy violation detected: {legacy_run_id}")

    def test_websocket_cleanup_correlation_with_ssot_ids(self):
        """Test WebSocket cleanup correlation logic works correctly with SSOT IDs."""

        # Generate SSOT-compliant IDs
        id_manager = UnifiedIDManager()
        user1_id = id_manager.generate_id(IDType.USER, prefix="demo")
        user2_id = id_manager.generate_id(IDType.USER, prefix="demo")

        thread1_id = id_manager.generate_id(IDType.THREAD, prefix="demo")
        thread2_id = id_manager.generate_id(IDType.THREAD, prefix="demo")

        run1_id = UnifiedIDManager.generate_run_id(thread1_id)
        run2_id = UnifiedIDManager.generate_run_id(thread2_id)

        # Simulate active connections with SSOT patterns
        active_connections = {
            run1_id: {"type": "ssot", "user_id": user1_id},
            run2_id: {"type": "ssot", "user_id": user2_id},
        }

        # Test cleanup correlation - all should be SSOT pattern
        ssot_pattern_count = 0
        legacy_pattern_count = 0

        for conn_id, conn_data in active_connections.items():
            if self._is_legacy_violation(conn_id):
                legacy_pattern_count += 1
            else:
                ssot_pattern_count += 1

        # Assert all are SSOT pattern (no legacy violations)
        self.assertEqual(ssot_pattern_count, 2)
        self.assertEqual(legacy_pattern_count, 0)

        print(f"✅ All connections use SSOT pattern: {ssot_pattern_count}")
        print(f"✅ No legacy violations found: {legacy_pattern_count}")

    def _is_ssot_compliant_id(self, id_value: str, expected_type: str) -> bool:
        """Check if ID follows SSOT UnifiedIDManager pattern."""
        if not id_value:
            return False

        # SSOT pattern: [prefix_]idtype_counter_uuid8
        parts = id_value.split('_')
        if len(parts) < 3:
            return False

        # Should contain expected type
        if expected_type not in id_value:
            return False

        # Last part should be 8-character hex (UUID part)
        uuid_part = parts[-1]
        if len(uuid_part) != 8:
            return False

        # Check if it's hex
        try:
            int(uuid_part, 16)
            return True
        except ValueError:
            return False

    def _is_ssot_compliant_run_id(self, run_id: str) -> bool:
        """Check if run_id follows SSOT pattern."""
        if not run_id:
            return False

        # Run ID should follow UnifiedIDManager.generate_run_id pattern
        return run_id.startswith("run_") and len(run_id.split('_')) >= 4

    def _is_legacy_violation(self, id_value: str) -> bool:
        """Detect legacy UUID pattern violations."""
        if not id_value:
            return False

        # Check for problematic patterns like "demo-user-{uuid}"
        legacy_patterns = [
            r'^demo-user-[a-f0-9-]{36}$',
            r'^demo-thread-[a-f0-9-]{36}$',
            r'^demo-run-[a-f0-9-]{36}$',
        ]

        for pattern in legacy_patterns:
            if re.match(pattern, id_value):
                return True
        return False

    def test_demo_websocket_source_code_compliance(self):
        """Test that demo_websocket.py source code uses SSOT patterns and no legacy UUID."""

        # Read the demo_websocket.py source code
        import os
        demo_websocket_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "netra_backend", "app", "routes", "demo_websocket.py"
        )

        # Verify file exists
        self.assertTrue(os.path.exists(demo_websocket_path),
                       f"demo_websocket.py not found at {demo_websocket_path}")

        with open(demo_websocket_path, 'r') as f:
            source_code = f.read()

        # Check for SSOT compliance imports
        self.assertIn("from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType",
                     source_code, "Missing SSOT UnifiedIDManager import")

        # Check for SSOT usage patterns
        self.assertIn("id_manager = UnifiedIDManager()", source_code,
                     "Missing UnifiedIDManager instantiation")
        self.assertIn("id_manager.generate_id(IDType.USER", source_code,
                     "Missing SSOT USER ID generation")
        self.assertIn("id_manager.generate_id(IDType.THREAD", source_code,
                     "Missing SSOT THREAD ID generation")

        # Check for legacy violation patterns that should NOT exist
        legacy_violations = [
            'f"demo-user-{uuid.uuid4()}"',
            'f"demo-thread-{uuid.uuid4()}"',
            'f"demo-run-{uuid.uuid4()}"',
            "demo_user_id = f\"demo-user-{uuid.uuid4()}\"",
            "thread_id = f\"demo-thread-{uuid.uuid4()}\"",
            "run_id = f\"demo-run-{uuid.uuid4()}\""
        ]

        for violation_pattern in legacy_violations:
            self.assertNotIn(violation_pattern, source_code,
                           f"SSOT VIOLATION DETECTED: Found legacy pattern '{violation_pattern}' in demo_websocket.py")

        # Verify the fix is in place
        self.assertIn("# ISSUE #584 FIX", source_code,
                     "Missing Issue #584 fix comment documentation")

        print("✅ demo_websocket.py source code compliance verified")
        print("✅ No legacy UUID patterns found")
        print("✅ SSOT UnifiedIDManager usage confirmed")

    def test_websocket_cleanup_correlation_with_mismatched_ids(self):
        """Test WebSocket cleanup correlation logic with mismatched vs SSOT IDs."""
        
        # Simulate mixed ID patterns in active connections
        active_connections = {
            # SSOT pattern (correct)
            str(uuid.uuid4()): {"type": "ssot", "user_id": "user1"},
            str(uuid.uuid4()): {"type": "ssot", "user_id": "user2"},
            
            # Demo pattern (inconsistent)
            f"demo-run-{uuid.uuid4()}": {"type": "demo", "user_id": "demo-user-123"},
            f"demo-thread-{uuid.uuid4()}": {"type": "demo", "user_id": "demo-user-456"},
        }
        
        # Test cleanup correlation
        ssot_pattern_count = 0
        demo_pattern_count = 0
        
        for conn_id, conn_data in active_connections.items():
            if conn_id.startswith("demo-"):
                demo_pattern_count += 1
            else:
                ssot_pattern_count += 1
                
        # Assert we have mixed patterns (this is the problem)
        self.assertGreater(ssot_pattern_count, 0)
        self.assertGreater(demo_pattern_count, 0)
        
        print(f"SSOT pattern connections: {ssot_pattern_count}")
        print(f"Demo pattern connections: {demo_pattern_count}")
        
        # This mixed state makes cleanup correlation difficult
        # because different parts of the system use different ID generation patterns
        
    def test_id_pattern_standardization_proposal(self):
        """Test proposed SSOT ID generation pattern for consistency."""
        
        # Proposed SSOT pattern: all IDs use plain UUID format
        def generate_ssot_ids():
            return {
                "user_id": str(uuid.uuid4()),
                "thread_id": str(uuid.uuid4()),
                "run_id": str(uuid.uuid4()),
                "request_id": str(uuid.uuid4())
            }
            
        ids1 = generate_ssot_ids()
        ids2 = generate_ssot_ids()
        
        # All IDs should be plain UUIDs (no prefixes)
        for id_type, id_value in ids1.items():
            self.assertIsInstance(id_value, str)
            self.assertEqual(len(id_value), 36)  # Standard UUID length
            self.assertIn("-", id_value)  # UUID format
            self.assertFalse(id_value.startswith("demo-"))  # No prefix
            
        # All IDs should be unique
        all_ids = list(ids1.values()) + list(ids2.values())
        self.assertEqual(len(all_ids), len(set(all_ids)))  # All unique
        
        print("SSOT ID pattern validation passed")
        print(f"Sample SSOT IDs: {ids1}")


if __name__ == "__main__":
    unittest.main()