"""
Central Network Configuration Constants Module

SSOT (Single Source of Truth) for all network-related string literals.
Business Value: Platform/Internal - Deployment Flexibility - Centralizes network configuration
to enable easier deployment across different environments and reduces configuration errors.

All network-related constants are defined here to prevent duplication
and ensure consistency across the entire codebase.

Usage:
    from netra_backend.app.core.network_constants import ServicePorts, DatabaseConstants, HostConstants
    
    # Use constants instead of hardcoded strings
    database_url = f"postgresql://user:pass@{HostConstants.LOCALHOST}:{ServicePorts.POSTGRES_DEFAULT}/db"
"""

from typing import Dict, Final, Optional
import re


class ServicePorts:
    """Service port constants."""
    
    # Database ports
    POSTGRES_DEFAULT: Final[int] = 5432
    POSTGRES_TEST: Final[int] = 5433
    REDIS_DEFAULT: Final[int] = 6379  
    REDIS_TEST: Final[int] = 6380
    CLICKHOUSE_HTTP: Final[int] = 8123
    CLICKHOUSE_HTTP_TEST: Final[int] = 8124
    CLICKHOUSE_NATIVE: Final[int] = 9000
    CLICKHOUSE_NATIVE_TEST: Final[int] = 9001
    
    # Application ports
    BACKEND_DEFAULT: Final[int] = 8000
    FRONTEND_DEFAULT: Final[int] = 3000
    AUTH_SERVICE_DEFAULT: Final[int] = 8081
    AUTH_SERVICE_TEST: Final[int] = 8001
    
    # Docker registry
    DOCKER_REGISTRY: Final[int] = 5000
    
    # Port ranges for dynamic allocation
    DYNAMIC_PORT_MIN: Final[int] = 8000
    DYNAMIC_PORT_MAX: Final[int] = 9999
    
    @classmethod
    def get_postgres_port(cls, is_test: bool = False) -> int:
        """Get PostgreSQL port based on environment."""
        return cls.POSTGRES_TEST if is_test else cls.POSTGRES_DEFAULT
    
    @classmethod
    def get_redis_port(cls, is_test: bool = False) -> int:
        """Get Redis port based on environment.""" 
        return cls.REDIS_TEST if is_test else cls.REDIS_DEFAULT
    
    @classmethod
    def get_clickhouse_http_port(cls, is_test: bool = False) -> int:
        """Get ClickHouse HTTP port based on environment."""
        return cls.CLICKHOUSE_HTTP_TEST if is_test else cls.CLICKHOUSE_HTTP
    
    @classmethod
    def get_clickhouse_native_port(cls, is_test: bool = False) -> int:
        """Get ClickHouse native port based on environment."""
        return cls.CLICKHOUSE_NATIVE_TEST if is_test else cls.CLICKHOUSE_NATIVE
    
    @classmethod
    def get_auth_service_port(cls, is_test: bool = False) -> int:
        """Get Auth Service port based on environment."""
        return cls.AUTH_SERVICE_TEST if is_test else cls.AUTH_SERVICE_DEFAULT


class HostConstants:
    """Host and IP address constants."""
    
    LOCALHOST: Final[str] = "localhost"
    LOCALHOST_IP: Final[str] = "127.0.0.1"
    ANY_HOST: Final[str] = "0.0.0.0"
    
    # Cloud hosts (parameterized)
    POSTGRES_CLOUD_HOST_PLACEHOLDER: Final[str] = "postgres_host_placeholder"
    CLICKHOUSE_HOST_PLACEHOLDER: Final[str] = "clickhouse_host_url_placeholder"
    REDIS_CLOUD_HOST_PLACEHOLDER: Final[str] = "redis_host_placeholder"
    
    @classmethod
    def get_default_host(cls, use_localhost_ip: bool = False) -> str:
        """Get default host for local development."""
        return cls.LOCALHOST_IP if use_localhost_ip else cls.LOCALHOST


