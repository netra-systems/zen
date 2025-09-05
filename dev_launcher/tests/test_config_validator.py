from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Tests for Service Config Validator.

Validates the intelligent configuration detection and validation functionality.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from dev_launcher.config_validator import (
    ConfigDecisionEngine,
    ConfigStatus,
    ConfigValidationResult,
    ServiceConfigValidator,
    ValidationContext,
    _detect_ci_environment,
    _extract_env_overrides,
    validate_service_config,
)


class TestConfigValidationResult:
    """Test ConfigValidationResult model."""
    
    def test_valid_status_creation(self):
        """Test creating result with valid status."""
        result = ConfigValidationResult(status=ConfigStatus.VALID)
        assert result.status == ConfigStatus.VALID
        assert result.warnings == []
        assert result.errors == []
    
    def test_result_with_warnings_and_errors(self):
        """Test result with warnings and errors."""
        result = ConfigValidationResult(
            status=ConfigStatus.STALE,
            warnings=["Config is old"],
            errors=["Service unreachable"]
        )
        assert len(result.warnings) == 1
        assert len(result.errors) == 1


class TestValidationContext:
    """Test ValidationContext dataclass."""
    
    def test_context_creation(self):
        """Test context creation with default values."""
        path = Path("/test/config.json")
        context = ValidationContext(config_path=path)
        assert context.config_path == path
        assert context.is_interactive is True
        assert context.is_ci_environment is False


class TestServiceConfigValidator:
    """Test ServiceConfigValidator class."""
    
    @pytest.fixture
    def temp_config_path(self, tmp_path):
        """Create temporary config file path."""
        return tmp_path / ".dev_services.json"
    
    @pytest.fixture
    def context(self, temp_config_path):
        """Create validation context."""
        return ValidationContext(config_path=temp_config_path)
    
    @pytest.fixture
    def validator(self, context):
        """Create validator instance."""
        return ServiceConfigValidator(context)
    
    @pytest.mark.asyncio
    async def test_missing_config_file(self, validator):
        """Test validation with missing config file."""
        result = await validator.validate_config()
        assert result.status == ConfigStatus.MISSING
    
    def test_file_age_check_recent(self, validator, temp_config_path):
        """Test file age check for recent file."""
        temp_config_path.touch()
        result = validator._check_file_age()
        assert result.status == ConfigStatus.VALID
        assert result.config_age_days == 0
    
    def test_file_age_check_stale(self, validator, temp_config_path):
        """Test file age check for stale file."""
        import os
        temp_config_path.touch()
        old_time = datetime.now() - timedelta(days=35)
        timestamp = old_time.timestamp()
        os.utime(temp_config_path, (timestamp, timestamp))
        
        result = validator._check_file_age()
        assert result.status == ConfigStatus.STALE
        assert result.config_age_days > 30


class TestConfigDecisionEngine:
    """Test ConfigDecisionEngine class."""
    
    @pytest.fixture
    def context(self):
        """Create validation context."""
        return ValidationContext(
            config_path=Path("/test/config.json"),
            is_interactive=True
        )
    
    @pytest.fixture
    def engine(self, context):
        """Create decision engine."""
        return ConfigDecisionEngine(context)
    
    def test_should_use_valid_config(self, engine):
        """Test using valid configuration."""
        result = ConfigValidationResult(status=ConfigStatus.VALID)
        assert engine.should_use_existing_config(result) is True
    
    def test_should_not_use_missing_config(self, engine):
        """Test not using missing configuration."""
        result = ConfigValidationResult(status=ConfigStatus.MISSING)
        assert engine.should_use_existing_config(result) is False
    
    def test_should_prompt_for_stale_config(self, engine):
        """Test prompting for stale configuration."""
        result = ConfigValidationResult(status=ConfigStatus.STALE)
        assert engine.should_prompt_user(result) is True
    
    def test_no_prompt_in_ci_environment(self):
        """Test no prompting in CI environment."""
        context = ValidationContext(
            config_path=Path("/test/config.json"),
            is_ci_environment=True
        )
        engine = ConfigDecisionEngine(context)
        result = ConfigValidationResult(status=ConfigStatus.STALE)
        assert engine.should_prompt_user(result) is False


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_detect_ci_environment_with_ci(self):
        """Test CI environment detection with CI flag."""
        assert _detect_ci_environment() is True
    
    def test_detect_ci_environment_without_ci(self):
        """Test CI environment detection without CI flag."""
        assert _detect_ci_environment() is False
    
    def test_extract_env_overrides(self):
        """Test extraction of environment overrides."""
        overrides = _extract_env_overrides()
        assert 'REDIS_HOST' in overrides
        assert 'POSTGRES_PORT' in overrides
        assert overrides['REDIS_HOST'] == 'localhost'


class TestValidateServiceConfig:
    """Test main validation function."""
    
    @pytest.mark.asyncio
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    async def test_main_validation_flow(self, mock_engine_class, mock_validator_class):
        """Test main validation flow."""
        # Setup mocks
        # Mock: Generic component isolation for controlled unit testing
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator
        
        mock_result = ConfigValidationResult(status=ConfigStatus.VALID)
        # Mock: Async component isolation for testing without real async operations
        mock_validator.validate_config = AsyncMock(return_value=mock_result)
        # Mock: Generic component isolation for controlled unit testing
        mock_validator._load_config.return_value = Mock()
        
        # Mock: Generic component isolation for controlled unit testing
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        mock_engine.should_use_existing_config.return_value = True
        
        # Run validation
        config, result = await validate_service_config(interactive=False)
        
        # Verify
        assert result.status == ConfigStatus.VALID
        mock_validator.validate_config.assert_called_once()
        mock_engine.should_use_existing_config.assert_called_once_with(mock_result)
