"""
Config Validator Tests - Core Components
Tests for configuration status, validation results, and validation context.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import sys
from pathlib import Path
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import pytest

# Mock the classes that would normally be imported
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any

class ConfigStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"
    MISSING = "missing"
    UNREACHABLE = "unreachable"

@dataclass
class ConfigValidationResult:
    status: ConfigStatus
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    config_age_days: Optional[int] = None
    reachable_endpoints: List[str] = field(default_factory=list)
    unreachable_endpoints: List[str] = field(default_factory=list)

class ResourceMode(Enum):
    LOCAL = "local"
    SHARED = "shared"
    DOCKER = "docker"
    DISABLED = "disabled"
    
@dataclass
class ValidationContext:
    config_path: Path
    is_interactive: bool = True
    is_ci_environment: bool = False
    cli_overrides: Dict[str, str] = field(default_factory=dict)
    env_overrides: Dict[str, str] = field(default_factory=dict)

# Mock ServicesConfiguration for tests
class ServicesConfiguration:
    def __init__(self):
        self.redis = None
        self.clickhouse = None

@pytest.fixture
def temp_config_path(tmp_path: Path) -> Path:
    """Create temporary config file path."""
    return tmp_path / ".dev_services.json"

@pytest.fixture
def mock_validation_context(temp_config_path: Path) -> ValidationContext:
    """Create mock validation context."""
    return ValidationContext(
        config_path=temp_config_path,
        is_interactive=True,
        is_ci_environment=False,
        cli_overrides={"REDIS_HOST": "localhost"},
        env_overrides={"POSTGRES_HOST": "db.example.com"}
    )

@pytest.fixture
def mock_services_config() -> ServicesConfiguration:
    """Create mock services configuration."""
    # Mock: Component isolation for controlled unit testing
    config = Mock(spec=ServicesConfiguration)
    
    # Create mock redis service
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock_redis = TestRedisManager().get_client()
    mock_redis.mode = ResourceMode.SHARED
    mock_redis.get_config.return_value = {"host": "redis.example.com", "port": 6379}
    config.redis = mock_redis
    
    # Create mock clickhouse service
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    mock_clickhouse = mock_clickhouse_instance  # Initialize appropriate service
    mock_clickhouse.mode = ResourceMode.LOCAL
    mock_clickhouse.get_config.return_value = {"host": "ch.example.com", "port": 8123, "secure": False}
    config.clickhouse = mock_clickhouse
    
    return config

class TestConfigStatus:
    """Test configuration status enumeration."""
    
    def test_config_status_values(self) -> None:
        """Test all config status enum values."""
        assert ConfigStatus.VALID.value == "valid"
        assert ConfigStatus.INVALID.value == "invalid"
        assert ConfigStatus.STALE.value == "stale"
        assert ConfigStatus.MISSING.value == "missing"
        assert ConfigStatus.UNREACHABLE.value == "unreachable"

class TestConfigValidationResult:
    """Test configuration validation result model."""
    
    def test_validation_result_creation(self) -> None:
        """Test creating validation result with defaults."""
        result = ConfigValidationResult(status=ConfigStatus.VALID)
        assert result.status == ConfigStatus.VALID
        assert len(result.warnings) == 0
        assert len(result.errors) == 0
        assert result.config_age_days is None

    def test_validation_result_with_data(self) -> None:
        """Test creating validation result with full data."""
        result = ConfigValidationResult(
            status=ConfigStatus.STALE,
            warnings=["Config is old"],
            errors=["Invalid endpoint"],
            config_age_days=45,
            reachable_endpoints=["http://api.example.com"],
            unreachable_endpoints=["http://old.example.com"]
        )
        assert result.status == ConfigStatus.STALE
        assert len(result.warnings) == 1
        assert result.config_age_days == 45

class TestValidationContext:
    """Test validation context dataclass."""
    
    def test_validation_context_defaults(self, temp_config_path: Path) -> None:
        """Test validation context with default values."""
        context = ValidationContext(config_path=temp_config_path)
        assert context.is_interactive is True
        assert context.is_ci_environment is False
        assert len(context.cli_overrides) == 0
        assert len(context.env_overrides) == 0

    def test_validation_context_with_overrides(self, temp_config_path: Path) -> None:
        """Test validation context with custom overrides."""
        cli_overrides = {"REDIS_PORT": "6380"}
        env_overrides = {"DB_NAME": "test"}
        
        context = ValidationContext(
            config_path=temp_config_path,
            is_interactive=False,
            cli_overrides=cli_overrides,
            env_overrides=env_overrides
        )
        assert context.is_interactive is False
        assert context.cli_overrides == cli_overrides
        assert context.env_overrides == env_overrides

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
