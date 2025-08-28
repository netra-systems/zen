"""
Core Security Module: Unified security infrastructure for the Netra platform.

This module provides security services including input validation, sanitization,
access control, and threat detection across all platform components.

Business Value Justification (BVJ):
- Segment: Enterprise (security requirements, compliance)
- Business Goal: Zero security incidents, SOC2 compliance
- Value Impact: Enterprise trust enables 50% pricing premium
- Revenue Impact: $25K MRR from enterprise accounts requiring security
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, field_validator


class SecurityLevel(str, Enum):
    """Security level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Types of security threats."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    RATE_LIMIT = "rate_limit"
    BRUTE_FORCE = "brute_force"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    MALICIOUS_INPUT = "malicious_input"


class SecurityContext(BaseModel):
    """Security context for request processing."""
    user_id: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    ip_address: str = "127.0.0.1"
    user_agent: Optional[str] = None
    authenticated: bool = False
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None


class SecurityEvent(BaseModel):
    """Security event record."""
    event_id: str
    threat_type: ThreatType
    severity: SecurityLevel
    source_ip: str
    user_id: Optional[str] = None
    endpoint: str
    payload: Dict[str, Any] = {}
    timestamp: datetime = datetime.now(timezone.utc)
    blocked: bool = True
    details: str = ""


class SecurityRule(BaseModel):
    """Security validation rule."""
    rule_id: str
    name: str
    pattern: str
    threat_type: ThreatType
    severity: SecurityLevel
    enabled: bool = True
    description: str = ""


