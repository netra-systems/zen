"""
Integration tests for environment-aware service startup coordination - Issue #586.

Tests real service startup timing with environment-specific optimizations and
WebSocket race condition prevention across different deployment environments.

Business Value Justification (BVJ):
- Segment: Platform/All Users
- Business Goal: Performance Optimization & Platform Reliability
- Value Impact: Validates service coordination works optimally across all deployment 
  environments while maintaining $500K+ ARR protection through reliable WebSocket connections
- Strategic Impact: Environment-aware service coordination ensures optimal performance
  per deployment context without compromising system stability

This test suite validates:
1. Real service startup timing with environment-optimized timeouts
2. Service dependency chain coordination (Database → Redis → Auth → Agent → WebSocket)
3. Race condition prevention maintained across all environments
4. Golden Path chat functionality preservation during environment-specific optimizations
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    create_gcp_websocket_validator,
    GCPReadinessState
)


class TestEnvironmentAwareServiceStartup(SSotBaseTestCase):
    """
    Test service startup with environment-aware timeout configuration.
    
    These tests validate that service startup coordination works correctly
    with environment-specific timeout optimizations while maintaining reliability.
    """
    
    def setup_method(self, method):
        """Set up test environment with service startup simulation context."""
        super().setup_method(method)
        self.record_metric("test_category", "environment_service_startup_integration")
        
        # Clear environment variables that affect service startup testing
        env_vars_to_clear = [
            "ENVIRONMENT", "K_SERVICE", "TESTING", "REDIS_MODE", "CLICKHOUSE_MODE"
        ]
        for var in env_vars_to_clear:
            if self.get_env_var(var):
                self.delete_env_var(var)
        
        # Create mock app_state with realistic service dependencies
        self.mock_app_state = self._create_mock_app_state()
    
    def _create_mock_app_state(self):
        """Create realistic mock app_state for service integration testing."""
        mock_state = MagicMock()
        
        # Startup phase tracking (simulates deterministic startup sequence)
        mock_state.startup_phase = "init"
        mock_state.startup_complete = False
        mock_state.startup_failed = False
        
        # Database components
        mock_state.db_session_factory = MagicMock()
        mock_state.database_available = False  # Initially unavailable
        
        # Redis components  
        mock_redis_manager = MagicMock()
        mock_redis_manager.is_connected = False  # Initially disconnected
        mock_state.redis_manager = mock_redis_manager
        
        # Auth components
        mock_state.key_manager = None  # Initially unavailable
        mock_state.auth_validation_complete = False
        
        # Agent components
        mock_state.agent_supervisor = None  # Initially unavailable
        mock_state.thread_service = None
        
        # WebSocket components
        mock_state.agent_websocket_bridge = None  # Initially unavailable
        
        return mock_state
    
    async def _simulate_service_startup_progression(self, environment="development"):
        """
        Simulate realistic service startup progression with environment-aware timing.
        
        This simulates the deterministic startup sequence phases:
        1. Init phase - basic initialization
        2. Dependencies phase - database and Redis startup
        3. Services phase - auth, agent supervisor, WebSocket bridge
        4. WebSocket phase - final WebSocket integration
        5. Complete phase - all services ready
        """
        startup_delays = {
            "development": {
                "database": 0.1,      # Very fast for development
                "redis": 0.05,        # Very fast for development  
                "auth": 0.1,          # Fast auth validation
                "agent": 0.2,         # Agent supervisor startup
                "websocket": 0.1      # WebSocket bridge setup
            },
            "staging": {
                "database": 0.3,      # Balanced timing for staging
                "redis": 0.2,         # Balanced Redis connection
                "auth": 0.3,          # Balanced auth validation
                "agent": 0.5,         # Agent supervisor with more checks
                "websocket": 0.2      # WebSocket bridge with validation
            },
            "production": {
                "database": 0.5,      # Conservative timing for production
                "redis": 0.3,         # Reliable Redis connection
                "auth": 0.5,          # Thorough auth validation
                "agent": 0.8,         # Full agent supervisor startup
                "websocket": 0.3      # Complete WebSocket validation
            }
        }
        
        delays = startup_delays.get(environment, startup_delays["development"])
        
        # Phase 1-2: Dependencies startup (database, Redis)
        self.mock_app_state.startup_phase = "dependencies"
        await asyncio.sleep(delays["database"])
        self.mock_app_state.database_available = True
        self.mock_app_state.db_session_factory = MagicMock()
        
        await asyncio.sleep(delays["redis"])
        self.mock_app_state.redis_manager.is_connected = True
        
        # Phase 3: Auth system startup
        self.mock_app_state.startup_phase = "cache"  # Cache phase includes auth
        await asyncio.sleep(delays["auth"])
        self.mock_app_state.key_manager = MagicMock()
        self.mock_app_state.auth_validation_complete = True
        
        # Phase 5: Services startup (agent supervisor, WebSocket bridge)
        self.mock_app_state.startup_phase = "services" 
        await asyncio.sleep(delays["agent"])
        self.mock_app_state.agent_supervisor = MagicMock()
        self.mock_app_state.thread_service = MagicMock()
        
        await asyncio.sleep(delays["websocket"])
        mock_bridge = MagicMock()
        mock_bridge.notify_agent_started = MagicMock()
        mock_bridge.notify_agent_completed = MagicMock() 
        mock_bridge.notify_tool_executing = MagicMock()
        self.mock_app_state.agent_websocket_bridge = mock_bridge
        
        # Phase 6: WebSocket integration
        self.mock_app_state.startup_phase = "websocket"
        
        # Phase 7: Startup complete
        self.mock_app_state.startup_phase = "complete"
        self.mock_app_state.startup_complete = True
    
    @pytest.mark.asyncio 
    async def test_development_environment_rapid_startup(self):
        """
        Test rapid service startup in development environment.
        
        CRITICAL: This test validates that services start within optimized timeouts
        using the 0.3x multiplier for very fast development feedback.
        
        Should initially fail if services take longer than development-optimized timeouts.
        """
        # Set up development environment
        with self.temp_env_vars(ENVIRONMENT="development"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Verify development configuration
            self.assertEqual(validator.environment, "development")
            self.assertEqual(validator.timeout_multiplier, 0.3)
            
            # Record test start time
            test_start = time.time()
            
            # Start service startup simulation in background
            startup_task = asyncio.create_task(
                self._simulate_service_startup_progression("development")
            )
            
            # Test WebSocket validation with development-optimized timeouts
            validation_start = time.time()
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
            validation_duration = time.time() - validation_start
            
            # Wait for startup simulation to complete
            await startup_task
            total_duration = time.time() - test_start
            
            # Validate rapid startup performance
            self.assertTrue(
                result.ready,
                f"Development environment should be ready quickly. Failed services: {result.failed_services}"
            )
            
            # Development should complete validation very quickly (< 2s)
            self.assertLess(
                validation_duration,
                2.0,
                f"Development validation should be very fast: took {validation_duration:.3f}s"
            )
            
            # Total test time should be very fast for development
            self.assertLess(
                total_duration,
                3.0,
                f"Development total startup should be very fast: took {total_duration:.3f}s"
            )
            
            self.record_metric("development_validation_duration", validation_duration)
            self.record_metric("development_total_duration", total_duration)
            self.record_metric("development_rapid_startup", "success")
    
    @pytest.mark.asyncio
    async def test_staging_environment_balanced_startup(self):
        """
        Test balanced service startup in staging environment.
        
        CRITICAL: This test validates that services start within balanced timeouts
        using the 0.7x multiplier for staging performance optimization.
        
        Should initially fail if staging balance not achieved correctly.
        """
        # Set up staging environment with GCP Cloud Run
        with self.temp_env_vars(ENVIRONMENT="staging", K_SERVICE="netra-backend-staging"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Verify staging configuration
            self.assertEqual(validator.environment, "staging")
            self.assertTrue(validator.is_gcp_environment)
            self.assertEqual(validator.timeout_multiplier, 0.7)
            
            # Record test start time
            test_start = time.time()
            
            # Start service startup simulation with staging timing
            startup_task = asyncio.create_task(
                self._simulate_service_startup_progression("staging")
            )
            
            # Test WebSocket validation with staging-optimized timeouts
            validation_start = time.time()
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
            validation_duration = time.time() - validation_start
            
            # Wait for startup simulation to complete
            await startup_task
            total_duration = time.time() - test_start
            
            # Validate balanced startup performance
            self.assertTrue(
                result.ready,
                f"Staging environment should achieve balanced readiness. Failed services: {result.failed_services}"
            )
            
            # Staging should complete validation in balanced time (< 4s)
            self.assertLess(
                validation_duration,
                4.0,
                f"Staging validation should be balanced: took {validation_duration:.3f}s"
            )
            
            # Should be faster than production baseline but not as aggressive as development
            self.assertLess(
                validation_duration,
                5.0,  # Faster than production baseline
                f"Staging should be faster than production: took {validation_duration:.3f}s"
            )
            
            # Verify Cloud Run safety minimum is maintained
            self.assertGreaterEqual(
                result.elapsed_time,
                0.5,  # Cloud Run minimum safety timeout
                "Cloud Run minimum safety timeout should be maintained in staging"
            )
            
            self.record_metric("staging_validation_duration", validation_duration) 
            self.record_metric("staging_total_duration", total_duration)
            self.record_metric("staging_balanced_startup", "success")
    
    @pytest.mark.asyncio
    async def test_production_environment_reliable_startup(self):
        """
        Test reliable service startup in production environment.
        
        CRITICAL: This test validates that services start within conservative timeouts
        using the 1.0x multiplier for maximum production reliability.
        
        Should initially fail if production reliability compromised by optimization.
        """
        # Set up production environment with GCP Cloud Run
        with self.temp_env_vars(ENVIRONMENT="production", K_SERVICE="netra-backend-prod"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Verify production configuration
            self.assertEqual(validator.environment, "production")
            self.assertTrue(validator.is_gcp_environment)
            self.assertEqual(validator.timeout_multiplier, 1.0)
            self.assertEqual(validator.safety_margin, 1.2)  # 20% safety margin
            
            # Record test start time
            test_start = time.time()
            
            # Start service startup simulation with production timing
            startup_task = asyncio.create_task(
                self._simulate_service_startup_progression("production")
            )
            
            # Test WebSocket validation with production-conservative timeouts
            validation_start = time.time()
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=8.0)
            validation_duration = time.time() - validation_start
            
            # Wait for startup simulation to complete
            await startup_task
            total_duration = time.time() - test_start
            
            # Validate reliable startup performance
            self.assertTrue(
                result.ready,
                f"Production environment should achieve reliable readiness. Failed services: {result.failed_services}"
            )
            
            # Production should complete within conservative timeout (< 8s)
            self.assertLess(
                validation_duration,
                8.0,
                f"Production validation should complete within conservative timeout: took {validation_duration:.3f}s"
            )
            
            # Should prioritize reliability over speed
            self.assertGreaterEqual(
                validation_duration,
                1.0,  # Should not be as aggressive as development/staging
                f"Production should prioritize reliability over speed: took {validation_duration:.3f}s"
            )
            
            self.record_metric("production_validation_duration", validation_duration)
            self.record_metric("production_total_duration", total_duration)
            self.record_metric("production_reliable_startup", "success")
    
    @pytest.mark.asyncio
    async def test_gcp_websocket_validator_environment_adaptation(self):
        """
        Test GCP WebSocket validator adapts to detected environment.
        
        CRITICAL: This test validates that the validator correctly adapts its
        behavior based on the detected environment and uses appropriate configurations.
        
        Should initially fail if environment adaptation not working correctly.
        """
        environments_to_test = [
            ("development", False, 0.3, 1.0, 3.0),  # env, is_gcp, multiplier, safety, max
            ("staging", True, 0.7, 1.1, 5.0),
            ("production", True, 1.0, 1.2, 8.0)
        ]
        
        for env_name, is_gcp, expected_multiplier, expected_safety, expected_max in environments_to_test:
            # Set up environment (with K_SERVICE if GCP)
            env_vars = {"ENVIRONMENT": env_name}
            if is_gcp:
                env_vars["K_SERVICE"] = f"netra-backend-{env_name}"
                
            with self.temp_env_vars(**env_vars):
                validator = create_gcp_websocket_validator(self.mock_app_state)
                
                # Verify environment detection
                self.assertEqual(validator.environment, env_name)
                self.assertEqual(validator.is_gcp_environment, is_gcp)
                
                # Verify timeout configuration adaptation
                self.assertAlmostEqual(
                    validator.timeout_multiplier,
                    expected_multiplier,
                    delta=0.01,
                    msg=f"Environment {env_name} timeout multiplier incorrect"
                )
                
                self.assertAlmostEqual(
                    validator.safety_margin,
                    expected_safety,
                    delta=0.01,
                    msg=f"Environment {env_name} safety margin incorrect"
                )
                
                self.assertEqual(
                    validator.max_total_timeout,
                    expected_max,
                    msg=f"Environment {env_name} max timeout incorrect"
                )
                
                # Test service readiness checks use appropriate timeouts
                service_checks = validator.readiness_checks
                
                # Database timeout should reflect environment
                database_check = service_checks["database"]
                expected_db_timeout = 3.0 if is_gcp else 5.0
                self.assertEqual(
                    database_check.timeout_seconds,
                    expected_db_timeout,
                    f"Environment {env_name} database timeout should be {expected_db_timeout}s"
                )
                
                # Redis timeout should reflect environment
                redis_check = service_checks["redis"]
                expected_redis_timeout = 1.5 if is_gcp else 3.0
                self.assertEqual(
                    redis_check.timeout_seconds,
                    expected_redis_timeout,
                    f"Environment {env_name} Redis timeout should be {expected_redis_timeout}s"
                )
                
                self.record_metric(f"{env_name}_environment_adaptation", "success")
    
    @pytest.mark.asyncio
    async def test_race_condition_prevention_across_environments(self):
        """
        Test race condition prevention works in all environments.
        
        CRITICAL: This test validates that minimum safety timeouts are maintained
        even with optimization, ensuring WebSocket race conditions are prevented
        across all deployment environments.
        
        Should initially fail if race condition prevention compromised by optimization.
        """
        environments = ["development", "staging", "production"]
        
        for env_name in environments:
            # Set up environment with Cloud Run (to test safety minimums)
            with self.temp_env_vars(ENVIRONMENT=env_name, K_SERVICE=f"test-{env_name}"):
                validator = create_gcp_websocket_validator(self.mock_app_state)
                
                # Verify Cloud Run detection
                self.assertTrue(validator.is_cloud_run, f"Should detect Cloud Run for {env_name}")
                
                # Test race condition scenario: validation runs before services phase
                self.mock_app_state.startup_phase = "dependencies"  # Early phase
                self.mock_app_state.startup_complete = False
                
                # Make services unavailable (race condition scenario)
                self.mock_app_state.database_available = False
                self.mock_app_state.redis_manager.is_connected = False
                self.mock_app_state.agent_supervisor = None
                self.mock_app_state.agent_websocket_bridge = None
                
                # Test validation detects race condition
                race_condition_start = time.time()
                result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=2.0)
                race_condition_duration = time.time() - race_condition_start
                
                # Should detect race condition appropriately
                self.assertFalse(
                    result.ready,
                    f"Should detect race condition in {env_name} environment"
                )
                
                # Should still respect minimum safety timeout for Cloud Run
                self.assertGreaterEqual(
                    race_condition_duration,
                    0.4,  # Close to 0.5s minimum but allowing some tolerance
                    f"Should maintain minimum safety timeout in {env_name} even during race condition"
                )
                
                # Verify race condition detected in failure details
                self.assertIn(
                    "startup_phase_timeout",
                    result.failed_services,
                    f"Should detect startup phase timeout in {env_name}"
                )
                
                self.record_metric(f"{env_name}_race_condition_prevention", "success")
                self.record_metric(f"{env_name}_race_condition_duration", race_condition_duration)
    
    @pytest.mark.asyncio
    async def test_service_failure_recovery_timing(self):
        """
        Test service failure recovery with environment-aware timing.
        
        CRITICAL: This test validates that service failures are handled gracefully
        with appropriate retry timing based on environment optimization.
        
        Should initially fail if recovery timing not properly environment-aware.
        """
        # Test staging environment recovery
        with self.temp_env_vars(ENVIRONMENT="staging", K_SERVICE="staging-service"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Simulate Redis connection failure and recovery
            self.mock_app_state.startup_phase = "services"  # Services phase
            self.mock_app_state.database_available = True
            self.mock_app_state.redis_manager.is_connected = False  # Redis fails initially
            self.mock_app_state.agent_supervisor = MagicMock()
            self.mock_app_state.agent_websocket_bridge = MagicMock()
            
            # Start validation
            recovery_start = time.time()
            
            # Simulate Redis recovery after short delay
            async def simulate_redis_recovery():
                await asyncio.sleep(0.8)  # Redis recovers after delay
                self.mock_app_state.redis_manager.is_connected = True
            
            recovery_task = asyncio.create_task(simulate_redis_recovery())
            
            # Test validation with recovery
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
            recovery_duration = time.time() - recovery_start
            
            await recovery_task
            
            # In staging, Redis failures should allow graceful degradation
            # (based on the graceful degradation logic in the validator)
            # Result may be ready due to staging's graceful degradation for Redis
            if not result.ready:
                # If not ready, should have appropriate warnings about Redis
                self.assertIn(
                    "redis",
                    [s for s in result.failed_services] + [w for w in result.warnings if "redis" in w.lower()],
                    "Should detect Redis issue in staging"
                )
            
            # Recovery should complete within staging timeout optimization
            self.assertLess(
                recovery_duration,
                3.0,
                f"Staging recovery should complete within optimized timeout: took {recovery_duration:.3f}s"
            )
            
            self.record_metric("staging_service_recovery_duration", recovery_duration)
            self.record_metric("staging_service_recovery", "success")
    
    def teardown_method(self, method):
        """Clean up test environment and record service startup metrics."""
        # Record test completion and service coordination metrics
        execution_time = self.get_metrics().execution_time
        self.record_metric("test_execution_time", execution_time)
        
        # Analyze service startup performance across environments
        metrics = self.get_all_metrics()
        duration_metrics = {k: v for k, v in metrics.items() if "duration" in k}
        
        if duration_metrics:
            avg_duration = sum(duration_metrics.values()) / len(duration_metrics)
            self.record_metric("average_service_startup_duration", avg_duration)
            
            # Log if service startup is slow
            if avg_duration > 5.0:
                print(f"PERFORMANCE WARNING: Average service startup duration: {avg_duration:.3f}s")
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Allow running individual test file for debugging
    pytest.main([__file__, "-v", "--tb=short"])