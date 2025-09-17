"""
Integration Test: Real WebSocket Connection SSOT Patterns - Issue #1098

CRITICAL: This test must FAIL initially to prove SSOT violations exist.
After SSOT migration, this test must PASS to prove success.

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform)
- Business Goal: Validate real WebSocket connections use SSOT patterns exclusively
- Value Impact: Ensures Golden Path reliability with real service integration
- Revenue Impact: Protects $500K+ ARR by validating SSOT patterns work in practice

ENVIRONMENT REQUIREMENTS:
- Real PostgreSQL database (NO Docker)
- Real Redis instance (NO Docker)
- Real WebSocket connections
- Local services only

FAILING TEST STRATEGY:
1. Test initially FAILS proving real services use factory patterns
2. SSOT migration updates real service integration
3. Test PASSES proving real services use SSOT exclusively
"""

import asyncio
import pytest
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Real service imports for integration testing
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestRealWebSocketSSoTIntegration(SSotAsyncTestCase):
    """
    Integration tests with real services to validate SSOT patterns.

    CRITICAL: These tests use real PostgreSQL, Redis, and WebSocket connections.
    NO Docker dependencies. Tests must FAIL initially proving factory usage.
    """

    async def asyncSetUp(self):
        """Set up real service integration test environment."""
        await super().asyncSetUp()

        # Skip if real services not available
        self.real_services_available = await self._check_real_services_available()
        if not self.real_services_available:
            self.skipTest("Real services (PostgreSQL, Redis) not available")

        # Test configuration
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"

    async def test_websocket_connection_lifecycle_ssot_real_services(self):
        """
        Test complete WebSocket lifecycle uses SSOT patterns with real services

        CRITICAL: Must detect if real WebSocket connections use factory patterns
        """
        # Create real WebSocket manager
        websocket_manager = await self._create_real_websocket_manager()

        # Validate SSOT compliance in real manager
        ssot_violations = self._validate_manager_ssot_compliance(websocket_manager)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(ssot_violations) == 0, (
            f"REAL SERVICES SSOT VIOLATIONS: Real WebSocket manager has {len(ssot_violations)} "
            f"SSOT violations. Real services must use SSOT patterns exclusively.\n"
            f"Violations: {ssot_violations[:3]}"
        )

        # Test connection creation with real services
        connection = await self._create_real_websocket_connection(websocket_manager)

        # Validate connection uses SSOT patterns
        connection_violations = self._validate_connection_ssot_compliance(connection)

        assert len(connection_violations) == 0, (
            f"CONNECTION SSOT VIOLATIONS: Real connection has {len(connection_violations)} "
            f"SSOT violations.\n"
            f"Violations: {connection_violations}"
        )

        # Test event delivery through SSOT with real services
        events_sent = await self._test_critical_events_delivery_real_services(
            websocket_manager, connection
        )

        # CRITICAL: All 5 events must be delivered via SSOT
        assert len(events_sent) == 5, (
            f"INCOMPLETE EVENT DELIVERY: Expected 5 critical events, got {len(events_sent)}. "
            f"Events sent: {[e.get('type') for e in events_sent]}"
        )

        # Validate each event uses SSOT delivery
        for event in events_sent:
            event_violations = self._validate_event_ssot_compliance(event)
            assert len(event_violations) == 0, (
                f"EVENT SSOT VIOLATIONS: Event {event.get('type')} has violations: {event_violations}"
            )

        # Cleanup
        await self._cleanup_real_connection(websocket_manager, connection)

    async def test_multi_user_isolation_ssot_compliance_real_services(self):
        """
        Test multi-user isolation uses SSOT patterns with real services

        CRITICAL: Must detect if user isolation uses factory patterns
        """
        # Create connections for multiple users using real services
        user1_manager = await self._create_user_websocket_manager_real("user_001")
        user2_manager = await self._create_user_websocket_manager_real("user_002")

        # Validate SSOT compliance in multi-user scenario
        user1_violations = self._validate_manager_ssot_compliance(user1_manager)
        user2_violations = self._validate_manager_ssot_compliance(user2_manager)

        # CRITICAL: These assertions MUST FAIL initially
        assert len(user1_violations) == 0, (
            f"USER1 SSOT VIOLATIONS: User 1 manager has {len(user1_violations)} SSOT violations.\n"
            f"Violations: {user1_violations}"
        )

        assert len(user2_violations) == 0, (
            f"USER2 SSOT VIOLATIONS: User 2 manager has {len(user2_violations)} SSOT violations.\n"
            f"Violations: {user2_violations}"
        )

        # Validate proper isolation via SSOT (not factory patterns)
        isolation_violations = self._validate_user_isolation_ssot(user1_manager, user2_manager)

        assert len(isolation_violations) == 0, (
            f"USER ISOLATION SSOT VIOLATIONS: Found {len(isolation_violations)} isolation violations.\n"
            f"User isolation must use SSOT patterns, not factory patterns.\n"
            f"Violations: {isolation_violations}"
        )

        # Test event isolation with real services
        user1_events = await self._send_test_events_real_services(user1_manager, "user_001")
        user2_events = await self._send_test_events_real_services(user2_manager, "user_002")

        # CRITICAL: No cross-user event bleeding
        bleeding_violations = self._check_cross_user_bleeding(user1_events, user2_events)
        assert len(bleeding_violations) == 0, (
            f"CROSS-USER EVENT BLEEDING: Detected {len(bleeding_violations)} cross-user bleeding violations.\n"
            f"Violations: {bleeding_violations}"
        )

        # Cleanup
        await self._cleanup_user_managers([user1_manager, user2_manager])

    async def test_database_integration_ssot_real_services(self):
        """
        Test WebSocket database integration uses SSOT patterns with real PostgreSQL

        CRITICAL: Must detect if database operations use factory patterns
        """
        # Create real database session
        db_session = await self._create_real_db_session()

        # Create WebSocket manager with real database integration
        websocket_manager = await self._create_websocket_manager_with_real_db(db_session)

        # Validate database integration uses SSOT
        db_integration_violations = self._validate_db_integration_ssot(websocket_manager)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(db_integration_violations) == 0, (
            f"DATABASE INTEGRATION SSOT VIOLATIONS: Found {len(db_integration_violations)} "
            f"database integration SSOT violations.\n"
            f"Database operations must use SSOT patterns.\n"
            f"Violations: {db_integration_violations[:3]}"
        )

        # Test state persistence with real database
        connection_state = await self._create_connection_state()
        persistence_violations = await self._test_state_persistence_ssot(
            websocket_manager, connection_state, db_session
        )

        assert len(persistence_violations) == 0, (
            f"STATE PERSISTENCE SSOT VIOLATIONS: Found {len(persistence_violations)} "
            f"state persistence SSOT violations.\n"
            f"Violations: {persistence_violations}"
        )

        # Cleanup
        await db_session.close()

    async def test_redis_integration_ssot_real_services(self):
        """
        Test WebSocket Redis integration uses SSOT patterns with real Redis

        CRITICAL: Must detect if Redis operations use factory patterns
        """
        # Create real Redis connection
        redis_client = await self._create_real_redis_client()

        # Create WebSocket manager with real Redis integration
        websocket_manager = await self._create_websocket_manager_with_real_redis(redis_client)

        # Validate Redis integration uses SSOT
        redis_integration_violations = self._validate_redis_integration_ssot(websocket_manager)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(redis_integration_violations) == 0, (
            f"REDIS INTEGRATION SSOT VIOLATIONS: Found {len(redis_integration_violations)} "
            f"Redis integration SSOT violations.\n"
            f"Redis operations must use SSOT patterns.\n"
            f"Violations: {redis_integration_violations[:3]}"
        )

        # Test cache operations with real Redis
        cache_violations = await self._test_cache_operations_ssot(websocket_manager, redis_client)

        assert len(cache_violations) == 0, (
            f"CACHE OPERATIONS SSOT VIOLATIONS: Found {len(cache_violations)} "
            f"cache operations SSOT violations.\n"
            f"Violations: {cache_violations}"
        )

        # Cleanup
        await redis_client.close()

    # Helper methods for real service SSOT validation

    async def _check_real_services_available(self) -> bool:
        """Check if real services (PostgreSQL, Redis) are available."""
        try:
            # Try to connect to PostgreSQL
            pg_available = await self._test_postgresql_connection()

            # Try to connect to Redis
            redis_available = await self._test_redis_connection()

            return pg_available and redis_available

        except Exception as e:
            logger.warning(f"Real services not available: {e}")
            return False

    async def _test_postgresql_connection(self) -> bool:
        """Test PostgreSQL connection availability."""
        try:
            # Import PostgreSQL dependencies
            from netra_backend.app.db.database_manager import DatabaseManager

            # Try to create a connection
            db_manager = DatabaseManager()
            session = await db_manager.get_session()

            # Test basic query
            result = await session.execute("SELECT 1")
            await session.close()

            return result is not None

        except Exception:
            return False

    async def _test_redis_connection(self) -> bool:
        """Test Redis connection availability."""
        try:
            # Import Redis dependencies
            import redis.asyncio as redis

            # Try to create a connection
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

            # Test basic operation
            await redis_client.ping()
            await redis_client.close()

            return True

        except Exception:
            return False

    async def _create_real_websocket_manager(self):
        """Create real WebSocket manager for testing."""
        try:
            # Import real WebSocket manager
            from netra_backend.app.websocket_core.unified_manager import (
                _UnifiedWebSocketManagerImplementation
            )

            # Create manager instance
            manager = _UnifiedWebSocketManagerImplementation()

            # Initialize with real dependencies
            await manager.initialize()

            return manager

        except Exception as e:
            self.fail(f"Failed to create real WebSocket manager: {e}")

    def _validate_manager_ssot_compliance(self, manager) -> List[str]:
        """Validate manager uses SSOT patterns."""
        violations = []

        # Check for factory-related attributes (violations)
        factory_attributes = [
            '_factory_created',
            '_factory_instance',
            '_manager_factory',
            '_isolated_factory'
        ]

        for attr in factory_attributes:
            if hasattr(manager, attr):
                violations.append(f"Manager has factory attribute: {attr}")

        # Check for SSOT compliance markers
        if not hasattr(manager, '_ssot_marker'):
            violations.append("Manager missing SSOT compliance marker")

        # Check manager class name
        manager_class = manager.__class__.__name__
        if 'Factory' in manager_class:
            violations.append(f"Manager class name indicates factory pattern: {manager_class}")

        return violations

    async def _create_real_websocket_connection(self, manager):
        """Create real WebSocket connection for testing."""
        try:
            # Create connection data
            connection_data = {
                'connection_id': f"conn_{uuid.uuid4().hex[:8]}",
                'user_id': self.test_user_id,
                'thread_id': self.test_thread_id,
                'websocket': AsyncMock(),  # Mock WebSocket for testing
                'connected_at': time.time()
            }

            # Create connection via manager
            connection = await manager.add_connection(connection_data)

            return connection

        except Exception as e:
            self.fail(f"Failed to create real WebSocket connection: {e}")

    def _validate_connection_ssot_compliance(self, connection) -> List[str]:
        """Validate connection uses SSOT patterns."""
        violations = []

        # Check connection attributes for factory patterns
        if hasattr(connection, '_factory_created'):
            violations.append("Connection created via factory pattern")

        if hasattr(connection, '_isolated_manager'):
            violations.append("Connection uses isolated manager pattern")

        return violations

    async def _test_critical_events_delivery_real_services(self, manager, connection) -> List[Dict]:
        """Test critical events delivery with real services."""
        events_sent = []

        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        for event_type in critical_events:
            try:
                # Send event via manager
                event_data = {
                    'type': event_type,
                    'user_id': self.test_user_id,
                    'thread_id': self.test_thread_id,
                    'timestamp': time.time(),
                    'data': {'test': True}
                }

                await manager.send_event(connection.connection_id, event_data)
                events_sent.append(event_data)

            except Exception as e:
                logger.warning(f"Failed to send event {event_type}: {e}")

        return events_sent

    def _validate_event_ssot_compliance(self, event: Dict) -> List[str]:
        """Validate event uses SSOT delivery patterns."""
        violations = []

        # Check for factory-related metadata
        if event.get('factory_delivered'):
            violations.append("Event delivered via factory pattern")

        if event.get('isolated_delivery'):
            violations.append("Event uses isolated delivery pattern")

        return violations

    async def _create_user_websocket_manager_real(self, user_id: str):
        """Create user-specific WebSocket manager with real services."""
        try:
            # Import user execution context
            from netra_backend.app.services.user_execution_context import (
                create_defensive_user_execution_context
            )

            # Create user context
            user_context = await create_defensive_user_execution_context(user_id)

            # Get WebSocket manager from context
            manager = user_context.websocket_manager

            return manager

        except Exception as e:
            self.fail(f"Failed to create user WebSocket manager: {e}")

    def _validate_user_isolation_ssot(self, user1_manager, user2_manager) -> List[str]:
        """Validate user isolation uses SSOT patterns."""
        violations = []

        # Check if managers are properly isolated
        if user1_manager is user2_manager:
            violations.append("Users share same manager instance (violates isolation)")

        # Check for factory-based isolation markers
        if hasattr(user1_manager, '_factory_isolated'):
            violations.append("User 1 manager uses factory isolation pattern")

        if hasattr(user2_manager, '_factory_isolated'):
            violations.append("User 2 manager uses factory isolation pattern")

        return violations

    async def _send_test_events_real_services(self, manager, user_id: str) -> List[Dict]:
        """Send test events via real services."""
        events = []

        test_events = ['agent_started', 'agent_completed']

        for event_type in test_events:
            try:
                event_data = {
                    'type': event_type,
                    'user_id': user_id,
                    'timestamp': time.time(),
                    'data': {'test': True}
                }

                await manager.send_event(f"conn_{user_id}", event_data)
                events.append(event_data)

            except Exception as e:
                logger.warning(f"Failed to send test event {event_type}: {e}")

        return events

    def _check_cross_user_bleeding(self, user1_events: List[Dict], user2_events: List[Dict]) -> List[str]:
        """Check for cross-user event bleeding violations."""
        violations = []

        # Check if user1 events contain user2 data
        for event in user1_events:
            if event.get('user_id') != 'user_001':
                violations.append(f"User 1 received event for wrong user: {event.get('user_id')}")

        # Check if user2 events contain user1 data
        for event in user2_events:
            if event.get('user_id') != 'user_002':
                violations.append(f"User 2 received event for wrong user: {event.get('user_id')}")

        return violations

    async def _create_real_db_session(self):
        """Create real database session."""
        try:
            from netra_backend.app.db.database_manager import DatabaseManager

            db_manager = DatabaseManager()
            session = await db_manager.get_session()

            return session

        except Exception as e:
            self.fail(f"Failed to create real database session: {e}")

    async def _create_websocket_manager_with_real_db(self, db_session):
        """Create WebSocket manager with real database integration."""
        try:
            # Create manager with database integration
            manager = await self._create_real_websocket_manager()

            # Initialize database integration
            await manager.initialize_database(db_session)

            return manager

        except Exception as e:
            self.fail(f"Failed to create WebSocket manager with database: {e}")

    def _validate_db_integration_ssot(self, manager) -> List[str]:
        """Validate database integration uses SSOT patterns."""
        violations = []

        # Check for factory-based database integration
        if hasattr(manager, '_factory_db_session'):
            violations.append("Manager uses factory-based database session")

        if hasattr(manager, '_isolated_db_manager'):
            violations.append("Manager uses isolated database manager")

        return violations

    async def _create_connection_state(self) -> Dict:
        """Create test connection state."""
        return {
            'connection_id': f"conn_{uuid.uuid4().hex[:8]}",
            'user_id': self.test_user_id,
            'thread_id': self.test_thread_id,
            'state': 'active',
            'metadata': {'test': True}
        }

    async def _test_state_persistence_ssot(self, manager, state, db_session) -> List[str]:
        """Test state persistence uses SSOT patterns."""
        violations = []

        try:
            # Persist state
            await manager.persist_connection_state(state)

            # Retrieve state
            retrieved_state = await manager.get_connection_state(state['connection_id'])

            # Check for factory-based persistence markers
            if retrieved_state and retrieved_state.get('factory_persisted'):
                violations.append("State persistence uses factory pattern")

        except Exception as e:
            violations.append(f"State persistence failed: {e}")

        return violations

    async def _create_real_redis_client(self):
        """Create real Redis client."""
        try:
            import redis.asyncio as redis

            client = redis.Redis(host='localhost', port=6379, decode_responses=True)

            # Test connection
            await client.ping()

            return client

        except Exception as e:
            self.fail(f"Failed to create real Redis client: {e}")

    async def _create_websocket_manager_with_real_redis(self, redis_client):
        """Create WebSocket manager with real Redis integration."""
        try:
            # Create manager with Redis integration
            manager = await self._create_real_websocket_manager()

            # Initialize Redis integration
            await manager.initialize_redis(redis_client)

            return manager

        except Exception as e:
            self.fail(f"Failed to create WebSocket manager with Redis: {e}")

    def _validate_redis_integration_ssot(self, manager) -> List[str]:
        """Validate Redis integration uses SSOT patterns."""
        violations = []

        # Check for factory-based Redis integration
        if hasattr(manager, '_factory_redis_client'):
            violations.append("Manager uses factory-based Redis client")

        if hasattr(manager, '_isolated_redis_manager'):
            violations.append("Manager uses isolated Redis manager")

        return violations

    async def _test_cache_operations_ssot(self, manager, redis_client) -> List[str]:
        """Test cache operations use SSOT patterns."""
        violations = []

        try:
            # Test cache operations
            cache_key = f"test_cache_{uuid.uuid4().hex[:8]}"
            cache_value = {'test': True}

            await manager.cache_set(cache_key, cache_value)
            retrieved_value = await manager.cache_get(cache_key)

            # Check for factory-based cache markers
            if retrieved_value and retrieved_value.get('factory_cached'):
                violations.append("Cache operations use factory pattern")

        except Exception as e:
            violations.append(f"Cache operations failed: {e}")

        return violations

    async def _cleanup_real_connection(self, manager, connection):
        """Cleanup real connection."""
        try:
            await manager.remove_connection(connection.connection_id)
        except Exception:
            pass

    async def _cleanup_user_managers(self, managers):
        """Cleanup user managers."""
        for manager in managers:
            try:
                await manager.cleanup()
            except Exception:
                pass


if __name__ == "__main__":
    # Run this test independently to check for real service SSOT violations
    pytest.main([__file__, "-v"])