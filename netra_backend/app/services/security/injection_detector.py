"""
Injection Attack Detector - SSOT Security Implementation

This module provides injection attack detection functionality for the Netra platform.
Following SSOT principles, this is the canonical implementation for injection detection.

Business Value: Security/Internal - Risk Reduction & Security Compliance
Prevents SQL injection, XSS, and other injection attacks across all platform inputs.

CRITICAL: This is a minimal SSOT-compliant stub to resolve import errors.
Full implementation should follow CLAUDE.md SSOT patterns.
"""

import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from shared.isolated_environment import get_env


class InjectionType(Enum):
    """Types of injection attacks that can be detected."""
    SQL_INJECTION = "sql_injection"
    XSS_INJECTION = "xss_injection"
    COMMAND_INJECTION = "command_injection"
    LDAP_INJECTION = "ldap_injection"
    XPATH_INJECTION = "xpath_injection"
    HTML_INJECTION = "html_injection"
    JAVASCRIPT_INJECTION = "javascript_injection"
    NO_INJECTION = "no_injection"


@dataclass
class InjectionDetectionResult:
    """Result of injection attack detection."""
    is_safe: bool
    detected_injections: List[InjectionType]
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    sanitized_input: Optional[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class InjectionDetector:
    """
    SSOT Injection Attack Detector.
    
    This is the canonical implementation for all injection detection across the platform.
    """
    
    def __init__(self):
        """Initialize injection detector with SSOT environment."""
        self._env = get_env()
        self._detection_enabled = self._env.get("INJECTION_DETECTION_ENABLED", "true").lower() == "true"
        self._strict_mode = self._env.get("INJECTION_DETECTION_STRICT", "false").lower() == "true"
        
        # Common injection patterns
        self._sql_patterns = [
            r"(?i)(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            r"(?i)(\b(or|and)\s+\d+\s*=\s*\d+)",
            r"(?i)(\'\s*(or|and)\s+\')",
            r"(?i)(--|\#|\/\*|\*\/)",
            r"(?i)(\bxp_cmdshell\b)"
        ]
        
        self._xss_patterns = [
            r"(?i)(<script[^>]*>.*?</script>)",
            r"(?i)(javascript:)",
            r"(?i)(on\w+\s*=)",
            r"(?i)(<iframe[^>]*>)",
            r"(?i)(<object[^>]*>)",
            r"(?i)(<embed[^>]*>)"
        ]
        
        self._command_patterns = [
            r"(?i)(\||\|\||&&|;|`)",
            r"(?i)(\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig)\b)",
            r"(?i)(\$\(|\$\{)",
            r"(?i)(\.\.\/|\.\.\\)"
        ]
    
    def detect_injection(self, 
                        input_data: Union[str, Dict[str, Any]], 
                        context: str = "general") -> InjectionDetectionResult:
        """
        Detect injection attacks in input data.
        
        Args:
            input_data: Data to check for injection attacks
            context: Context of the input (e.g., "sql_query", "user_input", "url_param")
            
        Returns:
            Injection detection result
        """
        if not self._detection_enabled:
            return InjectionDetectionResult(
                is_safe=True,
                detected_injections=[],
                risk_level="LOW",
                sanitized_input=None,
                warnings=["Injection detection is disabled"],
                metadata={"context": context, "detection_enabled": False}
            )
        
        detected_injections = []
        warnings = []
        risk_level = "LOW"
        
        # Convert input to string for pattern matching
        if isinstance(input_data, dict):
            input_str = str(input_data)
        else:
            input_str = str(input_data)
        
        # Check for SQL injection
        if self._check_sql_injection(input_str):
            detected_injections.append(InjectionType.SQL_INJECTION)
            risk_level = "HIGH"
        
        # Check for XSS
        if self._check_xss_injection(input_str):
            detected_injections.append(InjectionType.XSS_INJECTION)
            if risk_level == "LOW":
                risk_level = "MEDIUM"
        
        # Check for command injection
        if self._check_command_injection(input_str):
            detected_injections.append(InjectionType.COMMAND_INJECTION)
            risk_level = "CRITICAL"
        
        # Determine if input is safe
        is_safe = len(detected_injections) == 0
        if not is_safe and self._strict_mode:
            risk_level = "CRITICAL"
        
        # Basic sanitization (expand as needed)
        sanitized_input = self._sanitize_input(input_str) if not is_safe else None
        
        return InjectionDetectionResult(
            is_safe=is_safe,
            detected_injections=detected_injections,
            risk_level=risk_level,
            sanitized_input=sanitized_input,
            warnings=warnings,
            metadata={
                "context": context,
                "input_length": len(input_str),
                "strict_mode": self._strict_mode,
                "detection_enabled": self._detection_enabled
            }
        )
    
    def _check_sql_injection(self, input_str: str) -> bool:
        """Check for SQL injection patterns."""
        for pattern in self._sql_patterns:
            if re.search(pattern, input_str):
                return True
        return False
    
    def _check_xss_injection(self, input_str: str) -> bool:
        """Check for XSS injection patterns."""
        for pattern in self._xss_patterns:
            if re.search(pattern, input_str):
                return True
        return False
    
    def _check_command_injection(self, input_str: str) -> bool:
        """Check for command injection patterns."""
        for pattern in self._command_patterns:
            if re.search(pattern, input_str):
                return True
        return False
    
    def _sanitize_input(self, input_str: str) -> str:
        """Basic input sanitization."""
        # Remove common dangerous characters
        sanitized = re.sub(r"[<>\"'&]", "", input_str)
        sanitized = re.sub(r"(--|#|\/\*|\*\/)", "", sanitized)
        return sanitized.strip()
    
    def validate_sql_query(self, query: str, allowed_operations: Optional[List[str]] = None) -> InjectionDetectionResult:
        """
        Validate SQL query for injection attacks.
        
        Args:
            query: SQL query to validate
            allowed_operations: List of allowed SQL operations
            
        Returns:
            Injection detection result
        """
        result = self.detect_injection(query, context="sql_query")
        
        if allowed_operations:
            # Check if query contains only allowed operations
            query_lower = query.lower()
            for operation in ["select", "insert", "update", "delete", "create", "alter", "drop"]:
                if operation in query_lower and operation not in [op.lower() for op in allowed_operations]:
                    result.detected_injections.append(InjectionType.SQL_INJECTION)
                    result.is_safe = False
                    result.risk_level = "HIGH"
                    result.warnings.append(f"Disallowed SQL operation detected: {operation}")
        
        return result


# SSOT Factory Function
def create_injection_detector() -> InjectionDetector:
    """
    SSOT factory function for creating injection detector instances.
    
    Returns:
        Configured injection detector
    """
    return InjectionDetector()


# Export SSOT interface
__all__ = [
    "InjectionDetector",
    "InjectionDetectionResult",
    "InjectionType", 
    "create_injection_detector"
]