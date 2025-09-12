"""
Unified Secret Manager - SSOT for all secret management operations.

CRITICAL FIX for Issue #169: Consolidates 4+ different secret loading mechanisms
into a single source of truth to eliminate defensive programming duplications
and strengthen configuration-middleware integration.

Business Value Justification (BVJ):
1. Segment: All services and customer tiers
2. Business Goal: System reliability and $500K+ ARR protection
3. Value Impact: Eliminates secret loading failures across all deployment environments  
4. Revenue Impact: Ensures authentication continuity preventing customer churn

This module serves as the authoritative source for all secret operations, replacing:
- Multiple environment variable loading patterns
- Duplicate GCP Secret Manager integrations
- Inconsistent fallback strategies
- Service-specific secret handling
"""

import logging
import hashlib
import secrets
from typing import Dict, Optional, List, Any
from enum import Enum
from dataclasses import dataclass

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class SecretType(Enum):
    """Types of secrets managed by the system."""
    SESSION_SECRET = "SESSION_SECRET"  # For SessionMiddleware
    JWT_SECRET = "JWT_SECRET"         # For JWT token validation
    DATABASE_PASSWORD = "DATABASE_PASSWORD"  # Database connections
    API_KEY = "API_KEY"              # External service API keys
    OAUTH_CLIENT_SECRET = "OAUTH_CLIENT_SECRET"  # OAuth integration
    ENCRYPTION_KEY = "ENCRYPTION_KEY"  # Data encryption


class SecretSource(Enum):
    """Sources where secrets can be loaded from."""
    ENVIRONMENT_VARIABLE = "env"
    GCP_SECRET_MANAGER = "gcp"
    DEVELOPMENT_FALLBACK = "dev"
    EMERGENCY_GENERATED = "emergency"
    CONFIGURATION_FILE = "config"


@dataclass
class SecretInfo:
    """Information about a loaded secret."""
    value: str
    source: SecretSource
    length: int
    environment: str
    is_fallback: bool = False
    is_generated: bool = False
    validation_notes: List[str] = None

    def __post_init__(self):
        if self.validation_notes is None:
            self.validation_notes = []
        self.length = len(self.value)


