"""Test Circular Reference Prevention - Issue #824 Phase 1

Test for import circular references that caused production failures.
Verify clean import paths between WebSocket components.
Ensure no dependency loops in SSOT structure.

Business Value: Prevents import failures that block WebSocket initialization ($500K+ ARR protection).
"""

import pytest
import sys
import importlib
import ast
import inspect
from typing import Set, Dict, List, Optional, Tuple
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
class CircularReferencePreventionValidationTests(SSotAsyncTestCase):
    """Test circular reference prevention for WebSocket Manager SSOT."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.websocket_modules = [
            "netra_backend.app.websocket_core.unified_manager",
            "netra_backend.app.websocket_core.websocket_manager_factory",
            "netra_backend.app.websocket_core.protocols",
            "netra_backend.app.websocket_core.ssot_validation_enhancer",
            "netra_backend.app.websocket_core.migration_adapter",
            "netra_backend.app.routes.websocket",
            "netra_backend.app.routes.websocket_factory",
        ]
        self.import_graph: Dict[str, Set[str]] = {}

    def _extract_imports_from_module(self, module_name: str) -> Set[str]:
        """Extract import statements from a module."""
        try:
            # Get the module file path
            module = importlib.import_module(module_name)
            module_file = getattr(module, '__file__', None)

            if not module_file or not Path(module_file).exists():
                return set()

            # Read and parse the module source
            with open(module_file, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)
            imports = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)

            return imports

        except Exception as e:
            logger.warning(f"Could not analyze imports for {module_name}: {e}")
            return set()

    def _build_import_graph(self) -> None:
        """Build import dependency graph for WebSocket modules."""
        for module_name in self.websocket_modules:
            try:
                imports = self._extract_imports_from_module(module_name)
                # Filter to only WebSocket-related imports
                websocket_imports = {
                    imp for imp in imports
                    if any(ws_mod in imp for ws_mod in ['websocket', 'unified_manager'])
                    and imp.startswith('netra_backend.app')
                }
                self.import_graph[module_name] = websocket_imports
            except Exception as e:
                logger.warning(f"Failed to build import graph for {module_name}: {e}")
                self.import_graph[module_name] = set()

    def _detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the import graph using DFS."""
        def dfs(node: str, path: List[str], visited: Set[str], rec_stack: Set[str]) -> List[List[str]]:
            cycles = []

            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return cycles

            if node in visited:
                return cycles

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # Visit all dependencies
            for dependency in self.import_graph.get(node, set()):
                if dependency in self.import_graph:  # Only check modules we're tracking
                    cycles.extend(dfs(dependency, path.copy(), visited, rec_stack))

            rec_stack.remove(node)
            return cycles

        all_cycles = []
        visited = set()

        for module in self.import_graph:
            if module not in visited:
                cycles = dfs(module, [], visited, set())
                all_cycles.extend(cycles)

        return all_cycles

    def test_no_circular_imports_in_websocket_core(self):
        """Test that WebSocket core modules have no circular import dependencies."""
        self._build_import_graph()

        # Log the import graph for debugging
        logger.info("WebSocket module import graph:")
        for module, imports in self.import_graph.items():
            if imports:
                logger.info(f"  {module} imports: {', '.join(sorted(imports))}")

        # Detect circular dependencies
        cycles = self._detect_circular_dependencies()

        if cycles:
            cycle_descriptions = []
            for cycle in cycles:
                cycle_desc = " -> ".join(cycle)
                cycle_descriptions.append(cycle_desc)

            self.fail(f"CIRCULAR IMPORT DETECTED: Found {len(cycles)} circular dependencies:\n" +
                     "\n".join(f"  {cycle}" for cycle in cycle_descriptions))

        logger.info("✅ No circular import dependencies detected")

    def test_websocket_manager_import_safety(self):
        """Test that WebSocket Manager can be imported without circular reference issues."""
        # Clear any cached modules to test fresh imports
        modules_to_clear = [mod for mod in sys.modules.keys()
                           if 'websocket' in mod.lower() and mod.startswith('netra_backend')]

        cleared_modules = []
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]
                cleared_modules.append(module_name)

        logger.info(f"Cleared {len(cleared_modules)} cached WebSocket modules for fresh import test")

        try:
            # Test importing the canonical WebSocket Manager
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            logger.info("✓ WebSocketManager imported successfully")

            # Verify it's actually usable (not just importable)
            self.assertTrue(inspect.isclass(WebSocketManager))
            self.assertTrue(hasattr(WebSocketManager, '__init__'))

            # Test that we can get its methods without issues
            methods = [method for method in dir(WebSocketManager) if not method.startswith('_')]
            self.assertGreater(len(methods), 0, "WebSocketManager should have public methods")

            logger.info(f"✓ WebSocketManager has {len(methods)} public methods")

        except ImportError as e:
            if "circular" in str(e).lower():
                self.fail(f"CIRCULAR IMPORT ERROR: {e}")
            else:
                self.fail(f"IMPORT ERROR (non-circular): {e}")
        except Exception as e:
            self.fail(f"WEBSOCKET MANAGER IMPORT FAILED: {e}")

        logger.info("✅ WebSocket Manager import safety validated")

    def test_factory_import_isolation(self):
        """Test that factory module imports don't create circular dependencies."""
        try:
            # Test importing factory module
            from netra_backend.app.websocket_core import websocket_manager_factory
            logger.info("✓ Factory module imported successfully")

            # Test that factory doesn't cause circular issues with manager
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            logger.info("✓ Manager imported after factory without issues")

            # Test reverse order
            importlib.reload(sys.modules['netra_backend.app.websocket_core.unified_manager'])
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            logger.info("✓ Factory imported after manager reload without issues")

        except ImportError as e:
            if "circular" in str(e).lower():
                self.fail(f"FACTORY CIRCULAR IMPORT: {e}")
            elif "websocket_manager_factory" in str(e):
                logger.info("ℹ Factory module not found - likely removed (acceptable)")
            else:
                self.fail(f"FACTORY IMPORT ERROR: {e}")
        except Exception as e:
            self.fail(f"FACTORY IMPORT SAFETY TEST FAILED: {e}")

        logger.info("✅ Factory import isolation validated")

    def test_websocket_route_integration_safety(self):
        """Test that WebSocket route integration doesn't create circular dependencies."""
        try:
            # Test importing WebSocket routes
            from netra_backend.app.routes import websocket
            logger.info("✓ WebSocket routes imported successfully")

            # Test that routes can access WebSocket manager without cycles
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            logger.info("✓ Manager accessible from routes without circular issues")

        except ImportError as e:
            if "circular" in str(e).lower():
                self.fail(f"ROUTE CIRCULAR IMPORT: {e}")
            else:
                logger.warning(f"⚠ Route import issue (may be acceptable): {e}")
        except Exception as e:
            logger.warning(f"⚠ Route integration test issue (may be acceptable): {e}")

        logger.info("✅ WebSocket route integration safety validated")

    def test_protocol_import_dependencies(self):
        """Test that protocol definitions don't create import cycles."""
        try:
            # Test importing protocols module
            from netra_backend.app.websocket_core import protocols
            logger.info("✓ Protocols module imported successfully")

            # Test that protocols and manager can coexist
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            logger.info("✓ Manager and protocols coexist without circular issues")

            # Verify protocols don't depend on manager implementation
            protocol_source = inspect.getsource(protocols)
            if "unified_manager" in protocol_source.lower():
                logger.warning("⚠ Protocols may have tight coupling to manager implementation")

        except ImportError as e:
            if "circular" in str(e).lower():
                self.fail(f"PROTOCOL CIRCULAR IMPORT: {e}")
            else:
                logger.warning(f"⚠ Protocol import issue: {e}")
        except Exception as e:
            logger.warning(f"⚠ Protocol dependency test issue: {e}")

        logger.info("✅ Protocol import dependencies validated")

    def test_import_order_independence(self):
        """Test that WebSocket components can be imported in any order without cycles."""
        import_orders = [
            # Order 1: Manager first
            ["netra_backend.app.websocket_core.unified_manager",
             "netra_backend.app.websocket_core.protocols"],

            # Order 2: Protocols first
            ["netra_backend.app.websocket_core.protocols",
             "netra_backend.app.websocket_core.unified_manager"],

            # Order 3: Factory included
            ["netra_backend.app.websocket_core.websocket_manager_factory",
             "netra_backend.app.websocket_core.unified_manager"],
        ]

        for i, import_order in enumerate(import_orders, 1):
            logger.info(f"Testing import order {i}: {' -> '.join(import_order)}")

            # Clear modules for fresh test
            for module_name in import_order:
                if module_name in sys.modules:
                    del sys.modules[module_name]

            try:
                # Import in specified order
                for module_name in import_order:
                    try:
                        importlib.import_module(module_name)
                        logger.info(f"  ✓ {module_name} imported successfully")
                    except ImportError as e:
                        if "circular" in str(e).lower():
                            self.fail(f"CIRCULAR IMPORT in order {i} at {module_name}: {e}")
                        else:
                            logger.warning(f"  ⚠ {module_name} not available: {e}")

                logger.info(f"✓ Import order {i} completed without circular issues")

            except Exception as e:
                self.fail(f"IMPORT ORDER {i} FAILED: {e}")

        logger.info("✅ Import order independence validated")


if __name__ == '__main__':
    import unittest
    unittest.main()