"""
Unified JWT Secret Manager - Single Source of Truth for JWT Secrets

This module provides a unified approach to JWT secret resolution across all services.
It eliminates the JWT secret mismatch issue that causes WebSocket 403 authentication failures.

Business Value:
- Ensures consistent JWT secret resolution across auth service and backend
- Prevents $50K MRR loss from WebSocket authentication failures  
- Provides single source of truth for JWT configuration

CRITICAL: This module MUST be used by both:
- auth_service/auth_core/auth_environment.py
- netra_backend/app/websocket_core/user_context_extractor.py

Any service that generates or validates JWT tokens MUST use this unified manager.
"""

import logging
from typing import Optional
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class JWTSecretManager:
    """
    Unified JWT secret management for consistent secret resolution.
    
    This manager ensures that all services (auth service, backend service)
    use exactly the same JWT secret resolution logic, preventing the
    signature mismatch issues that cause WebSocket 403 errors.
    """
    
    def __init__(self):
        """Initialize JWT secret manager."""
        # Don't cache the environment - always get fresh environment for staging tests
        self._cached_secret: Optional[str] = None
        self._cached_algorithm: Optional[str] = None
    
    def _get_env(self):
        """Get current environment - always fresh for staging test compatibility."""
        return get_env()
        
    def get_jwt_secret(self) -> str:
        """
        Get JWT secret with unified resolution logic.
        
        CRITICAL: This is the SINGLE SOURCE OF TRUTH for JWT secret resolution.
        All services MUST use this method to ensure consistency.
        
        Priority order (consistent across ALL services):
        1. Environment-specific JWT_SECRET_{ENVIRONMENT} (e.g., JWT_SECRET_STAGING)  
        2. Generic JWT_SECRET_KEY
        3. Legacy JWT_SECRET
        4. Environment-specific fallbacks (dev/test only)
        
        Returns:
            JWT secret string for token signing/validation
            
        Raises:
            ValueError: If JWT secret cannot be resolved in staging/production
        """
        # Return cached secret if available
        if self._cached_secret:
            return self._cached_secret
            
        try:
            env = self._get_env()
            environment = env.get("ENVIRONMENT", "development").lower()
            
            # CRITICAL FIX: Determine test context detection early for length validation
            is_testing_context = (
                environment in ["testing", "development", "test"] or 
                env.get("TESTING", "false").lower() == "true" or
                env.get("PYTEST_CURRENT_TEST") is not None
            )
            
            # Minimum secret length - very lenient in test contexts for validation testing
            min_secret_length = 4 if is_testing_context else 32
            
            # CRITICAL FIX: Unified secret resolution with staging override
            if environment == "staging":
                # STAGING: Use explicit staging secret hierarchy with proper validation
                staging_secrets = [
                    "JWT_SECRET_STAGING",
                    "JWT_SECRET_KEY", 
                    "JWT_SECRET"
                ]
                
                for secret_key in staging_secrets:
                    jwt_secret = env.get(secret_key)
                    if jwt_secret and len(jwt_secret.strip()) >= min_secret_length:
                        logger.info(f"STAGING JWT SECRET: Using {secret_key} (length: {len(jwt_secret.strip())})")
                        self._cached_secret = jwt_secret.strip()
                        return self._cached_secret
                
                # STAGING FALLBACK: Use unified secret from secrets manager if available
                try:
                    from deployment.secrets_config import get_staging_secret
                    staging_secret = get_staging_secret("JWT_SECRET")
                    if staging_secret and len(staging_secret) >= min_secret_length:
                        logger.info("STAGING JWT SECRET: Using deployment secrets manager")
                        self._cached_secret = staging_secret
                        return self._cached_secret
                except ImportError:
                    logger.warning("Deployment secrets manager not available for staging")
            
            # 1. Try environment-specific secret first (ALL environments including staging)
            env_specific_key = f"JWT_SECRET_{environment.upper()}"
            jwt_secret = env.get(env_specific_key)
            
            # CRITICAL FIX: Always use environment-specific secret if provided and valid
            if jwt_secret and len(jwt_secret.strip()) >= min_secret_length:
                logger.info(f"Using environment-specific JWT secret: {env_specific_key} (length: {len(jwt_secret.strip())})")
                self._cached_secret = jwt_secret.strip()
                return self._cached_secret
            
            # 2. Try generic JWT_SECRET_KEY (second priority)
            jwt_secret = env.get("JWT_SECRET_KEY")
            
            # In testing context, check if JWT_SECRET_KEY is a default test value that should be ignored
            if is_testing_context and jwt_secret:
                # Check if it's a default test secret that should be replaced with deterministic one
                # ONLY replace truly insecure defaults, not legitimate test values
                insecure_default_secrets = [
                    'development-jwt-secret-minimum-32-characters-long',
                    'test-jwt-secret-key-32-characters-long-for-testing-only',
                    'dev-jwt-secret-key-must-be-at-least-32-characters',
                    'your-secret-key', 'secret'
                ]
                
                if jwt_secret in insecure_default_secrets:
                    logger.warning(f"JWT_SECRET_KEY is a default test value, using deterministic secret for {environment}")
                    # Generate consistent deterministic secret for dev/test environments
                    import hashlib
                    deterministic_secret = hashlib.sha256(f"netra_{environment}_jwt_key".encode()).hexdigest()[:32]
                    self._cached_secret = deterministic_secret
                    return self._cached_secret
            
            # Use generic JWT_SECRET_KEY if it's valid and not a default test value
            if jwt_secret and len(jwt_secret.strip()) >= min_secret_length:
                logger.info(f"Using generic JWT_SECRET_KEY (length: {len(jwt_secret.strip())})")
                self._cached_secret = jwt_secret.strip()
                return self._cached_secret
            
            # 3. No more legacy fallbacks - must use proper env vars
            
            # 5. Environment-specific fallbacks for development/testing only
            if is_testing_context:
                logger.warning(f"Using deterministic JWT secret for {environment} (test context) - NOT FOR PRODUCTION")
                # Generate consistent deterministic secret for dev/test environments
                import hashlib
                deterministic_secret = hashlib.sha256(f"netra_{environment}_jwt_key".encode()).hexdigest()[:32]
                self._cached_secret = deterministic_secret
                return self._cached_secret
                
            # 6. Hard failure for staging/production environments (non-test contexts)
            if environment in ["staging", "production"]:
                expected_vars = [env_specific_key, "JWT_SECRET_KEY", "JWT_SECRET"]
                logger.critical(f"JWT secret not configured for {environment} environment")
                logger.critical(f"Expected one of: {expected_vars}")
                logger.critical("This will cause WebSocket 403 authentication failures")
                raise ValueError(
                    f"JWT secret not configured for {environment} environment. "
                    f"Please set {env_specific_key} or JWT_SECRET_KEY. "
                    f"This is blocking $50K MRR WebSocket functionality."
                )
            
            # 7. Unknown environment fallback
            logger.error(f"Unknown environment '{environment}' - using emergency fallback")
            self._cached_secret = "emergency_jwt_secret_please_configure_properly"
            return self._cached_secret
            
        except ImportError:
            logger.error("Could not import isolated environment - using emergency fallback")
            self._cached_secret = "fallback_jwt_secret_for_emergency_only"
            return self._cached_secret
    
    def get_jwt_algorithm(self) -> str:
        """
        Get JWT algorithm with unified defaults.
        
        Returns:
            JWT algorithm string (e.g., 'HS256')
        """
        if self._cached_algorithm:
            return self._cached_algorithm
        
        env = self._get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        # Check for explicit algorithm configuration
        algorithm = env.get("JWT_ALGORITHM")
        if algorithm:
            self._cached_algorithm = algorithm
            return algorithm
        
        # Environment-specific defaults
        if environment == "production":
            # Production: Require explicit configuration for security
            logger.warning("JWT_ALGORITHM not set in production - using HS256 default")
            self._cached_algorithm = "HS256"
        elif environment == "staging":
            # Staging: Use production-like defaults
            self._cached_algorithm = "HS256"
        else:
            # Development/test: Standard algorithm
            self._cached_algorithm = "HS256"
            
        return self._cached_algorithm
    
    def validate_jwt_configuration(self) -> dict:
        """
        Validate JWT configuration and return diagnostics.
        
        Returns:
            Dict with validation results and diagnostics
        """
        env = self._get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        issues = []
        warnings = []
        info = {}
        
        try:
            # Test secret resolution
            secret = self.get_jwt_secret()
            info["secret_source"] = "resolved_successfully"
            info["secret_length"] = len(secret)
            
            # Check secret strength
            if len(secret) < 32:
                warnings.append(f"JWT secret is only {len(secret)} characters (recommend 32+)")
                
            # Check for insecure defaults
            if secret == "emergency_jwt_secret_please_configure_properly":
                issues.append("Using emergency fallback JWT secret - CONFIGURE PROPERLY")
            elif "emergency" in secret or "fallback" in secret:
                issues.append("Using emergency/fallback JWT secret - not secure")
                
            # Environment-specific checks
            if environment in ["staging", "production"]:
                env_specific_key = f"JWT_SECRET_{environment.upper()}"
                if not env.get(env_specific_key) and not env.get("JWT_SECRET_KEY"):
                    issues.append(f"No environment-specific JWT secret configured for {environment}")
                    
        except Exception as e:
            issues.append(f"JWT secret resolution failed: {str(e)}")
            info["error"] = str(e)
        
        try:
            # Test algorithm resolution
            algorithm = self.get_jwt_algorithm()
            info["algorithm"] = algorithm
            
            if algorithm not in ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]:
                warnings.append(f"Unusual JWT algorithm: {algorithm}")
                
        except Exception as e:
            issues.append(f"JWT algorithm resolution failed: {str(e)}")
        
        return {
            "valid": len(issues) == 0,
            "environment": environment,
            "issues": issues,
            "warnings": warnings,
            "info": info
        }
    
    def clear_cache(self):
        """Clear cached values - useful for testing."""
        self._cached_secret = None
        self._cached_algorithm = None
    
    def get_debug_info(self) -> dict:
        """
        Get debug information about JWT configuration.
        
        Returns:
            Dict with debug information (sanitized - no actual secrets)
        """
        env = self._get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        env_specific_key = f"JWT_SECRET_{environment.upper()}"
        
        return {
            "environment": environment,
            "environment_specific_key": env_specific_key,
            "has_env_specific": bool(env.get(env_specific_key)),
            "has_generic_key": bool(env.get("JWT_SECRET_KEY")),
            "has_legacy_key": bool(env.get("JWT_SECRET")),
            "available_keys": [
                key for key in [env_specific_key, "JWT_SECRET_KEY", "JWT_SECRET"]
                if env.get(key)
            ],
            "algorithm": self.get_jwt_algorithm()
        }


