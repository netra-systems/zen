"""
Security compliance auditors and scoring logic.
Contains all auditor implementations and compliance calculation functionality.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

from app.logging_config import central_logger
# NOTE: Temporarily commented out - these modules need to be moved to auth_integration
# from app.auth.enhanced_auth_security import enhanced_auth_security
# from app.auth.api_key_manager import api_key_manager
enhanced_auth_security = None  # Placeholder until consolidation complete
api_key_manager = None  # Placeholder until consolidation complete
from app.security.audit_findings import SecurityFinding, SecuritySeverity, SecurityCategory

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
        return SecurityFinding(
            id="AUTH001", title="High Failed Login Attempt Threshold",
            description=f"Max failed attempts set to {enhanced_auth_security.max_failed_attempts}, recommended <= 5",
            severity=SecuritySeverity.MEDIUM, category=SecurityCategory.AUTHENTICATION,
            cwe_id="CWE-307", owasp_category="A02:2021 - Cryptographic Failures",
            recommendation="Reduce max_failed_attempts to 5 or lower",
            evidence={"current_threshold": enhanced_auth_security.max_failed_attempts},
            timestamp=datetime.now(timezone.utc)
        )
    
    def _check_lockout_duration(self, findings: List[SecurityFinding]) -> None:
        """Check lockout duration configuration."""
        if enhanced_auth_security.lockout_duration.total_seconds() >= 300:
            return
        findings.append(self._create_lockout_duration_finding())
    
    def _create_lockout_duration_finding(self) -> SecurityFinding:
        """Create finding for short lockout duration."""
        return SecurityFinding(
            id="AUTH002", title="Short Account Lockout Duration",
            description=f"Lockout duration is {enhanced_auth_security.lockout_duration.total_seconds()} seconds, recommended >= 300",
            severity=SecuritySeverity.LOW, category=SecurityCategory.AUTHENTICATION,
            cwe_id="CWE-307", owasp_category="A02:2021 - Cryptographic Failures",
            recommendation="Increase lockout duration to at least 5 minutes",
            evidence={"current_duration": enhanced_auth_security.lockout_duration.total_seconds()},
            timestamp=datetime.now(timezone.utc)
        )
    
    def _check_excessive_failed_logins(self, findings: List[SecurityFinding], auth_status: Dict[str, Any]) -> None:
        """Check for excessive failed login attempts."""
        if auth_status["metrics"]["failed_logins"] <= 100:
            return
        findings.append(self._create_excessive_logins_finding(auth_status))
    
    def _create_excessive_logins_finding(self, auth_status: Dict[str, Any]) -> SecurityFinding:
        """Create finding for excessive failed logins."""
        return SecurityFinding(
            id="AUTH003", title="High Number of Failed Login Attempts",
            description=f"Detected {auth_status['metrics']['failed_logins']} failed login attempts",
            severity=SecuritySeverity.HIGH, category=SecurityCategory.AUTHENTICATION,
            cwe_id="CWE-307", owasp_category="A07:2021 - Identification and Authentication Failures",
            recommendation="Investigate potential brute force attacks and implement additional monitoring",
            evidence=auth_status["metrics"], timestamp=datetime.now(timezone.utc)
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
        return SecurityFinding(
            id="API001", title="Expired API Keys Not Cleaned Up",
            description=f"Found {api_metrics['expired_keys']} expired API keys",
            severity=SecuritySeverity.MEDIUM, category=SecurityCategory.API_SECURITY,
            cwe_id="CWE-613", owasp_category="A02:2021 - Cryptographic Failures",
            recommendation="Implement automated cleanup of expired API keys",
            evidence=api_metrics, timestamp=datetime.now(timezone.utc)
        )
    
    def _check_rotation_needed(self, findings: List[SecurityFinding], api_metrics: Dict[str, Any]) -> None:
        """Check for keys needing rotation."""
        if api_metrics["rotation_needed"] == 0:
            return
        findings.append(self._create_rotation_needed_finding(api_metrics))
    
    def _create_rotation_needed_finding(self, api_metrics: Dict[str, Any]) -> SecurityFinding:
        """Create finding for keys needing rotation."""
        return SecurityFinding(
            id="API002", title="API Keys Need Rotation",
            description=f"{api_metrics['rotation_needed']} API keys are approaching expiration",
            severity=SecuritySeverity.LOW, category=SecurityCategory.API_SECURITY,
            cwe_id="CWE-344", owasp_category="A02:2021 - Cryptographic Failures",
            recommendation="Rotate API keys before they expire",
            evidence={"rotation_candidates": api_key_manager.get_rotation_candidates()},
            timestamp=datetime.now(timezone.utc)
        )
    
    def _check_keys_per_user(self, findings: List[SecurityFinding], api_metrics: Dict[str, Any]) -> None:
        """Check for users with too many API keys."""
        if api_metrics["average_keys_per_user"] <= 5:
            return
        findings.append(self._create_keys_per_user_finding(api_metrics))
    
    def _create_keys_per_user_finding(self, api_metrics: Dict[str, Any]) -> SecurityFinding:
        """Create finding for high API keys per user."""
        return SecurityFinding(
            id="API003", title="High Average API Keys Per User",
            description=f"Average of {api_metrics['average_keys_per_user']:.1f} keys per user",
            severity=SecuritySeverity.LOW, category=SecurityCategory.API_SECURITY,
            cwe_id="CWE-250", owasp_category="A01:2021 - Broken Access Control",
            recommendation="Review API key usage patterns and implement key limits",
            evidence=api_metrics, timestamp=datetime.now(timezone.utc)
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
        return SecurityFinding(
            id="SESS001", title="High Number of Active Sessions",
            description=f"Found {auth_status['active_sessions']} active sessions",
            severity=SecuritySeverity.MEDIUM, category=SecurityCategory.SESSION_MANAGEMENT,
            cwe_id="CWE-613", owasp_category="A07:2021 - Identification and Authentication Failures",
            recommendation="Implement session cleanup and monitor for unusual session patterns",
            evidence={"active_sessions": auth_status["active_sessions"]},
            timestamp=datetime.now(timezone.utc)
        )
    
    def _check_session_timeout(self, findings: List[SecurityFinding]) -> None:
        """Check session timeout configuration."""
        if enhanced_auth_security.session_timeout.total_seconds() <= 28800:
            return
        findings.append(self._create_session_timeout_finding())
    
    def _create_session_timeout_finding(self) -> SecurityFinding:
        """Create finding for long session timeout."""
        return SecurityFinding(
            id="SESS002", title="Long Session Timeout",
            description=f"Session timeout is {enhanced_auth_security.session_timeout.total_seconds()} seconds",
            severity=SecuritySeverity.LOW, category=SecurityCategory.SESSION_MANAGEMENT,
            cwe_id="CWE-613", owasp_category="A07:2021 - Identification and Authentication Failures",
            recommendation="Consider reducing session timeout for better security",
            evidence={"timeout_seconds": enhanced_auth_security.session_timeout.total_seconds()},
            timestamp=datetime.now(timezone.utc)
        )
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.SESSION_MANAGEMENT


class ConfigurationAuditor(SecurityAuditor):
    """Auditor for security configuration."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit security configuration."""
        findings = []
        from app.config import settings
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
        return SecurityFinding(
            id="CONF001", title="Debug Mode Enabled in Non-Development Environment",
            description=f"Debug mode is enabled in {settings.environment} environment",
            severity=SecuritySeverity.HIGH, category=SecurityCategory.CONFIGURATION,
            cwe_id="CWE-489", owasp_category="A05:2021 - Security Misconfiguration",
            recommendation="Disable debug mode in production and staging environments",
            evidence={"environment": settings.environment, "debug": settings.debug},
            timestamp=datetime.now(timezone.utc)
        )
    
    def _check_jwt_secret(self, findings: List[SecurityFinding], settings: Any) -> None:
        """Check for weak JWT secret."""
        if not (hasattr(settings, 'jwt_secret_key') and len(settings.jwt_secret_key) < 32):
            return
        findings.append(self._create_jwt_secret_finding(settings))
    
    def _create_jwt_secret_finding(self, settings: Any) -> SecurityFinding:
        """Create finding for weak JWT secret."""
        return SecurityFinding(
            id="CONF002", title="Weak JWT Secret Key",
            description=f"JWT secret key length is {len(settings.jwt_secret_key)} characters",
            severity=SecuritySeverity.CRITICAL, category=SecurityCategory.CRYPTOGRAPHY,
            cwe_id="CWE-326", owasp_category="A02:2021 - Cryptographic Failures",
            recommendation="Use a JWT secret key of at least 32 characters",
            evidence={"key_length": len(settings.jwt_secret_key)},
            timestamp=datetime.now(timezone.utc)
        )
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.CONFIGURATION


# Import scoring functionality from dedicated module
from app.security.audit_scoring import compliance_score_calculator, security_recommendation_engine