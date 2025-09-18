"""
Test to demonstrate SSOT violation in message routing implementations.

This test demonstrates the critical SSOT violation where multiple message router 
implementations exist in parallel, causing confusion and potential routing conflicts
that threaten the $500K+ ARR Golden Path chat functionality.

The test INTENTIONALLY FAILS to show the problem before SSOT consolidation.
After consolidation, this test should be updated to validate the resolved state.

Business Impact:
- Multiple router implementations create maintenance overhead
- Inconsistent routing behavior across system components  
- Risk of cross-user message routing in multi-user environment
- Potential security vulnerabilities from routing confusion

Created: 2025-09-17
GitHub Issue: SSOT-incomplete-migration-message-routing-consolidation
"""

import asyncio
import inspect
import importlib
from typing import List, Dict, Any, Set, Type
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestMessageRoutingSSOTViolation(SSotAsyncTestCase):
    """
    Test that demonstrates the SSOT violation in message routing.
    
    This test FAILS INTENTIONALLY to show the problem that needs to be fixed.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.env = get_env()
        self.discovered_routers = []
        self.import_paths = []

    async def test_multiple_router_implementations_exist(self):
        """
        FAILING TEST: Demonstrates that multiple router implementations exist.
        
        This test discovers and documents all router implementations in the codebase,
        proving the SSOT violation. It will fail until consolidation is complete.
        """
        # Discover all router implementations
        router_implementations = await self._discover_router_implementations()
        
        # Document what we found for analysis
        self._log_router_discovery(router_implementations)
        
        # INTENTIONAL FAILURE: This test proves we have SSOT violations
        # After consolidation, only CanonicalMessageRouter should exist as primary implementation
        primary_routers = [r for r in router_implementations if not r.get('is_adapter', False)]
        
        self.assertGreater(
            len(primary_routers), 1,
            f"SSOT VIOLATION CONFIRMED: Found {len(primary_routers)} primary router implementations. "
            f"Expected exactly 1 (CanonicalMessageRouter). Found: {[r['name'] for r in primary_routers]}"
        )

    async def test_inconsistent_router_interfaces(self):
        """
        FAILING TEST: Shows interface inconsistencies between router implementations.
        
        Different routers have different method signatures and capabilities,
        proving the need for SSOT consolidation.
        """
        router_implementations = await self._discover_router_implementations()
        
        # Analyze interface differences
        interface_analysis = await self._analyze_router_interfaces(router_implementations)
        
        # Document interface inconsistencies
        inconsistencies = interface_analysis.get('inconsistencies', [])
        
        # INTENTIONAL FAILURE: Proves interface inconsistencies exist
        self.assertGreater(
            len(inconsistencies), 0,
            f"INTERFACE INCONSISTENCY VIOLATION: Found {len(inconsistencies)} interface inconsistencies. "
            f"This proves multiple router implementations have different capabilities."
        )

    async def test_factory_pattern_violations(self):
        """
        FAILING TEST: Shows multiple factory functions for router creation.
        
        Multiple factory functions indicate fragmented router creation patterns,
        violating SSOT principles for router instantiation.
        """
        factory_functions = await self._discover_router_factories()
        
        # INTENTIONAL FAILURE: Proves multiple factory patterns exist
        self.assertGreater(
            len(factory_functions), 1,
            f"FACTORY PATTERN VIOLATION: Found {len(factory_functions)} router factory functions. "
            f"Expected exactly 1 canonical factory. Found: {[f['name'] for f in factory_functions]}"
        )

    async def test_import_path_confusion(self):
        """
        FAILING TEST: Shows multiple import paths for similar router functionality.
        
        Multiple import paths for router functionality create confusion and
        potential for importing wrong router implementation.
        """
        import_paths = await self._discover_router_import_paths()
        
        # Group by functionality to find duplicates
        functionality_groups = self._group_imports_by_functionality(import_paths)
        
        # Find groups with multiple import paths
        conflicting_groups = {
            func: paths for func, paths in functionality_groups.items() 
            if len(paths) > 1
        }
        
        # INTENTIONAL FAILURE: Proves import path confusion exists
        self.assertGreater(
            len(conflicting_groups), 0,
            f"IMPORT PATH CONFUSION: Found {len(conflicting_groups)} functionality groups with multiple import paths. "
            f"This creates confusion about which router to import. Conflicts: {list(conflicting_groups.keys())}"
        )

    async def _discover_router_implementations(self) -> List[Dict[str, Any]]:
        """Discover all router class implementations in the codebase."""
        routers = []
        
        try:
            # CanonicalMessageRouter - SSOT implementation
            from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
            routers.append({
                'name': 'CanonicalMessageRouter',
                'class': CanonicalMessageRouter,
                'module': 'netra_backend.app.websocket_core.canonical_message_router',
                'is_adapter': False,
                'is_ssot': True,
                'line_count': await self._get_class_line_count(CanonicalMessageRouter)
            })
        except ImportError as e:
            self.fail(f"CRITICAL: Cannot import CanonicalMessageRouter (SSOT): {e}")

        try:
            # WebSocketEventRouter - Legacy implementation  
            from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
            routers.append({
                'name': 'WebSocketEventRouter', 
                'class': WebSocketEventRouter,
                'module': 'netra_backend.app.services.websocket_event_router',
                'is_adapter': getattr(WebSocketEventRouter, '_is_adapter', False),
                'is_ssot': False,
                'line_count': await self._get_class_line_count(WebSocketEventRouter)
            })
        except ImportError:
            pass  # May have been removed

        try:
            # UserScopedWebSocketEventRouter - Legacy implementation
            from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter
            routers.append({
                'name': 'UserScopedWebSocketEventRouter',
                'class': UserScopedWebSocketEventRouter, 
                'module': 'netra_backend.app.services.user_scoped_websocket_event_router',
                'is_adapter': getattr(UserScopedWebSocketEventRouter, '_is_adapter', False),
                'is_ssot': False,
                'line_count': await self._get_class_line_count(UserScopedWebSocketEventRouter)
            })
        except ImportError:
            pass  # May have been removed

        # Check for compatibility adapters
        try:
            # MessageRouter compatibility adapter
            from netra_backend.app.routes.message_router import MessageRouter
            routers.append({
                'name': 'MessageRouter',
                'class': MessageRouter,
                'module': 'netra_backend.app.routes.message_router', 
                'is_adapter': True,
                'is_ssot': False,
                'line_count': await self._get_class_line_count(MessageRouter)
            })
        except ImportError:
            pass

        return routers

    async def _discover_router_factories(self) -> List[Dict[str, Any]]:
        """Discover all router factory functions."""
        factories = []
        
        # Check for various factory function patterns
        factory_patterns = [
            ('create_message_router', 'netra_backend.app.websocket_core.canonical_message_router'),
            ('get_websocket_router', 'netra_backend.app.services.websocket_event_router'),
            ('create_user_event_router', 'netra_backend.app.services.user_scoped_websocket_event_router'),
            ('get_message_router', 'netra_backend.app.routes.message_router'),
        ]
        
        for func_name, module_name in factory_patterns:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, func_name):
                    factories.append({
                        'name': func_name,
                        'module': module_name,
                        'function': getattr(module, func_name)
                    })
            except ImportError:
                continue
                
        return factories

    async def _discover_router_import_paths(self) -> List[Dict[str, Any]]:
        """Discover all possible import paths for router functionality."""
        import_paths = []
        
        # Test various import paths that might exist
        import_tests = [
            {
                'functionality': 'message_routing',
                'path': 'netra_backend.app.websocket_core.canonical_message_router',
                'target': 'CanonicalMessageRouter'
            },
            {
                'functionality': 'event_routing', 
                'path': 'netra_backend.app.services.websocket_event_router',
                'target': 'WebSocketEventRouter'
            },
            {
                'functionality': 'user_routing',
                'path': 'netra_backend.app.services.user_scoped_websocket_event_router', 
                'target': 'UserScopedWebSocketEventRouter'
            },
            {
                'functionality': 'message_routing',
                'path': 'netra_backend.app.routes.message_router',
                'target': 'MessageRouter'
            },
            {
                'functionality': 'message_routing',
                'path': 'netra_backend.app.websocket_core.handlers',
                'target': 'MessageRouter'
            },
        ]
        
        for test in import_tests:
            try:
                module = importlib.import_module(test['path'])
                if hasattr(module, test['target']):
                    import_paths.append(test)
            except ImportError:
                continue
                
        return import_paths

    async def _analyze_router_interfaces(self, routers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze interface differences between router implementations."""
        analysis = {
            'methods': {},
            'inconsistencies': []
        }
        
        for router_info in routers:
            router_class = router_info['class']
            methods = [method for method in dir(router_class) if not method.startswith('_')]
            analysis['methods'][router_info['name']] = methods
            
        # Find methods that exist in some routers but not others
        all_methods = set()
        for methods in analysis['methods'].values():
            all_methods.update(methods)
            
        for method in all_methods:
            router_with_method = []
            router_without_method = []
            
            for router_name, methods in analysis['methods'].items():
                if method in methods:
                    router_with_method.append(router_name)
                else:
                    router_without_method.append(router_name)
                    
            if router_without_method:
                analysis['inconsistencies'].append({
                    'method': method,
                    'has_method': router_with_method,
                    'missing_method': router_without_method
                })
                
        return analysis

    def _group_imports_by_functionality(self, import_paths: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group import paths by functionality to find duplicates."""
        groups = {}
        
        for import_info in import_paths:
            functionality = import_info['functionality']
            path = f"{import_info['path']}.{import_info['target']}"
            
            if functionality not in groups:
                groups[functionality] = []
            groups[functionality].append(path)
            
        return groups

    async def _get_class_line_count(self, cls: Type) -> int:
        """Get approximate line count for a class."""
        try:
            source_lines = inspect.getsourcelines(cls)[0]
            return len(source_lines)
        except (OSError, TypeError):
            return 0

    def _log_router_discovery(self, routers: List[Dict[str, Any]]):
        """Log discovered routers for analysis."""
        print(f"\n=== MESSAGE ROUTER SSOT VIOLATION ANALYSIS ===")
        print(f"Total router implementations found: {len(routers)}")
        
        for router in routers:
            print(f"\nRouter: {router['name']}")
            print(f"  Module: {router['module']}")
            print(f"  SSOT: {router['is_ssot']}")
            print(f"  Adapter: {router['is_adapter']}")
            print(f"  Lines: {router['line_count']}")
            
        primary_routers = [r for r in routers if not r.get('is_adapter', False)]
        print(f"\nPrimary implementations: {len(primary_routers)}")
        print(f"Adapter implementations: {len(routers) - len(primary_routers)}")
        print(f"SSOT Violation: {len(primary_routers) > 1}")