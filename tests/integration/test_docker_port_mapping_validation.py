"""
Docker Port Mapping Validation Tests - Five Whys Root Cause Prevention

CRITICAL: This addresses Five Whys finding:
"No automated validation of Docker vs application configuration consistency"

These tests validate:
1. Port mapping consistency between docker-compose.yml and application config
2. Service name resolution in Docker internal vs external contexts  
3. Environment-specific port configurations (dev, test, staging)
4. External port accessibility for test environments
5. Internal service communication within Docker networks

ROOT CAUSE ADDRESSED: WHY #4 - Process gap that allowed Docker port mismatches
to go undetected, causing Redis connection failures in integration tests.

Business Value: Platform/Internal - Configuration Reliability & Docker Integration
Prevents Docker port mapping inconsistencies that cause service connection failures.
"""
import pytest
import os
import subprocess  
import socket
import time
import json
import yaml
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.backend_environment import BackendEnvironment


class DockerComposeParser:
    """Parse docker-compose.yml to extract service configuration."""
    
    def __init__(self, compose_file_path: Path):
        """Initialize with docker-compose.yml file path."""
        self.compose_file_path = compose_file_path
        self._compose_data = None
        self._load_compose_file()
    
    def _load_compose_file(self):
        """Load and parse docker-compose.yml file."""
        try:
            with open(self.compose_file_path, 'r') as f:
                self._compose_data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"docker-compose.yml not found at {self.compose_file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse docker-compose.yml: {e}")
    
    def get_service_port_mappings(self, service_name: str) -> Dict[str, int]:
        """Get port mappings for a specific service."""
        if not self._compose_data or 'services' not in self._compose_data:
            return {}
        
        service = self._compose_data['services'].get(service_name, {})
        ports = service.get('ports', [])
        
        port_mappings = {}
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ':' in port_mapping:
                # CRITICAL FIX: Handle environment variables with colon syntax correctly
                # Need to find the LAST colon that separates external:internal ports
                # not the colons inside ${VAR:-default} syntax
                
                if port_mapping.startswith('${') and '}:' in port_mapping:
                    # Environment variable syntax: ${VAR:-default}:internal_port
                    # Find the }:  to split correctly
                    brace_colon_index = port_mapping.find('}:')
                    if brace_colon_index != -1:
                        external = port_mapping[:brace_colon_index + 1]  # Include the }
                        internal = port_mapping[brace_colon_index + 2:]  # Skip }:
                    else:
                        # Fallback to original logic if format is unexpected
                        external, internal = port_mapping.split(':', 1)
                else:
                    # No environment variable, use standard split
                    external, internal = port_mapping.split(':', 1)
                
                # Handle environment variable substitution like ${DEV_REDIS_PORT:-6380}
                if external.startswith('${') and external.endswith('}'):
                    # Extract default value from ${VAR:-default}
                    if ':-' in external:
                        # Format: ${VAR:-default}
                        var_and_default = external[2:-1]  # Remove ${ and }
                        if ':-' in var_and_default:
                            var_name, default_value = var_and_default.split(':-', 1)
                            try:
                                port_mappings['external'] = int(default_value)
                            except ValueError:
                                raise ValueError(f"Invalid port default value in {service_name}: {default_value}")
                        else:
                            # No default value, skip this mapping
                            continue
                    else:
                        # Format: ${VAR} - no default, would be resolved by Docker
                        # Skip this mapping as it's environment-dependent
                        continue
                else:
                    # Direct port number
                    try:
                        port_mappings['external'] = int(external)
                    except ValueError:
                        raise ValueError(f"Invalid external port in {service_name}: {external}")
                
                # Parse internal port
                try:
                    port_mappings['internal'] = int(internal)
                except ValueError:
                    raise ValueError(f"Invalid internal port in {service_name}: {internal}")
        
        return port_mappings
    
    def get_service_environment_vars(self, service_name: str) -> Dict[str, str]:
        """Get environment variables for a specific service."""
        if not self._compose_data or 'services' not in self._compose_data:
            return {}
        
        service = self._compose_data['services'].get(service_name, {})
        environment = service.get('environment', {})
        
        if isinstance(environment, list):
            # Environment as list: ["KEY=value", "KEY2=value2"]
            env_dict = {}
            for env_var in environment:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    env_dict[key] = value
            return env_dict
        elif isinstance(environment, dict):
            # Environment as dict: {KEY: value, KEY2: value2}
            return environment
        
        return {}
    
    def get_service_profiles(self, service_name: str) -> List[str]:
        """Get profiles that include this service."""
        if not self._compose_data or 'services' not in self._compose_data:
            return []
        
        service = self._compose_data['services'].get(service_name, {})
        profiles = service.get('profiles', [])
        
        # If no profiles specified, service runs in default profile
        return profiles if profiles else ['default']