class DatabaseConstants:
    """Database connection constants - configuration keys and schemes only.
    
    IMPORTANT: This class only defines constants. All URL building functionality
    has been moved to DatabaseURLBuilder as per database_connectivity_architecture.xml.
    """
    
    # Environment variable names
    REDIS_URL: Final[str] = "REDIS_URL" 
    CLICKHOUSE_URL: Final[str] = "CLICKHOUSE_URL"
    
    # Additional PostgreSQL environment variables
    POSTGRES_HOST: Final[str] = "POSTGRES_HOST"
    POSTGRES_PORT: Final[str] = "POSTGRES_PORT"
    POSTGRES_DB: Final[str] = "POSTGRES_DB"
    POSTGRES_USER: Final[str] = "POSTGRES_USER"
    POSTGRES_PASSWORD: Final[str] = "POSTGRES_PASSWORD"
    
    # Database drivers/schemes
    POSTGRES_SCHEME: Final[str] = "postgresql"
    POSTGRES_ASYNC_SCHEME: Final[str] = "postgresql+asyncpg"
    POSTGRES_SYNC_SCHEME: Final[str] = "postgresql+psycopg2"
    REDIS_SCHEME: Final[str] = "redis"
    CLICKHOUSE_SCHEME: Final[str] = "clickhouse"
    
    # Default database names (environment-aware, no hardcoded credentials)
    POSTGRES_DEFAULT_DB: Final[str] = "netra_db"
    POSTGRES_TEST_DB: Final[str] = "netra_test"
    CLICKHOUSE_DEFAULT_DB: Final[str] = "default"
    CLICKHOUSE_TEST_DB: Final[str] = "test"
    CLICKHOUSE_DEFAULT_USER: Final[str] = "default"
    REDIS_DEFAULT_DB: Final[int] = 0
    REDIS_TEST_DB: Final[int] = 0
    
    # SSL modes
    SSL_MODE_DISABLE: Final[str] = "disable"
    SSL_MODE_PREFER: Final[str] = "prefer"
    SSL_MODE_REQUIRE: Final[str] = "require"
    SSL_MODE_VERIFY_CA: Final[str] = "verify-ca"
    SSL_MODE_VERIFY_FULL: Final[str] = "verify-full"
    
    @classmethod
    def resolve_ssl_parameter_conflicts(cls, url: str) -> str:
        """Resolve SSL parameter conflicts between database drivers.
        
        This implements the SSL parameter resolution as specified in
        database_connectivity_architecture.xml.
        
        Rules:
        - For asyncpg: Convert sslmode=require to ssl=require
        - For psycopg2: Convert ssl=require to sslmode=require  
        - For Unix sockets (/cloudsql/): Remove ALL SSL parameters
        - Preserve other URL components unchanged
        """
        # Unix socket connections - no SSL parameters needed
        if '/cloudsql/' in url:
            url = re.sub(r'[?&]ssl(mode)?=[^&]*', '', url)
            return url.rstrip('?&')
        
        # Driver-specific SSL parameter handling
        if 'asyncpg' in url:
            url = url.replace('sslmode=', 'ssl=')
        elif 'psycopg2' in url or (
            'postgresql://' in url and 
            '+' not in url.split('://')[0]  # Plain postgresql:// without driver
        ):
            url = url.replace('ssl=', 'sslmode=')
        
        return url
    
    @classmethod
    def build_clickhouse_url(cls, 
                           host: str,
                           port: int,
                           database: str,
                           user: str = None,
                           password: str = None) -> str:
        """Build ClickHouse URL with proper formatting.
        
        Args:
            host: ClickHouse host
            port: ClickHouse port (typically 8123 for HTTP)
            database: Database name
            user: Username (defaults to 'default')
            password: Password (optional)
            
        Returns:
            Formatted ClickHouse URL
        """
        user = user or cls.CLICKHOUSE_DEFAULT_USER
        
        if password:
            return f"{cls.CLICKHOUSE_SCHEME}://{user}:{password}@{host}:{port}/{database}"
        else:
            return f"{cls.CLICKHOUSE_SCHEME}://{user}@{host}:{port}/{database}"

    @classmethod
    def build_redis_url(cls,
                       host: str,
                       port: int,
                       database: int = 0,
                       password: str = None) -> str:
        """Build Redis URL with proper formatting.
        
        Args:
            host: Redis host
            port: Redis port
            database: Database number (defaults to 0)
            password: Password (optional)
            
        Returns:
            Formatted Redis URL
        """
        if password:
            return f"{cls.REDIS_SCHEME}://:{password}@{host}:{port}/{database}"
        else:
            return f"{cls.REDIS_SCHEME}://{host}:{port}/{database}"


