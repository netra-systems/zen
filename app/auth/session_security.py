"""Session security and hijacking detection - MODULAR ARCHITECTURE.

Handles session hijacking detection and security analysis.
Follows 300-line limit and 8-line function requirements.
"""

from typing import List
from datetime import datetime, timezone, timedelta

from app.logging_config import central_logger
from .enhanced_auth_core import SecuritySession

logger = central_logger.get_logger(__name__)


class SessionSecurityChecker:
    """Handles session security analysis and hijacking detection."""
    
    def detect_session_hijacking(self, session: SecuritySession, current_ip: str, 
                                current_user_agent: str) -> bool:
        """Detect potential session hijacking."""
        if self._rapid_ip_change_detected(session, current_ip):
            return True
        
        if self._suspicious_user_agent_change(session, current_user_agent):
            return True
        
        return False
    
    def _rapid_ip_change_detected(self, session: SecuritySession, current_ip: str) -> bool:
        """Detect rapid IP address changes."""
        if session.ip_address == current_ip:
            return False
        
        time_since_creation = datetime.now(timezone.utc) - session.created_at
        return self._is_suspicious_timing(time_since_creation)
    
    def _is_suspicious_timing(self, time_since_creation: timedelta) -> bool:
        """Check if timing indicates suspicious activity."""
        return (time_since_creation > timedelta(minutes=1) and 
                time_since_creation < timedelta(minutes=5))
    
    def _suspicious_user_agent_change(self, session: SecuritySession, current_user_agent: str) -> bool:
        """Detect suspicious user agent changes."""
        if session.user_agent == current_user_agent:
            return False
        
        if self._is_reasonable_ua_change(session.user_agent, current_user_agent):
            return False
        
        return self._is_different_browser_family(session.user_agent, current_user_agent)
    
    def _is_reasonable_ua_change(self, old_ua: str, new_ua: str) -> bool:
        """Check if user agent change is reasonable."""
        old_parts = self._split_user_agent(old_ua)
        new_parts = self._split_user_agent(new_ua)
        
        if len(old_parts) > 0 and len(new_parts) > 0:
            return old_parts[0] == new_parts[0]
        
        return False
    
    def _split_user_agent(self, user_agent: str) -> List[str]:
        """Split user agent string into parts."""
        return user_agent.split()
    
    def _is_different_browser_family(self, old_ua: str, new_ua: str) -> bool:
        """Check if user agents represent different browser families."""
        old_browser = self._extract_browser_name(old_ua)
        new_browser = self._extract_browser_name(new_ua)
        
        return self._are_different_browsers(old_browser, new_browser)
    
    def _extract_browser_name(self, user_agent: str) -> str:
        """Extract browser name from user agent."""
        parts = self._split_user_agent(user_agent)
        return parts[0] if parts else ""
    
    def _are_different_browsers(self, old_browser: str, new_browser: str) -> bool:
        """Check if browsers are different and both valid."""
        return (old_browser != new_browser and 
                bool(old_browser) and bool(new_browser))


class SessionThreatAnalyzer:
    """Analyzes session threats and patterns."""
    
    def analyze_session_patterns(self, session: SecuritySession) -> List[str]:
        """Analyze session for threat patterns."""
        threats = []
        
        if self._has_multiple_location_access(session):
            threats.append("multiple_locations")
        
        if self._has_rapid_activity_changes(session):
            threats.append("rapid_activity")
        
        return threats
    
    def _has_multiple_location_access(self, session: SecuritySession) -> bool:
        """Check for access from multiple locations."""
        security_flags = session.security_flags
        return security_flags.get("security_issues", []).count("ip_mismatch") > 2
    
    def _has_rapid_activity_changes(self, session: SecuritySession) -> bool:
        """Check for rapid activity pattern changes."""
        time_diff = session.last_activity - session.created_at
        return time_diff < timedelta(minutes=1)
    
    def calculate_threat_level(self, session: SecuritySession) -> str:
        """Calculate threat level for session."""
        threat_patterns = self.analyze_session_patterns(session)
        threat_count = len(threat_patterns)
        
        if threat_count >= 3:
            return "high"
        elif threat_count >= 1:
            return "medium"
        
        return "low"
    
    def should_require_additional_auth(self, session: SecuritySession) -> bool:
        """Determine if additional authentication is required."""
        threat_level = self.calculate_threat_level(session)
        return threat_level in ["high", "medium"]


class SessionSecurityEnforcer:
    """Enforces security policies on sessions."""
    
    def __init__(self):
        """Initialize security enforcer."""
        self.threat_analyzer = SessionThreatAnalyzer()
    
    def enforce_security_policies(self, session: SecuritySession) -> List[str]:
        """Enforce security policies and return actions taken."""
        actions = []
        
        if self._should_escalate_security(session):
            actions.extend(self._escalate_session_security(session))
        
        if self._should_require_reauth(session):
            actions.append(self._require_reauthentication(session))
        
        return actions
    
    def _should_escalate_security(self, session: SecuritySession) -> bool:
        """Check if security should be escalated."""
        return self.threat_analyzer.calculate_threat_level(session) == "high"
    
    def _should_require_reauth(self, session: SecuritySession) -> bool:
        """Check if reauthentication should be required."""
        return self.threat_analyzer.should_require_additional_auth(session)
    
    def _escalate_session_security(self, session: SecuritySession) -> List[str]:
        """Escalate session security measures."""
        actions = []
        session.security_flags["security_escalated"] = True
        actions.append("security_escalated")
        return actions
    
    def _require_reauthentication(self, session: SecuritySession) -> str:
        """Require reauthentication for session."""
        session.security_flags["requires_reauth"] = True
        return "reauthentication_required"