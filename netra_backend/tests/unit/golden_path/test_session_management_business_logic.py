"""
Test Session Management Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - User session foundation
- Business Goal: Secure, scalable session management for concurrent users
- Value Impact: Session management enables multi-user $500K+ ARR platform scaling
- Strategic Impact: Session failures = user disconnection = immediate revenue loss

This test validates core session management algorithms that power:
1. Secure session creation and validation
2. Session timeout and cleanup management
3. Multi-user session isolation and concurrency
4. WebSocket session binding and lifecycle
5. Session persistence and recovery patterns

CRITICAL BUSINESS RULES:
- Free tier: 1 concurrent session, 2 hour timeout
- Early tier: 3 concurrent sessions, 4 hour timeout
- Mid tier: 10 concurrent sessions, 8 hour timeout  
- Enterprise tier: 50 concurrent sessions, 24 hour timeout
- All sessions must have complete isolation
- Failed sessions must not affect other users
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import uuid
import threading
import hashlib

from shared.types.core_types import UserID, SessionID
from shared.isolated_environment import get_env

# Business Logic Classes (SSOT for session management)

class SubscriptionTier(Enum):
    FREE = "free"
    EARLY = "early"
    MID = "mid"
    ENTERPRISE = "enterprise"

class SessionState(Enum):
    CREATING = "creating"
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    TERMINATED = "terminated"

class SessionType(Enum):
    WEB = "web"
    API = "api"
    WEBSOCKET = "websocket"

@dataclass
class SessionConfig:
    """Session configuration based on user tier."""
    max_concurrent_sessions: int
    session_timeout_minutes: int
    idle_timeout_minutes: int
    requires_encryption: bool
    supports_websocket: bool

@dataclass
class UserSession:
    """Individual user session."""
    session_id: str
    user_id: str
    user_tier: SubscriptionTier
    session_type: SessionType
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    state: SessionState
    metadata: Dict[str, any]
    websocket_connections: Set[str]

@dataclass
class SessionMetrics:
    """Session metrics for monitoring."""
    total_sessions: int
    active_sessions: int
    sessions_by_tier: Dict[str, int]
    average_session_duration: float
    concurrent_peak: int
    cleanup_efficiency: float

class SessionManager:
    """
    SSOT Session Management Business Logic
    
    This class implements secure, scalable session management for
    multi-user platform operations.
    """
    
    # TIER-BASED SESSION CONFIGURATION
    TIER_CONFIGS = {
        SubscriptionTier.FREE: SessionConfig(
            max_concurrent_sessions=1,
            session_timeout_minutes=120,  # 2 hours
            idle_timeout_minutes=30,
            requires_encryption=True,
            supports_websocket=True
        ),
        SubscriptionTier.EARLY: SessionConfig(
            max_concurrent_sessions=3,
            session_timeout_minutes=240,  # 4 hours
            idle_timeout_minutes=60,
            requires_encryption=True,
            supports_websocket=True
        ),
        SubscriptionTier.MID: SessionConfig(
            max_concurrent_sessions=10,
            session_timeout_minutes=480,  # 8 hours
            idle_timeout_minutes=120,
            requires_encryption=True,
            supports_websocket=True
        ),
        SubscriptionTier.ENTERPRISE: SessionConfig(
            max_concurrent_sessions=50,
            session_timeout_minutes=1440,  # 24 hours
            idle_timeout_minutes=240,
            requires_encryption=True,
            supports_websocket=True
        )
    }
    
    def __init__(self):
        self._active_sessions: Dict[str, UserSession] = {}
        self._user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self._session_lock = threading.Lock()
        
    def create_session(self, user_id: str, user_tier: SubscriptionTier, 
                      session_type: SessionType = SessionType.WEB,
                      metadata: Optional[Dict[str, any]] = None) -> UserSession:
        """
        Create new user session with tier-based configuration.
        
        Critical: Enforces tier limits and ensures session isolation.
        """
        with self._session_lock:
            # Check concurrent session limits
            existing_sessions = self._get_active_user_sessions(user_id)
            tier_config = self.TIER_CONFIGS[user_tier]
            
            if len(existing_sessions) >= tier_config.max_concurrent_sessions:
                # Clean up expired sessions first
                self._cleanup_expired_sessions(user_id)
                existing_sessions = self._get_active_user_sessions(user_id)
                
                if len(existing_sessions) >= tier_config.max_concurrent_sessions:
                    raise ValueError(f"Maximum concurrent sessions ({tier_config.max_concurrent_sessions}) reached for tier {user_tier.value}")
            
            # Generate secure session ID
            session_id = self._generate_secure_session_id(user_id)
            
            # Calculate expiration times
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(minutes=tier_config.session_timeout_minutes)
            
            # Create session
            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                user_tier=user_tier,
                session_type=session_type,
                created_at=now,
                last_activity=now,
                expires_at=expires_at,
                state=SessionState.CREATING,
                metadata=metadata or {},
                websocket_connections=set()
            )
            
            # Register session
            self._active_sessions[session_id] = session
            
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session_id)
            
            # Activate session
            session.state = SessionState.ACTIVE
            
            return session

    def validate_session(self, session_id: str) -> Dict[str, any]:
        """
        Validate session and return status.
        
        Critical: Ensures only valid sessions can access platform.
        """
        if session_id not in self._active_sessions:
            return {
                'valid': False,
                'reason': 'session_not_found',
                'action': 'redirect_to_login'
            }
        
        session = self._active_sessions[session_id]
        now = datetime.now(timezone.utc)
        
        # Check expiration
        if now > session.expires_at:
            session.state = SessionState.EXPIRED
            return {
                'valid': False,
                'reason': 'session_expired',
                'action': 'redirect_to_login',
                'expired_at': session.expires_at
            }
        
        # Check idle timeout
        tier_config = self.TIER_CONFIGS[session.user_tier]
        idle_cutoff = now - timedelta(minutes=tier_config.idle_timeout_minutes)
        
        if session.last_activity < idle_cutoff:
            session.state = SessionState.IDLE
            return {
                'valid': False,
                'reason': 'session_idle',
                'action': 'prompt_for_activity',
                'idle_since': session.last_activity
            }
        
        # Valid session - update activity
        session.last_activity = now
        session.state = SessionState.ACTIVE
        
        return {
            'valid': True,
            'session_id': session_id,
            'user_id': session.user_id,
            'user_tier': session.user_tier.value,
            'expires_at': session.expires_at,
            'time_remaining_minutes': int((session.expires_at - now).total_seconds() / 60)
        }

    def extend_session(self, session_id: str, extension_minutes: int = 60) -> bool:
        """
        Extend session expiration time.
        
        Used for active users to prevent disconnection.
        """
        if session_id not in self._active_sessions:
            return False
        
        session = self._active_sessions[session_id]
        tier_config = self.TIER_CONFIGS[session.user_tier]
        
        # Limit extension to session timeout
        max_extension = tier_config.session_timeout_minutes
        extension_minutes = min(extension_minutes, max_extension)
        
        session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=extension_minutes)
        session.last_activity = datetime.now(timezone.utc)
        session.state = SessionState.ACTIVE
        
        return True

    def bind_websocket_connection(self, session_id: str, connection_id: str) -> bool:
        """
        Bind WebSocket connection to session.
        
        Critical for WebSocket-based real-time features.
        """
        if session_id not in self._active_sessions:
            return False
        
        session = self._active_sessions[session_id]
        tier_config = self.TIER_CONFIGS[session.user_tier]
        
        if not tier_config.supports_websocket:
            return False
        
        session.websocket_connections.add(connection_id)
        session.last_activity = datetime.now(timezone.utc)
        
        return True

    def unbind_websocket_connection(self, session_id: str, connection_id: str) -> bool:
        """
        Unbind WebSocket connection from session.
        
        Maintains connection state consistency.
        """
        if session_id not in self._active_sessions:
            return False
        
        session = self._active_sessions[session_id]
        session.websocket_connections.discard(connection_id)
        
        return True

    def terminate_session(self, session_id: str, reason: str = "user_logout") -> Dict[str, any]:
        """
        Terminate session and cleanup resources.
        
        Critical: Must clean up all session resources.
        """
        termination_result = {
            'terminated': False,
            'reason': reason,
            'cleanup_results': {},
            'websocket_connections_closed': 0
        }
        
        with self._session_lock:
            if session_id not in self._active_sessions:
                termination_result['reason'] = 'session_not_found'
                return termination_result
            
            session = self._active_sessions[session_id]
            session.state = SessionState.EXPIRING
            
            # Close WebSocket connections
            websocket_count = len(session.websocket_connections)
            session.websocket_connections.clear()
            
            # Remove from user session tracking
            if session.user_id in self._user_sessions:
                self._user_sessions[session.user_id].discard(session_id)
                if not self._user_sessions[session.user_id]:
                    del self._user_sessions[session.user_id]
            
            # Mark as terminated
            session.state = SessionState.TERMINATED
            
            # Remove from active sessions
            del self._active_sessions[session_id]
            
            termination_result['terminated'] = True
            termination_result['websocket_connections_closed'] = websocket_count
        
        return termination_result

    def cleanup_expired_sessions(self) -> Dict[str, any]:
        """
        Cleanup all expired sessions.
        
        Critical for system health and resource management.
        """
        cleanup_results = {
            'sessions_cleaned': 0,
            'websocket_connections_closed': 0,
            'cleanup_failures': [],
            'cleanup_time_ms': 0
        }
        
        start_time = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)
        
        expired_session_ids = []
        
        with self._session_lock:
            # Find expired sessions
            for session_id, session in self._active_sessions.items():
                if (now > session.expires_at or 
                    session.state in [SessionState.EXPIRED, SessionState.TERMINATED]):
                    expired_session_ids.append(session_id)
        
        # Cleanup expired sessions
        for session_id in expired_session_ids:
            try:
                termination = self.terminate_session(session_id, "expired")
                if termination['terminated']:
                    cleanup_results['sessions_cleaned'] += 1
                    cleanup_results['websocket_connections_closed'] += termination['websocket_connections_closed']
            except Exception as e:
                cleanup_results['cleanup_failures'].append(f"Session {session_id}: {str(e)}")
        
        end_time = datetime.now(timezone.utc)
        cleanup_results['cleanup_time_ms'] = (end_time - start_time).total_seconds() * 1000
        
        return cleanup_results

    def get_session_metrics(self) -> SessionMetrics:
        """
        Generate comprehensive session metrics.
        
        Critical for operational monitoring and scaling decisions.
        """
        with self._session_lock:
            total_sessions = len(self._active_sessions)
            
            # Count active sessions
            now = datetime.now(timezone.utc)
            active_sessions = sum(
                1 for session in self._active_sessions.values()
                if session.state == SessionState.ACTIVE and now <= session.expires_at
            )
            
            # Sessions by tier
            sessions_by_tier = {}
            for tier in SubscriptionTier:
                sessions_by_tier[tier.value] = sum(
                    1 for session in self._active_sessions.values()
                    if session.user_tier == tier
                )
            
            # Calculate average session duration
            session_durations = []
            for session in self._active_sessions.values():
                duration = (session.last_activity - session.created_at).total_seconds() / 60
                session_durations.append(duration)
            
            avg_duration = sum(session_durations) / len(session_durations) if session_durations else 0
            
            # Calculate concurrent peak (simplified - would track over time in real implementation)
            concurrent_peak = len(self._user_sessions)
            
            # Cleanup efficiency (percentage of sessions that cleanup successfully)
            cleanup_efficiency = 0.95  # Would calculate based on actual cleanup history
            
            return SessionMetrics(
                total_sessions=total_sessions,
                active_sessions=active_sessions,
                sessions_by_tier=sessions_by_tier,
                average_session_duration=avg_duration,
                concurrent_peak=concurrent_peak,
                cleanup_efficiency=cleanup_efficiency
            )

    def get_user_active_sessions(self, user_id: str) -> List[UserSession]:
        """
        Get all active sessions for user.
        
        Used for session management and security monitoring.
        """
        sessions = []
        now = datetime.now(timezone.utc)
        
        if user_id in self._user_sessions:
            for session_id in self._user_sessions[user_id]:
                if session_id in self._active_sessions:
                    session = self._active_sessions[session_id]
                    if session.state == SessionState.ACTIVE and now <= session.expires_at:
                        sessions.append(session)
        
        return sessions

    def detect_session_anomalies(self) -> Dict[str, List[str]]:
        """
        Detect session anomalies for security monitoring.
        
        Critical for detecting potential security issues.
        """
        anomalies = {
            'concurrent_limit_violations': [],
            'expired_but_active': [],
            'orphaned_sessions': [],
            'suspicious_activity_patterns': []
        }
        
        now = datetime.now(timezone.utc)
        
        with self._session_lock:
            # Check concurrent limits
            for user_id, session_ids in self._user_sessions.items():
                active_sessions = []
                for session_id in session_ids:
                    if session_id in self._active_sessions:
                        session = self._active_sessions[session_id]
                        if session.state == SessionState.ACTIVE and now <= session.expires_at:
                            active_sessions.append(session)
                
                if active_sessions:
                    tier_config = self.TIER_CONFIGS[active_sessions[0].user_tier]
                    if len(active_sessions) > tier_config.max_concurrent_sessions:
                        anomalies['concurrent_limit_violations'].append(
                            f"User {user_id} has {len(active_sessions)} sessions (limit: {tier_config.max_concurrent_sessions})"
                        )
            
            # Check for expired but active sessions
            for session_id, session in self._active_sessions.items():
                if session.state == SessionState.ACTIVE and now > session.expires_at:
                    anomalies['expired_but_active'].append(session_id)
                
                # Check for suspicious activity (very old sessions still active)
                session_age = (now - session.created_at).total_seconds() / 3600  # hours
                if session_age > 48:  # Sessions older than 48 hours
                    anomalies['suspicious_activity_patterns'].append(
                        f"Session {session_id} active for {session_age:.1f} hours"
                    )
        
        return anomalies

    # PRIVATE HELPER METHODS

    def _generate_secure_session_id(self, user_id: str) -> str:
        """Generate cryptographically secure session ID."""
        timestamp = str(datetime.now(timezone.utc).timestamp())
        random_component = str(uuid.uuid4())
        
        # Create hash from user_id + timestamp + random component
        hash_input = f"{user_id}:{timestamp}:{random_component}"
        session_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        return f"sess_{session_hash[:32]}"

    def _get_active_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get active sessions for user."""
        sessions = []
        now = datetime.now(timezone.utc)
        
        if user_id in self._user_sessions:
            for session_id in self._user_sessions[user_id]:
                if session_id in self._active_sessions:
                    session = self._active_sessions[session_id]
                    if session.state in [SessionState.ACTIVE, SessionState.IDLE] and now <= session.expires_at:
                        sessions.append(session)
        
        return sessions

    def _cleanup_expired_sessions(self, user_id: str):
        """Cleanup expired sessions for specific user."""
        if user_id not in self._user_sessions:
            return
        
        expired_session_ids = []
        now = datetime.now(timezone.utc)
        
        for session_id in list(self._user_sessions[user_id]):
            if session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                if now > session.expires_at:
                    expired_session_ids.append(session_id)
        
        for session_id in expired_session_ids:
            self.terminate_session(session_id, "expired")


