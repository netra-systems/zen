"""Core authentication security module - MODULAR ARCHITECTURE.

Core authentication result types, session management, and security metrics.
Follows 300-line limit and 8-line function requirements.
"""

from typing import Dict, Optional, List, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AuthenticationResult(str, Enum):
    """Authentication result types."""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    REQUIRES_MFA = "requires_mfa"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class SessionStatus(str, Enum):
    """Session status types."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"


@dataclass
class AuthenticationAttempt:
    """Track authentication attempts."""
    user_id: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    result: AuthenticationResult
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class SecuritySession:
    """Enhanced session with security tracking."""
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    status: SessionStatus
    security_flags: Dict[str, Any]
    csrf_token: str


class SecurityMetrics:
    """Track security metrics for monitoring."""
    
    def __init__(self):
        """Initialize security metrics."""
        self._reset_counters()
        self.reset_time = datetime.now(timezone.utc)
    
    def _reset_counters(self):
        """Reset all metric counters."""
        self.failed_login_attempts = 0
        self.successful_logins = 0
        self.blocked_attempts = 0
        self.suspicious_activities = 0
        self.session_hijacking_attempts = 0
        self.csrf_attempts = 0
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self.__init__()
    
    def get_security_score(self) -> float:
        """Calculate security health score (0-1)."""
        total_attempts = self._calculate_total_attempts()
        if total_attempts == 0:
            return 1.0
        
        success_rate = self._calculate_success_rate(total_attempts)
        threat_ratio = self._calculate_threat_ratio(total_attempts)
        
        return max(0.0, success_rate - (threat_ratio * 0.5))
    
    def _calculate_total_attempts(self) -> int:
        """Calculate total login attempts."""
        return self.failed_login_attempts + self.successful_logins
    
    def _calculate_success_rate(self, total_attempts: int) -> float:
        """Calculate success rate from attempts."""
        return self.successful_logins / total_attempts
    
    def _calculate_threat_ratio(self, total_attempts: int) -> float:
        """Calculate threat ratio from blocked attempts."""
        threats = self.blocked_attempts + self.suspicious_activities
        return threats / max(1, total_attempts)


class SecurityConfiguration:
    """Security configuration constants and settings."""
    
    def __init__(self):
        """Initialize security configuration."""
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.session_timeout = timedelta(hours=8)
        self.max_concurrent_sessions = 3
        self.ip_whitelist = self._load_ip_whitelist()
        self.trusted_networks = self._load_trusted_networks()
    
    def _load_ip_whitelist(self) -> List[str]:
        """Load IP whitelist from configuration."""
        return ["127.0.0.1", "::1"]  # localhost only for dev
    
    def _load_trusted_networks(self) -> List[str]:
        """Load trusted network ranges."""
        return ["10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12"]
