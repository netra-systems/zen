"""
Configuration management for the unified test framework.

Manages test configurations across environments and provides validation.
"""

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from dotenv import load_dotenv

from test_framework.unified.base_interfaces import (
    IConfigurationManager,
    ServiceConfig,
    TestEnvironment,
    TestLevel,
)


@dataclass
class EnvironmentConfig:
    """Configuration for a test environment."""
    name: TestEnvironment
    enabled: bool = True
    base_url: Optional[str] = None
    auth_required: bool = False
    auth_type: Optional[str] = None  # oauth2, api_key, jwt
    credentials_path: Optional[str] = None
    timeout_seconds: int = 30
    retry_count: int = 3
    log_level: str = "INFO"
    services: Dict[str, ServiceConfig] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TestLevelConfig:
    """Configuration for a test level."""
    name: TestLevel
    enabled: bool = True
    timeout_seconds: int = 300
    parallel_execution: bool = False
    fail_fast: bool = False
    retry_count: int = 1
    coverage_required: bool = False
    min_coverage_percent: float = 80.0
    excluded_paths: List[str] = None
    
    def __post_init__(self):
        if self.excluded_paths is None:
            self.excluded_paths = []


class ConfigurationManager(IConfigurationManager):
    """Manages test framework configuration."""
    
    def __init__(self, config_dir: Union[str, Path]):
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, Any] = {}
        self._env_configs: Dict[TestEnvironment, EnvironmentConfig] = {}
        self._level_configs: Dict[TestLevel, TestLevelConfig] = {}
        self._service_configs: Dict[str, Dict[TestEnvironment, ServiceConfig]] = {}
        self._loaded = False
        
        # Load environment variables
        env_file = self.config_dir.parent / '.env'
        if env_file.exists():
            load_dotenv(env_file)
    
    def load_all_configs(self) -> None:
        """Load all configuration files."""
        if self._loaded:
            return
        
        # Load main config
        self._load_main_config()
        
        # Load environment configs
        self._load_environment_configs()
        
        # Load test level configs
        self._load_test_level_configs()
        
        # Load service configs
        self._load_service_configs()
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        # Validate all configs
        self._validate_all_configs()
        
        self._loaded = True
    
    def load_config(self, environment: TestEnvironment) -> Dict[str, Any]:
        """Load configuration for an environment."""
        if not self._loaded:
            self.load_all_configs()
        
        env_config = self._env_configs.get(environment)
        if not env_config:
            raise ValueError(f"No configuration found for environment: {environment}")
        
        return asdict(env_config)
    
    def get_service_configs(self, environment: TestEnvironment) -> List[ServiceConfig]:
        """Get service configurations for an environment."""
        if not self._loaded:
            self.load_all_configs()
        
        env_config = self._env_configs.get(environment)
        if not env_config:
            return []
        
        return list(env_config.services.values())
    
    def get_test_config(self, test_level: TestLevel) -> Dict[str, Any]:
        """Get test configuration for a level."""
        if not self._loaded:
            self.load_all_configs()
        
        level_config = self._level_configs.get(test_level)
        if not level_config:
            raise ValueError(f"No configuration found for test level: {test_level}")
        
        return asdict(level_config)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure."""
        required_fields = ['name', 'enabled']
        
        for field in required_fields:
            if field not in config:
                return False
        
        # Validate service configs if present
        if 'services' in config:
            for service_name, service_config in config['services'].items():
                if not self._validate_service_config(service_config):
                    return False
        
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key path."""
        if not self._loaded:
            self.load_all_configs()
        
        # Support dot notation for nested keys
        keys = key.split('.')
        value = self._configs
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value by key path."""
        if not self._loaded:
            self.load_all_configs()
        
        keys = key.split('.')
        config = self._configs
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries."""
        result = {}
        
        for config in configs:
            self._deep_merge(result, config)
        
        return result
    
    def export_config(self, environment: TestEnvironment, output_path: Path) -> None:
        """Export configuration for an environment."""
        if not self._loaded:
            self.load_all_configs()
        
        config = self.load_config(environment)
        
        with open(output_path, 'w') as f:
            if output_path.suffix == '.yaml':
                yaml.dump(config, f, default_flow_style=False)
            else:
                json.dump(config, f, indent=2, default=str)
    
    def get_staging_config(self) -> Dict[str, Any]:
        """Get staging-specific configuration."""
        if not self._loaded:
            self.load_all_configs()
        
        staging_config = self.load_config(TestEnvironment.STAGING)
        
        # Add GCP-specific settings
        staging_config['gcp'] = {
            'project_id': os.getenv('GCP_PROJECT_ID', 'netra-staging'),
            'region': os.getenv('GCP_REGION', 'us-central1'),
            'service_account': os.getenv('GCP_SERVICE_ACCOUNT'),
            'log_filters': {
                'errors': 'severity>=ERROR',
                'websocket': 'jsonPayload.event_type="websocket"',
                'agents': 'jsonPayload.agent_id!=null'
            }
        }
        
        return staging_config
    
    def get_docker_config(self) -> Dict[str, Any]:
        """Get Docker-specific configuration."""
        if not self._loaded:
            self.load_all_configs()
        
        docker_config = self.load_config(TestEnvironment.DOCKER)
        
        # Add Docker Compose settings
        docker_config['compose'] = {
            'file': 'docker-compose.test.yml',
            'project_name': 'netra-test',
            'build_args': {
                'TEST_MODE': 'true',
                'ENABLE_DEBUG': os.getenv('ENABLE_DEBUG', 'false')
            }
        }
        
        return docker_config
    
    def _load_main_config(self) -> None:
        """Load the main configuration file."""
        main_config_file = self.config_dir / 'test_config.yaml'
        
        if main_config_file.exists():
            with open(main_config_file, 'r') as f:
                self._configs = yaml.safe_load(f) or {}
    
    def _load_environment_configs(self) -> None:
        """Load environment-specific configurations."""
        env_dir = self.config_dir / 'environments'
        
        if not env_dir.exists():
            return
        
        for env_file in env_dir.glob('*.yaml'):
            env_name = env_file.stem.upper()
            
            try:
                env_enum = TestEnvironment[env_name]
            except KeyError:
                continue
            
            with open(env_file, 'r') as f:
                config_data = yaml.safe_load(f) or {}
            
            # Parse service configs
            services = {}
            for service_name, service_data in config_data.get('services', {}).items():
                services[service_name] = ServiceConfig(
                    name=service_name,
                    environment=env_enum,
                    url=service_data.get('url'),
                    health_endpoint=service_data.get('health_endpoint', '/health'),
                    port=service_data.get('port'),
                    container_name=service_data.get('container_name'),
                    timeout=service_data.get('timeout', 30),
                    retry_count=service_data.get('retry_count', 3),
                    dependencies=service_data.get('dependencies', [])
                )
            
            env_config = EnvironmentConfig(
                name=env_enum,
                enabled=config_data.get('enabled', True),
                base_url=config_data.get('base_url'),
                auth_required=config_data.get('auth_required', False),
                auth_type=config_data.get('auth_type'),
                credentials_path=config_data.get('credentials_path'),
                timeout_seconds=config_data.get('timeout_seconds', 30),
                retry_count=config_data.get('retry_count', 3),
                log_level=config_data.get('log_level', 'INFO'),
                services=services,
                metadata=config_data.get('metadata', {})
            )
            
            self._env_configs[env_enum] = env_config
    
    def _load_test_level_configs(self) -> None:
        """Load test level configurations."""
        levels_file = self.config_dir / 'test_levels.yaml'
        
        if not levels_file.exists():
            # Use defaults
            for level in TestLevel:
                self._level_configs[level] = TestLevelConfig(name=level)
            return
        
        with open(levels_file, 'r') as f:
            levels_data = yaml.safe_load(f) or {}
        
        for level_name, level_data in levels_data.items():
            try:
                level_enum = TestLevel[level_name.upper()]
            except KeyError:
                continue
            
            level_config = TestLevelConfig(
                name=level_enum,
                enabled=level_data.get('enabled', True),
                timeout_seconds=level_data.get('timeout_seconds', 300),
                parallel_execution=level_data.get('parallel_execution', False),
                fail_fast=level_data.get('fail_fast', False),
                retry_count=level_data.get('retry_count', 1),
                coverage_required=level_data.get('coverage_required', False),
                min_coverage_percent=level_data.get('min_coverage_percent', 80.0),
                excluded_paths=level_data.get('excluded_paths', [])
            )
            
            self._level_configs[level_enum] = level_config
    
    def _load_service_configs(self) -> None:
        """Load service-specific configurations."""
        services_dir = self.config_dir / 'services'
        
        if not services_dir.exists():
            return
        
        for service_file in services_dir.glob('*.yaml'):
            service_name = service_file.stem
            
            with open(service_file, 'r') as f:
                service_data = yaml.safe_load(f) or {}
            
            self._service_configs[service_name] = {}
            
            for env_name, env_data in service_data.get('environments', {}).items():
                try:
                    env_enum = TestEnvironment[env_name.upper()]
                except KeyError:
                    continue
                
                service_config = ServiceConfig(
                    name=service_name,
                    environment=env_enum,
                    url=env_data.get('url'),
                    health_endpoint=env_data.get('health_endpoint', '/health'),
                    port=env_data.get('port'),
                    container_name=env_data.get('container_name'),
                    timeout=env_data.get('timeout', 30),
                    retry_count=env_data.get('retry_count', 3),
                    dependencies=env_data.get('dependencies', [])
                )
                
                self._service_configs[service_name][env_enum] = service_config
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        # Pattern: TEST_CONFIG_<SECTION>_<KEY>
        pattern = re.compile(r'^TEST_CONFIG_(.+)$')
        
        for env_key, env_value in os.environ.items():
            match = pattern.match(env_key)
            if match:
                config_path = match.group(1).lower().replace('_', '.')
                self.set_config_value(config_path, env_value)
    
    def _validate_all_configs(self) -> None:
        """Validate all loaded configurations."""
        # Validate environment configs
        for env, config in self._env_configs.items():
            if not config.name:
                raise ValueError(f"Environment config missing name: {env}")
            
            # Validate service dependencies
            for service_name, service_config in config.services.items():
                for dep in service_config.dependencies:
                    if dep not in config.services:
                        raise ValueError(
                            f"Service {service_name} has unknown dependency: {dep}"
                        )
        
        # Validate test level configs
        for level, config in self._level_configs.items():
            if config.min_coverage_percent < 0 or config.min_coverage_percent > 100:
                raise ValueError(
                    f"Invalid coverage percent for {level}: {config.min_coverage_percent}"
                )
    
    def _validate_service_config(self, config: Dict[str, Any]) -> bool:
        """Validate a service configuration."""
        required_fields = ['name']
        
        for field in required_fields:
            if field not in config:
                return False
        
        # Validate URL format if present
        if 'url' in config:
            url = config['url']
            if not url.startswith(('http://', 'https://')):
                return False
        
        return True
    
    def _deep_merge(self, target: Dict, source: Dict) -> None:
        """Deep merge source dictionary into target."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value