class URLConstants:
    """URL building and template constants."""
    
    # URL schemes
    HTTP: Final[str] = "http"
    HTTPS: Final[str] = "https"
    WS: Final[str] = "ws"
    WSS: Final[str] = "wss"
    
    # Environment variable names for URL configuration
    BACKEND_SERVICE_URL: Final[str] = "BACKEND_SERVICE_URL"
    FRONTEND_URL: Final[str] = "FRONTEND_URL"
    AUTH_SERVICE_URL: Final[str] = "AUTH_SERVICE_URL"
    CORS_ORIGINS: Final[str] = "CORS_ORIGINS"
    
    # URL path constants
    HEALTH_PATH: Final[str] = "/health"
    API_PREFIX: Final[str] = "/api"
    AUTH_LOGIN_PATH: Final[str] = "/auth/login"
    AUTH_CALLBACK_PATH: Final[str] = "/auth/callback"
    AUTH_LOGOUT_PATH: Final[str] = "/auth/logout"
    WEBSOCKET_PATH: Final[str] = "/ws"
    
    # Production domains
    PRODUCTION_FRONTEND: Final[str] = "https://netrasystems.ai"
    PRODUCTION_APP: Final[str] = "https://app.netrasystems.ai"
    
    # Legacy staging constants (DEPRECATED - use STAGING_*_URL instead)
    STAGING_FRONTEND: Final[str] = "https://app.staging.netrasystems.ai"
    STAGING_APP: Final[str] = "https://api.staging.netrasystems.ai"
    
    # GCP Staging Service URLs - SSOT for all staging services
    # CRITICAL: Use load balancer endpoints, not direct Cloud Run URLs
    STAGING_BACKEND_URL: Final[str] = "https://api.staging.netrasystems.ai"
    STAGING_AUTH_URL: Final[str] = "https://auth.staging.netrasystems.ai"
    STAGING_FRONTEND_URL: Final[str] = "https://app.staging.netrasystems.ai"
    STAGING_WEBSOCKET_URL: Final[str] = "wss://api.staging.netrasystems.ai/ws"
    
    @classmethod
    def build_http_url(cls, 
                      host: str = HostConstants.LOCALHOST,
                      port: int = ServicePorts.BACKEND_DEFAULT,
                      path: str = "",
                      secure: bool = False) -> str:
        """Build HTTP/HTTPS URL."""
        scheme = cls.HTTPS if secure else cls.HTTP
        url = f"{scheme}://{host}"
        if port != (443 if secure else 80):
            url += f":{port}"
        if path:
            if not path.startswith("/"):
                path = "/" + path
            url += path
        return url
    
    @classmethod
    def build_websocket_url(cls,
                           host: str = HostConstants.LOCALHOST,
                           port: int = ServicePorts.BACKEND_DEFAULT,
                           path: str = WEBSOCKET_PATH,
                           secure: bool = False) -> str:
        """Build WebSocket URL."""
        scheme = cls.WSS if secure else cls.WS
        url = f"{scheme}://{host}"
        if port != (443 if secure else 80):
            url += f":{port}"
        if path:
            if not path.startswith("/"):
                path = "/" + path
            url += path
        return url
    
    @classmethod
    def get_cors_origins(cls, environment: str = "development") -> list[str]:
        """Get CORS origins based on environment - supports dynamic ports in development."""
        if environment == "production":
            return [cls.PRODUCTION_FRONTEND, cls.PRODUCTION_APP]
        elif environment == "staging":
            return [
                cls.STAGING_FRONTEND_URL,  # Load balancer frontend
                cls.STAGING_BACKEND_URL,   # Load balancer backend  
                cls.STAGING_AUTH_URL,      # Load balancer auth
                cls.build_http_url(port=ServicePorts.FRONTEND_DEFAULT)  # Local dev
            ]
        else:
            # Development environment - support dynamic ports
            # Include common development ports and patterns
            dev_origins = []
            
            # Common frontend ports
            for port in [3000, 3001, 3002]:
                dev_origins.append(cls.build_http_url(port=port))
                dev_origins.append(cls.build_http_url(host=HostConstants.LOCALHOST_IP, port=port))
            
            # Common backend ports
            for port in [8000, 8001, 8002, 8080, 8081, 8082]:
                dev_origins.append(cls.build_http_url(port=port))
                dev_origins.append(cls.build_http_url(host=HostConstants.LOCALHOST_IP, port=port))
            
            return dev_origins


