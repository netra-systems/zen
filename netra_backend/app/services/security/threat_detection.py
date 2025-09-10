"""Threat Detection Module - SSOT Security Implementation

This module provides threat detection functionality for the Netra platform.
Following SSOT principles, this is the canonical implementation for threat detection.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Security Infrastructure
- Business Goal: Risk Reduction & Security Compliance
- Value Impact: Proactive threat detection to prevent security incidents
- Strategic Impact: Maintains platform security posture and customer trust
"""

import logging
import time
import hashlib
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from shared.isolated_environment import get_env
from netra_backend.app.services.security.data_sanitizer import SanitizationType

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high" 
    CRITICAL = "critical"


class ThreatType(Enum):
    """Types of threats that can be detected."""
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    BRUTE_FORCE = "brute_force"
    DDoS = "ddos"
    MALICIOUS_UPLOAD = "malicious_upload"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    RATE_LIMITING = "rate_limiting"
    AUTHENTICATION_BYPASS = "authentication_bypass"


@dataclass
class ThreatDetectionResult:
    """Result of threat detection analysis."""
    threat_detected: bool
    threat_type: Optional[ThreatType] = None
    threat_level: ThreatLevel = ThreatLevel.LOW
    confidence: float = 0.0
    description: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ThreatDetectionConfig:
    """Configuration for threat detection operations."""
    enable_sql_injection_detection: bool = True
    enable_xss_detection: bool = True
    enable_command_injection_detection: bool = True
    enable_path_traversal_detection: bool = True
    enable_brute_force_detection: bool = True
    enable_rate_limiting: bool = True
    
    # Detection sensitivity (0.0 to 1.0)
    detection_sensitivity: float = 0.7
    
    # Rate limiting thresholds
    max_requests_per_minute: int = 100
    max_failed_auth_attempts: int = 5
    
    # Pattern matching settings
    use_regex_patterns: bool = True
    use_ml_detection: bool = False  # Future enhancement
    
    # Response settings
    auto_block_critical_threats: bool = True
    log_all_detections: bool = True


