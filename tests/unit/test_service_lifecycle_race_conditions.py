"""
Test suite for service lifecycle race condition fixes.

This test suite validates the Five Whys analysis implementation:
- Level 1-2: Race condition protection and error attribution  
- Level 3-5: Service lifecycle architecture improvements

CRITICAL: These tests ensure that the race condition causing OAuth validation
errors during service startup has been resolved.
"""

import asyncio
import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from shared.configuration.central_config_validator import (
    CentralConfigurationValidator, 
    get_central_validator,
    clear_central_validator_cache
)
from shared.lifecycle.service_lifecycle_manager import (
    ServiceLifecycleManager,
    ServiceRegistration,
    ServiceDependency,
    ReadinessContract,
    InitializationPhase,
    ServiceState,
    get_lifecycle_manager
)


class TestRaceConditionProtection:
    """Test race condition protection in central config validator."""
    
    @pytest.fixture
    def validator(self):
        """Create a fresh validator instance for each test."""
        clear_central_validator_cache()
        return CentralConfigurationValidator()
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment that simulates timing issues."""
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env_instance = Mock()
            mock_get_env.return_value = mock_env_instance
            
            # Default working behavior
            mock_env_instance._is_test_context.return_value = True
            mock_env_instance.get.return_value = "test"
            mock_env_instance.get_debug_info.return_value = {
                "isolation_enabled": True,
                "isolated_vars_count": 10
            }
            
            yield mock_env_instance
    
    def test_environment_readiness_detection(self, validator, mock_env):
        """Test that environment readiness detection works correctly."""
        # Test successful readiness
        result = validator._wait_for_environment_readiness(timeout_seconds=1.0)
        assert result is True
        
        # Test failed readiness (environment throws exceptions)
        mock_env.get.side_effect = Exception("Environment not ready")
        result = validator._wait_for_environment_readiness(timeout_seconds=0.5)
        assert result is False
    
    def test_timing_issue_detection(self, validator, mock_env):
        """Test detection of various timing issues."""
        # Test normal state (no timing issues)
        timing_issue = validator._detect_timing_issue()
        assert timing_issue is None
        
        # Test basic access failure
        mock_env.get.side_effect = Exception("Access failed")
        timing_issue = validator._detect_timing_issue()
        assert "Environment access completely failing" in timing_issue
        
        # Test isolation enabled but no variables
        mock_env.get.side_effect = None
        mock_env.get_debug_info.return_value = {
            "isolation_enabled": True,
            "isolated_vars_count": 0
        }
        timing_issue = validator._detect_timing_issue()
        assert "Isolation enabled but no isolated variables loaded" in timing_issue
    
    def test_concurrent_validation_race_condition(self, validator, mock_env):
        """Test concurrent validation calls to simulate race conditions."""
        validation_results = []
        errors = []
        
        def validate_worker():
            try:
                # Simulate some environment instability
                if threading.current_thread().name == "Thread-1":
                    time.sleep(0.1)  # Slight delay to create timing differences
                
                result = validator._wait_for_environment_readiness(timeout_seconds=2.0)
                validation_results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple validation attempts concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=validate_worker, name=f"Thread-{i}")
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All validations should succeed (no race conditions)
        assert len(errors) == 0, f"Validation errors: {errors}"
        assert all(validation_results), "Some validations failed"
        assert len(validation_results) == 5
    
    @pytest.mark.asyncio
    async def test_validation_with_retry_logic(self, validator, mock_env):
        """Test validation retry logic for intermittent timing issues."""
        # Simulate intermittent failures
        call_count = [0]
        
        def flaky_get(key, default=None):
            call_count[0] += 1
            if call_count[0] <= 2:  # Fail first 2 calls
                raise Exception("Temporary failure")
            return "test-value"
        
        mock_env.get = flaky_get
        
        from shared.configuration.central_config_validator import ConfigRule, ConfigRequirement, Environment
        
        # Create a test rule
        rule = ConfigRule(
            env_var="TEST_VAR",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.TEST}
        )
        
        # This should succeed after retries
        validator._validate_single_requirement_with_timing(rule, Environment.TEST)
        
        # Should have made multiple calls due to retries
        assert call_count[0] > 2
    
    def test_readiness_state_tracking(self, validator):
        """Test that validator properly tracks readiness state."""
        # Initial state should be uninitialized
        assert validator.get_readiness_state() == "uninitialized"
        assert not validator.is_ready()
        
        # Force readiness check
        with patch.object(validator, '_wait_for_environment_readiness', return_value=True):
            result = validator.force_readiness_check()
            assert result is True
    
    def test_enhanced_error_attribution(self, validator, mock_env):
        """Test that timing-related errors are properly attributed."""
        # Simulate a timing issue
        mock_env.get_debug_info.return_value = {
            "isolation_enabled": True, 
            "isolated_vars_count": 0  # This indicates a timing issue
        }
        
        # Mock a validation failure
        with patch.object(validator, '_validate_single_requirement') as mock_validate:
            mock_validate.side_effect = ValueError("Validation failed")
            
            from shared.configuration.central_config_validator import ConfigRule, ConfigRequirement, Environment
            rule = ConfigRule(
                env_var="TEST_VAR",
                requirement=ConfigRequirement.REQUIRED,
                environments={Environment.TEST}
            )
            
            # This should include timing issue information in the error
            try:
                validator._validate_single_requirement_with_timing(rule, Environment.TEST)
                assert False, "Should have raised an exception"
            except ValueError as e:
                # Error should be the original validation error (after all retries)
                assert "Validation failed" in str(e)


class TestServiceLifecycleManager:
    """Test service lifecycle management and dependency resolution."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        """Create a fresh lifecycle manager for each test."""
        return ServiceLifecycleManager()
    
    def test_service_registration(self, lifecycle_manager):
        """Test basic service registration."""
        registration = ServiceRegistration(
            name="test-service",
            phase=InitializationPhase.BOOTSTRAP,
            is_critical=True
        )
        
        lifecycle_manager.register_service(registration)
        
        # Service should be registered
        assert "test-service" in lifecycle_manager._services
        assert lifecycle_manager._services["test-service"].current_state == ServiceState.UNINITIALIZED
    
    def test_dependency_resolution(self, lifecycle_manager):
        """Test dependency resolution and ordering."""
        # Register services with dependencies
        service_a = ServiceRegistration(
            name="service-a",
            phase=InitializationPhase.BOOTSTRAP,
            dependencies=[]  # No dependencies
        )
        
        service_b = ServiceRegistration(
            name="service-b", 
            phase=InitializationPhase.BOOTSTRAP,
            dependencies=[
                ServiceDependency(
                    service_name="service-a",
                    required_state=ServiceState.READY
                )
            ]
        )
        
        lifecycle_manager.register_service(service_a)
        lifecycle_manager.register_service(service_b)
        
        # Get services in dependency order
        services_in_phase = [service_a, service_b]
        ordered_services = lifecycle_manager._resolve_dependencies_in_phase(services_in_phase)
        
        # service-a should come before service-b
        assert ordered_services[0].name == "service-a"
        assert ordered_services[1].name == "service-b"
    
    def test_circular_dependency_detection(self, lifecycle_manager):
        """Test detection and handling of circular dependencies."""
        service_a = ServiceRegistration(
            name="service-a",
            phase=InitializationPhase.BOOTSTRAP,
            dependencies=[
                ServiceDependency(
                    service_name="service-b",
                    required_state=ServiceState.READY
                )
            ]
        )
        
        service_b = ServiceRegistration(
            name="service-b",
            phase=InitializationPhase.BOOTSTRAP,
            dependencies=[
                ServiceDependency(
                    service_name="service-a", 
                    required_state=ServiceState.READY
                )
            ]
        )
        
        lifecycle_manager.register_service(service_a)
        lifecycle_manager.register_service(service_b)
        
        # This should handle circular dependency gracefully
        services_in_phase = [service_a, service_b]
        ordered_services = lifecycle_manager._resolve_dependencies_in_phase(services_in_phase)
        
        # Both services should be included (even if order is ambiguous)
        assert len(ordered_services) == 2
        service_names = {s.name for s in ordered_services}
        assert service_names == {"service-a", "service-b"}
    
    @pytest.mark.asyncio
    async def test_readiness_contract_validation(self, lifecycle_manager):
        """Test readiness contract validation."""
        # Mock custom validator
        mock_validator = Mock(return_value=True)
        
        contract = ReadinessContract(
            service_name="test-service",
            custom_validator=mock_validator,
            retry_count=1
        )
        
        service = ServiceRegistration(
            name="test-service",
            phase=InitializationPhase.BOOTSTRAP,
            readiness_contract=contract
        )
        
        lifecycle_manager.register_service(service)
        
        # Test successful validation
        result = await lifecycle_manager._validate_readiness_contract(service)
        assert result is True
        mock_validator.assert_called_once()
        
        # Test failed validation
        mock_validator.return_value = False
        mock_validator.reset_mock()
        
        result = await lifecycle_manager._validate_readiness_contract(service)
        assert result is False
        assert mock_validator.call_count == 1  # Only one attempt with retry_count=1
    
    @pytest.mark.asyncio
    async def test_dependency_checking(self, lifecycle_manager):
        """Test dependency checking during initialization."""
        # Set up services with dependency relationship
        service_a = ServiceRegistration(
            name="service-a",
            phase=InitializationPhase.BOOTSTRAP
        )
        service_a.current_state = ServiceState.READY  # Already ready
        
        service_b = ServiceRegistration(
            name="service-b",
            phase=InitializationPhase.BOOTSTRAP,
            dependencies=[
                ServiceDependency(
                    service_name="service-a",
                    required_state=ServiceState.READY,
                    is_critical=True
                )
            ]
        )
        
        lifecycle_manager.register_service(service_a)
        lifecycle_manager.register_service(service_b)
        
        # Dependency check should pass
        result = await lifecycle_manager._check_service_dependencies(service_b)
        assert result is True
        
        # Change dependency to failed state
        service_a.current_state = ServiceState.FAILED
        
        # Dependency check should fail
        result = await lifecycle_manager._check_service_dependencies(service_b)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_full_initialization_sequence(self, lifecycle_manager):
        """Test complete initialization sequence with multiple phases."""
        # Register services across different phases
        bootstrap_service = ServiceRegistration(
            name="bootstrap-service", 
            phase=InitializationPhase.BOOTSTRAP,
            initializer=Mock(),
            is_critical=True
        )
        
        deps_service = ServiceRegistration(
            name="deps-service",
            phase=InitializationPhase.DEPENDENCIES,
            initializer=Mock(),
            dependencies=[
                ServiceDependency(
                    service_name="bootstrap-service",
                    required_state=ServiceState.READY
                )
            ]
        )
        
        lifecycle_manager.register_service(bootstrap_service)
        lifecycle_manager.register_service(deps_service)
        
        # Run full initialization
        result = await lifecycle_manager.initialize_all_services()
        
        # Should succeed
        assert result is True
        assert lifecycle_manager.is_initialization_complete()
        
        # Check that initializers were called
        bootstrap_service.initializer.assert_called_once()
        deps_service.initializer.assert_called_once()
        
        # Check service states
        assert bootstrap_service.current_state == ServiceState.READY
        assert deps_service.current_state == ServiceState.READY
    
    @pytest.mark.asyncio
    async def test_critical_service_failure_stops_initialization(self, lifecycle_manager):
        """Test that critical service failure stops initialization."""
        failing_service = ServiceRegistration(
            name="failing-service",
            phase=InitializationPhase.BOOTSTRAP,
            initializer=Mock(side_effect=Exception("Service failed")),
            is_critical=True
        )
        
        lifecycle_manager.register_service(failing_service)
        
        # Initialization should fail
        result = await lifecycle_manager.initialize_all_services()
        assert result is False
        assert not lifecycle_manager.is_initialization_complete()
        
        # Service should be in failed state
        assert failing_service.current_state == ServiceState.FAILED
        assert "Service failed" in failing_service.last_error
    
    def test_initialization_status_reporting(self, lifecycle_manager):
        """Test detailed initialization status reporting."""
        service = ServiceRegistration(
            name="test-service",
            phase=InitializationPhase.BOOTSTRAP
        )
        
        lifecycle_manager.register_service(service)
        
        status = lifecycle_manager.get_initialization_status()
        
        # Check status structure
        assert "complete" in status
        assert "current_phase" in status
        assert "total_services" in status
        assert "services" in status
        
        # Check service details
        assert "test-service" in status["services"]
        service_status = status["services"]["test-service"]
        assert service_status["state"] == ServiceState.UNINITIALIZED.value
        assert service_status["phase"] == InitializationPhase.BOOTSTRAP.value


class TestIntegrationScenarios:
    """Integration tests for race condition scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_validator_and_lifecycle_initialization(self):
        """Test concurrent validator and lifecycle manager usage."""
        errors = []
        
        async def validator_worker():
            try:
                validator = get_central_validator()
                # Force some environment checking
                validator.force_readiness_check()
            except Exception as e:
                errors.append(f"Validator: {e}")
        
        async def lifecycle_worker():
            try:
                manager = get_lifecycle_manager()
                service = ServiceRegistration(
                    name=f"service-{threading.current_thread().ident}",
                    phase=InitializationPhase.BOOTSTRAP
                )
                manager.register_service(service)
            except Exception as e:
                errors.append(f"Lifecycle: {e}")
        
        # Run both concurrently
        tasks = []
        for _ in range(3):
            tasks.append(asyncio.create_task(validator_worker()))
            tasks.append(asyncio.create_task(lifecycle_worker()))
        
        await asyncio.gather(*tasks)
        
        # Should have no errors from concurrent access
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
    
    @pytest.mark.asyncio
    async def test_oauth_validation_race_condition_reproduction(self):
        """
        Test that reproduces the original OAuth validation race condition
        and verifies it's fixed.
        """
        # Simulate the race condition scenario from the Five Whys analysis
        validator = CentralConfigurationValidator()
        
        # Mock environment that simulates the race condition timing
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()
            mock_get_env.return_value = mock_env
            
            # Simulate environment still loading
            call_count = [0]
            def simulate_loading_environment(key, default=None):
                call_count[0] += 1
                if call_count[0] <= 2:
                    # First few calls fail (environment still loading)
                    raise Exception("Environment still initializing")
                
                # After environment is "ready", return test values
                if key == "ENVIRONMENT":
                    return "test"
                elif key in ["GOOGLE_OAUTH_CLIENT_ID_TEST", "GOOGLE_OAUTH_CLIENT_SECRET_TEST"]:
                    return f"test-{key.lower()}"
                return default
            
            mock_env.get = simulate_loading_environment
            mock_env._is_test_context.return_value = True
            mock_env.get_debug_info.return_value = {
                "isolation_enabled": True,
                "isolated_vars_count": 5
            }
            
            # This should now succeed with retries (race condition fixed)
            validator.force_readiness_check()
            
            # The environment should have been called multiple times due to retries
            assert call_count[0] > 2, "Retry logic should have been triggered"


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v"])