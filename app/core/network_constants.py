"""
Central Network Configuration Constants Module

SSOT (Single Source of Truth) for all network-related string literals.
Business Value: Platform/Internal - Deployment Flexibility - Centralizes network configuration
to enable easier deployment across different environments and reduces configuration errors.

All network-related constants are defined here to prevent duplication
and ensure consistency across the entire codebase.

Usage:
    from app.core.network_constants import ServicePorts, DatabaseConstants, HostConstants
    
    # Use constants instead of hardcoded strings
    database_url = f"postgresql://user:pass@{HostConstants.LOCALHOST}:{ServicePorts.POSTGRES_DEFAULT}/db"
"""

import os
from typing import Final, Dict, Optional


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
    """Database connection constants."""
    
    # Environment variable names
    DATABASE_URL: Final[str] = "DATABASE_URL"
    REDIS_URL: Final[str] = "REDIS_URL" 
    CLICKHOUSE_URL: Final[str] = "CLICKHOUSE_URL"
    
    # Database drivers/schemes
    POSTGRES_SCHEME: Final[str] = "postgresql"
    POSTGRES_ASYNC_SCHEME: Final[str] = "postgresql+asyncpg"
    REDIS_SCHEME: Final[str] = "redis"
    CLICKHOUSE_SCHEME: Final[str] = "clickhouse"
    
    # Default database names
    POSTGRES_DEFAULT_DB: Final[str] = "netra_db"
    POSTGRES_TEST_DB: Final[str] = "netra_test"
    CLICKHOUSE_DEFAULT_DB: Final[str] = "default"
    CLICKHOUSE_TEST_DB: Final[str] = "test"
    REDIS_DEFAULT_DB: Final[int] = 0
    REDIS_TEST_DB: Final[int] = 1
    
    # Default credentials (for development only)
    POSTGRES_DEFAULT_USER: Final[str] = "postgres"
    POSTGRES_DEFAULT_PASSWORD: Final[str] = "postgres"
    POSTGRES_TEST_USER: Final[str] = "test_user"
    POSTGRES_TEST_PASSWORD: Final[str] = "test_password"
    CLICKHOUSE_DEFAULT_USER: Final[str] = "default"
    REDIS_TEST_PASSWORD: Final[str] = "test_password"
    
    @classmethod
    def build_postgres_url(cls, 
                          user: str = POSTGRES_DEFAULT_USER,
                          password: str = POSTGRES_DEFAULT_PASSWORD,
                          host: str = HostConstants.LOCALHOST,
                          port: int = ServicePorts.POSTGRES_DEFAULT,
                          database: str = POSTGRES_DEFAULT_DB,
                          async_driver: bool = False) -> str:
        """Build PostgreSQL connection URL."""
        scheme = cls.POSTGRES_ASYNC_SCHEME if async_driver else cls.POSTGRES_SCHEME
        return f"{scheme}://{user}:{password}@{host}:{port}/{database}"
    
    @classmethod
    def build_redis_url(cls,
                       host: str = HostConstants.LOCALHOST,
                       port: int = ServicePorts.REDIS_DEFAULT,
                       database: int = REDIS_DEFAULT_DB,
                       password: Optional[str] = None) -> str:
        """Build Redis connection URL."""
        if password:
            return f"{cls.REDIS_SCHEME}://:{password}@{host}:{port}/{database}"
        return f"{cls.REDIS_SCHEME}://{host}:{port}/{database}"
    
    @classmethod
    def build_clickhouse_url(cls,
                            host: str = HostConstants.LOCALHOST,
                            port: int = ServicePorts.CLICKHOUSE_NATIVE,
                            database: str = CLICKHOUSE_DEFAULT_DB,
                            user: str = CLICKHOUSE_DEFAULT_USER,
                            password: Optional[str] = None) -> str:
        """Build ClickHouse connection URL."""
        if password:
            return f"{cls.CLICKHOUSE_SCHEME}://{user}:{password}@{host}:{port}/{database}"
        return f"{cls.CLICKHOUSE_SCHEME}://{user}@{host}:{port}/{database}"


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
    STAGING_FRONTEND: Final[str] = "https://app.staging.netrasystems.ai"
    STAGING_APP: Final[str] = "https://app.staging.netrasystems.ai"
    
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
            return [cls.STAGING_FRONTEND, cls.STAGING_APP,
                   cls.build_http_url(port=ServicePorts.FRONTEND_DEFAULT)]
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
    """Helper for environment-based network configuration."""
    
    @classmethod
    def is_test_environment(cls) -> bool:
        """Check if running in test environment."""
        return bool(os.environ.get("PYTEST_CURRENT_TEST") or 
                   os.environ.get("TESTING") == "true")
    
    @classmethod
    def get_environment(cls) -> str:
        """Get current environment (development, staging, production)."""
        return os.environ.get("ENVIRONMENT", "development").lower()
    
    @classmethod
    def is_cloud_environment(cls) -> bool:
        """Check if running in cloud environment."""
        return bool(os.environ.get("K_SERVICE") or 
                   os.environ.get("CLOUD_RUN_SERVICE"))
    
    @classmethod
    def get_database_urls_for_environment(cls) -> Dict[str, str]:
        """Get database URLs for current environment."""
        is_test = cls.is_test_environment()
        env = cls.get_environment()
        
        if env == "production" or env == "staging":
            # Use environment variables for production/staging
            return {
                "postgres": os.environ.get("DATABASE_URL", ""),
                "redis": os.environ.get("REDIS_URL", ""),
                "clickhouse": os.environ.get("CLICKHOUSE_URL", "")
            }
        else:
            # Generate local URLs for development
            return {
                "postgres": DatabaseConstants.build_postgres_url(
                    port=ServicePorts.get_postgres_port(is_test),
                    database=DatabaseConstants.POSTGRES_TEST_DB if is_test else DatabaseConstants.POSTGRES_DEFAULT_DB,
                    user=DatabaseConstants.POSTGRES_TEST_USER if is_test else DatabaseConstants.POSTGRES_DEFAULT_USER,
                    password=DatabaseConstants.POSTGRES_TEST_PASSWORD if is_test else DatabaseConstants.POSTGRES_DEFAULT_PASSWORD,
                    async_driver=True
                ),
                "redis": DatabaseConstants.build_redis_url(
                    port=ServicePorts.get_redis_port(is_test),
                    database=DatabaseConstants.REDIS_TEST_DB if is_test else DatabaseConstants.REDIS_DEFAULT_DB,
                    password=DatabaseConstants.REDIS_TEST_PASSWORD if is_test else None
                ),
                "clickhouse": DatabaseConstants.build_clickhouse_url(
                    port=ServicePorts.get_clickhouse_native_port(is_test),
                    database=DatabaseConstants.CLICKHOUSE_TEST_DB if is_test else DatabaseConstants.CLICKHOUSE_DEFAULT_DB
                )
            }
    
    @classmethod
    def get_service_urls_for_environment(cls) -> Dict[str, str]:
        """Get service URLs for current environment."""
        is_test = cls.is_test_environment()
        env = cls.get_environment()
        
        if env == "production":
            return {
                "frontend": URLConstants.PRODUCTION_FRONTEND,
                "backend": os.environ.get("BACKEND_SERVICE_URL", URLConstants.PRODUCTION_APP),
                "auth_service": os.environ.get("AUTH_SERVICE_URL", "")
            }
        elif env == "staging":
            return {
                "frontend": URLConstants.STAGING_FRONTEND,
                "backend": os.environ.get("BACKEND_SERVICE_URL", URLConstants.STAGING_APP),
                "auth_service": os.environ.get("AUTH_SERVICE_URL", "")
            }
        else:
            # Development URLs
            return {
                "frontend": ServiceEndpoints.build_frontend_url(),
                "backend": ServiceEndpoints.build_backend_service_url(),
                "auth_service": ServiceEndpoints.build_auth_service_url(
                    port=ServicePorts.get_auth_service_port(is_test)
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