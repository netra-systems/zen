"""
Test SSOT Compliance Validation - Issue #1100

Business Value Justification (BVJ):
- Segment: Platform/Internal Infrastructure
- Business Goal: Ensure single source of truth for WebSocket management
- Value Impact: Eliminates race conditions and inconsistencies affecting $500K+ ARR
- Strategic Impact: Enables reliable WebSocket operations at scale

This test module validates SSOT compliance patterns and ensures only one
WebSocket manager implementation is active at any time.

CRITICAL: These tests are designed to FAIL initially with current dual pattern
code and PASS after factory elimination is complete.
"""

import pytest
import asyncio
import importlib
import sys
import inspect
from typing import Dict, List, Any, Set
from unittest.mock import patch, MagicMock
from test_framework.base_integration_test import BaseIntegrationTest
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class SSotComplianceValidationTests(BaseIntegrationTest):
    """Test SSOT compliance for WebSocket manager implementations."""
    
    @pytest.mark.unit
    def test_single_websocket_manager_implementation_active(self):
        """
        SHOULD FAIL: Ensure only one WebSocket manager implementation active.
        
        This test validates that only one WebSocket manager implementation
        is imported and active at any time. With current dual pattern code,
        this should FAIL due to multiple implementations.
        """
        logger.info("Validating single WebSocket manager implementation")
        
        websocket_manager_modules = []
        active_implementations = []
        
        try:
            # Check for canonical SSOT implementation
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            websocket_manager_modules.append({
                'module': 'netra_backend.app.websocket_core.websocket_manager',
                'class': 'WebSocketManager',
                'implementation': WebSocketManager,
                'type': 'canonical_ssot'
            })
            active_implementations.append('canonical_ssot')
            logger.info("Found canonical SSOT WebSocketManager implementation")
        except ImportError as e:
            logger.error(f"Canonical WebSocketManager not available: {e}")
        
        try:
            # Check for deprecated factory implementation
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            websocket_manager_modules.append({
                'module': 'netra_backend.app.websocket_core.websocket_manager_factory',
                'class': 'WebSocketManagerFactory',
                'implementation': WebSocketManagerFactory,
                'type': 'deprecated_factory'
            })
            active_implementations.append('deprecated_factory')
            logger.warning("Found deprecated WebSocketManagerFactory implementation")
        except ImportError:
            logger.info("Deprecated WebSocketManagerFactory not found (good)")
        
        try:
            # Check for any other WebSocket manager implementations
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            websocket_manager_modules.append({
                'module': 'netra_backend.app.websocket_core.unified_manager',
                'class': 'UnifiedWebSocketManager',
                'implementation': UnifiedWebSocketManager,
                'type': 'unified_implementation'
            })
            # Unified implementation is allowed as exported interface
            logger.info("Found UnifiedWebSocketManager implementation (allowed)")
        except ImportError:
            pass
        
        logger.info(f"Active WebSocket implementations: {active_implementations}")
        
        # Should have only the canonical SSOT implementation accessible publicly
        public_implementations = [impl for impl in active_implementations 
                                if impl != 'internal_implementation']
        
        # This assertion should FAIL initially with current dual pattern code
        assert len(public_implementations) == 1, (
            f"Multiple public WebSocket manager implementations active: {public_implementations}. "
            "Only canonical SSOT implementation should be accessible. "
            f"Found modules: {[m['module'] for m in websocket_manager_modules if m['type'] != 'internal_implementation']}"
        )
        
        assert 'canonical_ssot' in public_implementations, (
            "Canonical SSOT WebSocketManager implementation must be available"
        )
    
    @pytest.mark.unit
    def test_websocket_manager_import_path_consistency(self):
        """
        SHOULD FAIL: Validate consistent import paths across all modules.
        
        All modules should import WebSocketManager from the same canonical path
        to ensure SSOT compliance and prevent confusion.
        """
        logger.info("Validating WebSocket manager import path consistency")
        
        # Test different import scenarios
        import_scenarios = []
        
        try:
            # Canonical import (should work)
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as CanonicalWsManager
            import_scenarios.append({
                'path': 'netra_backend.app.websocket_core.websocket_manager',
                'class': 'WebSocketManager',
                'status': 'available',
                'type': 'canonical'
            })
            logger.info("Canonical WebSocketManager import successful")
        except ImportError as e:
            import_scenarios.append({
                'path': 'netra_backend.app.websocket_core.websocket_manager',
                'class': 'WebSocketManager', 
                'status': f'failed: {e}',
                'type': 'canonical'
            })
        
        try:
            # Deprecated factory import (should not work or be deprecated)
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            import_scenarios.append({
                'path': 'netra_backend.app.websocket_core.websocket_manager_factory',
                'class': 'WebSocketManagerFactory',
                'status': 'available',
                'type': 'deprecated'
            })
            logger.warning("Deprecated WebSocketManagerFactory import still available")
        except ImportError:
            import_scenarios.append({
                'path': 'netra_backend.app.websocket_core.websocket_manager_factory',
                'class': 'WebSocketManagerFactory',
                'status': 'not_available',
                'type': 'deprecated'
            })
            logger.info("Deprecated WebSocketManagerFactory not available (good)")
        
        # Validate import consistency
        available_imports = [s for s in import_scenarios if s['status'] == 'available']
        deprecated_imports = [s for s in available_imports if s['type'] == 'deprecated']
        canonical_imports = [s for s in available_imports if s['type'] == 'canonical']
        
        # This assertion should FAIL initially if deprecated imports are still available
        assert len(deprecated_imports) == 0, (
            f"Deprecated WebSocket manager imports still available: "
            f"{[imp['path'] for imp in deprecated_imports]}. "
            "These should be eliminated for SSOT compliance."
        )
        
        # Must have canonical import available
        assert len(canonical_imports) >= 1, (
            "Canonical WebSocket manager import must be available: "
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager"
        )
    
    @pytest.mark.unit
    def test_no_factory_pattern_in_websocket_instantiation(self):
        """
        SHOULD FAIL: Ensure no factory pattern usage for WebSocket creation.
        
        WebSocket managers should be instantiated directly using the canonical
        class, not through factory functions or patterns.
        """
        logger.info("Validating no factory pattern usage in WebSocket instantiation")
        
        instantiation_patterns = []
        
        try:
            # Test direct instantiation (should work)
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            # Create minimal test context
            test_user_id = ensure_user_id("test_user_ssot")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="test_thread",
                run_id="test_run", 
                request_id="ssot_compliance_test"
            )
            
            # Direct instantiation test
            try:
                manager = WebSocketManager(
                    mode=WebSocketManagerMode.UNIFIED,
                    user_context=test_context
                )
                instantiation_patterns.append({
                    'method': 'direct_instantiation',
                    'status': 'success',
                    'class': manager.__class__.__name__
                })
                logger.info("Direct WebSocketManager instantiation successful")
            except Exception as e:
                instantiation_patterns.append({
                    'method': 'direct_instantiation',
                    'status': f'failed: {e}',
                    'class': None
                })
                
        except ImportError as e:
            logger.error(f"Cannot import WebSocketManager for direct instantiation test: {e}")
        
        try:
            # Test deprecated factory function (should not be used)
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            
            # If factory function exists, it's a SSOT violation
            instantiation_patterns.append({
                'method': 'deprecated_factory',
                'status': 'available',
                'class': 'factory_function'
            })
            logger.warning("Deprecated factory function still available")
            
        except ImportError:
            instantiation_patterns.append({
                'method': 'deprecated_factory', 
                'status': 'not_available',
                'class': None
            })
            logger.info("Deprecated factory function not available (good)")
        
        # Validate instantiation patterns
        deprecated_patterns = [p for p in instantiation_patterns 
                              if p['method'] == 'deprecated_factory' and p['status'] == 'available']
        direct_patterns = [p for p in instantiation_patterns
                          if p['method'] == 'direct_instantiation' and p['status'] == 'success']
        
        # This assertion should FAIL initially if deprecated factory patterns are available
        assert len(deprecated_patterns) == 0, (
            f"Deprecated factory patterns still available: "
            f"{[p['method'] for p in deprecated_patterns]}. "
            "WebSocket managers should use direct instantiation for SSOT compliance."
        )
        
        # Direct instantiation should work
        assert len(direct_patterns) >= 1, (
            "Direct WebSocketManager instantiation should be available and working"
        )
    
    @pytest.mark.unit
    def test_websocket_manager_class_consistency(self):
        """
        SHOULD FAIL: Validate WebSocketManager class consistency across imports.
        
        The WebSocketManager class should be the same object regardless of
        how it's imported to ensure SSOT compliance.
        """
        logger.info("Validating WebSocketManager class consistency")
        
        websocket_classes = []
        
        try:
            # Import from canonical path
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as CanonicalWsManager
            websocket_classes.append({
                'import_path': 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager',
                'class_object': CanonicalWsManager,
                'class_id': id(CanonicalWsManager),
                'class_name': CanonicalWsManager.__name__,
                'module': CanonicalWsManager.__module__
            })
        except ImportError as e:
            logger.error(f"Cannot import canonical WebSocketManager: {e}")
            pytest.fail("Canonical WebSocketManager must be importable")
        
        try:
            # Try to import from other potential paths that shouldn't exist
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            # If WebSocketManagerFactory creates WebSocketManager instances,
            # they should be the same class as canonical
            if hasattr(WebSocketManagerFactory, 'websocket_manager_class'):
                factory_class = getattr(WebSocketManagerFactory, 'websocket_manager_class')
                websocket_classes.append({
                    'import_path': 'websocket_manager_factory.WebSocketManagerFactory.websocket_manager_class',
                    'class_object': factory_class,
                    'class_id': id(factory_class),
                    'class_name': factory_class.__name__,
                    'module': factory_class.__module__
                })
        except (ImportError, AttributeError):
            pass
        
        # All WebSocketManager classes should be the same object (same id)
        if len(websocket_classes) > 1:
            canonical_id = websocket_classes[0]['class_id']
            different_classes = [cls for cls in websocket_classes[1:] 
                               if cls['class_id'] != canonical_id]
            
            # This assertion should FAIL initially if different WebSocketManager classes exist
            assert len(different_classes) == 0, (
                f"Found {len(different_classes)} different WebSocketManager classes. "
                "All should reference the same canonical class for SSOT compliance:\n" +
                "\n".join([f"  {cls['import_path']} (id: {cls['class_id']})" 
                          for cls in websocket_classes])
            )
        
        logger.info(f"Validated {len(websocket_classes)} WebSocketManager class references")
    
    @pytest.mark.unit
    def test_websocket_manager_ssot_attributes_consistency(self):
        """
        SHOULD FAIL: Validate WebSocketManager SSOT attributes consistency.
        
        The WebSocketManager class should have consistent attributes and methods
        across all usage patterns to ensure SSOT compliance.
        """
        logger.info("Validating WebSocketManager SSOT attributes consistency")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        except ImportError as e:
            pytest.fail(f"Cannot import WebSocketManager for attribute validation: {e}")
        
        # Expected SSOT attributes for WebSocketManager
        expected_attributes = [
            '__init__',
            'send_event', 
            'connect',
            'disconnect',
            'user_context',
            'mode'
        ]
        
        # Expected SSOT methods for WebSocketManager
        expected_methods = [
            'send_event',
            'connect',
            'disconnect'
        ]
        
        missing_attributes = []
        missing_methods = []
        
        for attr in expected_attributes:
            if not hasattr(WebSocketManager, attr):
                missing_attributes.append(attr)
        
        for method in expected_methods:
            if hasattr(WebSocketManager, method):
                method_obj = getattr(WebSocketManager, method)
                if not callable(method_obj):
                    missing_methods.append(f"{method} (not callable)")
            else:
                missing_methods.append(f"{method} (missing)")
        
        # Validate SSOT interface consistency
        assert len(missing_attributes) == 0, (
            f"WebSocketManager missing expected SSOT attributes: {missing_attributes}"
        )
        
        assert len(missing_methods) == 0, (
            f"WebSocketManager missing expected SSOT methods: {missing_methods}"
        )
        
        logger.info("WebSocketManager SSOT attributes validation completed")


