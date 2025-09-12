"""
Import Standardization SSOT Validation Tests - Issue #186 WebSocket Manager Fragmentation

Tests that FAIL initially to prove import path inconsistency exists in WebSocket managers.
After SSOT consolidation, these tests should PASS, proving standardized imports work.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)  
- Business Goal: Stability - Eliminate import path confusion causing integration failures
- Value Impact: Ensure consistent WebSocket manager access across all modules
- Revenue Impact: Prevent development delays and runtime errors from import inconsistencies

SSOT Violations This Module Proves:
1. Multiple import paths leading to different manager instances
2. Inconsistent import patterns across modules  
3. Circular import dependencies causing failures
4. Missing standardized import interfaces
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import sys
import importlib
import inspect
import unittest
from typing import Any, Dict, List, Set, Type, Optional
from unittest.mock import patch, Mock

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerImportStandardization(SSotBaseTestCase):
    """
    Tests to prove WebSocket manager import standardization violations exist.
    
    These tests are designed to FAIL initially, proving SSOT violations.
    After proper import standardization, they should PASS.
    """

    def test_websocket_manager_import_paths(self):
        """
        Test that all imports resolve to same SSOT implementation.
        
        EXPECTED INITIAL STATE: FAIL - Different import paths resolve to different classes
        EXPECTED POST-SSOT STATE: PASS - All import paths resolve to same canonical class
        
        VIOLATION BEING PROVED: Multiple import paths leading to different manager implementations
        """
        import_attempts = []
        successful_imports = {}
        failed_imports = []
        
        # Test various import patterns that might exist
        import_patterns = [
            # Main factory import
            ('websocket_manager_factory', 'netra_backend.app.websocket_core.websocket_manager_factory', 'WebSocketManagerFactory'),
            
            # Unified manager import
            ('unified_manager', 'netra_backend.app.websocket_core.unified_manager', 'UnifiedWebSocketManager'),
            
            # Protocol imports
            ('protocols', 'netra_backend.app.websocket_core.protocols', 'WebSocketManagerProtocol'),
            
            # Interface imports
            ('interfaces_websocket', 'netra_backend.app.core.interfaces_websocket', 'WebSocketManagerProtocol'),
            
            # Legacy adapter imports (should be deprecated)
            ('migration_adapter', 'netra_backend.app.websocket_core.migration_adapter', 'WebSocketManagerAdapter'),
            
            # Connection manager imports
            ('connection_manager', 'netra_backend.app.websocket_core.connection_manager', 'ConnectionManager'),
            
            # Direct manager imports (potential anti-pattern)
            ('manager', 'netra_backend.app.websocket_core.manager', 'WebSocketManager'),
        ]
        
        for alias, module_path, class_name in import_patterns:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    successful_imports[alias] = {
                        'module_path': module_path,
                        'class_name': class_name,
                        'class_id': id(cls),
                        'class_module': cls.__module__,
                        'class_qualname': getattr(cls, '__qualname__', 'Unknown')
                    }
                    import_attempts.append(f"[U+2713] {alias}: {module_path}.{class_name}")
                else:
                    failed_imports.append(f"[U+2717] {alias}: {module_path}.{class_name} (class not found)")
            except ImportError as e:
                failed_imports.append(f"[U+2717] {alias}: {module_path}.{class_name} (import error: {e})")
            except Exception as e:
                failed_imports.append(f"[U+2717] {alias}: {module_path}.{class_name} (error: {e})")

        # Log findings for debugging
        logger.info(f"Successful imports: {len(successful_imports)}")
        logger.info(f"Failed imports: {len(failed_imports)}")
        
        # Analyze if imports resolve to same canonical class
        canonical_imports = {}
        for alias, import_info in successful_imports.items():
            class_key = (import_info['class_module'], import_info['class_qualname'])
            if class_key not in canonical_imports:
                canonical_imports[class_key] = []
            canonical_imports[class_key].append(alias)

        # ASSERTION THAT SHOULD FAIL INITIALLY: All manager imports should resolve to one canonical class
        if len(canonical_imports) > 1:
            violation_details = []
            for class_key, aliases in canonical_imports.items():
                violation_details.append(f"Class {class_key}: imported as {aliases}")
            
            self.fail(
                f"SSOT VIOLATION: Multiple WebSocket manager classes found via different imports:\n" +
                "\n".join(violation_details) + 
                f"\nExpected all imports to resolve to single canonical class. This proves import fragmentation."
            )

        # If we have successful imports, ensure they're the canonical ones
        if successful_imports:
            # The canonical import should be the factory
            canonical_alias = 'websocket_manager_factory'
            if canonical_alias not in successful_imports:
                available_aliases = list(successful_imports.keys())
                self.fail(
                    f"SSOT VIOLATION: Canonical import '{canonical_alias}' not available. "
                    f"Available imports: {available_aliases}. This proves import standardization is incomplete."
                )

    def test_deprecated_imports_still_work(self):
        """
        Test backward compatibility during migration.
        
        EXPECTED INITIAL STATE: FAIL - Legacy imports exist without deprecation warnings
        EXPECTED POST-SSOT STATE: PASS - Legacy imports either removed or properly deprecated
        
        VIOLATION BEING PROVED: Legacy import paths still active without proper migration strategy
        """
        legacy_import_patterns = [
            # Legacy adapter patterns
            ('netra_backend.app.websocket_core.migration_adapter', 'WebSocketManagerAdapter'),
            
            # Legacy direct manager access
            ('netra_backend.app.websocket_core.manager', 'WebSocketManager'),
            
            # Legacy global functions
            ('netra_backend.app.websocket_core', 'get_websocket_manager'),
            
            # Legacy singleton patterns
            ('netra_backend.app.websocket_core.singleton', 'WebSocketManagerSingleton'),
        ]
        
        active_legacy_imports = []
        deprecated_imports = []
        
        for module_path, item_name in legacy_import_patterns:
            try:
                with patch('warnings.warn') as mock_warn:
                    module = importlib.import_module(module_path)
                    if hasattr(module, item_name):
                        item = getattr(module, item_name)
                        
                        # Check if deprecation warning was issued
                        if mock_warn.called:
                            deprecated_imports.append(f"{module_path}.{item_name}")
                        else:
                            active_legacy_imports.append(f"{module_path}.{item_name}")
                            
            except ImportError:
                # Good - legacy import removed
                pass
            except Exception as e:
                logger.warning(f"Error testing legacy import {module_path}.{item_name}: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: No active legacy imports should exist
        self.assertEqual(
            len(active_legacy_imports), 0,
            f"SSOT VIOLATION: Active legacy imports found without deprecation: {active_legacy_imports}. "
            f"Expected all legacy imports to be deprecated or removed. This proves incomplete migration."
        )

    def test_circular_import_prevention(self):
        """
        Test that import structure prevents circular dependencies.
        
        EXPECTED INITIAL STATE: FAIL - Circular import dependencies exist
        EXPECTED POST-SSOT STATE: PASS - Clean import hierarchy with no circular dependencies
        
        VIOLATION BEING PROVED: Circular import dependencies causing import failures
        """
        # Test potential circular import scenarios
        circular_import_tests = [
            # Test factory -> unified_manager -> factory circle
            ('netra_backend.app.websocket_core.websocket_manager_factory', 
             'netra_backend.app.websocket_core.unified_manager'),
            
            # Test protocols -> manager -> protocols circle  
            ('netra_backend.app.websocket_core.protocols',
             'netra_backend.app.websocket_core.unified_manager'),
             
            # Test interfaces -> websocket_core -> interfaces circle
            ('netra_backend.app.core.interfaces_websocket',
             'netra_backend.app.websocket_core.unified_manager'),
        ]
        
        circular_dependencies = []
        
        for module_a_path, module_b_path in circular_import_tests:
            try:
                # Import module A
                module_a = importlib.import_module(module_a_path)
                
                # Check if module A imports module B
                a_imports_b = False
                if hasattr(module_a, '__file__'):
                    with open(module_a.__file__, 'r') as f:
                        content = f.read()
                        if module_b_path.split('.')[-1] in content:
                            a_imports_b = True
                
                # Import module B
                module_b = importlib.import_module(module_b_path)
                
                # Check if module B imports module A
                b_imports_a = False
                if hasattr(module_b, '__file__'):
                    with open(module_b.__file__, 'r') as f:
                        content = f.read()
                        if module_a_path.split('.')[-1] in content:
                            b_imports_a = True
                
                # Detect circular dependency
                if a_imports_b and b_imports_a:
                    circular_dependencies.append(f"{module_a_path} <-> {module_b_path}")
                    
            except ImportError as e:
                # Import error could indicate circular dependency
                if "circular import" in str(e).lower():
                    circular_dependencies.append(f"{module_a_path} <-> {module_b_path}: {e}")
            except Exception as e:
                logger.warning(f"Error testing circular import {module_a_path} <-> {module_b_path}: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: No circular dependencies should exist
        self.assertEqual(
            len(circular_dependencies), 0,
            f"SSOT VIOLATION: Circular import dependencies found: {circular_dependencies}. "
            f"This proves import structure needs refactoring for clean dependency hierarchy."
        )

    def test_import_performance_consistency(self):
        """
        Test that import performance is consistent across all paths.
        
        EXPECTED INITIAL STATE: FAIL - Import performance varies significantly
        EXPECTED POST-SSOT STATE: PASS - Consistent import performance across all paths
        
        VIOLATION BEING PROVED: Import performance inconsistency indicating structural issues
        """
        import time
        
        import_performance_tests = [
            ('netra_backend.app.websocket_core.websocket_manager_factory', 'WebSocketManagerFactory'),
            ('netra_backend.app.websocket_core.unified_manager', 'UnifiedWebSocketManager'),
            ('netra_backend.app.websocket_core.protocols', 'WebSocketManagerProtocol'),
            ('netra_backend.app.core.interfaces_websocket', 'WebSocketManagerProtocol'),
        ]
        
        import_times = {}
        performance_issues = []
        
        for module_path, class_name in import_performance_tests:
            try:
                # Clear module from cache to get true import time
                if module_path in sys.modules:
                    del sys.modules[module_path]
                
                start_time = time.time()
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    _ = getattr(module, class_name)
                end_time = time.time()
                
                import_time = end_time - start_time
                import_times[f"{module_path}.{class_name}"] = import_time
                
            except ImportError:
                # Expected for some legacy imports
                pass
            except Exception as e:
                performance_issues.append(f"{module_path}.{class_name}: {e}")

        if import_times:
            avg_import_time = sum(import_times.values()) / len(import_times)
            max_import_time = max(import_times.values())
            min_import_time = min(import_times.values())
            
            # Performance thresholds
            MAX_IMPORT_TIME = 0.1  # 100ms max for any single import
            MAX_VARIANCE_RATIO = 3.0  # Max time shouldn't be more than 3x min time
            
            if max_import_time > MAX_IMPORT_TIME:
                performance_issues.append(f"Slow import: {max_import_time:.3f}s > {MAX_IMPORT_TIME}s")
            
            if min_import_time > 0 and (max_import_time / min_import_time) > MAX_VARIANCE_RATIO:
                performance_issues.append(
                    f"High import variance: {max_import_time:.3f}s / {min_import_time:.3f}s = "
                    f"{max_import_time/min_import_time:.1f}x > {MAX_VARIANCE_RATIO}x"
                )

        # ASSERTION THAT SHOULD FAIL INITIALLY: Import performance should be consistent
        self.assertEqual(
            len(performance_issues), 0,
            f"SSOT VIOLATION: Import performance issues: {performance_issues}. "
            f"Import times: {import_times}. This proves import structure needs optimization."
        )

    def test_import_interface_consistency(self):
        """
        Test that all imports provide consistent interfaces.
        
        EXPECTED INITIAL STATE: FAIL - Different imports provide different interfaces
        EXPECTED POST-SSOT STATE: PASS - All imports provide same consistent interface
        
        VIOLATION BEING PROVED: Import interface inconsistency causing integration failures
        """
        # Import all available WebSocket-related classes
        available_classes = {}
        
        import_paths = [
            ('netra_backend.app.websocket_core.websocket_manager_factory', 'WebSocketManagerFactory'),
            ('netra_backend.app.websocket_core.unified_manager', 'UnifiedWebSocketManager'),
            ('netra_backend.app.websocket_core.protocols', 'WebSocketManagerProtocol'),
            ('netra_backend.app.core.interfaces_websocket', 'WebSocketManagerProtocol'),
        ]
        
        for module_path, class_name in import_paths:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    
                    # Extract public methods and attributes
                    interface = set()
                    for attr_name in dir(cls):
                        if not attr_name.startswith('_'):
                            attr = getattr(cls, attr_name)
                            if callable(attr):
                                # Get method signature
                                try:
                                    sig = str(inspect.signature(attr))
                                    interface.add(f"{attr_name}{sig}")
                                except (ValueError, TypeError):
                                    interface.add(f"{attr_name}()")
                            else:
                                interface.add(f"{attr_name}:property")
                    
                    available_classes[f"{module_path}.{class_name}"] = interface
                    
            except ImportError:
                # Expected for some imports
                pass
            except Exception as e:
                logger.warning(f"Error analyzing interface for {module_path}.{class_name}: {e}")

        # Analyze interface consistency
        interface_differences = []
        if len(available_classes) > 1:
            class_names = list(available_classes.keys())
            base_class = class_names[0]
            base_interface = available_classes[base_class]
            
            for other_class in class_names[1:]:
                other_interface = available_classes[other_class]
                
                # Find differences
                only_in_base = base_interface - other_interface
                only_in_other = other_interface - base_interface
                
                if only_in_base or only_in_other:
                    interface_differences.append({
                        'classes': f"{base_class} vs {other_class}",
                        'only_in_first': list(only_in_base),
                        'only_in_second': list(only_in_other)
                    })

        # ASSERTION THAT SHOULD FAIL INITIALLY: All interfaces should be consistent
        if interface_differences:
            diff_details = []
            for diff in interface_differences:
                diff_details.append(
                    f"{diff['classes']}: "
                    f"first_only={diff['only_in_first'][:3]}{'...' if len(diff['only_in_first']) > 3 else ''}, "
                    f"second_only={diff['only_in_second'][:3]}{'...' if len(diff['only_in_second']) > 3 else ''}"
                )
            
            self.fail(
                f"SSOT VIOLATION: Interface inconsistencies found:\n" + 
                "\n".join(diff_details) +
                f"\nThis proves import interfaces are not standardized across implementations."
            )

    def test_import_path_canonicalization(self):
        """
        Test that there is one canonical import path for each class.
        
        EXPECTED INITIAL STATE: FAIL - Multiple import paths for same functionality
        EXPECTED POST-SSOT STATE: PASS - Single canonical import path per functionality
        
        VIOLATION BEING PROVED: Multiple import paths causing confusion and maintenance issues
        """
        # Define what the canonical import paths should be
        canonical_imports = {
            'WebSocketManagerFactory': 'netra_backend.app.websocket_core.websocket_manager_factory',
            'WebSocketManagerProtocol': 'netra_backend.app.core.interfaces_websocket',
            'WebSocketConnection': 'netra_backend.app.websocket_core.unified_manager',
        }
        
        # Find all actual import paths for each class
        actual_imports = {}
        
        # Search through common websocket modules
        search_modules = [
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.unified_manager', 
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.core.interfaces_websocket',
            'netra_backend.app.websocket_core.migration_adapter',
            'netra_backend.app.websocket_core.connection_manager',
        ]
        
        for module_path in search_modules:
            try:
                module = importlib.import_module(module_path)
                for class_name in canonical_imports.keys():
                    if hasattr(module, class_name):
                        if class_name not in actual_imports:
                            actual_imports[class_name] = []
                        actual_imports[class_name].append(module_path)
            except ImportError:
                # Expected for some modules
                pass
            except Exception as e:
                logger.warning(f"Error searching module {module_path}: {e}")

        # Check for violations
        canonicalization_violations = []
        
        for class_name, expected_canonical_path in canonical_imports.items():
            if class_name in actual_imports:
                actual_paths = actual_imports[class_name]
                
                # Multiple import paths violation
                if len(actual_paths) > 1:
                    canonicalization_violations.append(
                        f"{class_name}: found in {actual_paths}, expected only in {expected_canonical_path}"
                    )
                
                # Wrong canonical path violation  
                elif len(actual_paths) == 1 and actual_paths[0] != expected_canonical_path:
                    canonicalization_violations.append(
                        f"{class_name}: found in {actual_paths[0]}, expected in {expected_canonical_path}"
                    )
            else:
                # Missing canonical import violation
                canonicalization_violations.append(
                    f"{class_name}: not found in any module, expected in {expected_canonical_path}"
                )

        # ASSERTION THAT SHOULD FAIL INITIALLY: Canonical import paths should be enforced
        self.assertEqual(
            len(canonicalization_violations), 0,
            f"SSOT VIOLATION: Import canonicalization violations: {canonicalization_violations}. "
            f"This proves import paths are not properly standardized and canonical."
        )


if __name__ == '__main__':
    import unittest
    unittest.main()