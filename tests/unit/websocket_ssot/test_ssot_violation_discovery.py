"""
Core SSOT Violation Discovery Tests - Issue #186 WebSocket Manager Fragmentation

Tests that systematically discover all WebSocket manager implementations in the codebase.
These tests are designed to FAIL initially, proving that multiple WebSocket manager 
implementations exist that violate the Single Source of Truth (SSOT) principle.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Stability - Identify fragmentation blocking golden path chat functionality
- Value Impact: Discover root cause of $500K+ ARR chat reliability issues
- Revenue Impact: Enable systematic consolidation to prevent customer chat disruptions

SSOT Violations This Module Proves:
1. Multiple WebSocket manager class implementations exist
2. Factory creation patterns are inconsistent
3. Constructor signatures vary between implementations
4. Import paths fragment access patterns
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import os
import inspect
import importlib
import pkgutil
import unittest
from typing import Any, Dict, List, Set, Type, Optional, Tuple
from pathlib import Path

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerSSotViolationDiscovery(SSotBaseTestCase):
    """
    Core tests to systematically discover WebSocket manager SSOT violations.
    
    These tests are designed to FAIL initially, proving fragmentation exists.
    After SSOT consolidation, they should PASS, proving unification worked.
    """

    def test_discover_all_websocket_manager_implementations(self):
        """
        Discover all WebSocket manager class implementations in codebase.
        
        EXPECTED INITIAL STATE: FAIL - 6+ manager implementations found
        EXPECTED POST-SSOT STATE: PASS - Only 1 canonical manager implementation
        
        VIOLATION BEING PROVED: Multiple manager implementations exist
        """
        manager_implementations = []
        websocket_modules = []
        
        # Scan for all WebSocket-related modules
        netra_backend_path = Path(__file__).parents[3] / "netra_backend"
        
        try:
            for root, dirs, files in os.walk(netra_backend_path):
                for file in files:
                    if file.endswith('.py') and 'websocket' in file.lower():
                        module_path = Path(root) / file
                        relative_path = module_path.relative_to(netra_backend_path.parent)
                        module_name = str(relative_path).replace('/', '.').replace('\\', '.')[:-3]
                        websocket_modules.append(module_name)
                        
        except Exception as e:
            logger.warning(f"Could not scan filesystem for WebSocket modules: {e}")
            
        # Known WebSocket module locations to check
        known_websocket_modules = [
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.unified_manager', 
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.websocket_core.migration_adapter',
            'netra_backend.app.websocket_core.unified',
            'netra_backend.app.routes.websocket',
            'netra_backend.app.routes.websocket_ssot',
            'netra_backend.app.core.interfaces_websocket',
        ]
        
        all_modules = list(set(websocket_modules + known_websocket_modules))
        
        # Check each module for WebSocket manager classes
        for module_name in all_modules:
            try:
                module = importlib.import_module(module_name)
                
                # Look for classes that look like WebSocket managers
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if ('websocket' in name.lower() and 
                        ('manager' in name.lower() or 'handler' in name.lower())):
                        
                        # Skip imported classes (check if defined in this module)
                        if obj.__module__ == module_name:
                            manager_implementations.append({
                                'module': module_name,
                                'class_name': name,
                                'class': obj,
                                'methods': [m for m in dir(obj) if not m.startswith('_')],
                                'constructor_params': list(inspect.signature(obj.__init__).parameters.keys())
                            })
                            
            except ImportError:
                continue
            except Exception as e:
                logger.warning(f"Error checking module {module_name}: {e}")
                continue
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Should find only 1 manager implementation
        self.assertEqual(
            len(manager_implementations), 1,
            f"SSOT VIOLATION: Found {len(manager_implementations)} WebSocket manager implementations. "
            f"Expected exactly 1 for SSOT compliance. Found: {[impl['module'] + '.' + impl['class_name'] for impl in manager_implementations]}. "
            f"This proves manager fragmentation exists."
        )

    def test_factory_creation_pattern_consistency(self):
        """
        Test all factory patterns create managers consistently.
        
        EXPECTED INITIAL STATE: FAIL - Different factory patterns exist
        EXPECTED POST-SSOT STATE: PASS - Single consistent factory pattern
        
        VIOLATION BEING PROVED: Factory creation patterns are inconsistent
        """
        factory_patterns = []
        factory_violations = []
        
        # Known factory patterns to test
        factory_modules = [
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.migration_adapter',
            'netra_backend.app.agents.supervisor.agent_registry',
        ]
        
        for module_name in factory_modules:
            try:
                module = importlib.import_module(module_name)
                
                # Look for factory classes and methods
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and 'factory' in name.lower():
                        factory_methods = []
                        
                        for method_name, method in inspect.getmembers(obj, inspect.ismethod):
                            if 'create' in method_name.lower() or 'get' in method_name.lower():
                                try:
                                    sig = inspect.signature(method)
                                    factory_methods.append({
                                        'method': method_name,
                                        'params': list(sig.parameters.keys()),
                                        'return_annotation': sig.return_annotation
                                    })
                                except Exception:
                                    pass
                        
                        if factory_methods:
                            factory_patterns.append({
                                'module': module_name,
                                'factory_class': name,
                                'methods': factory_methods
                            })
                            
                    elif (callable(obj) and 
                          ('create' in name.lower() or 'get' in name.lower()) and
                          'websocket' in name.lower()):
                        # Function-level factory patterns
                        try:
                            sig = inspect.signature(obj)
                            factory_patterns.append({
                                'module': module_name,
                                'factory_function': name,
                                'params': list(sig.parameters.keys()),
                                'return_annotation': sig.return_annotation
                            })
                        except Exception:
                            pass
                            
            except ImportError:
                continue
            except Exception as e:
                logger.warning(f"Error checking factory module {module_name}: {e}")
                continue
        
        # Check for consistency across factory patterns
        if len(factory_patterns) > 1:
            # Test parameter consistency
            param_patterns = set()
            for pattern in factory_patterns:
                if 'methods' in pattern:
                    for method in pattern['methods']:
                        param_patterns.add(tuple(method['params']))
                else:
                    param_patterns.add(tuple(pattern['params']))
                    
            if len(param_patterns) > 1:
                factory_violations.append(
                    f"Inconsistent parameter patterns: {param_patterns}"
                )
                
            # Test return type consistency
            return_types = set()
            for pattern in factory_patterns:
                if 'methods' in pattern:
                    for method in pattern['methods']:
                        return_types.add(str(method['return_annotation']))
                else:
                    return_types.add(str(pattern['return_annotation']))
                    
            if len(return_types) > 1:
                factory_violations.append(
                    f"Inconsistent return types: {return_types}"
                )
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Should have consistent factory patterns
        self.assertEqual(
            len(factory_violations), 0,
            f"SSOT VIOLATION: Factory pattern inconsistencies found: {factory_violations}. "
            f"Factory patterns discovered: {factory_patterns}. "
            f"This proves factory creation patterns need standardization."
        )

    def test_constructor_signature_standardization(self):
        """
        Test all manager constructors have standardized signatures.
        
        EXPECTED INITIAL STATE: FAIL - Constructor signatures vary
        EXPECTED POST-SSOT STATE: PASS - All constructors have same signature
        
        VIOLATION BEING PROVED: Constructor signatures vary between implementations
        """
        constructor_signatures = {}
        signature_violations = []
        
        # Manager classes to check
        manager_classes = []
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager_classes.append(('UnifiedWebSocketManager', UnifiedWebSocketManager))
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            manager_classes.append(('WebSocketManager', WebSocketManager))
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WSM
            manager_classes.append(('websocket_manager.WebSocketManager', WSM))
        except ImportError:
            pass
        
        # Analyze constructor signatures
        for name, cls in manager_classes:
            try:
                init_sig = inspect.signature(cls.__init__)
                params = list(init_sig.parameters.keys())
                param_types = {}
                
                for param_name, param in init_sig.parameters.items():
                    param_types[param_name] = {
                        'annotation': param.annotation,
                        'default': param.default,
                        'kind': param.kind
                    }
                
                constructor_signatures[name] = {
                    'param_names': params,
                    'param_types': param_types,
                    'param_count': len(params)
                }
                
            except Exception as e:
                signature_violations.append(f"Could not analyze {name} constructor: {e}")
        
        # Check for signature consistency
        if len(constructor_signatures) > 1:
            param_counts = {name: sig['param_count'] for name, sig in constructor_signatures.items()}
            unique_counts = set(param_counts.values())
            
            if len(unique_counts) > 1:
                signature_violations.append(
                    f"Inconsistent parameter counts: {param_counts}"
                )
                
            # Check parameter name consistency (excluding 'self')
            param_name_sets = []
            for name, sig in constructor_signatures.items():
                params = [p for p in sig['param_names'] if p != 'self']
                param_name_sets.append((name, set(params)))
                
            if len(param_name_sets) > 1:
                first_set = param_name_sets[0][1]
                for name, param_set in param_name_sets[1:]:
                    if param_set != first_set:
                        signature_violations.append(
                            f"Parameter names differ between {param_name_sets[0][0]} and {name}: "
                            f"{first_set} vs {param_set}"
                        )
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Constructor signatures should be standardized
        self.assertEqual(
            len(signature_violations), 0,
            f"SSOT VIOLATION: Constructor signature inconsistencies: {signature_violations}. "
            f"Signatures found: {constructor_signatures}. "
            f"This proves constructor signatures need standardization."
        )

    def test_import_path_fragmentation(self):
        """
        Test that import paths are not fragmented across modules.
        
        EXPECTED INITIAL STATE: FAIL - Multiple import paths for same functionality
        EXPECTED POST-SSOT STATE: PASS - Single canonical import path per class
        
        VIOLATION BEING PROVED: Import paths fragment access to same functionality
        """
        import_violations = []
        websocket_classes = {}
        
        # Core WebSocket class names to track
        target_classes = [
            'WebSocketManager',
            'UnifiedWebSocketManager', 
            'WebSocketManagerFactory',
            'WebSocketProtocol',
            'WebSocketManagerProtocol',
            'WebSocketConnection'
        ]
        
        # Modules where these might be imported
        check_modules = [
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.websocket_core.migration_adapter',
            'netra_backend.app.core.interfaces_websocket',
        ]
        
        # Check where each class can be imported from
        for class_name in target_classes:
            import_locations = []
            
            for module_name in check_modules:
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, class_name):
                        cls = getattr(module, class_name)
                        import_locations.append({
                            'module': module_name,
                            'class': cls,
                            'is_alias': cls.__module__ != module_name
                        })
                except ImportError:
                    continue
                except Exception:
                    continue
            
            websocket_classes[class_name] = import_locations
            
            # Check for fragmentation
            if len(import_locations) > 1:
                # Multiple import paths found
                actual_classes = set(id(loc['class']) for loc in import_locations)
                if len(actual_classes) == 1:
                    # Same class, multiple import paths (alias fragmentation)
                    import_violations.append(
                        f"{class_name} available from {len(import_locations)} import paths: "
                        f"{[loc['module'] for loc in import_locations]}"
                    )
                else:
                    # Different classes with same name (naming collision)
                    import_violations.append(
                        f"{class_name} has {len(actual_classes)} different implementations across modules: "
                        f"{[loc['module'] for loc in import_locations]}"
                    )
        
        # ASSERTION THAT SHOULD FAIL INITIALLY: Each class should have one canonical import path
        self.assertEqual(
            len(import_violations), 0,
            f"SSOT VIOLATION: Import path fragmentation found: {import_violations}. "
            f"Import analysis: {websocket_classes}. "
            f"This proves import paths need consolidation."
        )


if __name__ == '__main__':
    unittest.main()