class InputSanitizer:
    """Input sanitization and validation service."""
    
    # Common malicious patterns
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(union\s+select|union\s+all\s+select)",
        r"(\b(OR|AND)\s+1\s*=\s*1\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bxp_cmdshell\b|\bsp_executesql\b)"
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>"
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.\/",
        r"\.\.\\"
    ]
    
    def __init__(self):
        self._compiled_patterns = {
            ThreatType.SQL_INJECTION: [re.compile(p, re.IGNORECASE) for p in self.SQL_PATTERNS],
            ThreatType.XSS: [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS],
            ThreatType.MALICIOUS_INPUT: [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
        }
    
    def sanitize_string(self, value: str, max_length: int = 1000) -> str:
        """Sanitize string input by removing dangerous characters."""
        if not isinstance(value, str):
            return str(value)[:max_length]
        
        # Remove null bytes and control characters
        sanitized = value.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        
        # Truncate to max length
        sanitized = sanitized[:max_length]
        
        # HTML encode dangerous characters
        sanitized = (sanitized
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
        
        return sanitized.strip()
    
    def validate_input(self, value: str, threat_types: Optional[List[ThreatType]] = None) -> List[ThreatType]:
        """Validate input against security patterns and return detected threats."""
        if not value:
            return []
        
        threats = []
        check_types = threat_types or list(self._compiled_patterns.keys())
        
        for threat_type in check_types:
            patterns = self._compiled_patterns.get(threat_type, [])
            for pattern in patterns:
                if pattern.search(value):
                    threats.append(threat_type)
                    break
        
        return threats
    
    def is_safe_input(self, value: str, threat_types: Optional[List[ThreatType]] = None) -> bool:
        """Check if input is safe (no threats detected)."""
        return len(self.validate_input(value, threat_types)) == 0


class AccessController:
    """Access control and authorization service."""
    
    def __init__(self):
        self._user_permissions: Dict[str, Set[str]] = {}
        self._resource_permissions: Dict[str, Dict[str, Set[str]]] = {}
        self._admin_users: Set[str] = set()
    
    def grant_permission(self, user_id: str, resource: str, permission: str) -> None:
        """Grant permission to user for resource."""
        if user_id not in self._user_permissions:
            self._user_permissions[user_id] = set()
        
        if resource not in self._resource_permissions:
            self._resource_permissions[resource] = {}
        
        if user_id not in self._resource_permissions[resource]:
            self._resource_permissions[resource][user_id] = set()
        
        self._user_permissions[user_id].add(f"{resource}:{permission}")
        self._resource_permissions[resource][user_id].add(permission)
    
    def revoke_permission(self, user_id: str, resource: str, permission: str) -> None:
        """Revoke permission from user for resource."""
        if user_id in self._user_permissions:
            self._user_permissions[user_id].discard(f"{resource}:{permission}")
        
        if (resource in self._resource_permissions and 
            user_id in self._resource_permissions[resource]):
            self._resource_permissions[resource][user_id].discard(permission)
    
    def has_permission(self, user_id: str, resource: str, permission: str) -> bool:
        """Check if user has permission for resource."""
        # Admin users have all permissions
        if user_id in self._admin_users:
            return True
        
        # Check specific permission
        if user_id in self._user_permissions:
            return f"{resource}:{permission}" in self._user_permissions[user_id]
        
        return False
    
    def set_admin_user(self, user_id: str, is_admin: bool = True) -> None:
        """Set or remove admin status for user."""
        if is_admin:
            self._admin_users.add(user_id)
        else:
            self._admin_users.discard(user_id)
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for user."""
        return self._user_permissions.get(user_id, set()).copy()


class ThreatDetector:
    """Real-time threat detection and response service."""
    
    def __init__(self):
        self._security_events: List[SecurityEvent] = []
        self._rate_limits: Dict[str, Dict[str, datetime]] = {}
        self._blocked_ips: Set[str] = set()
        self._sanitizer = InputSanitizer()
    
    def analyze_request(self, 
                       source_ip: str, 
                       endpoint: str, 
                       payload: Dict[str, Any],
                       user_id: Optional[str] = None) -> List[SecurityEvent]:
        """Analyze incoming request for threats."""
        events = []
        
        # Check if IP is blocked
        if source_ip in self._blocked_ips:
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                threat_type=ThreatType.BRUTE_FORCE,
                severity=SecurityLevel.HIGH,
                source_ip=source_ip,
                user_id=user_id,
                endpoint=endpoint,
                payload=payload,
                blocked=True,
                details="Blocked IP address"
            )
            events.append(event)
        
        # Check rate limits
        if self._check_rate_limit(source_ip, endpoint):
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                threat_type=ThreatType.RATE_LIMIT,
                severity=SecurityLevel.MEDIUM,
                source_ip=source_ip,
                user_id=user_id,
                endpoint=endpoint,
                payload=payload,
                blocked=True,
                details="Rate limit exceeded"
            )
            events.append(event)
        
        # Analyze payload for malicious content
        threats = self._analyze_payload_threats(payload)
        for threat_type in threats:
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                threat_type=threat_type,
                severity=SecurityLevel.HIGH if threat_type in [ThreatType.SQL_INJECTION, ThreatType.XSS] else SecurityLevel.MEDIUM,
                source_ip=source_ip,
                user_id=user_id,
                endpoint=endpoint,
                payload=payload,
                blocked=True,
                details=f"Detected {threat_type.value} in payload"
            )
            events.append(event)
        
        # Store events
        self._security_events.extend(events)
        
        return events
    
    def _check_rate_limit(self, source_ip: str, endpoint: str, max_requests: int = 100, window_minutes: int = 1) -> bool:
        """Check if source IP exceeds rate limit for endpoint."""
        key = f"{source_ip}:{endpoint}"
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=window_minutes)
        
        if key not in self._rate_limits:
            self._rate_limits[key] = {}
        
        # Clean old entries
        self._rate_limits[key] = {
            timestamp: dt for timestamp, dt in self._rate_limits[key].items() 
            if dt > window_start
        }
        
        # Check current count
        current_count = len(self._rate_limits[key])
        
        if current_count >= max_requests:
            return True  # Rate limit exceeded
        
        # Record this request
        self._rate_limits[key][str(now.timestamp())] = now
        return False
    
    def _analyze_payload_threats(self, payload: Dict[str, Any]) -> List[ThreatType]:
        """Analyze payload for various threat types."""
        threats = set()
        
        def analyze_value(value: Any) -> None:
            if isinstance(value, str):
                detected = self._sanitizer.validate_input(value)
                threats.update(detected)
            elif isinstance(value, dict):
                for v in value.values():
                    analyze_value(v)
            elif isinstance(value, list):
                for item in value:
                    analyze_value(item)
        
        analyze_value(payload)
        return list(threats)
    
    def block_ip(self, ip_address: str, duration_hours: int = 24) -> None:
        """Block IP address for specified duration."""
        self._blocked_ips.add(ip_address)
        # In production, this would be stored in database with expiration
    
    def get_security_events(self, limit: int = 100) -> List[SecurityEvent]:
        """Get recent security events."""
        return self._security_events[-limit:] if self._security_events else []
    
    def _generate_event_id(self) -> str:
        """Generate unique security event ID."""
        return f"SEC_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"


class SecurityService:
    """Main security service coordinating all security functions."""
    
    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.access_controller = AccessController()
        self.threat_detector = ThreatDetector()
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize security service."""
        self._initialized = True
    
    def validate_and_sanitize_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize all input data."""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Validate for threats
                threats = self.sanitizer.validate_input(value)
                if threats:
                    # Log security event but continue with sanitized value
                    pass
                
                sanitized[key] = self.sanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self.validate_and_sanitize_input(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitizer.sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def check_request_security(self, 
                             source_ip: str, 
                             endpoint: str, 
                             payload: Dict[str, Any],
                             user_id: Optional[str] = None) -> bool:
        """Check if request passes security validation."""
        events = self.threat_detector.analyze_request(source_ip, endpoint, payload, user_id)
        
        # Block request if any high severity threats detected
        for event in events:
            if event.severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                return False
        
        return True
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get overall security service status."""
        recent_events = self.threat_detector.get_security_events(50)
        
        return {
            "initialized": self._initialized,
            "recent_events_count": len(recent_events),
            "blocked_ips_count": len(self.threat_detector._blocked_ips),
            "high_severity_events": sum(
                1 for event in recent_events 
                if event.severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]
            )
        }


# Global security service instance
security_service = SecurityService()


def get_security_service() -> SecurityService:
    """Get the global security service instance."""
    return security_service


# Export key components
__all__ = [
    "SecurityLevel",
    "ThreatType",
    "SecurityContext",
    "SecurityEvent",
    "SecurityRule",
    "InputSanitizer",
    "AccessController",
    "ThreatDetector",
    "SecurityService",
    "security_service",
    "get_security_service"
]