"""
Auth Service Redis Configuration Builder
Service-specific Redis configuration following shared patterns while maintaining service independence.
"""
from typing import Optional, Dict, Any
from shared.redis_configuration_builder import RedisConfigurationBuilder
import logging

logger = logging.getLogger(__name__)


class AuthRedisConfigurationBuilder(RedisConfigurationBuilder):
    """
    Auth service-specific Redis configuration builder.
    
    Extends the shared RedisConfigurationBuilder with auth-specific behaviors
    while maintaining service independence (no imports from netra_backend).
    """
    
    def __init__(self, env_vars: Dict[str, Any]):
        """Initialize auth Redis configuration with service-specific defaults."""
        # Auth service uses different database numbers for isolation
        self._auth_db_mapping = {
            "development": "1",  # Auth dev uses db 1
            "test": "2",         # Auth test uses db 2  
            "staging": "3",      # Auth staging uses db 3
            "production": "4"    # Auth production uses db 4
        }
        
        # Initialize parent after setting auth-specific attributes
        super().__init__(env_vars)
        
        # Override test and development builders with auth-specific versions
        self.test = self.AuthTestBuilder(self)
        self.development = self.AuthDevelopmentBuilder(self)
    
    @property
    def redis_db(self) -> Optional[str]:
        """Get Redis database number with auth-specific defaults for isolation."""
        # First check explicit configuration
        explicit_db = self.env.get("REDIS_DB")
        if explicit_db:
            return explicit_db
        
        # Use auth-specific database mapping for service isolation
        return self._auth_db_mapping.get(self.environment, "1")
    
    class AuthTestBuilder(RedisConfigurationBuilder.TestBuilder):
        """Auth-specific test environment Redis configuration."""
        
        def __init__(self, parent):
            super().__init__(parent)
        
        @property
        def isolated_url(self) -> str:
            """Auth service uses db 2 for test isolation."""
            return "redis://localhost:6379/2"
        
        @property
        def auto_url(self) -> str:
            """Auto-select Redis URL for auth test environment."""
            # Auth tests always use isolated database
            if self.parent.connection.has_config:
                # Use component config but with auth test database
                base_url = self.parent.connection.sync_url
                if base_url:
                    import re
                    # Replace database number with auth test database
                    return re.sub(r'/\d+$', '/2', base_url)
            return self.isolated_url
    
    class AuthDevelopmentBuilder(RedisConfigurationBuilder.DevelopmentBuilder):
        """Auth-specific development environment Redis configuration."""
        
        def __init__(self, parent):
            super().__init__(parent)
        
        @property
        def default_url(self) -> str:
            """Auth service uses db 1 for development isolation."""
            return "redis://localhost:6379/1"
    
    def validate_auth_redis_config(self) -> tuple[bool, str]:
        """
        Auth-specific Redis validation with session storage requirements.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Run base validation first
        is_valid, error_msg = self.validate()
        if not is_valid:
            return is_valid, error_msg
        
        # Auth-specific validations
        if self.environment in ["staging", "production"]:
            # Auth service needs Redis for session management
            if not self.connection.has_config:
                return False, f"Auth service requires Redis configuration for session management in {self.environment}"
            
            # Check for session-specific configuration
            session_timeout = self.env.get("SESSION_TIMEOUT")
            if not session_timeout:
                logger.warning(f"SESSION_TIMEOUT not configured for {self.environment} - using default")
        
        return True, ""
    
    def get_session_config(self) -> Dict[str, Any]:
        """Get Redis configuration specific to auth session management."""
        return {
            "url": self.get_url_for_environment(),
            "session_timeout": int(self.env.get("SESSION_TIMEOUT", "3600")),  # 1 hour default
            "key_prefix": f"auth:{self.environment}:session:",
            "serialization": "json",
            "pool_config": self.pool.get_pool_config()
        }
    
    def get_safe_log_message(self) -> str:
        """Auth service-specific log message with session info."""
        base_message = super().get_safe_log_message()
        session_timeout = self.env.get("SESSION_TIMEOUT", "3600")
        return f"{base_message} [Session TTL: {session_timeout}s]"


def get_auth_redis_builder(env_vars: Dict[str, Any]) -> AuthRedisConfigurationBuilder:
    """
    Factory function to create auth-specific Redis configuration builder.
    
    Args:
        env_vars: Environment variables dictionary
        
    Returns:
        AuthRedisConfigurationBuilder instance
    """
    return AuthRedisConfigurationBuilder(env_vars)