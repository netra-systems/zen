"""
Auth Database Session Test Manager - SSOT for Test Database Sessions

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable proper test database session management for auth tests
- Value Impact: Ensures test isolation and proper transaction handling
- Strategic Impact: Prevents test pollution and ensures reliable test execution
"""

import asyncio
import logging
from typing import AsyncContextManager, Dict, Optional, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class AuthDatabaseSessionTestManager:
    """
    Manages database sessions for auth-related integration tests.
    
    Provides isolated sessions with proper transaction management
    and rollback capabilities for test isolation.
    """
    
    def __init__(self):
        self.sessions: Dict[str, Any] = {}
        self.session_lock = asyncio.Lock()
        self.active_sessions = set()
    
    @asynccontextmanager
    async def get_test_session(self, session_id: Optional[str] = None) -> AsyncContextManager[Any]:
        """
        Get an isolated test database session.
        
        Args:
            session_id: Optional session identifier for conflict detection
            
        Yields:
            Database session with transaction management
            
        Raises:
            Exception: If session conflicts are detected
        """
        if session_id is None:
            session_id = f"session_{id(asyncio.current_task())}"
        
        async with self.session_lock:
            if session_id in self.active_sessions:
                raise Exception(f"Session conflict detected for session_id: {session_id}")
            
            self.active_sessions.add(session_id)
        
        # Mock session object for testing
        mock_session = MockDatabaseSession(session_id)
        
        try:
            yield mock_session
        except Exception as e:
            # Handle transaction rollback on failure
            await mock_session.rollback()
            logger.error(f"Session {session_id} rolled back due to: {e}")
            raise
        finally:
            async with self.session_lock:
                self.active_sessions.discard(session_id)
                if session_id in self.sessions:
                    del self.sessions[session_id]


class MockDatabaseSession:
    """Mock database session for testing session management."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.executed_queries = []
        self.is_rolled_back = False
    
    async def execute(self, query: str, *args) -> None:
        """Execute a mock database query."""
        if self.is_rolled_back:
            raise Exception("Cannot execute on rolled back session")
        
        self.executed_queries.append((query, args))
        
        # Simulate session isolation failure for test purposes
        if "isolation" in query.lower():
            raise Exception("Session isolation not properly configured")
    
    async def rollback(self) -> None:
        """Rollback the session transaction."""
        self.is_rolled_back = True
        self.executed_queries.clear()
        logger.info(f"Session {self.session_id} rolled back")