"""
Docker Configuration Loader - SSOT for Docker Environment Configuration

Provides typed access to centralized Docker environment configuration.
Follows CLAUDE.md type safety requirements and SSOT principles.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Eliminate configuration drift, enable reliable multi-environment deployment
3. Value Impact: Prevents configuration errors, enables consistent Docker operations
4. Revenue Impact: Reduces development time by 2-4 hours/week, prevents production issues
"""

import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

# CLAUDE.md compliance: Use IsolatedEnvironment for all environment access
from shared.isolated_environment import get_env


class DockerEnvironment(Enum):
    """Supported Docker environments."""
    DEVELOPMENT = "development"
    TEST = "test" 
    ALPINE_TEST = "alpine_test"
    ALPINE_DEVELOPMENT = "alpine_development"
    PRODUCTION = "production"


@dataclass(frozen=True)
class CredentialsConfig:
    """Docker environment credentials configuration."""
    postgres_user: str
    postgres_password: str
    postgres_db: str
    clickhouse_user: Optional[str] = None
    clickhouse_password: Optional[str] = None
    clickhouse_db: Optional[str] = None
    rabbitmq_user: Optional[str] = None
    rabbitmq_password: Optional[str] = None
    redis_password: Optional[str] = None


@dataclass(frozen=True)
class PortsConfig:
    """Docker environment ports configuration."""
    backend: int
    auth: int
    frontend: int
    postgres: int
    redis: int
    clickhouse_http: Optional[int] = None
    clickhouse_tcp: Optional[int] = None
    rabbitmq: Optional[int] = None
    rabbitmq_mgmt: Optional[int] = None
    monitor: Optional[int] = None


@dataclass(frozen=True)
class HealthCheckConfig:
    """Docker health check configuration."""
    timeout: int
    retries: int
    interval: int
    start_period: int


@dataclass(frozen=True)
class ResourceLimitsConfig:
    """Docker resource limits configuration."""
    memory_limits: Dict[str, str]
    cpu_limits: Dict[str, str]


@dataclass(frozen=True)
class VolumeConfig:
    """Docker volume configuration."""
    use_tmpfs: Optional[bool] = None
    tmpfs_size: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class PerformanceOptimizations:
    """Performance optimization settings for services."""
    postgres: Optional[Dict[str, Union[str, int]]] = None
    redis: Optional[Dict[str, Union[str, int, bool]]] = None
    clickhouse: Optional[Dict[str, Union[str, int]]] = None


@dataclass(frozen=True)
class DockerEnvironmentConfig:
    """Complete Docker environment configuration."""
    compose_file: str
    prefix: str
    project_name_prefix: str
    profiles: List[str]
    credentials: CredentialsConfig
    ports: PortsConfig
    health_check: HealthCheckConfig
    memory_limits: Dict[str, str]
    cpu_limits: Dict[str, str]
    environment_variables: Dict[str, Union[str, bool, int]]
    volume_config: Optional[VolumeConfig] = None
    performance_optimizations: Optional[PerformanceOptimizations] = None


@dataclass(frozen=True)
class GlobalConfig:
    """Global Docker configuration settings."""
    network: Dict[str, Union[str, int]]
    volumes: Dict[str, int]
    build: Dict[str, str]
    services: Dict[str, Dict[str, str]]
    image_tags: Dict[str, Dict[str, str]]


@dataclass(frozen=True)
class SecretsConfig:
    """Environment-specific secrets configuration."""
    jwt_secret_key: str
    service_secret: str
    fernet_key: Optional[str] = None
    secret_key: Optional[str] = None


class DockerConfigurationError(Exception):
    """Raised when Docker configuration is invalid or missing."""
    pass


