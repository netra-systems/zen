"""
ClickHouse Logging Integration Tests - End-to-End Logging Behavior
================================================================

Phase 2 of comprehensive test suite for ClickHouse logging issue:
https://github.com/netra-systems/netra-apex/issues/134

ISSUE CONTEXT:
- ClickHouse ERROR logging for optional services in staging affects golden path observability
- Real connection failures should behave differently based on environment configuration
- Integration-level validation of logging behavior with real connection attempts

PHASE 2 GOAL: Test real connection failures with proper environment context

Business Value Justification (BVJ):
- Segment: Platform/Internal | Goal: System Reliability & Observability | Impact: Operational efficiency
- Validates real-world scenarios where ClickHouse is unavailable
- Ensures staging graceful degradation vs production hard failures
- Tests environment-specific logging behavior with actual services

TEST BEHAVIOR:
- Uses REAL service connections (no mocks at integration level per CLAUDE.md)
- Tests should FAIL with current code (proving wrong logging behavior)
- Tests should PASS after implementing context-aware logging fix
- Validates integration between service initialization and connection handling

Expected Current Failures:
- test_staging_real_connection_failure_graceful_degradation: SHOULD FAIL (logs ERROR instead of WARNING)
- test_production_connection_failure_hard_error: SHOULD PASS (correct ERROR behavior)
- test_environment_transition_logging_consistency: SHOULD FAIL (inconsistent logging)
- test_retry_logic_logging_progression: SHOULD FAIL (inappropriate log levels during retries)
"""

import asyncio
import logging
import pytest
from typing import Dict, Any, List
import io
import sys
import time
from contextlib import contextmanager

from netra_backend.app.db.clickhouse import ClickHouseService
from netra_backend.app.core.configuration import get_configuration
from shared.isolated_environment import IsolatedEnvironment
from test_framework.database.test_database_manager import DatabaseTestManager


