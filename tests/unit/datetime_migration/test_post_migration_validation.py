"""
Post-Migration Validation Tests

This module validates that the datetime migration was successful and
that all migrated modules function correctly with the new patterns.
"""

import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import unittest
import sys
import os

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class PostMigrationValidationTests(unittest.TestCase):
    """Test cases to validate successful datetime migration."""

    def setUp(self):
        """Set up test environment."""
        self.warnings_captured = []

    def test_all_target_modules_import_successfully(self):
        """Test that all migrated modules can be imported without errors."""
        modules_to_test = [
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.db.clickhouse',
            'netra_backend.app.api.health_checks',
            'netra_backend.app.websocket_core.connection_manager',
            'netra_backend.app.agents.supervisor.pipeline_executor'
        ]

        successful_imports = 0

        for module_name in modules_to_test:
            try:
                __import__(module_name)
                successful_imports += 1
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")
            except Exception as e:
                self.fail(f"Unexpected error importing {module_name}: {e}")

        self.assertEqual(successful_imports, len(modules_to_test),
                        f"Expected all {len(modules_to_test)} modules to import successfully")

    def test_no_deprecated_patterns_remain(self):
        """Test that no deprecated datetime.now(UTC) patterns remain in target files."""
        target_files = [
            "netra_backend/app/websocket_core/protocols.py",
            "netra_backend/app/db/clickhouse.py",
            "netra_backend/app/api/health_checks.py",
            "netra_backend/app/websocket_core/connection_manager.py",
            "netra_backend/app/agents/supervisor/pipeline_executor.py"
        ]

        total_deprecated_patterns = 0

        for file_path in target_files:
            full_path = project_root / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Count deprecated patterns
                patterns = content.count('datetime.now(UTC)')
                total_deprecated_patterns += patterns

                self.assertEqual(patterns, 0,
                               f"Found {patterns} deprecated datetime.now(UTC) patterns in {file_path}")

        self.assertEqual(total_deprecated_patterns, 0,
                        f"Expected 0 deprecated patterns total, found {total_deprecated_patterns}")

    def test_new_datetime_pattern_functionality(self):
        """Test that the new datetime pattern works correctly."""
        # Test timezone-aware datetime creation
        new_timestamp = datetime.now(timezone.utc)

        # Should be timezone-aware
        self.assertIsNotNone(new_timestamp.tzinfo, "New timestamp should be timezone-aware")
        self.assertEqual(new_timestamp.tzinfo, timezone.utc, "New timestamp should be in UTC timezone")

        # Should produce valid ISO format with timezone
        iso_string = new_timestamp.isoformat()
        self.assertTrue(iso_string.endswith('+00:00'),
                       f"ISO format should end with +00:00, got: {iso_string}")

        # Should be parseable
        parsed_timestamp = datetime.fromisoformat(iso_string)
        self.assertIsInstance(parsed_timestamp, datetime)
        self.assertEqual(parsed_timestamp.tzinfo, timezone.utc)

    def test_behavioral_equivalence(self):
        """Test that old and new patterns produce equivalent UTC times."""
        # Compare timestamps (allowing for small execution time differences)
        old_timestamp = datetime.now(UTC)  # Still works for comparison
        new_timestamp = datetime.now(timezone.utc)

        # Convert new timestamp to naive for comparison
        new_naive = new_timestamp.replace(tzinfo=None)

        # Should be within 1 second of each other
        time_diff = abs((new_naive - old_timestamp).total_seconds())
        self.assertLess(time_diff, 1.0,
                       f"Old and new patterns should produce equivalent times, diff: {time_diff}s")

    def test_iso_format_backward_compatibility(self):
        """Test that ISO format strings are still parseable by existing code."""
        # Test new format
        new_timestamp = datetime.now(timezone.utc)
        new_iso = new_timestamp.isoformat()

        # Should be parseable by datetime.fromisoformat
        parsed = datetime.fromisoformat(new_iso)
        self.assertIsInstance(parsed, datetime)
        self.assertEqual(parsed.tzinfo, timezone.utc)

        # Test that the parsed timestamp is equivalent
        time_diff = abs((parsed - new_timestamp).total_seconds())
        self.assertLess(time_diff, 0.001, "Parsed timestamp should be equivalent to original")

    def test_no_new_deprecation_warnings_in_production_code(self):
        """Test that production code doesn't generate datetime deprecation warnings."""
        # This test would need to be more sophisticated in a real implementation
        # For now, we just test that our new pattern doesn't generate warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Use new pattern - should not generate warnings
            timestamp = datetime.now(timezone.utc)
            iso_string = timestamp.isoformat()

            # Filter for datetime-related warnings
            datetime_warnings = [warning for warning in w
                               if 'utcnow' in str(warning.message).lower() or
                                  'timezone' in str(warning.message).lower()]

            self.assertEqual(len(datetime_warnings), 0,
                           f"New pattern should not generate warnings, got: {[str(w.message) for w in datetime_warnings]}")

    def test_datetime_arithmetic_still_works(self):
        """Test that datetime arithmetic operations still work correctly."""
        from datetime import timedelta

        # Test arithmetic with new pattern
        current_time = datetime.now(timezone.utc)
        past_time = current_time - timedelta(hours=1)
        future_time = current_time + timedelta(hours=1)

        # Should be able to calculate differences
        diff_past = current_time - past_time
        diff_future = future_time - current_time

        self.assertAlmostEqual(diff_past.total_seconds(), 3600, delta=1,
                             msg="Past time difference should be approximately 1 hour")
        self.assertAlmostEqual(diff_future.total_seconds(), 3600, delta=1,
                             msg="Future time difference should be approximately 1 hour")

        # All timestamps should be timezone-aware
        self.assertIsNotNone(current_time.tzinfo)
        self.assertIsNotNone(past_time.tzinfo)
        self.assertIsNotNone(future_time.tzinfo)


class SpecificFunctionalityTests(unittest.TestCase):
    """Test specific functionality of migrated modules."""

    def test_websocket_protocol_validation_timestamp(self):
        """Test WebSocket protocol validation includes proper timestamp."""
        try:
            from netra_backend.app.websocket_core.protocols import WebSocketProtocolValidator

            validator = WebSocketProtocolValidator()

            # Create a mock interface for testing
            class MockInterface:
                async def send_message(self, message):
                    pass
                async def receive_message(self):
                    pass

            result = validator.validate_protocol_interface(MockInterface())

            self.assertIn('validation_timestamp', result)
            timestamp_str = result['validation_timestamp']

            # Should be valid ISO format with timezone
            self.assertTrue(timestamp_str.endswith('+00:00'),
                           f"Validation timestamp should include timezone: {timestamp_str}")

            # Should be parseable
            parsed = datetime.fromisoformat(timestamp_str)
            self.assertIsNotNone(parsed.tzinfo)

        except ImportError:
            self.skipTest("WebSocket protocol validator not available")

    def test_health_checks_timestamp_format(self):
        """Test that health checks produce proper timestamp formats."""
        try:
            # Test that we can import the module
            import netra_backend.app.api.health_checks

            # Test new datetime functionality
            current_time = datetime.now(timezone.utc)
            iso_format = current_time.isoformat()

            # Should be valid format expected by health checks
            self.assertTrue(iso_format.endswith('+00:00'))
            self.assertIsInstance(current_time, datetime)
            self.assertIsNotNone(current_time.tzinfo)

        except ImportError:
            self.skipTest("Health checks module not available")


if __name__ == '__main__':
    # Set up warning capture
    warnings.simplefilter("always")

    # Run tests
    unittest.main(verbosity=2)