"""
Issue #1176 Phase 2: WebSocket Import Coordination Testing

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket coordination enables 90% of platform value
- Value Impact: Consistent import patterns prevent coordination failures
- Strategic Impact: SSOT consolidation reduces technical debt

This test suite validates WebSocket import coordination across the 13+ modules
identified in Issue #1176 Phase 2 analysis.
"""

import inspect
import importlib
import sys
from typing import Dict, List, Set, Any
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class WebSocketImportCoordinationTests(SSotBaseTestCase):
    """Test WebSocket import coordination across 13+ modules."""

    def setup_method(self):
        """Set up WebSocket import coordination test environment."""
        super().setup_method()
        self.websocket_modules = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.unified_emitter',
            'netra_backend.app.websocket_core.protocols',
            'netra_backend.app.websocket_core.types',
            'netra_backend.app.websocket_core.handlers',
            'netra_backend.app.websocket_core.auth',
            'netra_backend.app.websocket_core.notifier',
            'netra_backend.app.websocket_core.events',
            'netra_backend.app.websocket_core.factory',
            'netra_backend.app.websocket_core.bridge',
            'netra_backend.app.websocket_core.coordinator',
            'netra_backend.app.websocket_core'
        ]

    def test_websocket_manager_ssot_import_consolidation(self):
        """Test that WebSocket manager exports use canonical SSOT patterns.

        ISSUE #1176 PHASE 2: This test validates that core manager classes
        have canonical import paths, distinguishing between exports and necessary imports.
        """
        canonical_exports = []
        imported_classes = []

        # CANONICAL PATHS: Only these should export WebSocketManager classes
        canonical_modules = [
            'netra_backend.app.websocket_core.websocket_manager',  # WebSocketManager
            'netra_backend.app.websocket_core.unified_manager',    # UnifiedWebSocketManager
        ]

        for module_name in canonical_modules:
            try:
                module = importlib.import_module(module_name)

                # Find WebSocket manager classes DEFINED in this module (not imported)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if ('WebSocketManager' in name and 'Mode' not in name and 'Protocol' not in name
                        and not name.startswith('_')):  # Exclude internal classes
                        # Check if this class is defined here (canonical) vs imported
                        if hasattr(obj, '__module__') and obj.__module__ == module_name:
                            canonical_exports.append(f"{module_name}.{name}")
                        else:
                            imported_classes.append(f"{module_name}.{name} (from {obj.__module__})")

            except ImportError:
                continue

        # For SSOT compliance, we should have exactly 2 canonical manager exports:
        # 1. WebSocketManager from websocket_manager.py
        # 2. UnifiedWebSocketManager from unified_manager.py
        expected_canonical_count = 2

        if len(canonical_exports) != expected_canonical_count:
            # Log what we found for debugging
            all_found = canonical_exports + imported_classes
            self.fail(
                f"WEBSOCKET MANAGER SSOT COORDINATION GAP: "
                f"Expected {expected_canonical_count} canonical manager exports, found {len(canonical_exports)}. "
                f"Canonical exports: {canonical_exports}. "
                f"All detected: {all_found}. "
                f"Each manager class should have exactly one canonical export location."
            )

        # If we get here, manager exports are properly coordinated
        assert len(canonical_exports) == expected_canonical_count, "WebSocket manager exports properly coordinated"

    def test_websocket_protocol_import_fragmentation_detection(self):
        """Test that WebSocket protocol classes use canonical import patterns.

        ISSUE #1176 PHASE 2: Validates that protocol classes are defined in
        protocols.py and not duplicated across multiple modules.
        """
        canonical_protocol_exports = []
        imported_protocols = []

        # CANONICAL PATH: protocols.py should be the only source for protocol definitions
        canonical_protocol_module = 'netra_backend.app.websocket_core.protocols'

        try:
            module = importlib.import_module(canonical_protocol_module)

            # Find protocol classes DEFINED in protocols.py (not imported)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if 'Protocol' in name and 'WebSocket' in name:
                    # Check if this class is defined here (canonical) vs imported
                    if hasattr(obj, '__module__') and obj.__module__ == canonical_protocol_module:
                        canonical_protocol_exports.append(f"{canonical_protocol_module}.{name}")
                    else:
                        imported_protocols.append(f"{canonical_protocol_module}.{name} (from {obj.__module__})")

        except ImportError:
            pass

        # Check other modules for protocol duplicates
        duplicate_protocol_definitions = []
        other_modules = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.types'
        ]

        for module_name in other_modules:
            try:
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if 'Protocol' in name and 'WebSocket' in name:
                        # If protocol is defined here instead of protocols.py, it's a duplicate
                        if hasattr(obj, '__module__') and obj.__module__ == module_name:
                            duplicate_protocol_definitions.append(f"{module_name}.{name}")

            except ImportError:
                continue

        # SSOT Violation: Protocol classes should only be defined in protocols.py
        if duplicate_protocol_definitions:
            self.fail(
                f"WEBSOCKET PROTOCOL FRAGMENTATION DETECTED: "
                f"Found {len(duplicate_protocol_definitions)} protocol classes defined outside protocols.py: "
                f"{duplicate_protocol_definitions}. "
                f"Canonical exports in protocols.py: {canonical_protocol_exports}. "
                f"All protocol classes should be defined in protocols.py for SSOT compliance."
            )

        # If we get here, protocols are properly centralized
        assert len(duplicate_protocol_definitions) == 0, "Protocol definitions properly centralized"

    def test_websocket_emitter_import_path_standardization(self):
        """Test that WebSocket emitter classes use canonical SSOT patterns.

        ISSUE #1176 PHASE 2: Validates that emitter classes are defined in
        unified_emitter.py and not duplicated across multiple modules.
        """
        canonical_emitter_exports = []

        # CANONICAL PATH: unified_emitter.py should be the only source for emitter definitions
        canonical_emitter_module = 'netra_backend.app.websocket_core.unified_emitter'

        try:
            module = importlib.import_module(canonical_emitter_module)

            # Find emitter classes DEFINED in unified_emitter.py (not imported)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if 'Emitter' in name and 'WebSocket' in name:
                    # Check if this class is defined here (canonical) vs imported
                    if hasattr(obj, '__module__') and obj.__module__ == canonical_emitter_module:
                        canonical_emitter_exports.append(f"{canonical_emitter_module}.{name}")

        except ImportError:
            pass

        # Check other modules for emitter duplicates
        duplicate_emitter_definitions = []
        other_modules = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.handlers'
        ]

        for module_name in other_modules:
            try:
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if 'Emitter' in name and 'WebSocket' in name:
                        # If emitter is defined here instead of unified_emitter.py, it's a duplicate
                        if hasattr(obj, '__module__') and obj.__module__ == module_name:
                            duplicate_emitter_definitions.append(f"{module_name}.{name}")

            except ImportError:
                continue

        # SSOT Violation: Emitter classes should only be defined in unified_emitter.py
        if duplicate_emitter_definitions:
            self.fail(
                f"WEBSOCKET EMITTER COORDINATION GAP DETECTED: "
                f"Found {len(duplicate_emitter_definitions)} emitter classes defined outside unified_emitter.py: "
                f"{duplicate_emitter_definitions}. "
                f"Canonical exports in unified_emitter.py: {canonical_emitter_exports}. "
                f"All emitter classes should be defined in unified_emitter.py for SSOT compliance."
            )

        # For SSOT compliance, we should have at least 1 canonical emitter export:
        # UnifiedWebSocketEmitter from unified_emitter.py
        if len(canonical_emitter_exports) < 1:
            self.fail(
                f"WEBSOCKET EMITTER SSOT VALIDATION FAILED: "
                f"Expected at least 1 canonical emitter export, found {len(canonical_emitter_exports)}. "
                f"unified_emitter.py should export UnifiedWebSocketEmitter."
            )

        # If we get here, emitter imports are properly coordinated
        assert len(duplicate_emitter_definitions) == 0, "Emitter imports properly standardized"

    def test_websocket_core_module_import_consistency(self):
        """Test consistency of WebSocket core module imports.

        EXPECTED TO FAIL: Core module imports are inconsistent, with some
        components importing directly and others importing through __init__.py
        """
        core_module_imports = []
        direct_imports = []

        # Check if components import from websocket_core directly
        try:
            from netra_backend.app.websocket_core import (
                UnifiedWebSocketManager, UnifiedWebSocketEmitter
            )
            core_module_imports.append("websocket_core.__init__")
        except ImportError:
            pass

        # Check if components import directly from submodules
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            direct_imports.append("websocket_core.unified_manager")
        except ImportError:
            pass

        try:
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
            direct_imports.append("websocket_core.unified_emitter")
        except ImportError:
            pass

        # If both core module and direct imports exist, there's coordination confusion
        if core_module_imports and direct_imports:
            # COORDINATION GAP DETECTED: Mixed import patterns
            self.fail(
                f"WEBSOCKET CORE IMPORT INCONSISTENCY DETECTED: "
                f"Found both core module imports {core_module_imports} and "
                f"direct imports {direct_imports}. Mixed import patterns create "
                f"coordination confusion. Should use consistent import strategy."
            )

        # If we get here, import patterns are consistent
        assert not (core_module_imports and direct_imports), "Core imports consistent"

    def test_websocket_ssot_warning_detection(self):
        """Test detection of WebSocket SSOT warnings in system.

        EXPECTED TO FAIL: SSOT warnings are present, indicating multiple
        WebSocket manager classes violating SSOT principles.
        """
        import logging
        from io import StringIO
        import sys

        # Capture logging output to detect SSOT warnings
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)

        # Get the websocket_manager logger
        logger = logging.getLogger('netra_backend.app.websocket_core.websocket_manager')
        original_level = logger.level
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        try:
            # Import websocket_manager to trigger SSOT validation
            from netra_backend.app.websocket_core import websocket_manager
            importlib.reload(websocket_manager)

            # Check log output for SSOT warnings
            log_output = log_capture.getvalue()

            if "SSOT WARNING" in log_output:
                # COORDINATION GAP DETECTED: SSOT warnings present
                self.fail(
                    f"WEBSOCKET SSOT COORDINATION GAP DETECTED: "
                    f"SSOT warnings found in system logs: {log_output}. "
                    f"This indicates multiple WebSocket Manager classes violating "
                    f"SSOT principles and creating coordination conflicts."
                )

        finally:
            # Cleanup
            logger.removeHandler(handler)
            logger.setLevel(original_level)

        # If we get here, no SSOT warnings detected
        assert True, "No WebSocket SSOT warnings detected"