class TestClickHouseLoggingIntegration:
    """Integration tests for ClickHouse logging behavior with real connections."""
    
    @contextmanager
    def _capture_logs(self, logger_name: str = "netra_backend.app.logging_config"):
        """Capture log messages for analysis."""
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        # Get the logger and add our handler
        logger = logging.getLogger(logger_name)
        original_level = logger.level
        original_handlers = logger.handlers.copy()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        
        try:
            yield log_capture_string
        finally:
            logger.removeHandler(ch)
            logger.setLevel(original_level)
    
    def _extract_log_records(self, log_output: str) -> List[Dict[str, Any]]:
        """Extract log records from captured output."""
        records = []
        for line in log_output.strip().split('\n'):
            if line.strip():
                if 'ERROR -' in line:
                    records.append({'level': 'ERROR', 'message': line})
                elif 'WARNING -' in line:
                    records.append({'level': 'WARNING', 'message': line})
                elif 'INFO -' in line:
                    records.append({'level': 'INFO', 'message': line})
        return records
    
    @pytest.mark.asyncio
    async def test_staging_real_connection_failure_graceful_degradation(self):
        """
        Test Case 5: Staging real connection failure with graceful degradation
        
        SETUP: Real staging environment, ClickHouse unavailable
        ACTION: Initialize ClickHouseService in staging mode
        EXPECTED: WARNING logs, service continues without ClickHouse
        VALIDATION: Golden path continues, no ERROR noise in logs
        
        This test should FAIL with current code (logs ERROR instead of WARNING for optional service).
        """
        # Configure staging environment with unavailable ClickHouse
        staging_env = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_REQUIRED': 'false',
            'CLICKHOUSE_HOST': 'nonexistent.clickhouse.staging.test',  # Guaranteed to fail
            'CLICKHOUSE_PORT': '8443',
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': 'test_password',
            'CLICKHOUSE_DATABASE': 'test_db',
            'USE_MOCK_CLICKHOUSE': 'false'  # Force real connection attempt
        }
        
        env = IsolatedEnvironment()
        env.enable_isolation()
        
        # Set environment variables
        for key, value in staging_env.items():
            env.set(key, value, "test")
        
        try:
            with self._capture_logs() as log_capture:
                # Initialize service - should gracefully handle unavailable ClickHouse
                service = ClickHouseService()
                
                start_time = time.time()
                initialization_succeeded = False
                initialization_error = None
                
                try:
                    await service.initialize()
                    initialization_succeeded = True
                except Exception as e:
                    initialization_error = e
                    initialization_succeeded = False
                
                elapsed_time = time.time() - start_time
                
                # Analyze captured logs
                log_output = log_capture.getvalue()
                log_records = self._extract_log_records(log_output)
                
                # CRITICAL TEST: Optional service should NOT log ERROR
                error_logs = [r for r in log_records if r['level'] == 'ERROR']
                clickhouse_error_logs = [r for r in error_logs if 'ClickHouse' in r['message'] or 'clickhouse' in r['message'].lower()]
                
                # This should FAIL with current code - currently logs ERROR for optional services
                assert len(clickhouse_error_logs) == 0, (
                    f"STAGING GRACEFUL DEGRADATION FAILURE: Optional ClickHouse in staging should NOT "
                    f"log ERROR on connection failure but found {len(clickhouse_error_logs)} ERROR logs: "
                    f"{clickhouse_error_logs}. This demonstrates the core issue - ERROR logs for optional "
                    f"service failures create noise in staging observability."
                )
                
                # Should contain graceful degradation warnings
                warning_logs = [r for r in log_records if r['level'] == 'WARNING']
                degradation_warnings = [r for r in warning_logs if 'optional' in r['message'].lower() or 'continuing without' in r['message'].lower()]
                
                assert len(degradation_warnings) > 0, (
                    f"STAGING DEGRADATION WARNING REQUIRED: Should log WARNING about graceful degradation "
                    f"for optional ClickHouse but found no degradation warnings. Warning logs: {warning_logs}"
                )
                
                # Service initialization should succeed despite ClickHouse failure
                assert initialization_succeeded, (
                    f"STAGING SERVICE CONTINUATION: ClickHouse service initialization should succeed "
                    f"in staging when ClickHouse is optional but failed with error: {initialization_error}. "
                    f"Elapsed time: {elapsed_time:.2f}s"
                )
                
                # Should complete within reasonable time (no hanging)
                assert elapsed_time < 30.0, (
                    f"STAGING TIMEOUT HANDLING: Service initialization took {elapsed_time:.2f}s, "
                    f"should complete quickly for optional services to avoid blocking startup."
                )
        finally:
            env.disable_isolation()
    
    @pytest.mark.asyncio
    async def test_production_connection_failure_hard_error(self):
        """
        Test Case 6: Production connection failure should be hard error
        
        SETUP: Production environment simulation, ClickHouse required
        ACTION: Initialize ClickHouseService with forced connection failure
        EXPECTED: ERROR logs, service initialization fails
        VALIDATION: Hard failure prevents startup, clear ERROR indication
        
        This test should PASS with current code (demonstrates correct ERROR behavior for required services).
        """
        # Configure production environment with unavailable ClickHouse
        production_env = {
            'ENVIRONMENT': 'production',
            'CLICKHOUSE_REQUIRED': 'true',
            'CLICKHOUSE_HOST': 'nonexistent.clickhouse.production.test',  # Guaranteed to fail
            'CLICKHOUSE_PORT': '8443',
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': 'prod_password',
            'CLICKHOUSE_DATABASE': 'prod_db',
            'USE_MOCK_CLICKHOUSE': 'false'  # Force real connection attempt
        }
        
        with IsolatedEnvironment(production_env):
            with self._capture_logs() as log_capture:
                # Initialize service - should fail hard for required service
                service = ClickHouseService()
                
                start_time = time.time()
                initialization_failed = False
                initialization_error = None
                
                try:
                    await service.initialize()
                    initialization_failed = False
                except Exception as e:
                    initialization_error = e
                    initialization_failed = True
                
                elapsed_time = time.time() - start_time
                
                # Analyze captured logs
                log_output = log_capture.getvalue()
                log_records = self._extract_log_records(log_output)
                
                # REQUIRED service should fail initialization
                assert initialization_failed, (
                    f"PRODUCTION HARD FAILURE REQUIRED: Required ClickHouse service in production "
                    f"should FAIL initialization when ClickHouse unavailable but succeeded. "
                    f"Elapsed time: {elapsed_time:.2f}s"
                )
                
                assert initialization_error is not None, (
                    "PRODUCTION ERROR REQUIRED: Should raise exception for required service failure"
                )
                
                # Should contain ERROR logs for required service
                error_logs = [r for r in log_records if r['level'] == 'ERROR']
                clickhouse_error_logs = [r for r in error_logs if 'ClickHouse' in r['message'] or 'clickhouse' in r['message'].lower()]
                
                assert len(clickhouse_error_logs) > 0, (
                    f"PRODUCTION ERROR LOGGING REQUIRED: Required ClickHouse service should log "
                    f"ERROR on connection failure but found no ClickHouse ERROR logs. "
                    f"Error logs: {error_logs}"
                )
                
                # Should NOT contain graceful degradation warnings for required service
                warning_logs = [r for r in log_records if r['level'] == 'WARNING']
                degradation_warnings = [r for r in warning_logs if 'optional' in r['message'].lower()]
                
                assert len(degradation_warnings) == 0, (
                    f"PRODUCTION NO DEGRADATION: Required service should NOT log graceful degradation "
                    f"warnings but found: {degradation_warnings}"
                )
                
                # Should fail within reasonable time (not hang indefinitely)
                assert elapsed_time < 60.0, (
                    f"PRODUCTION TIMEOUT HANDLING: Service initialization took {elapsed_time:.2f}s, "
                    f"should fail quickly for required services to provide fast feedback."
                )
    
    @pytest.mark.asyncio
    async def test_environment_transition_logging_consistency(self):
        """
        Test Case 7: Environment transition logging consistency
        
        SETUP: Same codebase, different environment configurations
        ACTION: Run identical operations in staging vs production contexts
        EXPECTED: Consistent log level behavior based on environment
        VALIDATION: Staging=WARNING degradation, Production=ERROR failure
        
        This test should FAIL with current code (inconsistent logging between environments).
        """
        # Test scenarios: same failure, different environments
        test_scenarios = [
            {
                'name': 'staging_optional',
                'env': {
                    'ENVIRONMENT': 'staging',
                    'CLICKHOUSE_REQUIRED': 'false',
                    'CLICKHOUSE_HOST': 'failing.clickhouse.test',
                    'CLICKHOUSE_PORT': '8443',
                    'USE_MOCK_CLICKHOUSE': 'false'
                },
                'expected_initialization': 'succeed',
                'expected_log_level': 'WARNING',
                'expected_error_count': 0
            },
            {
                'name': 'production_required',
                'env': {
                    'ENVIRONMENT': 'production',
                    'CLICKHOUSE_REQUIRED': 'true',
                    'CLICKHOUSE_HOST': 'failing.clickhouse.test',
                    'CLICKHOUSE_PORT': '8443',
                    'USE_MOCK_CLICKHOUSE': 'false'
                },
                'expected_initialization': 'fail',
                'expected_log_level': 'ERROR',
                'expected_error_count': 1  # At least 1 ERROR log
            }
        ]
        
        results = {}
        
        for scenario in test_scenarios:
            with IsolatedEnvironment(scenario['env']):
                with self._capture_logs() as log_capture:
                    service = ClickHouseService()
                    
                    try:
                        await service.initialize()
                        initialization_result = 'succeed'
                    except Exception:
                        initialization_result = 'fail'
                    
                    # Analyze logs
                    log_output = log_capture.getvalue()
                    log_records = self._extract_log_records(log_output)
                    
                    error_logs = [r for r in log_records if r['level'] == 'ERROR']
                    warning_logs = [r for r in log_records if r['level'] == 'WARNING']
                    clickhouse_error_logs = [r for r in error_logs if 'ClickHouse' in r['message']]
                    
                    results[scenario['name']] = {
                        'initialization': initialization_result,
                        'error_count': len(clickhouse_error_logs),
                        'warning_count': len(warning_logs),
                        'log_output': log_output
                    }
        
        # Validate staging behavior (optional service)
        staging_result = results['staging_optional']
        assert staging_result['initialization'] == 'succeed', (
            f"STAGING CONSISTENCY: Staging should succeed with optional ClickHouse but got: "
            f"{staging_result['initialization']}"
        )
        
        # CRITICAL TEST: Staging should NOT have ERROR logs for optional service
        assert staging_result['error_count'] == 0, (
            f"STAGING ERROR CONSISTENCY FAILURE: Staging with optional ClickHouse should have "
            f"0 ERROR logs but found {staging_result['error_count']} ERROR logs. This demonstrates "
            f"inconsistent logging behavior - optional services should use WARNING, not ERROR. "
            f"Staging logs: {staging_result['log_output']}"
        )
        
        assert staging_result['warning_count'] > 0, (
            f"STAGING WARNING CONSISTENCY: Staging should have WARNING logs for graceful degradation "
            f"but found {staging_result['warning_count']} WARNING logs."
        )
        
        # Validate production behavior (required service)
        production_result = results['production_required']
        assert production_result['initialization'] == 'fail', (
            f"PRODUCTION CONSISTENCY: Production should fail with required ClickHouse but got: "
            f"{production_result['initialization']}"
        )
        
        assert production_result['error_count'] > 0, (
            f"PRODUCTION ERROR CONSISTENCY: Production with required ClickHouse should have "
            f"ERROR logs but found {production_result['error_count']} ERROR logs."
        )
        
        # Cross-environment consistency validation
        error_diff = production_result['error_count'] - staging_result['error_count']
        assert error_diff > 0, (
            f"CROSS-ENVIRONMENT CONSISTENCY FAILURE: Production should have more ERROR logs than "
            f"staging (required vs optional) but got Production: {production_result['error_count']}, "
            f"Staging: {staging_result['error_count']}. This demonstrates the core issue - "
            f"both environments log the same ERROR level regardless of service requirements."
        )
    
    @pytest.mark.asyncio
    async def test_retry_logic_logging_progression(self):
        """
        Test Case 8: Retry logic logging progression
        
        SETUP: Connection with intermittent failures across retry attempts
        ACTION: Trigger retry sequence in ClickHouseService.initialize()
        EXPECTED: Progressive warning messages, final decision based on optionality
        VALIDATION: Clear retry progression, appropriate final log level
        
        This test should FAIL with current code (inappropriate log levels during retries).
        """
        # Test retry behavior in staging (optional) vs production (required)
        retry_scenarios = [
            {
                'name': 'staging_optional_retries',
                'env': {
                    'ENVIRONMENT': 'staging',
                    'CLICKHOUSE_REQUIRED': 'false',
                    'CLICKHOUSE_HOST': 'retry.test.clickhouse',
                    'CLICKHOUSE_PORT': '8443',
                    'USE_MOCK_CLICKHOUSE': 'false'
                },
                'expected_final_initialization': 'succeed',
                'expected_final_log_level': 'WARNING',
                'max_expected_errors': 0  # Should not log ERROR for optional service
            },
            {
                'name': 'production_required_retries',
                'env': {
                    'ENVIRONMENT': 'production',
                    'CLICKHOUSE_REQUIRED': 'true',
                    'CLICKHOUSE_HOST': 'retry.test.clickhouse',
                    'CLICKHOUSE_PORT': '8443',
                    'USE_MOCK_CLICKHOUSE': 'false'
                },
                'expected_final_initialization': 'fail',
                'expected_final_log_level': 'ERROR',
                'max_expected_errors': 3  # Should log ERROR for required service
            }
        ]
        
        for scenario in retry_scenarios:
            with IsolatedEnvironment(scenario['env']):
                with self._capture_logs() as log_capture:
                    service = ClickHouseService()
                    
                    start_time = time.time()
                    
                    try:
                        await service.initialize()
                        final_result = 'succeed'
                    except Exception:
                        final_result = 'fail'
                    
                    elapsed_time = time.time() - start_time
                    
                    # Analyze retry progression in logs
                    log_output = log_capture.getvalue()
                    log_records = self._extract_log_records(log_output)
                    
                    # Look for retry-related logs
                    retry_logs = [r for r in log_records if 'attempt' in r['message'].lower() or 'retry' in r['message'].lower()]
                    error_logs = [r for r in log_records if r['level'] == 'ERROR']
                    warning_logs = [r for r in log_records if r['level'] == 'WARNING']
                    
                    clickhouse_error_logs = [r for r in error_logs if 'ClickHouse' in r['message']]
                    
                    # Validate final initialization result
                    assert final_result == scenario['expected_final_initialization'], (
                        f"RETRY FINAL RESULT: Scenario '{scenario['name']}' should result in "
                        f"'{scenario['expected_final_initialization']}' but got '{final_result}'"
                    )
                    
                    # CRITICAL TEST: Validate appropriate log levels during retries
                    if scenario['name'] == 'staging_optional_retries':
                        # Staging optional: should NOT log ERROR during retries
                        assert len(clickhouse_error_logs) <= scenario['max_expected_errors'], (
                            f"STAGING RETRY ERROR LOGGING FAILURE: Optional ClickHouse in staging should "
                            f"NOT log ERROR during retries but found {len(clickhouse_error_logs)} ERROR logs "
                            f"(max expected: {scenario['max_expected_errors']}). Error logs: {clickhouse_error_logs}. "
                            f"This demonstrates inappropriate ERROR logging for optional service retries."
                        )
                        
                        # Should have warning about final graceful degradation
                        degradation_warnings = [r for r in warning_logs if 'optional' in r['message'].lower()]
                        assert len(degradation_warnings) > 0, (
                            f"STAGING RETRY WARNING REQUIRED: Should log WARNING about graceful degradation "
                            f"after retries but found no degradation warnings in: {warning_logs}"
                        )
                    
                    elif scenario['name'] == 'production_required_retries':
                        # Production required: should log ERROR for final failure
                        assert len(clickhouse_error_logs) > 0, (
                            f"PRODUCTION RETRY ERROR REQUIRED: Required ClickHouse in production should "
                            f"log ERROR after failed retries but found {len(clickhouse_error_logs)} ERROR logs."
                        )
                    
                    # Validate retry timing (should not take too long)
                    max_expected_time = 30.0 if scenario['name'] == 'staging_optional_retries' else 60.0
                    assert elapsed_time < max_expected_time, (
                        f"RETRY TIMING: Scenario '{scenario['name']}' took {elapsed_time:.2f}s, "
                        f"should complete within {max_expected_time}s to avoid blocking startup."
                    )


