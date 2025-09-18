"""WebSocket Manager SSOT Violations Test Suite

PURPOSE: Detect and validate WebSocket manager SSOT violations for Issue #1182
BUSINESS VALUE: Protects $500K+ ARR Golden Path functionality by ensuring single source of truth

This test suite MUST FAIL with current fragmented state and PASS after SSOT consolidation.

CRITICAL: These tests follow claude.md requirements:
- NO Docker dependencies 
- Failing tests first approach
- SSOT validation focus
- Real services only (no mocks in integration)
"""

import pytest
import sys
import unittest
import importlib
import inspect
from typing import Dict, List, Set, Tuple, Any, Type
from unittest.mock import patch
import warnings

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
class WebSocketManagerSSOTViolationsTests(SSotBaseTestCase):
    """Test suite to detect WebSocket Manager SSOT violations.
    
    These tests MUST FAIL with current fragmented state to prove violations exist.
    After SSOT consolidation, they MUST PASS to prove single source of truth.
    """

    def setUp(self):
        """Set up test environment for SSOT violation detection."""
        super().setUp()
        self.websocket_manager_classes = {}
        self.import_paths = []
        self.detected_violations = []
        
    @property
    def detected_violations(self):
        """Ensure detected_violations is always available."""
        if not hasattr(self, '_detected_violations'):
            self._detected_violations = []
        return self._detected_violations
        
    @detected_violations.setter
    def detected_violations(self, value):
        self._detected_violations = value
        
    def test_multiple_websocket_manager_implementations_detected(self):
        """
        CRITICAL TEST: Detect multiple WebSocket manager class implementations
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Multiple WebSocket manager classes found
        - MUST PASS (after SSOT): Only one canonical WebSocket manager class
        """
        logger.info("Testing for multiple WebSocket manager implementations...")
        
        # Test different import paths that should resolve to SAME class
        import_paths_to_test = [
            "netra_backend.app.websocket_core.manager.WebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager", 
            "netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager.WebSocketConnectionManager",
            "netra_backend.app.websocket_core.unified_manager._UnifiedWebSocketManagerImplementation"
        ]
        
        imported_classes = {}
        import_failures = []
        
        for import_path in import_paths_to_test:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                imported_classes[import_path] = cls
                logger.info(f"Successfully imported {import_path}: {cls}")
            except (ImportError, AttributeError) as e:
                import_failures.append(f"{import_path}: {e}")
                logger.warning(f"Failed to import {import_path}: {e}")
        
        # Check if multiple DIFFERENT classes exist (SSOT violation)
        unique_classes = set(imported_classes.values())
        
        if len(unique_classes) > 1:
            self.detected_violations.append(f"SSOT VIOLATION: Found {len(unique_classes)} different WebSocket manager classes")
            for path, cls in imported_classes.items():
                self.detected_violations.append(f"  - {path}: {cls} (id: {id(cls)})")
        
        # ASSERTION: This MUST FAIL currently (proving violations exist)
        # After SSOT consolidation, this MUST PASS (proving single source)
        self.assertEqual(len(unique_classes), 1, 
                        f"SSOT VIOLATION: Multiple WebSocket manager classes detected. "
                        f"Found {len(unique_classes)} unique classes: {unique_classes}. "
                        f"Import failures: {import_failures}. "
                        f"All violations: {self.detected_violations}")

    def test_websocket_manager_import_path_fragmentation(self):
        """
        CRITICAL TEST: Detect import path fragmentation across codebase
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Multiple import paths for WebSocket managers
        - MUST PASS (after SSOT): Single canonical import path used everywhere
        """
        logger.info("Testing for WebSocket manager import path fragmentation...")
        
        # Search for WebSocket manager import patterns in loaded modules
        fragmented_imports = []
        websocket_modules = []
        
        # Create snapshot to avoid runtime modifications during iteration
        modules_snapshot = dict(sys.modules.items())
        
        for module_name, module in modules_snapshot.items():
            if module is None:
                continue
                
            # Look for WebSocket-related modules
            if 'websocket' in module_name.lower():
                websocket_modules.append(module_name)
                
                # Check for manager classes in this module
                try:
                    if hasattr(module, '__dict__'):
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name, None)
                            if (attr and inspect.isclass(attr) and 
                                'websocket' in attr_name.lower() and 
                                'manager' in attr_name.lower()):
                                fragmented_imports.append(f"{module_name}.{attr_name}")
                except (AttributeError, TypeError):
                    continue
        
        logger.info(f"Found WebSocket modules: {websocket_modules}")
        logger.info(f"Found WebSocket manager imports: {fragmented_imports}")
        
        # Count unique import patterns
        unique_patterns = set()
        for import_path in fragmented_imports:
            # Extract the pattern (module path without specific class)
            if '.websocket_core.' in import_path:
                pattern = import_path.split('.websocket_core.')[1].split('.')[0]
                unique_patterns.add(pattern)
        
        logger.info(f"Unique WebSocket manager patterns: {unique_patterns}")
        
        # ASSERTION: This MUST FAIL currently (proving fragmentation exists)
        # After SSOT consolidation, this MUST PASS (single pattern)
        self.assertLessEqual(len(unique_patterns), 1,
                           f"IMPORT FRAGMENTATION: Found {len(unique_patterns)} different WebSocket manager import patterns: {unique_patterns}. "
                           f"Full imports found: {fragmented_imports}")

    def test_websocket_manager_alias_consistency(self):
        """
        CRITICAL TEST: Verify all WebSocket manager aliases point to same implementation
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Aliases point to different implementations
        - MUST PASS (after SSOT): All aliases point to same implementation
        """
        logger.info("Testing WebSocket manager alias consistency...")
        
        # Test known aliases from the codebase
        aliases_to_test = [
            ("netra_backend.app.websocket_core.websocket_manager", "WebSocketManager"),
            ("netra_backend.app.websocket_core.websocket_manager", "UnifiedWebSocketManager"),
            ("netra_backend.app.websocket_core.websocket_manager", "WebSocketConnectionManager"),
            ("netra_backend.app.websocket_core.manager", "WebSocketManager"),
        ]
        
        resolved_aliases = {}
        alias_inconsistencies = []
        
        for module_path, alias_name in aliases_to_test:
            try:
                module = importlib.import_module(module_path)
                alias_cls = getattr(module, alias_name)
                resolved_aliases[f"{module_path}.{alias_name}"] = alias_cls
                logger.info(f"Resolved alias {module_path}.{alias_name}: {alias_cls}")
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to resolve alias {module_path}.{alias_name}: {e}")
        
        # Check if all aliases point to the same class
        unique_implementations = set(resolved_aliases.values())
        
        if len(unique_implementations) > 1:
            for alias_path, cls in resolved_aliases.items():
                alias_inconsistencies.append(f"  - {alias_path}: {cls} (id: {id(cls)})")
        
        # ASSERTION: This MUST FAIL currently (proving alias inconsistencies)
        # After SSOT consolidation, this MUST PASS (all aliases same)
        self.assertEqual(len(unique_implementations), 1,
                        f"ALIAS INCONSISTENCY: WebSocket manager aliases point to {len(unique_implementations)} different implementations. "
                        f"Inconsistencies found: {alias_inconsistencies}")

    def test_websocket_manager_factory_pattern_violations(self):
        """
        CRITICAL TEST: Detect factory pattern violations in WebSocket manager creation
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Multiple factory patterns and singleton usage
        - MUST PASS (after SSOT): Single factory pattern with proper user isolation
        """
        logger.info("Testing for WebSocket manager factory pattern violations...")
        
        factory_violations = []
        singleton_patterns = []
        
        # Look for singleton patterns (SSOT violation)
        modules_to_check = [
            "netra_backend.app.websocket_core.websocket_manager",
            "netra_backend.app.websocket_core.unified_manager",
            "netra_backend.app.websocket_core.manager"
        ]
        
        for module_path in modules_to_check:
            try:
                module = importlib.import_module(module_path)
                
                # Check for singleton-like patterns
                if hasattr(module, '_instance'):
                    singleton_patterns.append(f"{module_path}._instance")
                if hasattr(module, '_singleton'):
                    singleton_patterns.append(f"{module_path}._singleton")
                if hasattr(module, 'getInstance'):
                    singleton_patterns.append(f"{module_path}.getInstance")
                    
                # Check for multiple factory functions
                factory_functions = []
                for attr_name in dir(module):
                    if ('get_' in attr_name.lower() and 
                        'websocket' in attr_name.lower() and 
                        'manager' in attr_name.lower()):
                        factory_functions.append(f"{module_path}.{attr_name}")
                
                if len(factory_functions) > 1:
                    factory_violations.append(f"Multiple factory functions in {module_path}: {factory_functions}")
                    
            except ImportError:
                continue
        
        logger.info(f"Singleton patterns found: {singleton_patterns}")
        logger.info(f"Factory violations found: {factory_violations}")
        
        # ASSERTION: This MUST FAIL currently (proving factory violations)
        # After SSOT consolidation, this MUST PASS (clean factory pattern)
        total_violations = len(singleton_patterns) + len(factory_violations)
        self.assertEqual(total_violations, 0,
                        f"FACTORY PATTERN VIOLATIONS: Found {total_violations} violations. "
                        f"Singleton patterns: {singleton_patterns}. "
                        f"Factory violations: {factory_violations}")

    def test_websocket_manager_circular_import_detection(self):
        """
        CRITICAL TEST: Detect circular import patterns in WebSocket manager modules
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Circular imports detected due to fragmentation
        - MUST PASS (after SSOT): Clean import hierarchy with no cycles
        """
        logger.info("Testing for circular import patterns...")
        
        # Track import chains for WebSocket manager modules
        websocket_modules = [
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.websocket_core.websocket_manager", 
            "netra_backend.app.websocket_core.unified_manager"
        ]
        
        import_chains = {}
        circular_imports = []
        
        for module_name in websocket_modules:
            try:
                # Force reimport to detect circular dependencies
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    module = importlib.import_module(module_name)
                    
                    # Check for import warnings that might indicate circular imports
                    for warning in w:
                        if "circular" in str(warning.message).lower():
                            circular_imports.append(f"{module_name}: {warning.message}")
                            
                    import_chains[module_name] = "imported successfully"
                    
            except ImportError as e:
                if "circular" in str(e).lower():
                    circular_imports.append(f"{module_name}: {e}")
        
        logger.info(f"Import chains: {import_chains}")
        logger.info(f"Circular imports detected: {circular_imports}")
        
        # ASSERTION: This MUST FAIL currently (proving circular imports exist)
        # After SSOT consolidation, this MUST PASS (no circular imports)
        self.assertEqual(len(circular_imports), 0,
                        f"CIRCULAR IMPORT VIOLATIONS: Found {len(circular_imports)} circular import patterns: {circular_imports}")

    def tearDown(self):
        """Clean up after SSOT violation tests."""
        super().tearDown()
        logger.info(f"Test completed. Total violations detected: {len(self.detected_violations)}")
        for violation in self.detected_violations:
            logger.warning(f"SSOT VIOLATION: {violation}")


if __name__ == '__main__':
    unittest.main()