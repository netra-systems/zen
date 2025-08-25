"""Critical Auth Service Staging Shutdown Timeout Failures - Failing Tests
Tests that replicate specific graceful shutdown timeout issues found in staging logs.

CRITICAL SHUTDOWN TIMEOUT ISSUES TO REPLICATE:
1. SHUTDOWN_TIMEOUT_SECONDS environment variable not respected in staging
2. Cloud Run termination signals not handled within allocated time window
3. Database connection pools hanging during shutdown causing timeouts
4. Redis session cleanup hanging during service termination

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Service lifecycle reliability in production environments
- Value Impact: Prevents ungraceful shutdowns that could cause data corruption
- Strategic Impact: Ensures proper resource cleanup for enterprise scalability
"""

import os
import sys
import pytest
import asyncio
import logging
import signal
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import asynccontextmanager

from auth_service.auth_core.database.connection import AuthDatabase, auth_db
from auth_service.auth_core.config import AuthConfig
from auth_service.main import lifespan, shutdown_event
from test_framework.environment_markers import env, staging_only, env_requires

logger = logging.getLogger(__name__)


@env("staging")
@env_requires(services=["auth_service"], features=["cloud_run_configured"])
class TestCriticalStagingShutdownTimeouts:
    """Test suite for staging-specific shutdown timeout failures."""
    
    @pytest.mark.asyncio
    async def test_shutdown_timeout_seconds_environment_variable_ignored(self):
        """FAILING TEST: Replicates SHUTDOWN_TIMEOUT_SECONDS being ignored in staging.
        
        The staging environment might not respect the SHUTDOWN_TIMEOUT_SECONDS
        configuration, causing shutdowns to exceed Cloud Run's termination window.
        """
        # Set a specific timeout that should be honored
        timeout_env = {
            'ENVIRONMENT': 'staging',
            'SHUTDOWN_TIMEOUT_SECONDS': '3',  # Short timeout for testing
            'K_SERVICE': 'netra-auth-staging',  # Cloud Run indicator
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, timeout_env):
            test_auth_db = AuthDatabase()
            
            # Mock engine that takes longer than the configured timeout
            mock_engine = AsyncMock()
            
            async def slow_dispose():
                # Takes longer than SHUTDOWN_TIMEOUT_SECONDS (3 seconds)
                await asyncio.sleep(5.0)
            
            mock_engine.dispose = AsyncMock(side_effect=slow_dispose)
            test_auth_db.engine = mock_engine
            test_auth_db._initialized = True
            
            # Get the configured timeout - if it's not respected, this test will fail
            expected_timeout = float(os.getenv("SHUTDOWN_TIMEOUT_SECONDS", "8"))
            
            start_time = asyncio.get_event_loop().time()
            
            # Attempt shutdown with environment-configured timeout
            try:
                await asyncio.wait_for(test_auth_db.close(timeout=expected_timeout), timeout=expected_timeout + 1)
                # If it completes within the timeout, the configuration was respected
                elapsed = asyncio.get_event_loop().time() - start_time
                assert elapsed <= expected_timeout, f"Shutdown took {elapsed}s but should respect {expected_timeout}s limit"
            except asyncio.TimeoutError:
                elapsed = asyncio.get_event_loop().time() - start_time
                # This indicates the environment variable is being ignored
                if elapsed > expected_timeout:
                    pytest.fail(f"SHUTDOWN_TIMEOUT_SECONDS={expected_timeout} ignored - shutdown took {elapsed}s")
            
            logger.error(f"Shutdown timeout configuration test - Expected: {expected_timeout}s, Actual: {elapsed}s")
    
    @pytest.mark.asyncio  
    async def test_cloud_run_termination_signal_handling_timeout(self):
        """FAILING TEST: Tests Cloud Run SIGTERM handling timeout in staging.
        
        Cloud Run sends SIGTERM and gives ~10 seconds before SIGKILL. The service
        should handle this gracefully within the allotted time.
        """
        cloud_run_env = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-auth-staging',
            'K_REVISION': 'netra-auth-staging-001',
            'PORT': '8080',
            'SHUTDOWN_TIMEOUT_SECONDS': '8',  # Cloud Run typical timeout
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, cloud_run_env):
            # Simulate the lifespan shutdown process with long-running cleanup
            test_auth_db = AuthDatabase()
            mock_engine = AsyncMock()
            mock_redis_manager = AsyncMock()
            
            # Database cleanup that hangs
            async def hanging_db_close():
                logger.warning("Database connection hanging during Cloud Run shutdown")
                await asyncio.sleep(12.0)  # Longer than Cloud Run allows
            
            # Redis cleanup that also hangs  
            async def hanging_redis_close():
                logger.warning("Redis connection hanging during Cloud Run shutdown")
                await asyncio.sleep(8.0)
            
            mock_engine.dispose = AsyncMock(side_effect=hanging_db_close)
            mock_redis_manager.close_redis = AsyncMock(side_effect=hanging_redis_close)
            
            test_auth_db.engine = mock_engine
            test_auth_db._initialized = True
            
            # Simulate Cloud Run termination sequence
            cloud_run_timeout = 10.0  # Cloud Run SIGTERM->SIGKILL window
            
            start_time = asyncio.get_event_loop().time()
            
            # Create shutdown tasks like in the actual lifespan
            cleanup_tasks = []
            
            async def close_database():
                try:
                    await test_auth_db.close()
                except Exception as e:
                    logger.warning(f"Database close error: {e}")
            
            async def close_redis():
                try:
                    await mock_redis_manager.close_redis()
                except Exception as e:
                    logger.warning(f"Redis close error: {e}")
            
            cleanup_tasks.extend([close_database(), close_redis()])
            
            # Test if cleanup completes within Cloud Run's termination window
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=cloud_run_timeout
                )
                
                elapsed = asyncio.get_event_loop().time() - start_time
                logger.info(f"Cloud Run shutdown completed in {elapsed}s")
                
            except asyncio.TimeoutError:
                elapsed = asyncio.get_event_loop().time() - start_time
                # This simulates Cloud Run SIGKILL scenario
                logger.error(f"Cloud Run shutdown timeout - cleanup exceeded {cloud_run_timeout}s window")
                pytest.fail(f"Service shutdown timeout in Cloud Run environment: {elapsed}s > {cloud_run_timeout}s")
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_hanging_during_staging_shutdown(self):
        """FAILING TEST: Tests database connection pools hanging during staging shutdown.
        
        Connection pools in staging might have connections that don't close properly,
        causing shutdown timeouts.
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-db-host',
            'POSTGRES_DB': 'postgres', 
            'SHUTDOWN_TIMEOUT_SECONDS': '5',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, staging_env):
            test_auth_db = AuthDatabase()
            mock_engine = AsyncMock()
            mock_pool = MagicMock()
            
            # Simulate pool with active connections that won't close
            mock_pool.size.return_value = 5
            mock_pool.checked_out.return_value = 3  # Active connections
            mock_pool.checked_in.return_value = 2
            mock_pool.invalid.return_value = 0
            
            mock_engine.pool = mock_pool
            
            # Pool disposal hangs due to active connections
            async def hanging_pool_disposal():
                logger.warning("Connection pool hanging - active connections won't close")
                # Simulate connections that don't respond to close signals
                await asyncio.sleep(10.0)  # Exceeds any reasonable timeout
            
            mock_engine.dispose = AsyncMock(side_effect=hanging_pool_disposal)
            
            test_auth_db.engine = mock_engine
            test_auth_db._initialized = True
            
            shutdown_timeout = 5.0  # From environment
            start_time = asyncio.get_event_loop().time()
            
            # Attempt shutdown with realistic timeout
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(test_auth_db.close(), timeout=shutdown_timeout)
            
            elapsed = asyncio.get_event_loop().time() - start_time
            assert elapsed >= shutdown_timeout
            
            # Verify pool still has active connections after timeout
            assert mock_pool.checked_out.return_value > 0
            
            logger.error(f"Database pool hanging caused shutdown timeout: {elapsed}s")
    
    @pytest.mark.asyncio
    async def test_redis_session_cleanup_hanging_during_shutdown(self):
        """FAILING TEST: Tests Redis session cleanup hanging during service shutdown.
        
        Redis connections for session management might hang during cleanup,
        preventing graceful shutdown within timeout limits.
        """
        redis_env = {
            'ENVIRONMENT': 'staging',
            'REDIS_URL': 'redis://staging-redis:6379/0',
            'REDIS_DISABLED': 'false',
            'SHUTDOWN_TIMEOUT_SECONDS': '4',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, redis_env):
            # Mock Redis manager that hangs during shutdown
            mock_redis_manager = AsyncMock()
            
            async def hanging_redis_cleanup():
                logger.warning("Redis session cleanup hanging during shutdown")
                # Simulate Redis connections that don't close properly
                await asyncio.sleep(8.0)  # Longer than shutdown timeout
            
            mock_redis_manager.close_redis = AsyncMock(side_effect=hanging_redis_cleanup)
            
            # Simulate the Redis cleanup task from lifespan
            shutdown_timeout = float(os.getenv("SHUTDOWN_TIMEOUT_SECONDS", "4"))
            
            start_time = asyncio.get_event_loop().time()
            
            try:
                await asyncio.wait_for(mock_redis_manager.close_redis(), timeout=shutdown_timeout)
            except asyncio.TimeoutError:
                elapsed = asyncio.get_event_loop().time() - start_time
                assert elapsed >= shutdown_timeout
                logger.error(f"Redis cleanup timeout: {elapsed}s >= {shutdown_timeout}s")
                pytest.fail(f"Redis session cleanup hanging prevented graceful shutdown")


@env("staging")
class TestStagingShutdownSignalHandling:
    """Test signal handling during shutdown in staging environment."""
    
    @pytest.mark.asyncio
    async def test_sigterm_handler_timeout_in_staging_deployment(self):
        """FAILING TEST: Tests SIGTERM signal handler timeout in staging deployment.
        
        The service should handle SIGTERM within a reasonable time frame,
        but might hang on cleanup operations in staging.
        """
        signal_env = {
            'ENVIRONMENT': 'staging', 
            'K_SERVICE': 'netra-auth-staging',
            'SHUTDOWN_TIMEOUT_SECONDS': '6',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, signal_env):
            # Mock the global shutdown event
            test_shutdown_event = asyncio.Event()
            
            # Simulate long-running cleanup that doesn't respond to signals
            async def unresponsive_cleanup():
                logger.warning("Cleanup operation not responding to SIGTERM")
                try:
                    # This should be cancelled when SIGTERM is received, but isn't
                    await asyncio.sleep(15.0)  # Very long operation
                except asyncio.CancelledError:
                    logger.info("Cleanup operation cancelled (this should happen)")
                    # But then it continues doing work anyway
                    await asyncio.sleep(2.0)  # Still does more work
                    raise
            
            cleanup_task = asyncio.create_task(unresponsive_cleanup())
            
            # Start the cleanup
            start_time = asyncio.get_event_loop().time()
            
            # Simulate SIGTERM after a short delay
            async def send_sigterm():
                await asyncio.sleep(0.5)
                test_shutdown_event.set()  # Signal shutdown
                cleanup_task.cancel()  # Try to cancel cleanup
            
            signal_task = asyncio.create_task(send_sigterm())
            
            # Wait for either completion or timeout
            shutdown_timeout = float(os.getenv("SHUTDOWN_TIMEOUT_SECONDS", "6"))
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(cleanup_task, signal_task, return_exceptions=True),
                    timeout=shutdown_timeout
                )
                
                elapsed = asyncio.get_event_loop().time() - start_time
                logger.info(f"SIGTERM handling completed in {elapsed}s")
                
            except asyncio.TimeoutError:
                elapsed = asyncio.get_event_loop().time() - start_time
                logger.error(f"SIGTERM handler timeout: {elapsed}s >= {shutdown_timeout}s")
                
                # Clean up
                cleanup_task.cancel()
                signal_task.cancel()
                
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass
                    
                try:
                    await signal_task  
                except asyncio.CancelledError:
                    pass
                
                pytest.fail(f"SIGTERM handler exceeded timeout in staging: {elapsed}s > {shutdown_timeout}s")
    
    def test_shutdown_timeout_environment_variable_type_conversion_error(self):
        """FAILING TEST: Tests type conversion errors with SHUTDOWN_TIMEOUT_SECONDS.
        
        Environment variables are strings, and improper conversion might cause
        default timeouts to be used instead of configured values.
        """
        # Test various invalid timeout values that might cause conversion errors
        invalid_timeouts = [
            'invalid',     # Non-numeric string
            '3.5.2',       # Invalid float format
            'ten',         # Word instead of number
            '${TIMEOUT}',  # Unexpanded environment variable
            '',            # Empty string
            'None',        # String "None"
            '-5',          # Negative timeout
            '0',           # Zero timeout
            '999999',      # Unreasonably large timeout
        ]
        
        for invalid_timeout in invalid_timeouts:
            test_env = {
                'ENVIRONMENT': 'staging',
                'SHUTDOWN_TIMEOUT_SECONDS': invalid_timeout,
                'AUTH_FAST_TEST_MODE': 'false'
            }
            
            with patch.dict(os.environ, test_env):
                # Test what happens when the service tries to parse the timeout
                try:
                    # This is how it's parsed in main.py
                    shutdown_timeout = float(os.getenv("SHUTDOWN_TIMEOUT_SECONDS", "8"))
                    
                    # If conversion succeeds with invalid input, that's a problem
                    if invalid_timeout in ['invalid', 'ten', '${TIMEOUT}', '', 'None']:
                        pytest.fail(f"Invalid timeout '{invalid_timeout}' should not convert to float: {shutdown_timeout}")
                    
                    # Negative or zero timeouts should be rejected
                    if shutdown_timeout <= 0:
                        pytest.fail(f"Invalid timeout '{invalid_timeout}' resulted in non-positive value: {shutdown_timeout}")
                    
                    # Unreasonably large timeouts should be capped
                    if shutdown_timeout > 300:  # 5 minutes is reasonable max
                        pytest.fail(f"Timeout '{invalid_timeout}' resulted in unreasonably large value: {shutdown_timeout}")
                    
                    logger.warning(f"Timeout '{invalid_timeout}' converted to: {shutdown_timeout}")
                    
                except ValueError as e:
                    # Type conversion errors should be handled gracefully
                    logger.info(f"Timeout '{invalid_timeout}' correctly caused ValueError: {e}")
                    
                    # But the service should still have a reasonable default
                    default_timeout = float(os.getenv("SHUTDOWN_TIMEOUT_SECONDS", "8"))
                    if default_timeout != 8.0:
                        pytest.fail(f"Default timeout not used after conversion error: {default_timeout}")


# Mark all tests as staging-specific integration tests with timeout handling
pytestmark = [pytest.mark.integration, pytest.mark.staging, pytest.mark.timeout(60)]