class TestSessionManagementBusinessLogic:
    """Test session management business logic for multi-user platform."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.session_manager = SessionManager()
        self.test_user_id = str(uuid.uuid4())
        
    # SESSION CREATION TESTS

    def test_create_session_successful(self):
        """Test successful session creation."""
        session = self.session_manager.create_session(
            user_id=self.test_user_id,
            user_tier=SubscriptionTier.MID,
            session_type=SessionType.WEB
        )
        
        assert session.user_id == self.test_user_id
        assert session.user_tier == SubscriptionTier.MID
        assert session.session_type == SessionType.WEB
        assert session.state == SessionState.ACTIVE
        assert session.session_id.startswith('sess_')
        assert session.expires_at > datetime.now(timezone.utc)

    def test_create_session_enforces_tier_limits(self):
        """Test that session creation enforces tier concurrent limits."""
        # Free tier allows only 1 concurrent session
        session1 = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.FREE
        )
        
        # Attempt to create second session should fail
        with pytest.raises(ValueError) as exc_info:
            self.session_manager.create_session(
                self.test_user_id, SubscriptionTier.FREE
            )
        
        assert "Maximum concurrent sessions" in str(exc_info.value)

    def test_create_multiple_sessions_different_users(self):
        """Test creating sessions for different users."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        
        session1 = self.session_manager.create_session(user1_id, SubscriptionTier.MID)
        session2 = self.session_manager.create_session(user2_id, SubscriptionTier.MID)
        
        assert session1.user_id != session2.user_id
        assert session1.session_id != session2.session_id

    def test_session_expiration_time_by_tier(self):
        """Test that session expiration times vary by tier."""
        free_session = self.session_manager.create_session(
            str(uuid.uuid4()), SubscriptionTier.FREE
        )
        
        enterprise_session = self.session_manager.create_session(
            str(uuid.uuid4()), SubscriptionTier.ENTERPRISE
        )
        
        # Enterprise sessions should expire later than Free
        assert enterprise_session.expires_at > free_session.expires_at

    # SESSION VALIDATION TESTS

    def test_validate_active_session(self):
        """Test validation of active session."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        validation = self.session_manager.validate_session(session.session_id)
        
        assert validation['valid'] is True
        assert validation['user_id'] == self.test_user_id
        assert validation['time_remaining_minutes'] > 0

    def test_validate_nonexistent_session(self):
        """Test validation of nonexistent session."""
        fake_session_id = "sess_nonexistent"
        
        validation = self.session_manager.validate_session(fake_session_id)
        
        assert validation['valid'] is False
        assert validation['reason'] == 'session_not_found'
        assert validation['action'] == 'redirect_to_login'

    def test_validate_expired_session(self):
        """Test validation of expired session."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.FREE
        )
        
        # Manually expire the session
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        
        validation = self.session_manager.validate_session(session.session_id)
        
        assert validation['valid'] is False
        assert validation['reason'] == 'session_expired'
        assert validation['action'] == 'redirect_to_login'

    def test_validate_idle_session(self):
        """Test validation of idle session."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.EARLY
        )
        
        # Make session idle by setting old last_activity
        tier_config = self.session_manager.TIER_CONFIGS[SubscriptionTier.EARLY]
        session.last_activity = datetime.now(timezone.utc) - timedelta(
            minutes=tier_config.idle_timeout_minutes + 1
        )
        
        validation = self.session_manager.validate_session(session.session_id)
        
        assert validation['valid'] is False
        assert validation['reason'] == 'session_idle'
        assert validation['action'] == 'prompt_for_activity'

    def test_session_activity_update_on_validation(self):
        """Test that successful validation updates last activity."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        original_activity = session.last_activity
        
        # Small delay to ensure different timestamp
        import time
        time.sleep(0.01)
        
        validation = self.session_manager.validate_session(session.session_id)
        
        assert validation['valid'] is True
        assert session.last_activity > original_activity

    # SESSION EXTENSION TESTS

    def test_extend_session_successful(self):
        """Test successful session extension."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        original_expiration = session.expires_at
        
        success = self.session_manager.extend_session(session.session_id, 120)
        
        assert success is True
        assert session.expires_at > original_expiration

    def test_extend_nonexistent_session(self):
        """Test extending nonexistent session."""
        success = self.session_manager.extend_session("fake_session", 60)
        
        assert success is False

    def test_extend_session_respects_tier_limits(self):
        """Test that session extension respects tier timeout limits."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.FREE
        )
        
        # Try to extend beyond tier limit
        self.session_manager.extend_session(session.session_id, 1000)  # Request 1000 minutes
        
        # Should be limited to tier maximum (120 minutes for Free)
        tier_config = self.session_manager.TIER_CONFIGS[SubscriptionTier.FREE]
        max_extension = timedelta(minutes=tier_config.session_timeout_minutes)
        
        assert session.expires_at <= session.created_at + max_extension + timedelta(minutes=1)  # Small buffer

    # WEBSOCKET CONNECTION TESTS

    def test_bind_websocket_connection(self):
        """Test binding WebSocket connection to session."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        connection_id = "ws_" + str(uuid.uuid4())
        
        success = self.session_manager.bind_websocket_connection(
            session.session_id, connection_id
        )
        
        assert success is True
        assert connection_id in session.websocket_connections

    def test_unbind_websocket_connection(self):
        """Test unbinding WebSocket connection from session."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        connection_id = "ws_" + str(uuid.uuid4())
        
        # Bind then unbind
        self.session_manager.bind_websocket_connection(session.session_id, connection_id)
        self.session_manager.unbind_websocket_connection(session.session_id, connection_id)
        
        assert connection_id not in session.websocket_connections

    def test_bind_websocket_to_nonexistent_session(self):
        """Test binding WebSocket to nonexistent session."""
        success = self.session_manager.bind_websocket_connection(
            "fake_session", "fake_connection"
        )
        
        assert success is False

    def test_websocket_binding_updates_activity(self):
        """Test that WebSocket binding updates session activity."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        original_activity = session.last_activity
        
        import time
        time.sleep(0.01)
        
        self.session_manager.bind_websocket_connection(
            session.session_id, "test_connection"
        )
        
        assert session.last_activity > original_activity

    # SESSION TERMINATION TESTS

    def test_terminate_session_successful(self):
        """Test successful session termination."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        # Add WebSocket connection
        connection_id = "test_connection"
        self.session_manager.bind_websocket_connection(session.session_id, connection_id)
        
        termination = self.session_manager.terminate_session(
            session.session_id, "user_logout"
        )
        
        assert termination['terminated'] is True
        assert termination['reason'] == "user_logout"
        assert termination['websocket_connections_closed'] == 1
        assert session.session_id not in self.session_manager._active_sessions

    def test_terminate_nonexistent_session(self):
        """Test terminating nonexistent session."""
        termination = self.session_manager.terminate_session("fake_session")
        
        assert termination['terminated'] is False
        assert termination['reason'] == 'session_not_found'

    def test_termination_removes_from_user_tracking(self):
        """Test that termination removes session from user tracking."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        # Verify session is tracked
        assert self.test_user_id in self.session_manager._user_sessions
        assert session.session_id in self.session_manager._user_sessions[self.test_user_id]
        
        self.session_manager.terminate_session(session.session_id)
        
        # Should be removed from user tracking
        if self.test_user_id in self.session_manager._user_sessions:
            assert session.session_id not in self.session_manager._user_sessions[self.test_user_id]

    # SESSION CLEANUP TESTS

    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions."""
        # Create sessions and expire them
        session1 = self.session_manager.create_session(
            str(uuid.uuid4()), SubscriptionTier.FREE
        )
        session2 = self.session_manager.create_session(
            str(uuid.uuid4()), SubscriptionTier.EARLY
        )
        
        # Expire both sessions
        past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        session1.expires_at = past_time
        session2.expires_at = past_time
        
        cleanup_results = self.session_manager.cleanup_expired_sessions()
        
        assert cleanup_results['sessions_cleaned'] == 2
        assert cleanup_results['cleanup_time_ms'] >= 0

    def test_cleanup_preserves_active_sessions(self):
        """Test that cleanup preserves active sessions."""
        active_session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        expired_session = self.session_manager.create_session(
            str(uuid.uuid4()), SubscriptionTier.FREE
        )
        expired_session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        cleanup_results = self.session_manager.cleanup_expired_sessions()
        
        assert cleanup_results['sessions_cleaned'] == 1
        assert active_session.session_id in self.session_manager._active_sessions

    # SESSION METRICS TESTS

    def test_session_metrics_generation(self):
        """Test session metrics generation."""
        # Create sessions of different tiers
        free_session = self.session_manager.create_session(
            str(uuid.uuid4()), SubscriptionTier.FREE
        )
        mid_session = self.session_manager.create_session(
            str(uuid.uuid4()), SubscriptionTier.MID
        )
        
        metrics = self.session_manager.get_session_metrics()
        
        assert metrics.total_sessions == 2
        assert metrics.active_sessions == 2
        assert metrics.sessions_by_tier['free'] == 1
        assert metrics.sessions_by_tier['mid'] == 1
        assert metrics.average_session_duration >= 0

    def test_empty_session_metrics(self):
        """Test session metrics with no sessions."""
        metrics = self.session_manager.get_session_metrics()
        
        assert metrics.total_sessions == 0
        assert metrics.active_sessions == 0
        assert metrics.average_session_duration == 0

    # USER SESSION MANAGEMENT TESTS

    def test_get_user_active_sessions(self):
        """Test retrieving user's active sessions."""
        session1 = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.EARLY
        )
        session2 = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.EARLY
        )
        
        active_sessions = self.session_manager.get_user_active_sessions(self.test_user_id)
        
        assert len(active_sessions) == 2
        session_ids = [s.session_id for s in active_sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids

    def test_get_user_sessions_excludes_expired(self):
        """Test that get_user_active_sessions excludes expired sessions."""
        active_session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.EARLY
        )
        
        expired_session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.EARLY
        )
        expired_session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        active_sessions = self.session_manager.get_user_active_sessions(self.test_user_id)
        
        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == active_session.session_id

    # ANOMALY DETECTION TESTS

    def test_detect_concurrent_limit_violations(self):
        """Test detection of concurrent session limit violations."""
        # Manually create violation by exceeding Free tier limit
        session1 = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.FREE
        )
        
        # Force create second session by bypassing limit check
        session2_id = self.session_manager._generate_secure_session_id(self.test_user_id)
        session2 = UserSession(
            session_id=session2_id,
            user_id=self.test_user_id,
            user_tier=SubscriptionTier.FREE,
            session_type=SessionType.WEB,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            state=SessionState.ACTIVE,
            metadata={},
            websocket_connections=set()
        )
        
        # Manually add to bypass limits
        self.session_manager._active_sessions[session2_id] = session2
        self.session_manager._user_sessions[self.test_user_id].add(session2_id)
        
        anomalies = self.session_manager.detect_session_anomalies()
        
        assert len(anomalies['concurrent_limit_violations']) > 0
        assert self.test_user_id in anomalies['concurrent_limit_violations'][0]

    def test_detect_expired_but_active_sessions(self):
        """Test detection of expired but still active sessions."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        # Expire session but keep it active (anomaly)
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        session.state = SessionState.ACTIVE
        
        anomalies = self.session_manager.detect_session_anomalies()
        
        assert session.session_id in anomalies['expired_but_active']

    def test_detect_suspicious_activity_patterns(self):
        """Test detection of suspicious activity patterns."""
        session = self.session_manager.create_session(
            self.test_user_id, SubscriptionTier.MID
        )
        
        # Make session very old (suspicious)
        session.created_at = datetime.now(timezone.utc) - timedelta(hours=50)
        
        anomalies = self.session_manager.detect_session_anomalies()
        
        assert len(anomalies['suspicious_activity_patterns']) > 0
        assert session.session_id in anomalies['suspicious_activity_patterns'][0]

    # CONFIGURATION AND BUSINESS RULES TESTS

    def test_tier_configurations_are_logical(self):
        """Test that tier configurations follow logical progression."""
        configs = self.session_manager.TIER_CONFIGS
        
        # All tiers should be configured
        for tier in SubscriptionTier:
            assert tier in configs
        
        # Higher tiers should have more sessions and longer timeouts
        free_config = configs[SubscriptionTier.FREE]
        enterprise_config = configs[SubscriptionTier.ENTERPRISE]
        
        assert enterprise_config.max_concurrent_sessions > free_config.max_concurrent_sessions
        assert enterprise_config.session_timeout_minutes > free_config.session_timeout_minutes

    def test_session_id_generation_is_secure(self):
        """Test that session ID generation is secure and unique."""
        session_ids = set()
        
        for i in range(100):
            session_id = self.session_manager._generate_secure_session_id(f"user_{i}")
            assert session_id.startswith('sess_')
            assert len(session_id) > 30  # Should be long enough
            assert session_id not in session_ids  # Should be unique
            session_ids.add(session_id)

    def test_all_tiers_support_websocket(self):
        """Test that all tiers support WebSocket connections."""
        for tier in SubscriptionTier:
            config = self.session_manager.TIER_CONFIGS[tier]
            assert config.supports_websocket is True  # All tiers should support WebSocket