class ThreatDetector:
    """Core threat detection engine."""
    
    def __init__(self, config: Optional[ThreatDetectionConfig] = None):
        """Initialize threat detector."""
        self.config = config or ThreatDetectionConfig()
        self._request_counts: Dict[str, List[float]] = defaultdict(list)
        self._failed_auth_attempts: Dict[str, List[float]] = defaultdict(list)
        
        # Compile threat detection patterns
        self._sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
            r"('|(\\')|(;)|(\-\-)|(\#))",
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bOR\b.*=.*)",
            r"(\bAND\b.*=.*)"
        ]
        
        self._xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"eval\s*\(",
            r"document\.cookie"
        ]
        
        self._command_injection_patterns = [
            r"(\||;|&|\$\(|\`)",
            r"(sh|bash|cmd|powershell)",
            r"(rm|del|format|fdisk)",
            r"(\.\./.*){2,}",
            r"(/etc/passwd|/etc/shadow)"
        ]
        
        self._path_traversal_patterns = [
            r"\.\.[\\/]",
            r"[\\/]\.\.[\\/]",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
            r"\.\.%2f",
            r"\.\.%5c"
        ]
    
    async def detect_threats(self, 
                           input_data: str, 
                           client_ip: Optional[str] = None,
                           user_id: Optional[str] = None,
                           request_type: str = "unknown") -> ThreatDetectionResult:
        """
        Analyze input for potential security threats.
        
        Args:
            input_data: The data to analyze for threats
            client_ip: Client IP address for rate limiting
            user_id: User ID for tracking
            request_type: Type of request being analyzed
            
        Returns:
            ThreatDetectionResult with detection details
        """
        try:
            # Check for SQL injection
            if self.config.enable_sql_injection_detection:
                sql_result = self._check_sql_injection(input_data)
                if sql_result.threat_detected:
                    return sql_result
            
            # Check for XSS
            if self.config.enable_xss_detection:
                xss_result = self._check_xss(input_data)
                if xss_result.threat_detected:
                    return xss_result
            
            # Check for command injection
            if self.config.enable_command_injection_detection:
                cmd_result = self._check_command_injection(input_data)
                if cmd_result.threat_detected:
                    return cmd_result
            
            # Check for path traversal
            if self.config.enable_path_traversal_detection:
                path_result = self._check_path_traversal(input_data)
                if path_result.threat_detected:
                    return path_result
            
            # Check rate limiting if client IP provided
            if client_ip and self.config.enable_rate_limiting:
                rate_result = self._check_rate_limiting(client_ip)
                if rate_result.threat_detected:
                    return rate_result
            
            # No threats detected
            return ThreatDetectionResult(
                threat_detected=False,
                description="No threats detected",
                confidence=1.0 - self.config.detection_sensitivity
            )
            
        except Exception as e:
            logger.error(f"Error during threat detection: {e}")
            return ThreatDetectionResult(
                threat_detected=False,
                description=f"Threat detection error: {str(e)}"
            )
    
    def _check_sql_injection(self, input_data: str) -> ThreatDetectionResult:
        """Check for SQL injection patterns."""
        matches = []
        input_lower = input_data.lower()
        
        for pattern in self._sql_injection_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                matches.append(pattern)
        
        if matches:
            return ThreatDetectionResult(
                threat_detected=True,
                threat_type=ThreatType.SQL_INJECTION,
                threat_level=ThreatLevel.HIGH,
                confidence=min(0.9, len(matches) * 0.3),
                description=f"SQL injection patterns detected: {len(matches)} matches",
                evidence={"patterns": matches, "input_sample": input_data[:100]},
                recommended_action="Block request and sanitize input"
            )
        
        return ThreatDetectionResult(threat_detected=False)
    
    def _check_xss(self, input_data: str) -> ThreatDetectionResult:
        """Check for XSS attack patterns."""
        matches = []
        
        for pattern in self._xss_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                matches.append(pattern)
        
        if matches:
            return ThreatDetectionResult(
                threat_detected=True,
                threat_type=ThreatType.XSS_ATTACK,
                threat_level=ThreatLevel.HIGH,
                confidence=min(0.9, len(matches) * 0.35),
                description=f"XSS attack patterns detected: {len(matches)} matches",
                evidence={"patterns": matches, "input_sample": input_data[:100]},
                recommended_action="Sanitize input and encode output"
            )
        
        return ThreatDetectionResult(threat_detected=False)
    
    def _check_command_injection(self, input_data: str) -> ThreatDetectionResult:
        """Check for command injection patterns."""
        matches = []
        
        for pattern in self._command_injection_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                matches.append(pattern)
        
        if matches:
            return ThreatDetectionResult(
                threat_detected=True,
                threat_type=ThreatType.COMMAND_INJECTION,
                threat_level=ThreatLevel.CRITICAL,
                confidence=min(0.95, len(matches) * 0.4),
                description=f"Command injection patterns detected: {len(matches)} matches",
                evidence={"patterns": matches, "input_sample": input_data[:100]},
                recommended_action="Block request immediately"
            )
        
        return ThreatDetectionResult(threat_detected=False)
    
    def _check_path_traversal(self, input_data: str) -> ThreatDetectionResult:
        """Check for path traversal patterns."""
        matches = []
        
        for pattern in self._path_traversal_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                matches.append(pattern)
        
        if matches:
            return ThreatDetectionResult(
                threat_detected=True,
                threat_type=ThreatType.PATH_TRAVERSAL,
                threat_level=ThreatLevel.HIGH,
                confidence=min(0.9, len(matches) * 0.45),
                description=f"Path traversal patterns detected: {len(matches)} matches",
                evidence={"patterns": matches, "input_sample": input_data[:100]},
                recommended_action="Block request and validate file paths"
            )
        
        return ThreatDetectionResult(threat_detected=False)
    
    def _check_rate_limiting(self, client_ip: str) -> ThreatDetectionResult:
        """Check for rate limiting violations."""
        current_time = time.time()
        time_window = 60  # 1 minute
        
        # Clean old entries
        self._request_counts[client_ip] = [
            t for t in self._request_counts[client_ip] 
            if current_time - t < time_window
        ]
        
        # Add current request
        self._request_counts[client_ip].append(current_time)
        
        request_count = len(self._request_counts[client_ip])
        
        if request_count > self.config.max_requests_per_minute:
            return ThreatDetectionResult(
                threat_detected=True,
                threat_type=ThreatType.RATE_LIMITING,
                threat_level=ThreatLevel.MEDIUM,
                confidence=0.9,
                description=f"Rate limit exceeded: {request_count} requests in {time_window}s",
                evidence={"request_count": request_count, "client_ip": client_ip},
                recommended_action="Apply rate limiting or temporary IP block"
            )
        
        return ThreatDetectionResult(threat_detected=False)
    
    def record_failed_auth_attempt(self, client_ip: str, user_id: Optional[str] = None) -> ThreatDetectionResult:
        """Record a failed authentication attempt and check for brute force."""
        current_time = time.time()
        time_window = 300  # 5 minutes
        
        # Clean old entries
        self._failed_auth_attempts[client_ip] = [
            t for t in self._failed_auth_attempts[client_ip]
            if current_time - t < time_window
        ]
        
        # Add current failed attempt
        self._failed_auth_attempts[client_ip].append(current_time)
        
        failed_count = len(self._failed_auth_attempts[client_ip])
        
        if failed_count >= self.config.max_failed_auth_attempts:
            return ThreatDetectionResult(
                threat_detected=True,
                threat_type=ThreatType.BRUTE_FORCE,
                threat_level=ThreatLevel.HIGH,
                confidence=0.85,
                description=f"Brute force attack detected: {failed_count} failed attempts in {time_window}s",
                evidence={
                    "failed_attempts": failed_count,
                    "client_ip": client_ip,
                    "user_id": user_id,
                    "time_window": time_window
                },
                recommended_action="Block IP temporarily and require additional authentication"
            )
        
        return ThreatDetectionResult(threat_detected=False)


# Initialize global threat detector
_threat_detector_config = ThreatDetectionConfig()
threat_detector = ThreatDetector(_threat_detector_config)


# Export all functionality
__all__ = [
    'ThreatLevel',
    'ThreatType',
    'ThreatDetectionResult',
    'ThreatDetectionConfig',
    'ThreatDetector',
    'threat_detector'
]