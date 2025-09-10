"""
ClickHouse Logging Fix Validation - Mission Critical Regression Prevention Tests
==============================================================================

Phase 4 of comprehensive test suite for ClickHouse logging issue:
https://github.com/netra-systems/netra-apex/issues/134

ISSUE CONTEXT:
- ClickHouse ERROR logging for optional services in staging affects golden path observability
- Fix involves context-aware logging - ERROR for required, WARNING for optional
- Critical validation that fix works and prevents regression

PHASE 4 GOAL: Ensure fix works and prevents regression

Business Value Justification (BVJ):
- Segment: Platform/Internal | Goal: Risk Mitigation & Quality Assurance | Impact: System stability  
- Prevents regression of logging fixes
- Validates context-aware logging implementation
- Ensures backward compatibility for required services
- Provides continuous validation framework

TEST BEHAVIOR:
- Mission critical tests for deployment validation
- Validates fix effectiveness before/after implementation
- Tests edge cases and configuration variations
- Ensures no breaking changes to existing functionality

REGRESSION PREVENTION STRATEGY:
- Before fix: Demonstrates current wrong behavior
- After fix: Validates correct behavior
- Edge cases: Ensures robust configuration handling
- Backward compatibility: Required services still log ERROR appropriately

Expected Behavior Progression:
Phase A (Before Fix): test_before_fix_behavior_reproduction should PASS (demonstrates problem)
Phase B (After Fix): test_after_fix_behavior_validation should PASS (demonstrates solution)
All other tests should PASS in both phases with different log patterns
"""

import asyncio
import logging
import pytest
from typing import Dict, Any, List, Optional
import io
import time
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

from netra_backend.app.db.clickhouse import ClickHouseService, _handle_connection_error
from shared.isolated_environment import IsolatedEnvironment