class TestClickHouseRealServiceIntegration:
    """Test ClickHouse integration with real service dependencies."""
    
    @pytest.mark.asyncio
    async def test_clickhouse_integration_with_database_manager(self):
        """
        Test ClickHouse integration with DatabaseTestManager for real connections.
        
        This test validates that ClickHouse logging behaves correctly when integrated
        with other database services and test infrastructure.
        """
        # Test with staging configuration (optional ClickHouse)
        staging_env = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_REQUIRED': 'false',
            'CLICKHOUSE_HOST': 'integration.test.nonexistent',
            'CLICKHOUSE_PORT': '8443',
            'USE_MOCK_CLICKHOUSE': 'false'
        }
        
        with IsolatedEnvironment(staging_env):
            # Initialize database manager (may start other services)
            db_manager = DatabaseTestManager()
            
            with self._capture_logs() as log_capture:
                # Initialize ClickHouse as part of broader service initialization
                clickhouse_service = ClickHouseService()
                
                try:
                    await clickhouse_service.initialize()
                    clickhouse_initialized = True
                except Exception as e:
                    clickhouse_initialized = False
                    pytest.fail(
                        f"INTEGRATION GRACEFUL DEGRADATION: ClickHouse should gracefully degrade "
                        f"when optional in staging but failed with: {e}"
                    )
                
                # Analyze integration logs
                log_output = log_capture.getvalue()
                
                # Should not interfere with other database services
                error_logs = [line for line in log_output.split('\n') if 'ERROR' in line and 'ClickHouse' in line]
                
                # CRITICAL: ClickHouse errors should not pollute integration logs
                assert len(error_logs) == 0, (
                    f"INTEGRATION ERROR POLLUTION: Optional ClickHouse should not create ERROR logs "
                    f"that pollute integration environment but found: {error_logs}. This demonstrates "
                    f"how ClickHouse ERROR logging affects broader system observability."
                )
                
                # ClickHouse should initialize successfully despite connection failure
                assert clickhouse_initialized, (
                    "INTEGRATION SERVICE CONTINUATION: ClickHouse should initialize successfully "
                    "when optional, allowing other services to continue normally."
                )
    
    @pytest.mark.asyncio
    async def test_clickhouse_circuit_breaker_integration_logging(self):
        """
        Test ClickHouse circuit breaker integration with proper logging levels.
        
        This validates that circuit breaker behavior respects service optionality.
        """
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreaker, UnifiedCircuitConfig
        
        # Test circuit breaker with optional service
        optional_env = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_REQUIRED': 'false',
            'CLICKHOUSE_HOST': 'circuit.test.nonexistent',
            'USE_MOCK_CLICKHOUSE': 'false'
        }
        
        with IsolatedEnvironment(optional_env):
            with self._capture_logs() as log_capture:
                # Create service with circuit breaker
                service = ClickHouseService()
                
                # Trigger multiple failures to test circuit breaker
                failure_count = 0
                for attempt in range(5):
                    try:
                        await service.initialize()
                        break
                    except Exception:
                        failure_count += 1
                        # Continue attempting to trigger circuit breaker
                        continue
                
                log_output = log_capture.getvalue()
                
                # Circuit breaker failures for optional service should not log ERROR
                error_logs = [line for line in log_output.split('\n') if 'ERROR' in line and 'ClickHouse' in line]
                
                # CRITICAL: Circuit breaker for optional service should use WARNING
                assert len(error_logs) == 0, (
                    f"CIRCUIT BREAKER OPTIONAL SERVICE: Circuit breaker for optional ClickHouse "
                    f"should not log ERROR but found {len(error_logs)} ERROR logs: {error_logs}. "
                    f"This demonstrates that circuit breaker logging is not context-aware."
                )
                
                # Should contain circuit breaker warnings instead
                warning_logs = [line for line in log_output.split('\n') if 'WARNING' in line]
                circuit_warnings = [line for line in warning_logs if 'circuit' in line.lower() or 'breaker' in line.lower()]
                
                # Circuit breaker should gracefully handle optional service failures
                if failure_count >= 3:  # If circuit breaker was triggered
                    assert len(circuit_warnings) > 0 or 'optional' in log_output.lower(), (
                        f"CIRCUIT BREAKER WARNING EXPECTED: Should log WARNING about circuit breaker "
                        f"or graceful degradation for optional service after {failure_count} failures. "
                        f"Warning logs: {warning_logs}"
                    )
    
    @contextmanager
    def _capture_logs(self, logger_name: str = "netra_backend.app.logging_config"):
        """Capture log messages for analysis."""
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        # Get the logger and add our handler
        logger = logging.getLogger(logger_name)
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        
        try:
            yield log_capture_string
        finally:
            logger.removeHandler(ch)
            logger.setLevel(original_level)


