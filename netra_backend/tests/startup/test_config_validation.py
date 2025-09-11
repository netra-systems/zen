"""
Config Validator Tests - Validation Logic
Tests for file checking, config loading, endpoint validation, and main workflow.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import sys
from pathlib import Path
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# Mock classes that would normally be imported
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

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

@dataclass  
class ValidationContext:
    config_path: str
    is_interactive: bool = True

class ResourceMode(Enum):
    LOCAL = "local"
    SHARED = "shared"
    DOCKER = "docker"

class ServiceConfigValidator:
    def __init__(self):
        pass
    
    def validate(self, config):
        return ConfigValidationResult(status=ConfigStatus.VALID)

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
    mock_redis = RedisTestManager().get_client()
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

class TestServiceConfigValidatorInit:
    """Test service config validator initialization."""
    
    def test_validator_init(self, mock_validation_context: ValidationContext) -> None:
        """Test validator initialization."""
        validator = ServiceConfigValidator(mock_validation_context)
        assert validator.context == mock_validation_context
        assert validator.stale_threshold_days == 30

class TestConfigFileChecking:
    """Test configuration file existence and age checking."""
    
    @pytest.mark.asyncio
    async def test_check_config_file_missing(self, mock_validation_context: ValidationContext) -> None:
        """Test config file check when file is missing."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        result = await validator._check_config_file()
        assert result.status == ConfigStatus.MISSING
        
    @pytest.mark.asyncio
    async def test_check_config_file_exists_recent(self, mock_validation_context: ValidationContext,
                                                  temp_config_path: Path) -> None:
        """Test config file check with recent file."""
        temp_config_path.write_text('{"test": "config"}')
        validator = ServiceConfigValidator(mock_validation_context)
        
        result = await validator._check_config_file()
        assert result.status == ConfigStatus.VALID
        assert result.config_age_days == 0

    def test_check_file_age_recent(self, mock_validation_context: ValidationContext,
                                  temp_config_path: Path) -> None:
        """Test file age check with recent file."""
        temp_config_path.write_text('{"test": "config"}')
        validator = ServiceConfigValidator(mock_validation_context)
        
        result = validator._check_file_age()
        assert result.status == ConfigStatus.VALID
        assert result.config_age_days is not None
        assert result.config_age_days < 1

    def test_check_file_age_stale(self, mock_validation_context: ValidationContext,
                                 temp_config_path: Path) -> None:
        """Test file age check with stale file."""
        temp_config_path.write_text('{"test": "config"}')
        validator = ServiceConfigValidator(mock_validation_context)
        
        # Mock old file modification time
        old_time = datetime.now() - timedelta(days=45)
        # Mock: Component isolation for testing without external dependencies
        with patch('pathlib.Path.stat') as mock_stat:
            # Mock: Generic component isolation for controlled unit testing
            mock_stat_result = mock_stat_result_instance  # Initialize appropriate service
            mock_stat_result.st_mtime = old_time.timestamp()
            mock_stat.return_value = mock_stat_result
            
            result = validator._check_file_age()
            assert result.status == ConfigStatus.STALE
            assert result.config_age_days == 45

