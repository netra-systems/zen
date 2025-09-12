"""
Session Security Manager - SSOT for Session Security Management

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Prevent session hijacking and unauthorized access
- Value Impact: Protects user sessions and prevents account takeover attacks
- Strategic Impact: Critical for maintaining user trust and regulatory compliance
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ThreatLevel(Enum):
    """Threat level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SessionAnomaly(Enum):
    """Types of session anomalies that can be detected."""
    UNUSUAL_LOCATION = "unusual_location"
    SUSPICIOUS_USER_AGENT = "suspicious_user_agent"
    RAPID_SESSION_CHANGES = "rapid_session_changes"
    CONCURRENT_SESSIONS = "concurrent_sessions"
    SESSION_REPLAY = "session_replay"
    PRIVILEGE_ESCALATION = "privilege_escalation"


@dataclass
class SessionSecurityResult:
    """Result of session security analysis."""
    is_secure: bool
    threat_level: ThreatLevel
    anomalies_detected: List[SessionAnomaly]
    analysis_timestamp: datetime
    session_metadata: Dict[str, Any]
    risk_score: float
    recommendations: List[str]


class SessionSecurityManager:
    """SSOT Session Security Manager for session analysis and protection.
    
    This class provides comprehensive session security monitoring and
    anomaly detection to prevent session-based attacks and unauthorized access.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the session security manager.
        
        Args:
            config: Optional configuration for security validation rules
        """
        self.config = config or self._get_default_config()
        self._anomaly_detection_rules = self._initialize_anomaly_rules()
        self._session_history: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("SessionSecurityManager initialized with anomaly detection")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default security configuration."""
        return {
            "max_concurrent_sessions": 3,
            "session_timeout_minutes": 30,
            "max_location_changes": 2,
            "suspicious_ua_patterns": ["bot", "crawler", "scanner"],
            "max_risk_score": 7.0,
            "enable_location_tracking": True,
            "enable_device_fingerprinting": True
        }
    
    def _initialize_anomaly_rules(self) -> Dict[str, Any]:
        """Initialize anomaly detection rules."""
        return {
            "location_change_threshold": 100,  # km
            "session_change_frequency": 5,  # changes per minute
            "concurrent_session_limit": self.config.get("max_concurrent_sessions", 3),
            "privilege_escalation_patterns": ["admin", "root", "superuser"]
        }
    
    def analyze_session_security(
        self,
        session_id: str,
        user_id: str,
        session_data: Dict[str, Any],
        request_context: Optional[Dict[str, Any]] = None
    ) -> SessionSecurityResult:
        """Analyze session security and detect anomalies.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier for the session
            session_data: Session data to analyze
            request_context: Additional request context for analysis
            
        Returns:
            SessionSecurityResult with security assessment
        """
        logger.debug(f"Analyzing session security for user: {user_id}")
        
        anomalies_detected = []
        session_metadata = {}
        risk_score = 0.0
        
        try:
            # Store session data for historical analysis
            self._store_session_data(user_id, session_id, session_data, request_context)
            
            # Extract session metadata
            session_metadata = self._extract_session_metadata(session_data, request_context)
            
            # Check for unusual location activity
            if self._detect_unusual_location(user_id, session_metadata):
                anomalies_detected.append(SessionAnomaly.UNUSUAL_LOCATION)
                risk_score += 3.0
            
            # Check for suspicious user agent
            if self._detect_suspicious_user_agent(session_metadata):
                anomalies_detected.append(SessionAnomaly.SUSPICIOUS_USER_AGENT)
                risk_score += 2.0
            
            # Check for rapid session changes
            if self._detect_rapid_session_changes(user_id):
                anomalies_detected.append(SessionAnomaly.RAPID_SESSION_CHANGES)
                risk_score += 4.0
            
            # Check for concurrent sessions
            if self._detect_concurrent_sessions(user_id):
                anomalies_detected.append(SessionAnomaly.CONCURRENT_SESSIONS)
                risk_score += 2.0
            
            # Check for session replay attacks
            if self._detect_session_replay(session_id, session_data):
                anomalies_detected.append(SessionAnomaly.SESSION_REPLAY)
                risk_score += 5.0
            
            # Check for privilege escalation
            if self._detect_privilege_escalation(session_data):
                anomalies_detected.append(SessionAnomaly.PRIVILEGE_ESCALATION)
                risk_score += 6.0
            
            # Determine threat level
            threat_level = self._calculate_threat_level(risk_score, anomalies_detected)
            
            # Generate recommendations
            recommendations = self._generate_security_recommendations(anomalies_detected)
            
            is_secure = risk_score <= self.config["max_risk_score"]
            
            logger.info(
                f"Session security analysis complete: secure={is_secure}, "
                f"anomalies={len(anomalies_detected)}, risk_score={risk_score:.2f}"
            )
            
            return SessionSecurityResult(
                is_secure=is_secure,
                threat_level=threat_level,
                anomalies_detected=anomalies_detected,
                analysis_timestamp=datetime.now(timezone.utc),
                session_metadata=session_metadata,
                risk_score=risk_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Session security analysis failed: {e}")
            
            return SessionSecurityResult(
                is_secure=False,
                threat_level=ThreatLevel.HIGH,
                anomalies_detected=[SessionAnomaly.SESSION_REPLAY],
                analysis_timestamp=datetime.now(timezone.utc),
                session_metadata={},
                risk_score=10.0,
                recommendations=["Session analysis failed - consider ending session"]
            )
    
    def _store_session_data(
        self,
        user_id: str,
        session_id: str,
        session_data: Dict[str, Any],
        request_context: Optional[Dict[str, Any]]
    ) -> None:
        """Store session data for historical analysis."""
        if user_id not in self._session_history:
            self._session_history[user_id] = []
        
        session_entry = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_data": session_data,
            "request_context": request_context or {}
        }
        
        # Keep only recent entries (last 100)
        self._session_history[user_id].append(session_entry)
        if len(self._session_history[user_id]) > 100:
            self._session_history[user_id] = self._session_history[user_id][-100:]
    
    def _extract_session_metadata(
        self,
        session_data: Dict[str, Any],
        request_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract metadata from session and request context."""
        metadata = {}
        
        # Extract from session data
        if "user_agent" in session_data:
            metadata["user_agent"] = session_data["user_agent"]
        if "ip_address" in session_data:
            metadata["ip_address"] = session_data["ip_address"]
        if "location" in session_data:
            metadata["location"] = session_data["location"]
        
        # Extract from request context
        if request_context:
            if "user_agent" in request_context:
                metadata["user_agent"] = request_context["user_agent"]
            if "client_ip" in request_context:
                metadata["ip_address"] = request_context["client_ip"]
        
        return metadata
    
    def _detect_unusual_location(self, user_id: str, session_metadata: Dict[str, Any]) -> bool:
        """Detect unusual location changes."""
        if not self.config.get("enable_location_tracking", True):
            return False
        
        current_location = session_metadata.get("location")
        if not current_location:
            return False
        
        # Check against historical locations
        user_history = self._session_history.get(user_id, [])
        if len(user_history) < 2:
            return False
        
        # Simple implementation - in reality would use geolocation
        recent_locations = [
            entry.get("session_data", {}).get("location")
            for entry in user_history[-5:]
            if entry.get("session_data", {}).get("location")
        ]
        
        # If current location is very different from recent ones
        return current_location not in recent_locations
    
    def _detect_suspicious_user_agent(self, session_metadata: Dict[str, Any]) -> bool:
        """Detect suspicious user agent patterns."""
        user_agent = session_metadata.get("user_agent", "").lower()
        if not user_agent:
            return False
        
        suspicious_patterns = self.config.get("suspicious_ua_patterns", [])
        return any(pattern in user_agent for pattern in suspicious_patterns)
    
    def _detect_rapid_session_changes(self, user_id: str) -> bool:
        """Detect rapid session changes."""
        user_history = self._session_history.get(user_id, [])
        if len(user_history) < 5:
            return False
        
        # Check last 5 sessions for rapid changes (within 1 minute)
        recent_sessions = user_history[-5:]
        timestamps = [
            datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            for entry in recent_sessions
        ]
        
        # If all sessions occurred within 1 minute
        time_span = (timestamps[-1] - timestamps[0]).total_seconds()
        return time_span < 60
    
    def _detect_concurrent_sessions(self, user_id: str) -> bool:
        """Detect concurrent sessions."""
        # Simple implementation - would need more sophisticated tracking
        user_history = self._session_history.get(user_id, [])
        if len(user_history) < 2:
            return False
        
        # Check for multiple different session IDs in recent history
        recent_sessions = user_history[-10:]
        session_ids = set(entry["session_id"] for entry in recent_sessions)
        
        return len(session_ids) > self._anomaly_detection_rules["concurrent_session_limit"]
    
    def _detect_session_replay(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Detect potential session replay attacks."""
        # Simple implementation - check for duplicate session patterns
        # In reality, would use more sophisticated replay detection
        return False
    
    def _detect_privilege_escalation(self, session_data: Dict[str, Any]) -> bool:
        """Detect privilege escalation attempts."""
        privileges = session_data.get("privileges", [])
        if not privileges:
            return False
        
        escalation_patterns = self._anomaly_detection_rules.get("privilege_escalation_patterns", [])
        return any(pattern in str(privileges).lower() for pattern in escalation_patterns)
    
    def _calculate_threat_level(self, risk_score: float, anomalies: List[SessionAnomaly]) -> ThreatLevel:
        """Calculate threat level based on risk score and anomalies."""
        if risk_score >= 8.0 or SessionAnomaly.PRIVILEGE_ESCALATION in anomalies:
            return ThreatLevel.CRITICAL
        elif risk_score >= 5.0 or SessionAnomaly.SESSION_REPLAY in anomalies:
            return ThreatLevel.HIGH
        elif risk_score >= 2.0 or len(anomalies) > 1:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW
    
    def _generate_security_recommendations(self, anomalies: List[SessionAnomaly]) -> List[str]:
        """Generate security recommendations based on detected anomalies."""
        recommendations = []
        
        if SessionAnomaly.UNUSUAL_LOCATION in anomalies:
            recommendations.append("Verify user location and consider additional authentication")
        
        if SessionAnomaly.SUSPICIOUS_USER_AGENT in anomalies:
            recommendations.append("Block suspicious user agents and review access patterns")
        
        if SessionAnomaly.RAPID_SESSION_CHANGES in anomalies:
            recommendations.append("Implement rate limiting for session changes")
        
        if SessionAnomaly.CONCURRENT_SESSIONS in anomalies:
            recommendations.append("Limit concurrent sessions and terminate older sessions")
        
        if SessionAnomaly.SESSION_REPLAY in anomalies:
            recommendations.append("Terminate session immediately and require re-authentication")
        
        if SessionAnomaly.PRIVILEGE_ESCALATION in anomalies:
            recommendations.append("Investigate privilege escalation and audit user permissions")
        
        if not recommendations:
            recommendations.append("Session security analysis passed - continue monitoring")
        
        return recommendations
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get session security metrics."""
        total_users = len(self._session_history)
        total_sessions = sum(len(sessions) for sessions in self._session_history.values())
        
        return {
            "manager_name": "SessionSecurityManager",
            "config": self.config,
            "total_users_tracked": total_users,
            "total_sessions_analyzed": total_sessions,
            "supported_anomalies": [anomaly.value for anomaly in SessionAnomaly],
            "threat_levels": [level.value for level in ThreatLevel]
        }


# Export for test compatibility
__all__ = [
    'SessionSecurityManager',
    'SessionSecurityResult',
    'SessionAnomaly',
    'ThreatLevel'
]