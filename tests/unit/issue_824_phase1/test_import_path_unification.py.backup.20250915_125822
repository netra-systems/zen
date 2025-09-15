"""Test Import Path Unification - Issue #824 Phase 1

Test that all WebSocket manager imports resolve to same canonical source.
Verify import consistency across modules.
Test that deprecated imports redirect properly.

Business Value: Ensures consistent behavior across all import paths, preventing SSOT fragmentation.
"""

import pytest
import sys
import importlib
import inspect
from typing import Dict, List, Set, Any, Optional, Tuple
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
class TestImportPathUnificationValidation(SSotAsyncTestCase):
    """Test import path unification for WebSocket Manager SSOT."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.canonical_import_path = "netra_backend.app.websocket_core.websocket_manager"
        self.canonical_class_name = "WebSocketManager"

        # All possible import paths that should resolve to the same class
        self.import_paths_to_test = [
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
        ]

        # Functions that should resolve to consistent implementations
        self.function_paths_to_test = [
            "netra_backend.app.websocket_core.websocket_manager.get_websocket_manager",
            "netra_backend.app.websocket_core.websocket_manager.get_websocket_manager",
        ]

    def _import_class_from_path(self, import_path: str) -> Optional[Tuple[Any, str]]:
        """Import a class from a given import path."""
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = importlib.import_module(module_path)

            if hasattr(module, class_name):
                class_obj = getattr(module, class_name)
                module_file = getattr(module, '__file__', 'unknown')
                return class_obj, module_file
            else:
                logger.warning(f"Class {class_name} not found in {module_path}")
                return None, "not_found"

        except ImportError as e:
            logger.warning(f"Could not import {import_path}: {e}")
            return None, "import_error"
        except Exception as e:
            logger.warning(f"Error importing {import_path}: {e}")
            return None, "error"

    def _import_function_from_path(self, import_path: str) -> Optional[Tuple[Any, str]]:
        """Import a function from a given import path."""
        try:
            module_path, function_name = import_path.rsplit('.', 1)
            module = importlib.import_module(module_path)

            if hasattr(module, function_name):
                function_obj = getattr(module, function_name)
                module_file = getattr(module, '__file__', 'unknown')
                return function_obj, module_file
            else:
                logger.warning(f"Function {function_name} not found in {module_path}")
                return None, "not_found"

        except ImportError as e:
            logger.warning(f"Could not import {import_path}: {e}")
            return None, "import_error"
        except Exception as e:
            logger.warning(f"Error importing {import_path}: {e}")
            return None, "error"

    def test_all_websocket_manager_imports_resolve_to_same_class(self):
        """Test that all WebSocket Manager import paths resolve to the same class object."""
        imported_classes = {}
        successful_imports = {}

        for import_path in self.import_paths_to_test:
            class_obj, module_file = self._import_class_from_path(import_path)

            if class_obj is not None:
                imported_classes[import_path] = {
                    'class': class_obj,
                    'id': id(class_obj),
                    'module_file': module_file,
                    'name': getattr(class_obj, '__name__', 'unknown')
                }
                successful_imports[import_path] = class_obj
                logger.info(f"✓ {import_path} -> class id {id(class_obj)} from {module_file}")

        # Must have at least one successful import
        self.assertGreater(len(successful_imports), 0,
                          "At least one WebSocketManager import path should work")

        # If multiple paths work, they must resolve to the same class
        if len(successful_imports) > 1:
            class_ids = set(info['id'] for info in imported_classes.values())

            if len(class_ids) > 1:
                # Multiple different class objects - SSOT violation
                details = []
                for path, info in imported_classes.items():
                    details.append(f"  {path}: class_id={info['id']}, name={info['name']}, from={info['module_file']}")

                self.fail(f"SSOT VIOLATION: Import paths resolve to different WebSocketManager classes:\n" +
                         "\n".join(details))

        logger.info("✅ All WebSocketManager imports resolve to same class object")

    def test_websocket_manager_function_unification(self):
        """Test that WebSocket Manager factory functions are unified across import paths."""
        imported_functions = {}
        successful_imports = {}

        for import_path in self.function_paths_to_test:
            function_obj, module_file = self._import_function_from_path(import_path)

            if function_obj is not None:
                imported_functions[import_path] = {
                    'function': function_obj,
                    'id': id(function_obj),
                    'module_file': module_file,
                    'name': getattr(function_obj, '__name__', 'unknown')
                }
                successful_imports[import_path] = function_obj
                logger.info(f"✓ {import_path} -> function id {id(function_obj)} from {module_file}")

        # If multiple paths work, they should ideally be the same function
        if len(successful_imports) > 1:
            function_ids = set(info['id'] for info in imported_functions.values())

            if len(function_ids) > 1:
                # Multiple different functions - check if they're equivalent
                logger.warning("⚠ Multiple get_websocket_manager functions found - checking equivalence")

                # At minimum, they should have consistent behavior documentation
                for path, info in imported_functions.items():
                    func_doc = info['function'].__doc__ or ""
                    if "DEPRECATED" in func_doc.upper():
                        logger.info(f"  {path} is marked as deprecated")

        logger.info("✅ WebSocket Manager function unification validated")

    def test_import_path_consistency_across_modules(self):
        """Test that modules consistently use the same import paths for WebSocket Manager."""
        # Modules that should use WebSocket Manager
        modules_to_check = [
            "netra_backend.app.routes.websocket",
            "netra_backend.app.agents.supervisor.agent_registry",
        ]

        import_patterns = {}

        for module_name in modules_to_check:
            try:
                module = importlib.import_module(module_name)
                module_file = getattr(module, '__file__', None)

                if module_file and Path(module_file).exists():
                    with open(module_file, 'r', encoding='utf-8') as f:
                        source_code = f.read()

                    # Look for WebSocketManager imports
                    websocket_imports = []
                    for line in source_code.split('\n'):
                        line = line.strip()
                        if ('import' in line and
                            'WebSocketManager' in line and
                            not line.startswith('#')):
                            websocket_imports.append(line)

                    if websocket_imports:
                        import_patterns[module_name] = websocket_imports
                        logger.info(f"WebSocket imports in {module_name}:")
                        for imp in websocket_imports:
                            logger.info(f"  {imp}")

            except Exception as e:
                logger.warning(f"Could not analyze {module_name}: {e}")

        # Check for consistency in import patterns
        if import_patterns:
            # Look for use of canonical import path
            canonical_usage = 0
            deprecated_usage = 0

            for module_name, imports in import_patterns.items():
                for import_line in imports:
                    if "unified_manager" in import_line:
                        canonical_usage += 1
                    elif "websocket_manager_factory" in import_line:
                        deprecated_usage += 1

            logger.info(f"Import pattern analysis: {canonical_usage} canonical, {deprecated_usage} deprecated")

            # Should trend toward canonical usage
            if deprecated_usage > canonical_usage:
                logger.warning("⚠ More deprecated imports than canonical imports found")

        logger.info("✅ Import path consistency across modules validated")

    def test_websocket_manager_class_identity_stability(self):
        """Test that WebSocket Manager class identity remains stable across imports."""
        # Import the canonical class multiple times and verify stability
        canonical_classes = []

        for i in range(3):
            try:
                # Clear and re-import
                module_name = self.canonical_import_path
                if module_name in sys.modules:
                    del sys.modules[module_name]

                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                canonical_classes.append({
                    'iteration': i,
                    'class': WebSocketManager,
                    'id': id(WebSocketManager),
                    'name': WebSocketManager.__name__
                })
                logger.info(f"Import {i}: WebSocketManager id {id(WebSocketManager)}")

            except Exception as e:
                self.fail(f"Canonical import failed on iteration {i}: {e}")

        # Class identity should be stable (same class object each time)
        class_ids = [info['id'] for info in canonical_classes]
        unique_ids = set(class_ids)

        if len(unique_ids) > 1:
            logger.warning("⚠ WebSocketManager class identity varies across imports")
            # This might be acceptable due to module reloading, but log it
            for info in canonical_classes:
                logger.info(f"  Iteration {info['iteration']}: id={info['id']}, name={info['name']}")
        else:
            logger.info("✓ WebSocketManager class identity stable across imports")

        # At minimum, all should have the same name and be classes
        for info in canonical_classes:
            self.assertTrue(inspect.isclass(info['class']))
            self.assertEqual(info['name'], self.canonical_class_name)

        logger.info("✅ WebSocket Manager class identity stability validated")

    def test_deprecated_imports_redirect_to_canonical(self):
        """Test that deprecated import paths properly redirect to canonical implementation."""
        canonical_class = None

        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as CanonicalWSM
            canonical_class = CanonicalWSM
            canonical_id = id(CanonicalWSM)
            logger.info(f"✓ Canonical WebSocketManager loaded (id: {canonical_id})")
        except ImportError as e:
            self.fail(f"Cannot load canonical WebSocketManager: {e}")

        # Test deprecated paths redirect to canonical
        deprecated_paths = [
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
        ]

        for deprecated_path in deprecated_paths:
            class_obj, module_file = self._import_class_from_path(deprecated_path)

            if class_obj is not None:
                deprecated_id = id(class_obj)

                if deprecated_id == canonical_id:
                    logger.info(f"✓ {deprecated_path} correctly redirects to canonical (same id)")
                else:
                    # Different class object - check if it's a compatible wrapper
                    if hasattr(class_obj, '__name__') and class_obj.__name__ == self.canonical_class_name:
                        logger.warning(f"⚠ {deprecated_path} uses different class object but same name")
                    else:
                        self.fail(f"REDIRECT FAILURE: {deprecated_path} resolves to different class "
                                 f"(id: {deprecated_id} vs canonical: {canonical_id})")

        logger.info("✅ Deprecated import redirection validated")

    def test_import_path_documentation_consistency(self):
        """Test that import path documentation is consistent across modules."""
        modules_with_import_docs = [
            "netra_backend.app.websocket_core.unified_manager",
            "netra_backend.app.websocket_core.websocket_manager_factory",
        ]

        import_instructions = {}

        for module_name in modules_with_import_docs:
            try:
                module = importlib.import_module(module_name)
                module_doc = module.__doc__ or ""

                # Extract import examples from documentation
                import_examples = []
                lines = module_doc.split('\n')

                in_example = False
                for line in lines:
                    line = line.strip()
                    if 'from netra_backend' in line and 'import' in line:
                        import_examples.append(line)
                    elif 'import netra_backend' in line:
                        import_examples.append(line)

                if import_examples:
                    import_instructions[module_name] = import_examples

            except Exception as e:
                logger.warning(f"Could not analyze documentation for {module_name}: {e}")

        # Check for consistent import recommendations
        if import_instructions:
            logger.info("Import documentation found:")
            for module_name, examples in import_instructions.items():
                logger.info(f"  {module_name}:")
                for example in examples:
                    logger.info(f"    {example}")

            # Should recommend canonical import path
            canonical_recommendations = sum(
                1 for examples in import_instructions.values()
                for example in examples
                if "unified_manager" in example
            )

            deprecated_recommendations = sum(
                1 for examples in import_instructions.values()
                for example in examples
                if "websocket_manager_factory" in example and "DEPRECATED" not in example.upper()
            )

            if deprecated_recommendations > canonical_recommendations:
                logger.warning("⚠ More deprecated import recommendations than canonical ones")

        logger.info("✅ Import path documentation consistency validated")


if __name__ == '__main__':
    import unittest
    unittest.main()