"""
Redis Configuration Builder
Comprehensive utility for constructing Redis URLs and configurations from environment variables.
Following the proven DatabaseURLBuilder pattern for SSOT compliance.
"""
from typing import Optional, Dict, Any
import logging
import re
import os
from urllib.parse import quote

logger = logging.getLogger(__name__)


class RedisConfigurationBuilder:
    """
    Build Redis configurations from environment variables.
    
    Provides organized access to all Redis patterns:
    - connection.async_url
    - connection.sync_url
    - connection.cluster_urls
    - ssl.enabled_url
    - development.default_url
    - test.isolated_url
    - docker.compose_url
    """
    
    def __init__(self, env_vars: Dict[str, Any]):
        """Initialize with environment variables."""
        self.env = env_vars
        self.environment = env_vars.get("ENVIRONMENT", "development").lower()

        # ALWAYS build from component parts never directly take REDIS_URL from env
        # This follows DatabaseURLBuilder SSOT pattern

        # Initialize sub-builders
        self.connection = self.ConnectionBuilder(self)
        self.ssl = self.SSLBuilder(self)
        self.development = self.DevelopmentBuilder(self)
        self.test = self.TestBuilder(self)
        self.docker = self.DockerBuilder(self)
        self.staging = self.StagingBuilder(self)
        self.production = self.ProductionBuilder(self)
        self.pool = self.PoolBuilder(self)
    
    def is_docker_environment(self) -> bool:
        """
        Detect if running in Docker container using multiple indicators.
        Follows DatabaseURLBuilder pattern exactly.
        
        Returns:
            bool: True if running in Docker, False otherwise
        """
        # Method 1: Check environment variables
        docker_env_vars = [
            "RUNNING_IN_DOCKER",
            "IS_DOCKER", 
            "DOCKER_CONTAINER"
        ]
        for var in docker_env_vars:
            if self.env.get(var) == "true":
                return True
        
        # Method 2: Check for .dockerenv file
        if os.path.exists("/.dockerenv"):
            return True
        
        # Method 3: Check /proc/self/cgroup for docker references
        try:
            if os.path.exists("/proc/self/cgroup"):
                with open("/proc/self/cgroup", "r") as f:
                    content = f.read()
                    if "docker" in content.lower():
                        return True
        except (OSError, IOError):
            # Ignore file access errors
            pass
        
        return False
    
    # ===== REDIS ENVIRONMENT VARIABLE PROPERTIES =====
    
    @property
    def redis_host(self) -> Optional[str]:
        """Get Redis host from environment variables."""
        return self.env.get("REDIS_HOST")
    
    @property 
    def redis_port(self) -> Optional[str]:
        """Get Redis port from environment variables."""
        return self.env.get("REDIS_PORT") or "6379"
    
    @property
    def redis_password(self) -> Optional[str]:
        """Get Redis password from environment variables."""
        return self.env.get("REDIS_PASSWORD")
    
    @property
    def redis_db(self) -> Optional[str]:
        """Get Redis database number from environment variables."""
        return self.env.get("REDIS_DB") or "0"
    
    @property
    def redis_url(self) -> Optional[str]:
        """Get Redis URL from environment variables (for compatibility only)."""
        return self.env.get("REDIS_URL")
    
    def apply_docker_hostname_resolution(self, host: str) -> str:
        """
        Apply Docker hostname resolution if conditions are met.
        
        Only applies in development and test environments, and only overrides
        localhost/127.0.0.1 with Docker service name 'redis'.
        
        Args:
            host: Original hostname
            
        Returns:
            str: Resolved hostname (original or Docker service name)
        """
        # Only apply Docker hostname resolution in development/test environments
        if self.environment not in ["development", "test"]:
            return host
        
        # Only override localhost/127.0.0.1 
        if host not in ["localhost", "127.0.0.1"]:
            return host
        
        # Check if running in Docker
        if self.is_docker_environment():
            logger.info(f"Detected Docker environment in {self.environment}, using 'redis' as Redis host")
            return "redis"
        
        return host
    
    class ConnectionBuilder:
        """Build Redis connection URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def has_config(self) -> bool:
            """Check if Redis configuration is available."""
            return bool(self.parent.redis_host)
        
        @property
        def async_url(self) -> Optional[str]:
            """Async URL for Redis connection (same as sync for Redis)."""
            return self.sync_url
        
        @property
        def sync_url(self) -> Optional[str]:
            """Sync URL for Redis connection."""
            if not self.has_config:
                return None
            
            # Apply Docker hostname resolution
            resolved_host = self.parent.apply_docker_hostname_resolution(self.parent.redis_host)
            
            # URL encode password if present
            if self.parent.redis_password:
                password_part = f":{quote(self.parent.redis_password, safe='')}"
                return (
                    f"redis://"
                    f"{password_part}@"
                    f"{resolved_host}"
                    f":{self.parent.redis_port}"
                    f"/{self.parent.redis_db}"
                )
            else:
                return (
                    f"redis://"
                    f"{resolved_host}"
                    f":{self.parent.redis_port}"
                    f"/{self.parent.redis_db}"
                )
        
        @property
        def cluster_urls(self) -> Optional[list]:
            """Redis cluster URLs if configured."""
            cluster_hosts = self.parent.env.get("REDIS_CLUSTER_HOSTS")
            if not cluster_hosts:
                return None
            
            urls = []
            hosts = cluster_hosts.split(",")
            for host_port in hosts:
                host_port = host_port.strip()
                if ":" not in host_port:
                    host_port = f"{host_port}:6379"
                
                host, port = host_port.split(":", 1)
                resolved_host = self.parent.apply_docker_hostname_resolution(host)
                
                if self.parent.redis_password:
                    password_part = f":{quote(self.parent.redis_password, safe='')}"
                    url = f"redis://{password_part}@{resolved_host}:{port}/{self.parent.redis_db}"
                else:
                    url = f"redis://{resolved_host}:{port}/{self.parent.redis_db}"
                
                urls.append(url)
            
            return urls
    
    class SSLBuilder:
        """Build Redis SSL-enabled URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def is_ssl_enabled(self) -> bool:
            """Check if SSL is enabled."""
            return self.parent.env.get("REDIS_SSL", "false").lower() == "true"
        
        @property
        def enabled_url(self) -> Optional[str]:
            """SSL-enabled Redis URL."""
            if not self.is_ssl_enabled or not self.parent.connection.has_config:
                return None
            
            # Get base URL and convert to rediss://
            base_url = self.parent.connection.sync_url
            if base_url and base_url.startswith("redis://"):
                return base_url.replace("redis://", "rediss://", 1)
            
            return None
        
        @property
        def cert_file(self) -> Optional[str]:
            """SSL certificate file path."""
            return self.parent.env.get("REDIS_SSL_CERT_FILE")
        
        @property
        def key_file(self) -> Optional[str]:
            """SSL key file path."""
            return self.parent.env.get("REDIS_SSL_KEY_FILE")
        
        @property
        def ca_certs(self) -> Optional[str]:
            """SSL CA certificates file path."""
            return self.parent.env.get("REDIS_SSL_CA_CERTS")
    
    class DevelopmentBuilder:
        """Build development environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def default_url(self) -> str:
            """Default development URL."""
            return "redis://localhost:6379/0"
        
        @property
        def auto_url(self) -> str:
            """Auto-select best URL for development."""
            # Try component-based config
            if self.parent.connection.has_config:
                return self.parent.connection.sync_url
            # Fall back to default
            return self.default_url
    
    class TestBuilder:
        """Build test environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def isolated_url(self) -> str:
            """Isolated Redis URL for test environment - separate database."""
            return "redis://localhost:6379/15"  # High DB number for isolation
        
        @property
        def auto_url(self) -> str:
            """Auto-select best URL for test."""
            # Tests use isolated database by default
            if self.parent.connection.has_config:
                # Use component config but with test database
                base_url = self.parent.connection.sync_url
                if base_url:
                    # Replace database number with test isolation database
                    return re.sub(r'/\d+$', '/15', base_url)
            return self.isolated_url
    
    class DockerBuilder:
        """Build Docker environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def compose_url(self) -> str:
            """URL for Docker Compose environment."""
            host = self.parent.redis_host or "redis"  # Docker service name
            port = self.parent.redis_port or "6379"
            db = self.parent.redis_db or "0"
            
            if self.parent.redis_password:
                password_part = f":{quote(self.parent.redis_password, safe='')}"
                return f"redis://{password_part}@{host}:{port}/{db}"
            else:
                return f"redis://{host}:{port}/{db}"
    
    class StagingBuilder:
        """Build staging environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def auto_url(self) -> Optional[str]:
            """Auto-select best URL for staging."""
            # Prefer SSL if enabled
            if self.parent.ssl.is_ssl_enabled:
                return self.parent.ssl.enabled_url
            # Use standard connection
            if self.parent.connection.has_config:
                return self.parent.connection.sync_url
            return None
    
    class ProductionBuilder:
        """Build production environment URLs."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def auto_url(self) -> Optional[str]:
            """Auto-select best URL for production."""
            # Prefer SSL if enabled
            if self.parent.ssl.is_ssl_enabled:
                return self.parent.ssl.enabled_url
            # Use standard connection
            if self.parent.connection.has_config:
                return self.parent.connection.sync_url
            return None
    
    class PoolBuilder:
        """Build Redis connection pool configuration."""
        
        def __init__(self, parent):
            self.parent = parent
        
        def get_pool_config(self) -> Dict[str, Any]:
            """Get Redis connection pool configuration."""
            env = self.parent.environment
            
            # Environment-specific pool configurations
            if env == "production":
                return {
                    "max_connections": int(self.parent.env.get("REDIS_POOL_MAX_CONNECTIONS", "50")),
                    "retry_on_timeout": True,
                    "health_check_interval": 30,
                    "socket_keepalive": True,
                    "socket_keepalive_options": {},
                    "connection_pool_class_kwargs": {
                        "max_connections_per_pool": 50
                    }
                }
            elif env == "staging":
                return {
                    "max_connections": int(self.parent.env.get("REDIS_POOL_MAX_CONNECTIONS", "25")),
                    "retry_on_timeout": True,
                    "health_check_interval": 60,
                    "socket_keepalive": True
                }
            elif env == "development":
                return {
                    "max_connections": int(self.parent.env.get("REDIS_POOL_MAX_CONNECTIONS", "10")),
                    "retry_on_timeout": False,
                    "health_check_interval": 120
                }
            else:  # test and others
                return {
                    "max_connections": int(self.parent.env.get("REDIS_POOL_MAX_CONNECTIONS", "5")),
                    "retry_on_timeout": False,
                    "health_check_interval": 300
                }
    
    def get_url_for_environment(self, async_mode: bool = False) -> Optional[str]:
        """
        Get the appropriate Redis URL for current environment.
        
        Args:
            async_mode: If True, return async-compatible URL (Redis uses same URLs for sync/async)
        """
        if self.environment == "staging":
            return self.staging.auto_url
        elif self.environment == "production":
            return self.production.auto_url
        elif self.environment == "test":
            return self.test.auto_url
        else:  # development
            return self.development.auto_url
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate Redis configuration for current environment.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.environment in ["staging", "production"]:
            # Must have explicit Redis configuration
            if not self.connection.has_config:
                missing = []
                if not self.redis_host:
                    missing.append("REDIS_HOST")
                
                return False, f"Missing required variables for {self.environment}: {', '.join(missing)}"
        
        # Validate SSL configuration if enabled
        if self.ssl.is_ssl_enabled:
            if self.environment in ["staging", "production"]:
                # SSL should be properly configured
                if not self.ssl.cert_file and not self.ssl.ca_certs:
                    return False, "SSL enabled but no certificate files configured"
        
        return True, ""
    
    def debug_info(self) -> Dict[str, Any]:
        """Get debug information about available URLs."""
        return {
            "environment": self.environment,
            "is_docker": self.is_docker_environment(),
            "has_connection_config": self.connection.has_config,
            "ssl_enabled": self.ssl.is_ssl_enabled,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_db": self.redis_db,
            "available_urls": {
                "connection_sync": self.connection.sync_url is not None,
                "connection_async": self.connection.async_url is not None,
                "ssl_enabled": self.ssl.enabled_url is not None,
                "cluster_urls": self.connection.cluster_urls is not None,
                "auto_url": self.get_url_for_environment() is not None,
            }
        }
    
    @staticmethod
    def mask_url_for_logging(redis_url: Optional[str]) -> str:
        """
        Mask sensitive information in Redis URL for safe logging.
        
        Args:
            redis_url: The Redis URL to mask
            
        Returns:
            A masked version safe for logging
        """
        if not redis_url:
            return "NOT SET"
        
        # Handle Redis URLs with passwords
        if "://" in redis_url:
            protocol, rest = redis_url.split("://", 1)
            if "@" in rest:
                # Mask the password
                _, host_part = rest.split("@", 1)
                return f"{protocol}://***@{host_part}"
            return redis_url  # No credentials to mask
        
        # Unknown format - mask everything except protocol
        if "://" in redis_url:
            protocol = redis_url.split("://")[0]
            return f"{protocol}://{'*' * 10}"
        
        return "*" * 10  # Complete mask for unknown formats
    
    def get_safe_log_message(self) -> str:
        """
        Get a safe log message with current configuration details.
        
        Returns:
            A formatted string safe for logging with masked credentials
        """
        url = self.get_url_for_environment()
        masked_url = self.mask_url_for_logging(url)
        
        config_type = "NOT CONFIGURED"
        if self.ssl.is_ssl_enabled:
            config_type = "SSL"
        elif self.connection.cluster_urls:
            config_type = "Cluster"
        elif self.connection.has_config:
            config_type = "Standard"
        elif url:
            config_type = "Default"
        
        return f"Redis URL ({self.environment}/{config_type}): {masked_url}"