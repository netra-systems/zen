"""
E2E test for ClickHouse Docker availability in Cloud Run staging environment (Issue #568).

This test validates the complete end-to-end behavior of ClickHouse initialization
when Docker is unavailable in GCP Cloud Run staging environment.

DESIGNED FOR REAL GCP STAGING: This test is specifically designed to run in 
the real GCP staging environment to demonstrate Issue #568 in production-like conditions.

EXPECTED TO FAIL: In GCP Cloud Run staging, Docker daemon is not available,
so this test should FAIL, proving that Issue #568 exists.

Test Status: IMPLEMENT AND EXECUTE
"""
import pytest
import asyncio
import os
import httpx
import subprocess
from typing import Optional, Dict, Any
from unittest.mock import patch, MagicMock

from netra_backend.app.startup_module import initialize_clickhouse, run_complete_startup
from netra_backend.app.core.environment_context.cloud_environment_detector import (
    get_cloud_environment_detector,
    detect_current_environment
)
from netra_backend.app.logging_config import central_logger
from fastapi import FastAPI


class TestClickHouseDockerCloudRunE2E:
    """End-to-end tests for ClickHouse Docker availability in Cloud Run."""
    
    @pytest.fixture
    def gcp_staging_app(self):
        """Create FastAPI app for GCP staging E2E testing."""
        app = FastAPI(title="ClickHouse E2E Test")
        return app
    
    def is_running_in_cloud_run(self) -> bool:
        """Detect if currently running in Google Cloud Run."""
        # Check for Cloud Run environment variables
        k_service = os.environ.get('K_SERVICE')
        google_project = os.environ.get('GOOGLE_CLOUD_PROJECT')
        port = os.environ.get('PORT')
        
        return bool(k_service and google_project and port)
    
    def get_real_docker_availability(self) -> Dict[str, Any]:
        """Check real Docker daemon availability."""
        docker_status = {
            'available': False,
            'error': None,
            'containers': [],
            'command_exists': False
        }
        
        try:
            # Check if docker command exists
            docker_version_result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            docker_status['command_exists'] = (docker_version_result.returncode == 0)
            
            if docker_status['command_exists']:
                # Check if daemon is accessible
                docker_ps_result = subprocess.run(
                    ['docker', 'ps', '--format', '{{.Names}}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if docker_ps_result.returncode == 0:
                    docker_status['available'] = True
                    container_names = docker_ps_result.stdout.strip().split('\n')
                    docker_status['containers'] = [name for name in container_names if name]
                else:
                    docker_status['error'] = f"Docker daemon not accessible: {docker_ps_result.stderr}"
            else:
                docker_status['error'] = "Docker command not found"
                
        except subprocess.TimeoutExpired:
            docker_status['error'] = "Docker command timed out"
        except FileNotFoundError:
            docker_status['error'] = "Docker command not found in PATH"
        except Exception as e:
            docker_status['error'] = f"Docker check failed: {str(e)}"
        
        return docker_status
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.environ.get('RUN_GCP_E2E_TESTS', '').lower() == 'true',
        reason="GCP E2E tests require RUN_GCP_E2E_TESTS=true environment variable"
    )
    async def test_real_gcp_cloud_run_docker_unavailability_e2e(self, gcp_staging_app):
        """
        E2E test in real GCP Cloud Run staging environment.
        
        This test runs in the actual GCP staging environment and validates:
        1. Environment detection correctly identifies Cloud Run
        2. Docker is unavailable (as expected in Cloud Run)
        3. ClickHouse initialization fails gracefully
        4. System continues operation without ClickHouse
        
        EXPECTED TO FAIL: This test should document Docker unavailability in Cloud Run.
        """
        logger = central_logger.get_logger(__name__)
        
        # Verify we're running in Cloud Run staging
        is_cloud_run = self.is_running_in_cloud_run()
        logger.info(f"Running in Cloud Run: {is_cloud_run}")
        
        if is_cloud_run:
            logger.info("✓ Confirmed running in Cloud Run environment")
            
            # Get real environment details
            k_service = os.environ.get('K_SERVICE', 'unknown')
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'unknown')
            logger.info(f"Cloud Run Service: {k_service}")
            logger.info(f"GCP Project: {project_id}")
            
            # Test environment detection
            try:
                environment_context = await detect_current_environment()
                logger.info(f"Detected Environment: {environment_context.environment_type.value}")
                logger.info(f"Detected Platform: {environment_context.cloud_platform.value}")
                logger.info(f"Detection Confidence: {environment_context.confidence_score}")
                
                # Validate Cloud Run detection
                assert environment_context.cloud_platform.value in ['cloud_run', 'unknown'], \
                    f"Expected Cloud Run platform, got: {environment_context.cloud_platform.value}"
                    
            except Exception as env_error:
                logger.error(f"Environment detection failed: {env_error}")
                pytest.fail(f"Environment detection failed in Cloud Run: {env_error}")
        else:
            logger.warning("Not running in Cloud Run - using Cloud Run simulation")
        
        # Check real Docker availability
        docker_status = self.get_real_docker_availability()
        logger.info(f"Docker Status: {docker_status}")
        
        if not docker_status['available']:
            logger.info("✓ Confirmed Docker unavailable - testing Issue #568 scenario")
            logger.info(f"Docker Error: {docker_status['error']}")
            
            # This is the Issue #568 scenario - Docker unavailable in Cloud Run
            
            # Test ClickHouse initialization with real Docker unavailability
            mock_config = MagicMock()
            mock_config.environment = 'staging'
            mock_config.clickhouse_mode = 'enabled'
            mock_config.graceful_startup_mode = 'true'
            
            with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
                # Use real environment variables
                result = await initialize_clickhouse(logger)
                
                # Validate Issue #568 behavior
                assert result is not None, "ClickHouse should return status report"
                assert result['service'] == 'clickhouse'
                
                if result['required']:
                    # If ClickHouse is required, initialization should fail hard
                    assert result['status'] == 'failed', \
                        f"ClickHouse required but status is {result['status']}"
                    logger.error(f"✓ Issue #568 confirmed: Required ClickHouse failed due to Docker unavailability")
                else:
                    # If ClickHouse is optional, should fail gracefully
                    expected_statuses = ['failed', 'skipped']
                    assert result['status'] in expected_statuses, \
                        f"Expected {expected_statuses}, got: {result['status']}"
                    logger.info(f"✓ Issue #568 documented: Optional ClickHouse failed gracefully: {result['status']}")
                
                # Document the Docker unavailability error
                if result['status'] == 'failed':
                    assert result['error'] is not None, "Failed status should include error message"
                    logger.info(f"ClickHouse Error: {result['error']}")
                    
                    # Validate error is related to Docker/connectivity
                    error_lower = result['error'].lower()
                    expected_error_keywords = [
                        'connection', 'refused', 'timeout', 'unreachable', 
                        'docker', 'daemon', 'network'
                    ]
                    has_expected_error = any(keyword in error_lower for keyword in expected_error_keywords)
                    
                    if has_expected_error:
                        logger.info("✓ Error message indicates connectivity/Docker issue as expected")
                    else:
                        logger.warning(f"Error message may not indicate Docker issue: {result['error']}")
                        
        else:
            logger.info("Docker is available - this environment cannot reproduce Issue #568")
            logger.info(f"Available containers: {docker_status['containers']}")
            
            # Test normal ClickHouse behavior when Docker is available
            result = await initialize_clickhouse(logger)
            logger.info(f"ClickHouse with Docker available: {result['status']}")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.environ.get('RUN_GCP_E2E_TESTS', '').lower() == 'true',
        reason="GCP E2E tests require RUN_GCP_E2E_TESTS=true environment variable"
    )
    async def test_full_startup_sequence_with_docker_unavailable_e2e(self, gcp_staging_app):
        """
        Test complete startup sequence in Cloud Run with Docker unavailable.
        
        This validates that the entire application startup handles Docker
        unavailability gracefully and continues to provide core functionality.
        """
        logger = central_logger.get_logger(__name__)
        
        docker_status = self.get_real_docker_availability()
        logger.info(f"Testing full startup with Docker status: {docker_status}")
        
        if not docker_status['available']:
            logger.info("Testing complete startup sequence with Docker unavailable...")
            
            try:
                # Attempt full startup sequence
                start_time, startup_logger = await run_complete_startup(gcp_staging_app)
                
                # Validate startup completed despite Docker unavailability
                assert hasattr(gcp_staging_app.state, 'startup_complete'), \
                    "Startup should set completion flag"
                
                # Check if core services are available
                core_services = ['db_session_factory', 'llm_manager', 'redis_manager']
                available_services = []
                unavailable_services = []
                
                for service in core_services:
                    if hasattr(gcp_staging_app.state, service) and getattr(gcp_staging_app.state, service) is not None:
                        available_services.append(service)
                    else:
                        unavailable_services.append(service)
                
                logger.info(f"Available services: {available_services}")
                logger.info(f"Unavailable services: {unavailable_services}")
                
                # Core chat functionality should still work
                essential_services = ['llm_manager']  # Minimum for chat
                for essential_service in essential_services:
                    assert essential_service in available_services, \
                        f"Essential service {essential_service} not available - chat functionality broken"
                
                logger.info("✓ Core chat functionality should be available despite Docker unavailability")
                
                # ClickHouse should be handled gracefully
                clickhouse_available = getattr(gcp_staging_app.state, 'clickhouse_available', None)
                if clickhouse_available is False:
                    logger.info("✓ ClickHouse marked as unavailable - graceful degradation working")
                else:
                    logger.info(f"ClickHouse availability status: {clickhouse_available}")
                
            except Exception as startup_error:
                # Startup should not fail completely due to Docker unavailability
                logger.error(f"Full startup failed due to Docker unavailability: {startup_error}")
                
                # If startup fails completely, this indicates a critical Issue #568 impact
                pytest.fail(
                    f"Complete application startup failed due to Docker unavailability. "
                    f"This indicates Issue #568 has broader impact than just ClickHouse: {startup_error}"
                )
        else:
            logger.info("Docker available - testing normal startup sequence")
            start_time, startup_logger = await run_complete_startup(gcp_staging_app)
            logger.info("✓ Normal startup completed successfully")
    
    @pytest.mark.asyncio  
    async def test_simulated_cloud_run_environment_docker_unavailable(self):
        """
        Test simulated Cloud Run environment with Docker unavailable.
        
        This test can run in any environment by simulating Cloud Run conditions
        and Docker unavailability to validate Issue #568 handling.
        """
        logger = central_logger.get_logger(__name__)
        
        # Simulate Cloud Run environment variables
        cloud_run_env = {
            'K_SERVICE': 'netra-backend-staging',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'PORT': '8080',
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_REQUIRED': 'false'
        }
        
        with patch.dict('os.environ', cloud_run_env, clear=False):
            # Mock Docker being unavailable
            def mock_subprocess_run(cmd, **kwargs):
                if cmd[0] == 'docker':
                    if 'ps' in cmd:
                        raise subprocess.CalledProcessError(1, cmd, "Cannot connect to the Docker daemon")
                    elif '--version' in cmd:
                        # Docker command exists but daemon not accessible
                        return MagicMock(returncode=1, stderr="Cannot connect to the Docker daemon")
                return MagicMock(returncode=0, stdout='', stderr='')
            
            with patch('subprocess.run', side_effect=mock_subprocess_run):
                # Test ClickHouse initialization in simulated Cloud Run
                mock_config = MagicMock()
                mock_config.environment = 'staging'
                mock_config.clickhouse_mode = 'enabled'
                mock_config.graceful_startup_mode = 'true'
                
                with patch('netra_backend.app.startup_module.get_config', return_value=mock_config):
                    with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                        mock_get_env.return_value.get.side_effect = lambda key, default=None: cloud_run_env.get(key, default)
                        
                        result = await initialize_clickhouse(logger)
                        
                        # Validate simulated Issue #568 behavior
                        assert result is not None
                        assert result['service'] == 'clickhouse'
                        assert result['required'] == False, "Should not be required in staging"
                        
                        # Should handle Docker unavailability gracefully
                        if result['status'] == 'failed':
                            logger.info(f"✓ Simulated Issue #568: ClickHouse failed gracefully: {result['error']}")
                        elif result['status'] == 'skipped':
                            logger.info("✓ ClickHouse skipped in simulated Cloud Run environment")
                        else:
                            pytest.fail(f"Unexpected status in simulated Cloud Run: {result['status']}")
    
    def test_docker_detection_utility_methods(self):
        """Test utility methods for Docker detection."""
        # Test Cloud Run detection
        is_cloud_run = self.is_running_in_cloud_run()
        logger = central_logger.get_logger(__name__)
        logger.info(f"Cloud Run detection result: {is_cloud_run}")
        
        # Test Docker availability detection  
        docker_status = self.get_real_docker_availability()
        logger.info(f"Docker availability detection: {docker_status}")
        
        # Validate structure of results
        assert isinstance(docker_status, dict)
        assert 'available' in docker_status
        assert 'error' in docker_status
        assert 'command_exists' in docker_status
        assert isinstance(docker_status['available'], bool)
        
        if not docker_status['available']:
            logger.info(f"✓ Docker unavailable as expected in Cloud Run: {docker_status['error']}")
        else:
            logger.info("Docker is available in this environment")


if __name__ == "__main__":
    # Run with specific markers for GCP E2E tests
    pytest.main([__file__, "-v", "-m", "not skipif"])