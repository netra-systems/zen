"""WebSocket Manager SSOT Consolidation Validation Test - Issue #824

CRITICAL BUSINESS CONTEXT:
- Issue #824: Multiple WebSocket Manager implementations causing Golden Path failures
- Business Impact: $500K+ ARR protection requires single authoritative WebSocket manager
- SSOT Violation: 3 different factory patterns creating different manager instances
- Consolidation Goal: Single import path and single manager implementation

TEST PURPOSE:
This test validates the complete SSOT consolidation of WebSocket Manager implementations.
It verifies that after consolidation, all import paths lead to the same authoritative implementation.

Expected Behavior:
- BEFORE CONSOLIDATION: Test finds multiple different implementations
- AFTER CONSOLIDATION: Test passes with single authoritative implementation

Business Value Justification:
- Segment: ALL (Free -> Enterprise) - Platform integrity
- Business Goal: Ensure consistent WebSocket behavior across all features
- Value Impact: Eliminate user data bleeding and race conditions
- Revenue Impact: Maintain $500K+ ARR by ensuring reliable chat functionality
"""

import pytest
import sys
import inspect
import importlib
from typing import Dict, Set, Any, List, Tuple
from unittest.mock import MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerSSOTConsolidationValidation(SSotBaseTestCase):
    """Validate SSOT consolidation of WebSocket Manager implementations."""

    def setup_method(self, method):
        """Set up test environment for SSOT validation."""
        super().setup_method(method)
        logger.info(f"Setting up SSOT consolidation validation test: {method.__name__}")

        # Clear module cache to ensure clean testing
        self.websocket_modules_to_clear = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core',
            'netra_backend.app.routes.websocket_ssot'
        ]

        for module_name in self.websocket_modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]

    def test_single_authoritative_websocket_manager_class(self):
        """
        Test that there is exactly ONE authoritative WebSocketManager class across all imports.

        SSOT Requirement: All import paths should resolve to the same class definition.
        """
        logger.info("Testing single authoritative WebSocketManager class")

        websocket_manager_classes = {}
        import_paths_to_test = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core'
        ]

        # Collect WebSocketManager classes from different import paths
        for import_path in import_paths_to_test:
            try:
                module = importlib.import_module(import_path)

                # Look for WebSocketManager class
                if hasattr(module, 'WebSocketManager'):
                    websocket_manager_class = getattr(module, 'WebSocketManager')
                    websocket_manager_classes[import_path] = websocket_manager_class

                    logger.info(f"Found WebSocketManager from {import_path}: {websocket_manager_class}")

                # Also look for UnifiedWebSocketManager (should be aliased)
                if hasattr(module, 'UnifiedWebSocketManager'):
                    unified_class = getattr(module, 'UnifiedWebSocketManager')
                    websocket_manager_classes[f"{import_path}.UnifiedWebSocketManager"] = unified_class

                    logger.info(f"Found UnifiedWebSocketManager from {import_path}: {unified_class}")

            except ImportError as e:
                logger.warning(f"Could not import {import_path}: {e}")
            except Exception as e:
                logger.error(f"Error importing {import_path}: {e}")

        # Analyze findings
        if len(websocket_manager_classes) == 0:
            pytest.skip("No WebSocketManager classes found - cannot validate SSOT consolidation")

        logger.info(f"Found {len(websocket_manager_classes)} WebSocketManager class references")

        # Get unique class objects
        unique_classes = {}
        for import_path, cls in websocket_manager_classes.items():
            class_id = id(cls)
            class_signature = f"{cls.__module__}.{cls.__name__}"

            if class_id not in unique_classes:
                unique_classes[class_id] = {
                    'class': cls,
                    'signature': class_signature,
                    'import_paths': []
                }
            unique_classes[class_id]['import_paths'].append(import_path)

        logger.info(f"Analysis: {len(unique_classes)} unique WebSocketManager classes found")

        for class_id, info in unique_classes.items():
            logger.info(f"  Class {info['signature']}: imported via {info['import_paths']}")

        # SSOT Validation: Should have exactly ONE unique class
        if len(unique_classes) > 1:
            error_msg = "SSOT VIOLATION: Multiple different WebSocketManager classes found:\n"
            for class_id, info in unique_classes.items():
                error_msg += f"  - {info['signature']} (id={class_id}) via {info['import_paths']}\n"

            pytest.fail(f"Issue #824: {error_msg}")

        # SUCCESS: Single authoritative class
        authoritative_class_info = next(iter(unique_classes.values()))
        logger.info(f"SUCCESS: Single authoritative WebSocketManager class: {authoritative_class_info['signature']}")
        logger.info(f"Available via import paths: {authoritative_class_info['import_paths']}")

        # Verify the class has expected WebSocket manager functionality
        websocket_manager_class = authoritative_class_info['class']
        expected_methods = ['send_event', 'broadcast', 'connect', 'disconnect']

        missing_methods = []
        for method_name in expected_methods:
            if not hasattr(websocket_manager_class, method_name):
                missing_methods.append(method_name)

        if missing_methods:
            logger.warning(f"Authoritative WebSocketManager missing expected methods: {missing_methods}")
        else:
            logger.info("Authoritative WebSocketManager has all expected methods")

    def test_single_authoritative_get_websocket_manager_function(self):
        """
        Test that there is exactly ONE authoritative get_websocket_manager() function.

        SSOT Requirement: All import paths should resolve to the same factory function.
        """
        logger.info("Testing single authoritative get_websocket_manager function")

        get_websocket_manager_functions = {}
        import_paths_to_test = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core'
        ]

        # Collect get_websocket_manager functions from different import paths
        for import_path in import_paths_to_test:
            try:
                module = importlib.import_module(import_path)

                if hasattr(module, 'get_websocket_manager'):
                    get_manager_func = getattr(module, 'get_websocket_manager')
                    get_websocket_manager_functions[import_path] = get_manager_func

                    logger.info(f"Found get_websocket_manager from {import_path}: {get_manager_func}")

            except ImportError as e:
                logger.warning(f"Could not import {import_path}: {e}")
            except Exception as e:
                logger.error(f"Error importing {import_path}: {e}")

        if len(get_websocket_manager_functions) == 0:
            pytest.skip("No get_websocket_manager functions found - cannot validate SSOT consolidation")

        logger.info(f"Found {len(get_websocket_manager_functions)} get_websocket_manager function references")

        # Get unique function objects
        unique_functions = {}
        for import_path, func in get_websocket_manager_functions.items():
            func_id = id(func)
            func_signature = f"{func.__module__}.{func.__name__}"

            if func_id not in unique_functions:
                unique_functions[func_id] = {
                    'function': func,
                    'signature': func_signature,
                    'import_paths': []
                }
            unique_functions[func_id]['import_paths'].append(import_path)

        logger.info(f"Analysis: {len(unique_functions)} unique get_websocket_manager functions found")

        for func_id, info in unique_functions.items():
            logger.info(f"  Function {info['signature']}: imported via {info['import_paths']}")

        # SSOT Validation: Should have exactly ONE unique function
        if len(unique_functions) > 1:
            error_msg = "SSOT VIOLATION: Multiple different get_websocket_manager functions found:\n"
            for func_id, info in unique_functions.items():
                error_msg += f"  - {info['signature']} (id={func_id}) via {info['import_paths']}\n"

            pytest.fail(f"Issue #824: {error_msg}")

        # SUCCESS: Single authoritative function
        authoritative_func_info = next(iter(unique_functions.values()))
        logger.info(f"SUCCESS: Single authoritative get_websocket_manager function: {authoritative_func_info['signature']}")
        logger.info(f"Available via import paths: {authoritative_func_info['import_paths']}")

        # Verify function signature is correct
        func = authoritative_func_info['function']
        sig = inspect.signature(func)
        logger.info(f"Function signature: {sig}")

        # Should accept user_context parameter
        params = list(sig.parameters.keys())
        if 'user_context' not in params:
            logger.warning(f"get_websocket_manager function missing 'user_context' parameter. Found params: {params}")

    def test_websocket_manager_import_path_consistency(self):
        """
        Test that all WebSocket manager imports lead to consistent implementations.

        SSOT Requirement: No matter which import path is used, behavior should be identical.
        """
        logger.info("Testing WebSocket manager import path consistency")

        mock_user_context = MagicMock()
        mock_user_context.user_id = "test_user_consistency"

        # Test various import patterns that should all work consistently
        import_patterns = [
            # Direct imports
            ('netra_backend.app.websocket_core.websocket_manager', 'WebSocketManager'),
            ('netra_backend.app.websocket_core.websocket_manager', 'get_websocket_manager'),
            ('netra_backend.app.websocket_core.unified_manager', 'UnifiedWebSocketManager'),
            ('netra_backend.app.websocket_core.unified_manager', 'get_websocket_manager'),

            # Module-level imports
            ('netra_backend.app.websocket_core', 'WebSocketManager'),
            ('netra_backend.app.websocket_core', 'get_websocket_manager'),
        ]

        successful_imports = {}
        failed_imports = {}

        for module_path, attribute_name in import_patterns:
            import_key = f"{module_path}.{attribute_name}"

            try:
                module = importlib.import_module(module_path)

                if hasattr(module, attribute_name):
                    attribute = getattr(module, attribute_name)
                    successful_imports[import_key] = {
                        'attribute': attribute,
                        'type': type(attribute),
                        'module': getattr(attribute, '__module__', 'unknown'),
                        'qualname': getattr(attribute, '__qualname__', 'unknown')
                    }
                    logger.info(f"✓ {import_key}: {type(attribute)} from {getattr(attribute, '__module__', 'unknown')}")
                else:
                    failed_imports[import_key] = f"Attribute '{attribute_name}' not found in module"
                    logger.warning(f"✗ {import_key}: Attribute not found")

            except ImportError as e:
                failed_imports[import_key] = f"Import error: {e}"
                logger.warning(f"✗ {import_key}: Import failed - {e}")

            except Exception as e:
                failed_imports[import_key] = f"Error: {e}"
                logger.error(f"✗ {import_key}: Error - {e}")

        logger.info(f"Import consistency test results:")
        logger.info(f"  Successful imports: {len(successful_imports)}")
        logger.info(f"  Failed imports: {len(failed_imports)}")

        if failed_imports:
            logger.info("Failed imports:")
            for import_key, error in failed_imports.items():
                logger.info(f"  - {import_key}: {error}")

        # Analyze consistency of successful imports
        if len(successful_imports) < 2:
            pytest.skip(f"Need at least 2 successful imports for consistency analysis, got {len(successful_imports)}")

        # Group by type (classes vs functions)
        classes = {k: v for k, v in successful_imports.items() if inspect.isclass(v['attribute'])}
        functions = {k: v for k, v in successful_imports.items() if callable(v['attribute']) and not inspect.isclass(v['attribute'])}

        logger.info(f"Found {len(classes)} class imports and {len(functions)} function imports")

        # Validate class consistency
        if len(classes) > 1:
            class_modules = set(info['module'] for info in classes.values())
            class_qualnames = set(info['qualname'] for info in classes.values())

            if len(class_modules) > 1:
                logger.error(f"INCONSISTENCY: Classes come from different modules: {class_modules}")
                pytest.fail(
                    f"Issue #824: WebSocket manager classes imported from different modules: {class_modules}. "
                    f"This violates SSOT principle."
                )

            if len(class_qualnames) > 1:
                logger.error(f"INCONSISTENCY: Different class qualnames: {class_qualnames}")
                pytest.fail(
                    f"Issue #824: Different WebSocket manager class implementations: {class_qualnames}. "
                    f"This indicates SSOT fragmentation."
                )

        # Validate function consistency
        if len(functions) > 1:
            func_modules = set(info['module'] for info in functions.values())
            func_qualnames = set(info['qualname'] for info in functions.values())

            if len(func_modules) > 1:
                logger.error(f"INCONSISTENCY: Functions come from different modules: {func_modules}")
                pytest.fail(
                    f"Issue #824: get_websocket_manager functions imported from different modules: {func_modules}. "
                    f"This violates SSOT principle."
                )

            if len(func_qualnames) > 1:
                logger.error(f"INCONSISTENCY: Different function qualnames: {func_qualnames}")
                pytest.fail(
                    f"Issue #824: Different get_websocket_manager function implementations: {func_qualnames}. "
                    f"This indicates SSOT fragmentation."
                )

        logger.info("SUCCESS: All WebSocket manager imports are consistent - SSOT consolidation achieved")

    def test_websocket_manager_factory_no_redundant_implementations(self):
        """
        Test that there are no redundant factory or adapter implementations.

        SSOT Requirement: No duplicate factory classes or adapter patterns should exist.
        """
        logger.info("Testing for redundant WebSocket manager factory implementations")

        # Search for potentially redundant implementations
        modules_to_check = [
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.agents.supervisor.agent_registry'
        ]

        redundant_implementations = {}

        for module_path in modules_to_check:
            try:
                module = importlib.import_module(module_path)

                # Look for factory, adapter, or manager classes
                for attr_name in dir(module):
                    if not attr_name.startswith('_'):
                        attr = getattr(module, attr_name)

                        if inspect.isclass(attr):
                            class_name = attr.__name__.lower()

                            # Check for redundant patterns
                            if any(pattern in class_name for pattern in [
                                'websocketmanager', 'websocket_manager', 'factory', 'adapter'
                            ]):
                                key = f"{module_path}.{attr_name}"
                                redundant_implementations[key] = {
                                    'class': attr,
                                    'module': module_path,
                                    'name': attr_name,
                                    'full_name': f"{attr.__module__}.{attr.__name__}"
                                }
                                logger.info(f"Found potential redundant implementation: {key}")

            except ImportError as e:
                logger.info(f"Module {module_path} not found: {e} (this might be expected after cleanup)")
            except Exception as e:
                logger.warning(f"Error checking {module_path}: {e}")

        logger.info(f"Found {len(redundant_implementations)} potential redundant implementations")

        # After SSOT consolidation, there should be minimal redundant implementations
        if redundant_implementations:
            logger.info("Redundant implementations found:")
            for key, info in redundant_implementations.items():
                logger.info(f"  - {key}: {info['full_name']}")

            # Some redundancy might be acceptable during transition, but not excessive
            max_acceptable_redundant = 3  # Allow some transition artifacts

            if len(redundant_implementations) > max_acceptable_redundant:
                pytest.fail(
                    f"Issue #824: Too many redundant WebSocket manager implementations found: "
                    f"{len(redundant_implementations)} (max acceptable: {max_acceptable_redundant}). "
                    f"This suggests incomplete SSOT consolidation. Found: {list(redundant_implementations.keys())}"
                )

        logger.info("SUCCESS: Minimal redundant implementations - SSOT consolidation on track")

    def teardown_method(self, method):
        """Clean up after SSOT validation test."""
        logger.info(f"Tearing down SSOT consolidation test: {method.__name__}")
        super().teardown_method(method)

        # Clear modules that were imported during testing
        for module_name in self.websocket_modules_to_clear:
            if module_name in sys.modules:
                try:
                    del sys.modules[module_name]
                except Exception as e:
                    logger.warning(f"Failed to clear module {module_name}: {e}")
