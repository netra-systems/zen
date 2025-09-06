from unittest.mock import Mock, AsyncMock, patch, MagicMock
from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
"""
Config Validator Tests - Decision Engine and Utilities
Tests for decision engine, utility functions, and main validation entry point.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import sys
from pathlib import Path

import asyncio
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

            class ConfigDecisionEngine:
                pass
                def __init__(self):
                    pass
                    pass

                    def _detect_ci_environment():
                        pass
                        return False

                    def _extract_env_overrides():
                        pass
                        return {}

                    def _handle_fallback_action():
                        pass
                        return None

                    def validate_service_config():
                        pass
                        return True

# Mock ServicesConfiguration for tests
                    class ServicesConfiguration:
                        pass
                        def __init__(self):
                            pass
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

    # Mock: Component isolation for testing without external dependencies
                                                                        def test_detect_ci_environment_true(self) -> None:
                                                                            """Test CI environment detection when in CI."""
                                                                            assert _detect_ci_environment() is True

    # Mock: Component isolation for testing without external dependencies
                                                                            def test_detect_ci_environment_false(self) -> None:
                                                                                """Test CI environment detection when not in CI."""
                                                                                assert _detect_ci_environment() is False

    # Mock: Component isolation for testing without external dependencies
                                                                                def test_extract_env_overrides(self) -> None:
                                                                                    """Test environment override extraction."""
                                                                                    overrides = _extract_env_overrides()
                                                                                    assert 'REDIS_HOST' in overrides
                                                                                    assert 'CLICKHOUSE_PORT' in overrides
                                                                                    assert 'OTHER_VAR' not in overrides

                                                                                    @pytest.mark.asyncio
                                                                                    async def test_handle_fallback_action_use_defaults(self, mock_validation_context: ValidationContext) -> None:
                                                                                        """Test fallback action handling for use_defaults."""
                                                                                        result = ConfigValidationResult(status=ConfigStatus.INVALID)

                                                                                        config, returned_result = await _handle_fallback_action("use_defaults", mock_validation_context, result)
                                                                                        assert isinstance(config, ServicesConfiguration)
                                                                                        assert returned_result == result

                                                                                        @pytest.mark.asyncio
                                                                                        async def test_handle_fallback_action_prompt_user(self, mock_validation_context: ValidationContext) -> None:
                                                                                            """Test fallback action handling for prompt_user."""
                                                                                            result = ConfigValidationResult(status=ConfigStatus.STALE)

        # Mock: Component isolation for testing without external dependencies
                                                                                            with patch('dev_launcher.service_config.load_or_create_config') as mock_load:
            # Mock: Component isolation for controlled unit testing
                                                                                                mock_config = Mock(spec=ServicesConfiguration)
                                                                                                mock_config.db_pool_size = 10
                                                                                                mock_config.db_max_overflow = 20
                                                                                                mock_config.db_pool_timeout = 60
                                                                                                mock_config.db_pool_recycle = 3600
                                                                                                mock_config.db_echo = False
                                                                                                mock_config.db_echo_pool = False
                                                                                                mock_config.environment = 'testing'

                                                                                                mock_load.return_value = mock_config

                                                                                                config, returned_result = await _handle_fallback_action("prompt_user", mock_validation_context, result)
                                                                                                assert config == mock_config
                                                                                                mock_load.assert_called_once_with(interactive=True)

                                                                                                class TestMainValidationFunction:
                                                                                                    """Test main validation entry point."""

                                                                                                    @pytest.mark.asyncio
                                                                                                    async def test_validate_service_config_defaults(self) -> None:
                                                                                                        """Test service config validation with defaults."""
        # Mock: Component isolation for testing without external dependencies
                                                                                                        with patch('dev_launcher.config_validator.ServiceConfigValidator') as mock_validator_class:
            # Mock: Component isolation for testing without external dependencies
                                                                                                            with patch('dev_launcher.config_validator.ConfigDecisionEngine') as mock_engine_class:
                # Mock: Generic component isolation for controlled unit testing
                                                                                                                mock_validator = mock_validator_instance  # Initialize appropriate service
                # Make validate_config return an awaitable
                # Mock: Async component isolation for testing without real async operations
                                                                                                                mock_validator.validate_config = AsyncMock(return_value=ConfigValidationResult(status=ConfigStatus.VALID))
                # Mock: Component isolation for controlled unit testing
                                                                                                                mock_validator._load_config.return_value = Mock(spec=ServicesConfiguration)
                                                                                                                mock_validator_class.return_value = mock_validator

                # Mock: Generic component isolation for controlled unit testing
                                                                                                                mock_engine = UserExecutionEngine()
                                                                                                                mock_engine.should_use_existing_config.return_value = True
                                                                                                                mock_engine_class.return_value = mock_engine

                                                                                                                config, result = await validate_service_config()
                                                                                                                assert isinstance(result, ConfigValidationResult)

                                                                                                                @pytest.mark.asyncio
                                                                                                                async def test_validate_service_config_with_overrides(self, temp_config_path: Path) -> None:
                                                                                                                    """Test service config validation with CLI overrides."""
                                                                                                                    cli_overrides = {"REDIS_HOST": "custom"}

        # Mock: Component isolation for testing without external dependencies
                                                                                                                    with patch('dev_launcher.config_validator.ServiceConfigValidator') as mock_validator_class:
            # Mock: Component isolation for testing without external dependencies
                                                                                                                        with patch('dev_launcher.config_validator.ConfigDecisionEngine') as mock_engine_class:
                # Mock: Generic component isolation for controlled unit testing
                                                                                                                            mock_validator = mock_validator_instance  # Initialize appropriate service
                # Make validate_config return an awaitable
                # Mock: Async component isolation for testing without real async operations
                                                                                                                            mock_validator.validate_config = AsyncMock(return_value=ConfigValidationResult(status=ConfigStatus.VALID))
                # Mock: Component isolation for controlled unit testing
                                                                                                                            mock_validator._load_config.return_value = Mock(spec=ServicesConfiguration)
                                                                                                                            mock_validator_class.return_value = mock_validator

                # Mock: Generic component isolation for controlled unit testing
                                                                                                                            mock_engine = UserExecutionEngine()
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

                                                                                                                            if __name__ == "__main__":
                                                                                                                                pytest.main([__file__, "-v"])
