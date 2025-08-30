"""
Dynamic ClickHouse Port Discovery

Intelligently discovers ClickHouse ports based on environment and Docker configuration.
Eliminates hardcoded port dependencies and provides automatic fallback handling.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Development Velocity & Test Reliability
- Value Impact: Reduces configuration errors, enables flexible deployment
- Strategic Impact: Supports multi-environment testing and development workflows
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from netra_backend.app.core.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger as logger


class ClickHousePortDiscovery:
    """
    Dynamic ClickHouse port discovery system.
    
    Automatically determines the correct ClickHouse HTTP port based on:
    1. Current environment (DEV vs TEST)
    2. Docker compose configuration
    3. Environment variables 
    4. Running Docker containers
    """
    
    def __init__(self):
        """Initialize the port discovery system."""
        self._env = get_env()
        self._logger = logger
        self._port_cache: Dict[str, int] = {}
        
    def discover_http_port(self, environment: Optional[str] = None) -> int:
        """
        Discover the ClickHouse HTTP port for the given environment.
        
        Args:
            environment: Target environment ('dev', 'test', 'development', 'testing')
                        If None, auto-detects from current environment
                        
        Returns:
            int: The ClickHouse HTTP port to use
            
        Raises:
            ValueError: If port cannot be determined
        """
        if environment is None:
            environment = self._detect_current_environment()
            
        # Normalize environment name
        env_key = self._normalize_environment(environment)
        
        # Check cache first
        if env_key in self._port_cache:
            return self._port_cache[env_key]
        
        # Try discovery methods in order of preference
        port = self._try_discovery_methods(env_key)
        
        if port is None:
            raise ValueError(f"Unable to discover ClickHouse port for environment: {environment}")
        
        # Cache the result
        self._port_cache[env_key] = port
        self._logger.info(f"Discovered ClickHouse HTTP port {port} for environment '{env_key}'")
        
        return port
    
    def discover_tcp_port(self, environment: Optional[str] = None) -> int:
        """
        Discover the ClickHouse TCP/native port for the given environment.
        
        Args:
            environment: Target environment ('dev', 'test', 'development', 'testing')
                        If None, auto-detects from current environment
                        
        Returns:
            int: The ClickHouse TCP port to use
        """
        if environment is None:
            environment = self._detect_current_environment()
        
        env_key = self._normalize_environment(environment)
        
        # Try discovery methods for TCP port
        port = self._try_tcp_discovery_methods(env_key)
        
        if port is None:
            # Default TCP ports based on environment
            if env_key == "test":
                port = 9001  # TEST environment TCP port
            else:
                port = 9000  # DEV environment TCP port
                
        self._logger.debug(f"Discovered ClickHouse TCP port {port} for environment '{env_key}'")
        return port
    
    def get_connection_url(self, environment: Optional[str] = None, 
                          include_credentials: bool = True) -> str:
        """
        Get the complete ClickHouse connection URL for the environment.
        
        Args:
            environment: Target environment
            include_credentials: Whether to include username/password in URL
            
        Returns:
            str: Complete ClickHouse HTTP URL
        """
        port = self.discover_http_port(environment)
        
        if include_credentials:
            # Get credentials from environment
            user = self._get_clickhouse_user(environment)
            password = self._get_clickhouse_password(environment)
            database = self._get_clickhouse_database(environment)
            
            if password:
                auth_part = f"{user}:{password}@"
            else:
                auth_part = f"{user}@" if user != "default" else ""
                
            url = f"http://{auth_part}localhost:{port}/{database}"
        else:
            url = f"http://localhost:{port}"
            
        return url
    
    def is_clickhouse_available(self, environment: Optional[str] = None) -> bool:
        """
        Check if ClickHouse is available on the discovered port.
        
        Args:
            environment: Target environment to check
            
        Returns:
            bool: True if ClickHouse is responding, False otherwise
        """
        try:
            port = self.discover_http_port(environment)
            return self._check_clickhouse_health(port)
        except Exception as e:
            self._logger.debug(f"ClickHouse availability check failed: {e}")
            return False
    
    def _detect_current_environment(self) -> str:
        """Detect the current environment from various sources."""
        # Check explicit test indicators first
        if (self._env.get("PYTEST_CURRENT_TEST") or 
            self._env.get("TESTING") == "1" or
            self._env.get("TEST_MODE") == "1"):
            return "test"
            
        # Check ENVIRONMENT variable
        env = self._env.get("ENVIRONMENT", "").lower()
        if env in ["testing", "test"]:
            return "test"
        elif env in ["development", "dev"]:
            return "dev"
            
        # Check if we're running in a Docker test environment
        if self._is_docker_test_environment():
            return "test"
            
        # Default to development
        return "dev"
    
    def _normalize_environment(self, environment: str) -> str:
        """Normalize environment name to standard form."""
        env_lower = environment.lower()
        if env_lower in ["test", "testing"]:
            return "test"
        elif env_lower in ["dev", "development"]:
            return "dev"
        else:
            # Default to dev for unknown environments
            return "dev"
    
    def _try_discovery_methods(self, environment: str) -> Optional[int]:
        """Try various port discovery methods in order of preference."""
        methods = [
            self._discover_from_environment_vars,
            self._discover_from_docker_compose,
            self._discover_from_running_containers,
            self._discover_from_defaults
        ]
        
        for method in methods:
            try:
                port = method(environment)
                if port is not None:
                    self._logger.debug(f"Port {port} discovered using {method.__name__}")
                    return port
            except Exception as e:
                self._logger.debug(f"Discovery method {method.__name__} failed: {e}")
                continue
                
        return None
    
    def _try_tcp_discovery_methods(self, environment: str) -> Optional[int]:
        """Try various TCP port discovery methods."""
        # Check environment variables first
        if environment == "test":
            port = self._env.get("TEST_CLICKHOUSE_TCP_PORT")
        else:
            port = self._env.get("CLICKHOUSE_TCP_PORT") or self._env.get("CLICKHOUSE_NATIVE_PORT")
            
        if port:
            try:
                return int(port)
            except ValueError:
                pass
                
        return None
    
    def _discover_from_environment_vars(self, environment: str) -> Optional[int]:
        """Discover port from environment variables."""
        if environment == "test":
            # Check test-specific environment variables
            port_vars = [
                "TEST_CLICKHOUSE_HTTP_PORT",
                "TEST_CLICKHOUSE_PORT"
            ]
        else:
            # Check development environment variables
            port_vars = [
                "CLICKHOUSE_HTTP_PORT", 
                "CLICKHOUSE_PORT"
            ]
        
        for var in port_vars:
            port_str = self._env.get(var)
            if port_str:
                try:
                    return int(port_str)
                except ValueError:
                    self._logger.warning(f"Invalid port value in {var}: {port_str}")
                    continue
                    
        return None
    
    def _discover_from_docker_compose(self, environment: str) -> Optional[int]:
        """Discover port from Docker compose configuration."""
        try:
            project_root = Path.cwd()
            
            if environment == "test":
                compose_file = project_root / "docker-compose.test.yml"
                service_name = "clickhouse-test"
            else:
                compose_file = project_root / "docker-compose.dev.yml"
                service_name = "clickhouse"
            
            if not compose_file.exists():
                return None
                
            # Use docker-compose config to parse the file
            result = subprocess.run([
                "docker-compose", "-f", str(compose_file), "config"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse the output to find port mappings
                port = self._parse_compose_config_for_port(result.stdout, service_name)
                if port:
                    return port
                    
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            self._logger.debug(f"Docker compose config parsing failed: {e}")
            
        return None
    
    def _discover_from_running_containers(self, environment: str) -> Optional[int]:
        """Discover port from running Docker containers."""
        try:
            if environment == "test":
                container_names = ["netra-test-clickhouse", "clickhouse-test"]
            else:
                container_names = ["netra-dev-clickhouse", "clickhouse"]
            
            for container_name in container_names:
                port = self._get_container_port_mapping(container_name, 8123)
                if port:
                    return port
                    
        except Exception as e:
            self._logger.debug(f"Container port discovery failed: {e}")
            
        return None
    
    def _discover_from_defaults(self, environment: str) -> Optional[int]:
        """Return default ports based on environment."""
        if environment == "test":
            return 8124  # TEST environment default
        else:
            return 8123  # DEV environment default
    
    def _parse_compose_config_for_port(self, config_output: str, service_name: str) -> Optional[int]:
        """Parse docker-compose config output for port mappings."""
        lines = config_output.split('\n')
        in_service = False
        in_ports = False
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith(f"{service_name}:"):
                in_service = True
                continue
                
            if in_service and stripped.startswith("ports:"):
                in_ports = True
                continue
                
            if in_service and in_ports:
                if stripped.startswith("- "):
                    # Parse port mapping like "- 8124:8123"
                    port_mapping = stripped[2:].strip().strip('"').strip("'")
                    if ":" in port_mapping:
                        external_port = port_mapping.split(":")[0]
                        try:
                            return int(external_port)
                        except ValueError:
                            continue
                elif not stripped.startswith("-") and stripped != "":
                    # End of ports section
                    break
                    
        return None
    
    def _get_container_port_mapping(self, container_name: str, internal_port: int) -> Optional[int]:
        """Get the external port mapping for a running container."""
        try:
            result = subprocess.run([
                "docker", "port", container_name, str(internal_port)
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                # Output format: "0.0.0.0:8124" or ":::8124"
                port_info = result.stdout.strip()
                if ":" in port_info:
                    external_port = port_info.split(":")[-1]
                    return int(external_port)
                    
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError) as e:
            self._logger.debug(f"Container port lookup failed for {container_name}: {e}")
            
        return None
    
    def _is_docker_test_environment(self) -> bool:
        """Check if we're running in a Docker test environment."""
        # Check for test container indicators
        hostname = self._env.get("HOSTNAME", "")
        if "test" in hostname.lower():
            return True
            
        # Check if backend port suggests test environment  
        port = self._env.get("PORT")
        if port == "8001":  # Test backend port
            return True
            
        return False
    
    def _check_clickhouse_health(self, port: int) -> bool:
        """Check if ClickHouse is responding on the given port."""
        try:
            import urllib.request
            
            health_url = f"http://localhost:{port}/ping"
            request = urllib.request.Request(health_url)
            
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status == 200
                
        except Exception as e:
            self._logger.debug(f"ClickHouse health check failed on port {port}: {e}")
            return False
    
    def _get_clickhouse_user(self, environment: Optional[str]) -> str:
        """Get ClickHouse username for the environment."""
        if environment == "test":
            return self._env.get("TEST_CLICKHOUSE_USER", "test")
        else:
            return self._env.get("CLICKHOUSE_USER", "netra")
    
    def _get_clickhouse_password(self, environment: Optional[str]) -> str:
        """Get ClickHouse password for the environment.""" 
        if environment == "test":
            return self._env.get("TEST_CLICKHOUSE_PASSWORD", "test")
        else:
            return self._env.get("CLICKHOUSE_PASSWORD", "netra123")
    
    def _get_clickhouse_database(self, environment: Optional[str]) -> str:
        """Get ClickHouse database name for the environment."""
        if environment == "test":
            return self._env.get("TEST_CLICKHOUSE_DB", "netra_test_analytics")
        else:
            return self._env.get("CLICKHOUSE_DB", "netra_analytics")


# Singleton instance for global access
_port_discovery = ClickHousePortDiscovery()


def discover_clickhouse_port(environment: Optional[str] = None) -> int:
    """
    Global function to discover ClickHouse HTTP port.
    
    Args:
        environment: Target environment ('dev', 'test', etc.)
        
    Returns:
        int: The ClickHouse HTTP port to use
    """
    return _port_discovery.discover_http_port(environment)


def get_clickhouse_url(environment: Optional[str] = None, 
                      include_credentials: bool = True) -> str:
    """
    Global function to get ClickHouse connection URL.
    
    Args:
        environment: Target environment
        include_credentials: Whether to include auth in URL
        
    Returns:
        str: Complete ClickHouse connection URL
    """
    return _port_discovery.get_connection_url(environment, include_credentials)


def is_clickhouse_available(environment: Optional[str] = None) -> bool:
    """
    Global function to check ClickHouse availability.
    
    Args:
        environment: Target environment to check
        
    Returns:
        bool: True if ClickHouse is responding
    """
    return _port_discovery.is_clickhouse_available(environment)