class ServiceEndpoints:
    """Service endpoint constants and builders."""
    
    # Google OAuth endpoints
    GOOGLE_TOKEN_URI: Final[str] = "https://oauth2.googleapis.com/token"
    GOOGLE_AUTH_URI: Final[str] = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_USERINFO_ENDPOINT: Final[str] = "https://www.googleapis.com/oauth2/userinfo"
    
    # ClickHouse health check
    CLICKHOUSE_PING_PATH: Final[str] = "/ping"
    
    @classmethod
    def build_auth_service_url(cls, 
                              host: str = HostConstants.LOCALHOST,
                              port: int = ServicePorts.AUTH_SERVICE_DEFAULT,
                              secure: bool = False) -> str:
        """Build auth service base URL."""
        return URLConstants.build_http_url(host, port, secure=secure)
    
    @classmethod
    def build_backend_service_url(cls,
                                 host: str = HostConstants.LOCALHOST,
                                 port: int = ServicePorts.BACKEND_DEFAULT,
                                 secure: bool = False) -> str:
        """Build backend service base URL."""
        return URLConstants.build_http_url(host, port, secure=secure)
    
    @classmethod
    def build_frontend_url(cls,
                          host: str = HostConstants.LOCALHOST,
                          port: int = ServicePorts.FRONTEND_DEFAULT,
                          secure: bool = False) -> str:
        """Build frontend service base URL."""
        return URLConstants.build_http_url(host, port, secure=secure)


