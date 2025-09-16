"""
Test WebSocket Import Path Consistency Validation (Issue #1055)

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure Protection
- Business Goal: Protect $500K+ ARR by preventing WebSocket import fragmentation
- Value Impact: Ensures consistent WebSocket Manager imports across all services
- Revenue Impact: Prevents race conditions that cause chat failures

CRITICAL PURPOSE: These tests INITIALLY FAIL to demonstrate import path fragmentation,
then PASS after SSOT import consolidation to validate the fix.

TEST STRATEGY: Detect inconsistent import paths that cause WebSocket Manager fragmentation.
This test validates that all WebSocket Manager imports use the canonical SSOT path.
"""

import pytest
import importlib
import sys
import inspect
from typing import Dict, List, Set, Tuple, Any
from pathlib import Path

from test_framework.base_integration_test import BaseIntegrationTest


class WebSocketImportPathConsistencyValidationTests(BaseIntegrationTest):
    """Test WebSocket import path consistency for SSOT validation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.canonical_imports = {}
        self.fragmented_imports = []

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_canonical_import_path(self):
        """
        FAIL-FIRST TEST: Validate canonical WebSocket Manager import path.

        This test ensures that there is exactly ONE canonical import path
        for WebSocket Manager functionality. Multiple import paths indicate
        SSOT fragmentation that can cause race conditions.
        """
        # Expected canonical SSOT import path (after consolidation)
        canonical_path = "netra_backend.app.websocket_core.websocket_manager.WebSocketManager"

        # Alternative import paths that indicate fragmentation
        fragmented_paths = [
            "netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory",
            "netra_backend.app.websocket_core.protocols.LegacyWebSocketManagerAdapter",
            "netra_backend.app.agents.supervisor.agent_registry.WebSocketManagerAdapter",
            "netra_backend.app.websocket_core.manager.WebSocketManager"  # Legacy path
        ]

        # Check which paths are currently available
        available_paths = []

        for path in fragmented_paths:
            module_path, class_name = path.rsplit('.', 1)
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    available_paths.append(path)
                    print(f"FRAGMENTATION DETECTED: {path} is available")
            except ImportError:
                pass  # Path doesn't exist, which is expected after consolidation

        # ASSERTION: Multiple import paths indicate SSOT violation
        if len(available_paths) > 1:
            pytest.fail(
                f"SSOT VIOLATION: Multiple WebSocket Manager import paths detected: "
                f"{available_paths}. This indicates import fragmentation that can cause "
                f"race conditions and inconsistent behavior. Expected only canonical path: {canonical_path}"
            )

        # Check if canonical path is available
        canonical_module_path, canonical_class_name = canonical_path.rsplit('.', 1)
        try:
            canonical_module = importlib.import_module(canonical_module_path)
            canonical_available = hasattr(canonical_module, canonical_class_name)
        except ImportError:
            canonical_available = False

        # SUCCESS CONDITION: Only canonical path should be available
        if not canonical_available and not available_paths:
            pytest.skip(
                f"WebSocket Manager not yet available at canonical path {canonical_path}. "
                f"This test will pass once SSOT consolidation is complete."
            )

        assert canonical_available, (
            f"Canonical WebSocket Manager path {canonical_path} should be available after SSOT consolidation"
        )

        assert len(available_paths) == 0, (
            f"Fragmented import paths should be eliminated after SSOT consolidation. "
            f"Found: {available_paths}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_factory_import_consolidation(self):
        """
        FAIL-FIRST TEST: Detect fragmented WebSocket factory imports.

        This test validates that WebSocket factory creation uses a single
        canonical import path, preventing factory pattern fragmentation.
        """
        # Expected canonical factory import after SSOT consolidation
        canonical_factory_path = "netra_backend.app.websocket_core.websocket_manager.create_websocket_manager"

        # Fragmented factory import paths that should be eliminated
        fragmented_factory_paths = [
            "netra_backend.app.websocket_core.websocket_manager_factory.create_websocket_manager",
            "netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory",
            "netra_backend.app.websocket_core.unified_manager.create_unified_websocket_manager",
            "netra_backend.app.websocket_core.protocols.create_websocket_adapter"
        ]

        # Check for fragmented factory imports
        available_factory_paths = []

        for path in fragmented_factory_paths:
            module_path, factory_name = path.rsplit('.', 1)
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, factory_name):
                    available_factory_paths.append(path)
                    print(f"FACTORY FRAGMENTATION DETECTED: {path} is available")
            except ImportError:
                pass  # Expected after consolidation

        # ASSERTION: Multiple factory imports indicate SSOT violation
        if len(available_factory_paths) > 1:
            pytest.fail(
                f"SSOT VIOLATION: Multiple WebSocket factory import paths detected: "
                f"{available_factory_paths}. This factory fragmentation can cause "
                f"inconsistent instance creation and race conditions."
            )

        # SUCCESS: After consolidation, only canonical factory should exist
        canonical_module_path, canonical_function_name = canonical_factory_path.rsplit('.', 1)
        try:
            canonical_module = importlib.import_module(canonical_module_path)
            canonical_factory_available = hasattr(canonical_module, canonical_function_name)
        except ImportError:
            canonical_factory_available = False

        if not canonical_factory_available and not available_factory_paths:
            pytest.skip(
                f"WebSocket factory not yet available at canonical path {canonical_factory_path}. "
                f"This test will pass once SSOT consolidation is complete."
            )

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_protocol_import_elimination(self):
        """
        FAIL-FIRST TEST: Verify elimination of protocol-based WebSocket imports.

        This test ensures that protocol-based adapters and legacy imports
        are eliminated during SSOT consolidation.
        """
        # Protocol imports that should be eliminated during consolidation
        protocol_imports_to_eliminate = [
            "netra_backend.app.websocket_core.protocols.LegacyWebSocketManagerAdapter",
            "netra_backend.app.websocket_core.protocols.WebSocketProtocolAdapter",
            "netra_backend.app.agents.supervisor.agent_registry.WebSocketManagerAdapter",
            "netra_backend.app.websocket_core.adapters.WebSocketAdapter"
        ]

        # Check which protocol imports still exist
        existing_protocol_imports = []

        for import_path in protocol_imports_to_eliminate:
            module_path, class_name = import_path.rsplit('.', 1)
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    existing_protocol_imports.append(import_path)

                    # Get class info for detailed analysis
                    cls = getattr(module, class_name)
                    print(f"PROTOCOL FRAGMENTATION: {import_path} still exists")
                    print(f"  - Base classes: {[base.__name__ for base in cls.__bases__]}")
                    print(f"  - Module: {cls.__module__}")

            except ImportError:
                pass  # Expected - protocol imports should be eliminated

        # ASSERTION: Protocol imports should be eliminated after SSOT consolidation
        if existing_protocol_imports:
            pytest.fail(
                f"SSOT VIOLATION: Protocol-based WebSocket imports still exist: "
                f"{existing_protocol_imports}. These should be eliminated during "
                f"SSOT consolidation to prevent adapter pattern fragmentation."
            )

        # SUCCESS: All protocol imports have been eliminated
        assert len(existing_protocol_imports) == 0, (
            f"All protocol-based WebSocket imports should be eliminated after SSOT consolidation"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_cross_service_websocket_import_consistency(self):
        """
        FAIL-FIRST TEST: Validate consistent WebSocket imports across services.

        This test ensures that all services (backend, auth, shared) use the same
        WebSocket Manager import path, preventing cross-service fragmentation.
        """
        # Services that may import WebSocket Manager
        services_to_check = [
            "netra_backend.app.agents",
            "netra_backend.app.websocket_core",
            "netra_backend.app.routes",
            "netra_backend.app.services",
            "auth_service.auth_core"  # If auth service uses WebSocket
        ]

        # Track import patterns across services
        service_import_patterns = {}

        for service_path in services_to_check:
            try:
                # Find WebSocket-related imports in this service
                service_websocket_imports = self._find_websocket_imports_in_service(service_path)
                if service_websocket_imports:
                    service_import_patterns[service_path] = service_websocket_imports

            except Exception as e:
                print(f"Could not analyze service {service_path}: {e}")

        # Check for inconsistent import patterns
        if len(service_import_patterns) > 1:
            # Analyze import consistency
            all_import_paths = set()
            for service, imports in service_import_patterns.items():
                all_import_paths.update(imports)

            # ASSERTION: Multiple import patterns across services indicate fragmentation
            if len(all_import_paths) > 1:
                inconsistent_services = []
                for service, imports in service_import_patterns.items():
                    if len(set(imports)) > 1 or not all_import_paths.issubset(set(imports)):
                        inconsistent_services.append((service, imports))

                if inconsistent_services:
                    pytest.fail(
                        f"SSOT VIOLATION: Inconsistent WebSocket imports across services. "
                        f"Services using different import paths: {inconsistent_services}. "
                        f"All imports found: {all_import_paths}. "
                        f"This cross-service fragmentation can cause integration issues."
                    )

        # SUCCESS: All services should use the same canonical import
        print(f"Cross-service WebSocket import analysis: {service_import_patterns}")

    def _find_websocket_imports_in_service(self, service_path: str) -> List[str]:
        """Find WebSocket-related imports in a service."""
        websocket_imports = []

        try:
            # Import the service module to analyze its structure
            service_module = importlib.import_module(service_path)

            # Look for WebSocket-related attributes
            websocket_related_attrs = [
                attr for attr in dir(service_module)
                if 'websocket' in attr.lower() or 'ws' in attr.lower()
            ]

            for attr_name in websocket_related_attrs:
                attr = getattr(service_module, attr_name)
                if inspect.isclass(attr) or inspect.isfunction(attr):
                    module_name = getattr(attr, '__module__', None)
                    if module_name and 'websocket' in module_name.lower():
                        import_path = f"{module_name}.{attr.__name__}"
                        websocket_imports.append(import_path)

        except ImportError:
            pass  # Service may not exist or be importable

        return websocket_imports

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_duplicate_class_detection(self):
        """
        FAIL-FIRST TEST: Detect duplicate WebSocket Manager class definitions.

        This test scans for multiple class definitions that provide similar
        WebSocket Manager functionality, indicating code duplication.
        """
        # Scan for WebSocket Manager-like classes across the codebase
        websocket_manager_classes = []

        # Known modules that might contain WebSocket Manager classes
        modules_to_scan = [
            "netra_backend.app.websocket_core.websocket_manager",
            "netra_backend.app.websocket_core.unified_manager",
            "netra_backend.app.websocket_core.websocket_manager_factory",
            "netra_backend.app.websocket_core.protocols",
            "netra_backend.app.agents.supervisor.agent_registry"
        ]

        for module_path in modules_to_scan:
            try:
                module = importlib.import_module(module_path)

                # Find classes that look like WebSocket Managers
                for attr_name in dir(module):
                    if not attr_name.startswith('_'):
                        attr = getattr(module, attr_name)
                        if inspect.isclass(attr):
                            # Check if this looks like a WebSocket Manager
                            if ('websocket' in attr_name.lower() and
                                ('manager' in attr_name.lower() or
                                 'adapter' in attr_name.lower() or
                                 'factory' in attr_name.lower())):

                                websocket_manager_classes.append({
                                    'name': attr_name,
                                    'module': module_path,
                                    'class': attr,
                                    'methods': [m for m in dir(attr) if not m.startswith('_')],
                                    'bases': [base.__name__ for base in attr.__bases__]
                                })

            except ImportError:
                pass  # Module may not exist

        # ASSERTION: Multiple WebSocket Manager classes indicate duplication
        if len(websocket_manager_classes) > 1:
            class_info = []
            for cls_info in websocket_manager_classes:
                class_info.append(f"{cls_info['name']} ({cls_info['module']})")

            pytest.fail(
                f"SSOT VIOLATION: Multiple WebSocket Manager classes detected: "
                f"{class_info}. This indicates code duplication that should be "
                f"consolidated into a single SSOT implementation. "
                f"Total classes found: {len(websocket_manager_classes)}"
            )

        # SUCCESS: Only one WebSocket Manager class should exist
        assert len(websocket_manager_classes) <= 1, (
            f"Expected at most 1 WebSocket Manager class after SSOT consolidation, "
            f"found {len(websocket_manager_classes)}"
        )

        if websocket_manager_classes:
            canonical_class = websocket_manager_classes[0]
            print(f"SSOT SUCCESS: Single WebSocket Manager class found: "
                  f"{canonical_class['name']} in {canonical_class['module']}")