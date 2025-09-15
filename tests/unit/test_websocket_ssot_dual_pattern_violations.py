"""
Unit tests for WebSocket SSOT dual pattern fragmentation violations.

This test file validates the detection and reproduction of dual pattern
violations where multiple WebSocket manager implementations are active
simultaneously, causing SSOT violations and potential race conditions.

Issue #1126 - WebSocket Factory Dual Pattern Fragmentation

Business Value Protection: $500K+ ARR Golden Path reliability
Priority: Critical infrastructure protection
"""

import pytest
import logging
import inspect
import importlib
import sys
from typing import Set, Dict, Any, List, Tuple
from unittest.mock import patch, MagicMock, Mock

from test_framework.ssot.base_test_case import SSotBaseTestCase, CategoryType


logger = logging.getLogger(__name__)


@pytest.mark.unit
class TestWebSocketSSOTDualPatternViolations(SSotBaseTestCase):
    """Test WebSocket SSOT dual pattern violations detection."""
    
    def setup_method(self, method):
        """Set up test with WebSocket-specific categories."""
        super().setup_method(method)
        if self._test_context:
            self._test_context.test_category = CategoryType.CRITICAL
            self._test_context.metadata.update({
                'business_impact': '$500K+ ARR',
                'issue': '#1126',
                'test_type': 'dual_pattern_detection'
            })
    
    def test_websocket_manager_import_path_dual_pattern_detection(self):
        """Test detection of dual import patterns for WebSocketManager.
        
        EXPECTED FAILURE: This test should FAIL to demonstrate the dual pattern issue exists.
        """
        logger.info("Testing WebSocket manager import path dual pattern detection")
        
        # Track different import paths that should resolve to same SSOT
        websocket_manager_imports = [
            "netra_backend.app.websocket_core.manager.WebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager", 
            "netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManager",
        ]
        
        imported_classes = []
        import_results = {}
        
        # Test each import path
        for import_path in websocket_manager_imports:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                websocket_class = getattr(module, class_name, None)
                
                if websocket_class:
                    imported_classes.append((import_path, websocket_class))
                    import_results[import_path] = {
                        'success': True,
                        'class_id': id(websocket_class),
                        'class_name': websocket_class.__name__,
                        'module': websocket_class.__module__
                    }
                else:
                    import_results[import_path] = {
                        'success': False,
                        'error': f"Class {class_name} not found in {module_path}"
                    }
                    
            except ImportError as e:
                import_results[import_path] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Record metrics for dual pattern analysis
        self.record_metric('import_paths_tested', len(websocket_manager_imports))
        self.record_metric('successful_imports', len(imported_classes))
        self.record_metric('import_results', import_results)
        
        logger.info(f"Import results: {import_results}")
        
        # CRITICAL TEST: All successful imports should resolve to SAME class object (SSOT)
        if len(imported_classes) > 1:
            reference_class = imported_classes[0][1]
            dual_patterns_detected = []
            
            for import_path, websocket_class in imported_classes[1:]:
                if websocket_class is not reference_class:
                    dual_patterns_detected.append({
                        'reference': imported_classes[0][0],
                        'reference_id': id(reference_class),
                        'duplicate': import_path,
                        'duplicate_id': id(websocket_class),
                        'same_object': websocket_class is reference_class
                    })
            
            self.record_metric('dual_patterns_detected', len(dual_patterns_detected))
            self.record_metric('dual_pattern_details', dual_patterns_detected)
            
            # EXPECTED FAILURE: This assertion should FAIL if dual patterns exist
            assert len(dual_patterns_detected) == 0, (
                f"SSOT VIOLATION: Found {len(dual_patterns_detected)} dual patterns in WebSocket managers. "
                f"All imports should resolve to same class object. Violations: {dual_patterns_detected}"
            )
        
        # If we reach here, SSOT compliance is maintained (unexpected for Issue #1126)
        logger.info("No dual patterns detected - SSOT compliance maintained")
    
    def test_websocket_factory_pattern_duplication_detection(self):
        """Test detection of duplicated factory patterns.
        
        EXPECTED FAILURE: Should detect multiple factory patterns violating SSOT.
        """
        logger.info("Testing WebSocket factory pattern duplication")
        
        factory_patterns = [
            "netra_backend.app.websocket_core.websocket_manager_factory",
            "netra_backend.app.services.websocket_bridge_factory", 
            "netra_backend.app.websocket_core.manager",  # Has create functions
        ]
        
        detected_factories = []
        factory_functions = {}
        
        for factory_module_path in factory_patterns:
            try:
                module = importlib.import_module(factory_module_path)
                
                # Look for factory functions and classes
                factory_items = []
                for name, obj in inspect.getmembers(module):
                    if (name.startswith('create_') and callable(obj)) or \
                       (name.endswith('Factory') and inspect.isclass(obj)):
                        factory_items.append({
                            'name': name,
                            'type': 'function' if callable(obj) and not inspect.isclass(obj) else 'class',
                            'module': factory_module_path
                        })
                
                if factory_items:
                    detected_factories.append(factory_module_path)
                    factory_functions[factory_module_path] = factory_items
                    
            except ImportError as e:
                logger.debug(f"Factory module {factory_module_path} not available: {e}")
        
        self.record_metric('factory_modules_tested', len(factory_patterns))
        self.record_metric('factory_modules_found', len(detected_factories))
        self.record_metric('factory_functions', factory_functions)
        
        logger.info(f"Factory functions detected: {factory_functions}")
        
        # EXPECTED FAILURE: Should find multiple factory patterns (SSOT violation)
        total_factory_items = sum(len(items) for items in factory_functions.values())
        self.record_metric('total_factory_items', total_factory_items)
        
        # Check for SSOT violation - multiple factory patterns for same functionality
        websocket_factories = 0
        for module_path, items in factory_functions.items():
            for item in items:
                if 'websocket' in item['name'].lower() and 'manager' in item['name'].lower():
                    websocket_factories += 1
        
        self.record_metric('websocket_manager_factories', websocket_factories)
        
        # EXPECTED FAILURE: Should detect multiple WebSocket manager factories
        assert websocket_factories <= 1, (
            f"SSOT VIOLATION: Found {websocket_factories} WebSocket manager factory patterns. "
            f"SSOT requires exactly 1 canonical factory. Detected patterns: {factory_functions}"
        )
        
        logger.info("No duplicate factory patterns detected - SSOT compliance maintained")
    
    def test_websocket_manager_inheritance_fragmentation(self):
        """Test detection of inheritance fragmentation in WebSocket managers.
        
        EXPECTED FAILURE: Should detect multiple inheritance hierarchies violating SSOT.
        """
        logger.info("Testing WebSocket manager inheritance fragmentation")
        
        # Import potential WebSocket manager classes
        websocket_classes = []
        
        manager_modules = [
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.websocket_core.websocket_manager", 
            "netra_backend.app.websocket_core.unified_manager",
        ]
        
        for module_path in manager_modules:
            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        'websocket' in name.lower() and 
                        'manager' in name.lower()):
                        websocket_classes.append((name, obj, module_path))
            except ImportError:
                continue
        
        self.record_metric('websocket_manager_classes_found', len(websocket_classes))
        
        # Analyze inheritance hierarchies
        inheritance_trees = {}
        for class_name, cls, module_path in websocket_classes:
            mro = inspect.getmro(cls)
            base_classes = [base.__name__ for base in mro[1:]]  # Exclude self
            inheritance_trees[f"{module_path}.{class_name}"] = {
                'class': class_name,
                'module': module_path,
                'bases': base_classes,
                'mro_length': len(mro)
            }
        
        self.record_metric('inheritance_trees', inheritance_trees)
        logger.info(f"Inheritance analysis: {inheritance_trees}")
        
        # Check for SSOT violation - multiple independent inheritance hierarchies
        unique_hierarchies = set()
        for class_info in inheritance_trees.values():
            # Create signature of inheritance hierarchy
            hierarchy_signature = tuple(sorted(class_info['bases']))
            unique_hierarchies.add(hierarchy_signature)
        
        self.record_metric('unique_inheritance_patterns', len(unique_hierarchies))
        
        # EXPECTED FAILURE: Should find multiple inheritance patterns (fragmentation)
        assert len(unique_hierarchies) <= 1, (
            f"SSOT VIOLATION: Found {len(unique_hierarchies)} different inheritance hierarchies "
            f"for WebSocket managers. SSOT requires unified hierarchy. "
            f"Patterns detected: {inheritance_trees}"
        )
        
        logger.info("No inheritance fragmentation detected - SSOT compliance maintained")
    
    def test_websocket_protocol_interface_duplication(self):
        """Test detection of duplicated protocol interfaces.
        
        EXPECTED FAILURE: Should detect multiple protocol definitions violating SSOT.
        """
        logger.info("Testing WebSocket protocol interface duplication")
        
        protocol_modules = [
            "netra_backend.app.websocket_core.protocols",
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.websocket_core.websocket_manager",
        ]
        
        protocol_interfaces = []
        
        for module_path in protocol_modules:
            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        ('protocol' in name.lower() or 
                         hasattr(obj, '__protocol__') or
                         name.endswith('Protocol'))):
                        protocol_interfaces.append((name, obj, module_path))
            except ImportError:
                continue
        
        self.record_metric('protocol_interfaces_found', len(protocol_interfaces))
        
        # Check for WebSocket-specific protocols
        websocket_protocols = []
        for name, obj, module_path in protocol_interfaces:
            if 'websocket' in name.lower():
                websocket_protocols.append({
                    'name': name,
                    'module': module_path,
                    'methods': [method for method in dir(obj) if not method.startswith('_')]
                })
        
        self.record_metric('websocket_protocols', len(websocket_protocols))
        self.record_metric('websocket_protocol_details', websocket_protocols)
        
        logger.info(f"WebSocket protocols found: {websocket_protocols}")
        
        # EXPECTED FAILURE: Should find multiple WebSocket protocol definitions
        assert len(websocket_protocols) <= 1, (
            f"SSOT VIOLATION: Found {len(websocket_protocols)} WebSocket protocol interfaces. "
            f"SSOT requires exactly 1 canonical protocol. Detected: {websocket_protocols}"
        )
        
        logger.info("No protocol duplication detected - SSOT compliance maintained")
    
    def test_websocket_event_system_fragmentation(self):
        """Test detection of fragmented event systems.
        
        EXPECTED FAILURE: Should detect multiple event emission patterns violating SSOT.
        """
        logger.info("Testing WebSocket event system fragmentation")
        
        # Look for event-related classes and functions
        event_modules = [
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.websocket_core.websocket_manager",
            "netra_backend.app.services.websocket_event_router",
            "netra_backend.app.services.websocket_bridge_factory",
        ]
        
        event_systems = {}
        
        for module_path in event_modules:
            try:
                module = importlib.import_module(module_path)
                event_methods = []
                
                for name, obj in inspect.getmembers(module):
                    if callable(obj) and ('emit' in name.lower() or 'send' in name.lower()):
                        event_methods.append(name)
                
                if event_methods:
                    event_systems[module_path] = event_methods
                    
            except ImportError:
                continue
        
        self.record_metric('event_system_modules', len(event_systems))
        self.record_metric('event_systems', event_systems)
        
        logger.info(f"Event systems detected: {event_systems}")
        
        # Check for SSOT violation - multiple event emission patterns
        total_event_methods = sum(len(methods) for methods in event_systems.values())
        self.record_metric('total_event_methods', total_event_methods)
        
        # Look for WebSocket-specific event methods
        websocket_event_methods = 0
        for module_path, methods in event_systems.items():
            for method in methods:
                if 'websocket' in method.lower():
                    websocket_event_methods += 1
        
        self.record_metric('websocket_event_methods', websocket_event_methods)
        
        # EXPECTED FAILURE: Should find fragmented event systems
        assert len(event_systems) <= 1, (
            f"SSOT VIOLATION: Found {len(event_systems)} different WebSocket event systems. "
            f"SSOT requires unified event emission. Systems: {event_systems}"
        )
        
        logger.info("No event system fragmentation detected - SSOT compliance maintained")