class NetworkEnvironmentHelper:
    """Helper for environment-based network configuration.
    
    Uses IsolatedEnvironment and DatabaseURLBuilder as per specifications.
    """
    
    @classmethod
    def is_test_environment(cls) -> bool:
        """SSOT: Check test environment via centralized utils."""
        from netra_backend.app.core.project_utils import is_test_environment
        return is_test_environment()
    
    @classmethod
    def get_environment(cls) -> str:
        """Get current environment (development, staging, production)."""
        from shared.isolated_environment import get_env
        env = get_env()
        return env.get("ENVIRONMENT", "development").lower()
    
    @classmethod
    def is_cloud_environment(cls) -> bool:
        """Check if running in cloud environment."""
        from shared.isolated_environment import get_env
        env = get_env()
        # Check for Cloud Run or Cloud SQL indicators
        return (env.get("K_SERVICE") is not None or 
                env.get("CLOUD_ENVIRONMENT", "false").lower() == "true" or
                "/cloudsql/" in env.get("POSTGRES_HOST", ""))
    
    @classmethod
    def get_database_urls_for_environment(cls) -> Dict[str, str]:
        """Get database URLs for current environment using DatabaseURLBuilder.
        
        This delegates all URL construction to DatabaseURLBuilder as per
        database_connectivity_architecture.xml specification.
        """
        from shared.isolated_environment import get_env
        from shared.database_url_builder import DatabaseURLBuilder
        
        env = get_env()
        builder = DatabaseURLBuilder(env.get_all())
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        if not is_valid and cls.get_environment() in ["staging", "production"]:
            # Critical error for staging/production
            import logging
            logging.error(f"Database configuration validation failed: {error_msg}")
        
        # Get environment-appropriate URLs
        postgres_url = builder.get_url_for_environment(sync=False)
        
        # For Redis and ClickHouse, check environment variables first
        redis_url = env.get(DatabaseConstants.REDIS_URL)
        clickhouse_url = env.get(DatabaseConstants.CLICKHOUSE_URL)
        
        # Build URLs if not provided
        if not redis_url:
            # Use sensible defaults based on environment
            is_test = cls.is_test_environment()
            redis_host = env.get("REDIS_HOST", HostConstants.LOCALHOST)
            redis_port = ServicePorts.get_redis_port(is_test)
            redis_db = DatabaseConstants.REDIS_TEST_DB if is_test else DatabaseConstants.REDIS_DEFAULT_DB
            redis_password = env.get("REDIS_PASSWORD")
            
            if redis_password:
                redis_url = f"{DatabaseConstants.REDIS_SCHEME}://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                redis_url = f"{DatabaseConstants.REDIS_SCHEME}://{redis_host}:{redis_port}/{redis_db}"
        
        if not clickhouse_url:
            # Use sensible defaults based on environment  
            is_test = cls.is_test_environment()
            ch_host = env.get("CLICKHOUSE_HOST", HostConstants.LOCALHOST)
            ch_port = ServicePorts.get_clickhouse_native_port(is_test)
            ch_db = DatabaseConstants.CLICKHOUSE_TEST_DB if is_test else DatabaseConstants.CLICKHOUSE_DEFAULT_DB
            ch_user = env.get("CLICKHOUSE_USER", "default")
            ch_password = env.get("CLICKHOUSE_PASSWORD")
            
            if ch_password:
                clickhouse_url = f"{DatabaseConstants.CLICKHOUSE_SCHEME}://{ch_user}:{ch_password}@{ch_host}:{ch_port}/{ch_db}"
            else:
                clickhouse_url = f"{DatabaseConstants.CLICKHOUSE_SCHEME}://{ch_user}@{ch_host}:{ch_port}/{ch_db}"
        
        return {
            "postgres": postgres_url or "",
            "redis": redis_url or "",
            "clickhouse": clickhouse_url or ""
        }
    
    @classmethod
    def get_service_urls_for_environment(cls) -> Dict[str, str]:
        """Get service URLs for current environment."""
        from shared.isolated_environment import get_env
        
        is_test = cls.is_test_environment()
        environment = cls.get_environment()
        env = get_env()
        
        if environment == "production":
            return {
                "frontend": env.get(URLConstants.FRONTEND_URL, URLConstants.PRODUCTION_FRONTEND),
                "backend": env.get(URLConstants.BACKEND_SERVICE_URL, URLConstants.PRODUCTION_APP),
                "auth_service": env.get(URLConstants.AUTH_SERVICE_URL, "")
            }
        elif environment == "staging":
            return {
                "frontend": env.get(URLConstants.FRONTEND_URL, URLConstants.STAGING_FRONTEND_URL),
                "backend": env.get(URLConstants.BACKEND_SERVICE_URL, URLConstants.STAGING_BACKEND_URL),
                "auth_service": env.get(URLConstants.AUTH_SERVICE_URL, URLConstants.STAGING_AUTH_URL)
            }
        else:
            # Development URLs
            return {
                "frontend": env.get(URLConstants.FRONTEND_URL, ServiceEndpoints.build_frontend_url()),
                "backend": env.get(URLConstants.BACKEND_SERVICE_URL, ServiceEndpoints.build_backend_service_url()),
                "auth_service": env.get(
                    URLConstants.AUTH_SERVICE_URL,
                    ServiceEndpoints.build_auth_service_url(port=ServicePorts.get_auth_service_port(is_test))
                )
            }


# Convenience export of all constant classes
__all__ = [
    'ServicePorts',
    'HostConstants', 
    'DatabaseConstants',
    'URLConstants',
    'ServiceEndpoints',
    'NetworkEnvironmentHelper'
]