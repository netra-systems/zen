"""
SSOT Import Violation Reproduction Test for DataHelper Agent

This test reproduces the exact SSOT violation identified in Issue #701:
DataHelper agent imports UnifiedToolDispatcher from facade `agents.tool_dispatcher`
instead of SSOT `core.tools.unified_tool_dispatcher`.

EXPECTED BEHAVIOR:
- This test MUST FAIL before the fix (demonstrating the violation)
- This test MUST PASS after the fix (validation fix works)

Business Value: Ensures proper SSOT compliance for mission-critical agent creation
"""

import ast
import inspect
import importlib
import sys
from typing import Dict, List, Set
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

class TestDataHelperSSotImportViolation(SSotBaseTestCase):
    """Test class that reproduces exact SSOT import violation for DataHelper agent."""

    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

        # Define the SSOT import path and facade path
        self.ssot_tool_dispatcher_path = "netra_backend.app.core.tools.unified_tool_dispatcher"
        self.facade_tool_dispatcher_path = "netra_backend.app.agents.tool_dispatcher"

        # DataHelper agent path
        self.data_helper_agent_path = "netra_backend.app.agents.data_helper_agent"

    def test_import_violation_reproduction_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Reproduces exact SSOT import violation.

        This test MUST FAIL before the fix to prove the violation exists.
        This test MUST PASS after the fix to validate remediation works.

        Violation: DataHelper imports UnifiedToolDispatcher from facade instead of SSOT.
        """
        # Get DataHelper agent source code
        data_helper_imports = self._extract_import_statements(self.data_helper_agent_path)

        # Check for facade import (this should NOT exist after fix)
        facade_imports = [
            imp for imp in data_helper_imports
            if 'tool_dispatcher' in imp and 'agents.tool_dispatcher' in imp
        ]

        # Check for SSOT import (this SHOULD exist after fix)
        ssot_imports = [
            imp for imp in data_helper_imports
            if 'tool_dispatcher' in imp and 'core.tools.unified_tool_dispatcher' in imp
        ]

        # CRITICAL ASSERTION: This test MUST fail before fix, pass after fix
        violation_message = (
            f"SSOT VIOLATION: DataHelper agent imports UnifiedToolDispatcher from facade "
            f"'{self.facade_tool_dispatcher_path}' instead of SSOT "
            f"'{self.ssot_tool_dispatcher_path}'. "
            f"Facade imports found: {facade_imports}. "
            f"SSOT imports found: {ssot_imports}. "
            f"This breaks AgentInstanceFactory dependency injection."
        )

        # FAILURE CONDITION: If facade imports exist, this is a violation
        if facade_imports:
            self.fail(violation_message)

        # SUCCESS CONDITION: SSOT imports should exist after fix
        self.assertTrue(
            len(ssot_imports) > 0,
            f"Expected SSOT imports from '{self.ssot_tool_dispatcher_path}' not found. "
            f"DataHelper must import UnifiedToolDispatcher from SSOT path for factory compatibility."
        )

    def test_datahelper_factory_method_compatibility(self):
        """
        Verify DataHelper agent has proper factory method for AgentInstanceFactory.

        This test validates that DataHelper can be created via factory pattern
        without SSOT import violations.
        """
        try:
            # Import DataHelper agent
            module = importlib.import_module(self.data_helper_agent_path)
            DataHelperAgent = getattr(module, 'DataHelperAgent')

            # Verify factory method exists
            self.assertTrue(
                hasattr(DataHelperAgent, 'create_agent_with_context'),
                "DataHelper agent must have create_agent_with_context factory method"
            )

            # Verify factory method signature
            factory_method = getattr(DataHelperAgent, 'create_agent_with_context')
            sig = inspect.signature(factory_method)

            # Should accept UserExecutionContext
            params = list(sig.parameters.keys())
            self.assertIn(
                'user_context', params,
                f"Factory method must accept user_context parameter. Found: {params}"
            )

        except ImportError as e:
            self.fail(f"Cannot import DataHelper agent: {e}")

    def test_agentinstancefactory_dependency_injection_compatibility(self):
        """
        Test that DataHelper agent is compatible with AgentInstanceFactory dependency injection.

        This test verifies the SSOT violation fix enables proper factory creation.
        """
        # Import dependencies
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # Create minimal factory (without WebSocket bridge for unit test)
            factory = AgentInstanceFactory()

            # Check if DataHelper is in supported agent dependencies
            supported_agents = factory.AGENT_DEPENDENCIES.keys()
            self.assertIn(
                'DataHelperAgent', supported_agents,
                f"DataHelper agent must be in factory dependencies. Supported: {list(supported_agents)}"
            )

            # Verify required dependencies for DataHelper
            data_helper_deps = factory.AGENT_DEPENDENCIES.get('DataHelperAgent', [])
            self.assertIn(
                'llm_manager', data_helper_deps,
                f"DataHelper must require llm_manager dependency. Found: {data_helper_deps}"
            )

        except ImportError as e:
            self.fail(f"Cannot import factory dependencies: {e}")

    def test_unified_tool_dispatcher_import_path_validation(self):
        """
        Validate that the SSOT UnifiedToolDispatcher import path is accessible.

        This ensures the fix can actually use the correct SSOT import.
        """
        try:
            # Test SSOT import path
            ssot_module = importlib.import_module(self.ssot_tool_dispatcher_path)
            self.assertTrue(
                hasattr(ssot_module, 'UnifiedToolDispatcher'),
                f"SSOT module {self.ssot_tool_dispatcher_path} must export UnifiedToolDispatcher"
            )

            # Test facade import path (should redirect to SSOT)
            facade_module = importlib.import_module(self.facade_tool_dispatcher_path)
            self.assertTrue(
                hasattr(facade_module, 'UnifiedToolDispatcher'),
                f"Facade module {self.facade_tool_dispatcher_path} must export UnifiedToolDispatcher"
            )

            # Both should reference the same class
            ssot_class = getattr(ssot_module, 'UnifiedToolDispatcher')
            facade_class = getattr(facade_module, 'UnifiedToolDispatcher')

            self.assertEqual(
                ssot_class, facade_class,
                "Facade and SSOT UnifiedToolDispatcher should be the same class"
            )

        except ImportError as e:
            self.fail(f"Import path validation failed: {e}")

    def _extract_import_statements(self, module_path: str) -> List[str]:
        """
        Extract import statements from a Python module.

        Args:
            module_path: Dot-separated module path

        Returns:
            List of import statement strings
        """
        try:
            # Convert module path to file path
            file_path = Path(__file__).parent.parent.parent.parent / "netra_backend" / "app" / "agents" / "data_helper_agent.py"

            if not file_path.exists():
                self.fail(f"DataHelper agent file not found: {file_path}")

            # Read source code
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Parse AST to extract imports
            tree = ast.parse(source_code)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    names = [alias.name for alias in node.names]
                    imports.append(f"from {module} import {', '.join(names)}")

            return imports

        except Exception as e:
            self.fail(f"Failed to extract imports from {module_path}: {e}")

    def teardown_method(self, method):
        """Cleanup test environment."""
        super().teardown_method(method)