"""
Security audit findings types and enums for Netra AI Platform.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class SecuritySeverity(str, Enum):
    """Security finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityCategory(str, Enum):
    """Security finding categories."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    API_SECURITY = "api_security"
    SESSION_MANAGEMENT = "session_management"
    CRYPTOGRAPHY = "cryptography"
    CONFIGURATION = "configuration"
    INPUT_VALIDATION = "input_validation"
    DATA_PROTECTION = "data_protection"
    LOGGING_MONITORING = "logging_monitoring"
    VULNERABILITY_MANAGEMENT = "vulnerability_management"


@dataclass
class SecurityFinding:
    """Individual security finding."""
    id: str
    title: str
    description: str
    severity: SecuritySeverity
    category: SecurityCategory
    cwe_id: str
    owasp_category: str
    recommendation: str
    evidence: Dict[str, Any]
    timestamp: datetime