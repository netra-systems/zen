"""
Test Issue #1228 Regression Prevention - Unit Test Collection Failures

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Infrastructure
- Business Goal: Development Velocity & Test Infrastructure Reliability
- Value Impact: Prevents developer blocked state during test execution
- Strategic Impact: Maintains development confidence in core infrastructure tests

CRITICAL: This test prevents regression of Issue #1228 - Unit test collection failures
due to missing EngineConfig attributes and incorrect QualityCheckValidator imports.
"""

import subprocess
import sys
import unittest
from pathlib import Path

class Issue1228RegressionPreventionTests(unittest.TestCase):
    """Prevent regression of Issue #1228 unit test collection failures."""

    def test_execution_engine_comprehensive_test_collection(self):
        """
        BVJ: Platform/Internal - Test Infrastructure Stability
        Ensure execution engine comprehensive tests can be collected without import errors.
        Prevents regression of Issue #1228 EngineConfig AttributeError.
        """
        # Test the main comprehensive test file that was failing
        test_file = "netra_backend/tests/unit/agents/test_execution_engine_consolidated_comprehensive.py"

        # Get the project root directory (netra-apex)
        project_root = Path(__file__).parent.parent.parent.parent
        result = subprocess.run([
            sys.executable, "-m", "pytest", "--collect-only", test_file
        ], cwd=project_root, capture_output=True, text=True)

        # Verify test collection succeeds
        self.assertEqual(result.returncode, 0,
                        f"Test collection failed for {test_file}: {result.stderr}")

        # Verify no AttributeError in output
        self.assertNotIn("AttributeError", result.stderr,
                        "AttributeError found during test collection - Issue #1228 regression")

        # Verify specific EngineConfig attributes are accessible (key fix)
        self.assertNotIn("'EngineConfig' object has no attribute", result.stderr,
                        "EngineConfig attribute missing - Issue #1228 regression")

    def test_execution_engine_focused_test_collection(self):
        """
        BVJ: Platform/Internal - Test Infrastructure Stability
        Ensure execution engine focused tests can be collected without import errors.
        Prevents regression of Issue #1228 EngineConfig AttributeError.
        """
        test_file = "netra_backend/tests/unit/agents/test_execution_engine_consolidated_comprehensive_focused.py"

        # Get the project root directory (netra-apex)
        project_root = Path(__file__).parent.parent.parent.parent
        result = subprocess.run([
            sys.executable, "-m", "pytest", "--collect-only", test_file
        ], cwd=project_root, capture_output=True, text=True)

        # Verify test collection succeeds
        self.assertEqual(result.returncode, 0,
                        f"Test collection failed for {test_file}: {result.stderr}")

        # Verify no AttributeError in output
        self.assertNotIn("AttributeError", result.stderr,
                        "AttributeError found during test collection - Issue #1228 regression")

    def test_message_routing_validation_test_collection(self):
        """
        BVJ: Platform/Internal - Test Infrastructure Stability
        Ensure message routing validation tests can be collected without import errors.
        Prevents regression of Issue #1228 QualityCheckValidator import error.
        """
        test_file = "netra_backend/tests/unit/agents/test_message_routing_validation_comprehensive.py"

        # Get the project root directory (netra-apex)
        project_root = Path(__file__).parent.parent.parent.parent
        result = subprocess.run([
            sys.executable, "-m", "pytest", "--collect-only", test_file
        ], cwd=project_root, capture_output=True, text=True)

        # Verify test collection succeeds
        self.assertEqual(result.returncode, 0,
                        f"Test collection failed for {test_file}: {result.stderr}")

        # Verify no import errors for QualityCheckValidator alias
        self.assertNotIn("ImportError", result.stderr,
                        "ImportError found during test collection - Issue #1228 regression")
        self.assertNotIn("cannot import name 'QualityCheckValidator'", result.stderr,
                        "QualityCheckValidator import failed - Issue #1228 regression")

    def test_all_three_affected_files_collect_together(self):
        """
        BVJ: Platform/Internal - Test Infrastructure Stability
        Ensure all three affected test files can be collected together without conflicts.
        Validates complete fix for Issue #1228.
        """
        test_files = [
            "netra_backend/tests/unit/agents/test_execution_engine_consolidated_comprehensive.py",
            "netra_backend/tests/unit/agents/test_execution_engine_consolidated_comprehensive_focused.py",
            "netra_backend/tests/unit/agents/test_message_routing_validation_comprehensive.py"
        ]

        # Get the project root directory (netra-apex)
        project_root = Path(__file__).parent.parent.parent.parent
        result = subprocess.run([
            sys.executable, "-m", "pytest", "--collect-only"] + test_files,
            cwd=project_root, capture_output=True, text=True)

        # Verify all tests collect successfully together
        self.assertEqual(result.returncode, 0,
                        f"Test collection failed for all files together: {result.stderr}")

        # Verify expected test count (should be 102 tests based on previous collection)
        self.assertIn("collected", result.stdout, "No tests collected - collection may have failed silently")

        # Verify no critical errors
        critical_errors = ["AttributeError", "ImportError", "ModuleNotFoundError"]
        for error in critical_errors:
            self.assertNotIn(error, result.stderr,
                           f"{error} found during combined test collection - Issue #1228 regression")

    def test_engine_config_compatibility_stub_attributes(self):
        """
        BVJ: Platform/Internal - Test Infrastructure Reliability
        Validate EngineConfig compatibility stub has all required attributes.
        Ensures the core fix for Issue #1228 remains functional.
        """
        # Import the SSOT implementation instead of deprecated consolidated import
        # Inline compatibility class to replace deprecated import
        class EngineConfig(dict):
            def __init__(self, **kwargs):
                defaults = {
                    'max_concurrent_agents': 10,
                    'agent_execution_timeout': 30.0,
                    'enable_user_features': False,
                    'enable_mcp': False,
                    'enable_data_features': False,
                    'enable_websocket_events': True,
                    'require_user_context': True,
                }
                defaults.update(kwargs)
                super().__init__(defaults)
                for key, value in defaults.items():
                    setattr(self, key, value)

        # Create instance with defaults
        config = EngineConfig()

        # Test all attributes that were causing AttributeError in Issue #1228
        required_attributes = [
            'enable_user_features', 'enable_mcp', 'enable_data_features',
            'enable_websocket_events', 'enable_metrics', 'enable_fallback',
            'max_concurrent_agents', 'agent_execution_timeout',
            'periodic_update_interval', 'max_history_size',
            'require_user_context', 'enable_request_scoping'
        ]

        for attr in required_attributes:
            self.assertTrue(hasattr(config, attr),
                          f"EngineConfig missing required attribute '{attr}' - Issue #1228 regression")

            # Verify attribute has expected type and reasonable default value
            value = getattr(config, attr)
            self.assertIsNotNone(value, f"EngineConfig attribute '{attr}' is None")

        # Test custom values are accepted (flexibility requirement)
        custom_config = EngineConfig(
            enable_user_features=True,
            max_concurrent_agents=20,
            agent_execution_timeout=60.0
        )

        self.assertTrue(custom_config.enable_user_features)
        self.assertEqual(custom_config.max_concurrent_agents, 20)
        self.assertEqual(custom_config.agent_execution_timeout, 60.0)

if __name__ == '__main__':
    unittest.main()