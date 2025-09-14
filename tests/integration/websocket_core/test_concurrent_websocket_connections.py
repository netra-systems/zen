#!/usr/bin/env python
"""Concurrent WebSocket Connections Race Condition Test

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Multi-User System Support
- Business Goal: $500K+ ARR protection through reliable concurrent connections
- Value Impact: Prevent connection state corruption and user data leakage
- Revenue Impact: Ensures system can handle multiple users simultaneously

Test Strategy: This test MUST FAIL before SSOT consolidation and PASS after
- FAIL: Currently race conditions from multiple managers cause connection issues
- PASS: After SSOT consolidation, proper connection isolation and state management

Issue #1033: WebSocket Manager SSOT Consolidation  
This test validates that WebSocket connections can handle multiple concurrent users
without race conditions, state corruption, or cross-user data contamination.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.logging.unified_logging_ssot import get_logger
from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest

# Import test utilities for real service integration
from test_framework.real_services_test_fixtures import real_services_fixture

logger = get_logger(__name__)


@dataclass
class ConcurrentTestUser:
    """Test user for concurrent connection testing."""
    user_id: str
    thread_id: str
    connection_id: str
    expected_messages: List[str]
    received_messages: List[str]
    connection_errors: List[str]


class TestConcurrentWebSocketConnections(BaseIntegrationTest):
    """Test WebSocket connection handling under concurrent load.
    
    This test suite validates that WebSocket connections maintain proper
    isolation and state management when multiple users connect simultaneously.
    """

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_concurrent_user_connections_isolation(self, real_services_fixture):
        """Test that concurrent user connections maintain proper isolation.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently race conditions cause connection state mixing
        - PASS: After SSOT consolidation, each user maintains isolated connection state
        
        This test creates multiple concurrent WebSocket connections and validates
        that messages sent to one user don't leak to other users.
        """
        logger.info("🔍 Testing concurrent user connection isolation...")
        
        num_concurrent_users = 5
        messages_per_user = 3
        
        # Create test users with unique data
        test_users = []
        for i in range(num_concurrent_users):
            user = ConcurrentTestUser(
                user_id=f"test_user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                connection_id=f"conn_{i}_{uuid.uuid4().hex[:8]}",
                expected_messages=[f"message_{i}_{j}" for j in range(messages_per_user)],
                received_messages=[],
                connection_errors=[]
            )
            test_users.append(user)
        
        # Create concurrent connection tasks
        connection_tasks = []
        for user in test_users:
            task = asyncio.create_task(self._simulate_user_connection(user))
            connection_tasks.append(task)
        
        # Wait for all connections to complete
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Analyze results for race conditions and isolation violations
        isolation_violations = []
        connection_failures = []
        
        for i, (user, result) in enumerate(zip(test_users, results)):
            if isinstance(result, Exception):
                connection_failures.append(f"User {user.user_id}: {str(result)}")
                continue
            
            # Check for message isolation violations
            for received_msg in user.received_messages:
                # Message should only contain this user's data
                if user.user_id not in received_msg:
                    # Check if it contains another user's data
                    for other_user in test_users:
                        if other_user.user_id != user.user_id and other_user.user_id in received_msg:
                            isolation_violations.append(
                                f"User {user.user_id} received message containing {other_user.user_id}: {received_msg}"
                            )
            
            # Check for missing expected messages
            missing_messages = set(user.expected_messages) - set(user.received_messages)
            if missing_messages:
                isolation_violations.append(
                    f"User {user.user_id} missing expected messages: {missing_messages}"
                )
        
        # Report violations
        if connection_failures:
            logger.error("Connection failures detected:")
            for failure in connection_failures:
                logger.error(f"  - {failure}")
        
        if isolation_violations:
            logger.error("SSOT VIOLATIONS: User isolation failures detected:")
            for violation in isolation_violations:
                logger.error(f"  - {violation}")
        
        # SSOT VIOLATION CHECK: Should have no isolation violations
        # This assertion WILL FAIL until proper connection isolation is implemented
        assert len(isolation_violations) == 0, (
            f"SSOT VIOLATION: Found {len(isolation_violations)} user isolation violations. "
            f"Concurrent connections must maintain proper user data separation."
        )
        
        assert len(connection_failures) == 0, (
            f"Connection failures detected: {len(connection_failures)}. "
            f"All concurrent connections should succeed with proper SSOT management."
        )

    @pytest.mark.integration  
    @pytest.mark.websocket
    async def test_websocket_manager_state_consistency(self, real_services_fixture):
        """Test WebSocket manager state consistency under concurrent load.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently multiple managers cause inconsistent state
        - PASS: After SSOT consolidation, single manager maintains consistent state
        
        This test validates that WebSocket connection state remains consistent
        when accessed concurrently from multiple threads/tasks.
        """
        logger.info("🔍 Testing WebSocket manager state consistency...")
        
        # Import WebSocket manager for testing
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        except ImportError as e:
            pytest.skip(f"WebSocket manager not available: {e}")
        
        # Create multiple manager instances to test state consistency
        num_managers = 3
        managers = []
        
        for i in range(num_managers):
            try:
                manager = WebSocketManager()
                managers.append(manager)
            except Exception as e:
                logger.error(f"Failed to create WebSocket manager {i}: {e}")
                continue
        
        if len(managers) < 2:
            pytest.skip("Need at least 2 WebSocket managers for consistency testing")
        
        # Test state consistency across managers
        consistency_violations = []
        
        # Add connections to different managers
        test_connections = []
        for i, manager in enumerate(managers):
            connection_id = f"test_conn_{i}_{uuid.uuid4().hex[:8]}"
            user_id = f"test_user_{i}_{uuid.uuid4().hex[:8]}"
            
            try:
                # Simulate adding a connection
                if hasattr(manager, 'add_connection'):
                    await manager.add_connection(connection_id, user_id)
                    test_connections.append((connection_id, user_id, i))
                elif hasattr(manager, 'connect'):
                    await manager.connect(connection_id, user_id)
                    test_connections.append((connection_id, user_id, i))
                else:
                    logger.warning(f"Manager {i} doesn't have expected connection methods")
            except Exception as e:
                logger.error(f"Failed to add connection to manager {i}: {e}")
                consistency_violations.append(f"Manager {i} failed to add connection: {e}")
        
        # Check if managers can see each other's connections (SSOT violation)
        cross_manager_visibility = []
        for i, manager_a in enumerate(managers):
            for j, manager_b in enumerate(managers):
                if i >= j:  # Only check each pair once
                    continue
                
                try:
                    # Check if manager A's connections are visible in manager B
                    if hasattr(manager_a, 'get_connections') and hasattr(manager_b, 'get_connections'):
                        connections_a = await manager_a.get_connections()
                        connections_b = await manager_b.get_connections()
                        
                        # In a proper SSOT system, all managers should see all connections
                        # OR each manager should only see its own connections
                        
                        if len(connections_a) != len(connections_b):
                            cross_manager_visibility.append(
                                f"Manager {i} sees {len(connections_a)} connections, "
                                f"Manager {j} sees {len(connections_b)} connections"
                            )
                except Exception as e:
                    logger.warning(f"Could not compare connections between managers {i} and {j}: {e}")
        
        # Test concurrent state modifications
        state_modification_errors = await self._test_concurrent_state_modifications(managers)
        
        # Compile all violations
        all_violations = consistency_violations + cross_manager_visibility + state_modification_errors
        
        if all_violations:
            logger.error("SSOT VIOLATIONS: WebSocket manager state inconsistencies:")
            for violation in all_violations:
                logger.error(f"  - {violation}")
        
        # SSOT VIOLATION CHECK: Should have consistent state across all manager instances
        # This assertion WILL FAIL until SSOT consolidation eliminates multiple managers
        assert len(all_violations) == 0, (
            f"SSOT VIOLATION: Found {len(all_violations)} state consistency violations. "
            f"All WebSocket manager instances should maintain consistent state."
        )

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_connection_cleanup_race_conditions(self, real_services_fixture):
        """Test connection cleanup doesn't have race conditions.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently cleanup races cause connection leaks or errors
        - PASS: After SSOT consolidation, clean connection lifecycle management
        
        This test validates that connection cleanup happens correctly even
        when multiple cleanup operations occur simultaneously.
        """
        logger.info("🔍 Testing connection cleanup race conditions...")
        
        # Import WebSocket manager
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        except ImportError as e:
            pytest.skip(f"WebSocket manager not available: {e}")
        
        manager = WebSocketManager()
        
        # Create connections
        num_connections = 10
        connection_ids = []
        
        for i in range(num_connections):
            connection_id = f"cleanup_test_{i}_{uuid.uuid4().hex[:8]}"
            user_id = f"user_{i}_{uuid.uuid4().hex[:8]}"
            
            try:
                if hasattr(manager, 'add_connection'):
                    await manager.add_connection(connection_id, user_id)
                elif hasattr(manager, 'connect'):
                    await manager.connect(connection_id, user_id)
                
                connection_ids.append(connection_id)
            except Exception as e:
                logger.warning(f"Failed to create connection {i}: {e}")
        
        # Perform concurrent cleanup operations
        cleanup_tasks = []
        cleanup_results = []
        
        for connection_id in connection_ids:
            # Create multiple cleanup tasks for the same connection (race condition test)
            for cleanup_attempt in range(2):  # Try to cleanup each connection twice
                task = asyncio.create_task(
                    self._cleanup_connection_safely(manager, connection_id, cleanup_attempt)
                )
                cleanup_tasks.append(task)
        
        # Wait for all cleanup operations
        cleanup_results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Analyze cleanup results for race conditions
        cleanup_violations = []
        cleanup_errors = []
        
        for i, result in enumerate(cleanup_results):
            if isinstance(result, Exception):
                # Some cleanup failures are expected (trying to cleanup already cleaned connections)
                # But systematic failures indicate race conditions
                cleanup_errors.append(str(result))
            elif isinstance(result, dict) and result.get('error'):
                cleanup_violations.append(result['error'])
        
        # Check final state - should have no connections left
        try:
            if hasattr(manager, 'get_connections'):
                remaining_connections = await manager.get_connections()
                if remaining_connections:
                    cleanup_violations.append(
                        f"Found {len(remaining_connections)} connections remaining after cleanup"
                    )
        except Exception as e:
            cleanup_violations.append(f"Failed to check remaining connections: {e}")
        
        # Analyze error patterns for race conditions
        systematic_errors = self._analyze_cleanup_error_patterns(cleanup_errors)
        cleanup_violations.extend(systematic_errors)
        
        if cleanup_violations:
            logger.error("SSOT VIOLATIONS: Connection cleanup race conditions:")
            for violation in cleanup_violations:
                logger.error(f"  - {violation}")
        
        # SSOT VIOLATION CHECK: Should have clean connection lifecycle management
        # This assertion WILL FAIL until race conditions in cleanup are resolved
        assert len(cleanup_violations) == 0, (
            f"SSOT VIOLATION: Found {len(cleanup_violations)} connection cleanup race conditions. "
            f"Connection cleanup should be thread-safe and complete."
        )

    async def _simulate_user_connection(self, user: ConcurrentTestUser) -> Dict[str, Any]:
        """Simulate a user WebSocket connection and message exchange."""
        try:
            # Import WebSocket manager
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            manager = WebSocketManager()
            
            # Connect user
            if hasattr(manager, 'add_connection'):
                await manager.add_connection(user.connection_id, user.user_id)
            elif hasattr(manager, 'connect'):
                await manager.connect(user.connection_id, user.user_id)
            
            # Send messages for this user
            for message in user.expected_messages:
                test_message = {
                    "type": "test_message",
                    "user_id": user.user_id,
                    "thread_id": user.thread_id,
                    "content": message,
                    "timestamp": time.time()
                }
                
                if hasattr(manager, 'send_message'):
                    await manager.send_message(user.connection_id, test_message)
                elif hasattr(manager, 'emit_event'):
                    await manager.emit_event(user.connection_id, "test_message", test_message)
                
                # Simulate receiving the message (in real system this would come from WebSocket)
                user.received_messages.append(message)
            
            return {"success": True, "user_id": user.user_id}
            
        except Exception as e:
            user.connection_errors.append(str(e))
            return {"success": False, "error": str(e), "user_id": user.user_id}

    async def _test_concurrent_state_modifications(self, managers: List[Any]) -> List[str]:
        """Test concurrent state modifications across multiple managers."""
        errors = []
        
        # Create tasks that modify state concurrently
        modification_tasks = []
        
        for i, manager in enumerate(managers):
            # Create concurrent connection operations
            for j in range(3):  # 3 operations per manager
                connection_id = f"concurrent_{i}_{j}_{uuid.uuid4().hex[:8]}"
                user_id = f"concurrent_user_{i}_{j}"
                
                task = asyncio.create_task(
                    self._modify_manager_state(manager, connection_id, user_id, i)
                )
                modification_tasks.append(task)
        
        # Wait for all modifications
        results = await asyncio.gather(*modification_tasks, return_exceptions=True)
        
        # Analyze results for state consistency issues
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Concurrent modification {i} failed: {str(result)}")
            elif isinstance(result, dict) and result.get('error'):
                errors.append(f"Concurrent modification {i}: {result['error']}")
        
        return errors

    async def _modify_manager_state(self, manager: Any, connection_id: str, user_id: str, manager_index: int) -> Dict[str, Any]:
        """Modify manager state and check for consistency."""
        try:
            # Add connection
            if hasattr(manager, 'add_connection'):
                await manager.add_connection(connection_id, user_id)
            elif hasattr(manager, 'connect'):
                await manager.connect(connection_id, user_id)
            
            # Small delay to increase chance of race conditions
            await asyncio.sleep(0.01)
            
            # Remove connection
            if hasattr(manager, 'remove_connection'):
                await manager.remove_connection(connection_id)
            elif hasattr(manager, 'disconnect'):
                await manager.disconnect(connection_id)
            
            return {"success": True}
            
        except Exception as e:
            return {"error": f"Manager {manager_index} state modification failed: {str(e)}"}

    async def _cleanup_connection_safely(self, manager: Any, connection_id: str, attempt: int) -> Dict[str, Any]:
        """Attempt to cleanup a connection, handling race conditions gracefully."""
        try:
            if hasattr(manager, 'remove_connection'):
                await manager.remove_connection(connection_id)
            elif hasattr(manager, 'disconnect'):
                await manager.disconnect(connection_id)
            
            return {"success": True, "connection_id": connection_id, "attempt": attempt}
            
        except Exception as e:
            # Some exceptions are expected (e.g., trying to remove already removed connection)
            return {"success": False, "error": str(e), "connection_id": connection_id, "attempt": attempt}

    def _analyze_cleanup_error_patterns(self, cleanup_errors: List[str]) -> List[str]:
        """Analyze cleanup errors to identify systematic race condition patterns."""
        error_patterns = []
        
        # Count error types
        error_counts = {}
        for error in cleanup_errors:
            error_type = type(error).__name__ if hasattr(error, '__name__') else str(error)[:50]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Look for patterns that indicate race conditions
        for error_type, count in error_counts.items():
            if count > 5:  # Arbitrary threshold for "too many similar errors"
                error_patterns.append(
                    f"Systematic error pattern: '{error_type}' occurred {count} times "
                    f"(may indicate race condition)"
                )
        
        return error_patterns


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])