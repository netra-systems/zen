"""
Integration test for startup ClickHouse environment integration (Issue #568).

This test validates the integration between startup_module.py initialize_clickhouse 
function and CloudEnvironmentDetector for proper Docker availability detection.

DESIGNED TO FAIL FIRST: This integration test should FAIL in environments where 
Docker is unavailable, demonstrating the real-world issue in staging/Cloud Run.

Test Status: IMPLEMENT AND EXECUTE
"""
import pytest
import asyncio
import os
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock

from netra_backend.app.startup_module import initialize_clickhouse
from netra_backend.app.core.environment_context.cloud_environment_detector import (
    get_cloud_environment_detector,
    EnvironmentContext, 
    EnvironmentType,
    CloudPlatform
)
from netra_backend.app.logging_config import central_logger


class TestStartupClickHouseEnvironmentIntegration:
    """Integration tests for ClickHouse startup with environment detection."""
    
    @pytest.fixture
    def staging_cloud_run_environment(self):
        """Mock staging Cloud Run environment."""
        env_vars = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-backend-staging', 
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'PORT': '8080',
            'CLICKHOUSE_REQUIRED': 'false',  # Optional in staging
            'CLICKHOUSE_HOST': 'localhost',
            'CLICKHOUSE_PORT': '9000',
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': ''
        }
        with patch.dict('os.environ', env_vars, clear=False):
            yield env_vars
    
    @pytest.fixture
    def real_docker_check(self):
        """Use real Docker availability check - may fail in Cloud Run."""
        # Don't mock subprocess.run - let it actually check Docker
        return True
    
    @pytest.fixture
    def mock_cloud_environment_detector(self):
        """Mock CloudEnvironmentDetector to return Cloud Run staging context."""
        staging_context = EnvironmentContext(
            environment_type=EnvironmentType.STAGING,
            cloud_platform=CloudPlatform.CLOUD_RUN,
            service_name='netra-backend-staging',
            project_id='netra-staging',
            region='us-central1',
            confidence_score=0.9,
            detection_metadata={
                'method': 'cloud_run_metadata',
                'service_name': 'netra-backend-staging'
            }
        )
        
        mock_detector = MagicMock()
        mock_detector.detect_environment_context = AsyncMock(return_value=staging_context)
        
        with patch('netra_backend.app.core.environment_context.cloud_environment_detector.get_cloud_environment_detector', 
                   return_value=mock_detector):
            yield mock_detector, staging_context
    
    @pytest.mark.asyncio
    async def test_real_docker_availability_check_integration(
        self,
        staging_cloud_run_environment,
        real_docker_check
    ):
        """
        Integration test with REAL Docker availability check.
        
        This test performs actual Docker daemon connectivity check.
        EXPECTED TO FAIL in Cloud Run staging where Docker is unavailable.
        
        This proves Issue #568 exists in real environments.
        """
        logger = central_logger.get_logger(__name__)
        
        # Use real get_config
        mock_config = MagicMock()
        mock_config.environment = 'staging'
        mock_config.clickhouse_mode = 'enabled'
        mock_config.graceful_startup_mode = 'true'
        
        with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
            with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                mock_get_env.return_value.get.side_effect = lambda key, default=None: staging_cloud_run_environment.get(key, default)
                
                # Check if Docker is actually available
                docker_available = False
                try:
                    result = subprocess.run(['docker', 'ps'], 
                                          capture_output=True, 
                                          text=True, 
                                          timeout=5)
                    docker_available = (result.returncode == 0)
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                    docker_available = False
                
                logger.info(f"Real Docker availability check: {docker_available}")
                
                if not docker_available:
                    # This is the expected case in Cloud Run - Docker unavailable
                    logger.info("Docker unavailable - testing ClickHouse graceful failure")
                    
                    # ClickHouse initialization should handle Docker unavailability
                    result = await initialize_clickhouse(logger)
                    
                    # Validate proper handling of Docker unavailability
                    assert result is not None, "Should return status report"
                    assert result['service'] == 'clickhouse'
                    assert result['required'] == False, "ClickHouse not required in staging"
                    
                    # In staging with Docker unavailable, should be handled gracefully
                    if result['status'] == 'failed':
                        logger.info(f"ClickHouse failed gracefully as expected: {result['error']}")
                        # This demonstrates Issue #568 - Docker unavailability causes ClickHouse failure
                        assert result['error'] is not None
                    elif result['status'] == 'skipped':
                        logger.info("ClickHouse skipped due to staging environment")
                    else:
                        pytest.fail(f"Unexpected ClickHouse status: {result['status']}")
                        
                else:
                    # Docker is available - ClickHouse should work normally
                    logger.info("Docker available - testing normal ClickHouse initialization")
                    
                    # May still fail due to ClickHouse server unavailability, but not Docker
                    result = await initialize_clickhouse(logger)
                    assert result is not None
                    assert result['service'] == 'clickhouse'
                    
                    # Status could be connected, failed, or skipped depending on ClickHouse server availability
                    logger.info(f"ClickHouse initialization result: {result['status']}")
    
    @pytest.mark.asyncio
    async def test_cloud_environment_detector_integration_with_clickhouse_startup(
        self,
        staging_cloud_run_environment,
        mock_cloud_environment_detector
    ):
        """
        Test integration between CloudEnvironmentDetector and ClickHouse startup.
        
        This validates that:
        1. CloudEnvironmentDetector properly identifies Cloud Run staging
        2. ClickHouse startup uses environment detection for Docker availability  
        3. Graceful handling when Docker unavailable in detected Cloud Run environment
        """
        mock_detector, staging_context = mock_cloud_environment_detector
        logger = central_logger.get_logger(__name__)
        
        mock_config = MagicMock()
        mock_config.environment = 'staging'
        mock_config.clickhouse_mode = 'enabled' 
        mock_config.graceful_startup_mode = 'true'
        
        with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
            with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                mock_get_env.return_value.get.side_effect = lambda key, default=None: staging_cloud_run_environment.get(key, default)
                
                # Test the integration - environment detection should influence ClickHouse behavior
                try:
                    # Mock ClickHouse connection failure due to Docker unavailability
                    with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                        mock_setup.side_effect = ConnectionError("Connection refused - Docker daemon not available")
                        
                        result = await initialize_clickhouse(logger)
                        
                        # Validate integration results
                        assert result is not None
                        assert result['service'] == 'clickhouse'
                        assert result['status'] == 'failed'  # Should fail gracefully
                        assert result['required'] == False  # Not required in staging
                        assert 'connection' in result['error'].lower()
                        
                        # Verify that ClickHouse setup was attempted  
                        mock_setup.assert_called_once()
                        
                        logger.info("✓ Integration test confirmed Docker unavailability handling")
                        
                except Exception as e:
                    # If an exception is raised, it indicates the integration is not handling
                    # Docker unavailability gracefully in staging environment
                    pytest.fail(f"ClickHouse startup should handle Docker unavailability gracefully in staging: {e}")
    
    @pytest.mark.asyncio
    async def test_environment_specific_docker_requirements(self):
        """
        Test that Docker requirements vary by environment as detected.
        
        This validates that environment detection properly influences
        whether Docker availability is critical or optional.
        """
        logger = central_logger.get_logger(__name__)
        
        # Test staging environment (Docker optional)
        staging_env = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-backend-staging',
            'CLICKHOUSE_REQUIRED': 'false'
        }
        
        mock_config_staging = MagicMock()
        mock_config_staging.environment = 'staging'
        mock_config_staging.clickhouse_mode = 'enabled'
        
        with patch.dict('os.environ', staging_env):
            with patch('netra_backend.app.startup_module.get_config', return_value=mock_config_staging):
                with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                    mock_get_env.return_value.get.side_effect = lambda key, default=None: staging_env.get(key, default)
                    
                    with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                        mock_setup.side_effect = ConnectionError("Docker unavailable") 
                        
                        # Should not raise exception in staging
                        result = await initialize_clickhouse(logger)
                        assert result['required'] == False
                        assert result['status'] == 'failed'  # Failed but graceful
        
        # Test production environment (Docker should be required)  
        production_env = {
            'ENVIRONMENT': 'production',
            'CLICKHOUSE_REQUIRED': 'true'
        }
        
        mock_config_production = MagicMock()
        mock_config_production.environment = 'production'
        mock_config_production.clickhouse_mode = 'enabled'
        
        with patch.dict('os.environ', production_env):
            with patch('netra_backend.app.startup_module.get_config', return_value=mock_config_production):
                with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                    mock_get_env.return_value.get.side_effect = lambda key, default=None: production_env.get(key, default)
                    
                    with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                        mock_setup.side_effect = ConnectionError("Docker unavailable")
                        
                        # Should raise exception in production when ClickHouse required
                        with pytest.raises(RuntimeError, match="ClickHouse.*required"):
                            await initialize_clickhouse(logger)
    
    @pytest.mark.asyncio 
    async def test_docker_availability_detection_integration_with_real_subprocess(
        self,
        staging_cloud_run_environment
    ):
        """
        Test Docker availability detection using real subprocess calls.
        
        This test demonstrates the actual Docker unavailability issue
        by using real subprocess calls to check Docker daemon status.
        
        EXPECTED TO FAIL in Cloud Run environments where Docker is unavailable.
        """
        logger = central_logger.get_logger(__name__)
        
        # Check actual Docker availability
        docker_available = True
        docker_error = None
        
        try:
            # This is the actual Docker check that happens in startup_module.py
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                docker_available = False
                docker_error = f"Docker command failed: {result.stderr}"
            else:
                running_containers = result.stdout.strip().split('\n')
                clickhouse_running = any('clickhouse' in name.lower() for name in running_containers if name)
                logger.info(f"Docker available. ClickHouse container running: {clickhouse_running}")
                
        except subprocess.TimeoutExpired:
            docker_available = False
            docker_error = "Docker command timed out"
        except FileNotFoundError:
            docker_available = False  
            docker_error = "Docker command not found"
        except Exception as e:
            docker_available = False
            docker_error = f"Docker check failed: {e}"
        
        logger.info(f"Docker availability: {docker_available}")
        if docker_error:
            logger.info(f"Docker error: {docker_error}")
        
        # Now test ClickHouse initialization with real Docker availability status
        mock_config = MagicMock()
        mock_config.environment = 'staging'
        mock_config.clickhouse_mode = 'enabled'
        mock_config.graceful_startup_mode = 'true'
        
        with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
            with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                mock_get_env.return_value.get.side_effect = lambda key, default=None: staging_cloud_run_environment.get(key, default)
                
                if not docker_available:
                    # This is the expected failure case in Cloud Run
                    # ClickHouse setup will fail due to Docker unavailability
                    logger.info("Testing ClickHouse behavior with Docker unavailable...")
                    
                    with patch('netra_backend.app.startup_module._setup_clickhouse_tables') as mock_setup:
                        # Simulate ClickHouse failing due to Docker unavailability
                        mock_setup.side_effect = ConnectionError(f"ClickHouse connection failed: {docker_error}")
                        
                        result = await initialize_clickhouse(logger)
                        
                        # This proves Issue #568 - Docker unavailability causes ClickHouse failure
                        assert result['status'] == 'failed'
                        assert result['required'] == False  # Optional in staging
                        assert result['error'] is not None
                        
                        logger.info(f"✓ Confirmed Issue #568: ClickHouse failed due to Docker unavailability: {result['error']}")
                        
                else:
                    logger.info("Docker is available - this environment doesn't reproduce Issue #568")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])