class DockerConfigLoader:
    """
    Loads and provides typed access to Docker environment configuration.
    
    CRITICAL: This is the SSOT for all Docker configuration access.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize Docker configuration loader.
        
        Args:
            config_path: Optional path to configuration file. 
                        Defaults to config/docker_environments.yaml in project root.
        """
        if config_path is None:
            # Find project root by looking for docker-compose.yml
            current_dir = Path(__file__).parent
            project_root = current_dir
            
            # Search up the directory tree for the project root
            max_depth = 10
            depth = 0
            while depth < max_depth:
                if (project_root / "docker-compose.yml").exists():
                    break
                parent = project_root.parent
                if parent == project_root:  # Reached filesystem root
                    break
                project_root = parent
                depth += 1
            
            config_path = project_root / "config" / "docker_environments.yaml"
        
        self.config_path = config_path
        self._config_data: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if not self.config_path.exists():
                raise DockerConfigurationError(
                    f"Docker configuration file not found: {self.config_path}"
                )
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f)
            
            if not isinstance(self._config_data, dict):
                raise DockerConfigurationError(
                    f"Invalid configuration format in {self.config_path}"
                )
                
            # Validate required sections
            required_sections = ['environments', 'global', 'secrets']
            for section in required_sections:
                if section not in self._config_data:
                    raise DockerConfigurationError(
                        f"Missing required section '{section}' in {self.config_path}"
                    )
                    
        except yaml.YAMLError as e:
            raise DockerConfigurationError(
                f"Failed to parse YAML configuration {self.config_path}: {e}"
            ) from e
        except Exception as e:
            raise DockerConfigurationError(
                f"Failed to load Docker configuration from {self.config_path}: {e}"
            ) from e
    
    def get_environment_config(self, environment: Union[str, DockerEnvironment]) -> DockerEnvironmentConfig:
        """
        Get configuration for a specific environment.
        
        Args:
            environment: Environment name or DockerEnvironment enum
            
        Returns:
            DockerEnvironmentConfig for the specified environment
            
        Raises:
            DockerConfigurationError: If environment not found or configuration invalid
        """
        if isinstance(environment, DockerEnvironment):
            env_name = environment.value
        else:
            env_name = environment
        
        if not self._config_data:
            raise DockerConfigurationError("Configuration not loaded")
        
        environments = self._config_data.get('environments', {})
        if env_name not in environments:
            available = list(environments.keys())
            raise DockerConfigurationError(
                f"Environment '{env_name}' not found. Available: {available}"
            )
        
        env_config = environments[env_name]
        
        try:
            # Parse credentials
            creds_data = env_config.get('credentials', {})
            credentials = CredentialsConfig(**creds_data)
            
            # Parse ports
            ports_data = env_config.get('ports', {})
            ports = PortsConfig(**ports_data)
            
            # Parse health check
            health_data = env_config.get('health_check', {})
            health_check = HealthCheckConfig(**health_data)
            
            # Parse volume config if present
            volume_config = None
            if 'volume_config' in env_config:
                volume_data = env_config['volume_config']
                volume_config = VolumeConfig(**volume_data)
            
            # Parse performance optimizations if present
            performance_opts = None
            if 'performance_optimizations' in env_config:
                perf_data = env_config['performance_optimizations']
                performance_opts = PerformanceOptimizations(**perf_data)
            
            return DockerEnvironmentConfig(
                compose_file=env_config['compose_file'],
                prefix=env_config['prefix'],
                project_name_prefix=env_config['project_name_prefix'],
                profiles=env_config.get('profiles', []),
                credentials=credentials,
                ports=ports,
                health_check=health_check,
                memory_limits=env_config.get('memory_limits', {}),
                cpu_limits=env_config.get('cpu_limits', {}),
                environment_variables=env_config.get('environment_variables', {}),
                volume_config=volume_config,
                performance_optimizations=performance_opts
            )
            
        except TypeError as e:
            raise DockerConfigurationError(
                f"Invalid configuration structure for environment '{env_name}': {e}"
            ) from e
    
    def get_global_config(self) -> GlobalConfig:
        """
        Get global Docker configuration.
        
        Returns:
            GlobalConfig with global Docker settings
        """
        if not self._config_data:
            raise DockerConfigurationError("Configuration not loaded")
        
        global_data = self._config_data.get('global', {})
        
        try:
            return GlobalConfig(
                network=global_data.get('network', {}),
                volumes=global_data.get('volumes', {}),
                build=global_data.get('build', {}),
                services=global_data.get('services', {}),
                image_tags=global_data.get('image_tags', {})
            )
        except TypeError as e:
            raise DockerConfigurationError(
                f"Invalid global configuration structure: {e}"
            ) from e
    
    def get_secrets_config(self, environment: Union[str, DockerEnvironment]) -> SecretsConfig:
        """
        Get secrets configuration for a specific environment.
        
        Args:
            environment: Environment name or DockerEnvironment enum
            
        Returns:
            SecretsConfig for the specified environment
        """
        if isinstance(environment, DockerEnvironment):
            env_name = environment.value
        else:
            env_name = environment
        
        if not self._config_data:
            raise DockerConfigurationError("Configuration not loaded")
        
        secrets_data = self._config_data.get('secrets', {})
        if env_name not in secrets_data:
            available = list(secrets_data.keys())
            raise DockerConfigurationError(
                f"Secrets for environment '{env_name}' not found. Available: {available}"
            )
        
        env_secrets = secrets_data[env_name]
        
        try:
            return SecretsConfig(**env_secrets)
        except TypeError as e:
            raise DockerConfigurationError(
                f"Invalid secrets configuration for environment '{env_name}': {e}"
            ) from e
    
    def get_available_environments(self) -> List[str]:
        """
        Get list of available environment names.
        
        Returns:
            List of available environment names
        """
        if not self._config_data:
            raise DockerConfigurationError("Configuration not loaded")
        
        return list(self._config_data.get('environments', {}).keys())
    
    def validate_environment(self, environment: Union[str, DockerEnvironment]) -> bool:
        """
        Validate that an environment exists and has required configuration.
        
        Args:
            environment: Environment name or DockerEnvironment enum
            
        Returns:
            True if environment is valid, False otherwise
        """
        try:
            self.get_environment_config(environment)
            return True
        except DockerConfigurationError:
            return False
    
    def get_port_for_service(self, environment: Union[str, DockerEnvironment], service: str) -> Optional[int]:
        """
        Get port number for a specific service in an environment.
        
        Args:
            environment: Environment name or DockerEnvironment enum
            service: Service name (e.g., 'backend', 'auth', 'postgres')
            
        Returns:
            Port number if found, None otherwise
        """
        try:
            env_config = self.get_environment_config(environment)
            return getattr(env_config.ports, service, None)
        except DockerConfigurationError:
            return None
    
    def get_memory_limit_for_service(self, environment: Union[str, DockerEnvironment], service: str) -> Optional[str]:
        """
        Get memory limit for a specific service in an environment.
        
        Args:
            environment: Environment name or DockerEnvironment enum
            service: Service name (e.g., 'backend', 'auth', 'postgres')
            
        Returns:
            Memory limit string if found, None otherwise
        """
        try:
            env_config = self.get_environment_config(environment)
            return env_config.memory_limits.get(service)
        except DockerConfigurationError:
            return None
    
    def get_compose_file_path(self, environment: Union[str, DockerEnvironment]) -> Optional[Path]:
        """
        Get full path to compose file for an environment.
        
        Args:
            environment: Environment name or DockerEnvironment enum
            
        Returns:
            Path to compose file if found, None otherwise
        """
        try:
            env_config = self.get_environment_config(environment)
            # Compose file paths are relative to project root
            project_root = self.config_path.parent.parent
            return project_root / env_config.compose_file
        except DockerConfigurationError:
            return None


# Singleton instance for global access
_config_loader: Optional[DockerConfigLoader] = None


def get_docker_config_loader() -> DockerConfigLoader:
    """
    Get singleton Docker configuration loader instance.
    
    Returns:
        DockerConfigLoader singleton instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = DockerConfigLoader()
    return _config_loader


def reload_docker_config() -> DockerConfigLoader:
    """
    Force reload of Docker configuration.
    
    Returns:
        New DockerConfigLoader instance
    """
    global _config_loader
    _config_loader = DockerConfigLoader()
    return _config_loader