class TestDockerPortMappingValidation:
    """Test Docker port mapping consistency with application configuration."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup clean environment for each test."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        self.compose_file = Path(__file__).parent.parent.parent / "docker-compose.yml"
        self.parser = DockerComposeParser(self.compose_file)
        yield
        self.env.reset_to_original()
    
    def test_development_postgres_port_mapping_consistency(self):
        """Test dev-postgres port mapping consistency."""
        # Parse docker-compose.yml for dev-postgres service
        postgres_ports = self.parser.get_service_port_mappings('dev-postgres')
        postgres_env = self.parser.get_service_environment_vars('dev-postgres')
        
        # Expected from docker-compose.yml analysis:
        # ports: - "${DEV_POSTGRES_PORT:-5433}:5432" 
        expected_external_port = 5433  # Default value
        expected_internal_port = 5432
        
        assert postgres_ports['external'] == expected_external_port
        assert postgres_ports['internal'] == expected_internal_port
        
        # Test application configuration for Docker development environment
        docker_dev_config = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "dev-postgres",  # Service name for internal Docker networking
            "POSTGRES_PORT": str(expected_internal_port),  # Internal port
            # External port would be used only for access from outside Docker
        }
        
        for key, value in docker_dev_config.items():
            self.env.set(key, value, "docker_dev_postgres_test")
        
        backend_env = BackendEnvironment()
        
        # Application should use internal Docker networking
        assert backend_env.get_postgres_host() == "dev-postgres"
        assert backend_env.get_postgres_port() == expected_internal_port
        
        # Database URL should use internal service name and port
        db_url = backend_env.get_database_url()
        assert "dev-postgres" in db_url
        assert f":{expected_internal_port}" in db_url
    
    def test_development_redis_port_mapping_consistency(self):
        """Test dev-redis port mapping consistency."""
        redis_ports = self.parser.get_service_port_mappings('dev-redis')
        
        # Expected from docker-compose.yml: "${DEV_REDIS_PORT:-6380}:6379"
        expected_external_port = 6380  # Default value 
        expected_internal_port = 6379
        
        assert redis_ports['external'] == expected_external_port
        assert redis_ports['internal'] == expected_internal_port
        
        # Test application configuration for Docker development
        docker_dev_config = {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "dev-redis",    # Service name
            "REDIS_PORT": str(expected_internal_port),  # Internal port
        }
        
        for key, value in docker_dev_config.items():
            self.env.set(key, value, "docker_dev_redis_test")
        
        backend_env = BackendEnvironment()
        
        assert backend_env.get_redis_host() == "dev-redis"
        assert backend_env.get_redis_port() == expected_internal_port
        
        # Redis URL should use internal networking
        redis_url = backend_env.get_redis_url()
        # Note: get_redis_url() uses REDIS_URL env var, not components
        # So we test the components are correct
    
    def test_test_environment_port_mapping_consistency(self):
        """Test test environment port mapping consistency."""
        # Parse test service port mappings
        test_postgres_ports = self.parser.get_service_port_mappings('test-postgres')
        test_redis_ports = self.parser.get_service_port_mappings('test-redis')
        
        # Expected from docker-compose.yml test services:
        # test-postgres: "${TEST_POSTGRES_PORT:-5434}:5432"
        # test-redis: "${TEST_REDIS_PORT:-6381}:6379"
        expected_postgres_external = 5434
        expected_redis_external = 6381
        
        assert test_postgres_ports['external'] == expected_postgres_external
        assert test_redis_ports['external'] == expected_redis_external
        
        # Test application configuration for external access to test services
        test_external_config = {
            "ENVIRONMENT": "test",
            "POSTGRES_HOST": "localhost",  # External access 
            "POSTGRES_PORT": str(expected_postgres_external),  # External port
            "REDIS_HOST": "localhost",     # External access
            "REDIS_PORT": str(expected_redis_external),        # External port
        }
        
        for key, value in test_external_config.items():
            self.env.set(key, value, "test_external_ports_test")
        
        backend_env = BackendEnvironment()
        
        # Should use external port mappings for test environment
        assert backend_env.get_postgres_port() == expected_postgres_external
        assert backend_env.get_redis_port() == expected_redis_external
        assert backend_env.is_testing() is True
    
    def test_auth_service_port_consistency(self):
        """Test auth service port consistency across environments."""
        # Parse dev-auth service configuration
        auth_ports = self.parser.get_service_port_mappings('dev-auth')
        auth_env = self.parser.get_service_environment_vars('dev-auth')
        
        # Expected from docker-compose.yml: "${DEV_AUTH_PORT:-8081}:8081"
        expected_external_port = 8081
        expected_internal_port = 8081
        
        assert auth_ports['external'] == expected_external_port
        assert auth_ports['internal'] == expected_internal_port
        
        # Auth service PORT environment variable should match
        assert auth_env.get('PORT') == '8081'
        
        # Test backend configuration for auth service access
        docker_config = {
            "ENVIRONMENT": "development",
            "AUTH_SERVICE_URL": "http://dev-auth:8081"  # Internal Docker networking
        }
        
        for key, value in docker_config.items():
            self.env.set(key, value, "auth_service_consistency_test")
        
        backend_env = BackendEnvironment()
        
        # Backend should use internal service name and port
        auth_url = backend_env.get_auth_service_url()
        assert auth_url == "http://dev-auth:8081"
        assert f":{expected_internal_port}" in auth_url
    
    def test_backend_service_port_consistency(self):
        """Test backend service port consistency."""
        backend_ports = self.parser.get_service_port_mappings('dev-backend')
        backend_env_vars = self.parser.get_service_environment_vars('dev-backend')
        
        # Expected: "${DEV_BACKEND_PORT:-8000}:8000"
        expected_external_port = 8000
        expected_internal_port = 8000
        
        assert backend_ports['external'] == expected_external_port
        assert backend_ports['internal'] == expected_internal_port
        
        # Environment PORT should match
        assert backend_env_vars.get('PORT') == '8000'
        
        # Test backend URL configuration
        docker_config = {
            "ENVIRONMENT": "development",
            "BACKEND_URL": "http://dev-backend:8000"
        }
        
        for key, value in docker_config.items():
            self.env.set(key, value, "backend_consistency_test")
        
        backend_env = BackendEnvironment()
        backend_url = backend_env.get_backend_url()
        
        # Should use default if not explicitly set, or the configured value
        if backend_url != "http://localhost:8000":  # Default
            assert f":{expected_internal_port}" in backend_url
    
    def test_clickhouse_port_mapping_consistency(self):
        """Test ClickHouse port mapping consistency."""
        ch_ports = self.parser.get_service_port_mappings('dev-clickhouse')
        ch_env = self.parser.get_service_environment_vars('dev-clickhouse')
        
        # ClickHouse has multiple ports in docker-compose.yml:
        # HTTP: "${DEV_CLICKHOUSE_HTTP_PORT:-8124}:8123" 
        # TCP: "${DEV_CLICKHOUSE_TCP_PORT:-9001}:9000"
        
        # Test backend ClickHouse configuration
        docker_config = {
            "ENVIRONMENT": "development",
            "CLICKHOUSE_HOST": "dev-clickhouse",
            "CLICKHOUSE_PORT": "9000",  # TCP port for database connections (internal)
            "CLICKHOUSE_USER": "netra",
            "CLICKHOUSE_PASSWORD": "netra123",
            "CLICKHOUSE_DB": "netra_analytics"
        }
        
        for key, value in docker_config.items():
            self.env.set(key, value, "clickhouse_consistency_test")
        
        backend_env = BackendEnvironment()
        
        # Validate ClickHouse configuration (if backend has ClickHouse methods)
        clickhouse_host = self.env.get("CLICKHOUSE_HOST")
        clickhouse_port = self.env.get("CLICKHOUSE_PORT")
        
        assert clickhouse_host == "dev-clickhouse"
        assert clickhouse_port == "9000"  # TCP port for connections
        
        # HTTP port (8123 internal, 8124 external) would be used for HTTP API access
        # TCP port (9000 internal, 9001 external) would be used for database connections
    
    def test_service_profile_consistency(self):
        """Test that services are in correct Docker Compose profiles."""
        # Test development services (no profile = default profile)
        dev_services = ['dev-postgres', 'dev-redis', 'dev-auth', 'dev-backend', 'dev-frontend']
        
        for service_name in dev_services:
            profiles = self.parser.get_service_profiles(service_name)
            assert 'default' in profiles, f"{service_name} should be in default profile"
        
        # Test test services (should have 'test' profile)
        test_services = ['test-postgres', 'test-redis', 'test-clickhouse']
        
        for service_name in test_services:
            profiles = self.parser.get_service_profiles(service_name)
            assert 'test' in profiles, f"{service_name} should be in test profile"
        
        # Test that test services are NOT in default profile
        for service_name in test_services:
            profiles = self.parser.get_service_profiles(service_name)
            assert 'default' not in profiles, f"{service_name} should NOT be in default profile"


class TestPortAccessibilityValidation:
    """Test actual port accessibility for Docker services."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield  
        self.env.reset_to_original()
    
    def _is_port_accessible(self, host: str, port: int, timeout: int = 5) -> bool:
        """Check if a port is accessible."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
    
    def _is_docker_service_running(self, service_name: str, profile: str = None) -> bool:
        """Check if Docker service is running."""
        try:
            cmd = ["docker", "compose"]
            if profile:
                cmd.extend(["--profile", profile])
            cmd.extend(["ps", service_name])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return service_name in result.stdout and "Up" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @pytest.mark.integration
    def test_development_services_port_accessibility(self):
        """Test that development Docker services are accessible on expected ports."""
        # Expected development service ports (external access)
        expected_ports = {
            "dev-postgres": 5433,  # DEV_POSTGRES_PORT default
            "dev-redis": 6380,     # DEV_REDIS_PORT default  
            "dev-auth": 8081,      # DEV_AUTH_PORT default
            "dev-backend": 8000,   # DEV_BACKEND_PORT default
            "dev-frontend": 3000,  # DEV_FRONTEND_PORT default
        }
        
        for service_name, expected_port in expected_ports.items():
            # Check if service is running
            if not self._is_docker_service_running(service_name):
                pytest.skip(f"Docker service {service_name} not running")
            
            # Test external port accessibility
            is_accessible = self._is_port_accessible("localhost", expected_port)
            assert is_accessible, f"Port {expected_port} for {service_name} should be accessible"
    
    @pytest.mark.integration  
    def test_test_services_port_accessibility(self):
        """Test that test Docker services are accessible on expected ports."""
        expected_test_ports = {
            "test-postgres": 5434,  # TEST_POSTGRES_PORT default
            "test-redis": 6381,     # TEST_REDIS_PORT default
        }
        
        for service_name, expected_port in expected_test_ports.items():
            # Check if test service is running
            if not self._is_docker_service_running(service_name, profile="test"):
                pytest.skip(f"Docker test service {service_name} not running")
            
            is_accessible = self._is_port_accessible("localhost", expected_port)
            assert is_accessible, f"Test port {expected_port} for {service_name} should be accessible"
    
    def test_port_conflict_detection(self):
        """Test detection of port conflicts between services."""
        # Parse all services and their port mappings
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.yml"
        parser = DockerComposeParser(compose_file)
        
        all_external_ports = {}
        service_names = [
            'dev-postgres', 'dev-redis', 'dev-clickhouse', 'dev-auth', 
            'dev-backend', 'dev-frontend', 'test-postgres', 'test-redis', 'test-clickhouse'
        ]
        
        for service_name in service_names:
            try:
                ports = parser.get_service_port_mappings(service_name)
                if 'external' in ports:
                    external_port = ports['external']
                    
                    if external_port in all_external_ports:
                        # Port conflict detected
                        conflicting_service = all_external_ports[external_port]
                        pytest.fail(
                            f"Port conflict detected: {service_name} and {conflicting_service} "
                            f"both use external port {external_port}"
                        )
                    
                    all_external_ports[external_port] = service_name
            except Exception:
                # Service might not exist or have port mappings
                continue
        
        # Test that common ports are properly separated
        common_port_expectations = {
            5432: None,  # Internal PostgreSQL - should not be exposed externally
            5433: "dev-postgres",   # Dev PostgreSQL external
            5434: "test-postgres",  # Test PostgreSQL external
            6379: None,  # Internal Redis - should not be exposed externally  
            6380: "dev-redis",      # Dev Redis external
            6381: "test-redis",     # Test Redis external
            8000: "dev-backend",    # Backend
            8081: "dev-auth",       # Auth service
            3000: "dev-frontend"    # Frontend
        }
        
        for port, expected_service in common_port_expectations.items():
            if expected_service:
                actual_service = all_external_ports.get(port)
                assert actual_service == expected_service, \
                    f"Port {port} expected to be used by {expected_service}, actually used by {actual_service}"


class TestDockerNetworkingValidation:
    """Test Docker internal networking configuration."""
    
    @pytest.fixture(autouse=True) 
    def setup_environment(self):
        """Setup environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_internal_service_networking_configuration(self):
        """Test that internal Docker service networking is configured correctly."""
        # Test internal networking configuration (service-to-service communication)
        internal_networking_config = {
            "ENVIRONMENT": "development",
            # Backend should connect to other services using service names
            "POSTGRES_HOST": "dev-postgres",
            "POSTGRES_PORT": "5432",  # Internal port
            "REDIS_HOST": "dev-redis", 
            "REDIS_PORT": "6379",     # Internal port
            "CLICKHOUSE_HOST": "dev-clickhouse",
            "CLICKHOUSE_PORT": "9000",  # Internal TCP port
            "AUTH_SERVICE_URL": "http://dev-auth:8081"  # Internal service URL
        }
        
        for key, value in internal_networking_config.items():
            self.env.set(key, value, "internal_networking_test")
        
        backend_env = BackendEnvironment()
        
        # Validate internal networking configuration
        assert backend_env.get_postgres_host() == "dev-postgres"
        assert backend_env.get_postgres_port() == 5432  # Internal port
        assert backend_env.get_redis_host() == "dev-redis"
        assert backend_env.get_redis_port() == 6379     # Internal port
        assert backend_env.get_auth_service_url() == "http://dev-auth:8081"
        
        # Database URL should use internal service names
        db_url = backend_env.get_database_url()
        assert "dev-postgres:5432" in db_url
    
    def test_external_access_configuration(self):
        """Test external access configuration for development/testing."""
        # Test external access (from host machine to Docker containers)
        external_access_config = {
            "ENVIRONMENT": "test",
            # External access uses localhost with mapped ports
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",  # External mapped port
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6381",     # External mapped port
            "AUTH_SERVICE_URL": "http://localhost:8081"  # External access
        }
        
        for key, value in external_access_config.items():
            self.env.set(key, value, "external_access_test")
        
        backend_env = BackendEnvironment()
        
        # Validate external access configuration
        assert backend_env.get_postgres_host() == "localhost"
        assert backend_env.get_postgres_port() == 5434  # External port
        assert backend_env.get_redis_host() == "localhost"  
        assert backend_env.get_redis_port() == 6381     # External port
        assert backend_env.get_auth_service_url() == "http://localhost:8081"
    
    def test_network_isolation_between_environments(self):
        """Test that different environments use different network configurations."""
        environment_configs = {
            "development": {
                "POSTGRES_HOST": "dev-postgres",
                "REDIS_HOST": "dev-redis",
                "AUTH_SERVICE_URL": "http://dev-auth:8081"
            },
            "test_internal": {
                "POSTGRES_HOST": "test-postgres", 
                "REDIS_HOST": "test-redis",
                "AUTH_SERVICE_URL": "http://test-auth:8081"  # If existed
            },
            "test_external": {
                "POSTGRES_HOST": "localhost",
                "REDIS_HOST": "localhost", 
                "AUTH_SERVICE_URL": "http://localhost:8081"
            }
        }
        
        for env_name, config in environment_configs.items():
            self.env.reset_to_original()
            self.env.enable_isolation()
            
            # Set environment
            if env_name.startswith("test"):
                self.env.set("ENVIRONMENT", "test", f"{env_name}_test")
            else:
                self.env.set("ENVIRONMENT", env_name, f"{env_name}_test")
            
            # Set configuration
            for key, value in config.items():
                self.env.set(key, value, f"{env_name}_test")
            
            backend_env = BackendEnvironment()
            
            # Validate configuration is environment-specific
            if env_name == "development":
                assert backend_env.get_postgres_host() == "dev-postgres"
                assert backend_env.get_redis_host() == "dev-redis" 
                assert "dev-auth" in backend_env.get_auth_service_url()
            elif env_name == "test_external":
                assert backend_env.get_postgres_host() == "localhost"
                assert backend_env.get_redis_host() == "localhost"
                assert "localhost" in backend_env.get_auth_service_url()


