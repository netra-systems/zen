"""
Dynamic Port Discovery for Netra Services
Provides centralized port configuration and discovery for all services.

This module enables dynamic port discovery instead of hardcoded ports,
supporting flexible deployment across different environments.
"""
import os
import socket
from typing import Dict, Optional, Tuple
import logging
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)

class PortDiscovery:
    """Dynamic port discovery and configuration for Netra services"""
    
    # Default port mappings for different environments
    DEFAULT_PORTS = {
        "development": {
            "backend": 8001,
            "auth": 8081,
            "analytics": 8090,
            "frontend": 3000,
            "postgres": 5433,  # Use dev PostgreSQL external port
            "redis": 6379,
            "clickhouse": 8123
        },
        "test": {
            "backend": 8001,
            "auth": 8082,  # Note: test uses different auth port
            "analytics": 8091,  # Note: test uses different analytics port
            "frontend": 3001,
            "postgres": 5434,
            "redis": 6381,
            "clickhouse": 8123
        },
        "staging": {
            "backend": 443,  # HTTPS in staging
            "auth": 443,  # HTTPS in staging
            "analytics": 443,  # HTTPS in staging
            "frontend": 443,  # HTTPS in staging
            "postgres": 5432,
            "redis": 6379,
            "clickhouse": 8123
        },
        "production": {
            "backend": 443,  # HTTPS in production
            "auth": 443,  # HTTPS in production
            "analytics": 443,  # HTTPS in production
            "frontend": 443,  # HTTPS in production
            "postgres": 5432,
            "redis": 6379,
            "clickhouse": 8123
        }
    }
    
    @classmethod
    def get_environment(cls) -> str:
        """Get current environment from environment variables"""
        env_manager = IsolatedEnvironment.get_instance()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        # Also check for TESTING flag
        if env_manager.get("TESTING", "").lower() in ["1", "true"]:
            return "test"
        return env if env in cls.DEFAULT_PORTS else "development"
    
    @classmethod
    def get_port(cls, service: str, environment: Optional[str] = None) -> int:
        """
        Get port for a specific service.
        
        Args:
            service: Service name (backend, auth, frontend, etc.)
            environment: Optional environment override
            
        Returns:
            Port number for the service
        """
        env = environment or cls.get_environment()
        
        # Check for environment variable override first
        env_var_name = f"{service.upper()}_PORT"
        if service == "auth":
            # Special handling for auth service port
            if env == "test":
                env_var_name = "TEST_AUTH_PORT"
            else:
                env_var_name = "AUTH_SERVICE_PORT"
        
        env_manager = IsolatedEnvironment.get_instance()
        env_port = env_manager.get(env_var_name)
        if env_port:
            try:
                return int(env_port)
            except ValueError:
                logger.warning(f"Invalid port value in {env_var_name}: {env_port}")
        
        # Fall back to default port for environment
        if env in cls.DEFAULT_PORTS and service in cls.DEFAULT_PORTS[env]:
            return cls.DEFAULT_PORTS[env][service]
        
        # Ultimate fallback to development defaults
        if service in cls.DEFAULT_PORTS["development"]:
            return cls.DEFAULT_PORTS["development"][service]
        
        raise ValueError(f"Unknown service: {service}")
    
    @classmethod
    def get_service_url(cls, service: str, 
                       host: Optional[str] = None,
                       environment: Optional[str] = None,
                       protocol: Optional[str] = None) -> str:
        """
        Get full URL for a service.
        
        Args:
            service: Service name
            host: Optional host override (defaults to localhost/environment-specific)
            environment: Optional environment override
            protocol: Optional protocol override (http/https/ws/wss)
            
        Returns:
            Full service URL
        """
        env = environment or cls.get_environment()
        port = cls.get_port(service, env)
        
        # Determine host
        if not host:
            if env in ["staging", "production"]:
                # Use domain names in staging/production
                if service == "auth":
                    host = f"auth.{'staging.' if env == 'staging' else ''}netrasystems.ai"
                elif service == "backend":
                    host = f"api.{'staging.' if env == 'staging' else ''}netrasystems.ai"
                elif service == "analytics":
                    host = f"analytics.{'staging.' if env == 'staging' else ''}netrasystems.ai"
                elif service == "frontend":
                    host = f"{'staging.' if env == 'staging' else ''}netrasystems.ai"
                else:
                    host = "localhost"
            else:
                # Check for Docker environment
                if cls._is_docker():
                    # Use service names in Docker
                    host = {
                        "backend": "dev-backend" if env == "development" else "test-backend",
                        "auth": "dev-auth" if env == "development" else "test-auth",
                        "analytics": "dev-analytics" if env == "development" else "test-analytics",
                        "frontend": "dev-frontend" if env == "development" else "test-frontend",
                        "postgres": "dev-postgres" if env == "development" else "test-postgres",
                        "redis": "dev-redis" if env == "development" else "test-redis",
                        "clickhouse": "dev-clickhouse" if env == "development" else "test-clickhouse"
                    }.get(service, "localhost")
                else:
                    host = "localhost"
        
        # Determine protocol
        if not protocol:
            if env in ["staging", "production"]:
                protocol = "https"
            else:
                protocol = "http"
        
        # Build URL
        if env in ["staging", "production"] and port == 443:
            # Don't include port for standard HTTPS
            return f"{protocol}://{host}"
        else:
            return f"{protocol}://{host}:{port}"
    
    @classmethod
    def discover_available_port(cls, start_port: int = 8000, 
                               max_attempts: int = 100) -> int:
        """
        Discover an available port starting from start_port.
        
        Args:
            start_port: Port to start searching from
            max_attempts: Maximum number of ports to try
            
        Returns:
            Available port number
        """
        for port in range(start_port, start_port + max_attempts):
            if cls._is_port_available(port):
                return port
        raise RuntimeError(f"No available ports found in range {start_port}-{start_port + max_attempts}")
    
    @staticmethod
    def _is_port_available(port: int) -> bool:
        """Check if a port is available for binding"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return True
        except OSError:
            return False
    
    @staticmethod
    def _is_docker() -> bool:
        """Check if running in Docker container"""
        env_manager = IsolatedEnvironment.get_instance()
        return (
            env_manager.get("RUNNING_IN_DOCKER") == "true" or
            env_manager.get("IS_DOCKER") == "true" or
            env_manager.get("DOCKER_CONTAINER") == "true" or
            os.path.exists("/.dockerenv") or
            (os.path.exists("/proc/self/cgroup") and 
             any("docker" in line for line in open("/proc/self/cgroup").readlines() 
                 if "docker" in line))
        )
    
    @classmethod
    def get_all_service_urls(cls, environment: Optional[str] = None) -> Dict[str, str]:
        """
        Get URLs for all services in the current environment.
        
        Returns:
            Dictionary of service names to URLs
        """
        env = environment or cls.get_environment()
        services = ["backend", "auth", "analytics", "frontend"]
        
        return {
            service: cls.get_service_url(service, environment=env)
            for service in services
        }
    
    @classmethod
    def validate_port_configuration(cls) -> Tuple[bool, str]:
        """
        Validate that port configuration is consistent.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        env = cls.get_environment()
        errors = []
        
        # Check for port conflicts
        used_ports = {}
        for service in ["backend", "auth", "analytics", "frontend", "postgres", "redis", "clickhouse"]:
            try:
                port = cls.get_port(service, env)
                if port in used_ports:
                    errors.append(
                        f"Port conflict: {service} and {used_ports[port]} "
                        f"both configured for port {port}"
                    )
                used_ports[port] = service
            except ValueError as e:
                errors.append(str(e))
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "Port configuration is valid"


# Convenience functions for backward compatibility
def get_auth_service_url(environment: Optional[str] = None) -> str:
    """Get auth service URL for current or specified environment"""
    return PortDiscovery.get_service_url("auth", environment=environment)

def get_backend_service_url(environment: Optional[str] = None) -> str:
    """Get backend service URL for current or specified environment"""
    return PortDiscovery.get_service_url("backend", environment=environment)

def get_analytics_service_url(environment: Optional[str] = None) -> str:
    """Get analytics service URL for current or specified environment"""
    return PortDiscovery.get_service_url("analytics", environment=environment)

def get_frontend_url(environment: Optional[str] = None) -> str:
    """Get frontend URL for current or specified environment"""
    return PortDiscovery.get_service_url("frontend", environment=environment)