class UnifiedSecretManager:
    """
    Unified secret management system - SSOT for all secret operations.
    
    This class consolidates all secret loading mechanisms and provides:
    1. Consistent secret loading across all services
    2. Multiple fallback strategies for high availability  
    3. Environment-appropriate security levels
    4. Comprehensive logging and validation
    5. Emergency fallbacks to prevent deployment failures
    """
    
    def __init__(self, environment: str = None):
        """Initialize the unified secret manager.
        
        Args:
            environment: Deployment environment (development, staging, production)
        """
        self.env_manager = get_env()
        self.environment = environment or self._detect_environment()
        self._secret_cache: Dict[str, SecretInfo] = {}
        self._load_strategies = self._initialize_load_strategies()
    
    def _detect_environment(self) -> str:
        """Detect current deployment environment."""
        env_value = self.env_manager.get('ENVIRONMENT', '').lower()
        if env_value:
            return env_value
        
        # Fallback detection strategies
        if self.env_manager.get('K_SERVICE'):  # Cloud Run
            return 'staging' if 'staging' in self.env_manager.get('K_SERVICE', '') else 'production'
        elif self.env_manager.get('PORT') == '8000':  # Local development
            return 'development'
        else:
            return 'development'  # Default
    
    def _initialize_load_strategies(self) -> List:
        """Initialize secret loading strategies in priority order."""
        return [
            self._load_from_environment,
            self._load_from_gcp_secret_manager,
            self._load_from_alternative_env_vars,
            self._load_from_configuration_file,
            self._generate_fallback_secret
        ]
    
    def get_secret(self, secret_name: str, secret_type: SecretType = None, 
                   min_length: int = 32, required: bool = True) -> SecretInfo:
        """Get a secret with comprehensive fallback strategies.
        
        Args:
            secret_name: Name of the secret to retrieve
            secret_type: Type of secret (affects validation and fallback behavior)
            min_length: Minimum required length for the secret
            required: Whether the secret is required (affects error handling)
            
        Returns:
            SecretInfo object containing the secret and metadata
            
        Raises:
            ValueError: If required secret cannot be obtained
        """
        # Check cache first
        cache_key = f"{secret_name}_{self.environment}"
        if cache_key in self._secret_cache:
            cached_secret = self._secret_cache[cache_key]
            logger.debug(f"Retrieved cached secret: {secret_name} (source: {cached_secret.source.value})")
            return cached_secret
        
        logger.info(f"Loading secret: {secret_name} (type: {secret_type}, env: {self.environment})")
        
        # Try each loading strategy in order
        for strategy in self._load_strategies:
            try:
                secret_info = strategy(secret_name, secret_type, min_length)
                if secret_info and secret_info.length >= min_length:
                    # Cache the result
                    self._secret_cache[cache_key] = secret_info
                    logger.info(f" PASS:  Secret loaded: {secret_name} (source: {secret_info.source.value}, "
                              f"length: {secret_info.length}, env: {self.environment})")
                    return secret_info
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} failed for {secret_name}: {e}")
                continue
        
        # If we get here, no strategy worked
        if required:
            raise ValueError(
                f"CRITICAL: Required secret '{secret_name}' could not be loaded for {self.environment}. "
                f"Tried all strategies: {[s.__name__ for s in self._load_strategies]}"
            )
        else:
            logger.warning(f"Optional secret '{secret_name}' could not be loaded")
            return None
    
    def _load_from_environment(self, secret_name: str, secret_type: SecretType, 
                              min_length: int) -> Optional[SecretInfo]:
        """Load secret from environment variables."""
        env_value = self.env_manager.get(secret_name)
        if env_value and len(env_value.strip()) >= min_length:
            return SecretInfo(
                value=env_value.strip(),
                source=SecretSource.ENVIRONMENT_VARIABLE,
                length=len(env_value.strip()),
                environment=self.environment,
                validation_notes=[f"Loaded from environment variable: {secret_name}"]
            )
        return None
    
    def _load_from_gcp_secret_manager(self, secret_name: str, secret_type: SecretType,
                                     min_length: int) -> Optional[SecretInfo]:
        """Load secret from GCP Secret Manager."""
        if self.environment not in ['staging', 'production']:
            return None  # Only use GCP in deployed environments
        
        project_id = self.env_manager.get('GCP_PROJECT_ID') or self.env_manager.get('GOOGLE_CLOUD_PROJECT')
        if not project_id:
            logger.debug("No GCP project ID found, skipping GCP Secret Manager")
            return None
        
        try:
            # Try existing secret manager infrastructure first
            secret_value = self._load_via_secret_manager_builder(secret_name)
            if secret_value and len(secret_value) >= min_length:
                return SecretInfo(
                    value=secret_value,
                    source=SecretSource.GCP_SECRET_MANAGER,
                    length=len(secret_value),
                    environment=self.environment,
                    validation_notes=[f"Loaded from GCP Secret Manager via SecretManagerBuilder"]
                )
            
            # Fallback to direct GCP access
            secret_value = self._load_via_direct_gcp(secret_name, project_id)
            if secret_value and len(secret_value) >= min_length:
                return SecretInfo(
                    value=secret_value,
                    source=SecretSource.GCP_SECRET_MANAGER,
                    length=len(secret_value),
                    environment=self.environment,
                    validation_notes=[f"Loaded from GCP Secret Manager directly"]
                )
                
        except Exception as e:
            logger.debug(f"GCP Secret Manager loading failed: {e}")
        
        return None
    
    def _load_via_secret_manager_builder(self, secret_name: str) -> Optional[str]:
        """Load via existing SecretManagerBuilder infrastructure."""
        try:
            from shared.secret_manager_builder import SecretManagerBuilder
            builder = SecretManagerBuilder()
            if hasattr(builder, 'get_secret'):
                return builder.get_secret(secret_name)
        except (ImportError, AttributeError, Exception) as e:
            logger.debug(f"SecretManagerBuilder not available: {e}")
        return None
    
    def _load_via_direct_gcp(self, secret_name: str, project_id: str) -> Optional[str]:
        """Load directly from GCP Secret Manager API."""
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("UTF-8").strip()
        except Exception as e:
            logger.debug(f"Direct GCP access failed: {e}")
        return None
    
    def _load_from_alternative_env_vars(self, secret_name: str, secret_type: SecretType,
                                       min_length: int) -> Optional[SecretInfo]:
        """Load from alternative environment variable names."""
        # Define alternative names based on secret type
        alternatives = self._get_alternative_names(secret_name, secret_type)
        
        for alt_name in alternatives:
            alt_value = self.env_manager.get(alt_name)
            if alt_value and len(alt_value.strip()) >= min_length:
                return SecretInfo(
                    value=alt_value.strip(),
                    source=SecretSource.ENVIRONMENT_VARIABLE,
                    length=len(alt_value.strip()),
                    environment=self.environment,
                    validation_notes=[f"Loaded from alternative environment variable: {alt_name}"]
                )
        return None
    
    def _get_alternative_names(self, secret_name: str, secret_type: SecretType) -> List[str]:
        """Get alternative names for a secret."""
        alternatives = []
        
        # Common alternatives for SECRET_KEY
        if secret_name == 'SECRET_KEY':
            alternatives = [
                'SESSION_SECRET_KEY',
                'STARLETTE_SECRET_KEY', 
                'APP_SECRET_KEY',
                'DJANGO_SECRET_KEY'
            ]
        elif secret_name == 'JWT_SECRET_KEY':
            alternatives = [
                'JWT_SECRET',
                'AUTH_SECRET_KEY',
                'TOKEN_SECRET_KEY'
            ]
        elif secret_type == SecretType.DATABASE_PASSWORD:
            alternatives = [
                f"{secret_name}_PASSWORD",
                f"DB_{secret_name}",
                f"{secret_name}_PASS"
            ]
        
        return alternatives
    
    def _load_from_configuration_file(self, secret_name: str, secret_type: SecretType,
                                     min_length: int) -> Optional[SecretInfo]:
        """Load from configuration files (development only)."""
        if self.environment not in ['development', 'testing']:
            return None
        
        try:
            # Try to load from configuration
            from netra_backend.app.core.configuration import get_configuration
            config = get_configuration()
            
            # Map secret names to config attributes
            config_attr = secret_name.lower()
            if hasattr(config, config_attr):
                config_value = getattr(config, config_attr)
                if config_value and len(str(config_value)) >= min_length:
                    return SecretInfo(
                        value=str(config_value),
                        source=SecretSource.CONFIGURATION_FILE,
                        length=len(str(config_value)),
                        environment=self.environment,
                        validation_notes=[f"Loaded from configuration attribute: {config_attr}"]
                    )
        except Exception as e:
            logger.debug(f"Configuration file loading failed: {e}")
        
        return None
    
    def _generate_fallback_secret(self, secret_name: str, secret_type: SecretType,
                                 min_length: int) -> Optional[SecretInfo]:
        """Generate fallback secrets for non-production environments."""
        # Development environments: Use deterministic but secure fallbacks
        if self.environment in ['development', 'testing']:
            dev_secret = self._generate_development_secret(secret_name, min_length)
            return SecretInfo(
                value=dev_secret,
                source=SecretSource.DEVELOPMENT_FALLBACK,
                length=len(dev_secret),
                environment=self.environment,
                is_fallback=True,
                validation_notes=[f"Generated development fallback for {secret_name}"]
            )
        
        # Staging: Generate emergency secret to prevent deployment failures
        elif self.environment == 'staging':
            emergency_secret = self._generate_emergency_secret(secret_name, min_length)
            return SecretInfo(
                value=emergency_secret,
                source=SecretSource.EMERGENCY_GENERATED,
                length=len(emergency_secret),
                environment=self.environment,
                is_fallback=True,
                is_generated=True,
                validation_notes=[
                    f"EMERGENCY: Generated fallback for {secret_name}",
                    "This should only be used when GCP Secret Manager is unavailable"
                ]
            )
        
        # Production: Never generate fallbacks
        return None
    
    def _generate_development_secret(self, secret_name: str, min_length: int) -> str:
        """Generate deterministic development secret."""
        base_secret = f"dev-{secret_name.lower().replace('_', '-')}-{self.environment}"
        
        # Ensure minimum length
        while len(base_secret) < min_length:
            base_secret += f"-{len(base_secret)}"
        
        # Truncate if too long (keep it reasonable)
        return base_secret[:min(min_length + 32, 128)]
    
    def _generate_emergency_secret(self, secret_name: str, min_length: int) -> str:
        """Generate emergency secret for staging when GCP is unavailable."""
        # Get environment-specific data
        project_id = self.env_manager.get('GCP_PROJECT_ID', 'netra-staging')
        service_id = self.env_manager.get('K_SERVICE', 'netra-backend')
        
        # Create deterministic but secure key
        base_string = f"{project_id}-{service_id}-{secret_name}-{self.environment}"
        hash_value = hashlib.sha256(base_string.encode()).hexdigest()
        
        # Add randomness for additional security
        random_suffix = secrets.token_urlsafe(8)
        
        # Combine and ensure proper length
        emergency_key = f"{hash_value[:min_length-12]}{random_suffix}"
        
        # Ensure exact minimum length
        while len(emergency_key) < min_length:
            emergency_key += secrets.token_urlsafe(4)
        
        return emergency_key[:min_length + 32]  # Cap at reasonable length
    
    def get_session_secret(self) -> SecretInfo:
        """Get session secret for SessionMiddleware."""
        return self.get_secret('SECRET_KEY', SecretType.SESSION_SECRET, min_length=32)
    
    def get_jwt_secret(self) -> SecretInfo:
        """Get JWT secret for token validation."""
        return self.get_secret('JWT_SECRET_KEY', SecretType.JWT_SECRET, min_length=32)
    
    def validate_all_secrets(self) -> Dict[str, Any]:
        """Validate all critical secrets and return status report."""
        validation_report = {
            'environment': self.environment,
            'timestamp': self.env_manager.get('TIMESTAMP', 'unknown'),
            'secrets': {},
            'overall_status': 'unknown',
            'warnings': [],
            'errors': []
        }
        
        # Critical secrets to validate
        critical_secrets = [
            ('SECRET_KEY', SecretType.SESSION_SECRET, 32, True),
            ('JWT_SECRET_KEY', SecretType.JWT_SECRET, 32, False)
        ]
        
        all_success = True
        
        for secret_name, secret_type, min_length, required in critical_secrets:
            try:
                secret_info = self.get_secret(secret_name, secret_type, min_length, required)
                if secret_info:
                    validation_report['secrets'][secret_name] = {
                        'status': 'success',
                        'source': secret_info.source.value,
                        'length': secret_info.length,
                        'is_fallback': secret_info.is_fallback,
                        'is_generated': secret_info.is_generated,
                        'notes': secret_info.validation_notes
                    }
                    
                    # Add warnings for fallback secrets
                    if secret_info.is_fallback:
                        validation_report['warnings'].append(
                            f"{secret_name} using fallback secret (source: {secret_info.source.value})"
                        )
                else:
                    validation_report['secrets'][secret_name] = {
                        'status': 'missing',
                        'required': required
                    }
                    if required:
                        all_success = False
                        validation_report['errors'].append(f"Required secret {secret_name} is missing")
                        
            except Exception as e:
                all_success = False
                validation_report['secrets'][secret_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                validation_report['errors'].append(f"Error loading {secret_name}: {e}")
        
        validation_report['overall_status'] = 'success' if all_success else 'error'
        return validation_report
    
    def clear_cache(self):
        """Clear the secret cache."""
        self._secret_cache.clear()
        logger.debug("Secret cache cleared")


# Global instance for easy access
_unified_secret_manager = None


def get_unified_secret_manager(environment: str = None) -> UnifiedSecretManager:
    """Get the global unified secret manager instance.
    
    Args:
        environment: Optional environment override
        
    Returns:
        UnifiedSecretManager instance
    """
    global _unified_secret_manager
    if _unified_secret_manager is None or (environment and environment != _unified_secret_manager.environment):
        _unified_secret_manager = UnifiedSecretManager(environment)
    return _unified_secret_manager


# Convenience functions for common operations
def get_session_secret(environment: str = None) -> SecretInfo:
    """Get session secret for SessionMiddleware."""
    manager = get_unified_secret_manager(environment)
    return manager.get_session_secret()


def get_jwt_secret(environment: str = None) -> SecretInfo:
    """Get JWT secret for token validation."""
    manager = get_unified_secret_manager(environment)
    return manager.get_jwt_secret()


def validate_all_secrets(environment: str = None) -> Dict[str, Any]:
    """Validate all critical secrets."""
    manager = get_unified_secret_manager(environment)
    return manager.validate_all_secrets()