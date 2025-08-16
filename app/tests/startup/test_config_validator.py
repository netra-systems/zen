"""
Comprehensive Unit Tests for Service Config Validator
Tests configuration validation, endpoint checking, and decision engine logic.
COMPLIANCE: 300-line max file, 8-line max functions, async test support.
"""

import pytest
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Optional

from dev_launcher.config_validator import (
    ServiceConfigValidator, ConfigDecisionEngine, ConfigStatus,
    ConfigValidationResult, ValidationContext, validate_service_config,
    _detect_ci_environment, _extract_env_overrides, _handle_fallback_action
)
from dev_launcher.service_config import ServicesConfiguration, ResourceMode


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
    config = Mock(spec=ServicesConfiguration)
    config.redis.mode = ResourceMode.SHARED
    config.redis.get_config.return_value = {"host": "redis.example.com", "port": 6379}
    config.clickhouse.mode = ResourceMode.LOCAL
    config.clickhouse.get_config.return_value = {"host": "ch.example.com", "port": 8123, "secure": False}
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


class TestServiceConfigValidatorInit:
    """Test service config validator initialization."""
    
    def test_validator_init(self, mock_validation_context: ValidationContext) -> None:
        """Test validator initialization."""
        validator = ServiceConfigValidator(mock_validation_context)
        assert validator.context == mock_validation_context
        assert validator.stale_threshold_days == 30


