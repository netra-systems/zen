"""
Test Router Implementation Discovery and Fragmentation Detection

PURPOSE: Reproduce Issue #994 by discovering multiple MessageRouter implementations
STATUS: SHOULD FAIL initially - detecting fragmentation violations
EXPECTED: PASS after SSOT consolidation to single router

Business Value Justification (BVJ):
- Segment: Enterprise/Platform
- Goal: System Stability and Golden Path reliability
- Value Impact: Eliminates routing conflicts causing AI response delivery failures
- Revenue Impact: Protects $500K+ ARR by ensuring reliable WebSocket message routing

This test reproduces the core fragmentation issue blocking Golden Path:
Multiple router implementations cause message routing conflicts, preventing proper
tool dispatching and agent execution, which blocks users from receiving AI responses.
"""

import os
import ast
import inspect
from typing import Set, List, Dict, Any
from pathlib import Path
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class RouterImplementationDiscoveryTests(SSotAsyncTestCase):
    """Detect and validate MessageRouter implementation fragmentation."""

    def setUp(self) -> None:
        """Set up test environment."""
        super().setUp()
        self.project_root = Path(__file__).parents[3]  # Navigate to project root
        self.backend_path = self.project_root / "netra_backend"
        self.discovered_routers = {}

    async def test_single_message_router_implementation(self):
        """SHOULD FAIL: Multiple MessageRouter implementations detected.

        This test scans the codebase for MessageRouter class definitions and should
        initially FAIL by detecting multiple implementations that violate SSOT principles.

        Expected failures:
        1. MessageRouter in websocket_core/handlers.py
        2. QualityMessageRouter in services/websocket/quality_message_router.py
        3. WebSocketEventRouter in services/websocket_event_router.py
        4. Any additional router classes found

        SUCCESS CRITERIA: Only ONE canonical MessageRouter implementation exists
        """
        # Scan for all Python files in backend
        router_implementations = []

        for root, dirs, files in os.walk(self.backend_path):
            # Skip test directories and __pycache__
            if '__pycache__' in root or 'test' in root.lower():
                continue

            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            tree = ast.parse(content)

                        # Look for router class definitions
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                if 'router' in class_name.lower() or 'Router' in class_name:
                                    relative_path = file_path.relative_to(self.project_root)
                                    router_implementations.append({
                                        'name': class_name,
                                        'file': str(relative_path),
                                        'line': node.lineno
                                    })

                    except (UnicodeDecodeError, SyntaxError) as e:
                        # Skip files that can't be parsed
                        continue

        # Store for other tests
        self.discovered_routers['implementations'] = router_implementations

        # Document discovered implementations
        print("\n=== ROUTER IMPLEMENTATION DISCOVERY RESULTS ===")
        for router in router_implementations:
            print(f"Router: {router['name']} in {router['file']}:{router['line']}")

        # This should FAIL initially - we expect multiple router implementations
        # indicating SSOT fragmentation violation
        self.assertLessEqual(len(router_implementations), 1,
            f"SSOT VIOLATION: Found {len(router_implementations)} router implementations. "
            f"Expected 1 canonical implementation. Discovered: {router_implementations}")

    async def test_routing_interface_consistency(self):
        """SHOULD FAIL: Inconsistent routing interfaces across implementations.

        This test examines routing method interfaces across different router
        implementations to detect inconsistencies causing Golden Path failures.

        Expected failures:
        1. Different method signatures for routing operations
        2. Inconsistent message handling interfaces
        3. Conflicting handler registration patterns

        SUCCESS CRITERIA: All routing interfaces are consistent and interchangeable
        """
        # Import the known router classes for interface inspection
        router_classes = []

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router_classes.append(('MessageRouter', MessageRouter))
        except ImportError as e:
            print(f"Could not import MessageRouter: {e}")

        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            router_classes.append(('QualityMessageRouter', QualityMessageRouter))
        except ImportError as e:
            print(f"Could not import QualityMessageRouter: {e}")

        try:
            from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
            router_classes.append(('WebSocketEventRouter', WebSocketEventRouter))
        except ImportError as e:
            print(f"Could not import WebSocketEventRouter: {e}")

        # Analyze interface consistency
        routing_methods = {}
        for name, router_class in router_classes:
            methods = []
            for method_name in dir(router_class):
                if not method_name.startswith('_'):
                    method = getattr(router_class, method_name)
                    if callable(method):
                        try:
                            sig = inspect.signature(method)
                            methods.append({
                                'name': method_name,
                                'signature': str(sig),
                                'parameters': list(sig.parameters.keys())
                            })
                        except (ValueError, TypeError):
                            # Skip methods that can't be inspected
                            continue
            routing_methods[name] = methods

        # Document interface differences
        print("\n=== ROUTING INTERFACE ANALYSIS ===")
        for router_name, methods in routing_methods.items():
            print(f"\n{router_name} methods:")
            for method in methods:
                print(f"  {method['name']}{method['signature']}")

        # Check for common routing methods across implementations
        common_method_names = set()
        if routing_methods:
            first_router = next(iter(routing_methods.values()))
            common_method_names = {method['name'] for method in first_router}

            for router_methods in routing_methods.values():
                router_method_names = {method['name'] for method in router_methods}
                common_method_names &= router_method_names

        # This should FAIL initially - expect interface inconsistencies
        # indicating fragmented routing contracts
        inconsistency_count = len(routing_methods) - len(common_method_names) if routing_methods else 0

        self.assertEqual(inconsistency_count, 0,
            f"ROUTING INTERFACE INCONSISTENCY: Found {inconsistency_count} interface "
            f"inconsistencies across {len(routing_methods)} router implementations. "
            f"Common methods: {common_method_names}")

    async def test_handler_registration_conflicts(self):
        """SHOULD FAIL: Handler registration conflicts between routers.

        This test examines handler registration mechanisms across router
        implementations to detect conflicts that cause message routing failures.

        Expected failures:
        1. Multiple routers registering handlers for same message types
        2. Conflicting handler precedence rules
        3. Handler registration inconsistencies causing dispatch failures

        SUCCESS CRITERIA: Single consolidated handler registration mechanism
        """
        # Test handler registration patterns
        handler_registration_analysis = {}

        # Analyze MessageRouter handler registration
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()

            # Inspect handler lists
            custom_handlers = getattr(router, 'custom_handlers', [])
            builtin_handlers = getattr(router, 'builtin_handlers', [])

            handler_registration_analysis['MessageRouter'] = {
                'custom_handlers': [type(h).__name__ for h in custom_handlers],
                'builtin_handlers': [type(h).__name__ for h in builtin_handlers],
                'total_handlers': len(custom_handlers) + len(builtin_handlers),
                'has_quality_router_handler': any('Quality' in type(h).__name__
                                                for h in builtin_handlers)
            }

        except (ImportError, Exception) as e:
            print(f"Could not analyze MessageRouter handlers: {e}")
            handler_registration_analysis['MessageRouter'] = {'error': str(e)}

        # Analyze QualityMessageRouter handler registration
        try:
            # Can't instantiate without dependencies, but check class structure
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            import inspect

            # Get initialization signature
            init_sig = inspect.signature(QualityMessageRouter.__init__)
            method_list = [method for method in dir(QualityMessageRouter)
                          if not method.startswith('_')]

            handler_registration_analysis['QualityMessageRouter'] = {
                'init_parameters': list(init_sig.parameters.keys()),
                'public_methods': method_list,
                'has_handlers_attr': '_initialize_handlers' in method_list,
                'depends_on_supervisor': 'supervisor' in init_sig.parameters
            }

        except (ImportError, Exception) as e:
            print(f"Could not analyze QualityMessageRouter: {e}")
            handler_registration_analysis['QualityMessageRouter'] = {'error': str(e)}

        # Analyze WebSocketEventRouter registration
        try:
            from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
            import inspect

            init_sig = inspect.signature(WebSocketEventRouter.__init__)
            method_list = [method for method in dir(WebSocketEventRouter)
                          if not method.startswith('_')]

            handler_registration_analysis['WebSocketEventRouter'] = {
                'init_parameters': list(init_sig.parameters.keys()),
                'public_methods': method_list,
                'manages_connections': 'connection_pool' in method_list,
                'depends_on_websocket_manager': 'websocket_manager' in init_sig.parameters
            }

        except (ImportError, Exception) as e:
            print(f"Could not analyze WebSocketEventRouter: {e}")
            handler_registration_analysis['WebSocketEventRouter'] = {'error': str(e)}

        # Document handler registration conflicts
        print("\n=== HANDLER REGISTRATION CONFLICT ANALYSIS ===")
        for router_name, analysis in handler_registration_analysis.items():
            print(f"\n{router_name}:")
            for key, value in analysis.items():
                print(f"  {key}: {value}")

        # Detect registration conflicts
        conflicts = []

        # Check for overlapping responsibilities
        if ('MessageRouter' in handler_registration_analysis and
            'QualityMessageRouter' in handler_registration_analysis):
            if (handler_registration_analysis['MessageRouter'].get('has_quality_router_handler') and
                'error' not in handler_registration_analysis['QualityMessageRouter']):
                conflicts.append("MessageRouter has QualityRouterHandler while QualityMessageRouter exists")

        # Check for dependency conflicts
        router_count = len([r for r in handler_registration_analysis.values()
                           if 'error' not in r])

        if router_count > 1:
            conflicts.append(f"Multiple router implementations ({router_count}) create registration conflicts")

        # This should FAIL initially - expect handler registration conflicts
        # indicating fragmented message handling
        self.assertEqual(len(conflicts), 0,
            f"HANDLER REGISTRATION CONFLICTS: Found {len(conflicts)} conflicts: {conflicts}. "
            f"Analysis: {handler_registration_analysis}")

        # Store analysis for other tests
        self.discovered_routers['handler_analysis'] = handler_registration_analysis


if __name__ == "__main__":
    pytest.main([__file__, "-v"])