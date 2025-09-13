"""Compliance tests for Issue #686: Execution Engine SSOT Enforcement.

This test suite enforces SSOT (Single Source of Truth) compliance for execution engines
and prevents regression to multiple execution implementations.

Business Value Justification:
- Segment: Platform/Compliance
- Business Goal: System Integrity & Maintainability
- Value Impact: Prevents Golden Path degradation and ensures system stability
- Strategic Impact: Enforces architectural standards to protect $500K+ ARR functionality

Compliance Enforcement Strategy:
- Prevent new execution engine proliferation
- Enforce UserExecutionEngine as single SSOT
- Validate proper adapter patterns for legacy compatibility
- Ensure execution engine factories create SSOT instances only
- Monitor for architecture drift and violations

CRITICAL: These tests act as guardrails to prevent Issue #686 recurrence.
Any test failures indicate immediate SSOT violation that must be resolved.
"""

import ast
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Set, Type
from unittest import TestCase

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestExecutionEngineSSotEnforcement(SSotBaseTestCase):
    """Compliance tests that enforce execution engine SSOT patterns."""

    def setUp(self):
        """Set up compliance validation fixtures."""
        super().setUp()

        # SSOT Compliance Rules
        self.ssot_execution_engine = "UserExecutionEngine"
        self.ssot_module_path = "netra_backend.app.agents.supervisor.user_execution_engine"

        # Allowed execution engine patterns (STRICT)
        self.allowed_execution_patterns = {
            # Primary SSOT
            "UserExecutionEngine": {
                "type": "ssot_primary",
                "module_path": "netra_backend.app.agents.supervisor.user_execution_engine",
                "required": True
            },

            # Acceptable adapters (MINIMAL SET)
            "SupervisorExecutionEngineAdapter": {
                "type": "adapter",
                "module_path": "netra_backend.app.agents.execution_engine_legacy_adapter",
                "required": False
            },
            "ConsolidatedExecutionEngineWrapper": {
                "type": "adapter",
                "module_path": "netra_backend.app.agents.execution_engine_legacy_adapter",
                "required": False
            },

            # Legacy redirects (TEMPORARY)
            "ExecutionEngine": {
                "type": "legacy_redirect",
                "module_path": "netra_backend.app.agents.supervisor.execution_engine",
                "required": False,
                "must_redirect_to": "UserExecutionEngine"
            },

            # Tool-specific execution (SPECIALIZED)
            "ToolExecutionEngine": {
                "type": "tool_specialized",
                "module_path": "netra_backend.app.agents.tool_dispatcher_execution",
                "required": False,
                "must_delegate_to": "UnifiedToolExecutionEngine"
            },
            "UnifiedToolExecutionEngine": {
                "type": "tool_specialized",
                "module_path": "netra_backend.app.agents.unified_tool_execution",
                "required": False
            }
        }

        # FORBIDDEN patterns (ZERO TOLERANCE)
        self.forbidden_patterns = {
            "duplicate_execution_logic",
            "multiple_primary_engines",
            "shared_state_between_engines",
            "circular_engine_dependencies",
            "engine_without_user_context"
        }

        self.compliance_violations = []

    def test_01_enforce_single_primary_execution_engine_ssot(self):
        """COMPLIANCE ENFORCEMENT: Only one primary execution engine allowed."""

        discovered_engines = self._discover_all_execution_engines()
        primary_engines = []

        for engine_name, engine_info in discovered_engines.items():
            if engine_info.get('type') == 'primary_implementation':
                primary_engines.append(engine_name)

        # STRICT COMPLIANCE: Exactly one primary engine
        self.assertEqual(
            len(primary_engines),
            1,
            f"COMPLIANCE VIOLATION: Found {len(primary_engines)} primary execution engines. "
            f"SSOT requires exactly 1 primary engine. Found: {primary_engines}"
        )

        # Verify the primary is our SSOT target
        if primary_engines:
            self.assertEqual(
                primary_engines[0],
                self.ssot_execution_engine,
                f"COMPLIANCE VIOLATION: Primary execution engine is '{primary_engines[0]}', "
                f"but SSOT requires '{self.ssot_execution_engine}'"
            )

    def test_02_enforce_execution_engine_whitelist_compliance(self):
        """COMPLIANCE ENFORCEMENT: Only whitelisted execution engines allowed."""

        discovered_engines = self._discover_all_execution_engines()
        allowed_engine_names = set(self.allowed_execution_patterns.keys())
        actual_engine_names = set(discovered_engines.keys())

        # Check for unauthorized engines
        unauthorized_engines = actual_engine_names - allowed_engine_names

        self.assertEqual(
            len(unauthorized_engines),
            0,
            f"COMPLIANCE VIOLATION: Found unauthorized execution engines: {unauthorized_engines}. "
            f"Only these engines are allowed: {allowed_engine_names}. "
            f"Remove unauthorized engines or update compliance whitelist."
        )

        # Verify required engines exist
        required_engines = [
            name for name, config in self.allowed_execution_patterns.items()
            if config.get('required', False)
        ]

        missing_required = set(required_engines) - actual_engine_names

        self.assertEqual(
            len(missing_required),
            0,
            f"COMPLIANCE VIOLATION: Required execution engines missing: {missing_required}. "
            f"SSOT requires these engines to exist: {required_engines}"
        )

    def test_03_enforce_legacy_redirect_compliance(self):
        """COMPLIANCE ENFORCEMENT: Legacy engines must redirect to SSOT."""

        discovered_engines = self._discover_all_execution_engines()

        for engine_name, config in self.allowed_execution_patterns.items():
            if config.get('type') != 'legacy_redirect':
                continue

            if engine_name not in discovered_engines:
                continue  # Skip missing legacy engines

            engine_info = discovered_engines[engine_name]
            expected_redirect = config.get('must_redirect_to')

            if not expected_redirect:
                continue

            # Validate redirect implementation
            redirect_valid = self._validate_engine_redirects_to_ssot(
                engine_info, expected_redirect
            )

            self.assertTrue(
                redirect_valid,
                f"COMPLIANCE VIOLATION: Legacy engine '{engine_name}' must redirect to '{expected_redirect}' "
                f"but no valid redirect pattern found in {engine_info.get('file_path')}"
            )

    def test_04_enforce_adapter_pattern_compliance(self):
        """COMPLIANCE ENFORCEMENT: Adapter engines must follow proper patterns."""

        discovered_engines = self._discover_all_execution_engines()

        for engine_name, config in self.allowed_execution_patterns.items():
            if config.get('type') != 'adapter':
                continue

            if engine_name not in discovered_engines:
                continue

            engine_info = discovered_engines[engine_name]

            # Validate adapter implementation
            adapter_valid = self._validate_adapter_pattern(engine_info)

            self.assertTrue(
                adapter_valid,
                f"COMPLIANCE VIOLATION: Adapter engine '{engine_name}' does not follow proper adapter pattern. "
                f"Adapters must delegate to SSOT, not contain duplicate logic. File: {engine_info.get('file_path')}"
            )

    def test_05_enforce_execution_engine_factory_ssot_compliance(self):
        """COMPLIANCE ENFORCEMENT: Factories must create SSOT instances only."""

        factory_classes = self._discover_execution_engine_factories()

        for factory_name, factory_info in factory_classes.items():
            # Validate factory creates SSOT instances
            creates_ssot = self._validate_factory_creates_ssot(factory_info)

            self.assertTrue(
                creates_ssot,
                f"COMPLIANCE VIOLATION: Factory '{factory_name}' does not create SSOT instances. "
                f"All execution engine factories must create {self.ssot_execution_engine} instances. "
                f"File: {factory_info.get('file_path')}"
            )

    def test_06_enforce_forbidden_pattern_detection(self):
        """COMPLIANCE ENFORCEMENT: Detect and prevent forbidden patterns."""

        discovered_engines = self._discover_all_execution_engines()
        detected_violations = []

        for engine_name, engine_info in discovered_engines.items():
            # Check for forbidden patterns
            violations = self._detect_forbidden_patterns(engine_info)
            if violations:
                detected_violations.extend([
                    f"{engine_name}: {violation}" for violation in violations
                ])

        self.assertEqual(
            len(detected_violations),
            0,
            f"COMPLIANCE VIOLATION: Detected forbidden patterns: {detected_violations}. "
            f"These patterns violate SSOT principles and must be removed."
        )

    def test_07_enforce_websocket_integration_ssot_compliance(self):
        """COMPLIANCE ENFORCEMENT: WebSocket integration through SSOT only."""

        engines_with_websocket = self._discover_engines_with_websocket_integration()

        # Allowed WebSocket integration patterns
        allowed_websocket_engines = {
            self.ssot_execution_engine,  # Primary SSOT
            "UnifiedToolExecutionEngine"  # Tool-specific notifications
        }

        unauthorized_websocket_engines = set(engines_with_websocket.keys()) - allowed_websocket_engines

        self.assertEqual(
            len(unauthorized_websocket_engines),
            0,
            f"COMPLIANCE VIOLATION: Unauthorized WebSocket integration in execution engines: {unauthorized_websocket_engines}. "
            f"WebSocket events must be routed through SSOT channels only: {allowed_websocket_engines}"
        )

    def test_08_enforce_user_context_isolation_compliance(self):
        """COMPLIANCE ENFORCEMENT: All execution engines must support user context isolation."""

        discovered_engines = self._discover_all_execution_engines()

        engines_without_user_context = []

        for engine_name, engine_info in discovered_engines.items():
            # Skip legacy redirects and adapters
            config = self.allowed_execution_patterns.get(engine_name, {})
            if config.get('type') in ['legacy_redirect', 'adapter']:
                continue

            # Check for user context support
            has_user_context = self._validate_user_context_support(engine_info)

            if not has_user_context:
                engines_without_user_context.append(engine_name)

        self.assertEqual(
            len(engines_without_user_context),
            0,
            f"COMPLIANCE VIOLATION: Execution engines without user context support: {engines_without_user_context}. "
            f"All execution engines must support proper user isolation through UserExecutionContext."
        )

    def test_09_enforce_no_circular_dependencies_compliance(self):
        """COMPLIANCE ENFORCEMENT: No circular dependencies between execution engines."""

        discovered_engines = self._discover_all_execution_engines()
        dependency_graph = self._build_execution_engine_dependency_graph(discovered_engines)

        circular_dependencies = self._detect_circular_dependencies(dependency_graph)

        self.assertEqual(
            len(circular_dependencies),
            0,
            f"COMPLIANCE VIOLATION: Circular dependencies detected in execution engines: {circular_dependencies}. "
            f"Execution engines must have clean dependency hierarchy with SSOT at the top."
        )

    def test_10_enforce_execution_method_signature_consistency(self):
        """COMPLIANCE ENFORCEMENT: Execution method signatures must be consistent."""

        discovered_engines = self._discover_all_execution_engines()
        signature_violations = []

        # Define expected method signatures for consistency
        expected_signatures = {
            'execute': ['async def execute(', 'def execute('],
            'execute_with_context': ['async def execute_with_context('],
            'execute_tool': ['async def execute_tool('],
        }

        for engine_name, engine_info in discovered_engines.items():
            violations = self._validate_method_signatures(engine_info, expected_signatures)
            if violations:
                signature_violations.extend([
                    f"{engine_name}: {violation}" for violation in violations
                ])

        self.assertEqual(
            len(signature_violations),
            0,
            f"COMPLIANCE VIOLATION: Inconsistent execution method signatures: {signature_violations}. "
            f"All execution engines must maintain consistent method signatures for interoperability."
        )

    # Helper methods for compliance validation

    def _discover_all_execution_engines(self) -> Dict[str, Dict]:
        """Discover all execution engine classes for compliance checking."""
        engines = {}

        # Define search paths
        search_paths = [
            Path("netra_backend/app/agents"),
            Path("netra_backend/app/core"),
            Path("netra_backend/app/services"),
            Path("netra_backend/app/tools")
        ]

        project_root = Path(__file__).parent.parent.parent.parent

        for search_path in search_paths:
            full_path = project_root / search_path
            if not full_path.exists():
                continue

            for py_file in full_path.rglob("*.py"):
                if py_file.name.startswith("test_"):
                    continue

                engines.update(self._extract_execution_engines_from_file(py_file))

        # Classify engines by type
        for engine_name, engine_info in engines.items():
            engines[engine_name]['type'] = self._classify_execution_engine_type(engine_info)

        return engines

    def _extract_execution_engines_from_file(self, py_file: Path) -> Dict[str, Dict]:
        """Extract execution engine classes from a Python file."""
        engines = {}

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST to find execution engine classes
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and 'ExecutionEngine' in node.name:
                    engines[node.name] = {
                        'file_path': str(py_file),
                        'line_number': node.lineno,
                        'class_name': node.name,
                        'source_content': content,
                        'ast_node': node
                    }

        except (IOError, SyntaxError, UnicodeDecodeError):
            pass

        return engines

    def _classify_execution_engine_type(self, engine_info: Dict) -> str:
        """Classify execution engine type for compliance checking."""
        class_name = engine_info['class_name']
        content = engine_info.get('source_content', '')

        # Check for primary implementation
        if class_name == "UserExecutionEngine":
            return 'primary_implementation'

        # Check for adapter pattern
        if 'Adapter' in class_name or 'Wrapper' in class_name:
            return 'adapter'

        # Check for legacy redirect
        if 'import' in content and "UserExecutionEngine" in content:
            return 'legacy_redirect'

        # Check for tool specialization
        if 'Tool' in class_name:
            return 'tool_specialized'

        # Default to unknown (potential violation)
        return 'unknown'

    def _validate_engine_redirects_to_ssot(self, engine_info: Dict, expected_target: str) -> bool:
        """Validate that engine properly redirects to SSOT."""
        content = engine_info.get('source_content', '')

        # Look for import redirect patterns
        redirect_patterns = [
            f'from {self.ssot_module_path} import {expected_target}',
            f'{engine_info["class_name"]} = {expected_target}',
            f'import {expected_target}'
        ]

        return any(pattern in content for pattern in redirect_patterns)

    def _validate_adapter_pattern(self, engine_info: Dict) -> bool:
        """Validate that engine follows proper adapter pattern."""
        content = engine_info.get('source_content', '')

        # Adapter should delegate, not duplicate logic
        delegation_indicators = [
            'self._core_engine',
            'self._delegate',
            'self._wrapped',
            'super()',
            f'{self.ssot_execution_engine}('
        ]

        return any(indicator in content for indicator in delegation_indicators)

    def _discover_execution_engine_factories(self) -> Dict[str, Dict]:
        """Discover execution engine factory classes."""
        factories = {}

        search_paths = [
            Path("netra_backend/app/agents"),
            Path("netra_backend/app/core/managers"),
        ]

        project_root = Path(__file__).parent.parent.parent.parent

        for search_path in search_paths:
            full_path = project_root / search_path
            if not full_path.exists():
                continue

            for py_file in full_path.rglob("*.py"):
                if py_file.name.startswith("test_"):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Look for factory classes
                    if 'ExecutionEngine' in content and 'Factory' in content:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if (isinstance(node, ast.ClassDef) and
                                'ExecutionEngine' in node.name and 'Factory' in node.name):
                                factories[node.name] = {
                                    'file_path': str(py_file),
                                    'line_number': node.lineno,
                                    'class_name': node.name,
                                    'source_content': content
                                }

                except (IOError, SyntaxError, UnicodeDecodeError):
                    continue

        return factories

    def _validate_factory_creates_ssot(self, factory_info: Dict) -> bool:
        """Validate that factory creates SSOT instances."""
        content = factory_info.get('source_content', '')

        # Look for SSOT creation patterns
        ssot_creation_patterns = [
            f'{self.ssot_execution_engine}(',
            f'return {self.ssot_execution_engine}',
            f'from {self.ssot_module_path} import'
        ]

        return any(pattern in content for pattern in ssot_creation_patterns)

    def _detect_forbidden_patterns(self, engine_info: Dict) -> List[str]:
        """Detect forbidden patterns in execution engine."""
        content = engine_info.get('source_content', '')
        violations = []

        # Check for duplicate execution logic
        execution_keywords = ['async def execute', 'def execute', 'await', 'run_agent', 'process_task']
        if sum(1 for keyword in execution_keywords if keyword in content) > 3:
            violations.append('duplicate_execution_logic')

        # Check for shared state patterns
        shared_state_patterns = ['global ', 'class_var', '_instance = ', 'singleton']
        if any(pattern in content for pattern in shared_state_patterns):
            violations.append('shared_state_between_engines')

        return violations

    def _discover_engines_with_websocket_integration(self) -> Dict[str, Dict]:
        """Discover execution engines with WebSocket integration."""
        engines_with_websocket = {}
        discovered_engines = self._discover_all_execution_engines()

        for engine_name, engine_info in discovered_engines.items():
            content = engine_info.get('source_content', '')

            websocket_patterns = [
                'websocket_manager',
                'emit_event',
                'WebSocketManager',
                'send_websocket',
                'websocket_bridge'
            ]

            if any(pattern in content for pattern in websocket_patterns):
                engines_with_websocket[engine_name] = engine_info

        return engines_with_websocket

    def _validate_user_context_support(self, engine_info: Dict) -> bool:
        """Validate that engine supports user context isolation."""
        content = engine_info.get('source_content', '')

        user_context_patterns = [
            'UserExecutionContext',
            'user_context',
            'user_id',
            'session_id',
            'request_id'
        ]

        return any(pattern in content for pattern in user_context_patterns)

    def _build_execution_engine_dependency_graph(self, engines: Dict) -> Dict[str, List[str]]:
        """Build dependency graph for execution engines."""
        graph = {}

        for engine_name, engine_info in engines.items():
            content = engine_info.get('source_content', '')
            dependencies = []

            # Find imports of other execution engines
            for other_engine in engines.keys():
                if other_engine != engine_name and other_engine in content:
                    dependencies.append(other_engine)

            graph[engine_name] = dependencies

        return graph

    def _detect_circular_dependencies(self, graph: Dict[str, List[str]]) -> List[str]:
        """Detect circular dependencies in dependency graph."""
        def has_cycle(node, visited, rec_stack):
            visited[node] = True
            rec_stack[node] = True

            for neighbor in graph.get(node, []):
                if neighbor in graph:  # Only check if neighbor exists
                    if not visited.get(neighbor, False):
                        if has_cycle(neighbor, visited, rec_stack):
                            return True
                    elif rec_stack.get(neighbor, False):
                        return True

            rec_stack[node] = False
            return False

        visited = {}
        rec_stack = {}
        cycles = []

        for node in graph:
            if not visited.get(node, False):
                if has_cycle(node, visited, rec_stack):
                    cycles.append(node)

        return cycles

    def _validate_method_signatures(self, engine_info: Dict, expected_signatures: Dict) -> List[str]:
        """Validate method signatures for consistency."""
        content = engine_info.get('source_content', '')
        violations = []

        for method_name, expected_patterns in expected_signatures.items():
            if method_name in content:
                # Check if any expected pattern is found
                pattern_found = any(pattern in content for pattern in expected_patterns)
                if not pattern_found:
                    violations.append(f"Method '{method_name}' has inconsistent signature")

        return violations


if __name__ == '__main__':
    import unittest
    unittest.main()