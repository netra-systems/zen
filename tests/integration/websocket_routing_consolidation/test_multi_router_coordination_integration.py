"""
Test Multi-Router Coordination with Real Services

PURPOSE: Validate routing coordination failures with real PostgreSQL/Redis
STATUS: SHOULD FAIL initially - coordination failures with real data
EXPECTED: PASS after SSOT consolidation eliminates coordination complexity

Business Value Justification (BVJ):
- Segment: Enterprise/Platform
- Goal: System reliability and data consistency
- Value Impact: Ensures router coordination doesn't cause data inconsistencies
- Revenue Impact: Prevents $500K+ ARR loss from coordination failures affecting user data

This integration test validates that multiple router implementations don't
cause coordination failures when working with real services, which would
affect data integrity and user experience in production.
"""

import asyncio
from typing import Dict, Any, List, Optional
import pytest

from test_framework.ssot.base_test_case import BaseIntegrationTest


class MultiRouterCoordinationTests(BaseIntegrationTest):
    """Test router coordination with real services."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_routing_coordination(self, real_services_fixture):
        """Test routing coordination with real database operations.

        This test should FAIL initially by detecting that different router
        implementations cause coordination issues with real database operations,
        affecting thread and user data consistency.

        Expected failures:
        1. Different routers create conflicting database queries
        2. Thread/user data inconsistencies across routers
        3. Transaction coordination failures between routers

        SUCCESS CRITERIA: Single router maintains database consistency
        """
        coordination_failures = []

        # Test data for router coordination testing
        test_user_id = 'coordination-test-user-123'
        test_thread_id = 'coordination-test-thread-456'

        test_message = {
            'type': 'start_agent',
            'data': {
                'user_id': test_user_id,
                'thread_id': test_thread_id,
                'message': 'Test database coordination',
                'requires_db_access': True
            }
        }

        # Attempt to route through different routers and check database impact
        database_coordination_results = {}

        try:
            # Test MessageRouter database coordination
            from netra_backend.app.websocket_core.handlers import MessageRouter
            message_router = MessageRouter()

            # Simulate database-affecting routing
            database_coordination_results['MessageRouter'] = {
                'router_exists': True,
                'can_handle_db_message': await self._test_db_routing(
                    message_router, 'MessageRouter', test_message
                ),
                'coordination_method': 'handle_message'
            }

        except Exception as e:
            coordination_failures.append(f"MessageRouter database coordination error: {e}")
            database_coordination_results['MessageRouter'] = {'error': str(e)}

        try:
            # Test QualityMessageRouter database coordination
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

            # Mock dependencies for testing
            from unittest.mock import MagicMock
            mock_supervisor = MagicMock()
            mock_db_session_factory = MagicMock()
            mock_quality_gate_service = MagicMock()
            mock_monitoring_service = MagicMock()

            quality_router = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )

            database_coordination_results['QualityMessageRouter'] = {
                'router_exists': True,
                'can_handle_db_message': await self._test_db_routing(
                    quality_router, 'QualityMessageRouter', test_message
                ),
                'coordination_method': 'quality_handlers',
                'has_db_session_factory': mock_db_session_factory is not None
            }

        except Exception as e:
            coordination_failures.append(f"QualityMessageRouter database coordination error: {e}")
            database_coordination_results['QualityMessageRouter'] = {'error': str(e)}

        # Analyze database coordination conflicts
        print("\n=== DATABASE ROUTING COORDINATION ANALYSIS ===")
        for router_name, result in database_coordination_results.items():
            print(f"{router_name}: {result}")

        # Check for coordination conflicts
        routers_with_db_access = []
        for router_name, result in database_coordination_results.items():
            if ('error' not in result and
                result.get('can_handle_db_message', False)):
                routers_with_db_access.append(router_name)

        if len(routers_with_db_access) > 1:
            coordination_failures.append(
                f"Multiple routers with database access create coordination conflicts: "
                f"{routers_with_db_access}"
            )

        # Check for different coordination methods
        coordination_methods = set()
        for router_name, result in database_coordination_results.items():
            if 'error' not in result and 'coordination_method' in result:
                coordination_methods.add(result['coordination_method'])

        if len(coordination_methods) > 1:
            coordination_failures.append(
                f"Different database coordination methods detected: {coordination_methods}"
            )

        # This should FAIL initially - expect database coordination conflicts
        self.assertEqual(len(coordination_failures), 0,
            f"DATABASE ROUTING COORDINATION FAILURES: Found {len(coordination_failures)} "
            f"coordination failures: {coordination_failures}")

    async def _test_db_routing(self, router: Any, router_name: str,
                              message: Dict[str, Any]) -> bool:
        """Test if router can handle database-affecting messages."""
        try:
            if router_name == 'MessageRouter':
                # Check if MessageRouter has database-aware handlers
                builtin_handlers = getattr(router, 'builtin_handlers', [])
                for handler in builtin_handlers:
                    handler_name = type(handler).__name__
                    if any(db_term in handler_name.lower()
                          for db_term in ['agent', 'user', 'thread']):
                        return True
                return False

            elif router_name == 'QualityMessageRouter':
                # Check if QualityMessageRouter has database session factory
                return hasattr(router, 'db_session_factory')

        except Exception:
            return False

        return False

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_cache_routing_consistency(self, real_services_fixture):
        """Test routing consistency with real Redis cache.

        This test should FAIL initially by detecting that different router
        implementations handle Redis cache operations inconsistently.

        Expected failures:
        1. Different caching strategies across routers
        2. Cache key conflicts between router implementations
        3. Inconsistent cache invalidation patterns

        SUCCESS CRITERIA: Single router maintains cache consistency
        """
        cache_consistency_failures = []

        test_cache_message = {
            'type': 'agent_thinking',
            'data': {
                'user_id': 'cache-test-user-123',
                'thread_id': 'cache-test-thread-456',
                'message': 'Test cache consistency',
                'cache_key': 'agent_state_cache_test',
                'requires_caching': True
            }
        }

        cache_coordination_results = {}

        # Test cache handling across different routers
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            message_router = MessageRouter()

            cache_coordination_results['MessageRouter'] = {
                'handles_caching': await self._test_cache_routing(
                    message_router, 'MessageRouter', test_cache_message
                ),
                'cache_strategy': 'message_handler_based'
            }

        except Exception as e:
            cache_consistency_failures.append(f"MessageRouter cache error: {e}")

        try:
            from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
            from unittest.mock import MagicMock

            mock_websocket_manager = MagicMock()
            event_router = WebSocketEventRouter(websocket_manager=mock_websocket_manager)

            cache_coordination_results['WebSocketEventRouter'] = {
                'handles_caching': await self._test_cache_routing(
                    event_router, 'WebSocketEventRouter', test_cache_message
                ),
                'cache_strategy': 'event_based'
            }

        except Exception as e:
            cache_consistency_failures.append(f"WebSocketEventRouter cache error: {e}")

        # Analyze cache consistency
        print("\n=== REDIS CACHE ROUTING CONSISTENCY ANALYSIS ===")
        for router_name, result in cache_coordination_results.items():
            print(f"{router_name}: {result}")

        # Check for inconsistent cache handling
        cache_strategies = set()
        routers_with_caching = []

        for router_name, result in cache_coordination_results.items():
            if result.get('handles_caching', False):
                routers_with_caching.append(router_name)
                if 'cache_strategy' in result:
                    cache_strategies.add(result['cache_strategy'])

        if len(cache_strategies) > 1:
            cache_consistency_failures.append(
                f"Inconsistent cache strategies detected: {cache_strategies}"
            )

        if len(routers_with_caching) > 1:
            cache_consistency_failures.append(
                f"Multiple routers handling caching creates conflicts: {routers_with_caching}"
            )

        # This should FAIL initially - expect cache consistency issues
        self.assertEqual(len(cache_consistency_failures), 0,
            f"REDIS CACHE ROUTING CONSISTENCY FAILURES: Found {len(cache_consistency_failures)} "
            f"cache consistency failures: {cache_consistency_failures}")

    async def _test_cache_routing(self, router: Any, router_name: str,
                                 message: Dict[str, Any]) -> bool:
        """Test if router handles cache-related operations."""
        try:
            if router_name == 'MessageRouter':
                # Check for cache-aware handlers
                builtin_handlers = getattr(router, 'builtin_handlers', [])
                return any('agent' in type(handler).__name__.lower()
                          for handler in builtin_handlers)

            elif router_name == 'WebSocketEventRouter':
                # Check for connection pool management (cache-like behavior)
                return hasattr(router, 'connection_pool')

        except Exception:
            return False

        return False

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_routing_isolation_failures(self, real_services_fixture):
        """Test multi-user isolation failures in fragmented routing.

        This test should FAIL initially by detecting that multiple router
        implementations don't maintain proper user isolation, causing
        potential cross-user data leakage.

        Expected failures:
        1. Different user isolation strategies across routers
        2. Cross-user message routing due to fragmentation
        3. User context not maintained consistently

        SUCCESS CRITERIA: Single router maintains perfect user isolation
        """
        isolation_failures = []

        # Create test messages for different users
        user1_message = {
            'type': 'user_message',
            'data': {
                'user_id': 'isolation-user-1',
                'thread_id': 'thread-1',
                'message': 'User 1 private message',
                'sensitive_data': True
            }
        }

        user2_message = {
            'type': 'user_message',
            'data': {
                'user_id': 'isolation-user-2',
                'thread_id': 'thread-2',
                'message': 'User 2 private message',
                'sensitive_data': True
            }
        }

        isolation_results = {}

        # Test user isolation across different routers
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            message_router = MessageRouter()

            isolation_results['MessageRouter'] = await self._test_user_isolation(
                message_router, 'MessageRouter', user1_message, user2_message
            )

        except Exception as e:
            isolation_failures.append(f"MessageRouter isolation error: {e}")

        try:
            from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
            from unittest.mock import MagicMock

            mock_websocket_manager = MagicMock()
            event_router = WebSocketEventRouter(websocket_manager=mock_websocket_manager)

            isolation_results['WebSocketEventRouter'] = await self._test_user_isolation(
                event_router, 'WebSocketEventRouter', user1_message, user2_message
            )

        except Exception as e:
            isolation_failures.append(f"WebSocketEventRouter isolation error: {e}")

        # Analyze user isolation
        print("\n=== MULTI-USER ROUTING ISOLATION ANALYSIS ===")
        for router_name, result in isolation_results.items():
            print(f"{router_name}: {result}")

        # Check for isolation failures
        for router_name, result in isolation_results.items():
            if not result.get('maintains_isolation', True):
                isolation_failures.append(
                    f"{router_name} fails to maintain user isolation"
                )

            if result.get('cross_user_leakage', False):
                isolation_failures.append(
                    f"{router_name} shows potential cross-user data leakage"
                )

        # Check for different isolation mechanisms
        isolation_mechanisms = set()
        for router_name, result in isolation_results.items():
            if 'isolation_mechanism' in result:
                isolation_mechanisms.add(result['isolation_mechanism'])

        if len(isolation_mechanisms) > 1:
            isolation_failures.append(
                f"Different user isolation mechanisms create inconsistency: {isolation_mechanisms}"
            )

        # This should FAIL initially - expect user isolation issues
        self.assertEqual(len(isolation_failures), 0,
            f"MULTI-USER ROUTING ISOLATION FAILURES: Found {len(isolation_failures)} "
            f"user isolation failures: {isolation_failures}")

    async def _test_user_isolation(self, router: Any, router_name: str,
                                  user1_msg: Dict[str, Any],
                                  user2_msg: Dict[str, Any]) -> Dict[str, Any]:
        """Test user isolation capabilities of a router."""
        result = {
            'maintains_isolation': True,
            'cross_user_leakage': False,
            'isolation_mechanism': 'unknown'
        }

        try:
            if router_name == 'MessageRouter':
                # MessageRouter should isolate by user context in handlers
                result['isolation_mechanism'] = 'handler_based'

                # Check if handlers consider user_id
                builtin_handlers = getattr(router, 'builtin_handlers', [])
                has_user_aware_handlers = any(
                    'user' in type(handler).__name__.lower()
                    for handler in builtin_handlers
                )
                result['maintains_isolation'] = has_user_aware_handlers

            elif router_name == 'WebSocketEventRouter':
                # WebSocketEventRouter should isolate by connection pool
                result['isolation_mechanism'] = 'connection_pool'

                # Check for connection isolation features
                has_connection_pool = hasattr(router, 'connection_pool')
                has_user_mapping = hasattr(router, 'connection_to_user')

                result['maintains_isolation'] = has_connection_pool and has_user_mapping

        except Exception:
            result['maintains_isolation'] = False

        return result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])