"""
Canonical Imports SSOT Tests - Issue #186 WebSocket Manager Fragmentation

Tests that FAIL initially to prove import canonicalization violations exist in WebSocket modules.
After SSOT consolidation, these tests should PASS, proving single canonical import paths work.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Stability - Eliminate import confusion causing development and runtime errors
- Value Impact: Ensure clear, predictable WebSocket manager import patterns
- Revenue Impact: Reduce development time waste and prevent import-related production failures

SSOT Violations This Module Proves:
1. Multiple import paths for same functionality causing confusion
2. Deprecated imports still accessible without proper migration warnings
3. Import aliases point to different implementations
4. Dynamic/lazy imports create runtime instability
"""

import sys
import importlib
import inspect
import unittest
import warnings
from typing import Any, Dict, List, Optional, Set, Type, Tuple
from unittest.mock import patch, Mock
import ast

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerCanonicalImports(unittest.TestCase):
    """
    Tests to prove WebSocket manager canonical import violations exist.
    
    These tests are designed to FAIL initially, proving import canonicalization issues.
    After proper import standardization, they should PASS.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Clear import cache for consistent testing
        self.original_modules = dict(sys.modules)
        
    def tearDown(self):
        """Clean up after tests."""
        # Restore original module state
        modules_to_remove = set(sys.modules.keys()) - set(self.original_modules.keys())
        for module in modules_to_remove:
            if module.startswith('netra_backend.app.websocket'):
                sys.modules.pop(module, None)

    def test_single_canonical_import_path(self):
        """
        Test only one import path exists for WebSocket manager functionality.
        
        EXPECTED INITIAL STATE: FAIL - Multiple import paths for same functionality
        EXPECTED POST-SSOT STATE: PASS - Single canonical import path per functionality
        
        VIOLATION BEING PROVED: Multiple import paths causing developer confusion
        """
        canonicalization_violations = []
        
        # Define expected canonical import mapping
        canonical_mappings = {
            'WebSocketManagerFactory': {
                'canonical_path': 'netra_backend.app.websocket_core.websocket_manager_factory',
                'canonical_class': 'WebSocketManagerFactory',
                'aliases_allowed': [],  # No aliases should exist for factory
            },
            'WebSocketManager': {
                'canonical_path': 'netra_backend.app.websocket_core.websocket_manager',
                'canonical_class': 'WebSocketManager',
                'aliases_allowed': ['UnifiedWebSocketManager'],  # One alias allowed during migration
            },
            'WebSocketManagerProtocol': {
                'canonical_path': 'netra_backend.app.core.interfaces_websocket',
                'canonical_class': 'WebSocketManagerProtocol',
                'aliases_allowed': [],  # Protocol should have single import
            },
            'WebSocketConnection': {
                'canonical_path': 'netra_backend.app.websocket_core.unified_manager',
                'canonical_class': 'WebSocketConnection',
                'aliases_allowed': [],  # Connection class should be singular
            }
        }
        
        # Search for actual import paths
        search_modules = [
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.core.interfaces_websocket',
            'netra_backend.app.websocket_core.migration_adapter',
            'netra_backend.app.websocket_core.connection_manager',
        ]
        
        actual_imports = {}  # class_name -> [module_paths]
        
        for module_path in search_modules:
            try:
                module = importlib.import_module(module_path)
                
                for class_name in canonical_mappings.keys():
                    if hasattr(module, class_name):
                        if class_name not in actual_imports:
                            actual_imports[class_name] = []
                        actual_imports[class_name].append(module_path)
                        
                    # Also check for aliases
                    expected_aliases = canonical_mappings[class_name]['aliases_allowed']
                    for alias in expected_aliases:
                        if hasattr(module, alias):
                            alias_class = getattr(module, alias)
                            # Check if alias points to same class as canonical
                            try:
                                canonical_module = importlib.import_module(canonical_mappings[class_name]['canonical_path'])
                                if hasattr(canonical_module, class_name):
                                    canonical_class = getattr(canonical_module, class_name)
                                    if alias_class is not canonical_class:
                                        canonicalization_violations.append(
                                            f"Alias {alias} in {module_path} points to different class than canonical {class_name}"
                                        )
                            except ImportError:
                                pass
                                
            except ImportError:
                # Expected for some modules
                pass
            except Exception as e:
                logger.warning(f"Error searching module {module_path}: {e}")

        # Check canonicalization violations
        for class_name, expected in canonical_mappings.items():
            expected_canonical = expected['canonical_path']
            
            if class_name in actual_imports:
                actual_paths = actual_imports[class_name]
                
                # Check for multiple import paths (violation)
                if len(actual_paths) > 1:
                    canonicalization_violations.append(
                        f"{class_name}: found in multiple modules {actual_paths}, expected only in {expected_canonical}"
                    )
                
                # Check if canonical path is correct
                elif len(actual_paths) == 1:
                    if actual_paths[0] != expected_canonical:
                        canonicalization_violations.append(
                            f"{class_name}: found in {actual_paths[0]}, expected in {expected_canonical}"
                        )
                        
            else:
                # Check if canonical import exists at expected location
                try:
                    module = importlib.import_module(expected_canonical)
                    if not hasattr(module, expected['canonical_class']):
                        canonicalization_violations.append(
                            f"{class_name}: not found at canonical path {expected_canonical}"
                        )
                except ImportError:
                    canonicalization_violations.append(
                        f"{class_name}: canonical module {expected_canonical} not importable"
                    )

        # ASSERTION THAT SHOULD FAIL INITIALLY: Canonical import paths should be enforced
        self.assertEqual(
            len(canonicalization_violations), 0,
            f"SSOT VIOLATION: Import canonicalization violations: {canonicalization_violations}. "
            f"Actual imports found: {actual_imports}. "
            f"This proves import paths are not properly canonicalized and multiple paths exist for same functionality."
        )

    def test_deprecated_imports_removed(self):
        """
        Test old import paths are removed after migration.
        
        EXPECTED INITIAL STATE: FAIL - Legacy imports still accessible
        EXPECTED POST-SSOT STATE: PASS - Legacy imports properly removed or deprecated
        
        VIOLATION BEING PROVED: Legacy import paths still active without migration
        """
        deprecated_import_violations = []
        
        # Define deprecated import patterns that should be removed
        deprecated_imports = [
            # Legacy manager patterns
            {
                'module': 'netra_backend.app.websocket_core.legacy_manager',
                'class': 'LegacyWebSocketManager',
                'replacement': 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager'
            },
            {
                'module': 'netra_backend.app.websocket_core.singleton_manager',
                'class': 'SingletonWebSocketManager', 
                'replacement': 'netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory'
            },
            # Legacy connection patterns
            {
                'module': 'netra_backend.app.websocket_core.connection',
                'class': 'Connection',
                'replacement': 'netra_backend.app.websocket_core.unified_manager.WebSocketConnection'
            },
            # Legacy adapter patterns (should be fully removed)
            {
                'module': 'netra_backend.app.websocket_core.adapter',
                'class': 'WebSocketAdapter',
                'replacement': 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager'
            },
            # Legacy factory patterns
            {
                'module': 'netra_backend.app.websocket_core.factory',
                'class': 'ManagerFactory',
                'replacement': 'netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory'
            }
        ]
        
        # Test each deprecated import
        for deprecated in deprecated_imports:
            try:
                module = importlib.import_module(deprecated['module'])
                
                if hasattr(module, deprecated['class']):
                    # Check if deprecation warning is issued
                    with warnings.catch_warnings(record=True) as warning_list:
                        warnings.simplefilter("always")
                        
                        deprecated_class = getattr(module, deprecated['class'])
                        
                        # Check if accessing the class triggers deprecation warning
                        deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
                        
                        if not deprecation_warnings:
                            deprecated_import_violations.append(
                                f"Deprecated import {deprecated['module']}.{deprecated['class']} accessible without deprecation warning. "
                                f"Should be replaced with {deprecated['replacement']}"
                            )
                        
            except ImportError:
                # Good - deprecated module removed
                pass
            except Exception as e:
                logger.warning(f"Error testing deprecated import {deprecated['module']}: {e}")

        # Test for specific legacy patterns that should be removed
        legacy_patterns_to_check = [
            # Global functions (anti-pattern)
            ('netra_backend.app.websocket_core', 'get_websocket_manager'),
            ('netra_backend.app.websocket_core', 'create_websocket_manager'),
            ('netra_backend.app.websocket_core', 'websocket_manager_instance'),
            
            # Singleton patterns (security vulnerability)
            ('netra_backend.app.websocket_core.singleton', 'WebSocketManagerSingleton'),
            ('netra_backend.app.websocket_core', 'WEBSOCKET_MANAGER_INSTANCE'),
            
            # Direct instantiation helpers (anti-pattern for factory)
            ('netra_backend.app.websocket_core.helpers', 'create_manager'),
            ('netra_backend.app.websocket_core.utils', 'get_manager_instance'),
        ]
        
        for module_path, item_name in legacy_patterns_to_check:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, item_name):
                    deprecated_import_violations.append(
                        f"Legacy pattern {module_path}.{item_name} still accessible. "
                        f"This pattern should be removed in favor of factory pattern."
                    )
            except ImportError:
                # Good - legacy module removed
                pass
            except Exception as e:
                logger.warning(f"Error checking legacy pattern {module_path}.{item_name}: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Deprecated imports should be removed
        self.assertEqual(
            len(deprecated_import_violations), 0,
            f"SSOT VIOLATION: Deprecated import violations: {deprecated_import_violations}. "
            f"This proves legacy import patterns are still accessible and need proper deprecation or removal."
        )

    def test_import_aliases_consistency(self):
        """
        Test import aliases resolve to same implementation.
        
        EXPECTED INITIAL STATE: FAIL - Aliases point to different implementations
        EXPECTED POST-SSOT STATE: PASS - All aliases point to same canonical implementation
        
        VIOLATION BEING PROVED: Import aliases create inconsistency and confusion
        """
        alias_violations = []
        
        # Define expected alias consistency rules
        alias_groups = [
            # WebSocket Manager aliases (should all point to same implementation)
            {
                'canonical': ('netra_backend.app.websocket_core.websocket_manager', 'WebSocketManager'),
                'aliases': [
                    ('netra_backend.app.websocket_core.unified_manager', 'WebSocketManager'),
                    ('netra_backend.app.websocket_core.manager', 'WebSocketManager'),
                ]
            },
            # WebSocket Connection aliases
            {
                'canonical': ('netra_backend.app.websocket_core.unified_manager', 'WebSocketConnection'),
                'aliases': [
                    ('netra_backend.app.websocket_core.websocket_manager', 'WebSocketConnection'),
                    ('netra_backend.app.websocket_core.protocols', 'WebSocketConnection'),
                ]
            },
            # Protocol aliases
            {
                'canonical': ('netra_backend.app.core.interfaces_websocket', 'WebSocketManagerProtocol'),
                'aliases': [
                    ('netra_backend.app.websocket_core.protocols', 'WebSocketManagerProtocol'),
                ]
            }
        ]
        
        # Test alias consistency
        for alias_group in alias_groups:
            canonical_module_path, canonical_class_name = alias_group['canonical']
            canonical_class = None
            
            # Get canonical implementation
            try:
                canonical_module = importlib.import_module(canonical_module_path)
                if hasattr(canonical_module, canonical_class_name):
                    canonical_class = getattr(canonical_module, canonical_class_name)
                else:
                    alias_violations.append(
                        f"Canonical class {canonical_module_path}.{canonical_class_name} not found"
                    )
                    continue
            except ImportError:
                alias_violations.append(
                    f"Canonical module {canonical_module_path} not importable"
                )
                continue
            except Exception as e:
                alias_violations.append(
                    f"Error importing canonical {canonical_module_path}: {e}"
                )
                continue
            
            # Check each alias
            for alias_module_path, alias_class_name in alias_group['aliases']:
                try:
                    alias_module = importlib.import_module(alias_module_path)
                    if hasattr(alias_module, alias_class_name):
                        alias_class = getattr(alias_module, alias_class_name)
                        
                        # Check if alias points to same class as canonical
                        if alias_class is not canonical_class:
                            # Get class information for comparison
                            canonical_info = f"{canonical_class.__module__}.{canonical_class.__name__}"
                            alias_info = f"{alias_class.__module__}.{alias_class.__name__}"
                            
                            alias_violations.append(
                                f"Alias {alias_module_path}.{alias_class_name} points to {alias_info}, "
                                f"but canonical is {canonical_info}"
                            )
                        
                except ImportError:
                    # Alias module doesn't exist - could be good or bad
                    pass
                except Exception as e:
                    alias_violations.append(
                        f"Error checking alias {alias_module_path}.{alias_class_name}: {e}"
                    )

        # Test for unexpected aliases that shouldn't exist
        unexpected_aliases = []
        
        # Search through WebSocket modules for potential aliases
        websocket_modules = [
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.core.interfaces_websocket',
        ]
        
        known_classes = {}  # class_id -> (module_path, class_name)
        
        for module_path in websocket_modules:
            try:
                module = importlib.import_module(module_path)
                
                for attr_name in dir(module):
                    if not attr_name.startswith('_'):
                        attr = getattr(module, attr_name)
                        if inspect.isclass(attr) and 'WebSocket' in attr_name:
                            class_id = id(attr)
                            
                            if class_id in known_classes:
                                # Found potential alias
                                original_module, original_name = known_classes[class_id]
                                if (original_module, original_name) != (module_path, attr_name):
                                    unexpected_aliases.append(
                                        f"Class {attr_name} appears as alias: "
                                        f"{original_module}.{original_name} and {module_path}.{attr_name}"
                                    )
                            else:
                                known_classes[class_id] = (module_path, attr_name)
                                
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Error searching for aliases in {module_path}: {e}")

        if unexpected_aliases:
            alias_violations.extend(unexpected_aliases)

        # ASSERTION THAT SHOULD FAIL INITIALLY: Aliases should be consistent
        self.assertEqual(
            len(alias_violations), 0,
            f"SSOT VIOLATION: Import alias inconsistencies: {alias_violations}. "
            f"This proves import aliases point to different implementations causing confusion and runtime errors."
        )

    def test_lazy_import_patterns_eliminated(self):
        """
        Test no lazy/dynamic imports for WebSocket managers.
        
        EXPECTED INITIAL STATE: FAIL - Dynamic imports create instability  
        EXPECTED POST-SSOT STATE: PASS - All imports are static and predictable
        
        VIOLATION BEING PROVED: Dynamic/lazy imports cause runtime instability
        """
        lazy_import_violations = []
        
        # Search for lazy import patterns in WebSocket modules
        modules_to_analyze = [
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.websocket_manager', 
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.core.interfaces_websocket',
        ]
        
        lazy_import_patterns = [
            # Dynamic import patterns
            'importlib.import_module',
            '__import__',
            'importlib.util.spec_from_file_location',
            'importlib.util.module_from_spec',
            
            # Lazy import patterns
            'LazyImport',
            'lazy_import',
            'defer_import',
            
            # Conditional import patterns  
            'try:\n    import',
            'except ImportError:',
        ]
        
        for module_path in modules_to_analyze:
            try:
                # Get module source code
                module = importlib.import_module(module_path)
                if hasattr(module, '__file__') and module.__file__.endswith('.py'):
                    with open(module.__file__, 'r') as f:
                        source_code = f.read()
                    
                    # Parse AST to find dynamic imports
                    try:
                        tree = ast.parse(source_code)
                        
                        for node in ast.walk(tree):
                            # Check for importlib.import_module calls
                            if isinstance(node, ast.Call):
                                if isinstance(node.func, ast.Attribute):
                                    if (isinstance(node.func.value, ast.Name) and 
                                        node.func.value.id == 'importlib' and 
                                        node.func.attr == 'import_module'):
                                        lazy_import_violations.append(
                                            f"{module_path}: Dynamic import using importlib.import_module at line {node.lineno}"
                                        )
                                elif isinstance(node.func, ast.Name):
                                    if node.func.id == '__import__':
                                        lazy_import_violations.append(
                                            f"{module_path}: Dynamic import using __import__ at line {node.lineno}"
                                        )
                            
                            # Check for conditional imports
                            elif isinstance(node, ast.Try):
                                # Look for try/except ImportError patterns
                                for handler in node.handlers:
                                    if handler.type and isinstance(handler.type, ast.Name):
                                        if handler.type.id == 'ImportError':
                                            # Check if imports are in try block
                                            for stmt in node.body:
                                                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                                                    lazy_import_violations.append(
                                                        f"{module_path}: Conditional import in try/except at line {stmt.lineno}"
                                                    )
                    
                    except SyntaxError as e:
                        logger.warning(f"Could not parse {module_path}: {e}")
                    
                    # Also check for string-based patterns
                    for pattern in lazy_import_patterns:
                        if pattern in source_code:
                            if pattern not in ['try:\n    import', 'except ImportError:']:
                                # Simple string search for other patterns
                                line_numbers = [i+1 for i, line in enumerate(source_code.split('\n')) if pattern in line]
                                if line_numbers:
                                    lazy_import_violations.append(
                                        f"{module_path}: Lazy import pattern '{pattern}' found at lines {line_numbers[:3]}"
                                    )
                    
            except ImportError:
                # Module doesn't exist - not necessarily a problem
                pass
            except Exception as e:
                logger.warning(f"Error analyzing {module_path} for lazy imports: {e}")

        # Check for runtime import resolution patterns
        runtime_import_indicators = []
        
        for module_path in modules_to_analyze:
            try:
                module = importlib.import_module(module_path)
                
                # Look for functions that might do runtime imports
                for attr_name in dir(module):
                    if not attr_name.startswith('_'):
                        attr = getattr(module, attr_name)
                        if callable(attr) and hasattr(attr, '__code__'):
                            # Check if function contains import-related code
                            code = attr.__code__
                            if 'import' in str(code.co_names) or 'importlib' in str(code.co_names):
                                runtime_import_indicators.append(
                                    f"{module_path}.{attr_name} may contain runtime imports"
                                )
                                
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Error checking runtime imports in {module_path}: {e}")

        if runtime_import_indicators:
            lazy_import_violations.extend(runtime_import_indicators)

        # ASSERTION THAT SHOULD FAIL INITIALLY: No lazy imports should exist
        self.assertEqual(
            len(lazy_import_violations), 0,
            f"SSOT VIOLATION: Lazy/dynamic import violations: {lazy_import_violations}. "
            f"This proves WebSocket modules use lazy import patterns that create runtime instability."
        )


if __name__ == '__main__':
    import unittest
    unittest.main()