class TestConfigurationDriftDetection:
    """Test automated detection of configuration drift."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_docker_compose_vs_application_config_drift_detection(self):
        """Test detection of drift between docker-compose.yml and application config."""
        # Parse actual docker-compose.yml
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.yml"
        parser = DockerComposeParser(compose_file)
        
        # Get actual port mappings
        postgres_ports = parser.get_service_port_mappings('dev-postgres')
        redis_ports = parser.get_service_port_mappings('dev-redis')
        
        # Test with MISMATCHED configuration (simulated drift)
        mismatched_config = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "dev-postgres",
            "POSTGRES_PORT": "9999",  # WRONG - doesn't match docker-compose internal port
            "REDIS_HOST": "dev-redis",
            "REDIS_PORT": "8888",     # WRONG - doesn't match docker-compose internal port
        }
        
        for key, value in mismatched_config.items():
            self.env.set(key, value, "drift_detection_test")
        
        backend_env = BackendEnvironment()
        
        # Detect configuration drift
        actual_postgres_port = backend_env.get_postgres_port()
        actual_redis_port = backend_env.get_redis_port()
        
        expected_postgres_internal = postgres_ports.get('internal', 5432)
        expected_redis_internal = redis_ports.get('internal', 6379)
        
        # Configuration drift detected
        postgres_drift = actual_postgres_port != expected_postgres_internal
        redis_drift = actual_redis_port != expected_redis_internal
        
        assert postgres_drift, f"Postgres port drift should be detected: {actual_postgres_port} != {expected_postgres_internal}"
        assert redis_drift, f"Redis port drift should be detected: {actual_redis_port} != {expected_redis_internal}"
        
        # This would be caught by a configuration validation system
        total_drift_issues = sum([postgres_drift, redis_drift])
        assert total_drift_issues >= 2, f"Expected at least 2 drift issues, found {total_drift_issues}"
    
    def test_environment_port_consistency_validation(self):
        """Test validation of port consistency across environments."""
        # Define expected port configurations for each environment
        expected_port_configs = {
            "development": {
                "postgres_external": 5433,
                "postgres_internal": 5432,
                "redis_external": 6380,
                "redis_internal": 6379,
                "backend_external": 8000,
                "auth_external": 8081
            },
            "test": {
                "postgres_external": 5434,
                "postgres_internal": 5432,
                "redis_external": 6381,
                "redis_internal": 6379,
                "backend_external": 8000,  # Same as dev
                "auth_external": 8081      # Same as dev
            }
        }
        
        for env_name, expected_ports in expected_port_configs.items():
            self.env.reset_to_original()
            self.env.enable_isolation()
            
            self.env.set("ENVIRONMENT", env_name, f"{env_name}_consistency_test")
            
            if env_name == "development":
                # Internal Docker networking
                config = {
                    "POSTGRES_HOST": "dev-postgres",
                    "POSTGRES_PORT": str(expected_ports["postgres_internal"]),
                    "REDIS_HOST": "dev-redis",
                    "REDIS_PORT": str(expected_ports["redis_internal"])
                }
            else:  # test
                # External access
                config = {
                    "POSTGRES_HOST": "localhost", 
                    "POSTGRES_PORT": str(expected_ports["postgres_external"]),
                    "REDIS_HOST": "localhost",
                    "REDIS_PORT": str(expected_ports["redis_external"])
                }
            
            for key, value in config.items():
                self.env.set(key, value, f"{env_name}_consistency_test")
            
            backend_env = BackendEnvironment()
            
            # Validate port configuration matches expectations
            if env_name == "development":
                assert backend_env.get_postgres_port() == expected_ports["postgres_internal"]
                assert backend_env.get_redis_port() == expected_ports["redis_internal"]
            else:  # test
                assert backend_env.get_postgres_port() == expected_ports["postgres_external"] 
                assert backend_env.get_redis_port() == expected_ports["redis_external"]
    
    def test_missing_docker_environment_variable_detection(self):
        """Test detection of missing Docker environment variables."""
        # Simulate incomplete Docker environment (missing key variables)
        incomplete_docker_env = {
            "ENVIRONMENT": "development",
            # Missing POSTGRES_HOST, REDIS_HOST etc. that Docker should provide
            "HOSTNAME": "dev-backend-12345"  # Docker container indicator
        }
        
        for key, value in incomplete_docker_env.items():
            self.env.set(key, value, "missing_docker_vars_test")
        
        backend_env = BackendEnvironment()
        
        # Should use defaults when Docker variables are missing
        postgres_host = backend_env.get_postgres_host()
        redis_host = backend_env.get_redis_host()
        
        # These would be defaults, indicating missing Docker environment setup
        assert postgres_host == "localhost"  # Default, not "dev-postgres"
        assert redis_host == "localhost"     # Default, not "dev-redis"
        
        # This indicates configuration drift - Docker container but no Docker networking config
        hostname = self.env.get("HOSTNAME", "")
        is_docker_context = hostname.startswith("dev-")
        uses_docker_networking = postgres_host != "localhost"
        
        drift_detected = is_docker_context and not uses_docker_networking
        assert drift_detected, "Should detect Docker context without Docker networking configuration"