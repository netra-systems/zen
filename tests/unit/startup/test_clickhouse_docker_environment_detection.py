"""
Unit test for ClickHouse Docker environment detection (Issue #568).

This test validates that the initialize_clickhouse function properly detects 
Docker unavailability in Cloud Run environments and handles it appropriately.

DESIGNED TO FAIL FIRST: This test should FAIL when run in environments where 
Docker is not available (like GCP Cloud Run staging), proving the issue exists.

Test Status: IMPLEMENT AND EXECUTE
"""
import pytest
import asyncio
import unittest.mock as mock
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock
from netra_backend.app.startup_module import initialize_clickhouse
from netra_backend.app.logging_config import central_logger

@pytest.mark.unit
class TestClickHouseDockerEnvironmentDetection:
    """Test ClickHouse Docker environment detection and error handling."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger for testing."""
        return central_logger.get_logger(__name__)

    @pytest.fixture
    def cloud_run_environment(self):
        """Mock Cloud Run environment variables."""
        env_vars = {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend-staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'PORT': '8080', 'CLICKHOUSE_REQUIRED': 'false', 'CLICKHOUSE_HOST': 'localhost', 'CLICKHOUSE_PORT': '9000', 'CLICKHOUSE_USER': 'default', 'CLICKHOUSE_PASSWORD': ''}
        with patch.dict('os.environ', env_vars, clear=False):
            yield env_vars

    @pytest.fixture
    def mock_docker_unavailable(self):
        """Mock Docker being unavailable (Cloud Run scenario)."""

        def side_effect(cmd, **kwargs):
            if cmd[0] == 'docker':
                raise subprocess.CalledProcessError(1, cmd, 'Cannot connect to Docker daemon')
            return MagicMock(returncode=0, stdout='', stderr='')
        with patch('subprocess.run', side_effect=side_effect):
            yield

    @pytest.fixture
    def mock_get_config(self):
        """Mock get_config to return staging configuration."""
        mock_config = MagicMock()
        mock_config.environment = 'staging'
        mock_config.clickhouse_mode = 'enabled'
        mock_config.graceful_startup_mode = 'true'
        with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
            yield mock_config

    @pytest.mark.asyncio
    async def test_clickhouse_docker_unavailable_detection_works_with_environment_detection(self, mock_logger, cloud_run_environment, mock_docker_unavailable, mock_get_config):
        """
        Test that ClickHouse initialization properly handles Docker unavailability
        by using CloudEnvironmentDetector to skip Docker checks in Cloud Run.
        
        This test validates Issue #568 fix:
        
        1. Cloud Run environment is detected properly
        2. Docker checks are skipped when CloudPlatform.CLOUD_RUN is detected
        3. ClickHouse is skipped (not failed) in staging when optional
        4. Appropriate logging is provided for operational visibility
        """
        with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'staging', 'CLICKHOUSE_REQUIRED': 'false', 'CLICKHOUSE_HOST': 'localhost', 'CLICKHOUSE_PORT': '9000', 'CLICKHOUSE_USER': 'default', 'CLICKHOUSE_PASSWORD': ''}.get(key, default)
            with patch('netra_backend.app.core.environment_context.cloud_environment_detector.get_cloud_environment_detector') as mock_detector_factory:
                mock_detector = MagicMock()
                mock_context = MagicMock()
                mock_context.cloud_platform.value = 'cloud_run'
                mock_context.environment_type.value = 'staging'
                mock_context.service_name = 'netra-backend-staging'
                from netra_backend.app.core.environment_context.cloud_environment_detector import CloudPlatform
                mock_context.cloud_platform = CloudPlatform.CLOUD_RUN
                mock_detector.detect_environment_context = AsyncMock(return_value=mock_context)
                mock_detector_factory.return_value = mock_detector
                result = await initialize_clickhouse(mock_logger)
                assert result is not None, 'initialize_clickhouse should return status report'
                assert result['service'] == 'clickhouse'
                assert result['status'] == 'skipped', f"Expected skipped status in staging, got: {result['status']}"
                assert result['required'] == False, 'ClickHouse should not be required in staging'
                mock_detector.detect_environment_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_clickhouse_optional_in_staging_continues_gracefully(self, mock_logger, cloud_run_environment, mock_docker_unavailable, mock_get_config):
        """
        Test that ClickHouse Docker unavailability doesn't block startup when optional.
        
        This validates the proper behavior when ClickHouse is optional in staging:
        1. Docker unavailability is detected
        2. Service continues gracefully without ClickHouse
        3. Status report indicates skipped/failed but system continues
        """
        with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'staging', 'CLICKHOUSE_REQUIRED': 'false', 'CLICKHOUSE_HOST': 'localhost', 'CLICKHOUSE_PORT': '9000', 'CLICKHOUSE_USER': 'default', 'CLICKHOUSE_PASSWORD': ''}.get(key, default)
            with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                mock_setup.side_effect = ConnectionError('Docker daemon not available')
                result = await initialize_clickhouse(mock_logger)
                assert result['service'] == 'clickhouse'
                assert result['required'] == False
                assert result['status'] == 'skipped'

    @pytest.mark.asyncio
    async def test_clickhouse_required_in_production_fails_hard_on_docker_unavailable(self, mock_logger, mock_docker_unavailable):
        """
        Test that ClickHouse Docker unavailability blocks startup when required.
        
        This validates that when ClickHouse is required (production), Docker
        unavailability properly fails the initialization.
        """
        production_env = {'ENVIRONMENT': 'production', 'CLICKHOUSE_REQUIRED': 'true', 'CLICKHOUSE_HOST': 'localhost', 'CLICKHOUSE_PORT': '9000'}
        mock_config = MagicMock()
        mock_config.environment = 'production'
        mock_config.clickhouse_mode = 'enabled'
        with patch.dict('os.environ', production_env):
            with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
                with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                    mock_get_env.return_value.get.side_effect = lambda key, default=None: production_env.get(key, default)
                    with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                        mock_setup.side_effect = ConnectionError('Docker daemon not available')
                        with pytest.raises(RuntimeError, match='ClickHouse initialization failed.*required'):
                            await initialize_clickhouse(mock_logger)

    @pytest.mark.asyncio
    async def test_environment_aware_docker_detection_cloud_run(self):
        """
        Test environment-aware Docker detection specifically for Cloud Run.
        
        This test validates that the system properly detects it's running
        in Cloud Run and adjusts Docker availability expectations.
        """
        cloud_run_env = {'K_SERVICE': 'netra-backend-staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'ENVIRONMENT': 'staging'}
        mock_config = MagicMock()
        mock_config.environment = 'staging'
        mock_config.clickhouse_mode = 'enabled'
        mock_config.graceful_startup_mode = 'true'
        with patch.dict('os.environ', cloud_run_env):
            with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
                with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                    mock_get_env.return_value.get.side_effect = lambda key, default=None: {**cloud_run_env, 'CLICKHOUSE_REQUIRED': 'false'}.get(key, default)
                    with patch('netra_backend.app.core.environment_context.cloud_environment_detector.get_cloud_environment_detector') as mock_detector_factory:
                        mock_detector = MagicMock()
                        mock_context = MagicMock()
                        mock_context.cloud_platform.value = 'cloud_run'
                        mock_context.environment_type.value = 'staging'
                        mock_detector.detect_environment_context = AsyncMock(return_value=mock_context)
                        mock_detector_factory.return_value = mock_detector
                        with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                            mock_setup.side_effect = ConnectionError('Docker not available in Cloud Run')
                            logger = central_logger.get_logger(__name__)
                            result = await initialize_clickhouse(logger)
                            assert result['service'] == 'clickhouse'
                            assert result['status'] == 'skipped'
                            mock_detector.detect_environment_context.assert_called()

@pytest.mark.unit
def test_module_imports_successfully():
    """Test that all required modules can be imported."""
    from netra_backend.app.startup_module import initialize_clickhouse
    from netra_backend.app.logging_config import central_logger
    assert initialize_clickhouse is not None
    assert central_logger is not None
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')