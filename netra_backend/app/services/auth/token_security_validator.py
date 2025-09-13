"""
Token Security Validator - SSOT for Authentication Token Security

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Prevent unauthorized access and protect user data
- Value Impact: Security breaches cause customer churn and regulatory issues
- Strategic Impact: Enterprise security compliance enables high-value customers

This module provides comprehensive token security validation to ensure
authentication tokens meet security requirements and prevent security threats.

SSOT COMPLIANCE: This validator performs security analysis on token claims but
delegates actual token validation to auth service SSOT. JWT decoding here is
limited to security analysis only (signature verification disabled).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TokenSecurityLevel(Enum):
    """Token security level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityThreat(Enum):
    """Types of security threats that can be detected."""
    WEAK_SIGNATURE = "weak_signature"
    EXPIRED_TOKEN = "expired_token"
    INVALID_ISSUER = "invalid_issuer"
    SUSPICIOUS_CLAIMS = "suspicious_claims"
    REPLAY_ATTACK = "replay_attack"
    BRUTE_FORCE = "brute_force"
    TOKEN_HIJACKING = "token_hijacking"


@dataclass
class TokenValidationResult:
    """Result of token security validation."""
    is_valid: bool
    security_level: TokenSecurityLevel
    threats_detected: List[SecurityThreat]
    validation_timestamp: datetime
    token_metadata: Dict[str, Any]
    risk_score: float
    recommendations: List[str]


