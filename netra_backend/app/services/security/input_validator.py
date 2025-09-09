"""
Input Validator - SSOT Import Alias for Existing Implementation

This module provides SSOT import compatibility by aliasing the existing
InputValidator implementation from the middleware security module.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Prevent injection attacks and malicious input processing
- Value Impact: Protects user data and system integrity from security threats
- Strategic Impact: Critical for maintaining trust and regulatory compliance
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# SSOT Import: Use existing InputValidator from security middleware
from netra_backend.app.middleware.security_middleware import InputValidator

# Additional types required by tests
class SecurityThreat(Enum):
    """Types of security threats detected in input."""
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    LDAP_INJECTION = "ldap_injection"
    XML_INJECTION = "xml_injection"
    SCRIPT_INJECTION = "script_injection"
    HTML_INJECTION = "html_injection"


class ThreatLevel(Enum):
    """Severity levels for security threats."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    threats_detected: List[SecurityThreat]
    threat_level: ThreatLevel
    sanitized_input: Optional[str]
    validation_errors: List[str]
    security_score: float  # 0.0 to 1.0
    recommendations: List[str]
    validation_timestamp: datetime


# Export for test compatibility
__all__ = [
    'InputValidator',
    'ValidationResult',
    'SecurityThreat', 
    'ThreatLevel'
]