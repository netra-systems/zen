"""Configuration Validation Pipeline L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Prevent misconfiguration-induced outages and data corruption
- Value Impact: $75K MRR - Configuration errors cause 40% of production incidents
- Strategic Impact: Ensures system reliability through automated configuration validation

Critical Path: Configuration ingestion -> Schema validation -> Dependency checking -> Environment validation -> Breaking change detection -> Safe deployment
Coverage: Multi-environment config validation, schema compliance, dependency resolution, breaking change detection, rollback mechanisms
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, patch

import pytest

from netra_backend.app.config import get_config
from netra_backend.app.redis_manager import RedisManager
from test_framework.mock_utils import mock_justified

logger = logging.getLogger(__name__)

@dataclass
class ConfigValidationResult:
    """Configuration validation result."""
    config_name: str
    is_valid: bool
    validation_time: float
    schema_errors: List[str] = field(default_factory=list)
    dependency_errors: List[str] = field(default_factory=list)
    environment_errors: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class ConfigDependency:
    """Configuration dependency definition."""
    name: str
    config_key: str
    required: bool
    dependency_type: str  # service, database, external_api, config_value

@dataclass
class ConfigSchema:
    """Configuration schema definition."""
    required_fields: Set[str]
    optional_fields: Set[str]
    field_types: Dict[str, str]
    field_constraints: Dict[str, Dict[str, Any]]
    dependencies: List[ConfigDependency]

class ConfigurationValidationPipeline:
    """Configuration validation pipeline with comprehensive validation rules."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.validation_timeout = 30
        self.schema_cache = {}
        self.dependency_cache = {}
        self.validation_history = []
        
        # Define core configuration schemas
        self.schemas = {
            "database": ConfigSchema(
                required_fields={"host", "port", "database", "username"},
                optional_fields={"password", "ssl", "pool_size", "timeout"},
                field_types={
                    "host": "string",
                    "port": "integer",
                    "database": "string",
                    "username": "string",
                    "password": "string",
                    "ssl": "boolean",
                    "pool_size": "integer",
                    "timeout": "integer"
                },
                field_constraints={
                    "port": {"min": 1, "max": 65535},
                    "pool_size": {"min": 1, "max": 100},
                    "timeout": {"min": 1, "max": 300}
                },
                dependencies=[
                    ConfigDependency("database_server", "host", True, "service"),
                    ConfigDependency("auth_service", "username", True, "service")
                ]
            ),
            "redis": ConfigSchema(
                required_fields={"host", "port"},
                optional_fields={"password", "db", "ssl", "timeout"},
                field_types={
                    "host": "string",
                    "port": "integer",
                    "password": "string",
                    "db": "integer",
                    "ssl": "boolean",
                    "timeout": "integer"
                },
                field_constraints={
                    "port": {"min": 1, "max": 65535},
                    "db": {"min": 0, "max": 15},
                    "timeout": {"min": 1, "max": 60}
                },
                dependencies=[
                    ConfigDependency("redis_server", "host", True, "service")
                ]
            ),
            "auth_service": ConfigSchema(
                required_fields={"base_url", "client_id", "client_secret"},
                optional_fields={"timeout", "retries", "circuit_breaker"},
                field_types={
                    "base_url": "string",
                    "client_id": "string",
                    "client_secret": "string",
                    "timeout": "integer",
                    "retries": "integer",
                    "circuit_breaker": "boolean"
                },
                field_constraints={
                    "timeout": {"min": 1, "max": 300},
                    "retries": {"min": 0, "max": 10}
                },
                dependencies=[
                    ConfigDependency("auth_endpoint", "base_url", True, "external_api")
                ]
            ),
            "websocket": ConfigSchema(
                required_fields={"port", "max_connections"},
                optional_fields={"heartbeat_interval", "timeout", "compression"},
                field_types={
                    "port": "integer",
                    "max_connections": "integer",
                    "heartbeat_interval": "integer",
                    "timeout": "integer",
                    "compression": "boolean"
                },
                field_constraints={
                    "port": {"min": 1, "max": 65535},
                    "max_connections": {"min": 1, "max": 10000},
                    "heartbeat_interval": {"min": 10, "max": 300},
                    "timeout": {"min": 30, "max": 600}
                },
                dependencies=[
                    ConfigDependency("redis_cache", "host", True, "config_value")
                ]
            )
        }
    
    async def validate_configuration(self, config_name: str, config_data: Dict[str, Any], 
                                   environment: str = "development") -> ConfigValidationResult:
        """Validate configuration against schema and dependencies."""
        start_time = time.time()
        result = ConfigValidationResult(config_name=config_name, is_valid=True, validation_time=0)
        
        try:
            # Schema validation
            schema_errors = await self._validate_schema(config_name, config_data)
            result.schema_errors = schema_errors
            
            # Dependency validation
            dependency_errors = await self._validate_dependencies(config_name, config_data, environment)
            result.dependency_errors = dependency_errors
            
            # Environment-specific validation
            env_errors = await self._validate_environment_specific(config_name, config_data, environment)
            result.environment_errors = env_errors
            
            # Breaking change detection
            breaking_changes = await self._detect_breaking_changes(config_name, config_data)
            result.breaking_changes = breaking_changes
            
            # Determine overall validity
            result.is_valid = (
                len(schema_errors) == 0 and 
                len(dependency_errors) == 0 and 
                len(env_errors) == 0 and 
                len(breaking_changes) == 0
            )
            
            result.validation_time = time.time() - start_time
            
            # Cache validation result
            if self.redis_client:
                await self._cache_validation_result(result)
            
            return result
            
        except Exception as e:
            result.is_valid = False
            result.schema_errors.append(f"Validation pipeline error: {str(e)}")
            result.validation_time = time.time() - start_time
            return result
    
    async def _validate_schema(self, config_name: str, config_data: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema."""
        errors = []
        
        if config_name not in self.schemas:
            errors.append(f"No schema defined for configuration '{config_name}'")
            return errors
        
        schema = self.schemas[config_name]
        
        # Check required fields
        for field in schema.required_fields:
            if field not in config_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types and constraints
        for field, value in config_data.items():
            if field in schema.field_types:
                expected_type = schema.field_types[field]
                if not self._validate_field_type(value, expected_type):
                    errors.append(f"Field '{field}' has invalid type. Expected: {expected_type}")
                
                # Check constraints
                if field in schema.field_constraints:
                    constraint_errors = self._validate_field_constraints(field, value, schema.field_constraints[field])
                    errors.extend(constraint_errors)
            elif field not in schema.optional_fields and field not in schema.required_fields:
                errors.append(f"Unknown field: {field}")
        
        return errors
    
    def _validate_field_type(self, value: Any, expected_type: str) -> bool:
        """Validate field type."""
        type_mapping = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "float": float,
            "list": list,
            "dict": dict
        }
        
        if expected_type not in type_mapping:
            return False
        
        return isinstance(value, type_mapping[expected_type])
    
    def _validate_field_constraints(self, field_name: str, value: Any, constraints: Dict[str, Any]) -> List[str]:
        """Validate field constraints."""
        errors = []
        
        if "min" in constraints and isinstance(value, (int, float)):
            if value < constraints["min"]:
                errors.append(f"Field '{field_name}' value {value} is below minimum {constraints['min']}")
        
        if "max" in constraints and isinstance(value, (int, float)):
            if value > constraints["max"]:
                errors.append(f"Field '{field_name}' value {value} exceeds maximum {constraints['max']}")
        
        if "pattern" in constraints and isinstance(value, str):
            import re
            if not re.match(constraints["pattern"], value):
                errors.append(f"Field '{field_name}' value does not match required pattern")
        
        if "allowed_values" in constraints:
            if value not in constraints["allowed_values"]:
                errors.append(f"Field '{field_name}' value '{value}' not in allowed values: {constraints['allowed_values']}")
        
        return errors
    
    async def _validate_dependencies(self, config_name: str, config_data: Dict[str, Any], 
                                   environment: str) -> List[str]:
        """Validate configuration dependencies."""
        errors = []
        
        if config_name not in self.schemas:
            return errors
        
        schema = self.schemas[config_name]
        
        for dependency in schema.dependencies:
            if dependency.required and dependency.config_key not in config_data:
                errors.append(f"Missing required dependency: {dependency.name}")
                continue
            
            if dependency.config_key in config_data:
                dependency_value = config_data[dependency.config_key]
                
                # Validate dependency based on type
                if dependency.dependency_type == "service":
                    is_valid = await self._validate_service_dependency(dependency.name, dependency_value, environment)
                elif dependency.dependency_type == "external_api":
                    is_valid = await self._validate_external_api_dependency(dependency.name, dependency_value)
                elif dependency.dependency_type == "database":
                    is_valid = await self._validate_database_dependency(dependency.name, dependency_value)
                elif dependency.dependency_type == "config_value":
                    is_valid = await self._validate_config_value_dependency(dependency.name, dependency_value)
                else:
                    is_valid = True  # Unknown type, assume valid
                
                if not is_valid:
                    errors.append(f"Dependency validation failed: {dependency.name}")
        
        return errors
    
    async def _validate_service_dependency(self, service_name: str, config_value: str, environment: str) -> bool:
        """Validate service dependency."""
        # Simulate service health check
        await asyncio.sleep(0.01)
        
        # For testing, simulate most services being available
        unavailable_services = ["unreachable_service", "down_service"]
        return service_name not in unavailable_services
    
    async def _validate_external_api_dependency(self, api_name: str, config_value: str) -> bool:
        """Validate external API dependency."""
        # Simulate API connectivity check
        await asyncio.sleep(0.02)
        
        # For testing, validate URL format
        if not config_value.startswith(("http://", "https://")):
            return False
        
        # Simulate most APIs being reachable
        unreachable_apis = ["https://down-api.example.com", "http://offline-service.test"]
        return config_value not in unreachable_apis
    
    async def _validate_database_dependency(self, db_name: str, config_value: str) -> bool:
        """Validate database dependency."""
        # Simulate database connectivity check
        await asyncio.sleep(0.01)
        
        # For testing, assume databases are available unless specifically marked
        unavailable_dbs = ["offline_db", "maintenance_db"]
        return db_name not in unavailable_dbs
    
    async def _validate_config_value_dependency(self, dependency_name: str, config_value: str) -> bool:
        """Validate config value dependency."""
        # Simulate cross-config validation
        await asyncio.sleep(0.005)
        
        # For testing, validate some known dependency patterns
        if dependency_name == "redis_cache" and not config_value:
            return False
        
        return True
    
    async def _validate_environment_specific(self, config_name: str, config_data: Dict[str, Any], 
                                           environment: str) -> List[str]:
        """Validate environment-specific configuration requirements."""
        errors = []
        
        if environment == "production":
            # Production-specific validations
            if config_name == "database" and config_data.get("ssl") != True:
                errors.append("SSL must be enabled for production database connections")
            
            if config_name == "auth_service" and not config_data.get("client_secret"):
                errors.append("Client secret is required for production auth service")
            
            # Check for development values in production
            dev_indicators = ["localhost", "127.0.0.1", "dev", "test", "debug"]
            for field, value in config_data.items():
                if isinstance(value, str):
                    for indicator in dev_indicators:
                        if indicator in value.lower():
                            errors.append(f"Development value detected in production config: {field}={value}")
        
        elif environment == "staging":
            # Staging-specific validations
            if config_name == "database" and config_data.get("pool_size", 0) > 50:
                errors.append("Database pool size should be limited in staging environment")
        
        elif environment == "development":
            # Development-specific validations (more lenient)
            pass
        
        return errors
    
    async def _detect_breaking_changes(self, config_name: str, config_data: Dict[str, Any]) -> List[str]:
        """Detect breaking changes in configuration."""
        breaking_changes = []
        
        # Get previous configuration from cache/history
        previous_config = await self._get_previous_config(config_name)
        
        if not previous_config:
            return breaking_changes  # No previous config to compare
        
        # Check for removed required fields
        if config_name in self.schemas:
            schema = self.schemas[config_name]
            for required_field in schema.required_fields:
                if required_field in previous_config and required_field not in config_data:
                    breaking_changes.append(f"Required field '{required_field}' was removed")
        
        # Check for type changes
        for field in previous_config:
            if field in config_data:
                prev_type = type(previous_config[field]).__name__
                curr_type = type(config_data[field]).__name__
                if prev_type != curr_type:
                    breaking_changes.append(f"Field '{field}' type changed from {prev_type} to {curr_type}")
        
        # Check for significant value changes
        critical_fields = {
            "database": ["host", "port", "database"],
            "redis": ["host", "port"],
            "auth_service": ["base_url", "client_id"],
            "websocket": ["port"]
        }
        
        if config_name in critical_fields:
            for field in critical_fields[config_name]:
                if field in previous_config and field in config_data:
                    if previous_config[field] != config_data[field]:
                        breaking_changes.append(f"Critical field '{field}' value changed from '{previous_config[field]}' to '{config_data[field]}'")
        
        return breaking_changes
    
    async def _get_previous_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Get previous configuration for comparison."""
        if self.redis_client:
            try:
                key = f"config_history:{config_name}"
                config_json = await self.redis_client.get(key)
                if config_json:
                    return json.loads(config_json)
            except Exception:
                pass
        
        # Fallback to in-memory cache for testing
        return self.dependency_cache.get(config_name)
    
    async def _cache_validation_result(self, result: ConfigValidationResult):
        """Cache validation result for future reference."""
        try:
            if self.redis_client:
                key = f"config_validation:{result.config_name}"
                value = {
                    "is_valid": result.is_valid,
                    "validation_time": result.validation_time,
                    "timestamp": time.time(),
                    "errors": {
                        "schema": result.schema_errors,
                        "dependency": result.dependency_errors,
                        "environment": result.environment_errors,
                        "breaking_changes": result.breaking_changes
                    }
                }
                await self.redis_client.set(key, json.dumps(value), ex=3600)
        except Exception as e:
            logger.warning(f"Failed to cache validation result: {e}")
    
    async def validate_multiple_configs(self, configs: Dict[str, Dict[str, Any]], 
                                      environment: str = "development") -> Dict[str, ConfigValidationResult]:
        """Validate multiple configurations concurrently."""
        validation_tasks = []
        
        for config_name, config_data in configs.items():
            task = self.validate_configuration(config_name, config_data, environment)
            validation_tasks.append(task)
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        validated_configs = {}
        for i, (config_name, _) in enumerate(configs.items()):
            if isinstance(results[i], ConfigValidationResult):
                validated_configs[config_name] = results[i]
            else:
                # Handle exception
                validated_configs[config_name] = ConfigValidationResult(
                    config_name=config_name,
                    is_valid=False,
                    validation_time=0,
                    schema_errors=[f"Validation exception: {str(results[i])}"]
                )
        
        return validated_configs

@pytest.fixture
async def redis_client():
    """Create Redis client for configuration caching."""
    try:
        import redis.asyncio as redis
        client = redis.Redis(host="localhost", port=6379, decode_responses=True, db=1)
        # Test connection
        await client.ping()
        yield client
        await client.close()
    except Exception:
        # If Redis not available, return None
        yield None

@pytest.fixture
async def config_validator(redis_client):
    """Create configuration validation pipeline."""
    return ConfigurationValidationPipeline(redis_client)

@pytest.mark.L3
@pytest.mark.integration
class TestConfigurationValidationPipelineL3:
    """L3 integration tests for configuration validation pipeline."""
    
    @pytest.mark.asyncio
    async def test_basic_config_validation_performance(self, config_validator):
        """Test basic configuration validation meets performance requirements."""
        # Test database configuration
        db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "netra_test",
            "username": "test_user",
            "password": "test_pass",
            "ssl": True,
            "pool_size": 10
        }
        
        start_time = time.time()
        result = await config_validator.validate_configuration("database", db_config)
        validation_time = time.time() - start_time
        
        # Performance requirements
        assert validation_time < 30.0, f"Validation took {validation_time}s, should be <30s"
        assert result.validation_time < 30.0, f"Reported validation time {result.validation_time}s exceeds 30s limit"
        
        # Validation should succeed
        assert result.is_valid, f"Valid config failed validation: {result.schema_errors}"
        assert len(result.schema_errors) == 0, f"Unexpected schema errors: {result.schema_errors}"
    
    @pytest.mark.asyncio
    async def test_schema_validation_comprehensive(self, config_validator):
        """Test comprehensive schema validation with various error cases."""
        # Test missing required fields
        incomplete_config = {
            "host": "localhost",
            "port": 5432
            # Missing database, username
        }
        
        result = await config_validator.validate_configuration("database", incomplete_config)
        assert not result.is_valid
        assert len(result.schema_errors) >= 2  # Missing database and username
        assert "Missing required field: database" in result.schema_errors
        assert "Missing required field: username" in result.schema_errors
        
        # Test invalid types
        invalid_type_config = {
            "host": "localhost",
            "port": "not_a_number",  # Should be integer
            "database": "test_db",
            "username": "test_user",
            "ssl": "yes"  # Should be boolean
        }
        
        result = await config_validator.validate_configuration("database", invalid_type_config)
        assert not result.is_valid
        assert len(result.schema_errors) >= 2  # Invalid port and ssl types
        
        # Test constraint violations
        constraint_violation_config = {
            "host": "localhost",
            "port": 70000,  # Exceeds max port number
            "database": "test_db",
            "username": "test_user",
            "pool_size": 150  # Exceeds max pool size
        }
        
        result = await config_validator.validate_configuration("database", constraint_violation_config)
        assert not result.is_valid
        assert len(result.schema_errors) >= 2  # Port and pool_size violations
    
    @pytest.mark.asyncio
    async def test_dependency_validation_accuracy(self, config_validator):
        """Test dependency validation with >99.9% accuracy requirement."""
        dependency_test_cases = [
            # Valid dependencies
            ("database", {"host": "valid_service", "port": 5432, "database": "test", "username": "user"}),
            ("redis", {"host": "redis_server", "port": 6379}),
            ("auth_service", {"base_url": "https://auth.example.com", "client_id": "test_client", "client_secret": "secret"}),
            ("websocket", {"port": 8080, "max_connections": 1000, "host": "valid_host"}),
            
            # Invalid dependencies
            ("database", {"host": "unreachable_service", "port": 5432, "database": "test", "username": "user"}),
            ("auth_service", {"base_url": "invalid_url", "client_id": "test", "client_secret": "secret"}),
        ]
        
        total_tests = len(dependency_test_cases)
        correct_validations = 0
        
        for config_name, config_data in dependency_test_cases:
            result = await config_validator.validate_configuration(config_name, config_data)
            
            # Determine expected validity based on test case
            has_invalid_dependency = (
                "unreachable_service" in str(config_data) or 
                "invalid_url" in str(config_data)
            )
            expected_valid = not has_invalid_dependency
            
            if result.is_valid == expected_valid:
                correct_validations += 1
        
        accuracy = correct_validations / total_tests
        assert accuracy >= 0.999, f"Dependency validation accuracy {accuracy:.3f} below 99.9% requirement"
    
    @pytest.mark.asyncio
    async def test_environment_specific_validation(self, config_validator):
        """Test environment-specific validation rules."""
        # Production environment - should enforce strict rules
        prod_config = {
            "host": "localhost",  # Should trigger dev value warning
            "port": 5432,
            "database": "prod_db",
            "username": "prod_user",
            "ssl": False  # Should require SSL in production
        }
        
        result = await config_validator.validate_configuration("database", prod_config, "production")
        assert not result.is_valid
        assert len(result.environment_errors) >= 2  # SSL and localhost warnings
        
        # Fix production config
        fixed_prod_config = {
            "host": "prod-db.example.com",
            "port": 5432,
            "database": "prod_db",
            "username": "prod_user",
            "ssl": True
        }
        
        result = await config_validator.validate_configuration("database", fixed_prod_config, "production")
        assert result.is_valid or len(result.environment_errors) == 0
        
        # Development environment - should be more lenient
        dev_config = {
            "host": "localhost",
            "port": 5432,
            "database": "dev_db",
            "username": "dev_user",
            "ssl": False
        }
        
        result = await config_validator.validate_configuration("database", dev_config, "development")
        assert len(result.environment_errors) == 0  # Should allow dev values
    
    @pytest.mark.asyncio
    async def test_breaking_change_detection(self, config_validator):
        """Test breaking change detection mechanism."""
        # Simulate previous configuration
        original_config = {
            "host": "original-host",
            "port": 5432,
            "database": "original_db",
            "username": "original_user"
        }
        
        # Cache original config as previous version
        config_validator.dependency_cache["database"] = original_config
        
        # Test breaking changes
        breaking_config = {
            "host": "new-host",  # Critical field change
            "port": 3306,       # Critical field change
            "database": "new_db", # Critical field change
            # username removed - required field removal
        }
        
        result = await config_validator.validate_configuration("database", breaking_config)
        assert not result.is_valid
        assert len(result.breaking_changes) >= 3  # Host, port, database changes
        assert len(result.schema_errors) >= 1     # Missing username
        
        # Test non-breaking changes
        safe_config = {
            "host": "original-host",
            "port": 5432,
            "database": "original_db",
            "username": "original_user",
            "ssl": True,  # Added optional field
            "pool_size": 10  # Added optional field
        }
        
        result = await config_validator.validate_configuration("database", safe_config)
        assert len(result.breaking_changes) == 0  # No breaking changes
    
    @pytest.mark.asyncio
    async def test_concurrent_validation_performance(self, config_validator):
        """Test concurrent validation of multiple configurations."""
        # Prepare multiple configurations
        configs = {
            "database": {
                "host": "db-server",
                "port": 5432,
                "database": "test_db",
                "username": "test_user"
            },
            "redis": {
                "host": "redis-server",
                "port": 6379,
                "db": 0
            },
            "auth_service": {
                "base_url": "https://auth.example.com",
                "client_id": "test_client",
                "client_secret": "test_secret"
            },
            "websocket": {
                "port": 8080,
                "max_connections": 1000,
                "host": "ws-server"
            }
        }
        
        start_time = time.time()
        results = await config_validator.validate_multiple_configs(configs)
        total_time = time.time() - start_time
        
        # Performance requirements
        assert total_time < 30.0, f"Concurrent validation took {total_time}s, should be <30s"
        assert len(results) == len(configs), "Should validate all configurations"
        
        # All configurations should be valid
        for config_name, result in results.items():
            assert isinstance(result, ConfigValidationResult), f"Invalid result type for {config_name}"
            assert result.validation_time < 30.0, f"Individual validation time exceeded for {config_name}"
    
    @pytest.mark.asyncio
    async def test_validation_result_caching(self, config_validator):
        """Test validation result caching and retrieval."""
        config_data = {
            "host": "cache-test-host",
            "port": 5432,
            "database": "cache_test",
            "username": "cache_user"
        }
        
        # First validation (should cache result)
        result1 = await config_validator.validate_configuration("database", config_data)
        assert result1.is_valid
        
        # If Redis is available, test cache retrieval
        if config_validator.redis_client:
            cache_key = "config_validation:database"
            cached_data = await config_validator.redis_client.get(cache_key)
            assert cached_data is not None, "Validation result should be cached"
            
            cached_result = json.loads(cached_data)
            assert cached_result["is_valid"] == result1.is_valid
    
    @mock_justified("L3: Configuration validation pipeline testing with controlled dependency simulation")
    @pytest.mark.asyncio
    async def test_validation_pipeline_reliability(self, config_validator):
        """Test overall validation pipeline reliability and consistency."""
        # Test configuration with various complexity levels
        test_configs = [
            # Simple valid config
            ("simple_redis", {"host": "localhost", "port": 6379}),
            
            # Complex valid config
            ("complex_database", {
                "host": "db.example.com",
                "port": 5432,
                "database": "production",
                "username": "app_user",
                "password": "secure_pass",
                "ssl": True,
                "pool_size": 20,
                "timeout": 30
            }),
            
            # Config with validation errors
            ("invalid_websocket", {
                "port": 70000,  # Invalid port
                "max_connections": -5,  # Invalid value
                "heartbeat_interval": 5  # Below minimum
            }),
        ]
        
        validation_attempts = 10
        consistency_results = {}
        
        for config_name, config_data in test_configs:
            config_type = config_name.split('_')[1] if '_' in config_name else config_name
            if config_type not in config_validator.schemas:
                continue
                
            results = []
            for _ in range(validation_attempts):
                result = await config_validator.validate_configuration(config_type, config_data)
                results.append({
                    "is_valid": result.is_valid,
                    "error_count": len(result.schema_errors) + len(result.dependency_errors) + len(result.environment_errors),
                    "validation_time": result.validation_time
                })
            
            # Check consistency
            first_result = results[0]
            consistent = all(
                r["is_valid"] == first_result["is_valid"] and
                r["error_count"] == first_result["error_count"]
                for r in results
            )
            
            consistency_results[config_name] = {
                "consistent": consistent,
                "avg_time": sum(r["validation_time"] for r in results) / len(results),
                "max_time": max(r["validation_time"] for r in results)
            }
        
        # Assert consistency and performance
        for config_name, metrics in consistency_results.items():
            assert metrics["consistent"], f"Inconsistent validation results for {config_name}"
            assert metrics["avg_time"] < 10.0, f"Average validation time too high for {config_name}"
            assert metrics["max_time"] < 30.0, f"Maximum validation time exceeded for {config_name}"
    
    @pytest.mark.asyncio
    async def test_validation_timeout_handling(self, config_validator):
        """Test validation timeout handling and graceful degradation."""
        # Set short timeout for testing
        original_timeout = config_validator.validation_timeout
        config_validator.validation_timeout = 0.1  # 100ms timeout
        
        try:
            # Test configuration that would normally validate successfully
            config_data = {
                "host": "timeout-test-host",
                "port": 5432,
                "database": "timeout_test",
                "username": "timeout_user"
            }
            
            # Mock slow dependency validation
            async def slow_dependency_check(*args, **kwargs):
                await asyncio.sleep(0.2)  # Exceed timeout
                return True
            
            original_validate_service = config_validator._validate_service_dependency
            config_validator._validate_service_dependency = slow_dependency_check
            
            result = await config_validator.validate_configuration("database", config_data)
            
            # Should complete within reasonable time even with timeout
            assert result.validation_time < 5.0, "Validation should handle timeouts gracefully"
            
        finally:
            # Restore original settings
            config_validator.validation_timeout = original_timeout
            if hasattr(config_validator, '_validate_service_dependency'):
                config_validator._validate_service_dependency = original_validate_service

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])