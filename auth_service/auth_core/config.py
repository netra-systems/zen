"""
Auth Service Configuration
Handles environment variable loading with staging/production awareness

**UPDATED**: Now uses auth_service's own IsolatedEnvironment for unified environment management.
Follows SPEC/unified_environment_management.xml and SPEC/independent_services.xml for consistent 
environment access while maintaining complete microservice independence.
"""
import logging

# Use auth_service's own isolated environment management - NEVER import from dev_launcher or netra_backend
from shared.isolated_environment import get_env
from auth_service.auth_core.secret_loader import AuthSecretLoader
from shared.database_url_builder import DatabaseURLBuilder
from shared.port_discovery import PortDiscovery

logger = logging.getLogger(__name__)

class AuthConfig:
    """Centralized configuration for auth service"""
    
    # Class-level attributes for settings compatibility
    _env = get_env()  # Use IsolatedEnvironment singleton
    ENVIRONMENT = _env.get("ENVIRONMENT", "development").lower()
    LOG_ASYNC_CHECKOUT = _env.get("LOG_ASYNC_CHECKOUT", "false").lower() == "true"
    
    @staticmethod
    def get_environment() -> str:
        """Get current environment"""
        env = get_env().get("ENVIRONMENT", "development").lower()
        if env in ["staging", "production", "development", "test"]:
            return env
        return "development"
    
    @staticmethod
    def get_google_client_id() -> str:
        """Get Google OAuth Client ID using unified secret loader"""
        return AuthSecretLoader.get_google_client_id()
    
    @staticmethod
    def get_google_client_secret() -> str:
        """Get Google OAuth Client Secret using unified secret loader"""
        return AuthSecretLoader.get_google_client_secret()
    
    @staticmethod
    def get_jwt_secret() -> str:
        """
        Get JWT secret key using SHARED secret manager.
        
        CRITICAL: This now uses SharedJWTSecretManager to ensure
        the EXACT same JWT secret is used by both auth service and backend.
        This is REQUIRED for cross-service authentication to work.
        """
        from shared.jwt_secret_manager import SharedJWTSecretManager
        
        # Use the SINGLE source of truth for JWT secrets
        return SharedJWTSecretManager.get_jwt_secret()
    
    @staticmethod
    def get_service_secret() -> str:
        """Get service secret for enhanced JWT security (distinct from JWT secret)"""
        env_manager = get_env()
        service_secret = env_manager.get("SERVICE_SECRET", "")
        if not service_secret:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = env_manager.get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_SECRET must be set in production/staging")
            # For test/development environments, fail explicitly - no mock fallbacks allowed
            if env in ["test", "development"] or fast_test_mode:
                raise ValueError(f"SERVICE_SECRET must be set in {env} environment - no mock fallbacks allowed per CLAUDE.md")
            # For any other environment, fail loudly
            raise ValueError(
                f"SERVICE_SECRET is not configured for {env} environment. "
                "This must be explicitly set via environment variables."
            )
        
        # Validate service secret is distinct from JWT secret
        jwt_secret = AuthSecretLoader.get_jwt_secret()
        if service_secret == jwt_secret:
            raise ValueError("SERVICE_SECRET must be different from JWT_SECRET_KEY")
        
        if len(service_secret) < 32:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = get_env().get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_SECRET must be at least 32 characters in production")
        
        return service_secret
    
    @staticmethod
    def get_service_id() -> str:
        """Get service instance ID for enhanced JWT security"""
        env_manager = get_env()
        service_id = env_manager.get("SERVICE_ID", "")
        if not service_id:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = env_manager.get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_ID must be set in production/staging")
            # For test/development environments, fail explicitly - no mock fallbacks allowed
            if env in ["test", "development"] or fast_test_mode:
                raise ValueError(f"SERVICE_ID must be set in {env} environment - no mock fallbacks allowed per CLAUDE.md")
            # For any other environment, fail loudly
            raise ValueError(
                f"SERVICE_ID is not configured for {env} environment. "
                "This must be explicitly set via environment variables."
            )
        
        return service_id
    
    @staticmethod
    def get_jwt_algorithm() -> str:
        """Get JWT algorithm"""
        # @marked: JWT algorithm configuration for token generation
        return get_env().get("JWT_ALGORITHM", "HS256")
    
    @staticmethod
    def get_jwt_access_expiry_minutes() -> int:
        """Get JWT access token expiry in minutes"""
        # @marked: JWT access token expiry configuration using JWT Configuration Builder
        try:
            from shared.jwt_config_builder import JWTConfigBuilder
            builder = JWTConfigBuilder(service="auth_service")
            return builder.timing.get_access_token_expire_minutes()
        except Exception as e:
            logger.warning(f"Failed to load JWT config from builder, using fallback: {e}")
            # Fallback to environment variable with CANONICAL name
            return int(get_env().get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 
                      get_env().get("JWT_ACCESS_EXPIRY_MINUTES", "15")))
    
    @staticmethod
    def get_jwt_refresh_expiry_days() -> int:
        """Get JWT refresh token expiry in days"""
        # @marked: JWT refresh token expiry configuration using JWT Configuration Builder
        try:
            from shared.jwt_config_builder import JWTConfigBuilder
            builder = JWTConfigBuilder(service="auth_service")
            return builder.timing.get_refresh_token_expire_days()
        except Exception as e:
            logger.warning(f"Failed to load JWT refresh config from builder, using fallback: {e}")
            # Fallback to environment variable with CANONICAL name
            return int(get_env().get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 
                      get_env().get("JWT_REFRESH_EXPIRY_DAYS", "7")))
    
    @staticmethod
    def get_jwt_service_expiry_minutes() -> int:
        """Get JWT service token expiry in minutes"""
        # @marked: JWT service token expiry configuration using JWT Configuration Builder
        try:
            from shared.jwt_config_builder import JWTConfigBuilder
            builder = JWTConfigBuilder(service="auth_service")
            return builder.timing.get_service_token_expire_minutes()
        except Exception as e:
            logger.warning(f"Failed to load JWT service config from builder, using fallback: {e}")
            # Fallback to environment variable with CANONICAL name
            return int(get_env().get("JWT_SERVICE_TOKEN_EXPIRE_MINUTES", 
                      get_env().get("JWT_SERVICE_EXPIRY_MINUTES", "60")))
    
    @staticmethod
    def get_frontend_url() -> str:
        """Get frontend URL based on environment"""
        env = AuthConfig.get_environment()
        
        if env == "staging":
            return "https://app.staging.netrasystems.ai"
        elif env == "production":
            return "https://netrasystems.ai"
        
        return get_env().get("FRONTEND_URL", "http://localhost:3000")
    
    @staticmethod
    def get_auth_service_url() -> str:
        """Get auth service URL based on environment with dynamic port discovery"""
        env = AuthConfig.get_environment()
        
        # Check for explicit override first
        override_url = get_env().get("AUTH_SERVICE_URL")
        if override_url:
            return override_url
        
        # Use dynamic port discovery
        return PortDiscovery.get_service_url("auth", environment=env)
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL for auth service using comprehensive URL builder."""
        env_manager = get_env()
        
        # Get the base host configuration
        postgres_host = env_manager.get("POSTGRES_HOST")
        
        # Only apply Docker hostname resolution in dev/test environments
        current_env = AuthConfig.get_environment()
        if current_env in ["development", "test"]:
            # Detect if running in Docker container
            # Check common Docker environment indicators
            import os
            is_docker = (
                env_manager.get("RUNNING_IN_DOCKER") == "true" or
                env_manager.get("IS_DOCKER") == "true" or
                env_manager.get("DOCKER_CONTAINER") == "true" or
                # Check for Docker-specific file that exists in containers
                os.path.exists("/.dockerenv") or
                # Check if we're in a container by looking for docker in cgroup
                (os.path.exists("/proc/self/cgroup") and 
                 any("docker" in line for line in open("/proc/self/cgroup").readlines()))
            )
            
            # Override host for Docker context if needed
            if is_docker and postgres_host in ["localhost", "127.0.0.1"]:
                # In Docker, use the service name from docker-compose
                postgres_host = "postgres"
                logger.info(f"Detected Docker environment in {current_env}, using 'postgres' as database host")
        
        # Build all environment variables dict
        env_vars = {
            "ENVIRONMENT": AuthConfig.get_environment(),
            "POSTGRES_HOST": postgres_host,
            "POSTGRES_PORT": env_manager.get("POSTGRES_PORT"),
            "POSTGRES_DB": env_manager.get("POSTGRES_DB"),
            "POSTGRES_USER": env_manager.get("POSTGRES_USER"),
            "POSTGRES_PASSWORD": env_manager.get("POSTGRES_PASSWORD"),
            "DATABASE_URL": env_manager.get("DATABASE_URL")
        }
        
        # Create builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        if not is_valid:
            raise ValueError(f"Database configuration error: {error_msg}")
        
        # Get URL for current environment
        database_url = builder.get_url_for_environment(sync=False)
        
        if not database_url:
            env = AuthConfig.get_environment()
            if env in ["development", "staging", "production"]:
                raise ValueError(
                    f"No PostgreSQL configuration found for {env} environment. "
                    "Set POSTGRES_HOST/USER/DB environment variables."
                )
            logger.warning("No database configuration found for test environment")
            return ""
        
        logger.info(f"Using database URL from {builder.debug_info()['environment']} configuration")
        return database_url
    
    @staticmethod
    def get_raw_database_url() -> str:
        """Get raw database URL for synchronous operations (like alembic)."""
        env_manager = get_env()
        
        # Build all environment variables dict
        env_vars = {
            "ENVIRONMENT": AuthConfig.get_environment(),
            "POSTGRES_HOST": env_manager.get("POSTGRES_HOST"),
            "POSTGRES_PORT": env_manager.get("POSTGRES_PORT"),
            "POSTGRES_DB": env_manager.get("POSTGRES_DB"),
            "POSTGRES_USER": env_manager.get("POSTGRES_USER"),
            "POSTGRES_PASSWORD": env_manager.get("POSTGRES_PASSWORD"),
            "DATABASE_URL": env_manager.get("DATABASE_URL")
        }
        
        # Create builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Get synchronous URL for current environment
        database_url = builder.get_url_for_environment(sync=True)
        
        return database_url or ""
    
    @staticmethod
    def get_redis_url() -> str:
        """Get Redis URL for session management"""
        env = AuthConfig.get_environment()
        # @marked: Redis URL for session storage
        redis_url = get_env().get("REDIS_URL")
        
        if not redis_url:
            # Fail loudly in staging/production if no Redis configuration
            if env in ["staging", "production"]:
                raise ValueError(
                    f"REDIS_URL not configured for {env} environment. "
                    "Redis is required for session management in production/staging."
                )
            # Only warn in development/test
            logger.warning("REDIS_URL not configured for development/test environment")
            return ""  # Return empty string for development/test
        
        return redis_url
    
    @staticmethod
    def get_session_ttl_hours() -> int:
        """Get session TTL in hours"""
        # @marked: Session TTL configuration for session expiry
        return int(get_env().get("SESSION_TTL_HOURS", "24"))
    
    @staticmethod
    def is_redis_disabled() -> bool:
        """Check if Redis is explicitly disabled"""
        # @marked: Redis disable flag for testing/development
        return get_env().get("REDIS_DISABLED", "false").lower() == "true"
    
    @staticmethod
    def log_configuration():
        """Log current configuration (without secrets)"""
        env = AuthConfig.get_environment()
        logger.info(f"Auth Service Configuration:")
        logger.info(f"  Environment: {env}")
        logger.info(f"  Frontend URL: {AuthConfig.get_frontend_url()}")
        logger.info(f"  Auth Service URL: {AuthConfig.get_auth_service_url()}")
        logger.info(f"  Google Client ID: {'*' * 10 if AuthConfig.get_google_client_id() else 'NOT SET'}")
        logger.info(f"  Google Client Secret: {'*' * 10 if AuthConfig.get_google_client_secret() else 'NOT SET'}")
        logger.info(f"  JWT Secret: {'*' * 10 if AuthConfig.get_jwt_secret() else 'NOT SET'}")
        logger.info(f"  Service Secret: {'*' * 10 if AuthConfig.get_service_secret() else 'NOT SET'}")
        logger.info(f"  Service ID: {AuthConfig.get_service_id()}")
        logger.info(f"  JWT Algorithm: {AuthConfig.get_jwt_algorithm()}")
        logger.info(f"  JWT Access Expiry: {AuthConfig.get_jwt_access_expiry_minutes()} minutes")
        logger.info(f"  JWT Refresh Expiry: {AuthConfig.get_jwt_refresh_expiry_days()} days")
        logger.info(f"  JWT Service Expiry: {AuthConfig.get_jwt_service_expiry_minutes()} minutes")
        
        # Log database URL (masked)
        db_url = AuthConfig.get_database_url()
        masked_url = DatabaseURLBuilder.mask_url_for_logging(db_url)
        logger.info(f"  Database URL: {masked_url}")


def get_config() -> AuthConfig:
    """Get auth service configuration instance.
    
    Provides compatibility with test imports that expect get_config function.
    Returns a singleton instance of AuthConfig for consistent configuration access.
    """
    return AuthConfig()