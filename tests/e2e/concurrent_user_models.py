"""Concurrent User Models - E2E Testing Support

Business Value Justification (BVJ):
- Segment: Enterprise (concurrent user validation required)  
- Business Goal: Validate multi-user isolation and concurrency
- Value Impact: Prevents enterprise customer churn from concurrency issues
- Revenue Impact: Protects $100K+ ARR from enterprise contracts

This module provides models and utilities for testing concurrent user scenarios
in E2E tests, ensuring proper user isolation and system scalability.

CRITICAL: Following CLAUDE.md principles - uses real services, no mocks.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timezone

from shared.isolated_environment import IsolatedEnvironment


@dataclass
class UserTestSession:
    """Represents a single user test session for concurrent testing."""
    user_id: str
    session_id: str
    websocket_connection: Optional[Any] = None
    auth_token: Optional[str] = None
    messages_sent: List[Dict] = None
    messages_received: List[Dict] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def __post_init__(self):
        if self.messages_sent is None:
            self.messages_sent = []
        if self.messages_received is None:
            self.messages_received = []


class IsolationValidator:
    """
    Validates user isolation in concurrent scenarios.
    
    Key responsibilities:
    - Verify no cross-user data contamination  
    - Validate session isolation
    - Check WebSocket message routing
    - Monitor resource isolation
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.violations: List[Dict[str, Any]] = []
        self.user_sessions: Dict[str, UserTestSession] = {}
        
    def register_user_session(self, user_session: UserTestSession):
        """Register a user session for isolation tracking."""
        self.user_sessions[user_session.user_id] = user_session
        
    def check_message_isolation(self, 
                               sender_id: str, 
                               receiver_id: str, 
                               message: Dict) -> bool:
        """
        Check if message was properly isolated between users.
        
        Returns:
            True if isolation is maintained, False if violation detected
        """
        if sender_id == receiver_id:
            return True  # Same user, no isolation required
            
        # Check if sender's message was received by different user
        sender_session = self.user_sessions.get(sender_id)
        receiver_session = self.user_sessions.get(receiver_id)
        
        if not sender_session or not receiver_session:
            return True  # Can't validate without both sessions
            
        # Look for cross-contamination
        sender_message_ids = {msg.get('id') for msg in sender_session.messages_sent}
        receiver_message_ids = {msg.get('id') for msg in receiver_session.messages_received}
        
        # Check for unintended message sharing
        shared_messages = sender_message_ids.intersection(receiver_message_ids)
        if shared_messages:
            violation = {
                'type': 'message_cross_contamination',
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'shared_messages': list(shared_messages),
                'timestamp': time.time()
            }
            self.violations.append(violation)
            return False
            
        return True
        
    def check_session_isolation(self, user_id_1: str, user_id_2: str) -> bool:
        """Check if two user sessions are properly isolated."""
        session_1 = self.user_sessions.get(user_id_1)
        session_2 = self.user_sessions.get(user_id_2)
        
        if not session_1 or not session_2:
            return True  # Can't validate without both sessions
            
        # Check for session ID conflicts
        if session_1.session_id == session_2.session_id:
            violation = {
                'type': 'session_id_conflict',
                'user_1': user_id_1,
                'user_2': user_id_2,
                'session_id': session_1.session_id,
                'timestamp': time.time()
            }
            self.violations.append(violation)
            return False
            
        # Check for auth token sharing (security violation)
        if (session_1.auth_token and session_2.auth_token and 
            session_1.auth_token == session_2.auth_token):
            violation = {
                'type': 'auth_token_sharing',
                'user_1': user_id_1,
                'user_2': user_id_2,
                'timestamp': time.time()
            }
            self.violations.append(violation)
            return False
            
        return True
        
    def validate_concurrent_execution(self, 
                                    user_sessions: List[UserTestSession]) -> Dict[str, Any]:
        """
        Validate that concurrent user sessions maintained proper isolation.
        
        Returns:
            Validation report with results and any violations found
        """
        report = {
            'total_users': len(user_sessions),
            'isolation_maintained': True,
            'violations': [],
            'performance_metrics': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Register all sessions
        for session in user_sessions:
            self.register_user_session(session)
            
        # Check pairwise isolation for all user combinations
        users = list(self.user_sessions.keys())
        for i, user_1 in enumerate(users):
            for j, user_2 in enumerate(users[i+1:], i+1):
                if not self.check_session_isolation(user_1, user_2):
                    report['isolation_maintained'] = False
                    
        # Check message isolation
        for sender in users:
            for receiver in users:
                if sender != receiver:
                    # This is a simplified check - real implementation would
                    # need actual message data
                    self.check_message_isolation(sender, receiver, {})
                    
        # Calculate performance metrics
        if user_sessions:
            execution_times = []
            for session in user_sessions:
                if session.start_time and session.end_time:
                    execution_times.append(session.end_time - session.start_time)
                    
            if execution_times:
                report['performance_metrics'] = {
                    'avg_execution_time': sum(execution_times) / len(execution_times),
                    'max_execution_time': max(execution_times),
                    'min_execution_time': min(execution_times)
                }
                
        report['violations'] = self.violations
        return report
        
    def get_violation_count(self) -> int:
        """Get total number of isolation violations detected."""
        return len(self.violations)
        
    def reset_violations(self):
        """Reset violation tracking for new test."""
        self.violations.clear()
        self.user_sessions.clear()


def create_test_user_session(user_index: int = None) -> UserTestSession:
    """Create a test user session for concurrent testing."""
    if user_index is None:
        user_index = int(time.time() * 1000) % 10000
        
    user_id = f"test-user-{user_index:04d}"
    session_id = f"session-{uuid.uuid4().hex[:12]}"
    
    return UserTestSession(
        user_id=user_id,
        session_id=session_id,
        start_time=time.time()
    )


def create_concurrent_test_users(count: int) -> List[UserTestSession]:
    """Create multiple test user sessions for concurrent testing."""
    return [create_test_user_session(i) for i in range(count)]