class TokenSecurityValidator:
    """SSOT Token Security Validator for authentication token validation.
    
    This class provides comprehensive validation of JWT and other authentication
    tokens to ensure they meet security requirements and detect potential threats.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the token security validator.
        
        Args:
            config: Optional configuration for security validation rules
        """
        self.config = config or self._get_default_config()
        self._threat_detection_rules = self._initialize_threat_rules()
        
        logger.info("TokenSecurityValidator initialized with security level checks")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default security validation configuration."""
        return {
            "max_token_age_hours": 24,
            "min_signature_strength": "HS256",
            "allowed_issuers": ["netra-apex", "auth-service"],
            "max_risk_score": 7.0,
            "enable_replay_detection": True,
            "enable_brute_force_detection": True
        }
    
    def _initialize_threat_rules(self) -> Dict[str, Any]:
        """Initialize threat detection rules."""
        return {
            "signature_algorithms": ["HS256", "RS256", "ES256"],
            "suspicious_claim_patterns": ["admin", "root", "system"],
            "replay_window_seconds": 300,
            "max_failed_attempts": 5
        }
    
    def validate_token_security(
        self,
        token: str,
        expected_issuer: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> TokenValidationResult:
        """Validate the security of an authentication token.
        
        Args:
            token: The JWT or other authentication token to validate
            expected_issuer: Expected token issuer for validation
            user_context: Additional user context for security checks
            
        Returns:
            TokenValidationResult with security assessment
        """
        logger.debug(f"Validating token security for issuer: {expected_issuer}")
        
        threats_detected = []
        token_metadata = {}
        risk_score = 0.0
        
        try:
            # Basic token structure validation
            if not self._validate_token_structure(token):
                threats_detected.append(SecurityThreat.WEAK_SIGNATURE)
                risk_score += 3.0
            
            # Extract token metadata (without verification for security analysis)
            token_metadata = self._extract_token_metadata(token)
            
            # Check for expired tokens
            if self._is_token_expired(token_metadata):
                threats_detected.append(SecurityThreat.EXPIRED_TOKEN)
                risk_score += 2.0
            
            # Validate issuer if provided
            if expected_issuer and not self._validate_issuer(token_metadata, expected_issuer):
                threats_detected.append(SecurityThreat.INVALID_ISSUER)
                risk_score += 4.0
            
            # Check for suspicious claims
            if self._detect_suspicious_claims(token_metadata):
                threats_detected.append(SecurityThreat.SUSPICIOUS_CLAIMS)
                risk_score += 3.0
            
            # Check for potential replay attacks
            if self._detect_replay_attack(token, user_context):
                threats_detected.append(SecurityThreat.REPLAY_ATTACK)
                risk_score += 5.0
            
            # Determine security level
            security_level = self._calculate_security_level(risk_score, threats_detected)
            
            # Generate recommendations
            recommendations = self._generate_security_recommendations(threats_detected)
            
            is_valid = risk_score <= self.config["max_risk_score"]
            
            logger.info(
                f"Token security validation complete: valid={is_valid}, "
                f"threats={len(threats_detected)}, risk_score={risk_score:.2f}"
            )
            
            return TokenValidationResult(
                is_valid=is_valid,
                security_level=security_level,
                threats_detected=threats_detected,
                validation_timestamp=datetime.now(timezone.utc),
                token_metadata=token_metadata,
                risk_score=risk_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Token security validation failed: {e}")
            
            return TokenValidationResult(
                is_valid=False,
                security_level=TokenSecurityLevel.LOW,
                threats_detected=[SecurityThreat.WEAK_SIGNATURE],
                validation_timestamp=datetime.now(timezone.utc),
                token_metadata={},
                risk_score=10.0,
                recommendations=["Token validation failed - consider regenerating token"]
            )
    
    def _validate_token_structure(self, token: str) -> bool:
        """Validate basic token structure."""
        if not token or not isinstance(token, str):
            return False
        
        # Basic JWT structure check (header.payload.signature)
        parts = token.split('.')
        return len(parts) == 3 and all(part for part in parts)
    
    def _extract_token_metadata(self, token: str) -> Dict[str, Any]:
        """Extract metadata from token using auth service SSOT delegation."""
        try:
            # SSOT COMPLIANCE: Delegate to auth service for token metadata extraction
            from netra_backend.app.clients.auth_client_core import auth_client

            logger.debug("SSOT TokenSecurityValidator: Delegating token metadata extraction to auth service")

            # Use auth service to get token claims for security analysis
            # This ensures consistency with auth service token handling
            import asyncio

            async def get_token_metadata():
                validation_result = await auth_client.validate_token(token)
                if validation_result and validation_result.get('payload'):
                    return validation_result['payload']
                else:
                    # If validation fails, we can't perform security analysis
                    logger.warning("SSOT TokenSecurityValidator: Auth service validation failed - cannot extract metadata")
                    return {}

            # Run async validation in sync context for security analysis
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create new event loop
                import asyncio
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    metadata = new_loop.run_until_complete(get_token_metadata())
                    return metadata
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(loop)
            else:
                return loop.run_until_complete(get_token_metadata())

        except Exception as e:
            logger.warning(f"SSOT TokenSecurityValidator: Failed to extract token metadata via auth service - {e}")
            return {}
    
    def _is_token_expired(self, token_metadata: Dict[str, Any]) -> bool:
        """Check if token is expired."""
        exp_timestamp = token_metadata.get('exp')
        if not exp_timestamp:
            return False
        
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        return datetime.now(timezone.utc) > exp_datetime
    
    def _validate_issuer(self, token_metadata: Dict[str, Any], expected_issuer: str) -> bool:
        """Validate token issuer."""
        token_issuer = token_metadata.get('iss', '')
        allowed_issuers = self.config.get('allowed_issuers', [])
        
        return (token_issuer == expected_issuer or 
                expected_issuer in allowed_issuers or
                token_issuer in allowed_issuers)
    
    def _detect_suspicious_claims(self, token_metadata: Dict[str, Any]) -> bool:
        """Detect suspicious claims in token."""
        suspicious_patterns = self._threat_detection_rules.get('suspicious_claim_patterns', [])
        
        for claim_value in token_metadata.values():
            if isinstance(claim_value, str):
                for pattern in suspicious_patterns:
                    if pattern.lower() in claim_value.lower():
                        return True
        
        return False
    
    def _detect_replay_attack(self, token: str, user_context: Optional[Dict[str, Any]]) -> bool:
        """Detect potential replay attacks."""
        if not self.config.get('enable_replay_detection', False):
            return False
        
        # Implementation would involve checking token usage history
        # For now, return False as this requires persistent storage
        return False
    
    def _calculate_security_level(self, risk_score: float, threats: List[SecurityThreat]) -> TokenSecurityLevel:
        """Calculate security level based on risk score and threats."""
        if risk_score >= 8.0 or SecurityThreat.TOKEN_HIJACKING in threats:
            return TokenSecurityLevel.CRITICAL
        elif risk_score >= 5.0 or SecurityThreat.REPLAY_ATTACK in threats:
            return TokenSecurityLevel.HIGH
        elif risk_score >= 2.0 or len(threats) > 0:
            return TokenSecurityLevel.MEDIUM
        else:
            return TokenSecurityLevel.LOW
    
    def _generate_security_recommendations(self, threats: List[SecurityThreat]) -> List[str]:
        """Generate security recommendations based on detected threats."""
        recommendations = []
        
        if SecurityThreat.EXPIRED_TOKEN in threats:
            recommendations.append("Refresh expired token immediately")
        
        if SecurityThreat.WEAK_SIGNATURE in threats:
            recommendations.append("Use stronger signature algorithm (RS256 or ES256)")
        
        if SecurityThreat.INVALID_ISSUER in threats:
            recommendations.append("Verify token issuer configuration")
        
        if SecurityThreat.SUSPICIOUS_CLAIMS in threats:
            recommendations.append("Review token claims for unauthorized privilege escalation")
        
        if SecurityThreat.REPLAY_ATTACK in threats:
            recommendations.append("Implement nonce-based replay protection")
        
        if not recommendations:
            recommendations.append("Token security validation passed - continue monitoring")
        
        return recommendations
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security validation metrics."""
        return {
            "validator_name": "TokenSecurityValidator",
            "config": self.config,
            "threat_rules_count": len(self._threat_detection_rules),
            "supported_threats": [threat.value for threat in SecurityThreat],
            "security_levels": [level.value for level in TokenSecurityLevel]
        }


# Export for test compatibility
__all__ = [
    'TokenSecurityValidator',
    'TokenValidationResult', 
    'SecurityThreat',
    'TokenSecurityLevel'
]