"""Session utilities and cleanup operations - MODULAR ARCHITECTURE.

Handles session cleanup, expired session removal, and utility functions.
Follows 300-line limit and 8-line function requirements.
"""

from typing import Dict, List
from datetime import datetime, timezone

from app.logging_config import central_logger
from .enhanced_auth_core import SecuritySession

logger = central_logger.get_logger(__name__)


class SessionCleanupManager:
    """Manages session cleanup and maintenance operations."""
    
    def __init__(self, active_sessions: Dict[str, SecuritySession]):
        """Initialize session cleanup manager."""
        self.active_sessions = active_sessions
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count removed."""
        now = datetime.now(timezone.utc)
        expired_sessions = self._find_expired_sessions(now)
        
        for session_id in expired_sessions:
            self._remove_expired_session(session_id)
        
        return len(expired_sessions)
    
    def _find_expired_sessions(self, current_time: datetime) -> List[str]:
        """Find all expired session IDs."""
        return [
            session_id for session_id, session in self.active_sessions.items()
            if current_time > session.expires_at
        ]
    
    def _remove_expired_session(self, session_id: str) -> None:
        """Remove expired session from active sessions."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Removed expired session {session_id}")
    
    def cleanup_by_user(self, user_id: str) -> int:
        """Clean up all sessions for a specific user."""
        user_sessions = self._get_user_session_ids(user_id)
        
        for session_id in user_sessions:
            self._remove_user_session(session_id)
        
        return len(user_sessions)
    
    def _get_user_session_ids(self, user_id: str) -> List[str]:
        """Get session IDs for a specific user."""
        return [
            session_id for session_id, session in self.active_sessions.items()
            if session.user_id == user_id
        ]
    
    def _remove_user_session(self, session_id: str) -> None:
        """Remove a user session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Removed user session {session_id}")
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up sessions older than specified hours."""
        cutoff_time = self._calculate_age_cutoff(max_age_hours)
        old_sessions = self._find_old_sessions(cutoff_time)
        self._remove_old_sessions(old_sessions)
        return len(old_sessions)
    
    def _calculate_age_cutoff(self, max_age_hours: int) -> datetime:
        """Calculate cutoff time for old sessions."""
        cutoff_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return cutoff_time.replace(hour=cutoff_time.hour - max_age_hours)
    
    def _remove_old_sessions(self, old_sessions: List[str]) -> None:
        """Remove all old sessions from the list."""
        for session_id in old_sessions:
            self._remove_old_session(session_id)
    
    def _find_old_sessions(self, cutoff_time: datetime) -> List[str]:
        """Find sessions older than cutoff time."""
        return [
            session_id for session_id, session in self.active_sessions.items()
            if session.created_at < cutoff_time
        ]
    
    def _remove_old_session(self, session_id: str) -> None:
        """Remove an old session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Removed old session {session_id}")


class SessionMetricsCollector:
    """Collects metrics and analytics for sessions."""
    
    def __init__(self, active_sessions: Dict[str, SecuritySession]):
        """Initialize metrics collector."""
        self.active_sessions = active_sessions
    
    def get_session_statistics(self) -> Dict[str, int]:
        """Get comprehensive session statistics."""
        return {
            "total_sessions": len(self.active_sessions),
            "active_sessions": self._count_active_sessions(),
            "suspicious_sessions": self._count_suspicious_sessions(),
            "expired_sessions": self._count_expired_sessions()
        }
    
    def _count_active_sessions(self) -> int:
        """Count active sessions."""
        return len([
            s for s in self.active_sessions.values()
            if s.status.value == "active"
        ])
    
    def _count_suspicious_sessions(self) -> int:
        """Count suspicious sessions."""
        return len([
            s for s in self.active_sessions.values()
            if s.status.value == "suspicious"
        ])
    
    def _count_expired_sessions(self) -> int:
        """Count expired sessions."""
        now = datetime.now(timezone.utc)
        return len([
            s for s in self.active_sessions.values()
            if now > s.expires_at
        ])
    
    def get_user_session_counts(self) -> Dict[str, int]:
        """Get session counts per user."""
        user_counts = {}
        
        for session in self.active_sessions.values():
            user_id = session.user_id
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        
        return user_counts
    
    def get_session_health_metrics(self) -> Dict[str, float]:
        """Get session health metrics."""
        total_sessions = len(self.active_sessions)
        if total_sessions == 0:
            return {"health_score": 1.0, "suspicious_ratio": 0.0}
        
        suspicious_count = self._count_suspicious_sessions()
        suspicious_ratio = suspicious_count / total_sessions
        health_score = max(0.0, 1.0 - suspicious_ratio)
        
        return {
            "health_score": health_score,
            "suspicious_ratio": suspicious_ratio
        }


class SessionUtilities:
    """Utility functions for session operations."""
    
    @staticmethod
    def is_session_valid_format(session_id: str) -> bool:
        """Check if session ID has valid format."""
        if not session_id or not isinstance(session_id, str):
            return False
        
        if len(session_id) < 32:
            return False
        
        return session_id.replace('-', '').replace('_', '').isalnum()
    
    @staticmethod
    def extract_session_summary(session: SecuritySession) -> Dict[str, str]:
        """Extract summary information from session."""
        return {
            "id": session.session_id[:8] + "...",
            "user": session.user_id,
            "status": session.status.value,
            "age": str(datetime.now(timezone.utc) - session.created_at)
        }
    
    @staticmethod
    def format_session_duration(session: SecuritySession) -> str:
        """Format session duration as human-readable string."""
        duration = datetime.now(timezone.utc) - session.created_at
        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m"
        
        return f"{int(minutes)}m"
    
    @staticmethod
    def get_session_risk_factors(session: SecuritySession) -> List[str]:
        """Get risk factors for a session."""
        risk_factors = []
        
        if not session.security_flags.get("is_trusted_ip", False):
            risk_factors.append("untrusted_ip")
        
        if session.security_flags.get("security_issues"):
            risk_factors.append("security_issues")
        
        return risk_factors