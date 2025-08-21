"""
Security compliance auditors and scoring logic.
Contains all auditor implementations and compliance calculation functionality.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

from netra_backend.app.logging_config import central_logger
# NOTE: Temporarily commented out - these modules need to be moved to auth_integration
# from netra_backend.app.auth_integration.enhanced_auth_security import enhanced_auth_security
# from netra_backend.app.auth_integration.api_key_manager import api_key_manager
enhanced_auth_security = None  # Placeholder until consolidation complete
api_key_manager = None  # Placeholder until consolidation complete
from netra_backend.app.security.audit_findings import SecurityFinding, SecuritySeverity, SecurityCategory

logger = central_logger.get_logger(__name__)


class SecurityAuditor(ABC):
    """Base class for security auditors."""
    
    @abstractmethod
    async def audit(self) -> List[SecurityFinding]:
        """Perform security audit and return findings."""
        pass
    
    @abstractmethod
    def get_category(self) -> SecurityCategory:
        """Get the security category this auditor covers."""
        pass
    
    def _create_security_finding(self, id: str, title: str, description: str,
                               severity: SecuritySeverity, category: SecurityCategory,
                               cwe_id: str, owasp_category: str, recommendation: str,
                               evidence: Dict[str, Any]) -> SecurityFinding:
        """Helper to create SecurityFinding objects."""
        return SecurityFinding(id=id, title=title, description=description, severity=severity,
                             category=category, cwe_id=cwe_id, owasp_category=owasp_category,
                             recommendation=recommendation, evidence=evidence, timestamp=datetime.now(timezone.utc))


class AuthenticationAuditor(SecurityAuditor):
    """Auditor for authentication security."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit authentication security."""
        findings = []
        auth_status = enhanced_auth_security.get_security_status()
        self._check_failed_attempts_threshold(findings)
        self._check_lockout_duration(findings)
        self._check_excessive_failed_logins(findings, auth_status)
        return findings
    
    def _check_failed_attempts_threshold(self, findings: List[SecurityFinding]) -> None:
        """Check for weak authentication settings."""
        if enhanced_auth_security.max_failed_attempts <= 5:
            return
        findings.append(self._create_failed_attempts_finding())
    
    def _create_failed_attempts_finding(self) -> SecurityFinding:
        """Create finding for high failed attempts threshold."""
        return self._build_failed_attempts_security_finding()
    
    def _build_failed_attempts_security_finding(self) -> SecurityFinding:
        """Build security finding for failed attempts threshold."""
        current_threshold = enhanced_auth_security.max_failed_attempts
        description = f"Max failed attempts set to {current_threshold}, recommended <= 5"
        return self._create_security_finding(
            "AUTH001", "High Failed Login Attempt Threshold", description,
            SecuritySeverity.MEDIUM, SecurityCategory.AUTHENTICATION, "CWE-307",
            "A02:2021 - Cryptographic Failures", "Reduce max_failed_attempts to 5 or lower",
            {"current_threshold": current_threshold}
        )
    
    def _check_lockout_duration(self, findings: List[SecurityFinding]) -> None:
        """Check lockout duration configuration."""
        if enhanced_auth_security.lockout_duration.total_seconds() >= 300:
            return
        findings.append(self._create_lockout_duration_finding())
    
    def _create_lockout_duration_finding(self) -> SecurityFinding:
        """Create finding for short lockout duration."""
        return self._create_security_finding(
            "AUTH002", "Short Account Lockout Duration",
            f"Lockout duration is {enhanced_auth_security.lockout_duration.total_seconds()} seconds, recommended >= 300",
            SecuritySeverity.LOW, SecurityCategory.AUTHENTICATION, "CWE-307",
            "A02:2021 - Cryptographic Failures", "Increase lockout duration to at least 5 minutes",
            {"current_duration": enhanced_auth_security.lockout_duration.total_seconds()}
        )
    
    def _check_excessive_failed_logins(self, findings: List[SecurityFinding], auth_status: Dict[str, Any]) -> None:
        """Check for excessive failed login attempts."""
        if auth_status["metrics"]["failed_logins"] <= 100:
            return
        findings.append(self._create_excessive_logins_finding(auth_status))
    
    def _create_excessive_logins_finding(self, auth_status: Dict[str, Any]) -> SecurityFinding:
        """Create finding for excessive failed logins."""
        return self._create_security_finding(
            "AUTH003", "High Number of Failed Login Attempts",
            f"Detected {auth_status['metrics']['failed_logins']} failed login attempts",
            SecuritySeverity.HIGH, SecurityCategory.AUTHENTICATION, "CWE-307",
            "A07:2021 - Identification and Authentication Failures", "Investigate potential brute force attacks and implement additional monitoring",
            auth_status["metrics"]
        )
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.AUTHENTICATION


