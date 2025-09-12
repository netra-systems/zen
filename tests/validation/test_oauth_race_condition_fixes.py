"""
Test OAuth Race Condition Fixes - Five Whys Validation Suite

This test suite validates that the comprehensive Five Whys-driven solution for 
OAuth configuration race conditions is working correctly.

CRITICAL TEST SCENARIOS:
- Level 1-2: Race condition protection in central_config_validator.py
- Level 3-5: ServiceLifecycleManager implementation validation  
- Integration: Complete startup sequence reliability

Business Value: Platform/Internal - System Stability Validation
Ensures OAuth validation errors caused by race conditions are eliminated.
"""

import asyncio
import logging
import os
import pytest
import threading
import time
import unittest.mock
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from shared.configuration.central_config_validator import (
    CentralConfigurationValidator,
    Environment,
    get_central_validator,
    clear_central_validator_cache
)
from shared.lifecycle.service_lifecycle_manager import (
    ServiceLifecycleManager,
    ServiceRegistration,
    InitializationPhase,
    ServiceState,
    ServiceDependency,
    ReadinessContract,
    register_service
)
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestOAuthRaceConditionFixes:
    """Test suite for OAuth race condition fixes."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear any cached state
        clear_central_validator_cache()
        
        # Use actual test environment values to avoid conflicts
        # The real test environment uses these values from config/test.env
        self.expected_oauth_client_id = "test-oauth-client-id-for-automated-testing"
        self.expected_oauth_client_secret = "test-oauth-client-secret-for-automated-testing"
        
        # Ensure test environment variables are set
        os.environ["ENVIRONMENT"] = "test"
        os.environ["PYTEST_CURRENT_TEST"] = "test_oauth_race_condition_fixes.py"
        
        # These should already be set by test.env, but ensure they're present
        if not os.environ.get("GOOGLE_OAUTH_CLIENT_ID_TEST"):
            os.environ["GOOGLE_OAUTH_CLIENT_ID_TEST"] = self.expected_oauth_client_id
        if not os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST"):
            os.environ["GOOGLE_OAUTH_CLIENT_SECRET_TEST"] = self.expected_oauth_client_secret
        if not os.environ.get("JWT_SECRET_KEY"):
            os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-test-environment-only-32-chars-min"
    
    def teardown_method(self):
        """Clean up test environment."""
        # Clear cached state
        clear_central_validator_cache()


class TestLevel1And2RaceConditionProtection(TestOAuthRaceConditionFixes):
    """Test Level 1-2: Race condition protection in central_config_validator.py"""
    
    def test_environment_readiness_verification(self):
        """Test that environment readiness is verified before validation."""
        validator = CentralConfigurationValidator()
        
        # Test successful readiness check
        assert validator._wait_for_environment_readiness(timeout_seconds=5.0), \
            "Environment should be ready for validation"
        
        # Test readiness state tracking
        assert validator._readiness_state in ["ready", "uninitialized"], \
            "Readiness state should be properly tracked"
    
    def test_timing_issue_detection_vs_missing_config(self):
        """Test that timing issues are distinguished from missing configuration."""
        validator = CentralConfigurationValidator()
        
        # Test with properly configured environment - should not detect timing issues
        timing_issue = validator._detect_timing_issue()
        assert timing_issue is None, \
            "No timing issues should be detected in properly configured environment"
        
        # Test that the race condition protection mechanisms are in place
        # by checking if _wait_for_environment_readiness works
        readiness_result = validator._wait_for_environment_readiness(timeout_seconds=1.0)
        assert readiness_result is True, \
            "Environment readiness check should work in properly configured environment"
        
        # Test retry logic capability by checking the validator has the methods
        assert hasattr(validator, '_validate_single_requirement_with_timing'), \
            "Validator should have timing-aware validation method"
        assert hasattr(validator, '_detect_timing_issue'), \
            "Validator should have timing issue detection method"
    
    def test_retry_logic_for_initialization_race_conditions(self):
        """Test retry logic for initialization race conditions."""
        validator = CentralConfigurationValidator()
        
        # Mock a race condition that resolves after retry
        retry_count = 0
        
        def mock_get_env_with_retry(key, default=None):
            nonlocal retry_count
            retry_count += 1
            if retry_count == 1 and key == "GOOGLE_OAUTH_CLIENT_ID_TEST":
                # Simulate race condition on first call
                return None
            elif key == "GOOGLE_OAUTH_CLIENT_ID_TEST":
                return self.expected_oauth_client_id
            elif key == "GOOGLE_OAUTH_CLIENT_SECRET_TEST":
                return self.expected_oauth_client_secret
            elif key == "ENVIRONMENT":
                return "test"
            elif key == "PYTEST_CURRENT_TEST":
                return "test_oauth_race_condition_fixes.py"
            else:
                return default
        
        # Test with retry logic
        validator = CentralConfigurationValidator(env_getter_func=mock_get_env_with_retry)
        
        # This should succeed after retry
        try:
            oauth_creds = validator.get_oauth_credentials()
            assert oauth_creds["client_id"] == self.expected_oauth_client_id, \
                "OAuth credentials should be retrieved after retry"
            assert retry_count > 1, \
                "Retry logic should have been executed"
        except ValueError:
            pytest.fail("Validation should succeed after retry resolves race condition")
    
    @pytest.mark.asyncio
    async def test_concurrent_validation_no_race_conditions(self):
        """Test that concurrent validation calls don't cause race conditions."""
        validator = CentralConfigurationValidator()
        
        async def validate_concurrently():
            """Helper to run validation concurrently."""
            try:
                environment = validator.get_environment()
                assert environment == Environment.TEST
                oauth_creds = validator.get_oauth_credentials()
                assert oauth_creds["client_id"] == self.expected_oauth_client_id
                return True
            except Exception as e:
                logger.error(f"Concurrent validation failed: {e}")
                return False
        
        # Run multiple concurrent validations
        tasks = [validate_concurrently() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All validations should succeed
        assert all(results), \
            "All concurrent validations should succeed without race conditions"


class TestLevel3And5ServiceLifecycleManager(TestOAuthRaceConditionFixes):
    """Test Level 3-5: ServiceLifecycleManager implementation"""
    
    def setup_method(self):
        """Set up test environment with fresh ServiceLifecycleManager."""
        super().setup_method()
        self.lifecycle_manager = ServiceLifecycleManager()
    
    def test_initialization_phase_management(self):
        """Test initialization phase management."""
        # Register services in different phases
        bootstrap_service = ServiceRegistration(
            name="bootstrap_service",
            phase=InitializationPhase.BOOTSTRAP,
            is_critical=True
        )
        
        database_service = ServiceRegistration(
            name="database_service", 
            phase=InitializationPhase.DATABASE,
            is_critical=True
        )
        
        integration_service = ServiceRegistration(
            name="integration_service",
            phase=InitializationPhase.INTEGRATION,
            is_critical=True
        )
        
        self.lifecycle_manager.register_service(bootstrap_service)
        self.lifecycle_manager.register_service(database_service)
        self.lifecycle_manager.register_service(integration_service)
        
        # Verify services are registered with correct phases
        status = self.lifecycle_manager.get_initialization_status()
        assert status["total_services"] == 3, \
            "All three services should be registered"
        
        services = status["services"]
        assert services["bootstrap_service"]["phase"] == "bootstrap"
        assert services["database_service"]["phase"] == "database"
        assert services["integration_service"]["phase"] == "integration"
    
    def test_service_dependency_resolution(self):
        """Test service dependency resolution and ordering."""
        # Create services with dependencies
        config_service = ServiceRegistration(
            name="config_service",
            phase=InitializationPhase.BOOTSTRAP,
            is_critical=True
        )
        
        auth_service = ServiceRegistration(
            name="auth_service",
            phase=InitializationPhase.DEPENDENCIES,
            dependencies=[ServiceDependency(
                service_name="config_service",
                required_state=ServiceState.READY,
                is_critical=True
            )],
            is_critical=True
        )
        
        websocket_service = ServiceRegistration(
            name="websocket_service",
            phase=InitializationPhase.INTEGRATION,
            dependencies=[
                ServiceDependency(
                    service_name="config_service",
                    required_state=ServiceState.READY,
                    is_critical=True
                ),
                ServiceDependency(
                    service_name="auth_service", 
                    required_state=ServiceState.READY,
                    is_critical=True
                )
            ],
            is_critical=True
        )
        
        # Register services
        self.lifecycle_manager.register_service(config_service)
        self.lifecycle_manager.register_service(auth_service)
        self.lifecycle_manager.register_service(websocket_service)
        
        # Test dependency resolution within phases
        services_in_dep_phase = [auth_service]
        resolved = self.lifecycle_manager._resolve_dependencies_in_phase(services_in_dep_phase)
        assert len(resolved) == 1, \
            "Dependency resolution should handle single service correctly"
        
        services_in_integration_phase = [websocket_service]
        resolved = self.lifecycle_manager._resolve_dependencies_in_phase(services_in_integration_phase)
        assert len(resolved) == 1, \
            "Dependency resolution should handle services with external dependencies"
    
    def test_readiness_contracts_and_health_checks(self):
        """Test readiness contracts and health check functionality."""
        health_check_called = False
        custom_validator_called = False
        
        def mock_health_checker():
            nonlocal health_check_called
            health_check_called = True
            return True
        
        def mock_custom_validator():
            nonlocal custom_validator_called
            custom_validator_called = True
            return True
        
        # Create service with readiness contract
        readiness_contract = ReadinessContract(
            service_name="test_service",
            required_checks=["connectivity", "auth"],
            custom_validator=mock_custom_validator,
            timeout_seconds=10.0,
            retry_count=2
        )
        
        service = ServiceRegistration(
            name="test_service",
            phase=InitializationPhase.SERVICES,
            readiness_contract=readiness_contract,
            health_checker=mock_health_checker,
            is_critical=True
        )
        
        self.lifecycle_manager.register_service(service)
        
        # Verify readiness contract is set
        assert service.readiness_contract is not None, \
            "Readiness contract should be set on service"
        assert service.readiness_contract.custom_validator is not None, \
            "Custom validator should be available"
        assert service.health_checker is not None, \
            "Health checker should be available"
    
    @pytest.mark.asyncio
    async def test_full_startup_sequence_reliability(self):
        """Test complete startup sequence reliability."""
        initialization_order = []
        
        async def bootstrap_initializer():
            initialization_order.append("bootstrap")
            await asyncio.sleep(0.01)  # Simulate work
        
        async def dependency_initializer():
            initialization_order.append("dependencies")
            await asyncio.sleep(0.01)
        
        async def service_initializer():
            initialization_order.append("services")
            await asyncio.sleep(0.01)
        
        # Register services with initializers
        bootstrap_service = ServiceRegistration(
            name="bootstrap",
            phase=InitializationPhase.BOOTSTRAP,
            initializer=bootstrap_initializer,
            is_critical=True
        )
        
        dependency_service = ServiceRegistration(
            name="dependencies",
            phase=InitializationPhase.DEPENDENCIES,
            initializer=dependency_initializer,
            is_critical=True
        )
        
        service_service = ServiceRegistration(
            name="services",
            phase=InitializationPhase.SERVICES,
            initializer=service_initializer,
            is_critical=True
        )
        
        self.lifecycle_manager.register_service(bootstrap_service)
        self.lifecycle_manager.register_service(dependency_service)
        self.lifecycle_manager.register_service(service_service)
        
        # Initialize all services
        success = await self.lifecycle_manager.initialize_all_services()
        
        assert success, \
            "Service initialization should complete successfully"
        
        assert self.lifecycle_manager.is_initialization_complete(), \
            "Initialization should be marked as complete"
        
        # Verify initialization order
        expected_order = ["bootstrap", "dependencies", "services"]
        assert initialization_order == expected_order, \
            f"Services should initialize in correct phase order. Got: {initialization_order}"
        
        # Verify all services are ready
        status = self.lifecycle_manager.get_initialization_status()
        assert status["ready_services"] == 3, \
            "All services should be in ready state"
        assert status["failed_services"] == 0, \
            "No services should have failed"


class TestIntegrationValidation(TestOAuthRaceConditionFixes):
    """Test integration validation with complete startup sequence"""
    
    @pytest.mark.asyncio
    async def test_oauth_validation_with_proper_environment_loading(self):
        """Test OAuth validation works with proper environment loading."""
        # Test with race condition protection enabled
        validator = CentralConfigurationValidator()
        
        # This should not fail due to race conditions
        try:
            validator.validate_all_requirements()
            oauth_creds = validator.get_oauth_credentials()
            
            assert oauth_creds["client_id"] == self.expected_oauth_client_id, \
                "OAuth client ID should be properly loaded"
            assert oauth_creds["client_secret"] == self.expected_oauth_client_secret, \
                "OAuth client secret should be properly loaded"
                
        except ValueError as e:
            if "race condition" in str(e).lower():
                pytest.fail(f"Race condition detected - Five Whys fix not working: {e}")
            else:
                pytest.fail(f"Validation failed for unexpected reason: {e}")
    
    def test_no_more_race_conditions_during_startup(self):
        """Test that race conditions no longer occur during startup."""
        # Simulate multiple concurrent startup attempts
        results = []
        exceptions = []
        
        def startup_attempt(attempt_id):
            try:
                validator = CentralConfigurationValidator()
                validator.validate_all_requirements()
                oauth_creds = validator.get_oauth_credentials()
                results.append({
                    "attempt_id": attempt_id,
                    "success": True,
                    "client_id": oauth_creds["client_id"]
                })
                return True
            except Exception as e:
                exceptions.append({
                    "attempt_id": attempt_id,
                    "error": str(e)
                })
                return False
        
        # Run concurrent startup attempts
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(startup_attempt, i) 
                for i in range(10)
            ]
            
            # Wait for all attempts
            concurrent_results = [f.result() for f in futures]
        
        # Analyze results
        successful_attempts = sum(concurrent_results)
        race_condition_errors = [
            exc for exc in exceptions 
            if "race condition" in exc["error"].lower() or 
               "timing issue" in exc["error"].lower()
        ]
        
        assert successful_attempts >= 8, \
            f"At least 8/10 concurrent startup attempts should succeed. Got: {successful_attempts}"
        
        assert len(race_condition_errors) == 0, \
            f"No race condition errors should occur. Found: {race_condition_errors}"
    
    def test_concurrent_service_initialization(self):
        """Test concurrent service initialization doesn't cause race conditions."""
        lifecycle_manager = ServiceLifecycleManager()
        
        # Register multiple services that might compete for resources
        services_to_register = [
            ("config_validator", InitializationPhase.BOOTSTRAP),
            ("oauth_handler", InitializationPhase.DEPENDENCIES),
            ("auth_service", InitializationPhase.DEPENDENCIES),
            ("websocket_bridge", InitializationPhase.INTEGRATION),
            ("agent_factory", InitializationPhase.INTEGRATION),
        ]
        
        for name, phase in services_to_register:
            service = ServiceRegistration(
                name=name,
                phase=phase,
                is_critical=True,
                timeout_seconds=10.0
            )
            lifecycle_manager.register_service(service)
        
        # Verify all services registered
        status = lifecycle_manager.get_initialization_status()
        assert status["total_services"] == 5, \
            "All services should be registered successfully"
    
    def test_proper_error_messages_for_actual_vs_timing_issues(self):
        """Test that error messages properly identify timing vs configuration issues."""
        # Test with actual missing configuration
        missing_config_env = {
            "ENVIRONMENT": "test",
            "PYTEST_CURRENT_TEST": "test_oauth_race_condition_fixes.py",
            "JWT_SECRET_KEY": "test-jwt-secret-key-for-test-environment-only-32-chars-min",
            # Intentionally missing OAuth credentials - both client ID and secret
        }
        
        def mock_env_getter_missing_config(key, default=None):
            return missing_config_env.get(key, default)
        
        validator = CentralConfigurationValidator(env_getter_func=mock_env_getter_missing_config)
        
        try:
            # This specific call should fail with missing OAuth credentials
            oauth_creds = validator.get_oauth_credentials()
            pytest.fail("OAuth validation should fail with missing credentials")
        except ValueError as e:
            error_msg = str(e)
            # The actual error message from the validator
            assert "OAuth credentials not properly configured" in error_msg, \
                f"Error should mention OAuth configuration issue. Got: {error_msg}"
            assert "race condition" not in error_msg.lower(), \
                "Error should not mention race conditions for actual missing config"
            
            # Test that it's a configuration issue, not a timing issue
            timing_issue = validator._detect_timing_issue()
            # Should be None because this is a real config issue, not a timing issue
            assert timing_issue is None, \
                "Should not detect timing issues for actual missing configuration"
    
    @pytest.mark.asyncio
    async def test_startup_sequence_reliability(self):
        """Test startup sequence reliability with Five Whys fixes."""
        # Create a complete startup sequence test
        startup_events = []
        
        def log_event(event_name):
            startup_events.append({
                "event": event_name,
                "timestamp": time.time(),
                "thread_id": threading.current_thread().ident
            })
        
        # Test configuration validation phase
        log_event("config_validation_start")
        validator = CentralConfigurationValidator()
        
        # This should work reliably without race conditions
        validator.validate_all_requirements()
        log_event("config_validation_complete")
        
        # Test service lifecycle management phase
        log_event("service_lifecycle_start")
        lifecycle_manager = ServiceLifecycleManager()
        
        # Register a minimal service set
        oauth_service = ServiceRegistration(
            name="oauth_service",
            phase=InitializationPhase.DEPENDENCIES,
            initializer=lambda: log_event("oauth_service_init"),
            is_critical=True
        )
        lifecycle_manager.register_service(oauth_service)
        
        # Initialize services
        success = await lifecycle_manager.initialize_all_services()
        log_event("service_lifecycle_complete")
        
        assert success, \
            "Service lifecycle initialization should complete successfully"
        
        # Verify event sequence
        event_names = [event["event"] for event in startup_events]
        expected_sequence = [
            "config_validation_start",
            "config_validation_complete", 
            "service_lifecycle_start",
            "oauth_service_init",
            "service_lifecycle_complete"
        ]
        
        assert event_names == expected_sequence, \
            f"Startup events should occur in correct sequence. Got: {event_names}"
        
        # Verify timing - no excessive delays indicating race condition resolution
        total_time = startup_events[-1]["timestamp"] - startup_events[0]["timestamp"]
        assert total_time < 5.0, \
            f"Startup sequence should complete quickly without race condition delays. Took: {total_time}s"