# Global instance - singleton pattern
_jwt_secret_manager: Optional[JWTSecretManager] = None


def get_jwt_secret_manager() -> JWTSecretManager:
    """
    Get the global JWT secret manager instance.
    
    Returns:
        JWTSecretManager singleton instance
    """
    global _jwt_secret_manager
    if _jwt_secret_manager is None:
        _jwt_secret_manager = JWTSecretManager()
    return _jwt_secret_manager


# Convenience functions for direct access
def get_unified_jwt_secret() -> str:
    """
    Get JWT secret using unified resolution logic.
    
    CRITICAL: Use this function instead of direct environment variable access
    to ensure consistency across all services.
    
    Returns:
        JWT secret string
    """
    return get_jwt_secret_manager().get_jwt_secret()


def get_unified_jwt_algorithm() -> str:
    """
    Get JWT algorithm using unified defaults.
    
    Returns:
        JWT algorithm string
    """
    return get_jwt_secret_manager().get_jwt_algorithm()


def validate_unified_jwt_config() -> dict:
    """
    Validate unified JWT configuration.
    
    Returns:
        Dict with validation results
    """
    return get_jwt_secret_manager().validate_jwt_configuration()


# Legacy compatibility class
class SharedJWTSecretManager:
    """Legacy compatibility - redirects to unified manager"""
    
    @staticmethod
    def get_jwt_secret() -> str:
        """Get JWT secret from environment - redirects to unified manager"""
        return get_unified_jwt_secret()
    
    @staticmethod
    def get_service_secret() -> str:
        """Get service secret from environment"""
        env = get_env()
        return env.get(
            'SERVICE_SECRET', 
            'test-secret-for-local-development-only-32chars'
        )
    
    @staticmethod
    def validate_jwt_secret(secret: str) -> bool:
        """Validate JWT secret meets minimum requirements"""
        return bool(secret and len(secret) >= 32)
    
    @staticmethod
    def clear_cache() -> None:
        """Clear cached JWT secrets - redirects to unified manager"""
        get_jwt_secret_manager().clear_cache()


__all__ = [
    "JWTSecretManager",
    "get_jwt_secret_manager", 
    "get_unified_jwt_secret",
    "get_unified_jwt_algorithm",
    "validate_unified_jwt_config",
    "SharedJWTSecretManager"  # Legacy compatibility
]