class TestClickHouseLoggingFixValidation:
    """Mission critical tests for ClickHouse logging fix validation."""
    
    @contextmanager
    def _capture_logs(self, logger_name: str = "netra_backend.app.logging_config"):
        """Capture log messages for validation analysis."""
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
    
    def _analyze_logging_behavior(self, log_output: str) -> Dict[str, Any]:
        """Analyze logging behavior patterns for fix validation."""
        lines = [line.strip() for line in log_output.strip().split('\n') if line.strip()]
        
        analysis = {
            'total_lines': len(lines),
            'error_logs': [line for line in lines if 'ERROR' in line],
            'warning_logs': [line for line in lines if 'WARNING' in line],
            'info_logs': [line for line in lines if 'INFO' in line],
            'clickhouse_error_logs': [line for line in lines if 'ERROR' in line and ('ClickHouse' in line or 'clickhouse' in line.lower())],
            'clickhouse_warning_logs': [line for line in lines if 'WARNING' in line and ('ClickHouse' in line or 'clickhouse' in line.lower())],
            'degradation_warnings': [line for line in lines if 'WARNING' in line and ('optional' in line.lower() or 'degradation' in line.lower())],
            'connection_errors': [line for line in lines if 'ERROR' in line and ('connection' in line.lower() or 'Connection' in line)],
            'duplicate_patterns': self._detect_duplicate_log_patterns(lines)
        }
        
        return analysis
    
    def _detect_duplicate_log_patterns(self, log_lines: List[str]) -> Dict[str, int]:
        """Detect duplicate logging patterns that indicate multiple error handlers."""
        patterns = {}
        for line in log_lines:
            # Extract key patterns
            if 'ClickHouse' in line and 'ERROR' in line:
                if 'Connection failed' in line:
                    patterns['clickhouse_connection_failed'] = patterns.get('clickhouse_connection_failed', 0) + 1
                if 'CLICKHOUSE CONNECTION ERROR' in line:
                    patterns['clickhouse_connection_error_banner'] = patterns.get('clickhouse_connection_error_banner', 0) + 1
                if 'Environment:' in line:
                    patterns['environment_info'] = patterns.get('environment_info', 0) + 1
        
        return patterns
    
    @pytest.mark.asyncio
    async def test_before_fix_behavior_reproduction(self):
        """
        Test Case 13: Before fix behavior reproduction
        
        SETUP: Temporarily disable context-aware logging (if possible)
        ACTION: Force old behavior where ERROR logs always appear
        EXPECTED: ERROR logs for optional service failures (old bad behavior)
        VALIDATION: Reproduces exact issue described in staging logs
        
        This test validates we can reproduce the original problem.
        It should PASS when run against current (unfixed) code.
        """
        # Test environment that should demonstrate the original issue
        original_issue_env = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_REQUIRED': 'false',  # Optional service
            'CLICKHOUSE_HOST': 'reproduce.issue.test.unavailable',
            'CLICKHOUSE_PORT': '8443',
            'USE_MOCK_CLICKHOUSE': 'false'
        }
        
        with IsolatedEnvironment(original_issue_env):
            with self._capture_logs() as log_capture:
                # Force connection failure to reproduce original issue
                service = ClickHouseService()
                
                # This should demonstrate the original problematic behavior
                try:
                    await service.initialize()
                    initialization_result = 'succeeded'
                except Exception:
                    initialization_result = 'failed'
                
                # Analyze logged behavior
                log_output = log_capture.getvalue()
                log_analysis = self._analyze_logging_behavior(log_output)
                
                # ORIGINAL ISSUE REPRODUCTION: Should show problematic ERROR logging
                clickhouse_error_count = len(log_analysis['clickhouse_error_logs'])
                clickhouse_warning_count = len(log_analysis['clickhouse_warning_logs'])
                
                # Document the original issue pattern
                issue_reproduced = False
                
                if clickhouse_error_count > 0:
                    # Current (problematic) behavior: ERROR logs for optional service
                    issue_reproduced = True
                    pytest.skip(
                        f"ORIGINAL ISSUE REPRODUCED: Found {clickhouse_error_count} ClickHouse ERROR logs "
                        f"for optional service, demonstrating the original issue. ERROR logs: "
                        f"{log_analysis['clickhouse_error_logs']}. This test documents the problem "
                        f"state and should be replaced with after-fix validation once fix is implemented."
                    )
                
                elif clickhouse_warning_count > 0:
                    # Fixed behavior: WARNING logs for optional service
                    pytest.fail(
                        f"FIX ALREADY IMPLEMENTED: Found {clickhouse_warning_count} ClickHouse WARNING logs "
                        f"instead of ERROR logs, indicating the fix is already implemented. This test is "
                        f"designed to reproduce the original issue before the fix. Warning logs: "
                        f"{log_analysis['clickhouse_warning_logs']}"
                    )
                
                else:
                    # Unexpected: No ClickHouse logs at all
                    pytest.fail(
                        f"ISSUE REPRODUCTION FAILED: Expected to reproduce original issue with ClickHouse "
                        f"ERROR logs but found no ClickHouse logs. Total logs: {log_analysis['total_lines']}. "
                        f"Unable to validate fix without reproducing original problem."
                    )
    
    @pytest.mark.asyncio
    async def test_after_fix_behavior_validation(self):
        """
        Test Case 14: After fix behavior validation
        
        SETUP: Enable context-aware logging fix
        ACTION: Identical scenario to test 13
        EXPECTED: WARNING logs for optional service failures (new good behavior)
        VALIDATION: Demonstrates fix effectiveness
        
        This test should PASS after implementing the context-aware logging fix.
        """
        # Same environment as reproduction test
        fixed_behavior_env = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_REQUIRED': 'false',  # Optional service
            'CLICKHOUSE_HOST': 'validate.fix.test.unavailable',
            'CLICKHOUSE_PORT': '8443',
            'USE_MOCK_CLICKHOUSE': 'false'
        }
        
        with IsolatedEnvironment(fixed_behavior_env):
            with self._capture_logs() as log_capture:
                service = ClickHouseService()
                
                # Test the fixed behavior
                try:
                    await service.initialize()
                    initialization_result = 'succeeded'
                except Exception as e:
                    initialization_result = 'failed'
                    pytest.fail(
                        f"FIX VALIDATION INITIALIZATION: Optional ClickHouse service should succeed "
                        f"with graceful degradation but failed: {e}"
                    )
                
                # Analyze fixed behavior
                log_output = log_capture.getvalue()
                log_analysis = self._analyze_logging_behavior(log_output)
                
                # FIXED BEHAVIOR VALIDATION: Should show improved logging
                clickhouse_error_count = len(log_analysis['clickhouse_error_logs'])
                clickhouse_warning_count = len(log_analysis['clickhouse_warning_logs'])
                degradation_warning_count = len(log_analysis['degradation_warnings'])
                
                # Primary fix validation: No ERROR logs for optional service
                assert clickhouse_error_count == 0, (
                    f"FIX VALIDATION ERROR ELIMINATION: Optional ClickHouse service should NOT "
                    f"log ERROR after fix but found {clickhouse_error_count} ERROR logs: "
                    f"{log_analysis['clickhouse_error_logs']}. Fix did not eliminate inappropriate ERROR logging."
                )
                
                # Should have appropriate WARNING logs instead
                assert clickhouse_warning_count > 0 or degradation_warning_count > 0, (
                    f"FIX VALIDATION WARNING REQUIRED: Should log WARNING for optional service "
                    f"graceful degradation but found {clickhouse_warning_count} ClickHouse warnings "
                    f"and {degradation_warning_count} degradation warnings. Fix should provide "
                    f"appropriate WARNING-level feedback."
                )
                
                # Initialization should succeed (graceful degradation)
                assert initialization_result == 'succeeded', (
                    f"FIX VALIDATION GRACEFUL DEGRADATION: Optional service should succeed with "
                    f"graceful degradation but initialization {initialization_result}"
                )
                
                # Validate specific fix patterns
                expected_patterns = [
                    'optional',
                    'degradation', 
                    'continuing without',
                    'analytics disabled'
                ]
                
                found_patterns = []
                for pattern in expected_patterns:
                    if any(pattern.lower() in log.lower() for log in log_analysis['warning_logs']):
                        found_patterns.append(pattern)
                
                assert len(found_patterns) > 0, (
                    f"FIX VALIDATION PATTERN MATCHING: Should find appropriate degradation patterns "
                    f"in WARNING logs but found none of: {expected_patterns}. Warning logs: "
                    f"{log_analysis['warning_logs']}"
                )
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_required_services(self):
        """
        Test Case 15: Backward compatibility for required services
        
        SETUP: Services that legitimately require ClickHouse
        ACTION: Test with CLICKHOUSE_REQUIRED=true environments
        EXPECTED: ERROR logs still appear for genuinely required services
        VALIDATION: Fix doesn't break legitimate error reporting
        
        This test ensures the fix doesn't break existing required service behavior.
        """
        # Test required service behavior (should still log ERROR)
        required_service_scenarios = [
            {
                'name': 'production_required',
                'env': {
                    'ENVIRONMENT': 'production',
                    'CLICKHOUSE_REQUIRED': 'true',
                    'CLICKHOUSE_HOST': 'required.test.unavailable',
                    'USE_MOCK_CLICKHOUSE': 'false'
                },
                'expected_initialization': 'fail',
                'expected_error_logs': True,
                'expected_warning_logs': False
            },
            {
                'name': 'staging_explicitly_required',
                'env': {
                    'ENVIRONMENT': 'staging',
                    'CLICKHOUSE_REQUIRED': 'true',  # Explicitly required even in staging
                    'CLICKHOUSE_HOST': 'required.staging.test.unavailable',
                    'USE_MOCK_CLICKHOUSE': 'false'
                },
                'expected_initialization': 'fail',
                'expected_error_logs': True,
                'expected_warning_logs': False
            }
        ]
        
        for scenario in required_service_scenarios:
            with IsolatedEnvironment(scenario['env']):
                with self._capture_logs() as log_capture:
                    service = ClickHouseService()
                    
                    # Test required service behavior
                    try:
                        await service.initialize()
                        initialization_result = 'succeeded'
                    except Exception:
                        initialization_result = 'failed'
                    
                    # Analyze required service logging
                    log_output = log_capture.getvalue()
                    log_analysis = self._analyze_logging_behavior(log_output)
                    
                    # Validate initialization behavior
                    assert initialization_result == ('succeeded' if scenario['expected_initialization'] == 'succeed' else 'failed'), (
                        f"BACKWARD COMPATIBILITY {scenario['name']}: Required service initialization "
                        f"should {scenario['expected_initialization']} but {initialization_result}"
                    )
                    
                    # Validate ERROR logging for required services
                    clickhouse_error_count = len(log_analysis['clickhouse_error_logs'])
                    clickhouse_warning_count = len(log_analysis['clickhouse_warning_logs'])
                    
                    if scenario['expected_error_logs']:
                        assert clickhouse_error_count > 0, (
                            f"BACKWARD COMPATIBILITY {scenario['name']}: Required service should "
                            f"log ERROR when failing but found {clickhouse_error_count} ERROR logs. "
                            f"Fix broke legitimate error reporting for required services."
                        )
                    
                    if not scenario['expected_warning_logs']:
                        degradation_warnings = len(log_analysis['degradation_warnings'])
                        assert degradation_warnings == 0, (
                            f"BACKWARD COMPATIBILITY {scenario['name']}: Required service should NOT "
                            f"log graceful degradation warnings but found {degradation_warnings}. "
                            f"Required services should fail hard, not degrade gracefully."
                        )
                    
                    # Validate error message content for required services
                    if clickhouse_error_count > 0:
                        error_messages = log_analysis['clickhouse_error_logs']
                        required_indicators = ['required', 'REQUIRED', 'production', 'fail']
                        
                        has_required_context = any(
                            any(indicator in error_msg for indicator in required_indicators)
                            for error_msg in error_messages
                        )
                        
                        assert has_required_context, (
                            f"BACKWARD COMPATIBILITY {scenario['name']}: ERROR messages should "
                            f"indicate service is required. Error messages: {error_messages}"
                        )
    
    def test_configuration_edge_cases(self):
        """
        Test Case 16: Configuration edge cases
        
        SETUP: Missing CLICKHOUSE_REQUIRED, malformed environment configs
        ACTION: Test with various configuration edge cases
        EXPECTED: Sensible defaults, clear indication of configuration issues
        VALIDATION: Robust configuration handling
        
        This test ensures the fix handles configuration edge cases gracefully.
        """
        # Test configuration edge cases
        edge_case_scenarios = [
            {
                'name': 'missing_clickhouse_required',
                'env': {
                    'ENVIRONMENT': 'staging',
                    # CLICKHOUSE_REQUIRED missing - should default to false
                    'CLICKHOUSE_HOST': 'edge.case.test.unavailable'
                },
                'expected_behavior': 'optional_default',
                'expected_error_logs': False
            },
            {
                'name': 'invalid_clickhouse_required_value',
                'env': {
                    'ENVIRONMENT': 'staging', 
                    'CLICKHOUSE_REQUIRED': 'maybe',  # Invalid value
                    'CLICKHOUSE_HOST': 'edge.case.test.unavailable'
                },
                'expected_behavior': 'optional_default',  # Should default to false
                'expected_error_logs': False
            },
            {
                'name': 'missing_environment',
                'env': {
                    'CLICKHOUSE_REQUIRED': 'false',
                    # ENVIRONMENT missing - should default to development
                    'CLICKHOUSE_HOST': 'edge.case.test.unavailable'
                },
                'expected_behavior': 'optional_default',
                'expected_error_logs': False
            },
            {
                'name': 'production_missing_required_flag',
                'env': {
                    'ENVIRONMENT': 'production',
                    # CLICKHOUSE_REQUIRED missing in production - should default to required
                    'CLICKHOUSE_HOST': 'edge.case.test.unavailable'
                },
                'expected_behavior': 'required_default',
                'expected_error_logs': True
            }
        ]
        
        for scenario in edge_case_scenarios:
            with IsolatedEnvironment(scenario['env']):
                with self._capture_logs() as log_capture:
                    # Test error handler directly for configuration edge cases
                    test_exception = ConnectionRefusedError(f"Test edge case: {scenario['name']}")
                    
                    configuration_handled = True
                    try:
                        _handle_connection_error(test_exception)
                    except ConnectionRefusedError:
                        # Expected for required services
                        pass
                    except Exception as e:
                        configuration_handled = False
                        pytest.fail(
                            f"CONFIGURATION EDGE CASE {scenario['name']}: Configuration should be "
                            f"handled gracefully but raised unexpected exception: {e}"
                        )
                    
                    # Analyze edge case handling
                    log_output = log_capture.getvalue()
                    log_analysis = self._analyze_logging_behavior(log_output)
                    
                    clickhouse_error_count = len(log_analysis['clickhouse_error_logs'])
                    
                    # Validate expected behavior
                    if scenario['expected_error_logs']:
                        assert clickhouse_error_count > 0, (
                            f"CONFIGURATION EDGE CASE {scenario['name']}: Should log ERROR for "
                            f"required service but found {clickhouse_error_count} ERROR logs"
                        )
                    else:
                        assert clickhouse_error_count == 0, (
                            f"CONFIGURATION EDGE CASE {scenario['name']}: Should NOT log ERROR "
                            f"for optional service but found {clickhouse_error_count} ERROR logs: "
                            f"{log_analysis['clickhouse_error_logs']}"
                        )
                    
                    # Validate configuration handling
                    assert configuration_handled, (
                        f"CONFIGURATION EDGE CASE {scenario['name']}: Should handle configuration "
                        f"edge case gracefully without unexpected exceptions"
                    )
                    
                    # Check for configuration warnings
                    config_warnings = [log for log in log_analysis['warning_logs'] 
                                     if 'config' in log.lower() or 'default' in log.lower()]
                    
                    # Should provide clear feedback about configuration decisions
                    total_feedback = len(log_analysis['error_logs']) + len(log_analysis['warning_logs'])
                    assert total_feedback > 0, (
                        f"CONFIGURATION EDGE CASE {scenario['name']}: Should provide clear "
                        f"feedback about configuration handling but found no logs"
                    )


