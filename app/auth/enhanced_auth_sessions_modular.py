"""Session management module - MODULAR ARCHITECTURE.

Unified interface for session management using modular components.
Follows 300-line limit and 8-line function requirements.
"""

from typing import Dict, Any, Tuple, List, Optional

from app.logging_config import central_logger
from .enhanced_auth_core import SecuritySession, SecurityConfiguration
from .session_manager import SessionLifecycleManager
from .session_validation import SessionValidator
from .session_utils import SessionCleanupManager, SessionMetricsCollector

logger = central_logger.get_logger(__name__)


class AuthSessionManager:
    """Manages secure user authentication sessions with modular architecture."""
    
    def __init__(self, config: SecurityConfiguration):
        """Initialize session manager with modular components."""
        self.config = config
        self.active_sessions: Dict[str, SecuritySession] = {}
        self._initialize_managers()
    
    def _initialize_managers(self) -> None:
        """Initialize all modular managers."""
        self.lifecycle_manager = SessionLifecycleManager(self.config)
        self.lifecycle_manager.active_sessions = self.active_sessions
        
        self.validator = SessionValidator(self.active_sessions)
        self.cleanup_manager = SessionCleanupManager(self.active_sessions)
        self.metrics_collector = SessionMetricsCollector(self.active_sessions)
    
    def create_secure_session(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """Create a secure session with comprehensive tracking."""
        return self.lifecycle_manager.create_secure_session(user_id, ip_address, user_agent)
    
    def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> Tuple[bool, Optional[str]]:
        """Validate session with security checks."""
        return self.validator.validate_session(session_id, ip_address, user_agent)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information for monitoring."""
        return self.lifecycle_manager.get_session_info(session_id)
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count removed."""
        return self.cleanup_manager.cleanup_expired_sessions()
    
    def get_user_session_count(self, user_id: str) -> int:
        """Get count of active sessions for a user."""
        return self.lifecycle_manager.get_user_session_count(user_id)
    
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user and return count."""
        return self.lifecycle_manager.revoke_all_user_sessions(user_id)
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status for all sessions."""
        base_status = self.lifecycle_manager.get_security_status()
        expired_cleaned = self.cleanup_expired_sessions()
        base_status["expired_sessions_cleaned"] = expired_cleaned
        return base_status
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        return self.metrics_collector.get_session_statistics()
    
    def get_session_health_metrics(self) -> Dict[str, Any]:
        """Get session health metrics."""
        return self.metrics_collector.get_session_health_metrics()


# Backward compatibility - maintain the same interface
class EnhancedAuthSessionManager(AuthSessionManager):
    """Enhanced session manager with backward compatibility."""
    
    def handle_csp_violation(self, violation_report: Dict[str, Any]) -> None:
        """Handle CSP violation reports - compatibility method."""
        logger.warning(f"CSP Violation reported: {violation_report}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get security headers metrics - compatibility method."""
        return {
            "session_metrics": self.get_session_statistics(),
            "health_metrics": self.get_session_health_metrics()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status - compatibility method."""
        health_metrics = self.get_session_health_metrics()
        return {
            "status": self._determine_status_from_health(health_metrics["health_score"]),
            "health_score": health_metrics["health_score"],
            "details": self.get_security_status()
        }
    
    def _determine_status_from_health(self, health_score: float) -> str:
        """Determine status string from health score."""
        if health_score < 0.5:
            return "unhealthy"
        elif health_score < 0.8:
            return "degraded"
        return "healthy"