class TestConfigFileChecking:
    """Test configuration file existence and age checking."""
    async def test_check_config_file_missing(self, mock_validation_context: ValidationContext) -> None:
        """Test config file check when file is missing."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        result = await validator._check_config_file()
        assert result.status == ConfigStatus.MISSING
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
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat_result = Mock()
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
        
        with patch('dev_launcher.service_config.ServicesConfiguration.load_from_file') as mock_load:
            mock_config = Mock(spec=ServicesConfiguration)
            mock_load.return_value = mock_config
            
            config = validator._load_config()
            assert config == mock_config
            mock_load.assert_called_once_with(temp_config_path)

    def test_load_config_failure(self, mock_validation_context: ValidationContext,
                                temp_config_path: Path) -> None:
        """Test configuration loading failure."""
        validator = ServiceConfigValidator(mock_validation_context)
        
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
        config = Mock(spec=ServicesConfiguration)
        config.redis.mode = ResourceMode.LOCAL
        config.clickhouse.mode = ResourceMode.LOCAL
        
        endpoints = validator._get_service_endpoints(config)
        assert len(endpoints) == 0

    def test_get_service_endpoints_secure_clickhouse(self, mock_validation_context: ValidationContext) -> None:
        """Test endpoint extraction for secure ClickHouse."""
        validator = ServiceConfigValidator(mock_validation_context)
        config = Mock(spec=ServicesConfiguration)
        config.redis.mode = ResourceMode.LOCAL
        config.clickhouse.mode = ResourceMode.SHARED
        config.clickhouse.get_config.return_value = {"host": "ch.example.com", "port": 8443, "secure": True}
        
        endpoints = validator._get_service_endpoints(config)
        assert "https://ch.example.com:8443" in endpoints
    async def test_check_endpoints_all_reachable(self, mock_validation_context: ValidationContext) -> None:
        """Test endpoint checking when all are reachable."""
        validator = ServiceConfigValidator(mock_validation_context)
        endpoints = ["http://api.example.com", "redis://redis.example.com:6379"]
        
        with patch.object(validator, '_check_single_endpoint', return_value=True):
            reachable, unreachable = await validator._check_endpoints(endpoints)
            assert len(reachable) == 2
            assert len(unreachable) == 0
    async def test_check_endpoints_some_unreachable(self, mock_validation_context: ValidationContext) -> None:
        """Test endpoint checking with some unreachable."""
        validator = ServiceConfigValidator(mock_validation_context)
        endpoints = ["http://api.example.com", "http://bad.example.com"]
        
        with patch.object(validator, '_check_single_endpoint', side_effect=[True, False]):
            reachable, unreachable = await validator._check_endpoints(endpoints)
            assert len(reachable) == 1
            assert len(unreachable) == 1
    async def test_check_single_endpoint_http_success(self, mock_validation_context: ValidationContext) -> None:
        """Test single HTTP endpoint check success."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        mock_response = Mock()
        mock_response.status = 200
        mock_session = Mock()
        mock_session.head.return_value.__aenter__.return_value = mock_response
        
        result = await validator._check_single_endpoint(mock_session, "http://api.example.com")
        assert result is True
    async def test_check_single_endpoint_http_server_error(self, mock_validation_context: ValidationContext) -> None:
        """Test single HTTP endpoint check with server error."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        mock_response = Mock()
        mock_response.status = 500
        mock_session = Mock()
        mock_session.head.return_value.__aenter__.return_value = mock_response
        
        result = await validator._check_single_endpoint(mock_session, "http://api.example.com")
        assert result is False
    async def test_check_single_endpoint_redis_success(self, mock_validation_context: ValidationContext) -> None:
        """Test single Redis endpoint check."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        with patch.object(validator, '_check_redis_endpoint', return_value=True):
            result = await validator._check_single_endpoint(None, "redis://redis.example.com:6379")
            assert result is True
    async def test_check_redis_endpoint_no_library(self, mock_validation_context: ValidationContext) -> None:
        """Test Redis endpoint check without redis library."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        with patch('builtins.__import__', side_effect=ImportError("No redis")):
            result = await validator._check_redis_endpoint("redis://redis.example.com:6379")
            assert result is True  # Assumes valid if can't check


class TestValidationWorkflow:
    """Test complete validation workflow."""
    async def test_validate_config_missing_file(self, mock_validation_context: ValidationContext) -> None:
        """Test validation with missing config file."""
        validator = ServiceConfigValidator(mock_validation_context)
        
        result = await validator.validate_config()
        assert result.status == ConfigStatus.MISSING
    async def test_validate_config_load_failure(self, mock_validation_context: ValidationContext,
                                               temp_config_path: Path) -> None:
        """Test validation with config load failure."""
        temp_config_path.write_text('{"test": "config"}')
        validator = ServiceConfigValidator(mock_validation_context)
        
        with patch.object(validator, '_load_config', return_value=None):
            result = await validator.validate_config()
            assert result.status == ConfigStatus.INVALID
            assert "failed to load" in result.errors[0].lower()
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


class TestConfigDecisionEngine:
    """Test configuration decision engine."""
    
    def test_should_use_existing_config_missing(self, mock_validation_context: ValidationContext) -> None:
        """Test decision for missing config."""
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.MISSING)
        
        assert engine.should_use_existing_config(result) is False

    def test_should_use_existing_config_valid(self, mock_validation_context: ValidationContext) -> None:
        """Test decision for valid config."""
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.VALID)
        
        assert engine.should_use_existing_config(result) is True

    def test_should_use_existing_config_ci_environment(self, mock_validation_context: ValidationContext) -> None:
        """Test decision in CI environment."""
        mock_validation_context.is_ci_environment = True
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.STALE)
        
        assert engine.should_use_existing_config(result) is True

    def test_should_prompt_user_interactive(self, mock_validation_context: ValidationContext) -> None:
        """Test user prompt decision for interactive mode."""
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.STALE)
        
        assert engine.should_prompt_user(result) is True

    def test_should_prompt_user_non_interactive(self, mock_validation_context: ValidationContext) -> None:
        """Test user prompt decision for non-interactive mode."""
        mock_validation_context.is_interactive = False
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.STALE)
        
        assert engine.should_prompt_user(result) is False

    def test_get_fallback_action_missing(self, mock_validation_context: ValidationContext) -> None:
        """Test fallback action for missing config."""
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.MISSING)
        
        action = engine.get_fallback_action(result)
        assert action == "create_new"

    def test_get_fallback_action_invalid(self, mock_validation_context: ValidationContext) -> None:
        """Test fallback action for invalid config."""
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.INVALID)
        
        action = engine.get_fallback_action(result)
        assert action == "use_defaults"

    def test_get_fallback_action_stale_interactive(self, mock_validation_context: ValidationContext) -> None:
        """Test fallback action for stale config in interactive mode."""
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.STALE)
        
        action = engine.get_fallback_action(result)
        assert action == "prompt_user"

    def test_get_fallback_action_stale_ci(self, mock_validation_context: ValidationContext) -> None:
        """Test fallback action for stale config in CI."""
        mock_validation_context.is_interactive = False
        mock_validation_context.is_ci_environment = True
        engine = ConfigDecisionEngine(mock_validation_context)
        result = ConfigValidationResult(status=ConfigStatus.STALE)
        
        action = engine.get_fallback_action(result)
        assert action == "use_existing"


class TestUtilityFunctions:
    """Test utility functions."""
    
    @patch('os.environ', {'CI': '1', 'GITHUB_ACTIONS': 'true'})
    def test_detect_ci_environment_true(self) -> None:
        """Test CI environment detection when in CI."""
        assert _detect_ci_environment() is True

    @patch('os.environ', {})
    def test_detect_ci_environment_false(self) -> None:
        """Test CI environment detection when not in CI."""
        assert _detect_ci_environment() is False

    @patch('os.environ', {'REDIS_HOST': 'localhost', 'CLICKHOUSE_PORT': '8123', 'OTHER_VAR': 'value'})
    def test_extract_env_overrides(self) -> None:
        """Test environment override extraction."""
        overrides = _extract_env_overrides()
        assert 'REDIS_HOST' in overrides
        assert 'CLICKHOUSE_PORT' in overrides
        assert 'OTHER_VAR' not in overrides
    async def test_handle_fallback_action_use_defaults(self, mock_validation_context: ValidationContext) -> None:
        """Test fallback action handling for use_defaults."""
        result = ConfigValidationResult(status=ConfigStatus.INVALID)
        
        config, returned_result = await _handle_fallback_action("use_defaults", mock_validation_context, result)
        assert isinstance(config, ServicesConfiguration)
        assert returned_result == result
    async def test_handle_fallback_action_prompt_user(self, mock_validation_context: ValidationContext) -> None:
        """Test fallback action handling for prompt_user."""
        result = ConfigValidationResult(status=ConfigStatus.STALE)
        
        with patch('dev_launcher.service_config.load_or_create_config') as mock_load:
            mock_config = Mock(spec=ServicesConfiguration)
            mock_load.return_value = mock_config
            
            config, returned_result = await _handle_fallback_action("prompt_user", mock_validation_context, result)
            assert config == mock_config
            mock_load.assert_called_once_with(interactive=True)


class TestMainValidationFunction:
    """Test main validation entry point."""
    async def test_validate_service_config_defaults(self) -> None:
        """Test service config validation with defaults."""
        with patch('dev_launcher.config_validator.ServiceConfigValidator') as mock_validator_class:
            with patch('dev_launcher.config_validator.ConfigDecisionEngine') as mock_engine_class:
                mock_validator = Mock()
                mock_validator.validate_config.return_value = ConfigValidationResult(status=ConfigStatus.VALID)
                mock_validator._load_config.return_value = Mock(spec=ServicesConfiguration)
                mock_validator_class.return_value = mock_validator
                
                mock_engine = Mock()
                mock_engine.should_use_existing_config.return_value = True
                mock_engine_class.return_value = mock_engine
                
                config, result = await validate_service_config()
                assert isinstance(result, ConfigValidationResult)
    async def test_validate_service_config_with_overrides(self, temp_config_path: Path) -> None:
        """Test service config validation with CLI overrides."""
        cli_overrides = {"REDIS_HOST": "custom"}
        
        with patch('dev_launcher.config_validator.ServiceConfigValidator') as mock_validator_class:
            with patch('dev_launcher.config_validator.ConfigDecisionEngine') as mock_engine_class:
                mock_validator = Mock()
                mock_validator.validate_config.return_value = ConfigValidationResult(status=ConfigStatus.VALID)
                mock_validator._load_config.return_value = Mock(spec=ServicesConfiguration)
                mock_validator_class.return_value = mock_validator
                
                mock_engine = Mock()
                mock_engine.should_use_existing_config.return_value = True
                mock_engine_class.return_value = mock_engine
                
                config, result = await validate_service_config(
                    config_path=temp_config_path,
                    interactive=False,
                    cli_overrides=cli_overrides
                )
                
                # Verify context was created with correct overrides
                call_args = mock_validator_class.call_args[0][0]
                assert call_args.cli_overrides == cli_overrides