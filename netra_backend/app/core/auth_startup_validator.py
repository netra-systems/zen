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
        logger.info("[U+1F510] SSOT AUTH VALIDATION STARTING")
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
        logger.info("[U+1F510] AUTH VALIDATION SUMMARY")
        logger.info(f" PASS:  Passed: {len(successes)}")
        logger.info(f" WARNING: [U+FE0F]  Warnings: {len(warnings)}")
        logger.info(f" FAIL:  Critical Failures: {len(critical_failures)}")
        
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
        """Validate JWT secret configuration using COORDINATED DECISION-MAKING with JWT manager."""
        result = AuthValidationResult(component=AuthComponent.JWT_SECRET, valid=False)
        
        try:
            # Use SSOT JWT secret manager for consistent validation
            from shared.jwt_secret_manager import get_jwt_secret_manager
            jwt_manager = get_jwt_secret_manager()
            
            # COORDINATED FIX: Use JWT manager's validation logic instead of duplicating it
            # This ensures both components make identical decisions about JWT secret validity
            jwt_secret = jwt_manager.get_jwt_secret()
            is_valid, validation_context = jwt_manager.validate_jwt_secret_for_environment(
                jwt_secret, self.environment
            )
            
            if not is_valid:
                result.error = validation_context.get('error', 'JWT secret validation failed')
                result.details = {
                    "environment": self.environment,
                    "validation_context": validation_context,
                    "debug_info": jwt_manager.get_debug_info()
                }
                
                # Log detailed validation failure for troubleshooting
                logger.warning(f"   JWT validation failed for {self.environment}: {result.error}")
                if validation_context.get('reason'):
                    logger.warning(f"   Reason: {validation_context['reason']}")
            else:
                result.valid = True
                logger.info(f"  [U+2713] JWT secret validated (length: {len(jwt_secret)})")
                logger.info(f"  [U+2713] Using coordinated JWT validation for {self.environment}")
                result.details = {
                    "environment": self.environment,
                    "validation_context": validation_context
                }
        
        except Exception as e:
            result.error = f"JWT validation error: {e}"
            logger.error(f"   FAIL:  JWT validation failed: {e}")
        
        self.validation_results.append(result)
    
    async def _validate_service_credentials(self) -> None:
        """
        Validate service-to-service authentication credentials with enhanced isolation.
        
        CRITICAL: SERVICE_SECRET has 173+ dependencies across the codebase.
        Missing or misconfigured SERVICE_SECRET causes:
        - 100% authentication failure (all users locked out)
        - Circuit breaker permanently open (no recovery)
        - Complete system unusable (no business value)
        
        See SERVICE_SECRET_DEPENDENCY_ANALYSIS_COMPREHENSIVE.md for full impact analysis.
        """
        result = AuthValidationResult(component=AuthComponent.SERVICE_CREDENTIALS, valid=False)
        
        try:
            # ENHANCED ISOLATION: Use coordinated environment variable resolution
            service_id = self._get_coordinated_env_var('SERVICE_ID')
            service_secret = self._get_coordinated_env_var('SERVICE_SECRET')
            
            # Check SERVICE_ID first
            if not service_id:
                result.error = "SERVICE_ID not configured - CRITICAL for inter-service auth"
                result.is_critical = True  # Always critical
                result.details = {
                    "impact": "No inter-service communication possible",
                    "affected_services": ["auth_service", "analytics_service"],
                    "recovery": "Set SERVICE_ID environment variable",
                    "env_resolution_attempted": self._get_env_resolution_debug('SERVICE_ID')
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
                    "recovery": "Set SERVICE_SECRET environment variable immediately",
                    "env_resolution_attempted": self._get_env_resolution_debug('SERVICE_SECRET')
                }
                logger.critical(" ALERT:  SERVICE_SECRET MISSING - SYSTEM WILL FAIL")
            else:
                # Enhanced SERVICE_SECRET validation with environment awareness
                is_valid, validation_context = self._validate_service_secret_for_environment(
                    service_secret, self.environment
                )
                
                if not is_valid:
                    result.error = validation_context.get('error', 'SERVICE_SECRET validation failed')
                    result.details = {
                        "validation_context": validation_context,
                        "recovery": "Configure a secure SERVICE_SECRET"
                    }
                    if validation_context.get('is_critical', True):
                        result.is_critical = True
                        logger.critical(f" ALERT:  SERVICE_SECRET VALIDATION FAILED: {result.error}")
                else:
                    result.valid = True
                    logger.info(f"  [U+2713] SERVICE_SECRET validated (length: {len(service_secret)})")
                    result.details = {
                        "validation_context": validation_context,
                        "service_id": service_id[:8] + "..." if len(service_id) > 8 else service_id
                    }
        
        except Exception as e:
            result.error = f"Service credentials validation error: {e}"
            result.is_critical = True
            result.details = {
                "exception": str(e),
                "recovery": "Check environment configuration and SERVICE_SECRET format"
            }
        
        self.validation_results.append(result)
    
    async def _validate_auth_service_url(self) -> None:
        """Validate auth service URL configuration with enhanced isolation."""
        result = AuthValidationResult(component=AuthComponent.AUTH_SERVICE_URL, valid=False)
        
        try:
            # ENHANCED ISOLATION: Use coordinated environment variable resolution
            auth_url = self._get_coordinated_env_var('AUTH_SERVICE_URL')
            auth_enabled = self._get_coordinated_env_var('AUTH_SERVICE_ENABLED')
            auth_enabled = (auth_enabled or 'true').lower() == 'true'
            
            if not auth_enabled and not self.is_production:
                # Auth can be disabled in development
                result.valid = True
                result.is_critical = False
                logger.info("   WARNING:  Auth service disabled (development mode)")
                result.details = {
                    "auth_enabled": False,
                    "environment": self.environment,
                    "env_resolution_debug": self._get_env_resolution_debug('AUTH_SERVICE_URL')
                }
            elif not auth_url:
                result.error = "AUTH_SERVICE_URL not configured - CRITICAL for inter-service auth"
                result.details = {
                    "env_resolution_attempted": self._get_env_resolution_debug('AUTH_SERVICE_URL'),
                    "recovery": "Set AUTH_SERVICE_URL environment variable"
                }
            else:
                # Enhanced URL validation with environment awareness
                is_valid, validation_context = self._validate_auth_service_url_for_environment(
                    auth_url, self.environment
                )
                
                if not is_valid:
                    result.error = validation_context.get('error', 'AUTH_SERVICE_URL validation failed')
                    result.details = {
                        "url": auth_url,
                        "validation_context": validation_context
                    }
                else:
                    result.valid = True
                    logger.info(f"  [U+2713] Auth service URL validated: {auth_url}")
                    result.details = {
                        "url": auth_url,
                        "validation_context": validation_context
                    }
        
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
                        logger.info(f"  [U+2713] OAuth credentials validated: {', '.join(providers)}")
                elif frontend_url and oauth_config.redirect_uri:
                    # Less strict validation in staging/dev - just warn
                    result.valid = True  # Don't fail on this in staging
                    providers = []
                    if has_google: providers.append("Google")
                    if has_github: providers.append("GitHub")
                    logger.warning(f"   WARNING:  OAuth redirect URI mismatch (non-critical in {self.environment}): {oauth_config.redirect_uri} vs {frontend_url}")
                    logger.info(f"  [U+2713] OAuth credentials present: {', '.join(providers)}")
                else:
                    result.valid = True
                    logger.info("  [U+2713] OAuth credentials present (redirect URI validation skipped)")
        
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
                    logger.info(f"  [U+2713] CORS configuration validated ({len(origins_list)} origins)")
        
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
                logger.info(f"  [U+2713] Token expiry validated (access: {access_minutes}m, refresh: {refresh_days}d)")
        
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
                logger.info(f"  [U+2713] Circuit breaker config validated (threshold: {failure_threshold}, timeout: {timeout}s)")
        
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
                logger.info(f"  [U+2713] Cache config validated ({status}, TTL: {cache_ttl}s)")
        
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


    def _get_coordinated_env_var(self, var_name: str) -> Optional[str]:
        """
        Enhanced environment variable resolution with isolation-aware fallbacks.
        
        This method provides coordinated resolution using SSOT IsolatedEnvironment
        with fallback capabilities to handle test isolation issues.
        """
        # Try IsolatedEnvironment first (preferred)
        value = self.env.get(var_name)
        if value:
            return value
        
        # Try environment-specific variations
        env_specific = f"{var_name}_{self.environment.upper()}"
        env_specific_value = self.env.get(env_specific)
        if env_specific_value:
            logger.info(f"Using environment-specific variable: {env_specific}")
            return env_specific_value
        
        # Last resort: check if variable exists in os.environ directly
        # This provides fallback for edge cases where IsolatedEnvironment
        # might not have captured all variables during test context
        import os
        direct_value = os.environ.get(var_name)
        if direct_value:
            logger.info(f"Using direct os.environ fallback for {var_name} (compatibility)")
            return direct_value
        
        return None
    
    def _get_env_resolution_debug(self, var_name: str) -> dict:
        """Get debug information about environment variable resolution attempts."""
        env_specific = f"{var_name}_{self.environment.upper()}"
        
        # Check direct os.environ access for debug info
        import os
        return {
            "isolated_env": bool(self.env.get(var_name)),
            "os_environ_direct": bool(os.environ.get(var_name)),
            "environment_specific": bool(self.env.get(env_specific)),
            "env_specific_key": env_specific,
            "current_environment": self.environment
        }
    
    def _validate_service_secret_for_environment(self, service_secret: str, environment: str) -> tuple:
        """
        Validate SERVICE_SECRET strength and suitability for specific environment.
        
        Returns:
            Tuple of (is_valid: bool, validation_context: dict)
        """
        if not service_secret:
            return False, {
                'error': 'No SERVICE_SECRET provided',
                'reason': 'empty_secret',
                'is_critical': True
            }
        
        # Determine test context for more lenient validation
        is_testing_context = environment.lower() in ["testing", "development", "test"]
        
        # Check minimum length
        min_length = 16 if is_testing_context else 32
        if len(service_secret) < min_length:
            return False, {
                'error': f'SERVICE_SECRET too short ({len(service_secret)} chars, minimum {min_length})',
                'reason': 'insufficient_length',
                'current_length': len(service_secret),
                'minimum_length': min_length,
                'is_critical': True
            }
        
        # Check for weak patterns
        weak_patterns = ['password', 'demo', 'example', '12345', 'admin', 'default', 'changeme']
        
        # In test environments, be more permissive with structured test strings
        if is_testing_context:
            truly_weak = ['password', 'demo', 'example', '12345', 'admin', 'default', 'changeme']
            if service_secret.lower() in truly_weak:
                return False, {
                    'error': f'SERVICE_SECRET is a weak default value: {service_secret[:10]}...',
                    'reason': 'weak_default_secret',
                    'is_critical': True
                }
        else:
            # Production/staging: stricter validation
            all_weak_patterns = weak_patterns + ['secret', 'test']
            if any(pattern in service_secret.lower() for pattern in all_weak_patterns):
                return False, {
                    'error': 'SERVICE_SECRET contains weak/default patterns',
                    'reason': 'weak_pattern_detected',
                    'is_critical': True
                }
        
        # Check entropy for production environments
        if environment.lower() in ["staging", "production"]:
            has_upper = any(c.isupper() for c in service_secret)
            has_lower = any(c.islower() for c in service_secret)
            has_digit = any(c.isdigit() for c in service_secret)
            
            # Accept hex strings OR mixed case strings
            is_hex_string = all(c in '0123456789abcdef' for c in service_secret)
            has_mixed_case = has_upper and has_lower and has_digit
            
            if not (is_hex_string or has_mixed_case):
                return False, {
                    'error': 'SERVICE_SECRET has insufficient entropy for production',
                    'reason': 'insufficient_entropy',
                    'recommendation': 'Use hex format OR mixed case with digits',
                    'is_critical': True
                }
        
        # Production-specific minimum length
        if environment.lower() == "production" and len(service_secret) < 64:
            return False, {
                'error': f'Production SERVICE_SECRET requires 64+ characters (current: {len(service_secret)})',
                'reason': 'production_length_requirement',
                'current_length': len(service_secret),
                'minimum_length': 64,
                'is_critical': True
            }
        
        # All validation passed
        return True, {
            'valid': True,
            'reason': 'service_secret_validation_passed',
            'secret_length': len(service_secret),
            'environment': environment,
            'is_testing_context': is_testing_context
        }
    
    def _validate_auth_service_url_for_environment(self, auth_url: str, environment: str) -> tuple:
        """
        Validate AUTH_SERVICE_URL format and security requirements for environment.
        
        Returns:
            Tuple of (is_valid: bool, validation_context: dict)
        """
        if not auth_url:
            return False, {
                'error': 'No AUTH_SERVICE_URL provided',
                'reason': 'empty_url'
            }
        
        # Basic URL format validation
        if not auth_url.startswith(('http://', 'https://')):
            return False, {
                'error': f'Invalid AUTH_SERVICE_URL format: {auth_url}',
                'reason': 'invalid_url_format',
                'expected_format': 'http:// or https://'
            }
        
        # Environment-specific security requirements
        if environment.lower() in ["staging", "production"]:
            if not auth_url.startswith('https://'):
                return False, {
                    'error': f'AUTH_SERVICE_URL must use HTTPS in {environment}',
                    'reason': 'https_required_for_production',
                    'current_url': auth_url,
                    'required_scheme': 'https://'
                }
        
        # Check for localhost/development URLs in production
        if environment.lower() == "production":
            dev_patterns = ['localhost', '127.0.0.1', '0.0.0.0', '.local', 'dev', 'test']
            if any(pattern in auth_url.lower() for pattern in dev_patterns):
                return False, {
                    'error': 'Development/localhost URLs not allowed in production',
                    'reason': 'development_url_in_production',
                    'current_url': auth_url,
                    'detected_patterns': [p for p in dev_patterns if p in auth_url.lower()]
                }
        
        # Check for well-formed URL structure
        try:
            from urllib.parse import urlparse
            parsed = urlparse(auth_url)
            if not parsed.netloc:
                return False, {
                    'error': 'AUTH_SERVICE_URL missing host/netloc',
                    'reason': 'invalid_url_structure',
                    'current_url': auth_url
                }
        except Exception as e:
            return False, {
                'error': f'AUTH_SERVICE_URL parsing failed: {str(e)}',
                'reason': 'url_parsing_error',
                'current_url': auth_url
            }
        
        # All validation passed
        return True, {
            'valid': True,
            'reason': 'auth_service_url_validation_passed',
            'url': auth_url,
            'environment': environment,
            'scheme': auth_url.split('://')[0],
            'is_https': auth_url.startswith('https://')
        }


async def validate_auth_startup() -> None:
    """
    Perform comprehensive auth validation at startup.
    Raises AuthValidationError if any critical validation fails.
    """
    validator = AuthStartupValidator()
    success, results = await validator.validate_all()
    
    if not success:
        critical_failures = [r for r in results if not r.valid and r.is_critical]
        error_messages = [f"{f.component.value}: {f.error}" for f in critical_failures]
        raise AuthValidationError(
            f"Critical auth validation failures: {'; '.join(error_messages)}"
        )
    
    logger.info("[U+1F510] All auth validations passed - system is secure")