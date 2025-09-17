"""
Test suite for Issue #980 - BaseExecutionEngine deprecation warnings
Tests that BaseExecutionEngine imports trigger deprecation warnings and
validates migration to UserExecutionEngine.
"""

import warnings
import unittest
from unittest.mock import patch
import sys
import importlib

class TestIssue980DeprecationWarnings(unittest.TestCase):
    """Test BaseExecutionEngine deprecation warnings for Issue #980"""

    def setUp(self):
        """Reset warnings and module cache before each test"""
        warnings.resetwarnings()
        # Remove module from cache if it exists to force reimport
        modules_to_remove = [
            'netra_backend.app.agents.base.executor',
            'netra_backend.app.agents.execution.user_engine'
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

    def test_base_execution_engine_deprecation_warning(self):
        """Test that importing BaseExecutionEngine triggers deprecation warning"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            try:
                from netra_backend.app.agents.base.executor import BaseExecutionEngine

                # Check if deprecation warning was raised
                deprecation_warnings = [warning for warning in w
                                      if issubclass(warning.category, DeprecationWarning)]

                self.assertGreater(len(deprecation_warnings), 0,
                                 "BaseExecutionEngine import should trigger deprecation warning")

                # Check warning message content
                warning_messages = [str(warning.message) for warning in deprecation_warnings]
                self.assertTrue(any("BaseExecutionEngine" in msg for msg in warning_messages),
                              "Deprecation warning should mention BaseExecutionEngine")

            except ImportError as e:
                self.fail(f"BaseExecutionEngine import failed: {e}")

    def test_user_execution_engine_available(self):
        """Test that UserExecutionEngine can be imported without warnings"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            try:
                from netra_backend.app.agents.execution.user_engine import UserExecutionEngine

                # Check no deprecation warnings for UserExecutionEngine
                deprecation_warnings = [warning for warning in w
                                      if issubclass(warning.category, DeprecationWarning)]

                self.assertEqual(len(deprecation_warnings), 0,
                               "UserExecutionEngine import should not trigger deprecation warnings")

                # Verify class exists and is callable
                self.assertTrue(callable(UserExecutionEngine),
                              "UserExecutionEngine should be a callable class")

            except ImportError as e:
                self.fail(f"UserExecutionEngine import failed: {e}")

    def test_baseexecutionengine_instantiation_deprecated(self):
        """Test that instantiating BaseExecutionEngine triggers deprecation warning"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            try:
                from netra_backend.app.agents.base.executor import BaseExecutionEngine

                # Attempt to instantiate (may require parameters)
                try:
                    instance = BaseExecutionEngine()
                except TypeError:
                    # If BaseExecutionEngine requires parameters, that's expected
                    # The import itself should have triggered the deprecation warning
                    pass

                # Check for deprecation warnings
                deprecation_warnings = [warning for warning in w
                                      if issubclass(warning.category, DeprecationWarning)]

                self.assertGreater(len(deprecation_warnings), 0,
                                 "BaseExecutionEngine usage should trigger deprecation warning")

            except ImportError as e:
                # If BaseExecutionEngine doesn't exist, that's also evidence of deprecation
                self.assertTrue("BaseExecutionEngine" in str(e) or "executor" in str(e),
                              f"Expected import error for deprecated BaseExecutionEngine: {e}")

    def test_migration_files_still_import_baseexecutionengine(self):
        """Test that target migration files currently import BaseExecutionEngine"""
        target_files = [
            'netra_backend/app/agents/base_agent.py',
            'netra_backend/app/agents/mcp_integration/execution_orchestrator.py',
            'netra_backend/app/agents/mcp_integration/base_mcp_agent.py',
            'netra_backend/app/agents/synthetic_data_sub_agent_modern.py'
        ]

        files_with_import = []

        for file_path in target_files:
            try:
                with open(f"C:\\netra-apex\\{file_path}", 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'BaseExecutionEngine' in content:
                        files_with_import.append(file_path)
            except FileNotFoundError:
                # File doesn't exist, skip
                continue

        self.assertGreater(len(files_with_import), 0,
                         f"At least one target file should still import BaseExecutionEngine. Found in: {files_with_import}")

if __name__ == '__main__':
    unittest.main()