class ApiSecurityAuditor(SecurityAuditor):
    """Auditor for API security."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit API security."""
        findings = []
        api_metrics = api_key_manager.get_security_metrics()
        self._check_expired_keys(findings, api_metrics)
        self._check_rotation_needed(findings, api_metrics)
        self._check_keys_per_user(findings, api_metrics)
        return findings
    
    def _check_expired_keys(self, findings: List[SecurityFinding], api_metrics: Dict[str, Any]) -> None:
        """Check for expired keys that haven't been cleaned up."""
        if api_metrics["expired_keys"] == 0:
            return
        findings.append(self._create_expired_keys_finding(api_metrics))
    
    def _create_expired_keys_finding(self, api_metrics: Dict[str, Any]) -> SecurityFinding:
        """Create finding for expired API keys."""
        return self._create_security_finding(
            "API001", "Expired API Keys Not Cleaned Up",
            f"Found {api_metrics['expired_keys']} expired API keys",
            SecuritySeverity.MEDIUM, SecurityCategory.API_SECURITY, "CWE-613",
            "A02:2021 - Cryptographic Failures", "Implement automated cleanup of expired API keys",
            api_metrics
        )
    
    def _check_rotation_needed(self, findings: List[SecurityFinding], api_metrics: Dict[str, Any]) -> None:
        """Check for keys needing rotation."""
        if api_metrics["rotation_needed"] == 0:
            return
        findings.append(self._create_rotation_needed_finding(api_metrics))
    
    def _create_rotation_needed_finding(self, api_metrics: Dict[str, Any]) -> SecurityFinding:
        """Create finding for keys needing rotation."""
        return self._create_security_finding(
            "API002", "API Keys Need Rotation",
            f"{api_metrics['rotation_needed']} API keys are approaching expiration",
            SecuritySeverity.LOW, SecurityCategory.API_SECURITY, "CWE-344",
            "A02:2021 - Cryptographic Failures", "Rotate API keys before they expire",
            {"rotation_candidates": api_key_manager.get_rotation_candidates()}
        )
    
    def _check_keys_per_user(self, findings: List[SecurityFinding], api_metrics: Dict[str, Any]) -> None:
        """Check for users with too many API keys."""
        if api_metrics["average_keys_per_user"] <= 5:
            return
        findings.append(self._create_keys_per_user_finding(api_metrics))
    
    def _create_keys_per_user_finding(self, api_metrics: Dict[str, Any]) -> SecurityFinding:
        """Create finding for high API keys per user."""
        return self._create_security_finding(
            "API003", "High Average API Keys Per User",
            f"Average of {api_metrics['average_keys_per_user']:.1f} keys per user",
            SecuritySeverity.LOW, SecurityCategory.API_SECURITY, "CWE-250",
            "A01:2021 - Broken Access Control", "Review API key usage patterns and implement key limits",
            api_metrics
        )
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.API_SECURITY


