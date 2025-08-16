"""Session and IP security checker module.

Handles IP blocking, rate limiting, and session security checks.
Each function ≤8 lines, strong typing, security focused.
"""

from typing import Dict, List
from datetime import datetime, timezone, timedelta
from ipaddress import ip_address, ip_network

from app.logging_config import central_logger
from .enhanced_auth_core import AuthenticationAttempt, SecurityConfiguration

logger = central_logger.get_logger(__name__)


class SessionChecker:
    """Handles session security and IP management."""
    
    def __init__(self, config: SecurityConfiguration):
        """Initialize session checker."""
        self.config = config
        self.blocked_ips: Dict[str, datetime] = {}
        self.suspicious_users: Dict[str, datetime] = {}
        self.attempts_log: List[AuthenticationAttempt] = []
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked."""
        if not self._has_blocked_entry(ip_address):
            return False
        if self._is_block_expired(ip_address):
            self._remove_expired_block(ip_address)
            return False
        self._log_blocked_attempt(ip_address)
        return True
    
    def _has_blocked_entry(self, ip_address: str) -> bool:
        """Check if IP has blocked entry."""
        return ip_address in self.blocked_ips
    
    def _is_block_expired(self, ip_address: str) -> bool:
        """Check if IP block has expired."""
        return datetime.now(timezone.utc) >= self.blocked_ips[ip_address]
    
    def _remove_expired_block(self, ip_address: str):
        """Remove expired IP block."""
        del self.blocked_ips[ip_address]
    
    def is_user_suspended(self, user_id: str) -> bool:
        """Check if user is suspended."""
        if not self._has_suspension_entry(user_id):
            return False
        if self._is_suspension_expired(user_id):
            self._remove_expired_suspension(user_id)
            return False
        self._log_suspended_attempt(user_id)
        return True
    
    def _has_suspension_entry(self, user_id: str) -> bool:
        """Check if user has suspension entry."""
        return user_id in self.suspicious_users
    
    def _is_suspension_expired(self, user_id: str) -> bool:
        """Check if user suspension expired."""
        return datetime.now(timezone.utc) >= self.suspicious_users[user_id]
    
    def _remove_expired_suspension(self, user_id: str):
        """Remove expired user suspension."""
        del self.suspicious_users[user_id]
    
    def is_rate_limited(self, ip_address: str) -> bool:
        """Check if IP is rate limited."""
        recent_attempts = self._get_recent_ip_attempts(ip_address, 5)
        if len(recent_attempts) >= 10:
            self._apply_rate_limit_block(ip_address)
            return True
        return False
    
    def _get_recent_ip_attempts(self, ip_address: str, minutes: int) -> List[AuthenticationAttempt]:
        """Get recent attempts from IP."""
        cutoff_time = self._calculate_cutoff_time(minutes)
        return self._filter_ip_attempts(ip_address, cutoff_time)
    
    def _calculate_cutoff_time(self, minutes: int) -> datetime:
        """Calculate cutoff time for filtering attempts."""
        return datetime.now(timezone.utc) - timedelta(minutes=minutes)
    
    def _filter_ip_attempts(self, ip_address: str, cutoff_time: datetime) -> List[AuthenticationAttempt]:
        """Filter attempts by IP and time."""
        return [
            attempt for attempt in self.attempts_log
            if self._is_recent_ip_attempt(attempt, ip_address, cutoff_time)
        ]
    
    def _is_recent_ip_attempt(self, attempt: AuthenticationAttempt, ip: str, cutoff: datetime) -> bool:
        """Check if attempt is recent from IP."""
        return attempt.ip_address == ip and attempt.timestamp > cutoff
    
    def _apply_rate_limit_block(self, ip_address: str):
        """Apply rate limit block to IP."""
        self._block_ip(ip_address, 30)
        self._log_rate_limit_triggered(ip_address)
    
    def has_too_many_failures(self, user_id: str) -> bool:
        """Check if user has too many failures."""
        failed_attempts = self._get_user_failed_attempts(user_id, 60)
        if len(failed_attempts) >= self.config.max_failed_attempts:
            self._apply_failure_suspension(user_id)
            return True
        return False
    
    def _get_user_failed_attempts(self, user_id: str, minutes: int) -> List[AuthenticationAttempt]:
        """Get user's failed attempts."""
        cutoff_time = self._calculate_cutoff_time(minutes)
        return self._filter_user_failed_attempts(user_id, cutoff_time)
    
    def _filter_user_failed_attempts(self, user_id: str, cutoff_time: datetime) -> List[AuthenticationAttempt]:
        """Filter user failed attempts by time."""
        return [
            attempt for attempt in self.attempts_log
            if self._is_user_failed_attempt(attempt, user_id, cutoff_time)
        ]
    
    def _is_user_failed_attempt(self, attempt: AuthenticationAttempt, user_id: str, cutoff: datetime) -> bool:
        """Check if attempt is user failure."""
        return (attempt.user_id == user_id and 
                attempt.result.name == "FAILED" and 
                attempt.timestamp > cutoff)
    
    def _apply_failure_suspension(self, user_id: str):
        """Apply suspension for failures."""
        self._suspend_user(user_id, 15)
        self._log_max_failures(user_id)
    
    def is_trusted_ip(self, ip_address: str) -> bool:
        """Check if IP is trusted."""
        if self._is_whitelisted_ip(ip_address):
            return True
        try:
            ip = ip_address(ip_address)
            return self._is_in_trusted_networks(ip)
        except ValueError:
            self._log_invalid_ip(ip_address)
            return False
    
    def _is_whitelisted_ip(self, ip_address: str) -> bool:
        """Check if IP is in whitelist."""
        return ip_address in self.config.ip_whitelist
    
    def _is_in_trusted_networks(self, ip) -> bool:
        """Check if IP is in trusted networks."""
        for network_str in self.config.trusted_networks:
            if self._ip_in_network(ip, network_str):
                return True
        return False
    
    def _ip_in_network(self, ip, network_str: str) -> bool:
        """Check if IP is in network."""
        network = ip_network(network_str, strict=False)
        return ip in network
    
    def _block_ip(self, ip_address: str, minutes: int):
        """Block IP for duration."""
        block_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.blocked_ips[ip_address] = block_until
        logger.warning(f"Blocked IP {ip_address} until {block_until}")
    
    def _suspend_user(self, user_id: str, minutes: int):
        """Suspend user for duration."""
        suspend_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.suspicious_users[user_id] = suspend_until
        logger.warning(f"Suspended user {user_id} until {suspend_until}")
    
    def add_attempt(self, attempt: AuthenticationAttempt):
        """Add authentication attempt to log."""
        self.attempts_log.append(attempt)
        self._cleanup_old_attempts()
    
    def _cleanup_old_attempts(self):
        """Clean up old attempts from log."""
        cutoff_time = self._calculate_cleanup_cutoff()
        self.attempts_log = self._filter_valid_attempts(cutoff_time)
    
    def _calculate_cleanup_cutoff(self) -> datetime:
        """Calculate cutoff time for cleanup (24 hours)."""
        return datetime.now(timezone.utc) - timedelta(hours=24)
    
    def _filter_valid_attempts(self, cutoff_time: datetime) -> List[AuthenticationAttempt]:
        """Filter attempts that are still valid."""
        return [
            attempt for attempt in self.attempts_log 
            if attempt.timestamp > cutoff_time
        ]
    
    # Logging methods
    def _log_blocked_attempt(self, ip_address: str):
        """Log blocked IP attempt."""
        logger.warning(f"Authentication attempt from blocked IP: {ip_address}")
    
    def _log_suspended_attempt(self, user_id: str):
        """Log suspended user attempt."""
        logger.warning(f"Authentication attempt for suspended user: {user_id}")
    
    def _log_rate_limit_triggered(self, ip_address: str):
        """Log rate limit trigger."""
        logger.warning(f"Rate limiting triggered for IP: {ip_address}")
    
    def _log_max_failures(self, user_id: str):
        """Log max failures reached."""
        logger.warning(f"Max failed attempts reached for user: {user_id}")
    
    def _log_invalid_ip(self, ip_address: str):
        """Log invalid IP format."""
        logger.warning(f"Invalid IP address format: {ip_address}")