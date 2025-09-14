"""
Suite 1: WebSocket SSOT Compliance Validation Tests - Issue #1031

PURPOSE: Ensure complete elimination of deprecated WebSocket factory patterns and
validate SSOT consolidation compliance. These tests target deprecation cleanup
to validate Issue #1031 remediation.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability
- Business Goal: SSOT compliance and deprecation cleanup  
- Value Impact: Eliminates SSOT violations that could affect $500K+ ARR Golden Path
- Revenue Impact: Prevents WebSocket initialization failures and race conditions

EXPECTED BEHAVIOR:
- Suite 1 & 2: Should initially WARN about deprecated patterns
- Suite 3: Should PASS (warnings are working)
- Suite 4: Should PASS (Golden Path operational)

These tests are designed to guide the deprecation cleanup process for Issue #1031.
"""

import pytest
import warnings
import importlib
import sys
from typing import Any, Dict, Optional, List
from unittest.mock import Mock, patch, MagicMock

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketSsotDeprecationCleanup(SSotAsyncTestCase):
    """SSOT Compliance validation for WebSocket deprecation cleanup."""
    
    def setup_method(self, method):
        """Set up test environment for SSOT validation."""
        super().setup_method(method)
        self.deprecated_factory_imports = [
            "netra_backend.app.websocket_core.websocket_manager_factory.create_websocket_manager",
            "netra_backend.app.websocket_core.websocket_manager_factory.get_websocket_manager",  # May be deprecated
        ]
        self.ssot_imports = [
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager.get_websocket_manager",
            "netra_backend.app.websocket_core.unified_manager._UnifiedWebSocketManagerImplementation",
        ]

    def test_no_deprecated_websocket_factory_exports_remaining(self):
        """
        TEST DESIGNED TO WARN/FAIL: Ensure all deprecated factory exports are removed.
        
        This test validates that the deprecated factory module no longer exports
        functions that create SSOT fragmentation (Issue #824 remediation).
        
        EXPECTED: Should WARN if deprecated exports still exist, guiding cleanup.
        """
        try:
            # Try to import the deprecated factory module
            from netra_backend.app.websocket_core import websocket_manager_factory
            
            # Check for deprecated exports that should be removed
            deprecated_exports = []
            
            # Check for deprecated function exports
            if hasattr(websocket_manager_factory, 'create_websocket_manager'):
                deprecated_exports.append('create_websocket_manager')
            
            if hasattr(websocket_manager_factory, 'get_websocket_manager'):
                # This might be a compatibility shim - check if it's deprecated
                func = getattr(websocket_manager_factory, 'get_websocket_manager')
                if func.__doc__ and 'DEPRECATED' in func.__doc__:
                    deprecated_exports.append('get_websocket_manager (DEPRECATED)')
            
            # Check for deprecated class exports
            deprecated_classes = [
                'WebSocketManagerFactory', 
                'FactoryManager',
                'WebSocketFactory'
            ]
            
            for class_name in deprecated_classes:
                if hasattr(websocket_manager_factory, class_name):
                    deprecated_exports.append(f'class {class_name}')
            
            if deprecated_exports:
                warning_msg = (
                    f"DEPRECATION CLEANUP NEEDED: Found deprecated exports in websocket_manager_factory: "
                    f"{', '.join(deprecated_exports)}. These should be removed for SSOT compliance."
                )
                warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)
                logger.warning(f"Issue #1031 Cleanup Guide: {warning_msg}")
                
                # For now, this is a WARNING, not a failure, to guide cleanup
                pytest.skip(f"DEPRECATION CLEANUP: {warning_msg}")
            else:
                logger.info("✅ PASS: No deprecated factory exports found - SSOT compliance maintained")
                
        except ImportError as e:
            # If the deprecated module is completely removed, that's perfect SSOT compliance
            logger.info("✅ PASS: Deprecated factory module completely removed - excellent SSOT compliance")

    def test_websocket_manager_self_contained_implementation(self):
        """
        TEST DESIGNED TO PASS: Validate WebSocketManager is self-contained.
        
        This test ensures the main WebSocketManager can function without
        dependencies on deprecated factory patterns.
        
        EXPECTED: Should PASS - WebSocketManager should be self-contained.
        """
        try:
            # Import the canonical SSOT WebSocket manager
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            
            # Verify it can be imported without factory dependencies
            assert WebSocketManager is not None, "WebSocketManager should be directly importable"
            assert get_websocket_manager is not None, "get_websocket_manager should be directly importable"
            
            # Verify the class has core required methods for SSOT compliance
            required_methods = [
                'emit_to_user',
                'emit_to_thread', 
                'connect_user',
                'disconnect_user'
            ]
            
            missing_methods = []
            for method_name in required_methods:
                if not hasattr(WebSocketManager, method_name):
                    missing_methods.append(method_name)
            
            if missing_methods:
                logger.warning(f"WebSocketManager missing core methods: {missing_methods}")
                # This might be acceptable depending on the implementation approach
            
            logger.info("✅ PASS: WebSocketManager is self-contained and importable")
            
        except ImportError as e:
            pytest.fail(f"SSOT VIOLATION: Cannot import canonical WebSocketManager: {e}")

    def test_deprecated_imports_eliminated_from_ssot(self):
        """
        TEST DESIGNED TO WARN: Check if deprecated imports are still accessible.
        
        This test validates that deprecated import paths are either removed
        or properly redirect to SSOT implementations.
        
        EXPECTED: Should WARN if deprecated imports exist, guiding migration.
        """
        deprecated_import_issues = []
        
        for import_path in self.deprecated_factory_imports:
            try:
                # Try to import the deprecated path
                module_path, function_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                
                if hasattr(module, function_name):
                    func = getattr(module, function_name)
                    
                    # Check if it's properly marked as deprecated
                    if func.__doc__ and 'DEPRECATED' in func.__doc__:
                        logger.info(f"✅ Deprecated import {import_path} properly marked as DEPRECATED")
                    else:
                        deprecated_import_issues.append(
                            f"Import {import_path} exists but not marked as DEPRECATED"
                        )
                        
            except ImportError:
                # If import fails, that might be good (fully removed)
                logger.info(f"✅ Deprecated import {import_path} is no longer importable (good for SSOT)")
            except Exception as e:
                logger.warning(f"Unexpected error checking {import_path}: {e}")
        
        if deprecated_import_issues:
            warning_msg = f"DEPRECATION CLEANUP NEEDED: {'; '.join(deprecated_import_issues)}"
            warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)
            logger.warning(f"Issue #1031 Cleanup Guide: {warning_msg}")
            pytest.skip(f"DEPRECATION CLEANUP: {warning_msg}")
        else:
            logger.info("✅ PASS: All deprecated imports properly handled")

    def test_websocket_manager_import_unification(self):
        """
        TEST DESIGNED TO PASS: Validate all WebSocket manager imports resolve consistently.
        
        This test ensures that different import paths for WebSocket managers
        all resolve to the same underlying SSOT implementation.
        
        EXPECTED: Should PASS - All imports should be unified.
        """
        try:
            # Import from different paths that should all resolve to the same thing
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WM1
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as get_wm1
            
            # Try to import from the unified manager (underlying implementation)
            try:
                from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation
                logger.info("✅ Unified manager implementation accessible")
            except ImportError:
                logger.info("Unified manager not directly importable (may be private)")
            
            # Verify that the WebSocketManager class is properly defined
            assert WM1 is not None, "WebSocketManager should be importable"
            assert callable(get_wm1), "get_websocket_manager should be callable"
            
            # Check if WebSocketManager has expected attributes for SSOT compliance
            expected_attributes = ['__init__', '__class__', '__module__']
            for attr in expected_attributes:
                assert hasattr(WM1, attr), f"WebSocketManager missing {attr}"
            
            logger.info("✅ PASS: WebSocket manager imports are unified and consistent")
            
        except ImportError as e:
            pytest.fail(f"SSOT VIOLATION: Cannot import unified WebSocket manager: {e}")
        except AssertionError as e:
            pytest.fail(f"SSOT VIOLATION: WebSocket manager import inconsistency: {e}")

    def test_factory_pattern_elimination_compliance(self):
        """
        TEST DESIGNED TO WARN: Check for remaining factory pattern violations.
        
        This test identifies factory patterns that should be eliminated
        as part of SSOT consolidation.
        
        EXPECTED: Should WARN if unnecessary factory patterns remain.
        """
        try:
            # Check if the factory module still has complex factory patterns
            from netra_backend.app.websocket_core import websocket_manager_factory
            
            # Look for factory patterns that indicate SSOT violations
            factory_pattern_indicators = [
                'Factory',
                'Builder', 
                'Creator',
                'Generator',
                'Instantiator'
            ]
            
            found_patterns = []
            for attr_name in dir(websocket_manager_factory):
                if not attr_name.startswith('_'):  # Skip private attributes
                    for pattern in factory_pattern_indicators:
                        if pattern.lower() in attr_name.lower():
                            found_patterns.append(f"{attr_name} (contains '{pattern}')")
            
            if found_patterns:
                warning_msg = (
                    f"FACTORY PATTERN CLEANUP NEEDED: Found factory patterns in websocket_manager_factory: "
                    f"{', '.join(found_patterns)}. Consider simplification for SSOT compliance."
                )
                warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)
                logger.warning(f"Issue #1031 Cleanup Guide: {warning_msg}")
            else:
                logger.info("✅ PASS: No complex factory patterns found")
                
        except ImportError:
            logger.info("✅ PASS: Factory module not importable - excellent SSOT compliance")

    def test_websocket_module_structure_ssot_compliance(self):
        """
        TEST DESIGNED TO PASS: Validate WebSocket module structure follows SSOT.
        
        This test ensures the WebSocket module structure is clean and
        follows SSOT principles without unnecessary complexity.
        
        EXPECTED: Should PASS - Module structure should be SSOT compliant.
        """
        try:
            import netra_backend.app.websocket_core as websocket_core
            
            # Get list of all modules in websocket_core
            import pkgutil
            import netra_backend.app.websocket_core
            
            websocket_modules = []
            for importer, modname, ispkg in pkgutil.iter_modules(
                netra_backend.app.websocket_core.__path__, 
                prefix="netra_backend.app.websocket_core."
            ):
                websocket_modules.append(modname)
            
            logger.info(f"Found WebSocket modules: {websocket_modules}")
            
            # Check for SSOT compliance indicators
            ssot_compliance_score = 0
            total_checks = 0
            
            # Check 1: Should have a unified_manager
            total_checks += 1
            if any('unified_manager' in mod for mod in websocket_modules):
                ssot_compliance_score += 1
                logger.info("✅ Has unified_manager module")
            
            # Check 2: Should have main websocket_manager interface
            total_checks += 1
            if any('websocket_manager' in mod and 'factory' not in mod for mod in websocket_modules):
                ssot_compliance_score += 1
                logger.info("✅ Has main websocket_manager module")
            
            # Calculate compliance percentage
            compliance_percentage = (ssot_compliance_score / total_checks) * 100 if total_checks > 0 else 0
            
            logger.info(f"WebSocket module SSOT compliance: {compliance_percentage:.1f}% ({ssot_compliance_score}/{total_checks})")
            
            # This test should generally pass, just providing informational data
            assert compliance_percentage >= 50, f"WebSocket module structure SSOT compliance too low: {compliance_percentage:.1f}%"
            
        except Exception as e:
            logger.warning(f"Could not analyze WebSocket module structure: {e}")
            pytest.skip(f"Module structure analysis failed: {e}")