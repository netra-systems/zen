"""
Test Broadcast Duplication Detection - Phase 1 SSOT Violation Detection

CRITICAL TEST PURPOSE: Detect 3 different broadcast_to_user() implementations
These tests MUST FAIL initially to prove SSOT violations exist:

1. WebSocketEventRouter.broadcast_to_user() (legacy singleton)
2. UserScopedWebSocketEventRouter.broadcast_to_user() (user-scoped)
3. WebSocketBroadcastService.broadcast_to_user() (consolidated SSOT)

Business Value Justification (BVJ):
- Segment: Platform/Internal - SSOT Compliance
- Business Goal: Eliminate broadcast duplication causing cross-user event leakage
- Value Impact: Detect multiple broadcast implementations that create security vulnerabilities
- Strategic Impact: Foundation for $500K+ ARR protection through unified broadcasting

EXPECTED RESULT: These tests SHOULD FAIL, proving SSOT violations exist
SUCCESS CRITERIA: Tests fail demonstrating 3 different broadcast implementations

GitHub Issue: #1074 Message Router SSOT Violations - Phase 1 Detection
"""

import pytest
import asyncio
import importlib
import inspect
from typing import Dict, Any, List, Callable
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class BroadcastDuplicationViolationsTests(SSotAsyncTestCase):
    """
    Phase 1 SSOT Violation Detection: Multiple broadcast_to_user() implementations

    CRITICAL: These tests MUST FAIL to prove SSOT violations exist.
    Success is measured by test failure, not pass.
    """

    def setup_method(self, method):
        """Setup violation detection test."""
        super().setup_method(method)
        self.broadcast_implementations = []
        self.violation_evidence = {}

    async def test_detect_multiple_broadcast_to_user_implementations(self):
        """
        VIOLATION DETECTION: Multiple broadcast_to_user() implementations exist

        EXPECTED: FAIL - Multiple implementations should be detected
        PURPOSE: Prove SSOT violation exists in broadcast functionality
        """
        # Import paths for the 3 suspected broadcast_to_user() implementations
        import_specs = [
            {
                'module': 'netra_backend.app.services.websocket_event_router',
                'class': 'WebSocketEventRouter',
                'method': 'broadcast_to_user',
                'type': 'instance_method'
            },
            {
                'module': 'netra_backend.app.services.user_scoped_websocket_event_router',
                'class': 'UserScopedWebSocketEventRouter',
                'method': 'broadcast_to_user',
                'type': 'instance_method'
            },
            {
                'module': 'netra_backend.app.services.websocket_broadcast_service',
                'class': 'WebSocketBroadcastService',
                'method': 'broadcast_to_user',
                'type': 'instance_method'
            },
            {
                'module': 'netra_backend.app.services.websocket_event_router',
                'function': 'broadcast_to_user',
                'type': 'module_function'
            },
            {
                'module': 'netra_backend.app.services.user_scoped_websocket_event_router',
                'function': 'broadcast_to_user',
                'type': 'module_function'
            }
        ]

        discovered_implementations = []

        # Discover all broadcast_to_user implementations
        for spec in import_specs:
            try:
                module = importlib.import_module(spec['module'])

                if spec['type'] == 'instance_method' and 'class' in spec:
                    # Check for class method
                    if hasattr(module, spec['class']):
                        cls = getattr(module, spec['class'])
                        if hasattr(cls, spec['method']):
                            method_obj = getattr(cls, spec['method'])
                            if callable(method_obj):
                                discovered_implementations.append({
                                    'location': f"{spec['module']}.{spec['class']}.{spec['method']}",
                                    'method': method_obj,
                                    'source_file': inspect.getfile(cls),
                                    'source_line': inspect.findsource(method_obj)[1] if hasattr(method_obj, '__func__') else None,
                                    'type': 'class_method'
                                })

                elif spec['type'] == 'module_function' and 'function' in spec:
                    # Check for module function
                    if hasattr(module, spec['function']):
                        func_obj = getattr(module, spec['function'])
                        if callable(func_obj):
                            discovered_implementations.append({
                                'location': f"{spec['module']}.{spec['function']}",
                                'method': func_obj,
                                'source_file': inspect.getfile(func_obj),
                                'source_line': inspect.findsource(func_obj)[1],
                                'type': 'module_function'
                            })

            except (ImportError, AttributeError) as e:
                # Expected for some imports - not all may exist
                self.logger.debug(f"Could not import {spec}: {e}")
                continue

        # Record evidence of violations
        self.violation_evidence['broadcast_implementations'] = discovered_implementations
        self.violation_evidence['implementation_count'] = len(discovered_implementations)

        # Log discovered implementations for debugging
        self.logger.info(f"SSOT VIOLATION DETECTED: Found {len(discovered_implementations)} broadcast_to_user implementations:")
        for impl in discovered_implementations:
            self.logger.info(f"  - {impl['location']} ({impl['type']}) at {impl['source_file']}:{impl['source_line']}")

        # CRITICAL ASSERTION: This SHOULD FAIL if SSOT violations exist
        # If we find multiple implementations, we have an SSOT violation
        assert len(discovered_implementations) <= 1, (
            f"SSOT VIOLATION DETECTED: Found {len(discovered_implementations)} different broadcast_to_user() implementations. "
            f"SSOT compliance requires exactly 1 canonical implementation. "
            f"Detected implementations: {[impl['location'] for impl in discovered_implementations]}"
        )

        # If this assertion passes, it means SSOT compliance is achieved (unexpected for Phase 1)
        self.logger.warning("UNEXPECTED: No SSOT violations detected in broadcast_to_user implementations")

    async def test_detect_broadcast_behavior_inconsistencies(self):
        """
        VIOLATION DETECTION: Different broadcast_to_user() behaviors exist

        EXPECTED: FAIL - Inconsistent behavior should be detected
        PURPOSE: Prove behavioral differences between implementations
        """
        # Mock user_id and event for testing
        test_user_id = "test_user_123"
        test_event = {
            "type": "agent_started",
            "data": {"message": "Test broadcast"},
            "timestamp": "2025-09-14T12:00:00Z"
        }

        behavior_signatures = []

        # Test WebSocketEventRouter.broadcast_to_user (if it exists)
        try:
            from netra_backend.app.services.websocket_event_router import WebSocketEventRouter

            router = WebSocketEventRouter()

            # Mock the WebSocket manager to capture behavior
            router.websocket_manager = AsyncMock()
            router.websocket_manager.send_to_user = AsyncMock(return_value=1)

            result = await router.broadcast_to_user(test_user_id, test_event)

            behavior_signatures.append({
                'implementation': 'WebSocketEventRouter.broadcast_to_user',
                'accepts_user_id_param': True,
                'return_type': type(result).__name__,
                'return_value': result,
                'method_signature': str(inspect.signature(router.broadcast_to_user))
            })

        except (ImportError, AttributeError, Exception) as e:
            self.logger.debug(f"WebSocketEventRouter test failed: {e}")

        # Test UserScopedWebSocketEventRouter.broadcast_to_user (if it exists)
        try:
            from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # Create mock user execution context
            mock_context = MagicMock(spec=UserExecutionContext)
            mock_context.user_id = test_user_id

            router = UserScopedWebSocketEventRouter(mock_context)

            # Mock dependencies
            router.websocket_manager = AsyncMock()
            router.websocket_manager.send_to_user = AsyncMock(return_value=1)

            result = await router.broadcast_to_user(test_event)  # Note: no user_id param

            behavior_signatures.append({
                'implementation': 'UserScopedWebSocketEventRouter.broadcast_to_user',
                'accepts_user_id_param': False,  # Uses context user_id
                'return_type': type(result).__name__,
                'return_value': result,
                'method_signature': str(inspect.signature(router.broadcast_to_user))
            })

        except (ImportError, AttributeError, Exception) as e:
            self.logger.debug(f"UserScopedWebSocketEventRouter test failed: {e}")

        # Test WebSocketBroadcastService.broadcast_to_user (if it exists)
        try:
            from netra_backend.app.services.websocket_broadcast_service import WebSocketBroadcastService

            service = WebSocketBroadcastService()

            # Mock the underlying manager
            service._manager = AsyncMock()
            service._manager.send_to_user = AsyncMock(return_value=MagicMock())

            result = await service.broadcast_to_user(test_user_id, test_event)

            behavior_signatures.append({
                'implementation': 'WebSocketBroadcastService.broadcast_to_user',
                'accepts_user_id_param': True,
                'return_type': type(result).__name__,
                'return_value': result,
                'method_signature': str(inspect.signature(service.broadcast_to_user))
            })

        except (ImportError, AttributeError, Exception) as e:
            self.logger.debug(f"WebSocketBroadcastService test failed: {e}")

        # Record violation evidence
        self.violation_evidence['behavior_signatures'] = behavior_signatures

        # Log behavioral differences
        self.logger.info(f"BEHAVIORAL ANALYSIS: Found {len(behavior_signatures)} different broadcast behaviors:")
        for sig in behavior_signatures:
            self.logger.info(f"  - {sig['implementation']}: {sig['method_signature']}")
            self.logger.info(f"    Accepts user_id param: {sig['accepts_user_id_param']}")
            self.logger.info(f"    Return type: {sig['return_type']}")

        # CRITICAL ASSERTION: This SHOULD FAIL if behavioral inconsistencies exist
        if len(behavior_signatures) > 1:
            # Check for behavioral inconsistencies
            user_id_param_behaviors = {sig['accepts_user_id_param'] for sig in behavior_signatures}
            return_types = {sig['return_type'] for sig in behavior_signatures}

            inconsistencies = []
            if len(user_id_param_behaviors) > 1:
                inconsistencies.append("user_id parameter handling")
            if len(return_types) > 1:
                inconsistencies.append("return types")

            if inconsistencies:
                assert False, (
                    f"SSOT VIOLATION DETECTED: Behavioral inconsistencies found in broadcast_to_user implementations. "
                    f"Inconsistent behaviors: {', '.join(inconsistencies)}. "
                    f"SSOT compliance requires consistent behavior across all implementations."
                )

        # If this assertion passes, behavioral consistency exists (unexpected for Phase 1)
        self.logger.warning("UNEXPECTED: No behavioral inconsistencies detected in broadcast implementations")

    async def test_detect_import_path_duplication(self):
        """
        VIOLATION DETECTION: Multiple import paths for broadcast_to_user functionality

        EXPECTED: FAIL - Multiple import paths should exist
        PURPOSE: Prove import duplication violates SSOT principles
        """
        import_paths = [
            'netra_backend.app.services.websocket_event_router.WebSocketEventRouter.broadcast_to_user',
            'netra_backend.app.services.user_scoped_websocket_event_router.UserScopedWebSocketEventRouter.broadcast_to_user',
            'netra_backend.app.services.websocket_broadcast_service.WebSocketBroadcastService.broadcast_to_user',
            'netra_backend.app.services.websocket_event_router.broadcast_to_user',
            'netra_backend.app.services.user_scoped_websocket_event_router.broadcast_to_user'
        ]

        accessible_paths = []

        for path in import_paths:
            try:
                parts = path.split('.')
                module_path = '.'.join(parts[:-2]) if len(parts) > 2 else '.'.join(parts[:-1])

                module = importlib.import_module(module_path)

                # Navigate to the final callable
                obj = module
                for part in parts[len(module_path.split('.')):]:
                    if hasattr(obj, part):
                        obj = getattr(obj, part)
                    else:
                        obj = None
                        break

                if obj and callable(obj):
                    accessible_paths.append({
                        'path': path,
                        'callable': obj,
                        'module': module_path
                    })

            except (ImportError, AttributeError) as e:
                self.logger.debug(f"Import path not accessible: {path} - {e}")
                continue

        # Record violation evidence
        self.violation_evidence['import_paths'] = accessible_paths
        self.violation_evidence['accessible_path_count'] = len(accessible_paths)

        # Log accessible import paths
        self.logger.info(f"IMPORT PATH ANALYSIS: Found {len(accessible_paths)} accessible broadcast_to_user import paths:")
        for path_info in accessible_paths:
            self.logger.info(f"  - {path_info['path']} from {path_info['module']}")

        # CRITICAL ASSERTION: This SHOULD FAIL if multiple import paths exist
        assert len(accessible_paths) <= 1, (
            f"SSOT VIOLATION DETECTED: Found {len(accessible_paths)} different import paths for broadcast_to_user functionality. "
            f"SSOT compliance requires exactly 1 canonical import path. "
            f"Accessible paths: {[path['path'] for path in accessible_paths]}"
        )

        # If this assertion passes, SSOT compliance exists (unexpected for Phase 1)
        self.logger.warning("UNEXPECTED: SSOT compliance detected - only one broadcast import path found")

    def teardown_method(self, method):
        """Teardown and record violation evidence."""
        super().teardown_method(method)

        # Log summary of violations detected
        if self.violation_evidence:
            self.logger.info("SSOT VIOLATION EVIDENCE SUMMARY:")
            self.logger.info(f"  - Implementation count: {self.violation_evidence.get('implementation_count', 0)}")
            self.logger.info(f"  - Accessible import paths: {self.violation_evidence.get('accessible_path_count', 0)}")
            self.logger.info(f"  - Behavioral signatures: {len(self.violation_evidence.get('behavior_signatures', []))}")