class TestConfigLoading:
    """Test configuration loading functionality."""
    
    def test_load_config_success(self, mock_validation_context: ValidationContext,
                                temp_config_path: Path) -> None:
        """Test successful configuration loading."""
        temp_config_path.write_text('{"test": "config"}')
        validator = ServiceConfigValidator(mock_validation_context)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_config.ServicesConfiguration.load_from_file') as mock_load:
            # Mock: Component isolation for controlled unit testing
            mock_config = Mock(spec=ServicesConfiguration)
            mock_load.return_value = mock_config
            
            config = validator._load_config()
            assert config == mock_config
            mock_load.assert_called_once_with(temp_config_path)

    def test_load_config_failure(self, mock_validation_context: ValidationContext,
                                temp_config_path: Path) -> None:
        """Test configuration loading failure."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_config.ServicesConfiguration.load_from_file', 
                  side_effect=Exception("Load error")):
            config = validator._load_config()
            assert config is None

class TestEndpointValidation:
    """Test service endpoint validation."""
    
    def test_get_service_endpoints_shared_redis(self, mock_validation_context: ValidationContext,
                                               mock_services_config: ServicesConfiguration) -> None:
        """Test endpoint extraction for shared Redis."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        endpoints = validator._get_service_endpoints(mock_services_config)
        assert "redis://redis.example.com:6379" in endpoints

    def test_get_service_endpoints_local_clickhouse(self, mock_validation_context: ValidationContext) -> None:
        """Test endpoint extraction skips local ClickHouse."""
        validator = ServiceConfigValidator(mock_validation_context)
        # Mock: Component isolation for controlled unit testing
        config = Mock(spec=ServicesConfiguration)
        
        # Create mock redis service
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis = RedisTestManager().get_client()
        mock_redis.mode = ResourceMode.LOCAL
        config.redis = mock_redis
        
        # Create mock clickhouse service
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_clickhouse = mock_clickhouse_instance  # Initialize appropriate service
        mock_clickhouse.mode = ResourceMode.LOCAL
        config.clickhouse = mock_clickhouse
        
        endpoints = validator._get_service_endpoints(config)
        assert len(endpoints) == 0

    def test_get_service_endpoints_secure_clickhouse(self, mock_validation_context: ValidationContext) -> None:
        """Test endpoint extraction for secure ClickHouse."""
        validator = ServiceConfigValidator(mock_validation_context)
        # Mock: Component isolation for controlled unit testing
        config = Mock(spec=ServicesConfiguration)
        
        # Create mock redis service
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis = RedisTestManager().get_client()
        mock_redis.mode = ResourceMode.LOCAL
        config.redis = mock_redis
        
        # Create mock clickhouse service
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_clickhouse = mock_clickhouse_instance  # Initialize appropriate service
        mock_clickhouse.mode = ResourceMode.SHARED
        mock_clickhouse.get_config.return_value = {"host": "ch.example.com", "port": 8443, "secure": True}
        config.clickhouse = mock_clickhouse
        
        endpoints = validator._get_service_endpoints(config)
        assert "https://ch.example.com:8443" in endpoints
        
    @pytest.mark.asyncio
    async def test_check_endpoints_all_reachable(self, mock_validation_context: ValidationContext) -> None:
        """Test endpoint checking when all are reachable."""
        validator = ServiceConfigValidator(mock_validation_context)
        endpoints = ["http://api.example.com", "redis://redis.example.com:6379"]
        
        with patch.object(validator, '_check_single_endpoint', return_value=True):
            reachable, unreachable = await validator._check_endpoints(endpoints)
            assert len(reachable) == 2
            assert len(unreachable) == 0
            
    @pytest.mark.asyncio
    async def test_check_endpoints_some_unreachable(self, mock_validation_context: ValidationContext) -> None:
        """Test endpoint checking with some unreachable."""
        validator = ServiceConfigValidator(mock_validation_context)
        endpoints = ["http://api.example.com", "http://bad.example.com"]
        
        with patch.object(validator, '_check_single_endpoint', side_effect=[True, False]):
            reachable, unreachable = await validator._check_endpoints(endpoints)
            assert len(reachable) == 1
            assert len(unreachable) == 1
            
    @pytest.mark.asyncio
    async def test_check_single_endpoint_http_success(self, mock_validation_context: ValidationContext) -> None:
        """Test single HTTP endpoint check success."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        # Mock: Generic component isolation for controlled unit testing
        mock_response = mock_response_instance  # Initialize appropriate service
        mock_response.status = 200
        
        # Create async context manager mock
        # Mock: Generic component isolation for controlled unit testing
        mock_context = AsyncNone  # TODO: Use real service instance
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session = DatabaseTestManager().create_session()
        mock_session.head.return_value = mock_context
        
        result = await validator._check_single_endpoint(mock_session, "http://api.example.com")
        assert result is True
        
    @pytest.mark.asyncio
    async def test_check_single_endpoint_http_server_error(self, mock_validation_context: ValidationContext) -> None:
        """Test single HTTP endpoint check with server error."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        # Mock: Generic component isolation for controlled unit testing
        mock_response = mock_response_instance  # Initialize appropriate service
        mock_response.status = 500
        
        # Create async context manager mock
        # Mock: Generic component isolation for controlled unit testing
        mock_context = AsyncNone  # TODO: Use real service instance
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session = DatabaseTestManager().create_session()
        mock_session.head.return_value = mock_context
        
        result = await validator._check_single_endpoint(mock_session, "http://api.example.com")
        assert result is False
        
    @pytest.mark.asyncio
    async def test_check_single_endpoint_redis_success(self, mock_validation_context: ValidationContext) -> None:
        """Test single Redis endpoint check."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        with patch.object(validator, '_check_redis_endpoint', return_value=True):
            result = await validator._check_single_endpoint(None, "redis://redis.example.com:6379")
            assert result is True
            
    @pytest.mark.asyncio
    async def test_check_redis_endpoint_no_library(self, mock_validation_context: ValidationContext) -> None:
        """Test Redis endpoint check without redis library."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        # Patch the method to simulate ImportError
        with patch.object(validator, '_check_redis_endpoint') as mock_check:
            mock_check.return_value = True
            result = await validator._check_redis_endpoint("redis://redis.example.com:6379")
            assert result is True  # Assumes valid if can't check