class TestClickHouseEnvironmentSpecificBehavior:
    """Test environment-specific ClickHouse behavior patterns."""
    
    @pytest.mark.asyncio
    async def test_development_environment_logging_behavior(self):
        """
        Test ClickHouse logging behavior in development environment.
        
        Development should behave similarly to staging for developer experience.
        """
        dev_env = {
            'ENVIRONMENT': 'development',
            'CLICKHOUSE_REQUIRED': 'false',
            'CLICKHOUSE_HOST': 'localhost',
            'CLICKHOUSE_PORT': '8123',
            'USE_MOCK_CLICKHOUSE': 'false'
        }
        
        with IsolatedEnvironment(dev_env):
            with self._capture_logs() as log_capture:
                service = ClickHouseService()
                
                try:
                    await service.initialize()
                    dev_initialization_succeeded = True
                except Exception:
                    dev_initialization_succeeded = False
                
                log_output = log_capture.getvalue()
                error_logs = [line for line in log_output.split('\n') if 'ERROR' in line and 'ClickHouse' in line]
                
                # Development should succeed when ClickHouse optional
                assert dev_initialization_succeeded, (
                    "DEVELOPMENT GRACEFUL DEGRADATION: Development should succeed with optional ClickHouse"
                )
                
                # CRITICAL: Development should not log ERROR for optional ClickHouse
                assert len(error_logs) == 0, (
                    f"DEVELOPMENT ERROR LOGGING: Development with optional ClickHouse should not "
                    f"log ERROR but found: {error_logs}. This creates noise for developers."
                )
    
    @contextmanager
    def _capture_logs(self, logger_name: str = "netra_backend.app.logging_config"):
        """Capture log messages for analysis."""
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        logger = logging.getLogger(logger_name)
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        
        try:
            yield log_capture_string
        finally:
            logger.removeHandler(ch)
            logger.setLevel(original_level)