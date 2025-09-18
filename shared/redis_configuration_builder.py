"""
Redis Configuration Builder
Comprehensive utility for constructing Redis URLs and configurations from environment variables.
Following the proven DatabaseURLBuilder pattern for SSOT compliance.

ISSUE #1177 FIX: Enhanced with robust error handling and resilience patterns
- VPC connectivity validation and error classification
- Infrastructure failure detection and graceful degradation
- Enhanced monitoring and health check capabilities
- Connection pool optimization for high-latency environments
"""
from typing import Optional, Dict, Any, List, Tuple
import logging
import re
import os
import socket
import asyncio
from urllib.parse import quote, urlparse
from datetime import datetime, timedelta, UTC

logger = logging.getLogger(__name__)


class RedisConnectionError(Exception):
    """Redis-specific connection error with enhanced context."""

    def __init__(self, message: str, error_type: str = "connection", original_error: Exception = None):
        super().__init__(message)
        self.error_type = error_type
        self.original_error = original_error
        self.timestamp = datetime.now(UTC)


class RedisInfrastructureError(RedisConnectionError):
    """Redis infrastructure-level error (VPC, network, etc.)."""

    def __init__(self, message: str, infrastructure_type: str = "vpc", original_error: Exception = None):
        super().__init__(message, f"infrastructure_{infrastructure_type}", original_error)
        self.infrastructure_type = infrastructure_type


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

        # CRITICAL FIX: Issue #1177 - Parse URL to extract components when needed
        # This enables seamless handling of both component-based and URL-based configs
        self._parsed_url_components = self._parse_redis_url_if_needed()

        # ISSUE #1177 FIX: Enhanced connection monitoring and resilience tracking
        self._connection_attempts = []
        self._last_health_check = None
        self._health_check_result = None
        self._vpc_connectivity_validated = False

        # Initialize sub-builders
        self.connection = self.ConnectionBuilder(self)
        self.ssl = self.SSLBuilder(self)
        self.development = self.DevelopmentBuilder(self)
        self.test = self.TestBuilder(self)
        self.docker = self.DockerBuilder(self)
        self.staging = self.StagingBuilder(self)
        self.production = self.ProductionBuilder(self)
        self.pool = self.PoolBuilder(self)
        self.health = self.HealthBuilder(self)  # ISSUE #1177 FIX: New health monitoring
    
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

    def _parse_redis_url_if_needed(self) -> Optional[Dict[str, str]]:
        """
        Parse Redis URL to extract components when component-based config is missing.

        CRITICAL FIX: Issue #1177 - This enables seamless fallback from URL to components
        when deployment provides REDIS_URL but runtime expects component-based config.

        Returns:
            Dict with parsed components or None if parsing not needed/possible
        """
        redis_url = self.env.get("REDIS_URL")

        # Only parse URL if we don't have component config
        if not redis_url or self.env.get("REDIS_HOST"):
            return None

        try:
            parsed = urlparse(redis_url)

            if parsed.scheme not in ('redis', 'rediss'):
                logger.warning(f"Invalid Redis URL scheme: {parsed.scheme}")
                return None

            components = {
                'host': parsed.hostname or 'localhost',
                'port': str(parsed.port or 6379),
                'db': parsed.path.lstrip('/') or '0'
            }

            # Extract password if present
            if parsed.password:
                components['password'] = parsed.password

            logger.info(f"Parsed Redis URL components: host={components['host']}, port={components['port']}, db={components['db']}")
            return components

        except Exception as e:
            logger.error(f"Failed to parse Redis URL: {e}")
            return None

    # ===== REDIS ENVIRONMENT VARIABLE PROPERTIES =====
    
    @property
    def redis_host(self) -> Optional[str]:
        """Get Redis host from environment variables or parsed URL."""
        # Prefer component config over parsed URL
        component_host = self.env.get("REDIS_HOST")
        if component_host:
            return component_host

        # Fallback to parsed URL components
        if self._parsed_url_components:
            return self._parsed_url_components.get('host')

        return None
    
    @property
    def redis_port(self) -> Optional[str]:
        """Get Redis port from environment variables or parsed URL."""
        # Prefer component config over parsed URL
        component_port = self.env.get("REDIS_PORT")
        if component_port:
            return component_port

        # Fallback to parsed URL components
        if self._parsed_url_components:
            return self._parsed_url_components.get('port', '6379')

        return "6379"
    
    @property
    def redis_password(self) -> Optional[str]:
        """Get Redis password from environment variables or parsed URL."""
        # Prefer component config over parsed URL
        component_password = self.env.get("REDIS_PASSWORD")
        if component_password:
            return component_password

        # Fallback to parsed URL components
        if self._parsed_url_components:
            return self._parsed_url_components.get('password')

        return None
    
    @property
    def redis_db(self) -> Optional[str]:
        """Get Redis database number from environment variables or parsed URL."""
        # Prefer component config over parsed URL
        component_db = self.env.get("REDIS_DB")
        if component_db:
            return component_db

        # Fallback to parsed URL components
        if self._parsed_url_components:
            return self._parsed_url_components.get('db', '0')

        return "0"
    
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
            """Check if Redis configuration is available from either components or URL.

            CRITICAL FIX: Issue #1177 - Enhanced to check both component-based and URL-based patterns.
            This resolves deployment/runtime configuration mismatches.
            """
            # Check component-based config (preferred)
            if self.parent.redis_host:
                return True

            # Check URL-based config (fallback)
            redis_url = self.parent.env.get("REDIS_URL")
            if redis_url and redis_url.strip():
                return True

            return False
        
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
            
            # URL encode password if present and non-empty
            password = self.parent.redis_password
            if password and password.strip():
                password_part = f":{quote(password, safe='')}"
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
                
                password = self.parent.redis_password
                if password and password.strip():
                    password_part = f":{quote(password, safe='')}"
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

    # ISSUE #1177 FIX: Enhanced validation and health monitoring methods
    async def validate_vpc_connectivity(self) -> Tuple[bool, str]:
        """
        Validate VPC connectivity for Redis in staging/production environments.

        Returns:
            Tuple of (is_connected, error_message)
        """
        if self.environment not in ["staging", "production"]:
            return True, "VPC validation skipped for development/test environments"

        if not self.connection.has_config:
            return False, "No Redis configuration available for VPC validation"

        host = self.redis_host
        port = int(self.redis_port or "6379")

        try:
            # Test TCP connectivity to Redis host
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=10.0)

            # Close connection immediately
            writer.close()
            await writer.wait_closed()

            self._vpc_connectivity_validated = True
            logger.info(f"VPC connectivity to Redis {host}:{port} validated successfully")
            return True, "VPC connectivity validated"

        except asyncio.TimeoutError:
            error_msg = f"VPC connectivity timeout to Redis {host}:{port} - possible VPC connector issue"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"VPC connectivity failed to Redis {host}:{port}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def classify_redis_error(self, error: Exception) -> Dict[str, Any]:
        """
        Classify Redis errors for proper handling and monitoring.

        Args:
            error: Exception to classify

        Returns:
            Dictionary with error classification information
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # VPC and infrastructure errors (Issue #1177 patterns)
        vpc_patterns = [
            'error -3 connecting',
            'connection refused',
            'network is unreachable',
            'no route to host',
            'connection timeout',
            'connection reset',
            'vpc connector',
            'private ip',
            '10.166.204.83',  # Specific to staging Redis IP
        ]

        # Authentication and configuration errors
        auth_patterns = [
            'authentication required',
            'auth failed',
            'invalid password',
            'wrong auth',
            'no auth required',
        ]

        # Application-level errors
        app_patterns = [
            'wrong number of arguments',
            'unknown command',
            'syntax error',
            'invalid db index',
            'out of memory',
        ]

        # Check for VPC/infrastructure patterns
        for pattern in vpc_patterns:
            if pattern in error_str:
                return {
                    'type': 'infrastructure',
                    'category': 'vpc_connectivity',
                    'pattern': pattern,
                    'should_retry': True,
                    'description': f'VPC connectivity issue: {pattern}',
                    'suggested_action': 'Check VPC connector configuration and Redis IP routing'
                }

        # Check for authentication patterns
        for pattern in auth_patterns:
            if pattern in error_str:
                return {
                    'type': 'configuration',
                    'category': 'authentication',
                    'pattern': pattern,
                    'should_retry': False,
                    'description': f'Redis authentication issue: {pattern}',
                    'suggested_action': 'Verify REDIS_PASSWORD configuration'
                }

        # Check for application patterns
        for pattern in app_patterns:
            if pattern in error_str:
                return {
                    'type': 'application',
                    'category': 'redis_command',
                    'pattern': pattern,
                    'should_retry': False,
                    'description': f'Redis command error: {pattern}',
                    'suggested_action': 'Check Redis command syntax and usage'
                }

        # Default classification
        return {
            'type': 'unknown',
            'category': 'unclassified',
            'pattern': error_type,
            'should_retry': True,
            'description': f'Unknown Redis error: {error_str[:100]}',
            'suggested_action': 'Review error details and Redis logs'
        }

    def record_connection_attempt(self, success: bool, error: Optional[Exception] = None, response_time: Optional[float] = None):
        """Record connection attempt for monitoring and analysis."""
        attempt = {
            'timestamp': datetime.now(UTC),
            'success': success,
            'error': self.classify_redis_error(error) if error else None,
            'response_time': response_time,
            'environment': self.environment
        }

        self._connection_attempts.append(attempt)

        # Keep only recent attempts for memory efficiency
        cutoff_time = datetime.now(UTC) - timedelta(hours=1)
        self._connection_attempts = [a for a in self._connection_attempts if a['timestamp'] > cutoff_time]

        if not success and error:
            error_classification = self.classify_redis_error(error)
            logger.warning(
                f"Redis connection attempt failed: {error_classification['type']} - {error_classification['description']}"
            )

    def get_connection_health_metrics(self) -> Dict[str, Any]:
        """Get connection health metrics for monitoring."""
        recent_attempts = [a for a in self._connection_attempts if a['timestamp'] > datetime.now(UTC) - timedelta(minutes=10)]

        if not recent_attempts:
            return {
                'status': 'unknown',
                'recent_attempts': 0,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'vpc_validated': self._vpc_connectivity_validated
            }

        successful_attempts = [a for a in recent_attempts if a['success']]
        success_rate = len(successful_attempts) / len(recent_attempts) * 100

        response_times = [a['response_time'] for a in successful_attempts if a['response_time'] is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

        # Determine health status
        if success_rate >= 90:
            status = 'healthy'
        elif success_rate >= 70:
            status = 'degraded'
        else:
            status = 'unhealthy'

        return {
            'status': status,
            'recent_attempts': len(recent_attempts),
            'success_rate': success_rate,
            'avg_response_time_ms': avg_response_time * 1000 if avg_response_time else 0.0,
            'vpc_validated': self._vpc_connectivity_validated,
            'last_error_types': [a['error']['type'] for a in recent_attempts if a.get('error')],
        }

    class HealthBuilder:
        """ISSUE #1177 FIX: Health monitoring and validation builder."""

        def __init__(self, parent):
            self.parent = parent

        async def check_connectivity(self) -> Dict[str, Any]:
            """Comprehensive Redis connectivity health check."""
            start_time = datetime.now(UTC)

            # Basic configuration validation
            if not self.parent.connection.has_config:
                return {
                    'status': 'unhealthy',
                    'error': 'No Redis configuration available',
                    'timestamp': start_time.isoformat(),
                    'checks': {
                        'config_available': False,
                        'vpc_connectivity': False,
                        'redis_ping': False
                    }
                }

            checks = {
                'config_available': True,
                'vpc_connectivity': False,
                'redis_ping': False
            }

            # VPC connectivity check
            try:
                vpc_connected, vpc_error = await self.parent.validate_vpc_connectivity()
                checks['vpc_connectivity'] = vpc_connected

                if not vpc_connected:
                    return {
                        'status': 'unhealthy',
                        'error': f'VPC connectivity failed: {vpc_error}',
                        'timestamp': start_time.isoformat(),
                        'checks': checks
                    }

            except Exception as e:
                return {
                    'status': 'unhealthy',
                    'error': f'VPC connectivity check failed: {str(e)}',
                    'timestamp': start_time.isoformat(),
                    'checks': checks
                }

            # Redis ping check (if redis library is available)
            try:
                # Import redis here to avoid dependency issues
                import redis

                url = self.parent.get_url_for_environment()
                if url:
                    redis_client = redis.from_url(url, socket_timeout=5)
                    redis_client.ping()
                    checks['redis_ping'] = True

            except ImportError:
                # Redis library not available, skip ping check
                logger.info("Redis library not available for ping check")
            except Exception as e:
                logger.warning(f"Redis ping check failed: {e}")
                error_classification = self.parent.classify_redis_error(e)
                return {
                    'status': 'unhealthy',
                    'error': f'Redis ping failed: {error_classification["description"]}',
                    'error_classification': error_classification,
                    'timestamp': start_time.isoformat(),
                    'checks': checks
                }

            # All checks passed
            duration = (datetime.now(UTC) - start_time).total_seconds()
            return {
                'status': 'healthy',
                'timestamp': start_time.isoformat(),
                'duration_ms': duration * 1000,
                'checks': checks,
                'url_masked': self.parent.mask_url_for_logging(self.parent.get_url_for_environment())
            }

        def get_comprehensive_status(self) -> Dict[str, Any]:
            """Get comprehensive Redis health and configuration status."""
            return {
                'configuration': {
                    'environment': self.parent.environment,
                    'has_config': self.parent.connection.has_config,
                    'ssl_enabled': self.parent.ssl.is_ssl_enabled,
                    'is_docker': self.parent.is_docker_environment(),
                    'vpc_validated': self.parent._vpc_connectivity_validated
                },
                'connectivity': self.parent.get_connection_health_metrics(),
                'validation': {
                    'is_valid': self.parent.validate()[0],
                    'validation_message': self.parent.validate()[1]
                },
                'debug_info': self.parent.debug_info(),
                'safe_log_message': self.parent.get_safe_log_message()
            }