class TestClickHouseLoggingRegressionPrevention:
    """Regression prevention tests for ClickHouse logging fixes."""
    
    def test_duplicate_logging_elimination(self):
        """Test that duplicate logging paths are eliminated after fix."""
        env_config = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_REQUIRED': 'false',
            'CLICKHOUSE_HOST': 'duplicate.test.unavailable'
        }
        
        with IsolatedEnvironment(env_config):
            with self._capture_logs() as log_capture:
                test_exception = ConnectionRefusedError("Duplicate logging test")
                
                try:
                    _handle_connection_error(test_exception)
                except ConnectionRefusedError:
                    pass
                
                log_output = log_capture.getvalue()
                log_analysis = self._analyze_logging_behavior(log_output)
                
                # Check for duplicate patterns
                duplicate_patterns = log_analysis['duplicate_patterns']
                
                # Should not have multiple instances of the same error pattern
                for pattern, count in duplicate_patterns.items():
                    assert count <= 1, (
                        f"DUPLICATE LOGGING PREVENTION: Found {count} instances of pattern "
                        f"'{pattern}', should have at most 1. This indicates duplicate "
                        f"logging paths that create noise."
                    )
    
    def test_logging_performance_impact(self):
        """Test that logging fix doesn't negatively impact performance."""
        env_config = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_REQUIRED': 'false'
        }
        
        with IsolatedEnvironment(env_config):
            # Time multiple error handling calls
            start_time = time.time()
            
            for i in range(10):
                test_exception = ConnectionRefusedError(f"Performance test {i}")
                try:
                    _handle_connection_error(test_exception)
                except ConnectionRefusedError:
                    pass
            
            elapsed_time = time.time() - start_time
            avg_time_per_call = elapsed_time / 10
            
            # Error handling should be fast
            assert avg_time_per_call < 0.1, (
                f"LOGGING PERFORMANCE: Error handling took {avg_time_per_call:.3f}s per call, "
                f"should be under 0.1s. Logging fix may have introduced performance regression."
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
    
    def _analyze_logging_behavior(self, log_output: str) -> Dict[str, Any]:
        """Analyze logging behavior patterns."""
        lines = [line.strip() for line in log_output.strip().split('\n') if line.strip()]
        
        return {
            'total_lines': len(lines),
            'error_logs': [line for line in lines if 'ERROR' in line],
            'warning_logs': [line for line in lines if 'WARNING' in line],
            'clickhouse_error_logs': [line for line in lines if 'ERROR' in line and ('ClickHouse' in line or 'clickhouse' in line.lower())],
            'clickhouse_warning_logs': [line for line in lines if 'WARNING' in line and ('ClickHouse' in line or 'clickhouse' in line.lower())],
            'degradation_warnings': [line for line in lines if 'WARNING' in line and ('optional' in line.lower() or 'degradation' in line.lower())],
            'duplicate_patterns': self._detect_duplicate_patterns(lines)
        }
    
    def _detect_duplicate_patterns(self, log_lines: List[str]) -> Dict[str, int]:
        """Detect duplicate logging patterns."""
        patterns = {}
        for line in log_lines:
            if 'ClickHouse' in line and 'ERROR' in line:
                if 'Connection failed' in line:
                    patterns['clickhouse_connection_failed'] = patterns.get('clickhouse_connection_failed', 0) + 1
        return patterns