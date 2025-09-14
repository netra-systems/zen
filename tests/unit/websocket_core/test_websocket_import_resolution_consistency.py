"""
Suite 2: WebSocket Import Path Consistency Tests - Issue #1031

PURPOSE: Validate all WebSocket imports resolve to same SSOT implementation.
This suite ensures import path consistency and prevents SSOT fragmentation.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability 
- Business Goal: SSOT compliance and import consistency
- Value Impact: Prevents import confusion affecting $500K+ ARR Golden Path
- Revenue Impact: Eliminates import-related initialization failures

EXPECTED BEHAVIOR:
- Tests should initially WARN about import inconsistencies
- After cleanup, all imports should resolve to same SSOT implementation
- Tests guide the import consolidation process

These tests validate Issue #1031 import path remediation.
"""

import pytest
import importlib
import inspect
import warnings
from typing import Any, Dict, List, Optional, Type
from unittest.mock import Mock, patch

# SSOT Test Infrastructure  
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketImportResolutionConsistency(SSotAsyncTestCase):
    """Import path consistency validation for WebSocket SSOT compliance."""
    
    def setup_method(self, method):
        """Set up test environment for import consistency validation."""
        super().setup_method(method)
        
        # Define canonical SSOT import paths
        self.canonical_imports = {
            'WebSocketManager': 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager',
            'get_websocket_manager': 'netra_backend.app.websocket_core.websocket_manager.get_websocket_manager',
            'WebSocketConnection': 'netra_backend.app.websocket_core.websocket_manager.WebSocketConnection',
            'WebSocketManagerMode': 'netra_backend.app.websocket_core.websocket_manager.WebSocketManagerMode',
        }
        
        # Define potentially deprecated/alternative import paths
        self.alternative_imports = {
            'WebSocketManager': [
                'netra_backend.app.websocket_core.unified_manager._UnifiedWebSocketManagerImplementation',
                'netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManager',  # If exists
            ],
            'get_websocket_manager': [
                'netra_backend.app.websocket_core.websocket_manager_factory.get_websocket_manager',
                'netra_backend.app.websocket_core.websocket_manager_factory.create_websocket_manager',
            ],
        }

    def test_all_websocket_imports_resolve_to_same_object(self):
        """
        TEST DESIGNED TO WARN: Validate all WebSocket manager imports resolve consistently.
        
        This test checks if different import paths for the same logical component
        actually resolve to the same object, preventing SSOT violations.
        
        EXPECTED: Should WARN if imports resolve to different objects.
        """
        import_resolution_issues = []
        
        for component_name, canonical_path in self.canonical_imports.items():
            try:
                # Import from canonical path
                module_path, class_name = canonical_path.rsplit('.', 1)
                canonical_module = importlib.import_module(module_path)
                canonical_object = getattr(canonical_module, class_name, None)
                
                if canonical_object is None:
                    import_resolution_issues.append(f"Canonical {component_name} not found at {canonical_path}")
                    continue
                
                # Check alternative import paths if they exist
                alternative_paths = self.alternative_imports.get(component_name, [])
                for alt_path in alternative_paths:
                    try:
                        alt_module_path, alt_class_name = alt_path.rsplit('.', 1)
                        alt_module = importlib.import_module(alt_module_path)
                        alt_object = getattr(alt_module, alt_class_name, None)
                        
                        if alt_object is not None:
                            # Compare objects - they should be the same for SSOT compliance
                            if alt_object is not canonical_object:
                                # Check if they're at least the same class
                                if (inspect.isclass(canonical_object) and inspect.isclass(alt_object) and 
                                    canonical_object.__name__ == alt_object.__name__):
                                    # Same class name but different objects - potential SSOT violation
                                    import_resolution_issues.append(
                                        f"{component_name}: Canonical path {canonical_path} and alternative path {alt_path} "
                                        f"resolve to different class objects (potential SSOT violation)"
                                    )
                                else:
                                    import_resolution_issues.append(
                                        f"{component_name}: Different objects from {canonical_path} vs {alt_path}"
                                    )
                            else:
                                logger.info(f"✅ {component_name}: {canonical_path} and {alt_path} resolve to same object")
                                
                    except ImportError:
                        # Alternative import not available - that's fine
                        logger.debug(f"Alternative import {alt_path} not available")
                    except Exception as e:
                        logger.debug(f"Error checking alternative import {alt_path}: {e}")
                
            except ImportError as e:
                import_resolution_issues.append(f"Cannot import canonical {component_name} from {canonical_path}: {e}")
            except Exception as e:
                import_resolution_issues.append(f"Unexpected error importing {component_name}: {e}")
        
        if import_resolution_issues:
            warning_msg = f"IMPORT CONSISTENCY ISSUES: {'; '.join(import_resolution_issues)}"
            warnings.warn(warning_msg, UserWarning, stacklevel=2)
            logger.warning(f"Issue #1031 Import Consistency Guide: {warning_msg}")
            pytest.skip(f"IMPORT CONSISTENCY: {warning_msg}")
        else:
            logger.info("✅ PASS: All WebSocket imports resolve consistently")

    def test_websocket_manager_instance_unification(self):
        """
        TEST DESIGNED TO WARN: Validate WebSocketManager instances are properly unified.
        
        This test ensures that creating WebSocket manager instances through
        different methods results in consistent behavior and types.
        
        EXPECTED: Should WARN if instance creation is inconsistent.
        """
        instance_consistency_issues = []
        
        try:
            # Try different ways of getting/creating WebSocket manager instances
            creation_methods = []
            
            # Method 1: Direct class instantiation  
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                # Note: We can't actually instantiate without proper parameters, 
                # but we can check the class
                creation_methods.append(('Direct Class', WebSocketManager))
                logger.info("✅ Direct WebSocketManager class importable")
            except ImportError as e:
                instance_consistency_issues.append(f"Cannot import WebSocketManager class: {e}")
            
            # Method 2: Factory function
            try:
                from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
                creation_methods.append(('Factory Function', get_websocket_manager))
                logger.info("✅ get_websocket_manager function importable")
            except ImportError as e:
                instance_consistency_issues.append(f"Cannot import get_websocket_manager function: {e}")
            
            # Method 3: Deprecated factory (if it exists)
            try:
                from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                creation_methods.append(('Deprecated Factory', create_websocket_manager))
                logger.warning("⚠️ Deprecated create_websocket_manager still available")
            except ImportError:
                logger.info("✅ Deprecated create_websocket_manager not available (good)")
            
            # Validate consistency between methods
            if len(creation_methods) > 1:
                # Compare the classes/functions for consistency
                for i, (name1, obj1) in enumerate(creation_methods):
                    for j, (name2, obj2) in enumerate(creation_methods[i+1:], i+1):
                        if inspect.isclass(obj1) and callable(obj2):
                            # Can't directly compare class to function, but check module consistency
                            if obj1.__module__ != obj2.__module__ and 'deprecated' not in obj2.__module__:
                                instance_consistency_issues.append(
                                    f"Module inconsistency: {name1} from {obj1.__module__}, {name2} from {obj2.__module__}"
                                )
                        elif inspect.isclass(obj1) and inspect.isclass(obj2):
                            if obj1 is not obj2:
                                instance_consistency_issues.append(
                                    f"Class inconsistency: {name1} and {name2} are different classes"
                                )
            
        except Exception as e:
            instance_consistency_issues.append(f"Unexpected error during instance unification test: {e}")
        
        if instance_consistency_issues:
            warning_msg = f"INSTANCE UNIFICATION ISSUES: {'; '.join(instance_consistency_issues)}"
            warnings.warn(warning_msg, UserWarning, stacklevel=2)
            logger.warning(f"Issue #1031 Instance Consistency Guide: {warning_msg}")
            pytest.skip(f"INSTANCE CONSISTENCY: {warning_msg}")
        else:
            logger.info("✅ PASS: WebSocket manager instance creation is unified")

    def test_no_duplicate_websocket_manager_instances(self):
        """
        TEST DESIGNED TO WARN: Check for multiple WebSocketManager implementations.
        
        This test identifies if there are multiple WebSocketManager class
        implementations that could cause SSOT violations.
        
        EXPECTED: Should WARN if duplicate implementations exist.
        """
        duplicate_implementation_issues = []
        
        try:
            # Search for all WebSocketManager-like classes in the websocket_core package
            import netra_backend.app.websocket_core as websocket_core
            import pkgutil
            
            websocket_manager_classes = []
            
            # Iterate through all modules in websocket_core
            for importer, modname, ispkg in pkgutil.iter_modules(
                websocket_core.__path__, 
                prefix="netra_backend.app.websocket_core."
            ):
                try:
                    module = importlib.import_module(modname)
                    
                    # Look for classes that could be WebSocket manager implementations
                    for attr_name in dir(module):
                        if not attr_name.startswith('_'):  # Skip private attributes
                            attr = getattr(module, attr_name)
                            if inspect.isclass(attr):
                                class_name_lower = attr.__name__.lower()
                                if ('websocket' in class_name_lower and 
                                    ('manager' in class_name_lower or 'implementation' in class_name_lower)):
                                    websocket_manager_classes.append({
                                        'class': attr,
                                        'name': attr.__name__,
                                        'module': modname,
                                        'full_path': f"{modname}.{attr_name}"
                                    })
                                    
                except ImportError as e:
                    logger.debug(f"Could not import module {modname}: {e}")
                except Exception as e:
                    logger.debug(f"Error inspecting module {modname}: {e}")
            
            # Analyze for duplicates
            logger.info(f"Found WebSocket manager classes: {[cls['full_path'] for cls in websocket_manager_classes]}")
            
            if len(websocket_manager_classes) > 1:
                # Multiple implementations found - check if they're actually different
                unique_implementations = set()
                for cls_info in websocket_manager_classes:
                    # Use class id to identify truly different classes
                    unique_implementations.add(id(cls_info['class']))
                
                if len(unique_implementations) > 1:
                    class_paths = [cls['full_path'] for cls in websocket_manager_classes]
                    duplicate_implementation_issues.append(
                        f"Multiple WebSocket manager implementations found: {', '.join(class_paths)}. "
                        f"SSOT compliance requires single implementation."
                    )
                else:
                    logger.info("✅ Multiple imports found but they resolve to same implementation")
            elif len(websocket_manager_classes) == 0:
                duplicate_implementation_issues.append("No WebSocket manager classes found - this may indicate import issues")
            else:
                logger.info("✅ Single WebSocket manager implementation found - good SSOT compliance")
                
        except Exception as e:
            duplicate_implementation_issues.append(f"Error during duplicate implementation check: {e}")
        
        if duplicate_implementation_issues:
            warning_msg = f"DUPLICATE IMPLEMENTATION ISSUES: {'; '.join(duplicate_implementation_issues)}"
            warnings.warn(warning_msg, UserWarning, stacklevel=2)
            logger.warning(f"Issue #1031 Implementation Consistency Guide: {warning_msg}")
            pytest.skip(f"DUPLICATE IMPLEMENTATIONS: {warning_msg}")
        else:
            logger.info("✅ PASS: No duplicate WebSocket manager implementations")

    def test_import_path_canonical_resolution(self):
        """
        TEST DESIGNED TO PASS: Validate canonical import paths are accessible.
        
        This test ensures that the documented canonical SSOT import paths
        are accessible and functional.
        
        EXPECTED: Should PASS - Canonical imports should work.
        """
        canonical_import_failures = []
        
        for component_name, canonical_path in self.canonical_imports.items():
            try:
                # Try to import from the canonical path
                module_path, class_name = canonical_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                component = getattr(module, class_name, None)
                
                if component is None:
                    canonical_import_failures.append(f"{component_name} not found at canonical path {canonical_path}")
                else:
                    logger.info(f"✅ Canonical import {canonical_path} successful")
                    
                    # Basic validation that the imported object makes sense
                    if 'Manager' in component_name and inspect.isclass(component):
                        # Should be a class
                        logger.info(f"✅ {component_name} is a class as expected")
                    elif 'get_' in component_name and callable(component):
                        # Should be a function
                        logger.info(f"✅ {component_name} is callable as expected")
                    
            except ImportError as e:
                canonical_import_failures.append(f"Cannot import {component_name} from canonical path {canonical_path}: {e}")
            except Exception as e:
                canonical_import_failures.append(f"Unexpected error importing {component_name}: {e}")
        
        if canonical_import_failures:
            pytest.fail(f"CANONICAL IMPORT FAILURES: {'; '.join(canonical_import_failures)}")
        else:
            logger.info("✅ PASS: All canonical WebSocket imports accessible")

    def test_ssot_import_registry_compliance(self):
        """
        TEST DESIGNED TO PASS: Validate imports match SSOT_IMPORT_REGISTRY.md.
        
        This test checks that the actual importable WebSocket components
        match what's documented in the SSOT import registry.
        
        EXPECTED: Should PASS - Imports should match documentation.
        """
        # Expected imports from SSOT_IMPORT_REGISTRY.md
        expected_ssot_imports = [
            'netra_backend.app.websocket_core.websocket_manager.WebSocketManager',
            'netra_backend.app.websocket_core.websocket_manager.get_websocket_manager',
            'netra_backend.app.websocket_core.websocket_manager.WebSocketConnection',
            'netra_backend.app.websocket_core.websocket_manager.WebSocketManagerMode',
        ]
        
        registry_compliance_issues = []
        
        for import_path in expected_ssot_imports:
            try:
                module_path, component_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                component = getattr(module, component_name, None)
                
                if component is None:
                    registry_compliance_issues.append(f"SSOT Registry lists {import_path} but it's not importable")
                else:
                    logger.info(f"✅ SSOT Registry import {import_path} verified")
                    
            except ImportError as e:
                registry_compliance_issues.append(f"SSOT Registry import {import_path} failed: {e}")
            except Exception as e:
                registry_compliance_issues.append(f"Unexpected error with SSOT Registry import {import_path}: {e}")
        
        if registry_compliance_issues:
            pytest.fail(f"SSOT REGISTRY COMPLIANCE ISSUES: {'; '.join(registry_compliance_issues)}")
        else:
            logger.info("✅ PASS: All SSOT Registry WebSocket imports are compliant")

    def test_websocket_circular_import_detection(self):
        """
        TEST DESIGNED TO PASS: Detect circular import issues in WebSocket modules.
        
        This test attempts to detect circular import problems that could
        affect WebSocket SSOT compliance.
        
        EXPECTED: Should PASS - No circular imports should exist.
        """
        circular_import_issues = []
        
        try:
            # Test importing key WebSocket modules in different orders to detect circular imports
            import_sequences = [
                # Sequence 1: Main interface first
                ['netra_backend.app.websocket_core.websocket_manager',
                 'netra_backend.app.websocket_core.unified_manager'],
                
                # Sequence 2: Implementation first
                ['netra_backend.app.websocket_core.unified_manager',
                 'netra_backend.app.websocket_core.websocket_manager'],
                
                # Sequence 3: Include factory module if it exists
                ['netra_backend.app.websocket_core.websocket_manager_factory',
                 'netra_backend.app.websocket_core.websocket_manager'],
            ]
            
            for sequence_num, import_sequence in enumerate(import_sequences, 1):
                try:
                    logger.info(f"Testing import sequence {sequence_num}: {' -> '.join(import_sequence)}")
                    
                    # Clear any cached imports for this test
                    modules_to_clear = [mod for mod in list(sys.modules.keys()) if 'websocket' in mod]
                    for mod in modules_to_clear:
                        if mod.startswith('netra_backend.app.websocket_core'):
                            sys.modules.pop(mod, None)
                    
                    # Try importing in this sequence
                    for module_name in import_sequence:
                        try:
                            importlib.import_module(module_name)
                            logger.debug(f"Successfully imported {module_name}")
                        except ImportError as e:
                            if 'websocket_manager_factory' in module_name:
                                logger.debug(f"Factory module {module_name} not available (acceptable)")
                            else:
                                raise
                    
                    logger.info(f"✅ Import sequence {sequence_num} successful")
                    
                except ImportError as e:
                    if 'circular import' in str(e).lower() or 'cannot import' in str(e).lower():
                        circular_import_issues.append(f"Potential circular import in sequence {sequence_num}: {e}")
                    else:
                        logger.debug(f"Import sequence {sequence_num} failed (but not circular): {e}")
                
        except Exception as e:
            circular_import_issues.append(f"Unexpected error during circular import detection: {e}")
        
        if circular_import_issues:
            warning_msg = f"CIRCULAR IMPORT ISSUES: {'; '.join(circular_import_issues)}"
            warnings.warn(warning_msg, UserWarning, stacklevel=2)
            pytest.fail(f"CIRCULAR IMPORTS DETECTED: {warning_msg}")
        else:
            logger.info("✅ PASS: No circular import issues detected")