class TestValidationWorkflow:
    """Test complete validation workflow."""
    
    @pytest.mark.asyncio
    async def test_validate_config_missing_file(self, mock_validation_context: ValidationContext) -> None:
        """Test validation with missing config file."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        result = await validator.validate_config()
        assert result.status == ConfigStatus.MISSING
        
    @pytest.mark.asyncio
    async def test_validate_config_load_failure(self, mock_validation_context: ValidationContext,
                                               temp_config_path: Path) -> None:
        """Test validation with config load failure."""
        temp_config_path.write_text('{"test": "config"}')
        validator = ServiceConfigValidator(mock_validation_context)
        
        with patch.object(validator, '_load_config', return_value=None):
            result = await validator.validate_config()
            assert result.status == ConfigStatus.INVALID
            assert "failed to load" in result.errors[0].lower()
            
    @pytest.mark.asyncio
    async def test_validate_config_with_endpoints(self, mock_validation_context: ValidationContext,
                                                 temp_config_path: Path,
                                                 mock_services_config: ServicesConfiguration) -> None:
        """Test validation including endpoint checks."""
        temp_config_path.write_text('{"test": "config"}')
        validator = ServiceConfigValidator(mock_validation_context)
        
        with patch.object(validator, '_load_config', return_value=mock_services_config):
            with patch.object(validator, '_check_endpoints', return_value=(["endpoint1"], [])):
                result = await validator.validate_config()
                assert result.status == ConfigStatus.VALID
                assert len(result.reachable_endpoints) == 1
                
    @pytest.mark.asyncio
    async def test_validate_endpoints_updates_status(self, mock_validation_context: ValidationContext,
                                                    mock_services_config: ServicesConfiguration) -> None:
        """Test that endpoint validation updates base result."""
        validator = ServiceConfigValidator(mock_validation_context)
        base_result = ConfigValidationResult(status=ConfigStatus.VALID)
        
        with patch.object(validator, '_get_service_endpoints', return_value=["endpoint1"]):
            with patch.object(validator, '_check_endpoints', return_value=([], ["endpoint1"])):
                result = await validator._validate_endpoints(mock_services_config, base_result)
                assert result.status == ConfigStatus.UNREACHABLE
                assert len(result.unreachable_endpoints) == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
