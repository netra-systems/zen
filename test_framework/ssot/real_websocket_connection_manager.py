"""
SSOT Real WebSocket Connection Manager

This module provides centralized management of multiple real WebSocket connections
for concurrent multi-user testing with strict isolation validation.

CRITICAL: Per CLAUDE.md requirements
- NO MOCKS - only real WebSocket connections
- ALL e2e tests MUST use authentication
- Tests MUST fail hard when isolation is violated
- Multi-user isolation is CRITICAL for security

Business Value Justification:
- Segment: Platform/Internal - Multi-user chat infrastructure security
- Business Goal: Ensure user data isolation in multi-tenant environment
- Value Impact: Protects user privacy and prevents data leaks
- Revenue Impact: Prevents security breaches that could destroy customer trust

@compliance CLAUDE.md - Multi-user system, security violations = abomination
@compliance SPEC/core.xml - Real services testing, user isolation validation
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union, Callable, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

from test_framework.ssot.real_websocket_test_client import (
    RealWebSocketTestClient,
    WebSocketEvent,
    SecurityError,
    WebSocketConnectionState
)
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser

logger = logging.getLogger(__name__)


class DockerUnavailableError(Exception):
    """Exception raised when Docker services are unavailable."""
    pass


class IsolationTestType(Enum):
    """Types of isolation tests to perform."""
    USER_DATA_ISOLATION = "user_data_isolation"
    EVENT_ISOLATION = "event_isolation"
    AUTHENTICATION_ISOLATION = "authentication_isolation"
    CONCURRENT_SESSION_ISOLATION = "concurrent_session_isolation"


@dataclass
class ConnectionProfile:
    """Profile for a managed WebSocket connection."""
    connection_id: str
    user_id: str
    user_email: str
    client: RealWebSocketTestClient
    authenticated_user: AuthenticatedUser
    created_at: float
    isolation_violations: List[str] = field(default_factory=list)
    events_received: List[WebSocketEvent] = field(default_factory=list)
    
    def record_violation(self, violation: str):
        """Record an isolation violation."""
        self.isolation_violations.append(f"{time.time()}: {violation}")


@dataclass
class PooledConnection:
    """A connection in the connection pool."""
    client: RealWebSocketTestClient
    user_id: str
    last_used: float
    created_at: float
    usage_count: int = 0
    is_active: bool = True


@dataclass
class IsolationTestResult:
    """Results from isolation testing."""
    test_type: IsolationTestType
    test_passed: bool
    connections_tested: int
    total_violations: int
    violation_details: List[str]
    test_duration: float
    events_validated: int
    error_message: Optional[str] = None


class RealWebSocketConnectionManager:
    """
    SSOT Manager for Multiple Real WebSocket Connections.
    
    This manager coordinates multiple authenticated WebSocket connections
    to validate multi-user isolation and prevent cross-user data leaks.
    
    CRITICAL SECURITY FEATURES:
    - Strict user isolation validation
    - Cross-user event leak detection  
    - Authentication boundary enforcement
    - Concurrent session management
    - Fail-hard security validation
    
    The manager will FAIL TESTS IMMEDIATELY when:
    - Events leak between users
    - Authentication boundaries are crossed
    - User data is mixed between sessions
    - Isolation violations are detected
    """
    
    def __init__(
        self,
        backend_url: str = "ws://localhost:8000",
        environment: str = "test",
        max_connections: int = 50,
        connection_timeout: float = 10.0
    ):
        """Initialize the connection manager.
        
        Args:
            backend_url: WebSocket URL for backend service
            environment: Test environment ('test', 'staging', etc.)
            max_connections: Maximum concurrent connections allowed
            connection_timeout: Timeout for individual connections
        """
        self.backend_url = backend_url
        self.environment = environment
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        
        # Connection management
        self.connections: Dict[str, ConnectionProfile] = {}
        self.connection_by_user: Dict[str, str] = {}  # user_id -> connection_id
        self.active_connections: Set[str] = set()
        
        # Connection pool for optimization
        self.connection_pool: Dict[str, PooledConnection] = {}  # user_id -> pooled connection
        self.pool_enabled = True
        self.pool_max_age_seconds = 300.0  # 5 minutes
        self.pool_max_idle_seconds = 60.0  # 1 minute
        
        # Auth helper
        self.auth_helper = E2EAuthHelper(environment=environment)
        
        # Test state
        self.manager_id = f"ws_mgr_{uuid.uuid4().hex[:8]}"
        self.test_start_time: Optional[float] = None
        self.global_violations: List[str] = []
        
        logger.info(f"Initialized RealWebSocketConnectionManager: {self.manager_id}")
    
    async def create_authenticated_connection(
        self,
        user_email: Optional[str] = None,
        user_id: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        connect_immediately: bool = True,
        endpoint: str = "/ws"
    ) -> str:
        """Create an authenticated WebSocket connection.
        
        Args:
            user_email: User email (auto-generated if not provided)
            user_id: User ID (auto-generated if not provided)
            permissions: User permissions (defaults to ["read", "write"])
            connect_immediately: Whether to establish WebSocket connection immediately
            endpoint: WebSocket endpoint to connect to
            
        Returns:
            Connection ID for the created connection
            
        Raises:
            RuntimeError: If connection creation fails
            ValueError: If max connections exceeded
        """
        if len(self.connections) >= self.max_connections:
            raise ValueError(f"Maximum connections ({self.max_connections}) exceeded")
        
        # Clean up expired pooled connections
        self._cleanup_pool()
        
        # Try to get from pool first if we have a specific user_id
        client = None
        authenticated_user = None
        
        # If we have user_id, try to reuse from pool
        if user_id:
            pooled_client = self._get_pooled_connection(user_id)
            if pooled_client:
                logger.info(f"♻️ Reusing pooled connection for user: {user_id}")
                client = pooled_client
                authenticated_user = client.authenticated_user
        
        # Create new client if no pooled connection available
        if not client:
            client = RealWebSocketTestClient(
                backend_url=self.backend_url,
                environment=self.environment,
                connection_timeout=self.connection_timeout,
                auth_required=True
            )
            
            # Authenticate user
            authenticated_user = await client.authenticate_user(
                user_email=user_email,
                user_id=user_id,
                permissions=permissions
            )
            
            # Add to pool for future reuse
            self._add_to_pool(authenticated_user.user_id, client)
        
        try:
            
            # Create connection profile
            connection_id = client.connection_id
            profile = ConnectionProfile(
                connection_id=connection_id,
                user_id=authenticated_user.user_id,
                user_email=authenticated_user.email,
                client=client,
                authenticated_user=authenticated_user,
                created_at=time.time()
            )
            
            # Store connection
            self.connections[connection_id] = profile
            self.connection_by_user[authenticated_user.user_id] = connection_id
            
            # Connect immediately if requested
            if connect_immediately:
                await client.connect(endpoint=endpoint)
                self.active_connections.add(connection_id)
            
            logger.info(
                f"Created authenticated connection: {connection_id} "
                f"for user: {authenticated_user.user_id}"
            )
            
            return connection_id
            
        except Exception as e:
            error_msg = f"Failed to create authenticated connection: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def create_multiple_connections(
        self,
        count: int,
        connect_all: bool = True,
        endpoint: str = "/ws"
    ) -> List[str]:
        """Create multiple authenticated WebSocket connections.
        
        Args:
            count: Number of connections to create
            connect_all: Whether to connect all immediately
            endpoint: WebSocket endpoint for connections
            
        Returns:
            List of connection IDs created
        """
        if count > self.max_connections:
            raise ValueError(f"Requested {count} connections exceeds max {self.max_connections}")
        
        connection_ids = []
        tasks = []
        
        # Create connections concurrently
        for i in range(count):
            task = asyncio.create_task(
                self.create_authenticated_connection(
                    user_email=f"test_user_{i}_{uuid.uuid4().hex[:8]}@example.com",
                    connect_immediately=connect_all,
                    endpoint=endpoint
                )
            )
            tasks.append(task)
        
        # Wait for all connections to be created
        try:
            results = await asyncio.gather(*tasks)
            connection_ids.extend(results)
            
            logger.info(f"Created {len(connection_ids)} connections successfully")
            return connection_ids
            
        except Exception as e:
            logger.error(f"Failed to create multiple connections: {e}")
            # Cleanup any partial connections
            await self.cleanup_all_connections()
            raise
    
    def get_connection(self, connection_id: str) -> Optional[RealWebSocketTestClient]:
        """Get WebSocket client by connection ID.
        
        Args:
            connection_id: Connection ID to retrieve
            
        Returns:
            WebSocket client or None if not found
        """
        profile = self.connections.get(connection_id)
        return profile.client if profile else None
    
    def get_connection_by_user(self, user_id: str) -> Optional[RealWebSocketTestClient]:
        """Get WebSocket client by user ID.
        
        Args:
            user_id: User ID to look up
            
        Returns:
            WebSocket client or None if not found
        """
        connection_id = self.connection_by_user.get(user_id)
        if connection_id:
            return self.get_connection(connection_id)
        return None
    
    def get_all_connections(self) -> List[RealWebSocketTestClient]:
        """Get all managed WebSocket clients.
        
        Returns:
            List of all WebSocket clients
        """
        return [profile.client for profile in self.connections.values()]
    
    async def send_event_to_all(
        self,
        event_type: str,
        data: Dict[str, Any],
        exclude_connections: Optional[Set[str]] = None
    ) -> Dict[str, bool]:
        """Send an event to all connections.
        
        Args:
            event_type: Type of event to send
            data: Event data
            exclude_connections: Connection IDs to exclude
            
        Returns:
            Dict mapping connection_id -> success boolean
        """
        exclude_connections = exclude_connections or set()
        results = {}
        tasks = []
        
        for connection_id, profile in self.connections.items():
            if connection_id not in exclude_connections:
                task = asyncio.create_task(
                    self._send_event_safe(profile.client, event_type, data)
                )
                tasks.append((connection_id, task))
        
        # Wait for all sends to complete
        completed_tasks = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )
        
        for i, (connection_id, _) in enumerate(tasks):
            result = completed_tasks[i]
            results[connection_id] = not isinstance(result, Exception)
            
            if isinstance(result, Exception):
                logger.error(f"Failed to send event to {connection_id}: {result}")
        
        return results
    
    async def _send_event_safe(
        self,
        client: RealWebSocketTestClient,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Safely send event to client with error handling."""
        try:
            await client.send_event(event_type, data)
        except Exception as e:
            logger.error(f"Error sending event to {client.connection_id}: {e}")
            raise
    
    async def wait_for_events_from_all(
        self,
        event_types: Set[str],
        timeout: float = 30.0,
        require_all_connections: bool = True
    ) -> Dict[str, List[WebSocketEvent]]:
        """Wait for events from all connections.
        
        Args:
            event_types: Event types to wait for
            timeout: Total timeout for all connections
            require_all_connections: Whether all connections must receive events
            
        Returns:
            Dict mapping connection_id -> list of events received
            
        Raises:
            RuntimeError: If require_all_connections=True and some fail
        """
        results = {}
        tasks = []
        
        # Create tasks for each connection
        for connection_id, profile in self.connections.items():
            if connection_id in self.active_connections:
                task = asyncio.create_task(
                    profile.client.wait_for_events(
                        event_types=event_types,
                        timeout=timeout
                    )
                )
                tasks.append((connection_id, task))
        
        # Wait for all tasks to complete
        completed_tasks = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )
        
        failed_connections = []
        for i, (connection_id, _) in enumerate(tasks):
            result = completed_tasks[i]
            
            if isinstance(result, Exception):
                logger.error(f"Connection {connection_id} failed to receive events: {result}")
                results[connection_id] = []
                failed_connections.append(connection_id)
            else:
                results[connection_id] = result
                # Store events in profile for violation checking
                profile = self.connections[connection_id]
                profile.events_received.extend(result)
        
        if require_all_connections and failed_connections:
            raise RuntimeError(
                f"Failed to receive events from connections: {failed_connections}"
            )
        
        return results
    
    async def test_user_isolation(
        self,
        test_type: IsolationTestType = IsolationTestType.EVENT_ISOLATION
    ) -> IsolationTestResult:
        """Test user isolation between connections.
        
        CRITICAL: This test MUST detect cross-user data leaks.
        
        Args:
            test_type: Type of isolation test to perform
            
        Returns:
            IsolationTestResult with detailed violation information
            
        Raises:
            SecurityError: If critical isolation violations are detected
        """
        start_time = time.time()
        violations = []
        events_validated = 0
        
        logger.info(f"Starting {test_type.value} test with {len(self.connections)} connections")
        
        try:
            if test_type == IsolationTestType.EVENT_ISOLATION:
                violations, events_validated = await self._test_event_isolation()
            elif test_type == IsolationTestType.USER_DATA_ISOLATION:
                violations, events_validated = await self._test_user_data_isolation()
            elif test_type == IsolationTestType.AUTHENTICATION_ISOLATION:
                violations, events_validated = await self._test_authentication_isolation()
            elif test_type == IsolationTestType.CONCURRENT_SESSION_ISOLATION:
                violations, events_validated = await self._test_concurrent_session_isolation()
            
            test_duration = time.time() - start_time
            test_passed = len(violations) == 0
            
            result = IsolationTestResult(
                test_type=test_type,
                test_passed=test_passed,
                connections_tested=len(self.connections),
                total_violations=len(violations),
                violation_details=violations,
                test_duration=test_duration,
                events_validated=events_validated
            )
            
            if not test_passed:
                # Record global violations
                self.global_violations.extend(violations)
                
                error_msg = (
                    f"ISOLATION TEST FAILED: {test_type.value} "
                    f"detected {len(violations)} violations"
                )
                logger.error(error_msg)
                
                # FAIL HARD - this is a critical security issue
                raise SecurityError(error_msg)
            
            logger.info(f"Isolation test PASSED: {test_type.value}")
            return result
            
        except SecurityError:
            raise  # Re-raise security errors
        except Exception as e:
            test_duration = time.time() - start_time
            error_msg = f"Isolation test failed with error: {e}"
            
            return IsolationTestResult(
                test_type=test_type,
                test_passed=False,
                connections_tested=len(self.connections),
                total_violations=0,
                violation_details=[],
                test_duration=test_duration,
                events_validated=events_validated,
                error_message=error_msg
            )
    
    async def _test_event_isolation(self) -> Tuple[List[str], int]:
        """Test that events don't leak between users."""
        violations = []
        events_validated = 0
        
        # Send unique events from each connection
        sent_events = {}
        for connection_id, profile in self.connections.items():
            if connection_id in self.active_connections:
                unique_event = f"isolation_test_{connection_id}_{uuid.uuid4().hex[:8]}"
                await profile.client.send_event(
                    event_type="test_isolation",
                    data={
                        "unique_id": unique_event,
                        "sender": connection_id,
                        "test_type": "event_isolation"
                    }
                )
                sent_events[connection_id] = unique_event
        
        # Wait for events and validate isolation
        await asyncio.sleep(2.0)  # Allow events to propagate
        
        for connection_id, profile in self.connections.items():
            if connection_id in self.active_connections:
                try:
                    # Check recent events for cross-user leaks
                    for event in profile.events_received[-10:]:  # Check last 10 events
                        events_validated += 1
                        
                        # Check if event is from another user
                        event_sender = event.data.get('sender')
                        if event_sender and event_sender != connection_id:
                            violation = (
                                f"Connection {connection_id} (user: {profile.user_id}) "
                                f"received event from connection {event_sender}. "
                                f"Event type: {event.event_type}"
                            )
                            violations.append(violation)
                            profile.record_violation(violation)
                
                except Exception as e:
                    logger.error(f"Error validating events for {connection_id}: {e}")
        
        return violations, events_validated
    
    async def _test_user_data_isolation(self) -> Tuple[List[str], int]:
        """Test that user data doesn't leak between connections."""
        violations = []
        events_validated = 0
        
        # Send user-specific data from each connection
        for connection_id, profile in self.connections.items():
            if connection_id in self.active_connections:
                await profile.client.send_event(
                    event_type="user_data_test",
                    data={
                        "user_id": profile.user_id,
                        "user_email": profile.user_email,
                        "private_data": f"secret_for_{profile.user_id}",
                        "connection_id": connection_id
                    }
                )
        
        # Wait and validate no cross-user data
        await asyncio.sleep(1.5)
        
        for connection_id, profile in self.connections.items():
            if connection_id in self.active_connections:
                for event in profile.events_received:
                    events_validated += 1
                    
                    # Check for other users' data
                    event_user_id = event.data.get('user_id')
                    if event_user_id and event_user_id != profile.user_id:
                        violation = (
                            f"Connection {connection_id} (user: {profile.user_id}) "
                            f"received data for user: {event_user_id}"
                        )
                        violations.append(violation)
                        profile.record_violation(violation)
        
        return violations, events_validated
    
    async def _test_authentication_isolation(self) -> Tuple[List[str], int]:
        """Test that authentication contexts are isolated."""
        violations = []
        events_validated = 0
        
        # Each connection should only see its own auth context
        for connection_id, profile in self.connections.items():
            if connection_id in self.active_connections:
                # Validate JWT token isolation
                token = profile.authenticated_user.jwt_token
                expected_user = profile.user_id
                
                # Check if client has correct user context
                if profile.client.expected_user_id != expected_user:
                    violation = (
                        f"Connection {connection_id} has incorrect user context. "
                        f"Expected: {expected_user}, Got: {profile.client.expected_user_id}"
                    )
                    violations.append(violation)
                    profile.record_violation(violation)
                
                events_validated += 1
        
        return violations, events_validated
    
    async def _test_concurrent_session_isolation(self) -> Tuple[List[str], int]:
        """Test isolation under concurrent operations."""
        violations = []
        events_validated = 0
        
        # Perform concurrent operations
        tasks = []
        for connection_id, profile in self.connections.items():
            if connection_id in self.active_connections:
                task = asyncio.create_task(
                    self._concurrent_operation(profile, connection_id)
                )
                tasks.append((connection_id, task))
        
        # Wait for all operations
        results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )
        
        # Check for violations in concurrent operations
        for i, (connection_id, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, dict) and 'violations' in result:
                violations.extend(result['violations'])
                events_validated += result.get('events_checked', 0)
        
        return violations, events_validated
    
    async def _concurrent_operation(
        self,
        profile: ConnectionProfile,
        connection_id: str
    ) -> Dict[str, Any]:
        """Perform concurrent operation for isolation testing."""
        violations = []
        events_checked = 0
        
        try:
            # Send multiple events rapidly
            for i in range(5):
                await profile.client.send_event(
                    event_type="concurrent_test",
                    data={
                        "sequence": i,
                        "user_id": profile.user_id,
                        "timestamp": time.time()
                    }
                )
                await asyncio.sleep(0.1)  # Small delay between events
            
            # Check for cross-contamination
            await asyncio.sleep(1.0)
            
            for event in profile.events_received[-10:]:
                events_checked += 1
                if event.user_id and event.user_id != profile.user_id:
                    violations.append(
                        f"Concurrent operation contamination in {connection_id}: "
                        f"event from user {event.user_id}"
                    )
        
        except Exception as e:
            violations.append(f"Concurrent operation error in {connection_id}: {e}")
        
        return {
            'violations': violations,
            'events_checked': events_checked
        }
    
    async def cleanup_connection(self, connection_id: str) -> None:
        """Cleanup a specific connection.
        
        Args:
            connection_id: Connection ID to cleanup
        """
        profile = self.connections.get(connection_id)
        if profile:
            try:
                await profile.client.close()
            except Exception as e:
                logger.warning(f"Error closing connection {connection_id}: {e}")
            
            # Remove from tracking
            self.connections.pop(connection_id, None)
            self.active_connections.discard(connection_id)
            if profile.user_id in self.connection_by_user:
                del self.connection_by_user[profile.user_id]
            
            logger.info(f"Cleaned up connection: {connection_id}")
    
    async def cleanup_all_connections(self) -> None:
        """Cleanup all managed connections."""
        logger.info(f"Cleaning up {len(self.connections)} connections")
        
        cleanup_tasks = []
        for connection_id in list(self.connections.keys()):
            task = asyncio.create_task(self.cleanup_connection(connection_id))
            cleanup_tasks.append(task)
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Clear all tracking
        self.connections.clear()
        self.connection_by_user.clear()
        self.active_connections.clear()
        
        logger.info("All connections cleaned up")
    
    def get_isolation_summary(self) -> Dict[str, Any]:
        """Get summary of isolation violations across all connections.
        
        Returns:
            Summary of isolation violations and connection status
        """
        total_violations = len(self.global_violations)
        connection_violations = {}
        
        for connection_id, profile in self.connections.items():
            if profile.isolation_violations:
                connection_violations[connection_id] = {
                    'user_id': profile.user_id,
                    'violations': len(profile.isolation_violations),
                    'details': profile.isolation_violations
                }
        
        return {
            'manager_id': self.manager_id,
            'total_connections': len(self.connections),
            'active_connections': len(self.active_connections),
            'global_violations': total_violations,
            'connection_violations': connection_violations,
            'test_passed': total_violations == 0,
            'environment': self.environment,
            'backend_url': self.backend_url
        }
    
    def assert_no_violations(self) -> None:
        """Assert that no isolation violations occurred.
        
        Raises:
            AssertionError: If any violations were detected
        """
        summary = self.get_isolation_summary()
        if not summary['test_passed']:
            raise AssertionError(
                f"ISOLATION VIOLATIONS DETECTED:\n"
                f"Total violations: {summary['global_violations']}\n"
                f"Affected connections: {len(summary['connection_violations'])}\n"
                f"Details: {summary['connection_violations']}"
            )
    
    @asynccontextmanager
    async def managed_connections(
        self,
        count: int,
        connect_all: bool = True,
        endpoint: str = "/ws"
    ):
        """Context manager for managed WebSocket connections.
        
        Args:
            count: Number of connections to create and manage
            connect_all: Whether to connect all immediately
            endpoint: WebSocket endpoint for connections
            
        Yields:
            List of connection IDs for the managed connections
        """
        connection_ids = []
        try:
            self.test_start_time = time.time()
            connection_ids = await self.create_multiple_connections(
                count=count,
                connect_all=connect_all,
                endpoint=endpoint
            )
            
            logger.info(f"Managing {len(connection_ids)} WebSocket connections")
            yield connection_ids
            
        finally:
            await self.cleanup_all_connections()
            logger.info("Managed connections context completed")
    
    async def test_with_graceful_degradation(self, test_function: Callable, test_name: str = "WebSocket test"):
        """Test with graceful degradation for service unavailability.
        
        This method attempts to run real WebSocket tests, but gracefully handles
        scenarios where Docker services are unavailable, providing clear feedback
        about what couldn't be tested.
        
        Args:
            test_function: Async function to execute that requires WebSocket services
            test_name: Name of the test for logging purposes
            
        Returns:
            Test result or raises pytest.skip with appropriate message
            
        Raises:
            pytest.skip: When services are unavailable (graceful degradation)
            Other exceptions: When tests fail for reasons other than service availability
        """
        import pytest
        
        try:
            logger.info(f"🧪 Starting {test_name} with real WebSocket services")
            
            # Test basic connectivity first
            await self._verify_service_availability()
            
            # Execute the actual test
            result = await test_function()
            
            logger.info(f"✅ {test_name} completed successfully with real services")
            return result
            
        except (ConnectionRefusedError, OSError) as e:
            # Network-level issues - services likely not running
            logger.warning(f"⚠️ Network connectivity failed for {test_name}: {e}")
            pytest.skip(
                f"Docker services unavailable - {test_name} skipped. "
                f"Start services with: python tests/unified_test_runner.py --real-services"
            )
        
        except DockerUnavailableError as e:
            # Docker-specific unavailability
            logger.warning(f"⚠️ Docker services unavailable for {test_name}: {e}")
            pytest.skip(
                f"Docker services unavailable - {test_name} skipped. "
                f"Ensure Docker is running and services are started."
            )
        
        except Exception as e:
            # Other errors should not be gracefully degraded - they indicate real test failures
            logger.error(f"❌ {test_name} failed with real services: {e}")
            raise
    
    async def _verify_service_availability(self) -> None:
        """Verify that required services are available.
        
        Raises:
            DockerUnavailableError: If required services are not available
        """
        try:
            # Test basic connectivity to backend service
            import socket
            
            # Parse backend URL to get host and port
            backend_url_parts = self.backend_url.replace("ws://", "").split(":")
            if len(backend_url_parts) >= 2:
                host = backend_url_parts[0]
                port = int(backend_url_parts[1])
            else:
                host = "localhost"
                port = 8000
            
            # Try to connect to the service
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)  # Short timeout for quick failure detection
            
            try:
                result = sock.connect_ex((host, port))
                if result != 0:
                    raise DockerUnavailableError(
                        f"Backend service not available at {host}:{port}. "
                        f"Connection failed with code: {result}"
                    )
            finally:
                sock.close()
            
            logger.debug(f"✅ Service availability verified: {host}:{port}")
            
        except socket.gaierror as e:
            raise DockerUnavailableError(f"DNS resolution failed for backend service: {e}")
        except Exception as e:
            raise DockerUnavailableError(f"Service availability check failed: {e}")
    
    def create_graceful_test_wrapper(self, test_method):
        """Decorator to wrap test methods with graceful degradation.
        
        Usage:
        @manager.create_graceful_test_wrapper
        async def test_something(self):
            # Test implementation
            pass
        """
        async def wrapper(*args, **kwargs):
            return await self.test_with_graceful_degradation(
                lambda: test_method(*args, **kwargs),
                test_name=test_method.__name__
            )
        
        # Preserve original function metadata
        wrapper.__name__ = test_method.__name__
        wrapper.__doc__ = test_method.__doc__
        return wrapper
    
    def enable_connection_pool(self, enabled: bool = True) -> None:
        """Enable or disable connection pooling optimization.
        
        Args:
            enabled: Whether to enable connection pooling
        """
        self.pool_enabled = enabled
        logger.info(f"Connection pooling {'enabled' if enabled else 'disabled'}")
    
    def _get_pooled_connection(self, user_id: str) -> Optional[RealWebSocketTestClient]:
        """Get a connection from the pool for a specific user.
        
        Args:
            user_id: User ID to get connection for
            
        Returns:
            WebSocket client if available in pool, None otherwise
        """
        if not self.pool_enabled:
            return None
        
        pooled_conn = self.connection_pool.get(user_id)
        if not pooled_conn:
            return None
        
        current_time = time.time()
        
        # Check if connection is too old
        if current_time - pooled_conn.created_at > self.pool_max_age_seconds:
            logger.debug(f"Pooled connection for {user_id} too old, removing from pool")
            self._remove_from_pool(user_id)
            return None
        
        # Check if connection has been idle too long
        if current_time - pooled_conn.last_used > self.pool_max_idle_seconds:
            logger.debug(f"Pooled connection for {user_id} idle too long, removing from pool")
            self._remove_from_pool(user_id)
            return None
        
        # Check if connection is still active
        if not pooled_conn.is_active or pooled_conn.client.state in [
            WebSocketConnectionState.CLOSED, 
            WebSocketConnectionState.ERROR
        ]:
            logger.debug(f"Pooled connection for {user_id} no longer active, removing from pool")
            self._remove_from_pool(user_id)
            return None
        
        # Connection is good to reuse
        pooled_conn.last_used = current_time
        pooled_conn.usage_count += 1
        logger.debug(f"Reusing pooled connection for {user_id} (usage: {pooled_conn.usage_count})")
        return pooled_conn.client
    
    def _add_to_pool(self, user_id: str, client: RealWebSocketTestClient) -> None:
        """Add a connection to the pool.
        
        Args:
            user_id: User ID for the connection
            client: WebSocket client to add to pool
        """
        if not self.pool_enabled:
            return
        
        current_time = time.time()
        pooled_conn = PooledConnection(
            client=client,
            user_id=user_id,
            last_used=current_time,
            created_at=current_time,
            usage_count=1,
            is_active=True
        )
        
        self.connection_pool[user_id] = pooled_conn
        logger.debug(f"Added connection to pool for {user_id}")
    
    def _remove_from_pool(self, user_id: str) -> None:
        """Remove a connection from the pool.
        
        Args:
            user_id: User ID to remove from pool
        """
        pooled_conn = self.connection_pool.pop(user_id, None)
        if pooled_conn:
            # Close the pooled connection
            try:
                asyncio.create_task(pooled_conn.client.close())
            except Exception as e:
                logger.warning(f"Error closing pooled connection for {user_id}: {e}")
            
            logger.debug(f"Removed connection from pool for {user_id}")
    
    def _cleanup_pool(self) -> None:
        """Clean up expired connections from the pool."""
        if not self.pool_enabled:
            return
        
        current_time = time.time()
        expired_users = []
        
        for user_id, pooled_conn in self.connection_pool.items():
            if (current_time - pooled_conn.created_at > self.pool_max_age_seconds or
                current_time - pooled_conn.last_used > self.pool_max_idle_seconds or
                not pooled_conn.is_active):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self._remove_from_pool(user_id)
        
        if expired_users:
            logger.debug(f"Cleaned up {len(expired_users)} expired pooled connections")
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get connection pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        if not self.pool_enabled:
            return {"pool_enabled": False}
        
        current_time = time.time()
        active_connections = 0
        total_usage = 0
        avg_age = 0.0
        
        for pooled_conn in self.connection_pool.values():
            if pooled_conn.is_active:
                active_connections += 1
                total_usage += pooled_conn.usage_count
                avg_age += current_time - pooled_conn.created_at
        
        if active_connections > 0:
            avg_age = avg_age / active_connections
        
        return {
            "pool_enabled": True,
            "pooled_connections": len(self.connection_pool),
            "active_connections": active_connections,
            "total_usage_count": total_usage,
            "average_connection_age_seconds": avg_age,
            "pool_max_age_seconds": self.pool_max_age_seconds,
            "pool_max_idle_seconds": self.pool_max_idle_seconds
        }