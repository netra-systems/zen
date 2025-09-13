"""
Test Suite: ID Generation Inconsistency Reproduction for Issue #584

This test suite reproduces the exact ID generation patterns that cause
thread_id and run_id mismatches, breaking WebSocket cleanup correlation.

Purpose:
- Reproduce legacy UUID patterns from demo_websocket.py
- Validate detection of SSOT vs legacy patterns
- Test ID correlation logic with mismatched formats
- Prove that inconsistent patterns break cleanup logic

Business Impact:
- Ensures WebSocket resource cleanup works correctly
- Validates debugging capabilities through proper ID correlation
- Maintains architectural consistency through SSOT compliance
"""

import uuid
import pytest
from unittest.mock import patch
from typing import Dict, Tuple

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestIDGenerationInconsistency(SSotBaseTestCase):
    """Test suite for reproducing and detecting ID generation inconsistencies."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.id_manager = UnifiedIDManager()

    def setUpMethod(self, method):
        """Set up test environment for pytest compatibility."""
        super().setUp() if hasattr(super(), 'setUp') else None
        self.id_manager = UnifiedIDManager()

    def test_demo_websocket_legacy_uuid_patterns(self):
        """Reproduce legacy UUID pattern that bypasses SSOT.

        This test reproduces the exact pattern from demo_websocket.py lines 37-39
        that causes ID inconsistency warnings in production logs.
        """
        # REPRODUCE: The exact problematic pattern from demo_websocket.py
        demo_user_id = f"demo-user-{uuid.uuid4()}"
        thread_id = f"demo-thread-{uuid.uuid4()}"
        run_id = f"demo-run-{uuid.uuid4()}"

        # VALIDATE: These should be detected as non-SSOT compliant formats
        self.assertFalse(self._is_ssot_compliant_format(demo_user_id))
        self.assertFalse(self._is_ssot_compliant_format(thread_id))
        self.assertFalse(self._is_ssot_compliant_format(run_id))

        # VALIDATE: Pattern detection works correctly
        self.assertTrue(self._is_legacy_uuid_pattern(demo_user_id))
        self.assertTrue(self._is_legacy_uuid_pattern(thread_id))
        self.assertTrue(self._is_legacy_uuid_pattern(run_id))

        # VALIDATE: IDs are unique but inconsistent format
        unique_ids = {demo_user_id, thread_id, run_id}
        self.assertEqual(len(unique_ids), 3, "IDs should be unique")

        # VALIDATE: These patterns will fail correlation logic
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        self.assertNotEqual(extracted_thread_id, thread_id,
                          "Legacy patterns should not correlate properly")

    def test_ssot_vs_legacy_pattern_detection(self):
        """Validate detection of SSOT vs legacy patterns."""

        # Generate IDs using both methods
        # LEGACY METHOD (problematic)
        legacy_thread_id = f"demo-thread-{uuid.uuid4()}"
        legacy_run_id = f"demo-run-{uuid.uuid4()}"

        # SSOT METHOD (correct)
        id_manager = UnifiedIDManager()
        ssot_thread_id = id_manager.generate_id(IDType.THREAD, prefix="demo")
        ssot_run_id = UnifiedIDManager.generate_run_id(ssot_thread_id)

        # EXPECT: Clear distinction between SSOT and legacy formats
        self.assertTrue(self._is_legacy_uuid_pattern(legacy_thread_id))
        self.assertTrue(self._is_legacy_uuid_pattern(legacy_run_id))

        self.assertTrue(self._is_ssot_compliant_format(ssot_thread_id))
        self.assertTrue(self._is_ssot_compliant_format(ssot_run_id))

        # VALIDATE: Pattern classification accuracy
        legacy_patterns = [legacy_thread_id, legacy_run_id]
        ssot_patterns = [ssot_thread_id, ssot_run_id]

        for pattern in legacy_patterns:
            self.assertFalse(self._is_ssot_compliant_format(pattern),
                           f"Legacy pattern {pattern} incorrectly classified as SSOT")

        for pattern in ssot_patterns:
            self.assertFalse(self._is_legacy_uuid_pattern(pattern),
                           f"SSOT pattern {pattern} incorrectly classified as legacy")

    def test_id_correlation_logic_with_mismatched_formats(self):
        """Test ID correlation fails with mismatched formats.

        This test proves that mixing legacy and SSOT patterns breaks
        the correlation logic needed for WebSocket cleanup.
        """
        # Use different generation methods for thread_id and run_id
        legacy_thread_id = f"demo-thread-{uuid.uuid4()}"  # Legacy format
        ssot_run_id = UnifiedIDManager.generate_run_id("demo-base-thread")  # SSOT format

        # EXPECT: Correlation logic to fail gracefully
        extracted_thread_id = UnifiedIDManager.extract_thread_id(ssot_run_id)
        correlation_works = self._test_correlation_logic(extracted_thread_id, legacy_thread_id, ssot_run_id)

        self.assertFalse(correlation_works,
                        "Mixed format IDs should not correlate properly")

        # VALIDATE: Error detection and reporting
        mismatch_detected = self._detect_id_mismatch(ssot_run_id, legacy_thread_id)
        self.assertTrue(mismatch_detected,
                       "ID mismatch should be detected")

    def test_uuid_generation_uniqueness_collision_detection(self):
        """Test UUID generation for uniqueness and collision detection."""

        # Generate multiple IDs using legacy pattern
        legacy_ids = []
        for i in range(100):
            legacy_ids.extend([
                f"demo-user-{uuid.uuid4()}",
                f"demo-thread-{uuid.uuid4()}",
                f"demo-run-{uuid.uuid4()}"
            ])

        # Validate uniqueness
        unique_legacy_ids = set(legacy_ids)
        self.assertEqual(len(legacy_ids), len(unique_legacy_ids),
                        "Legacy UUID generation should produce unique IDs")

        # Generate multiple IDs using SSOT pattern
        id_manager = UnifiedIDManager()
        ssot_ids = []
        for i in range(100):
            thread_id = id_manager.generate_id(IDType.THREAD, prefix="demo")
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            user_id = id_manager.generate_id(IDType.USER, prefix="demo")
            ssot_ids.extend([user_id, thread_id, run_id])

        # Validate uniqueness
        unique_ssot_ids = set(ssot_ids)
        self.assertEqual(len(ssot_ids), len(unique_ssot_ids),
                        "SSOT generation should produce unique IDs")

        # Validate no overlap between legacy and SSOT formats
        overlap = unique_legacy_ids.intersection(unique_ssot_ids)
        self.assertEqual(len(overlap), 0,
                        "Legacy and SSOT patterns should not collide")

    def _is_legacy_uuid_pattern(self, id_value: str) -> bool:
        """Check if ID follows legacy UUID pattern."""
        if not id_value:
            return False

        # Legacy pattern: prefix-{uuid} (like demo-user-{uuid4})
        parts = id_value.split('-')
        if len(parts) < 6:  # UUID has 5 segments, plus prefix makes 6 total
            return False

        # Should start with a meaningful prefix
        if not parts[0] or len(parts[0]) < 3:
            return False

        # Last 5 parts should form a valid UUID when joined
        uuid_part = '-'.join(parts[-5:])
        try:
            uuid.UUID(uuid_part)
            return True
        except ValueError:
            # Also check if the full suffix (excluding first part) is a UUID
            uuid_part = '-'.join(parts[1:])
            try:
                uuid.UUID(uuid_part)
                return True
            except ValueError:
                return False

    def _is_ssot_compliant_format(self, id_value: str) -> bool:
        """Check if ID follows SSOT compliant format."""
        if not id_value:
            return False

        # SSOT pattern: [prefix_]idtype_counter_uuid8
        parts = id_value.split('_')
        if len(parts) < 3:
            return False

        # Last part should be 8-character hex
        uuid_part = parts[-1]
        if len(uuid_part) != 8:
            return False

        try:
            int(uuid_part, 16)  # Should be valid hex
        except ValueError:
            return False

        # Second to last should be numeric counter
        counter_part = parts[-2]
        return counter_part.isdigit()

    def _test_correlation_logic(self, extracted_thread_id: str, actual_thread_id: str, run_id: str) -> bool:
        """Test the correlation logic from user_execution_context.py."""
        # Simulate the validation from UserExecutionContext
        # Pattern 1: UnifiedIdGenerator pattern
        if run_id.startswith(('websocket_factory_', 'context_', 'agent_')):
            return run_id in actual_thread_id and actual_thread_id.startswith('thread_')

        # Pattern 2: UnifiedIDManager pattern
        if extracted_thread_id == actual_thread_id:
            return True

        # Pattern 3: Legacy/fallback patterns
        return False

    def _detect_id_mismatch(self, run_id: str, thread_id: str) -> bool:
        """Detect ID mismatch using similar logic to UserExecutionContext."""
        if not hasattr(UnifiedIDManager, 'extract_thread_id'):
            return False

        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        if not extracted_thread_id:
            return False

        return not self._test_correlation_logic(extracted_thread_id, thread_id, run_id)


class TestSSOTIDManagerCompliance(SSotBaseTestCase):
    """Test suite for SSOT ID Manager compliance validation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.id_manager = UnifiedIDManager()

    def setUpMethod(self, method):
        """Set up test environment for pytest compatibility."""
        super().setUp() if hasattr(super(), 'setUp') else None
        self.id_manager = UnifiedIDManager()

    def test_unified_id_manager_thread_run_correlation(self):
        """Validate SSOT generates correlated IDs."""

        # Use UnifiedIDManager for both thread_id and run_id
        id_manager = UnifiedIDManager()
        thread_id = id_manager.generate_id(IDType.THREAD, prefix="demo")
        run_id = UnifiedIDManager.generate_run_id(thread_id)

        # EXPECT: Correlated, consistent formats
        self.assertTrue(self._validate_ssot_format(thread_id))
        self.assertTrue(self._validate_ssot_format(run_id))

        # VALIDATE: run_id contains thread_id reference
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        self.assertIsNotNone(extracted_thread_id)

        # Validate correlation works
        correlation_valid = self._validate_correlation(extracted_thread_id, thread_id, run_id)
        self.assertTrue(correlation_valid,
                       f"SSOT IDs should correlate: extracted='{extracted_thread_id}', "
                       f"actual='{thread_id}', run_id='{run_id}'")

    def test_unified_id_manager_contract_validation(self):
        """Validate UnifiedIDManager meets all contracts."""

        # Test basic ID generation contracts
        id_manager = UnifiedIDManager()
        user_id = id_manager.generate_id(IDType.USER, prefix="test")
        thread_id = id_manager.generate_id(IDType.THREAD, prefix="test")
        run_id = UnifiedIDManager.generate_run_id(thread_id)

        # EXPECT: All contracts pass
        self.assertTrue(id_manager.is_valid_id(user_id, IDType.USER))
        self.assertTrue(id_manager.is_valid_id(thread_id, IDType.THREAD))

        # VALIDATE: SSOT compliance verified
        self.assertTrue(UnifiedIDManager.validate_run_id(run_id))

        parsed_run_id = UnifiedIDManager.parse_run_id(run_id)
        self.assertTrue(parsed_run_id['valid'])

        # Test contract compliance
        metadata = id_manager.get_id_metadata(user_id)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.id_type, IDType.USER)

    def test_unified_id_generator_compatibility(self):
        """Test compatibility between UnifiedIDManager and UnifiedIdGenerator."""

        # Generate IDs using UnifiedIdGenerator
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids("test_user", "test_op")

        # Validate format compatibility
        self.assertTrue(self._validate_id_format_compatible(thread_id))
        self.assertTrue(self._validate_id_format_compatible(run_id))
        self.assertTrue(self._validate_id_format_compatible(request_id))

        # Test correlation with UnifiedIDManager
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        correlation_valid = self._validate_correlation(extracted_thread_id, thread_id, run_id)

        # Should work with SSOT compatibility bridge
        self.assertTrue(correlation_valid or self._is_compatible_pattern(thread_id, run_id),
                       "UnifiedIdGenerator patterns should be compatible")

    def _validate_ssot_format(self, id_value: str) -> bool:
        """Validate SSOT format compliance."""
        id_manager = UnifiedIDManager()
        return id_manager._validate_structured_format(id_value)

    def _validate_correlation(self, extracted_thread_id: str, actual_thread_id: str, run_id: str) -> bool:
        """Validate ID correlation logic."""
        # Use the same logic as UserExecutionContext._validate_thread_run_id_consistency

        # Pattern 1: UnifiedIdGenerator pattern
        if run_id.startswith(('websocket_factory_', 'context_', 'agent_')):
            return run_id in actual_thread_id and actual_thread_id.startswith('thread_')

        # Pattern 2: UnifiedIDManager pattern
        if extracted_thread_id == actual_thread_id:
            return True

        return False

    def _validate_id_format_compatible(self, id_value: str) -> bool:
        """Validate ID format compatibility."""
        id_manager = UnifiedIDManager()
        return id_manager.is_valid_id_format_compatible(id_value)

    def _is_compatible_pattern(self, thread_id: str, run_id: str) -> bool:
        """Check if patterns are compatible for cleanup."""
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        return UnifiedIdGenerator.ids_match_for_cleanup(thread_id, run_id)


if __name__ == '__main__':
    pytest.main([__file__])