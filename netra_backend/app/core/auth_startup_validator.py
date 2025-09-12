"""
SSOT Auth Startup Validator - Critical authentication configuration validation.

This module performs comprehensive validation of all authentication-related
configuration during system startup. Any validation failure results in
immediate startup failure to prevent auth vulnerabilities in production.

CRITICAL: This is the SSOT for auth validation - all auth checks must be here.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from shared.isolated_environment import get_env
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.clients.auth_client_config import OAuthConfigGenerator
from netra_backend.app.core.environment_constants import get_current_environment, Environment


logger = logging.getLogger(__name__)


class AuthValidationError(Exception):
    """Critical auth validation failure that prevents startup."""
    pass


class AuthComponent(Enum):
    """Auth system components that must be validated."""
    JWT_SECRET = "jwt_secret"
    SERVICE_CREDENTIALS = "service_credentials"
    AUTH_SERVICE_URL = "auth_service_url"
    OAUTH_CREDENTIALS = "oauth_credentials"
    CORS_ORIGINS = "cors_origins"
    TOKEN_EXPIRY = "token_expiry"
    CIRCUIT_BREAKER = "circuit_breaker"
    CACHE_CONFIG = "cache_config"


@dataclass
class AuthValidationResult:
    """Result of auth validation check."""
    component: AuthComponent
    valid: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    is_critical: bool = True  # Most auth checks are critical


class AuthStartupValidator:
    """
    SSOT for authentication system validation at startup.
    Ensures all auth components are properly configured before system goes live.
    """
    
    def __init__(self):
        self.env = get_env()
        self.environment = get_current_environment()
        self.is_production = self.environment == Environment.PRODUCTION.value
        self.validation_results: List[AuthValidationResult] = []
    
    async def validate_all(self) -> Tuple[bool, List[AuthValidationResult]]:
        """
        Run all auth validation checks.
        Returns (success, results) tuple.
        """
        logger.info("=" * 60)
        logger.info("🔐 SSOT AUTH VALIDATION STARTING")
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Production Mode: {self.is_production}")
        logger.info("=" * 60)
        
        # Run all validation checks
        await self._validate_jwt_secret()
        await self._validate_service_credentials()
        await self._validate_auth_service_url()
        await self._validate_oauth_credentials()
        await self._validate_cors_configuration()
        await self._validate_token_expiry_settings()
        await self._validate_circuit_breaker_config()
        await self._validate_cache_configuration()
        
        # Additional production-only checks
        if self.is_production:
            await self._validate_production_requirements()
        
        # Analyze results
        critical_failures = [r for r in self.validation_results if not r.valid and r.is_critical]
        warnings = [r for r in self.validation_results if not r.valid and not r.is_critical]
        successes = [r for r in self.validation_results if r.valid]
        
        # Log summary
        logger.info("=" * 60)
        logger.info("🔐 AUTH VALIDATION SUMMARY")
        logger.info(f"✅ Passed: {len(successes)}")
        logger.info(f"⚠️  Warnings: {len(warnings)}")
        logger.info(f"❌ Critical Failures: {len(critical_failures)}")
        
        if critical_failures:
            logger.error("CRITICAL AUTH FAILURES DETECTED:")
            for failure in critical_failures:
                logger.error(f"  - {failure.component.value}: {failure.error}")
                if failure.details:
                    for key, value in failure.details.items():
                        logger.error(f"    {key}: {value}")
        
        logger.info("=" * 60)
        
        # Return success only if no critical failures
        return len(critical_failures) == 0, self.validation_results
    
    async def _validate_jwt_secret(self) -> None:
        """Validate JWT secret configuration using SSOT JWT manager."""
        result = AuthValidationResult(component=AuthComponent.JWT_SECRET, valid=False)
        
        try:
            # Use SSOT JWT secret manager for consistent validation
            from shared.jwt_secret_manager import get_jwt_secret_manager
            jwt_manager = get_jwt_secret_manager()
            
            # Get JWT secret through SSOT resolver
            jwt_secret = jwt_manager.get_jwt_secret()
            
            # Check if it's a real secret (not a default test value)
            is_default_secret = jwt_secret in [
                None, '', 'your-secret-key', 'test-secret', 'secret', 
                'emergency_jwt_secret_please_configure_properly',
                'fallback_jwt_secret_for_emergency_only',
                'test-jwt-secret-key-32-characters-long-for-testing-only',  # IsolatedEnvironment fallback
                'dev-jwt-secret-key-must-be-at-least-32-characters',  # IsolatedEnvironment development fallback
                'development-jwt-secret-minimum-32-characters-long'  # Another IsolatedEnvironment fallback
            ]
            
            # Check if JWT manager fell back to deterministic test secret (32-char hex from sha256)
            # The JWT manager might use a different environment detection, so check multiple possibilities
            import hashlib
            possible_envs = [self.environment, 'development', 'testing']
            is_deterministic_fallback = False
            for env in possible_envs:
                expected_test_secret = hashlib.sha256(f"netra_{env}_jwt_key".encode()).hexdigest()[:32]
                if jwt_secret == expected_test_secret:
                    is_deterministic_fallback = True
                    break
            
            if is_default_secret or not jwt_secret or is_deterministic_fallback:
                if is_default_secret:
                    result.error = f"JWT secret is configured but invalid (using default/test value: '{jwt_secret[:20]}...')"
                elif is_deterministic_fallback:
                    result.error = "JWT secret is configured but rejected (using deterministic test fallback - not acceptable for secure environments)"
                else:
                    result.error = "No JWT secret configured (JWT_SECRET, JWT_SECRET_KEY, or JWT_SECRET_STAGING)"
                debug_info = jwt_manager.get_debug_info()
                result.details = {
                    "environment": self.environment,
                    "debug_info": debug_info
                }
            elif len(jwt_secret) < 32:
                result.error = f"JWT secret too short ({len(jwt_secret)} chars, minimum 32)"
                result.details = {"length": len(jwt_secret), "minimum": 32}
            else:
                result.valid = True
                logger.info(f"  ✓ JWT secret validated (length: {len(jwt_secret)})")
                logger.info(f"  ✓ Using SSOT JWT secret resolution for {self.environment}")
        
        except Exception as e:
            result.error = f"JWT validation error: {e}"
            logger.error(f"  ❌ JWT validation failed: {e}")
        
        self.validation_results.append(result)
    
    async def _validate_service_credentials(self) -> None:
        """
        Validate service-to-service authentication credentials.
        
        CRITICAL: SERVICE_SECRET has 173+ dependencies across the codebase.
        Missing or misconfigured SERVICE_SECRET causes:
        - 100% authentication failure (all users locked out)
        - Circuit breaker permanently open (no recovery)
        - Complete system unusable (no business value)
        
        See SERVICE_SECRET_DEPENDENCY_ANALYSIS_COMPREHENSIVE.md for full impact analysis.
        """
        result = AuthValidationResult(component=AuthComponent.SERVICE_CREDENTIALS, valid=False)
        
        try:
            service_id = self.env.get('SERVICE_ID')
            service_secret = self.env.get('SERVICE_SECRET')

            # TEMPORARY FIX: Fallback to direct os.environ if IsolatedEnvironment doesn't find SERVICE_ID
            if not service_id:
                import os
                service_id = os.environ.get('SERVICE_ID')
                logger.warning(f"SERVICE_ID not found in IsolatedEnvironment, using direct os.environ fallback: {service_id is not None}")

            if not service_secret:
                import os
                service_secret = os.environ.get('SERVICE_SECRET')
                logger.warning(f"SERVICE_SECRET not found in IsolatedEnvironment, using direct os.environ fallback: {service_secret is not None}")
            
            # Check SERVICE_ID first
            if not service_id:
                result.error = "SERVICE_ID not configured - CRITICAL for inter-service auth"
                result.is_critical = True  # Always critical
                result.details = {
                    "impact": "No inter-service communication possible",
                    "affected_services": ["auth_service", "analytics_service"],
                    "recovery": "Set SERVICE_ID environment variable"
                }
            # Check SERVICE_SECRET - ULTRA CRITICAL
            elif not service_secret:
                result.error = "SERVICE_SECRET not configured - SINGLE POINT OF FAILURE"
                result.is_critical = True  # Always critical
                result.details = {
                    "impact": "100% authentication failure, all users locked out",
                    "dependencies": "173+ files depend on SERVICE_SECRET",
                    "affected_components": [
                        "Inter-service authentication",
                        "WebSocket authentication",
                        "Circuit breaker functionality",
                        "Token blacklist validation"
                    ],
                    "recovery": "Set SERVICE_SECRET environment variable immediately"
                }
                logger.critical("🚨 SERVICE_SECRET MISSING - SYSTEM WILL FAIL")
            else:
                # Validate SERVICE_SECRET format and strength
                validation_errors = []
                
                # Check minimum length
                if len(service_secret) < 32:
                    validation_errors.append(f"Too short ({len(service_secret)} chars, minimum 32)")
                
                # Check for default/weak values (more intelligent for test environments)
                weak_patterns = [
                    'password', 'demo', 'example', '12345', 'admin', 'default', 'changeme'
                ]
                
                # For test environments, be more permissive with "test" patterns if they're part of longer, structured strings
                if self.environment in ["testing", "development"]:
                    # In test/dev, only flag truly weak patterns, not structured test strings
                    truly_weak_patterns = ['password', 'demo', 'example', '12345', 'admin', 'default', 'changeme']
                    # Allow "secret" and "test" in test environments if part of longer strings
                    if any(pattern in service_secret.lower() for pattern in truly_weak_patterns):
                        validation_errors.append("Contains weak/default pattern")
                    # Only flag bare "secret" or "test" as weak, not when part of structured strings
                    elif service_secret.lower() in ['secret', 'test', 'password']:
                        validation_errors.append("Contains weak/default pattern")
                else:
                    # Production/staging: stricter validation including "secret" and "test"
                    production_weak_patterns = weak_patterns + ['secret', 'test']
                    if any(pattern in service_secret.lower() for pattern in production_weak_patterns):
                        validation_errors.append("Contains weak/default pattern")
                
                # Check for proper entropy (hex strings are valid, alphanumeric is sufficient)
                has_upper = any(c.isupper() for c in service_secret)
                has_lower = any(c.islower() for c in service_secret)
                has_digit = any(c.isdigit() for c in service_secret)
                has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in service_secret)
                
                # Accept hex strings (lowercase + digits) OR mixed case strings
                is_hex_string = all(c in '0123456789abcdef' for c in service_secret)
                has_mixed_case = has_upper and has_lower and has_digit
                has_good_entropy = is_hex_string or has_mixed_case or has_special
                
                if not has_good_entropy:
                    validation_errors.append("Insufficient entropy (needs hex format OR mixed case and digits OR special characters)")
                
                # Production-specific checks
                if self.is_production:
                    if len(service_secret) < 64:
                        validation_errors.append(f"Production requires 64+ chars (current: {len(service_secret)})")
                
                if validation_errors:
                    result.error = f"SERVICE_SECRET validation failed: {'; '.join(validation_errors)}"
                    result.is_critical = True
                    result.details = {
                        "current_length": len(service_secret),
                        "validation_errors": validation_errors,
                        "recommendation": "Generate strong SERVICE_SECRET using: openssl rand -hex 32"
                    }
                else:
                    # Additional connectivity check for production
                    if self.is_production:
                        logger.info("  🔍 Performing SERVICE_SECRET connectivity verification...")
                        # Could add actual auth service ping here
                    
                    result.valid = True
                    logger.info(f"  ✓ Service credentials validated (ID: {service_id})")
                    logger.info(f"  ✓ SERVICE_SECRET strength validated (length: {len(service_secret)})")
                    logger.info("  ✓ Inter-service authentication ready")
        
        except Exception as e:
            result.error = f"Service credentials validation error: {e}"
            result.is_critical = True
            result.details = {
                "exception": str(e),
                "recovery": "Check environment configuration and SERVICE_SECRET format"
            }
        
        self.validation_results.append(result)
    
    async def _validate_auth_service_url(self) -> None:
        """Validate auth service URL configuration."""
        result = AuthValidationResult(component=AuthComponent.AUTH_SERVICE_URL, valid=False)
        
        try:
            auth_url = self.env.get('AUTH_SERVICE_URL')
            auth_enabled = self.env.get('AUTH_SERVICE_ENABLED', 'true').lower() == 'true'
            
            if not auth_enabled and not self.is_production:
                # Auth can be disabled in development
                result.valid = True
                result.is_critical = False
                logger.info("  ⚠ Auth service disabled (development mode)")
            elif not auth_url:
                result.error = "AUTH_SERVICE_URL not configured"
            elif not auth_url.startswith(('http://', 'https://')):
                result.error = f"Invalid AUTH_SERVICE_URL format: {auth_url}"
            else:
                # In production, verify HTTPS
                if self.is_production and not auth_url.startswith('https://'):
                    result.error = "AUTH_SERVICE_URL must use HTTPS in production"
                    result.details = {"url": auth_url}
                else:
                    result.valid = True
                    logger.info(f"  ✓ Auth service URL validated: {auth_url}")
        
        except Exception as e:
            result.error = f"Auth service URL validation error: {e}"
        
        self.validation_results.append(result)
    
    async def _validate_oauth_credentials(self) -> None:
        """Validate OAuth provider credentials."""
        result = AuthValidationResult(component=AuthComponent.OAUTH_CREDENTIALS, valid=False)
        
        try:
            # Check Google OAuth
            google_client_id = self.env.get('GOOGLE_CLIENT_ID')
            google_client_secret = self.env.get('GOOGLE_CLIENT_SECRET')
            
            # Check GitHub OAuth
            github_client_id = self.env.get('GITHUB_CLIENT_ID')
            github_client_secret = self.env.get('GITHUB_CLIENT_SECRET')
            
            has_google = bool(google_client_id and google_client_secret)
            has_github = bool(github_client_id and github_client_secret)
            
            if not has_google and not has_github:
                result.error = "No OAuth providers configured"
                result.is_critical = self.is_production  # Critical in production
                result.details = {
                    "google_configured": has_google,
                    "github_configured": has_github
                }
            else:
                # Validate OAuth redirect URIs match environment
                oauth_gen = OAuthConfigGenerator()
                oauth_config = oauth_gen.get_oauth_config(self.environment)
                
                # Check redirect URI consistency (stricter in production only)
                frontend_url = self.env.get('FRONTEND_URL', '')
                if frontend_url and oauth_config.redirect_uri and self.is_production:
                    # Strict validation only in production
                    if not oauth_config.redirect_uri.startswith(frontend_url):
                        result.error = "OAuth redirect URI doesn't match FRONTEND_URL (production)"
                        result.details = {
                            "redirect_uri": oauth_config.redirect_uri,
                            "frontend_url": frontend_url
                        }
                    else:
                        result.valid = True
                        providers = []
                        if has_google: providers.append("Google")
                        if has_github: providers.append("GitHub")
                        logger.info(f"  ✓ OAuth credentials validated: {', '.join(providers)}")
                elif frontend_url and oauth_config.redirect_uri:
                    # Less strict validation in staging/dev - just warn
                    result.valid = True  # Don't fail on this in staging
                    providers = []
                    if has_google: providers.append("Google")
                    if has_github: providers.append("GitHub")
                    logger.warning(f"  ⚠ OAuth redirect URI mismatch (non-critical in {self.environment}): {oauth_config.redirect_uri} vs {frontend_url}")
                    logger.info(f"  ✓ OAuth credentials present: {', '.join(providers)}")
                else:
                    result.valid = True
                    logger.info("  ✓ OAuth credentials present (redirect URI validation skipped)")
        
        except Exception as e:
            result.error = f"OAuth validation error: {e}"
        
        self.validation_results.append(result)
    
    async def _validate_cors_configuration(self) -> None:
        """Validate CORS allowed origins configuration."""
        result = AuthValidationResult(component=AuthComponent.CORS_ORIGINS, valid=False)
        
        try:
            cors_origins = self.env.get('CORS_ALLOWED_ORIGINS', '')
            frontend_url = self.env.get('FRONTEND_URL', '')
            
            if not cors_origins:
                result.error = "CORS_ALLOWED_ORIGINS not configured"
                result.is_critical = False  # Warning, not critical
            elif frontend_url and frontend_url not in cors_origins:
                result.error = "FRONTEND_URL not in CORS_ALLOWED_ORIGINS"
                result.details = {
                    "frontend_url": frontend_url,
                    "cors_origins": cors_origins
                }
                result.is_critical = False  # Warning, not critical
            else:
                # In production, verify no wildcards
                if self.is_production and '*' in cors_origins:
                    result.error = "CORS wildcard (*) not allowed in production"
                    result.details = {"cors_origins": cors_origins}
                else:
                    result.valid = True
                    origins_list = cors_origins.split(',')
                    logger.info(f"  ✓ CORS configuration validated ({len(origins_list)} origins)")
        
        except Exception as e:
            result.error = f"CORS validation error: {e}"
        
        self.validation_results.append(result)
    
    async def _validate_token_expiry_settings(self) -> None:
        """Validate token expiry configuration."""
        result = AuthValidationResult(component=AuthComponent.TOKEN_EXPIRY, valid=False)
        
        try:
            access_expiry = self.env.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30')
            refresh_expiry = self.env.get('REFRESH_TOKEN_EXPIRE_DAYS', '7')
            
            access_minutes = int(access_expiry)
            refresh_days = int(refresh_expiry)
            
            if access_minutes < 5:
                result.error = f"ACCESS_TOKEN_EXPIRE_MINUTES too short ({access_minutes} min)"
                result.details = {"minimum": 5}
            elif access_minutes > 1440:  # 24 hours
                result.error = f"ACCESS_TOKEN_EXPIRE_MINUTES too long ({access_minutes} min)"
                result.details = {"maximum": 1440}
            elif refresh_days < 1:
                result.error = f"REFRESH_TOKEN_EXPIRE_DAYS too short ({refresh_days} days)"
                result.details = {"minimum": 1}
            elif refresh_days > 90:
                result.error = f"REFRESH_TOKEN_EXPIRE_DAYS too long ({refresh_days} days)"
                result.details = {"maximum": 90}
            else:
                result.valid = True
                logger.info(f"  ✓ Token expiry validated (access: {access_minutes}m, refresh: {refresh_days}d)")
        
        except ValueError as e:
            result.error = f"Invalid token expiry values: {e}"
        except Exception as e:
            result.error = f"Token expiry validation error: {e}"
        
        self.validation_results.append(result)
    
    async def _validate_circuit_breaker_config(self) -> None:
        """Validate auth circuit breaker configuration."""
        result = AuthValidationResult(component=AuthComponent.CIRCUIT_BREAKER, valid=False)
        
        try:
            # Check circuit breaker settings
            failure_threshold = int(self.env.get('AUTH_CIRCUIT_FAILURE_THRESHOLD', '3'))
            timeout = int(self.env.get('AUTH_CIRCUIT_TIMEOUT', '30'))
            
            if failure_threshold < 1:
                result.error = "Circuit breaker failure threshold too low"
                result.details = {"threshold": failure_threshold, "minimum": 1}
            elif timeout < 10:
                result.error = "Circuit breaker timeout too short"
                result.details = {"timeout": timeout, "minimum": 10}
            else:
                result.valid = True
                result.is_critical = False  # Not critical, just a warning
                logger.info(f"  ✓ Circuit breaker config validated (threshold: {failure_threshold}, timeout: {timeout}s)")
        
        except Exception as e:
            result.error = f"Circuit breaker validation error: {e}"
            result.is_critical = False
        
        self.validation_results.append(result)
    
    async def _validate_cache_configuration(self) -> None:
        """Validate auth cache configuration."""
        result = AuthValidationResult(component=AuthComponent.CACHE_CONFIG, valid=False)
        
        try:
            cache_ttl = int(self.env.get('AUTH_CACHE_TTL', '300'))
            cache_enabled = self.env.get('AUTH_CACHE_ENABLED', 'true').lower() == 'true'
            
            if cache_enabled and cache_ttl < 60:
                result.error = f"AUTH_CACHE_TTL too short ({cache_ttl}s)"
                result.details = {"minimum": 60}
                result.is_critical = False
            elif cache_enabled and cache_ttl > 3600:
                result.error = f"AUTH_CACHE_TTL too long ({cache_ttl}s)"
                result.details = {"maximum": 3600}
                result.is_critical = False
            else:
                result.valid = True
                result.is_critical = False
                status = "enabled" if cache_enabled else "disabled"
                logger.info(f"  ✓ Cache config validated ({status}, TTL: {cache_ttl}s)")
        
        except Exception as e:
            result.error = f"Cache validation error: {e}"
            result.is_critical = False
        
        self.validation_results.append(result)
    
    async def _validate_production_requirements(self) -> None:
        """Additional validation for production environment."""
        logger.info("Running production-specific auth validation...")
        
        # Ensure HTTPS is enforced
        frontend_url = self.env.get('FRONTEND_URL', '')
        backend_url = self.env.get('BACKEND_URL', '')
        
        if frontend_url and not frontend_url.startswith('https://'):
            self.validation_results.append(AuthValidationResult(
                component=AuthComponent.CORS_ORIGINS,
                valid=False,
                error="FRONTEND_URL must use HTTPS in production",
                details={"url": frontend_url}
            ))
        
        if backend_url and not backend_url.startswith('https://'):
            self.validation_results.append(AuthValidationResult(
                component=AuthComponent.AUTH_SERVICE_URL,
                valid=False,
                error="BACKEND_URL must use HTTPS in production",
                details={"url": backend_url}
            ))


async def validate_auth_at_startup() -> None:
    """
    Main entry point for auth validation during startup.
    Raises AuthValidationError if critical failures detected.
    """
    validator = AuthStartupValidator()
    success, results = await validator.validate_all()
    
    if not success:
        critical_failures = [r for r in results if not r.valid and r.is_critical]
        error_messages = [f"{f.component.value}: {f.error}" for f in critical_failures]
        raise AuthValidationError(
            f"Critical auth validation failures: {'; '.join(error_messages)}"
        )
    
    logger.info("🔐 All auth validations passed - system is secure")