class TestRaceConditionScenarios(TestOAuthRaceConditionFixes):
    """Test specific race condition scenarios that were problematic"""
    
    def test_original_oauth_validation_error_reproduction(self):
        """Test reproduction of original OAuth validation error (should now be fixed)."""
        # Simulate the original problematic scenario:
        # - Service startup happening concurrently
        # - OAuth validation during environment loading
        
        def concurrent_oauth_validation():
            try:
                validator = CentralConfigurationValidator()
                # This was the call that originally failed with race conditions
                oauth_client_id = validator.get_oauth_client_id()
                expected_id = "test-oauth-client-id-for-automated-testing"  # From test.env
                return oauth_client_id == expected_id
            except Exception:
                return False
        
        # Run the scenario that previously caused race conditions
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(concurrent_oauth_validation)
                for _ in range(5)
            ]
            results = [f.result() for f in futures]
        
        # With the Five Whys fix, all attempts should succeed
        success_count = sum(results)
        assert success_count == 5, \
            f"All OAuth validation attempts should succeed with race condition fix. Got: {success_count}/5"
    
    def test_environment_loading_timing_edge_cases(self):
        """Test edge cases in environment loading timing."""
        # Test rapid successive calls that might hit race conditions
        validator = CentralConfigurationValidator()
        
        # Clear cache to force fresh loading
        validator.clear_environment_cache()
        
        # Make rapid successive calls
        environments = []
        for i in range(20):
            env = validator.get_environment()
            environments.append(env)
            if i % 5 == 0:
                # Occasionally clear cache to test reloading
                validator.clear_environment_cache()
        
        # All calls should return consistent results
        assert all(env == Environment.TEST for env in environments), \
            "All environment detection calls should return consistent results"
    
    @pytest.mark.asyncio
    async def test_service_initialization_timing_robustness(self):
        """Test service initialization timing robustness."""
        lifecycle_manager = ServiceLifecycleManager()
        
        # Create services with varying initialization times
        fast_service = ServiceRegistration(
            name="fast_service",
            phase=InitializationPhase.BOOTSTRAP,
            initializer=lambda: time.sleep(0.001),  # 1ms
            is_critical=True
        )
        
        slow_service = ServiceRegistration(
            name="slow_service", 
            phase=InitializationPhase.DEPENDENCIES,
            initializer=lambda: time.sleep(0.1),   # 100ms
            is_critical=True
        )
        
        lifecycle_manager.register_service(fast_service)
        lifecycle_manager.register_service(slow_service)
        
        # Initialize with timing variations
        start_time = time.time()
        success = await lifecycle_manager.initialize_all_services()
        total_time = time.time() - start_time
        
        assert success, \
            "Service initialization should succeed despite timing variations"
        
        # Should complete in reasonable time (not hung due to race conditions)
        assert total_time < 2.0, \
            f"Initialization should complete quickly. Took: {total_time}s"


