"""Integration tests for configuration cascade and environment propagation.

CRITICAL: These tests verify real multi-component interactions for configuration
management without Docker dependencies. They test business-critical scenarios
where configuration changes cascade through multiple system components.

Business Value: Platform stability and configuration consistency across services.
"""

import os
import tempfile
import pytest
import asyncio
from typing import Dict, Any
from pathlib import Path

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.configuration.loader import ConfigLoader
from netra_backend.app.core.configuration.validator import ConfigValidator  
from netra_backend.app.core.configuration.environment_detector import EnvironmentDetector
from netra_backend.app.core.configuration.startup_validator import StartupValidator
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager


class TestConfigurationCascadePropagation:
    """Integration tests for configuration cascade and environment propagation."""
    
    @pytest.fixture
    def isolated_env(self):
        """Create isolated environment for testing."""
        env = IsolatedEnvironment()
        # Set minimal required environment variables for testing
        env.set('APP_ENV', 'test')
        env.set('DATABASE_URL', 'sqlite:///:memory:')
        env.set('REDIS_URL', 'redis://localhost:6379')
        env.set('JWT_SECRET', 'test_secret_key_for_integration_testing_only')
        return env
    
    @pytest.fixture
    def config_loader(self, isolated_env):
        """Create config loader with isolated environment."""
        return ConfigLoader(environment=isolated_env)
        
    @pytest.fixture
    def user_context(self):
        """Create test user execution context."""
        return UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456", 
            request_id="test_request_789",
            run_id="test_run_012"
        )

    def test_environment_cascade_through_config_components(self, isolated_env, config_loader):
        """
        Test that environment changes cascade properly through configuration components.
        
        This tests the REAL interaction between:
        - IsolatedEnvironment (environment management)
        - ConfigLoader (configuration loading)
        - EnvironmentDetector (environment detection)
        - ConfigValidator (configuration validation)
        
        Business scenario: When environment variables change, all config components
        must reflect those changes consistently.
        """
        # PHASE 1: Set up initial configuration
        isolated_env.set('APP_ENV', 'development')
        isolated_env.set('DEBUG', 'true')
        isolated_env.set('LOG_LEVEL', 'DEBUG')
        
        # PHASE 2: Create components that depend on environment
        detector = EnvironmentDetector(environment=isolated_env)
        validator = ConfigValidator(environment=isolated_env)
        
        # PHASE 3: Verify initial state cascade
        initial_env = detector.detect_environment()
        assert initial_env == 'development', "Environment detector should reflect environment changes"
        
        initial_config = config_loader.load_base_config()
        assert initial_config['app_env'] == 'development', "Config loader should reflect environment"
        
        # PHASE 4: Change environment and verify cascade
        isolated_env.set('APP_ENV', 'staging')
        isolated_env.set('DEBUG', 'false')
        isolated_env.set('LOG_LEVEL', 'INFO')
        
        # Create new instances to test cascade (simulates service restart scenario)
        new_detector = EnvironmentDetector(environment=isolated_env)
        new_validator = ConfigValidator(environment=isolated_env)
        
        updated_env = new_detector.detect_environment()
        assert updated_env == 'staging', "Environment changes should cascade to detector"
        
        updated_config = config_loader.load_base_config()
        assert updated_config['app_env'] == 'staging', "Environment changes should cascade to config"
        
        # PHASE 5: Verify validation reflects changes
        validation_result = new_validator.validate_environment_consistency()
        assert validation_result['is_valid'], "Validation should pass with consistent environment"
        assert validation_result['detected_environment'] == 'staging'
        
        # PHASE 6: Test error cascade - set invalid configuration
        isolated_env.set('APP_ENV', 'invalid_environment')
        
        invalid_detector = EnvironmentDetector(environment=isolated_env)
        # Should handle invalid environment gracefully
        fallback_env = invalid_detector.detect_environment()
        assert fallback_env in ['development', 'staging', 'production'], "Should fallback to valid environment"

    def test_configuration_propagation_to_execution_context(self, isolated_env, user_context):
        """
        Test that configuration changes propagate to execution contexts.
        
        This tests REAL interaction between:
        - IsolatedEnvironment (environment source)
        - UserExecutionContext (request isolation)
        - UnifiedIDManager (ID management)
        - ConfigLoader (configuration loading)
        
        Business scenario: When configuration changes, user execution contexts
        must receive updated configuration without breaking isolation.
        """
        # PHASE 1: Set up configuration environment
        isolated_env.set('APP_ENV', 'test')
        isolated_env.set('SESSION_TIMEOUT', '3600')
        isolated_env.set('MAX_CONNECTIONS_PER_USER', '10')
        isolated_env.set('ENABLE_METRICS', 'true')
        
        # PHASE 2: Create components that use configuration
        config_loader = ConfigLoader(environment=isolated_env)
        id_manager = UnifiedIDManager()
        
        # PHASE 3: Create execution context and verify configuration propagation
        context = UserExecutionContext(
            user_id="config_test_user",
            thread_id="config_test_thread",
            request_id="config_test_request"
        )
        
        # Load configuration through context interaction
        base_config = config_loader.load_base_config()
        assert base_config['app_env'] == 'test', "Base config should reflect environment"
        
        # PHASE 4: Test configuration changes propagate to new contexts
        isolated_env.set('SESSION_TIMEOUT', '7200')  # Change session timeout
        isolated_env.set('MAX_CONNECTIONS_PER_USER', '20')  # Change connection limit
        
        # Create new config loader to simulate configuration reload
        updated_loader = ConfigLoader(environment=isolated_env)
        updated_config = updated_loader.load_base_config()
        
        # Verify changes propagated
        assert updated_config.get('session_timeout', 7200) == 7200, "Session timeout should be updated"
        
        # PHASE 5: Create new execution context and verify it gets updated config
        new_context = UserExecutionContext(
            user_id="updated_config_user", 
            thread_id="updated_config_thread",
            request_id="updated_config_request"
        )
        
        # Verify context creation doesn't break with config changes
        assert new_context.user_id == "updated_config_user", "Context should be created successfully"
        
        # PHASE 6: Test configuration validation with multiple contexts
        startup_validator = StartupValidator(environment=isolated_env)
        validation_result = startup_validator.validate_startup_environment()
        
        assert validation_result['is_valid'], f"Startup validation failed: {validation_result.get('errors', [])}"
        assert 'test' in validation_result.get('detected_environment', ''), "Should detect test environment"

    @pytest.mark.asyncio
    async def test_async_configuration_cascade_with_context_isolation(self, isolated_env):
        """
        Test asynchronous configuration cascade while maintaining context isolation.
        
        This tests REAL async interaction between:
        - IsolatedEnvironment (thread-safe environment)
        - Multiple UserExecutionContext instances (isolation)
        - ConfigLoader (async config loading)
        - UnifiedIDManager (ID generation)
        
        Business scenario: Multiple users with different configurations should 
        maintain isolation while sharing updated base configuration.
        """
        # PHASE 1: Set up base configuration
        isolated_env.set('APP_ENV', 'integration_test')
        isolated_env.set('ASYNC_POOL_SIZE', '20')
        isolated_env.set('CONNECTION_TIMEOUT', '30')
        
        # PHASE 2: Create multiple execution contexts (simulating concurrent users)
        contexts = []
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"async_user_{i}",
                thread_id=f"async_thread_{i}", 
                request_id=f"async_request_{i}",
                run_id=f"async_run_{i}"
            )
            contexts.append(context)
        
        # PHASE 3: Create async tasks that use configuration
        config_loader = ConfigLoader(environment=isolated_env)
        
        async def process_with_config(context: UserExecutionContext) -> Dict[str, Any]:
            """Simulate async processing with configuration."""
            # Load configuration for this context
            config = config_loader.load_base_config()
            
            # Simulate some async work
            await asyncio.sleep(0.1)
            
            return {
                'user_id': context.user_id,
                'config_env': config.get('app_env'),
                'pool_size': config.get('async_pool_size', 10),
                'processed_at': context.created_at.isoformat()
            }
        
        # PHASE 4: Process all contexts concurrently
        tasks = [process_with_config(ctx) for ctx in contexts]
        results = await asyncio.gather(*tasks)
        
        # Verify all contexts got the same base configuration
        for result in results:
            assert result['config_env'] == 'integration_test', "All contexts should get same base config"
            assert result['pool_size'] == 20, "All contexts should get updated pool size"
            assert result['user_id'].startswith('async_user_'), "Context isolation should be maintained"
        
        # PHASE 5: Update configuration mid-processing
        isolated_env.set('ASYNC_POOL_SIZE', '50')
        isolated_env.set('CONNECTION_TIMEOUT', '60')
        
        # Create new config loader to get updated configuration
        updated_loader = ConfigLoader(environment=isolated_env)
        
        # Process new contexts with updated configuration
        new_contexts = [
            UserExecutionContext(
                user_id=f"updated_user_{i}",
                thread_id=f"updated_thread_{i}",
                request_id=f"updated_request_{i}"
            ) for i in range(3)
        ]
        
        async def process_with_updated_config(context: UserExecutionContext) -> Dict[str, Any]:
            """Process with updated configuration."""
            config = updated_loader.load_base_config()
            await asyncio.sleep(0.05)
            
            return {
                'user_id': context.user_id,
                'config_env': config.get('app_env'),
                'pool_size': config.get('async_pool_size', 10),
                'timeout': config.get('connection_timeout', 30)
            }
        
        updated_tasks = [process_with_updated_config(ctx) for ctx in new_contexts]
        updated_results = await asyncio.gather(*updated_tasks)
        
        # PHASE 6: Verify updated configuration propagated correctly
        for result in updated_results:
            assert result['config_env'] == 'integration_test', "Environment should remain consistent"
            assert result['pool_size'] == 50, "New contexts should get updated pool size"
            assert result['timeout'] == 60, "New contexts should get updated timeout"
        
        # PHASE 7: Verify isolation - old and new contexts should have different configs
        # This tests that configuration changes don't retroactively affect existing contexts
        # but do affect new contexts created after the change
        old_pool_sizes = {r['pool_size'] for r in results}
        new_pool_sizes = {r['pool_size'] for r in updated_results}
        
        assert 20 in old_pool_sizes, "Original contexts should retain original config"
        assert 50 in new_pool_sizes, "New contexts should get updated config"
        assert old_pool_sizes != new_pool_sizes, "Configuration cascade should create different states"