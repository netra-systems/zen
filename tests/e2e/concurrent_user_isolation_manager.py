"""
Concurrent User Isolation Manager for E2E Testing

This module manages concurrent user session isolation during E2E tests to ensure
that multiple users can be tested simultaneously without cross-contamination.

Business Value Justification (BVJ):
- Segment: Enterprise/Multi-tenant 
- Business Goal: Test multi-user scalability and isolation
- Value Impact: Validates enterprise multi-tenant security requirements
- Strategic Impact: Enables testing of concurrent user scenarios for 500K+ ARR
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from test_framework.ssot.e2e_auth_helper import create_authenticated_user, AuthenticatedUser
from shared.types.core_types import UserID, ensure_user_id

logger = logging.getLogger(__name__)


@dataclass
class ConcurrentUserSession:
    """
    Represents a concurrent user session for isolation testing.
    
    Tracks user authentication, WebSocket connections, and isolation state
    to ensure proper multi-user testing scenarios.
    """
    user_id: UserID
    user: AuthenticatedUser
    websocket_client_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_connected: bool = False
    isolation_verified: bool = False
    data_namespace: str = field(default_factory=lambda: f"test_ns_{uuid.uuid4().hex[:8]}")
    
    def __post_init__(self):
        """Ensure user_id is properly typed"""
        self.user_id = ensure_user_id(self.user_id)


class ConcurrentUserIsolationManager:
    """
    Manages concurrent user sessions for E2E isolation testing.
    
    This class provides utilities for creating multiple authenticated users,
    managing their concurrent sessions, and validating that they remain
    properly isolated from each other.
    
    Key Features:
    - Multi-user session management
    - Cross-contamination prevention
    - Concurrent connection handling
    - Isolation verification utilities
    """
    
    def __init__(self, max_concurrent_users: int = 10):
        """
        Initialize the concurrent user isolation manager.
        
        Args:
            max_concurrent_users: Maximum number of concurrent users to manage
        """
        self.max_concurrent_users = max_concurrent_users
        self.active_sessions: Dict[str, ConcurrentUserSession] = {}
        self.isolation_barriers: Set[str] = set()
        self._lock = asyncio.Lock()
        
    async def create_concurrent_users(
        self,
        user_count: int,
        base_user_prefix: str = "concurrent_test_user"
    ) -> List[ConcurrentUserSession]:
        """
        Create multiple concurrent user sessions for testing.
        
        Args:
            user_count: Number of users to create
            base_user_prefix: Prefix for generated user IDs
            
        Returns:
            List of concurrent user sessions
            
        Raises:
            ValueError: If user_count exceeds maximum allowed
        """
        if user_count > self.max_concurrent_users:
            raise ValueError(f"User count {user_count} exceeds maximum {self.max_concurrent_users}")
            
        async with self._lock:
            sessions = []
            
            for i in range(user_count):
                user_id = f"{base_user_prefix}_{i}_{uuid.uuid4().hex[:8]}"
                
                # Create authenticated user via SSOT helper
                user = await create_authenticated_user(
                    user_id=user_id,
                    email=f"{user_id}@concurrent.test.netrasystems.ai",
                    permissions=["read", "write", "concurrent_test"]
                )
                
                # Create concurrent session
                session = ConcurrentUserSession(
                    user_id=ensure_user_id(user_id),
                    user=user
                )
                
                sessions.append(session)
                self.active_sessions[user_id] = session
                
            logger.info(f"Created {len(sessions)} concurrent user sessions")
            return sessions
    
    async def establish_concurrent_connections(
        self,
        sessions: List[ConcurrentUserSession],
        connection_factory_callback=None
    ) -> List[ConcurrentUserSession]:
        """
        Establish concurrent connections for all user sessions.
        
        Args:
            sessions: List of user sessions to connect
            connection_factory_callback: Optional callback to create connections
            
        Returns:
            List of connected sessions
        """
        async with self._lock:
            connected_sessions = []
            
            # Create connections concurrently
            connection_tasks = []
            for session in sessions:
                task = self._establish_user_connection(session, connection_factory_callback)
                connection_tasks.append(task)
                
            # Wait for all connections
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(connection_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to connect user {sessions[i].user_id}: {result}")
                else:
                    connected_sessions.append(sessions[i])
                    sessions[i].is_connected = True
                    
            logger.info(f"Established {len(connected_sessions)} concurrent connections")
            return connected_sessions
    
    async def _establish_user_connection(
        self,
        session: ConcurrentUserSession,
        connection_factory_callback=None
    ) -> bool:
        """
        Establish connection for a single user session.
        
        Args:
            session: User session to connect
            connection_factory_callback: Optional connection factory
            
        Returns:
            True if connection successful
        """
        try:
            if connection_factory_callback:
                await connection_factory_callback(session)
            
            # Mark as connected (actual connection logic would be in callback)
            session.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Connection failed for {session.user_id}: {e}")
            return False
    
    async def verify_user_isolation(
        self,
        sessions: List[ConcurrentUserSession],
        isolation_test_callback=None
    ) -> Dict[str, bool]:
        """
        Verify that concurrent users are properly isolated.
        
        Args:
            sessions: List of user sessions to test
            isolation_test_callback: Optional callback for custom isolation tests
            
        Returns:
            Dictionary mapping user IDs to isolation verification results
        """
        isolation_results = {}
        
        for session in sessions:
            try:
                # Basic isolation checks
                is_isolated = await self._verify_session_isolation(session)
                
                # Custom isolation test if provided
                if isolation_test_callback and is_isolated:
                    is_isolated = await isolation_test_callback(session, sessions)
                
                session.isolation_verified = is_isolated
                isolation_results[str(session.user_id)] = is_isolated
                
            except Exception as e:
                logger.error(f"Isolation verification failed for {session.user_id}: {e}")
                isolation_results[str(session.user_id)] = False
                
        return isolation_results
    
    async def _verify_session_isolation(self, session: ConcurrentUserSession) -> bool:
        """
        Verify basic session isolation for a user.
        
        Args:
            session: User session to verify
            
        Returns:
            True if session appears properly isolated
        """
        # Check that session has unique identifiers
        if not session.websocket_client_id or not session.session_id:
            return False
            
        # Check that data namespace is unique
        if session.data_namespace in self.isolation_barriers:
            return False
            
        # Add to isolation barriers to prevent future conflicts
        self.isolation_barriers.add(session.data_namespace)
        
        return True
    
    @asynccontextmanager
    async def concurrent_user_context(
        self,
        user_count: int,
        base_user_prefix: str = "context_test_user"
    ):
        """
        Async context manager for concurrent user testing.
        
        Args:
            user_count: Number of concurrent users
            base_user_prefix: Prefix for user IDs
            
        Yields:
            List of concurrent user sessions
        """
        sessions = await self.create_concurrent_users(user_count, base_user_prefix)
        
        try:
            yield sessions
        finally:
            await self.cleanup_concurrent_sessions(sessions)
    
    async def cleanup_concurrent_sessions(
        self,
        sessions: List[ConcurrentUserSession]
    ) -> None:
        """
        Clean up concurrent user sessions.
        
        Args:
            sessions: List of sessions to clean up
        """
        async with self._lock:
            for session in sessions:
                # Remove from active sessions
                if str(session.user_id) in self.active_sessions:
                    del self.active_sessions[str(session.user_id)]
                
                # Remove isolation barriers
                self.isolation_barriers.discard(session.data_namespace)
                
                # Mark as disconnected
                session.is_connected = False
                session.isolation_verified = False
                
            logger.info(f"Cleaned up {len(sessions)} concurrent user sessions")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current concurrent sessions.
        
        Returns:
            Dictionary with session statistics
        """
        active_count = len(self.active_sessions)
        connected_count = sum(1 for s in self.active_sessions.values() if s.is_connected)
        verified_count = sum(1 for s in self.active_sessions.values() if s.isolation_verified)
        
        return {
            "active_sessions": active_count,
            "connected_sessions": connected_count,
            "verified_isolated_sessions": verified_count,
            "isolation_barriers": len(self.isolation_barriers),
            "max_concurrent_users": self.max_concurrent_users
        }


# Convenience functions for direct usage

async def create_concurrent_test_users(
    user_count: int,
    base_prefix: str = "concurrent_user"
) -> List[ConcurrentUserSession]:
    """
    Create concurrent test users for E2E scenarios.
    
    Args:
        user_count: Number of users to create
        base_prefix: Prefix for user identifiers
        
    Returns:
        List of concurrent user sessions
    """
    manager = ConcurrentUserIsolationManager()
    return await manager.create_concurrent_users(user_count, base_prefix)


async def verify_concurrent_isolation(
    sessions: List[ConcurrentUserSession]
) -> bool:
    """
    Verify that concurrent user sessions are properly isolated.
    
    Args:
        sessions: List of sessions to verify
        
    Returns:
        True if all sessions are properly isolated
    """
    manager = ConcurrentUserIsolationManager()
    results = await manager.verify_user_isolation(sessions)
    return all(results.values())


__all__ = [
    "ConcurrentUserSession",
    "ConcurrentUserIsolationManager", 
    "create_concurrent_test_users",
    "verify_concurrent_isolation"
]