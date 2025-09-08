"""
Configuration Test Fixtures for UnifiedConfigurationManager

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Test Infrastructure
- Business Goal: Provide reusable fixtures for configuration testing
- Value Impact: Consistent configuration testing across all services
- Strategic Impact: Reduces test duplication and ensures configuration reliability

SSOT for all configuration-related test utilities and fixtures.
Following TEST_CREATION_GUIDE.md patterns for real services, no mocks.
"""

import pytest
import tempfile
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator
from contextlib import contextmanager
import threading
import time

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.managers.unified_configuration_manager import (
    UnifiedConfigurationManager,
    ConfigurationManagerFactory,
    ConfigurationScope,
    ConfigurationSource,
    ConfigurationEntry
)


class ConfigurationTestEnvironment:
    """Manages isolated test environment for configuration testing."""
    
    def __init__(self, environment_name: str = "test"):
        self.environment_name = environment_name
        self.temp_dir: Optional[Path] = None
        self.isolated_env: Optional[IsolatedEnvironment] = None
        self.managers: Dict[str, UnifiedConfigurationManager] = {}
        self.original_env_vars: Dict[str, Optional[str]] = {}
        
    def __enter__(self):
        """Enter configuration test environment."""
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"config_test_{self.environment_name}_"))
        
        # Set up isolated environment
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("ENVIRONMENT", self.environment_name, source="test")
        
        # Clear factory state for clean test
        self._clear_factory_state()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit configuration test environment."""
        # Clean up temporary directory
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        # Restore original environment
        self._restore_environment()
        
        # Clear managers
        self.managers.clear()
        
        # Clear factory state
        self._clear_factory_state()
    
    def _clear_factory_state(self):
        """Clear configuration manager factory state."""
        ConfigurationManagerFactory._global_manager = None
        ConfigurationManagerFactory._user_managers.clear()
        ConfigurationManagerFactory._service_managers.clear()
    
    def _restore_environment(self):
        """Restore original environment variables."""
        for key, original_value in self.original_env_vars.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
    
    def set_environment_variable(self, key: str, value: str):
        """Set environment variable for test."""
        if key not in self.original_env_vars:
            self.original_env_vars[key] = os.environ.get(key)
        
        os.environ[key] = value
        if self.isolated_env:
            self.isolated_env.set(key, value, source="test")
    
    def create_config_file(self, filename: str, config_data: Dict[str, Any]) -> Path:
        """Create configuration file in test environment."""
        if not self.temp_dir:
            raise RuntimeError("Test environment not initialized")
        
        config_path = self.temp_dir / filename
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
        return config_path
    
    def get_manager(self, 
                   user_id: Optional[str] = None,
                   service_name: Optional[str] = None,
                   enable_validation: bool = True,
                   enable_caching: bool = True) -> UnifiedConfigurationManager:
        """Get configuration manager for test."""
        key = f"{user_id or 'global'}:{service_name or 'none'}"
        
        if key not in self.managers:
            self.managers[key] = UnifiedConfigurationManager(
                user_id=user_id,
                environment=self.environment_name,
                service_name=service_name,
                enable_validation=enable_validation,
                enable_caching=enable_caching
            )
        
        return self.managers[key]


class ConfigurationDatasets:
    """Predefined configuration datasets for testing."""
    
    # Basic application configuration
    BASIC_APP_CONFIG = {
        "app": {
            "name": "netra-test",
            "version": "1.0.0",
            "environment": "test",
            "debug": True
        },
        "database": {
            "url": "sqlite:///test.db",
            "pool_size": 5,
            "timeout": 30,
            "echo": False
        },
        "redis": {
            "url": "redis://localhost:6379/0",
            "max_connections": 10,
            "timeout": 5.0
        }
    }
    
    # Enterprise configuration with advanced features
    ENTERPRISE_CONFIG = {
        "app": {
            "name": "netra-enterprise",
            "version": "2.1.0",
            "environment": "production",
            "debug": False,
            "tier": "enterprise"
        },
        "database": {
            "url": "postgresql://user:pass@db-cluster:5432/netra_prod",
            "pool_size": 50,
            "max_overflow": 100,
            "timeout": 60,
            "echo": False,
            "ssl_mode": "require"
        },
        "redis": {
            "url": "redis://redis-cluster:6379/0",
            "max_connections": 100,
            "timeout": 10.0,
            "cluster_mode": True
        },
        "llm": {
            "openai": {
                "api_key": "sk-enterprise-key-12345",
                "model": "gpt-4",
                "timeout": 30.0,
                "max_retries": 3
            },
            "anthropic": {
                "api_key": "claude-enterprise-key-67890",
                "model": "claude-3-opus-20240229",
                "timeout": 30.0,
                "max_retries": 3
            }
        },
        "security": {
            "jwt_secret": "enterprise-jwt-secret-256-bit-key",
            "jwt_algorithm": "HS256",
            "jwt_expire_minutes": 60,
            "oauth": {
                "client_id": "enterprise-oauth-client-id",
                "client_secret": "enterprise-oauth-client-secret",
                "redirect_uri": "https://enterprise.netra.ai/auth/callback"
            }
        },
        "features": {
            "cost_optimization": True,
            "advanced_analytics": True,
            "multi_cloud": True,
            "white_labeling": True,
            "api_access": True
        },
        "limits": {
            "max_users": 1000,
            "max_agents": 50,
            "api_calls_per_hour": 100000,
            "storage_gb": 1000
        }
    }
    
    # Multi-environment configuration
    DEV_ENVIRONMENT_CONFIG = {
        "environment": "development",
        "database": {
            "url": "sqlite:///dev.db",
            "pool_size": 3,
            "echo": True
        },
        "redis": {
            "url": "redis://localhost:6379/1"
        },
        "llm": {
            "timeout": 60.0,
            "mock_responses": True
        },
        "features": {
            "debug_mode": True,
            "mock_external_apis": True
        }
    }
    
    STAGING_ENVIRONMENT_CONFIG = {
        "environment": "staging",
        "database": {
            "url": "postgresql://staging_user:pass@staging-db:5432/netra_staging",
            "pool_size": 15,
            "echo": False
        },
        "redis": {
            "url": "redis://staging-redis:6379/0"
        },
        "llm": {
            "timeout": 45.0,
            "mock_responses": False
        },
        "features": {
            "debug_mode": False,
            "mock_external_apis": False,
            "feature_flags": {
                "new_ui": True,
                "beta_features": True
            }
        }
    }
    
    PROD_ENVIRONMENT_CONFIG = {
        "environment": "production",
        "database": {
            "url": "postgresql://prod_user:secure_pass@prod-db-cluster:5432/netra_prod",
            "pool_size": 50,
            "echo": False,
            "ssl_mode": "require"
        },
        "redis": {
            "url": "redis://prod-redis-cluster:6379/0",
            "cluster_mode": True
        },
        "llm": {
            "timeout": 30.0,
            "mock_responses": False
        },
        "features": {
            "debug_mode": False,
            "mock_external_apis": False
        },
        "monitoring": {
            "enabled": True,
            "metrics_endpoint": "https://metrics.netra.ai",
            "log_level": "INFO"
        }
    }
    
    # Configuration with sensitive data
    SENSITIVE_CONFIG = {
        "database": {
            "url": "postgresql://user:very_secret_password@db:5432/netra",
            "ssl_cert": "-----BEGIN CERTIFICATE-----\\nMIIC..."
        },
        "security": {
            "jwt_secret": "super-secret-jwt-key-never-log-this",
            "encryption_key": "32-byte-encryption-key-for-data",
            "api_keys": {
                "openai": "sk-secret-openai-key-12345",
                "anthropic": "claude-secret-key-67890",
                "aws": "AKIA1234567890ABCDEF",
                "stripe": "sk_live_secret_stripe_key"
            }
        },
        "oauth": {
            "google": {
                "client_secret": "google-oauth-client-secret"
            },
            "github": {
                "client_secret": "github-oauth-client-secret"
            }
        }
    }
    
    # Feature flags configuration
    FEATURE_FLAGS_CONFIG = {
        "features": {
            "new_dashboard": {
                "enabled": True,
                "rollout_percentage": 25,
                "target_users": ["enterprise", "beta"]
            },
            "advanced_agents": {
                "enabled": False,
                "rollout_percentage": 0,
                "beta_users": ["user123", "user456"]
            },
            "real_time_optimization": {
                "enabled": True,
                "rollout_percentage": 100,
                "minimum_tier": "pro"
            },
            "experimental_llm": {
                "enabled": False,
                "rollout_percentage": 5,
                "whitelist": ["internal_team"]
            }
        },
        "experiments": {
            "ui_redesign": {
                "active": True,
                "variants": ["control", "variant_a", "variant_b"],
                "traffic_split": [50, 25, 25]
            }
        }
    }
    
    # Performance and scaling configuration
    PERFORMANCE_CONFIG = {
        "performance": {
            "database": {
                "pool_size": 100,
                "max_overflow": 200,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "query_timeout": 60
            },
            "redis": {
                "max_connections": 1000,
                "connection_pool_size": 50,
                "socket_timeout": 10.0,
                "socket_connect_timeout": 10.0
            },
            "llm": {
                "concurrent_requests": 20,
                "timeout": 30.0,
                "max_retries": 3,
                "backoff_factor": 2
            },
            "agents": {
                "max_concurrent": 50,
                "execution_timeout": 300.0,
                "queue_size": 1000,
                "worker_threads": 20
            }
        },
        "caching": {
            "enabled": True,
            "default_ttl": 300,
            "max_memory_mb": 1024,
            "eviction_policy": "lru"
        },
        "rate_limiting": {
            "api_calls_per_minute": 1000,
            "burst_allowance": 100,
            "per_user_limit": 100
        }
    }
    
    @classmethod
    def get_environment_config(cls, environment: str) -> Dict[str, Any]:
        """Get configuration for specific environment."""
        configs = {
            "development": cls.DEV_ENVIRONMENT_CONFIG,
            "staging": cls.STAGING_ENVIRONMENT_CONFIG,
            "production": cls.PROD_ENVIRONMENT_CONFIG
        }
        return configs.get(environment, cls.BASIC_APP_CONFIG)


class ConfigurationTestScenarios:
    """Predefined test scenarios for configuration testing."""
    
    @staticmethod
    def customer_onboarding_scenario() -> Dict[str, Any]:
        """Configuration for new customer onboarding."""
        return {
            "customer": {
                "id": "cust_12345",
                "name": "Acme Corp",
                "tier": "enterprise",
                "onboarding_date": "2024-01-15"
            },
            "features": {
                "cost_optimization": True,
                "ai_recommendations": True,
                "multi_cloud": True,
                "custom_integrations": True
            },
            "limits": {
                "monthly_api_calls": 100000,
                "max_users": 100,
                "max_agents": 20,
                "storage_gb": 500
            },
            "integrations": {
                "aws": {
                    "enabled": True,
                    "account_id": "123456789012"
                },
                "slack": {
                    "enabled": True,
                    "workspace_id": "T1234567890"
                }
            },
            "notifications": {
                "email": "admin@acmecorp.com",
                "webhook_url": "https://hooks.acmecorp.com/netra"
            }
        }
    
    @staticmethod
    def feature_rollout_scenario() -> Dict[str, Any]:
        """Configuration for gradual feature rollout."""
        return {
            "rollout": {
                "new_agent_engine": {
                    "enabled": True,
                    "percentage": 10,
                    "start_date": "2024-01-01",
                    "target_completion": "2024-02-01",
                    "rollback_threshold": 5.0  # Error rate %
                },
                "updated_dashboard": {
                    "enabled": True,
                    "percentage": 50,
                    "user_groups": ["beta", "enterprise"],
                    "exclude_groups": ["free"]
                }
            },
            "monitoring": {
                "track_errors": True,
                "track_performance": True,
                "alert_on_degradation": True
            }
        }
    
    @staticmethod
    def multi_tenant_scenario() -> List[Dict[str, Any]]:
        """Configuration for multi-tenant scenarios."""
        return [
            {
                "tenant_id": "tenant_startup",
                "tier": "startup",
                "limits": {
                    "api_calls": 10000,
                    "users": 10,
                    "agents": 3
                },
                "features": ["basic_optimization"]
            },
            {
                "tenant_id": "tenant_growth",
                "tier": "growth",
                "limits": {
                    "api_calls": 50000,
                    "users": 50,
                    "agents": 10
                },
                "features": ["basic_optimization", "advanced_analytics"]
            },
            {
                "tenant_id": "tenant_enterprise",
                "tier": "enterprise",
                "limits": {
                    "api_calls": 500000,
                    "users": 500,
                    "agents": 50
                },
                "features": ["basic_optimization", "advanced_analytics", "custom_integrations", "priority_support"]
            }
        ]


class ConfigurationValidationTestCases:
    """Test cases for configuration validation."""
    
    VALID_CONFIGURATIONS = {
        "database_url_postgresql": {
            "database.url": "postgresql://user:pass@localhost:5432/netra"
        },
        "database_url_sqlite": {
            "database.url": "sqlite:///./netra.db"
        },
        "jwt_secret_valid_length": {
            "security.jwt_secret": "this-is-a-valid-32-character-jwt-secret-key-for-signing"
        },
        "api_key_openai_format": {
            "llm.openai.api_key": "sk-1234567890abcdef1234567890abcdef1234567890abcdef"
        },
        "positive_integers": {
            "database.pool_size": 20,
            "redis.max_connections": 100,
            "llm.max_retries": 3
        }
    }
    
    INVALID_CONFIGURATIONS = {
        "database_url_invalid_scheme": {
            "database.url": "invalid://user:pass@localhost:5432/netra",
            "expected_errors": ["Invalid database URL scheme"]
        },
        "jwt_secret_too_short": {
            "security.jwt_secret": "short",
            "expected_errors": ["JWT secret too short"]
        },
        "api_key_wrong_format": {
            "llm.openai.api_key": "invalid-key-format",
            "expected_errors": ["Invalid API key format"]
        },
        "negative_integers": {
            "database.pool_size": -5,
            "redis.max_connections": -1,
            "expected_errors": ["Value must be positive"]
        },
        "missing_required_fields": {
            # Intentionally empty - missing required fields
        }
    }


@contextmanager
def configuration_test_environment(environment_name: str = "test") -> Generator[ConfigurationTestEnvironment, None, None]:
    """Context manager for configuration test environment."""
    test_env = ConfigurationTestEnvironment(environment_name)
    try:
        with test_env:
            yield test_env
    finally:
        pass


@pytest.fixture
def config_test_env():
    """Pytest fixture for configuration test environment."""
    with configuration_test_environment() as test_env:
        yield test_env


@pytest.fixture
def basic_config_manager(config_test_env):
    """Pytest fixture for basic configuration manager."""
    return config_test_env.get_manager()


@pytest.fixture
def enterprise_config_manager(config_test_env):
    """Pytest fixture for enterprise configuration manager."""
    manager = config_test_env.get_manager(service_name="enterprise")
    
    # Load enterprise configuration
    for key, value in _flatten_dict(ConfigurationDatasets.ENTERPRISE_CONFIG).items():
        manager.set(key, value)
    
    return manager


@pytest.fixture
def multi_user_config_managers(config_test_env):
    """Pytest fixture for multiple user configuration managers."""
    users = ["user_123", "user_456", "user_789"]
    managers = {}
    
    for user_id in users:
        manager = config_test_env.get_manager(user_id=user_id)
        # Set user-specific configuration
        manager.set(f"user.id", user_id)
        manager.set(f"user.tier", "enterprise" if "123" in user_id else "growth")
        managers[user_id] = manager
    
    return managers


@pytest.fixture
def performance_test_data():
    """Pytest fixture for performance test data."""
    config_keys = []
    config_values = {}
    
    # Generate realistic configuration dataset
    categories = ["database", "redis", "llm", "security", "features", "limits", "monitoring"]
    
    for category in categories:
        for i in range(50):  # 50 configs per category
            key = f"{category}.config_{i:03d}"
            value = f"{category}_value_{i}"
            config_keys.append(key)
            config_values[key] = value
    
    return {
        "keys": config_keys,
        "values": config_values,
        "total_count": len(config_keys)
    }


def _flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dictionary for configuration testing."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def create_realistic_config_file(file_path: Path, config_type: str = "basic") -> Path:
    """Create realistic configuration file for testing."""
    config_data = {
        "basic": ConfigurationDatasets.BASIC_APP_CONFIG,
        "enterprise": ConfigurationDatasets.ENTERPRISE_CONFIG,
        "sensitive": ConfigurationDatasets.SENSITIVE_CONFIG,
        "performance": ConfigurationDatasets.PERFORMANCE_CONFIG,
        "features": ConfigurationDatasets.FEATURE_FLAGS_CONFIG
    }
    
    data = config_data.get(config_type, ConfigurationDatasets.BASIC_APP_CONFIG)
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    return file_path


def assert_configuration_equals(manager: UnifiedConfigurationManager, 
                              expected_config: Dict[str, Any],
                              exclude_keys: List[str] = None) -> None:
    """Assert that configuration manager contains expected configuration."""
    exclude_keys = exclude_keys or []
    
    for key, expected_value in expected_config.items():
        if key in exclude_keys:
            continue
            
        actual_value = manager.get(key)
        assert actual_value == expected_value, f"Key '{key}': expected {expected_value}, got {actual_value}"


def assert_configuration_validation_passes(manager: UnifiedConfigurationManager) -> None:
    """Assert that configuration validation passes."""
    validation_result = manager.validate_all_configurations()
    
    # Should not have critical errors
    assert len(validation_result.critical_errors) == 0, f"Critical errors: {validation_result.critical_errors}"
    
    # Overall validation should pass or have only warnings
    if not validation_result.is_valid:
        # Only warnings are acceptable
        assert len(validation_result.errors) == 0, f"Validation errors: {validation_result.errors}"


def simulate_concurrent_config_access(manager: UnifiedConfigurationManager, 
                                    operations_per_thread: int = 100,
                                    num_threads: int = 5) -> Dict[str, Any]:
    """Simulate concurrent configuration access for testing thread safety."""
    results = {
        "operations_completed": 0,
        "errors": [],
        "read_times": [],
        "write_times": []
    }
    
    def worker_thread():
        """Worker thread for concurrent operations."""
        import random
        
        for i in range(operations_per_thread):
            try:
                if random.random() < 0.7:  # 70% reads
                    start_time = time.time()
                    value = manager.get(f"test.key.{random.randint(1, 100)}")
                    results["read_times"].append(time.time() - start_time)
                else:  # 30% writes
                    start_time = time.time()
                    manager.set(f"test.key.{random.randint(1, 100)}", f"value_{i}")
                    results["write_times"].append(time.time() - start_time)
                
                results["operations_completed"] += 1
                
            except Exception as e:
                results["errors"].append(str(e))
    
    # Run concurrent threads
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=worker_thread)
        threads.append(thread)
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    return results


def measure_configuration_performance(manager: UnifiedConfigurationManager,
                                    config_count: int = 1000) -> Dict[str, float]:
    """Measure configuration manager performance."""
    import random
    
    # Set up test data
    test_configs = {f"perf.test.{i:04d}": f"value_{i}" for i in range(config_count)}
    
    # Measure write performance
    start_time = time.time()
    for key, value in test_configs.items():
        manager.set(key, value)
    write_time = time.time() - start_time
    
    # Measure read performance
    keys = list(test_configs.keys())
    start_time = time.time()
    for _ in range(config_count):
        key = random.choice(keys)
        value = manager.get(key)
    read_time = time.time() - start_time
    
    return {
        "total_configs": config_count,
        "write_time_total": write_time,
        "write_time_per_config": write_time / config_count,
        "read_time_total": read_time,
        "read_time_per_config": read_time / config_count,
        "writes_per_second": config_count / write_time,
        "reads_per_second": config_count / read_time
    }


class ConfigurationTestManager:
    """
    Comprehensive Configuration Test Manager for System-Wide Testing
    
    Business Value Justification (BVJ):
    - Segment: Platform/Internal - Test Infrastructure
    - Business Goal: Ensure configuration integrity across all test scenarios
    - Value Impact: Prevents configuration-related failures in production
    - Strategic Impact: Enables reliable multi-environment testing
    
    SSOT for configuration testing management across all test types.
    Provides unified interface for test configuration setup, validation, and cleanup.
    """
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.test_environments: Dict[str, ConfigurationTestEnvironment] = {}
        self.managers: Dict[str, UnifiedConfigurationManager] = {}
        self.cleanup_callbacks: List[callable] = []
        
    def create_test_environment(self, name: str) -> ConfigurationTestEnvironment:
        """Create a new test environment for configuration testing."""
        if name in self.test_environments:
            return self.test_environments[name]
            
        test_env = ConfigurationTestEnvironment(f"{self.environment}_{name}")
        self.test_environments[name] = test_env
        return test_env
    
    def get_manager_for_scenario(self, 
                                scenario: str,
                                user_id: Optional[str] = None,
                                service_name: Optional[str] = None) -> UnifiedConfigurationManager:
        """Get configuration manager for specific test scenario."""
        key = f"{scenario}_{user_id or 'global'}_{service_name or 'none'}"
        
        if key not in self.managers:
            self.managers[key] = UnifiedConfigurationManager(
                user_id=user_id,
                environment=self.environment,
                service_name=service_name,
                enable_validation=True,
                enable_caching=True
            )
            
            # Set up scenario-specific configuration
            self._setup_scenario_configuration(scenario, self.managers[key])
        
        return self.managers[key]
    
    def _setup_scenario_configuration(self, scenario: str, manager: UnifiedConfigurationManager):
        """Set up configuration for specific test scenario."""
        scenario_configs = {
            "startup_finalize": {
                "startup.phase": "finalize",
                "startup.timeout": 30,
                "startup.validate_chat": True,
                "startup.validate_websocket": True,
                "startup.validate_agents": True
            },
            "auth_integration": {
                "auth.service_url": "http://localhost:8081",
                "auth.timeout": 15,
                "auth.validate_tokens": True,
                "auth.validate_oauth": True
            },
            "websocket_integration": {
                "websocket.host": "localhost",
                "websocket.port": 8000,
                "websocket.path": "/ws",
                "websocket.auth_required": True,
                "websocket.timeout": 10
            }
        }
        
        config = scenario_configs.get(scenario, {})
        for key, value in config.items():
            manager.set(key, value)
    
    def setup_multi_user_scenario(self, user_ids: List[str]) -> Dict[str, UnifiedConfigurationManager]:
        """Set up configuration managers for multi-user scenarios."""
        managers = {}
        
        for user_id in user_ids:
            manager = self.get_manager_for_scenario("multi_user", user_id=user_id)
            managers[user_id] = manager
            
            # Set user-specific configuration
            manager.set("user.id", user_id)
            manager.set("user.environment", self.environment)
            
        return managers
    
    def validate_scenario_configuration(self, scenario: str) -> bool:
        """Validate configuration for specific test scenario."""
        manager = self.get_manager_for_scenario(scenario)
        validation_result = manager.validate_all_configurations()
        
        # Log validation results
        if not validation_result.is_valid:
            logger.warning(f"Configuration validation failed for scenario {scenario}: {validation_result.errors}")
            
        return validation_result.is_valid
    
    def create_isolated_config_file(self, filename: str, config_data: Dict[str, Any]) -> Path:
        """Create isolated configuration file for testing."""
        temp_dir = Path(tempfile.mkdtemp(prefix=f"config_test_{self.environment}_"))
        config_path = temp_dir / filename
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
        # Register cleanup callback
        self.cleanup_callbacks.append(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        
        return config_path
    
    def cleanup_all(self):
        """Clean up all test resources."""
        # Clean up test environments
        for test_env in self.test_environments.values():
            try:
                test_env.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up test environment: {e}")
        
        # Clean up managers
        self.managers.clear()
        
        # Run cleanup callbacks
        for cleanup_callback in self.cleanup_callbacks:
            try:
                cleanup_callback()
            except Exception as e:
                logger.warning(f"Error in cleanup callback: {e}")
        
        # Clear callbacks
        self.cleanup_callbacks.clear()
        
        # Clear test environments
        self.test_environments.clear()
    
    def __enter__(self):
        """Enter configuration test manager context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit configuration test manager context."""
        self.cleanup_all()


@pytest.fixture
def config_test_manager():
    """Pytest fixture for configuration test manager."""
    with ConfigurationTestManager() as manager:
        yield manager


# Legacy alias for backward compatibility
isolated_config_env = config_test_env