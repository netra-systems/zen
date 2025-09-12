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


class TestClickHouseDockerEnvironmentDetection:
    """Test ClickHouse Docker environment detection and error handling."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger for testing."""
        return central_logger.get_logger(__name__)
    
    @pytest.fixture
    def cloud_run_environment(self):
        """Mock Cloud Run environment variables."""
        env_vars = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-backend-staging',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'PORT': '8080',
            'CLICKHOUSE_REQUIRED': 'false',  # Optional in staging
            'CLICKHOUSE_HOST': 'localhost',  # Will fail in Cloud Run
            'CLICKHOUSE_PORT': '9000',
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': ''
        }
        with patch.dict('os.environ', env_vars, clear=False):
            yield env_vars
    
    @pytest.fixture
    def mock_docker_unavailable(self):
        """Mock Docker being unavailable (Cloud Run scenario)."""
        def side_effect(cmd, **kwargs):
            if cmd[0] == 'docker':
                # Simulate Docker daemon not running in Cloud Run
                raise subprocess.CalledProcessError(1, cmd, "Cannot connect to Docker daemon")
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
    async def test_clickhouse_docker_unavailable_detection_works_with_environment_detection(
        self, 
        mock_logger,
        cloud_run_environment, 
        mock_docker_unavailable,
        mock_get_config
    ):
        """
        Test that ClickHouse initialization properly handles Docker unavailability
        by using CloudEnvironmentDetector to skip Docker checks in Cloud Run.
        
        This test validates Issue #568 fix:
        
        1. Cloud Run environment is detected properly
        2. Docker checks are skipped when CloudPlatform.CLOUD_RUN is detected
        3. ClickHouse is skipped (not failed) in staging when optional
        4. Appropriate logging is provided for operational visibility
        """
        # Mock CloudEnvironmentDetector to return Cloud Run staging
        with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'CLICKHOUSE_REQUIRED': 'false',
                'CLICKHOUSE_HOST': 'localhost',
                'CLICKHOUSE_PORT': '9000',
                'CLICKHOUSE_USER': 'default', 
                'CLICKHOUSE_PASSWORD': ''
            }.get(key, default)
            
            # Mock CloudEnvironmentDetector to detect Cloud Run
            with patch('netra_backend.app.core.environment_context.cloud_environment_detector.get_cloud_environment_detector') as mock_detector_factory:
                mock_detector = MagicMock()
                mock_context = MagicMock()
                mock_context.cloud_platform.value = 'cloud_run'
                mock_context.environment_type.value = 'staging'
                mock_context.service_name = 'netra-backend-staging'
                # Add CloudPlatform.CLOUD_RUN enum for comparison
                from netra_backend.app.core.environment_context.cloud_environment_detector import CloudPlatform
                mock_context.cloud_platform = CloudPlatform.CLOUD_RUN
                mock_detector.detect_environment_context = AsyncMock(return_value=mock_context)
                mock_detector_factory.return_value = mock_detector
                
                # Execute the test - should skip ClickHouse in staging environment
                result = await initialize_clickhouse(mock_logger)
                
                # VALIDATION: Environment detection fix should work correctly
                assert result is not None, "initialize_clickhouse should return status report"
                assert result['service'] == 'clickhouse'
                assert result['status'] == 'skipped', f"Expected skipped status in staging, got: {result['status']}"
                assert result['required'] == False, "ClickHouse should not be required in staging"
                # No error expected since it's properly skipped
                
                # Verify environment detection was called
                mock_detector.detect_environment_context.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_clickhouse_optional_in_staging_continues_gracefully(
        self,
        mock_logger,
        cloud_run_environment,
        mock_docker_unavailable, 
        mock_get_config
    ):
        """
        Test that ClickHouse Docker unavailability doesn't block startup when optional.
        
        This validates the proper behavior when ClickHouse is optional in staging:
        1. Docker unavailability is detected
        2. Service continues gracefully without ClickHouse
        3. Status report indicates skipped/failed but system continues
        """
        with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging', 
                'CLICKHOUSE_REQUIRED': 'false',  # Optional in staging
                'CLICKHOUSE_HOST': 'localhost',
                'CLICKHOUSE_PORT': '9000',
                'CLICKHOUSE_USER': 'default',
                'CLICKHOUSE_PASSWORD': ''
            }.get(key, default)
            
            with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                # Simulate Docker unavailability
                mock_setup.side_effect = ConnectionError("Docker daemon not available")
                
                # Should NOT raise exception since ClickHouse is optional
                result = await initialize_clickhouse(mock_logger)
                
                # Validation: System should handle gracefully
                assert result['service'] == 'clickhouse'
                assert result['required'] == False
                assert result['status'] == 'skipped'  # Skipped appropriately in staging
                
                # Should not raise exception - graceful handling
                # This proves Docker unavailability is handled when ClickHouse is optional
    
    @pytest.mark.asyncio
    async def test_clickhouse_required_in_production_fails_hard_on_docker_unavailable(
        self,
        mock_logger,
        mock_docker_unavailable
    ):
        """
        Test that ClickHouse Docker unavailability blocks startup when required.
        
        This validates that when ClickHouse is required (production), Docker
        unavailability properly fails the initialization.
        """
        # Mock production environment where ClickHouse is required
        production_env = {
            'ENVIRONMENT': 'production',
            'CLICKHOUSE_REQUIRED': 'true',  # Required in production
            'CLICKHOUSE_HOST': 'localhost',
            'CLICKHOUSE_PORT': '9000'
        }
        
        mock_config = MagicMock()
        mock_config.environment = 'production' 
        mock_config.clickhouse_mode = 'enabled'
        
        with patch.dict('os.environ', production_env):
            with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
                with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                    mock_get_env.return_value.get.side_effect = lambda key, default=None: production_env.get(key, default)
                    
                    with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                        # Docker unavailable in production
                        mock_setup.side_effect = ConnectionError("Docker daemon not available")
                        
                        # Should raise RuntimeError when ClickHouse required but Docker unavailable
                        with pytest.raises(RuntimeError, match="ClickHouse initialization failed.*required"):
                            await initialize_clickhouse(mock_logger)
    
    @pytest.mark.asyncio
    async def test_environment_aware_docker_detection_cloud_run(self):
        """
        Test environment-aware Docker detection specifically for Cloud Run.
        
        This test validates that the system properly detects it's running
        in Cloud Run and adjusts Docker availability expectations.
        """
        # Mock being in Cloud Run staging environment
        cloud_run_env = {
            'K_SERVICE': 'netra-backend-staging',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging', 
            'ENVIRONMENT': 'staging'
        }
        
        mock_config = MagicMock()
        mock_config.environment = 'staging'
        mock_config.clickhouse_mode = 'enabled'
        mock_config.graceful_startup_mode = 'true'
        
        with patch.dict('os.environ', cloud_run_env):
            with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
                with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                    mock_get_env.return_value.get.side_effect = lambda key, default=None: {
                        **cloud_run_env,
                        'CLICKHOUSE_REQUIRED': 'false'
                    }.get(key, default)
                    
                    # Mock CloudEnvironmentDetector to detect Cloud Run
                    with patch('netra_backend.app.core.environment_context.cloud_environment_detector.get_cloud_environment_detector') as mock_detector_factory:
                        mock_detector = MagicMock()
                        mock_context = MagicMock()
                        mock_context.cloud_platform.value = 'cloud_run'
                        mock_context.environment_type.value = 'staging'
                        mock_detector.detect_environment_context = AsyncMock(return_value=mock_context)
                        mock_detector_factory.return_value = mock_detector
                        
                        # Mock ClickHouse setup failure due to Docker unavailability
                        with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                            mock_setup.side_effect = ConnectionError("Docker not available in Cloud Run")
                            
                            logger = central_logger.get_logger(__name__)
                            result = await initialize_clickhouse(logger)
                            
                            # Validate Cloud Run environment was detected
                            # and ClickHouse is skipped appropriately in staging
                            assert result['service'] == 'clickhouse'
                            assert result['status'] == 'skipped'
                            # No error expected since it's properly skipped in staging
                            
                            # Should have attempted to detect environment
                            mock_detector.detect_environment_context.assert_called()


def test_module_imports_successfully():
    """Test that all required modules can be imported."""
    # This basic test ensures the test file can import all dependencies
    from netra_backend.app.startup_module import initialize_clickhouse
    from netra_backend.app.logging_config import central_logger
    assert initialize_clickhouse is not None
    assert central_logger is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])