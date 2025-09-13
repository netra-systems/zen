"""
UnifiedToolDispatcher SSOT Compliance Test

This test validates proper SSOT import patterns for UnifiedToolDispatcher across
the codebase, specifically focusing on agents that should import from core SSOT
instead of facade patterns.

EXPECTED BEHAVIOR:
- FAIL before fix: Detects facade imports in mission-critical agents
- PASS after fix: All imports use proper SSOT paths

Business Value: Ensures consistent dependency injection patterns for $500K+ ARR agents
"""

import ast
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

class TestUnifiedToolDispatcherSSotCompliance(SSotBaseTestCase):
    """Test proper SSOT import patterns for UnifiedToolDispatcher."""

    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

        # Define SSOT and facade paths
        self.ssot_path = "netra_backend.app.core.tools.unified_tool_dispatcher"
        self.facade_path = "netra_backend.app.agents.tool_dispatcher"

        # Mission-critical agents that must use SSOT imports
        self.critical_agents = [
            "netra_backend.app.agents.data_helper_agent",
            "netra_backend.app.agents.optimizations_core_sub_agent",
            "netra_backend.app.agents.synthetic_data_sub_agent",
            "netra_backend.app.agents.actions_to_meet_goals_sub_agent"
        ]

    def test_datahelper_ssot_import_compliance_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: DataHelper agent imports from facade instead of SSOT.

        Before fix: Facade import detected (violation)
        After fix: SSOT import used (compliance)
        """
        violations = self._scan_agent_import_violations("netra_backend.app.agents.data_helper_agent")

        # Check for specific facade import violation
        facade_violations = [v for v in violations if 'agents.tool_dispatcher' in v['import_statement']]

        if facade_violations:
            violation_details = facade_violations[0]
            self.fail(
                f"SSOT VIOLATION DETECTED: DataHelper agent imports UnifiedToolDispatcher "
                f"from facade path '{self.facade_path}' instead of SSOT path '{self.ssot_path}'. "
                f"Violation: {violation_details['import_statement']} at line {violation_details['line_number']}. "
                f"This breaks AgentInstanceFactory dependency injection patterns."
            )

        # After fix: Verify SSOT import exists
        ssot_imports = [v for v in violations if 'core.tools.unified_tool_dispatcher' in v['import_statement']]
        self.assertTrue(
            len(ssot_imports) > 0 or len(violations) == 0,
            f"DataHelper must import UnifiedToolDispatcher from SSOT path after fix. "
            f"Current imports: {[v['import_statement'] for v in violations]}"
        )

    def test_all_critical_agents_ssot_compliance(self):
        """
        Scan all mission-critical agents for SSOT compliance.

        This test validates that all important agents use proper SSOT imports.
        """
        all_violations = {}

        for agent_module in self.critical_agents:
            violations = self._scan_agent_import_violations(agent_module)
            facade_violations = [v for v in violations if 'agents.tool_dispatcher' in v['import_statement']]

            if facade_violations:
                all_violations[agent_module] = facade_violations

        # Report all violations found
        if all_violations:
            violation_report = []
            for module, violations in all_violations.items():
                for violation in violations:
                    violation_report.append(
                        f"  {module}: {violation['import_statement']} (line {violation['line_number']})"
                    )

            self.fail(
                f"SSOT COMPLIANCE VIOLATIONS DETECTED in critical agents:\n" +
                "\n".join(violation_report) +
                f"\n\nAll agents must import UnifiedToolDispatcher from SSOT path "
                f"'{self.ssot_path}' for proper factory dependency injection."
            )

    def test_tool_dispatcher_factory_pattern_compliance(self):
        """
        Test that agents use proper factory patterns instead of direct imports.

        This validates the recommended pattern for agent creation.
        """
        try:
            from netra_backend.app.agents.data_helper_agent import DataHelperAgent

            # Check if agent uses factory pattern
            self.assertTrue(
                hasattr(DataHelperAgent, 'create_agent_with_context'),
                "DataHelper must have create_agent_with_context factory method for SSOT compliance"
            )

            # Analyze factory method for proper patterns
            factory_method = getattr(DataHelperAgent, 'create_agent_with_context')
            source = inspect.getsource(factory_method)

            # Should use factory pattern, not direct imports
            factory_indicators = [
                'UnifiedToolDispatcherFactory',
                'create_for_user',
                'create_for_request'
            ]

            has_factory_pattern = any(indicator in source for indicator in factory_indicators)
            self.assertTrue(
                has_factory_pattern,
                f"DataHelper factory method should use UnifiedToolDispatcherFactory pattern. "
                f"Source analysis failed to find factory indicators: {factory_indicators}"
            )

        except ImportError as e:
            self.fail(f"Cannot import DataHelper for factory pattern test: {e}")

    def test_ssot_unified_tool_dispatcher_exports(self):
        """
        Validate that SSOT UnifiedToolDispatcher module exports all required components.

        This ensures the SSOT path is complete and usable.
        """
        try:
            # Import SSOT module
            ssot_module = importlib.import_module(self.ssot_path)

            # Required exports for agent compatibility
            required_exports = [
                'UnifiedToolDispatcher',
                'UnifiedToolDispatcherFactory',
                'ToolDispatchRequest',
                'ToolDispatchResponse',
                'create_request_scoped_dispatcher'
            ]

            missing_exports = []
            for export in required_exports:
                if not hasattr(ssot_module, export):
                    missing_exports.append(export)

            self.assertEqual(
                len(missing_exports), 0,
                f"SSOT module {self.ssot_path} missing required exports: {missing_exports}. "
                f"Agents cannot use SSOT imports without these components."
            )

        except ImportError as e:
            self.fail(f"Cannot import SSOT UnifiedToolDispatcher module: {e}")

    def test_facade_to_ssot_redirection_works(self):
        """
        Test that facade properly redirects to SSOT implementation.

        This validates the migration path works correctly.
        """
        try:
            # Import both facade and SSOT
            facade_module = importlib.import_module(self.facade_path)
            ssot_module = importlib.import_module(self.ssot_path)

            # Both should have UnifiedToolDispatcher
            facade_class = getattr(facade_module, 'UnifiedToolDispatcher')
            ssot_class = getattr(ssot_module, 'UnifiedToolDispatcher')

            # Should be the same class (facade redirects to SSOT)
            self.assertEqual(
                facade_class, ssot_class,
                f"Facade UnifiedToolDispatcher should redirect to SSOT implementation. "
                f"Facade: {facade_class}, SSOT: {ssot_class}"
            )

        except ImportError as e:
            self.fail(f"Facade-to-SSOT redirection test failed: {e}")

    def test_agent_import_replacement_validation(self):
        """
        Validate specific import replacement patterns for DataHelper.

        This test checks the exact import statements that need to change.
        """
        # Expected import patterns after fix
        expected_patterns = [
            # Should import from SSOT, not facade
            ('from netra_backend.app.core.tools.unified_tool_dispatcher import', 'REQUIRED'),
            # Facade import should be removed
            ('from netra_backend.app.agents.tool_dispatcher import', 'FORBIDDEN')
        ]

        data_helper_imports = self._extract_all_imports_from_file(
            Path(__file__).parent.parent.parent.parent /
            "netra_backend" / "app" / "agents" / "data_helper_agent.py"
        )

        violations = []

        for pattern, rule_type in expected_patterns:
            matching_imports = [imp for imp in data_helper_imports if pattern in imp]

            if rule_type == 'REQUIRED' and not matching_imports:
                violations.append(f"MISSING REQUIRED: {pattern}")
            elif rule_type == 'FORBIDDEN' and matching_imports:
                violations.append(f"FORBIDDEN IMPORT FOUND: {matching_imports[0]}")

        if violations:
            self.fail(
                f"DataHelper import pattern violations:\n" +
                "\n".join(f"  - {v}" for v in violations) +
                f"\n\nDataHelper must import UnifiedToolDispatcher from SSOT path for factory compatibility."
            )

    def _scan_agent_import_violations(self, module_path: str) -> List[Dict[str, any]]:
        """
        Scan agent module for UnifiedToolDispatcher import violations.

        Args:
            module_path: Dot-separated module path

        Returns:
            List of violation details
        """
        violations = []

        try:
            # Convert module path to file path
            path_parts = module_path.split('.')
            if path_parts[0] == 'netra_backend':
                file_path = Path(__file__).parent.parent.parent.parent
                for part in path_parts:
                    file_path = file_path / part
                file_path = file_path.with_suffix('.py')
            else:
                return violations  # Skip non-netra_backend modules

            if not file_path.exists():
                return violations

            # Read and parse source
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)

            # Find tool dispatcher imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if (node.module and
                        'tool_dispatcher' in node.module and
                        any('UnifiedToolDispatcher' in alias.name for alias in node.names)):
                        violations.append({
                            'import_statement': f"from {node.module} import {', '.join(alias.name for alias in node.names)}",
                            'line_number': node.lineno,
                            'module_path': node.module
                        })

            return violations

        except Exception as e:
            # Return empty list for modules we can't analyze
            return []

    def _extract_all_imports_from_file(self, file_path: Path) -> List[str]:
        """
        Extract all import statements from a file.

        Args:
            file_path: Path to Python file

        Returns:
            List of import statement strings
        """
        try:
            if not file_path.exists():
                return []

            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

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

        except Exception:
            return []

    def teardown_method(self, method):
        """Cleanup test environment."""
        super().teardown_method(method)