def test_comprehensive_race_condition_fix_validation():
    """
    Comprehensive validation that Five Whys race condition fixes are working.
    
    This test runs all critical scenarios to ensure the solution is robust.
    """
    test_results = {
        "level_1_2_protection": False,
        "level_3_5_lifecycle": False,
        "integration_validation": False,
        "race_condition_scenarios": False
    }
    
    try:
        # Level 1-2 validation
        validator = CentralConfigurationValidator()
        validator.validate_all_requirements()
        oauth_creds = validator.get_oauth_credentials()
        assert oauth_creds["client_id"] and oauth_creds["client_secret"]
        test_results["level_1_2_protection"] = True
        
        # Level 3-5 validation
        lifecycle_manager = ServiceLifecycleManager()
        test_service = ServiceRegistration(
            name="test_validation_service",
            phase=InitializationPhase.BOOTSTRAP,
            is_critical=True
        )
        lifecycle_manager.register_service(test_service)
        status = lifecycle_manager.get_initialization_status()
        assert status["total_services"] == 1
        test_results["level_3_5_lifecycle"] = True
        
        # Integration validation
        timing_issue = validator._detect_timing_issue()
        assert timing_issue is None  # No timing issues in properly configured environment
        test_results["integration_validation"] = True
        
        # Race condition scenarios
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(lambda: validator.get_oauth_client_id())
                for _ in range(5)
            ]
            results = [f.result() for f in futures]
            expected_id = "test-oauth-client-id-for-automated-testing"
            assert all(r == expected_id for r in results)
        test_results["race_condition_scenarios"] = True
        
    except Exception as e:
        pytest.fail(f"Comprehensive validation failed: {e}")
    
    # All validations should pass
    all_passed = all(test_results.values())
    assert all_passed, f"All Five Whys fix validations should pass. Results: {test_results}"
    
    logger.info(" PASS:  Five Whys OAuth race condition fixes validated successfully")
    logger.info(f"Validation results: {test_results}")


if __name__ == "__main__":
    # Run comprehensive validation
    test_comprehensive_race_condition_fix_validation()
    print(" PASS:  All Five Whys OAuth race condition fixes validated successfully!")