class WebSocketImportPathFragmentationTests(SSotBaseTestCase):
    """Test WebSocket import path fragmentation issues."""

    def test_canonical_import_path_validation(self):
        """Test validation of canonical import paths for WebSocket components.

        EXPECTED TO FAIL: Import paths are fragmented across multiple locations,
        making it unclear which import path should be used.
        """
        # Define expected canonical paths
        canonical_paths = {
            'UnifiedWebSocketManager': 'netra_backend.app.websocket_core.unified_manager',
            'UnifiedWebSocketEmitter': 'netra_backend.app.websocket_core.unified_emitter',
            'WebSocketAuthenticator': 'netra_backend.app.websocket_core.auth',
            'CanonicalMessageRouter': 'netra_backend.app.websocket_core.handlers'
        }

        fragmentation_detected = []

        for class_name, expected_path in canonical_paths.items():
            # Check if class can be imported from multiple paths
            import_paths = []

            # Try various possible import paths
            possible_paths = [
                f'netra_backend.app.websocket_core.{class_name}',
                f'netra_backend.app.websocket_core',
                expected_path,
                f'{expected_path}.{class_name}'
            ]

            for path in possible_paths:
                try:
                    if path.endswith(f'.{class_name}'):
                        module_path = path.rsplit('.', 1)[0]
                        module = importlib.import_module(module_path)
                        if hasattr(module, class_name):
                            import_paths.append(path)
                    else:
                        module = importlib.import_module(path)
                        if hasattr(module, class_name):
                            import_paths.append(f"{path}.{class_name}")
                except ImportError:
                    continue

            # If multiple import paths exist, fragmentation detected
            if len(import_paths) > 1:
                fragmentation_detected.append({
                    'class': class_name,
                    'paths': import_paths,
                    'expected': expected_path
                })

        if fragmentation_detected:
            # COORDINATION GAP DETECTED: Import path fragmentation
            fragmentation_details = '\n'.join([
                f"  {item['class']}: {item['paths']} (expected: {item['expected']})"
                for item in fragmentation_detected
            ])

            self.fail(
                f"WEBSOCKET IMPORT PATH FRAGMENTATION DETECTED:\n"
                f"{fragmentation_details}\n"
                f"Multiple import paths for same classes create coordination confusion. "
                f"Should have single canonical import path per class."
            )

        # If we get here, no fragmentation detected
        assert len(fragmentation_detected) == 0, "Import paths properly canonical"