class SessionManagementAuditor(SecurityAuditor):
    """Auditor for session management security."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit session management security."""
        findings = []
        auth_status = enhanced_auth_security.get_security_status()
        self._check_active_sessions(findings, auth_status)
        self._check_session_timeout(findings)
        return findings
    
    def _check_active_sessions(self, findings: List[SecurityFinding], auth_status: Dict[str, Any]) -> None:
        """Check for too many active sessions."""
        if auth_status["active_sessions"] <= 1000:
            return
        findings.append(self._create_active_sessions_finding(auth_status))
    
    def _create_active_sessions_finding(self, auth_status: Dict[str, Any]) -> SecurityFinding:
        """Create finding for high number of active sessions."""
        return self._create_security_finding(
            "SESS001", "High Number of Active Sessions",
            f"Found {auth_status['active_sessions']} active sessions",
            SecuritySeverity.MEDIUM, SecurityCategory.SESSION_MANAGEMENT, "CWE-613",
            "A07:2021 - Identification and Authentication Failures", "Implement session cleanup and monitor for unusual session patterns",
            {"active_sessions": auth_status["active_sessions"]}
        )
    
    def _check_session_timeout(self, findings: List[SecurityFinding]) -> None:
        """Check session timeout configuration."""
        if enhanced_auth_security.session_timeout.total_seconds() <= 28800:
            return
        findings.append(self._create_session_timeout_finding())
    
    def _create_session_timeout_finding(self) -> SecurityFinding:
        """Create finding for long session timeout."""
        return self._create_security_finding(
            "SESS002", "Long Session Timeout",
            f"Session timeout is {enhanced_auth_security.session_timeout.total_seconds()} seconds",
            SecuritySeverity.LOW, SecurityCategory.SESSION_MANAGEMENT, "CWE-613",
            "A07:2021 - Identification and Authentication Failures", "Consider reducing session timeout for better security",
            {"timeout_seconds": enhanced_auth_security.session_timeout.total_seconds()}
        )
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.SESSION_MANAGEMENT


class ConfigurationAuditor(SecurityAuditor):
    """Auditor for security configuration."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit security configuration."""
        findings = []
        from netra_backend.app.config import settings
        self._check_debug_mode(findings, settings)
        self._check_jwt_secret(findings, settings)
        return findings
    
    def _check_debug_mode(self, findings: List[SecurityFinding], settings: Any) -> None:
        """Check if running in debug mode in non-development environments."""
        if not (hasattr(settings, 'debug') and settings.debug and settings.environment != "development"):
            return
        findings.append(self._create_debug_mode_finding(settings))
    
    def _create_debug_mode_finding(self, settings: Any) -> SecurityFinding:
        """Create finding for debug mode in production."""
        return self._create_security_finding(
            "CONF001", "Debug Mode Enabled in Non-Development Environment",
            f"Debug mode is enabled in {settings.environment} environment",
            SecuritySeverity.HIGH, SecurityCategory.CONFIGURATION, "CWE-489",
            "A05:2021 - Security Misconfiguration", "Disable debug mode in production and staging environments",
            {"environment": settings.environment, "debug": settings.debug}
        )
    
    def _check_jwt_secret(self, findings: List[SecurityFinding], settings: Any) -> None:
        """Check for weak JWT secret."""
        if not (hasattr(settings, 'jwt_secret_key') and len(settings.jwt_secret_key) < 32):
            return
        findings.append(self._create_jwt_secret_finding(settings))
    
    def _create_jwt_secret_finding(self, settings: Any) -> SecurityFinding:
        """Create finding for weak JWT secret."""
        return self._create_security_finding(
            "CONF002", "Weak JWT Secret Key",
            f"JWT secret key length is {len(settings.jwt_secret_key)} characters",
            SecuritySeverity.CRITICAL, SecurityCategory.CRYPTOGRAPHY, "CWE-326",
            "A02:2021 - Cryptographic Failures", "Use a JWT secret key of at least 32 characters",
            {"key_length": len(settings.jwt_secret_key)}
        )
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.CONFIGURATION


# Import scoring functionality from dedicated module
from netra_backend.app.security.audit_scoring import compliance_score_calculator, security_recommendation_engine