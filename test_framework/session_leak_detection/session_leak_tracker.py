"""
Session Leak Tracker - Detects Database Session Leaks in Real-Time

This tracker monitors database session lifecycle events and detects
sessions that are not properly closed or committed/rolled back.

CRITICAL: Designed to FAIL HARD when session leaks are detected,
following CLAUDE.md principle: "Tests must raise errors"
"""

import asyncio
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine.events import event

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Information about a tracked database session."""
    session_id: str
    created_at: datetime
    creation_stack: str
    function_name: str
    is_closed: bool = False
    is_committed: bool = False
    is_rolled_back: bool = False
    close_time: Optional[datetime] = None
    
    @property
    def is_properly_closed(self) -> bool:
        """Check if session was properly closed with commit or rollback."""
        return self.is_closed and (self.is_committed or self.is_rolled_back)
    
    @property
    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        end_time = self.close_time or datetime.now(timezone.utc)
        return (end_time - self.created_at).total_seconds()


class SessionLeakTracker:
    """
    Tracks database sessions to detect leaks.
    
    Session leaks occur when:
    1. Session is not closed after use
    2. Session is closed without commit/rollback
    3. Session remains open longer than expected
    4. Multiple sessions are opened without proper cleanup
    
    CRITICAL: This tracker is designed to FAIL tests when leaks are detected.
    """
    
    def __init__(self, max_session_age_seconds: float = 30.0):
        """
        Initialize session leak tracker.
        
        Args:
            max_session_age_seconds: Maximum allowed session age before leak detection
        """
        self.max_session_age_seconds = max_session_age_seconds
        self.tracked_sessions: Dict[str, SessionInfo] = {}
        self.session_refs: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self.leak_detected = False
        self.leak_details: List[str] = []
        
    def _get_creation_stack(self) -> str:
        """Get stack trace of session creation for debugging."""
        import traceback
        stack = traceback.extract_stack()
        # Filter out internal tracker frames
        relevant_frames = [
            frame for frame in stack
            if 'session_leak_tracker' not in frame.filename
            and 'test_framework' not in frame.filename
        ][-5:]  # Last 5 relevant frames
        
        return '\n'.join([
            f"  {frame.filename}:{frame.lineno} in {frame.name}"
            for frame in relevant_frames
        ])
    
    def _get_calling_function(self) -> str:
        """Get the name of the function that created the session."""
        import traceback
        stack = traceback.extract_stack()
        # Look for thread handler functions
        for frame in reversed(stack):
            if 'handle_' in frame.name or 'test_' in frame.name:
                return frame.name
        return "unknown_function"
    
    async def track_session(self, session: AsyncSession) -> str:
        """
        Start tracking a database session.
        
        Args:
            session: AsyncSession to track
            
        Returns:
            Session tracking ID
        """
        async with self._lock:
            session_id = f"session_{id(session)}_{int(time.time() * 1000)}"
            
            session_info = SessionInfo(
                session_id=session_id,
                created_at=datetime.now(timezone.utc),
                creation_stack=self._get_creation_stack(),
                function_name=self._get_calling_function()
            )
            
            self.tracked_sessions[session_id] = session_info
            
            # Keep weak reference to session for monitoring
            self.session_refs[session_id] = weakref.ref(session)
            
            logger.debug(f"Started tracking session {session_id} from {session_info.function_name}")
            return session_id
    
    async def mark_session_committed(self, session: AsyncSession):
        """Mark session as committed."""
        session_id = self._find_session_id(session)
        if session_id:
            async with self._lock:
                if session_id in self.tracked_sessions:
                    self.tracked_sessions[session_id].is_committed = True
                    logger.debug(f"Session {session_id} marked as committed")
    
    async def mark_session_rolled_back(self, session: AsyncSession):
        """Mark session as rolled back."""
        session_id = self._find_session_id(session)
        if session_id:
            async with self._lock:
                if session_id in self.tracked_sessions:
                    self.tracked_sessions[session_id].is_rolled_back = True
                    logger.debug(f"Session {session_id} marked as rolled back")
    
    async def mark_session_closed(self, session: AsyncSession):
        """Mark session as closed."""
        session_id = self._find_session_id(session)
        if session_id:
            async with self._lock:
                if session_id in self.tracked_sessions:
                    session_info = self.tracked_sessions[session_id]
                    session_info.is_closed = True
                    session_info.close_time = datetime.now(timezone.utc)
                    logger.debug(f"Session {session_id} marked as closed")
    
    def _find_session_id(self, session: AsyncSession) -> Optional[str]:
        """Find session ID by session object."""
        session_obj_id = id(session)
        for session_id, ref in self.session_refs.items():
            if ref() and id(ref()) == session_obj_id:
                return session_id
        return None
    
    async def check_for_leaks(self) -> bool:
        """
        Check for session leaks.
        
        Returns:
            True if leaks detected
        """
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            leaked_sessions = []
            
            for session_id, session_info in self.tracked_sessions.items():
                # Check for sessions that are too old
                if session_info.duration_seconds > self.max_session_age_seconds:
                    if not session_info.is_properly_closed:
                        leaked_sessions.append((session_id, "session_age_leak", 
                                              f"Session {session_id} has been open for {session_info.duration_seconds:.1f}s"))
                
                # Check for sessions closed without transaction handling
                if session_info.is_closed and not (session_info.is_committed or session_info.is_rolled_back):
                    leaked_sessions.append((session_id, "transaction_leak", 
                                          f"Session {session_id} closed without commit/rollback"))
                
                # Check for dead session references (garbage collected but not properly closed)
                ref = self.session_refs.get(session_id)
                if ref and ref() is None and not session_info.is_closed:
                    leaked_sessions.append((session_id, "reference_leak", 
                                          f"Session {session_id} was garbage collected without proper closure"))
            
            if leaked_sessions:
                self.leak_detected = True
                self.leak_details = [detail for _, _, detail in leaked_sessions]
                logger.error(f"Session leaks detected: {len(leaked_sessions)} leaks found")
                for session_id, leak_type, detail in leaked_sessions:
                    logger.error(f"LEAK [{leak_type}]: {detail}")
                return True
            
            return False
    
    async def get_leak_report(self) -> Dict[str, Any]:
        """
        Get detailed leak report.
        
        Returns:
            Dictionary with leak analysis
        """
        async with self._lock:
            active_sessions = [
                session_info for session_info in self.tracked_sessions.values()
                if not session_info.is_properly_closed
            ]
            
            report = {
                'total_sessions_tracked': len(self.tracked_sessions),
                'active_sessions': len(active_sessions),
                'leak_detected': self.leak_detected,
                'leak_details': self.leak_details,
                'session_details': []
            }
            
            for session_info in self.tracked_sessions.values():
                report['session_details'].append({
                    'session_id': session_info.session_id,
                    'function_name': session_info.function_name,
                    'duration_seconds': session_info.duration_seconds,
                    'is_properly_closed': session_info.is_properly_closed,
                    'is_committed': session_info.is_committed,
                    'is_rolled_back': session_info.is_rolled_back,
                    'creation_stack': session_info.creation_stack
                })
            
            return report
    
    def assert_no_leaks(self):
        """
        Assert that no session leaks exist. FAILS HARD if leaks detected.
        
        This method implements CLAUDE.md testing principle:
        "Tests MUST raise errors" and "CHEATING ON TESTS = ABOMINATION"
        """
        if self.leak_detected:
            leak_summary = '\n'.join(self.leak_details)
            raise AssertionError(
                f"DATABASE SESSION LEAKS DETECTED!\n\n"
                f"Number of leaks: {len(self.leak_details)}\n\n"
                f"Leak details:\n{leak_summary}\n\n"
                f"This indicates improper session management in thread handlers.\n"
                f"Sessions must be properly closed with commit() or rollback().\n\n"
                f"CRITICAL: Fix session management before deployment to prevent "
                f"database connection pool exhaustion in production."
            )
    
    async def cleanup(self):
        """Clean up tracker state."""
        async with self._lock:
            self.tracked_sessions.clear()
            self.session_refs.clear()
            self.leak_detected = False
            self.leak_details.clear()


@asynccontextmanager
async def track_session_lifecycle(session: AsyncSession, tracker: SessionLeakTracker):
    """
    Context manager that tracks session lifecycle automatically.
    
    Args:
        session: AsyncSession to track
        tracker: SessionLeakTracker instance
    """
    session_id = await tracker.track_session(session)
    
    try:
        yield session
    finally:
        # Mark session as closed when context exits
        await tracker.mark_session_closed(session)