class FactoryPatternEliminationTests(BaseIntegrationTest):
    """Test elimination of factory patterns in favor of direct instantiation."""
    
    @pytest.mark.unit
    def test_no_websocket_manager_factory_class_available(self):
        """
        SHOULD FAIL: Ensure WebSocketManagerFactory class is not available.
        
        The WebSocketManagerFactory class should be eliminated as part of
        SSOT consolidation to prevent dual implementation patterns.
        """
        logger.info("Validating WebSocketManagerFactory class elimination")
        
        factory_availability = {
            'class_importable': False,
            'methods_available': [],
            'deprecation_warning': False
        }
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory_availability['class_importable'] = True
            
            # Check for factory methods
            factory_methods = [
                'create_websocket_manager',
                'get_websocket_manager',  
                'create_manager',
                'get_manager'
            ]
            
            for method in factory_methods:
                if hasattr(WebSocketManagerFactory, method):
                    factory_availability['methods_available'].append(method)
            
            logger.warning(f"WebSocketManagerFactory still available with methods: "
                          f"{factory_availability['methods_available']}")
            
        except ImportError:
            logger.info("WebSocketManagerFactory not importable (good for SSOT)")
        except DeprecationWarning:
            factory_availability['deprecation_warning'] = True
            logger.info("WebSocketManagerFactory shows deprecation warning (transitional)")
        
        # This assertion should FAIL initially if factory class is still available
        assert not factory_availability['class_importable'], (
            "WebSocketManagerFactory class should not be importable for SSOT compliance. "
            f"Found methods: {factory_availability['methods_available']}"
        )
    
    @pytest.mark.unit
    def test_no_websocket_factory_functions_available(self):
        """
        SHOULD FAIL: Ensure WebSocket factory functions are not available.
        
        Factory functions like create_websocket_manager should be eliminated
        in favor of direct WebSocketManager instantiation.
        """
        logger.info("Validating WebSocket factory functions elimination")
        
        factory_functions = [
            'create_websocket_manager',
            'create_websocket_manager_sync',
            'get_websocket_manager_factory'
        ]
        
        available_functions = []
        
        for func_name in factory_functions:
            try:
                import netra_backend.app.websocket_core.websocket_manager_factory as factory_module
                # Check if function exists in the module
                if hasattr(factory_module, func_name):
                    available_functions.append(func_name)
            except ImportError:
                pass
            
            try:
                # Try specific import
                module = importlib.import_module('netra_backend.app.websocket_core.websocket_manager_factory')
                if hasattr(module, func_name):
                    available_functions.append(f"{func_name} (module attribute)")
            except ImportError:
                pass
        
        # Remove duplicates
        available_functions = list(set(available_functions))
        
        logger.info(f"Available factory functions: {available_functions}")
        
        # This assertion should FAIL initially if factory functions are still available  
        assert len(available_functions) == 0, (
            f"WebSocket factory functions should not be available for SSOT compliance: "
            f"{available_functions}"
        )
    
    @pytest.mark.unit
    def test_websocket_manager_direct_instantiation_required(self):
        """
        SHOULD PASS: Validate direct WebSocketManager instantiation works.
        
        Direct instantiation should be the only way to create WebSocketManager
        instances for SSOT compliance.
        """
        logger.info("Validating WebSocketManager direct instantiation")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            # Create test user context
            test_user_id = ensure_user_id("direct_test_user")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="direct_test_thread",
                run_id="direct_test_run",
                request_id="direct_instantiation_test"
            )
            
            # Direct instantiation should work
            manager = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            # Validate manager properties
            assert manager.user_context == test_context
            assert manager.mode == WebSocketManagerMode.UNIFIED
            assert hasattr(manager, 'send_event')
            
            logger.info("Direct WebSocketManager instantiation successful")
            
        except Exception as e:
            pytest.fail(f"Direct WebSocketManager instantiation should work: {e}")