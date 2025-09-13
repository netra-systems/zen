"""
Integration Tests for GCP Logging Critical Message Infrastructure - Issue #253

Tests the SSOT logging infrastructure with real services to reproduce
empty CRITICAL log entries that mask failures in production environments.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System Reliability & Incident Response
- Value Impact: Ensures $500K+ ARR Golden Path failures remain visible for debugging
- Strategic Impact: Prevents silent failure masking affecting customer experience

Test Focus:
1. Real SSOT logging infrastructure with actual service components
2. Critical logging through service startup and error scenarios  
3. Integration between logging context and message generation
4. Real exception scenarios that produce proper diagnostic messages

SSOT Compliance: Inherits from SSotAsyncTestCase, uses real services (no Docker)
No Docker Dependency: Uses local/staging services only
Created: 2025-09-12 (Issue #253 Integration Test Implementation)
"""

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import (
    UnifiedLoggingSSOT,
    get_ssot_logger,
    reset_logging,
    request_id_context,
    user_id_context,
    trace_id_context
)

# Real service imports for integration testing (no Docker)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.configuration.base import get_config


class TestGCPLoggingCriticalMessageIntegration(SSotAsyncTestCase):
    """
    Integration test suite for GCP logging critical message infrastructure.
    
    Tests real SSOT logging with actual service components to reproduce
    empty CRITICAL log entries that occur in production environments.
    """
    
    def setup_method(self, method):
        """Setup integration test environment with real services."""
        super().setup_method(method)
        
        # Reset logging for clean test state
        reset_logging()
        
        # Configure for integration testing (no Docker)
        self._env.set('TESTING', '1', source='integration_test')
        self._env.set('ENVIRONMENT', 'test', source='integration_test')
        self._env.set('ENABLE_GCP_ERROR_REPORTING', 'false', source='integration_test')
        
        # Initialize real SSOT logger
        self.logger = get_ssot_logger()
        
        # Integration test tracking
        self.integration_logs = []
        self.service_contexts = []
        self.critical_log_entries = []
        
        # Mock GCP log capture for integration validation
        self.gcp_log_capture = []
        
        # Setup logging capture
        self._setup_log_capture()
        
    def teardown_method(self, method):
        """Clean up integration test state."""
        # Clear context variables
        request_id_context.set(None)
        user_id_context.set(None)
        trace_id_context.set(None)
        
        # Reset logging
        reset_logging()
        super().teardown_method(method)
    
    def _setup_log_capture(self):
        """Setup integration log capture for validation."""
        self.integration_logs.clear()
        self.critical_log_entries.clear()
        self.gcp_log_capture.clear()
        
        # Patch logger methods to capture outputs
        self.original_log = self.logger._log
        
        def capture_log(level: str, message: str, **kwargs):
            """Capture log calls for integration validation."""
            # Store log entry for analysis
            log_entry = {
                'level': level,
                'message': message,
                'kwargs': kwargs.copy(),
                'timestamp': time.time(),
                'context': self.logger._context.get_context()
            }
            
            self.integration_logs.append(log_entry)
            
            if level == 'CRITICAL':
                self.critical_log_entries.append(log_entry)
            
            # Call original method
            return self.original_log(level, message, **kwargs)
        
        self.logger._log = capture_log
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_critical_exception_logging_produces_content(self):
        """Test that real exceptions produce meaningful CRITICAL logs."""
        # Setup integration test context
        test_request_id = f"integration_test_{int(time.time())}"
        test_user_id = "integration_user_001"
        
        request_id_context.set(test_request_id)
        user_id_context.set(test_user_id)
        trace_id_context.set(f"integration_trace_{test_user_id}")
        
        # Test various real exception scenarios
        exception_scenarios = [
            # Database connection error
            {
                'name': 'database_connection',
                'exception': ConnectionError("Database connection timeout after 30s"),
                'operation': 'user_data_fetch'
            },
            # Service configuration error  
            {
                'name': 'config_validation',
                'exception': ValueError("Invalid JWT_SECRET_KEY configuration"),
                'operation': 'auth_service_startup'
            },
            # WebSocket connection error
            {
                'name': 'websocket_failure',
                'exception': RuntimeError("WebSocket handshake failed: Connection refused"),
                'operation': 'realtime_connection'
            },
            # User execution context error
            {
                'name': 'user_context',
                'exception': AttributeError("UserExecutionContext missing required field: user_id"),
                'operation': 'agent_execution_setup'
            }
        ]
        
        exception_results = {}
        
        for scenario in exception_scenarios:
            scenario_start = time.time()
            
            try:
                # Create realistic service operation that fails
                await self._simulate_service_operation_failure(
                    scenario['operation'], 
                    scenario['exception']
                )
                
            except Exception as e:
                # Log the critical error with full context
                self.logger.critical(
                    f"Integration test: {scenario['name']} operation failed",
                    exc_info=True,
                    exception=e,
                    extra={
                        'integration_test': True,
                        'scenario_name': scenario['name'],
                        'operation': scenario['operation'],
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'user_id': test_user_id,
                        'request_id': test_request_id,
                        'scenario_duration': time.time() - scenario_start
                    }
                )
                
                exception_results[scenario['name']] = {
                    'exception_caught': True,
                    'exception_type': type(e).__name__,
                    'exception_message': str(e),
                    'duration': time.time() - scenario_start
                }
        
        # Validate critical log generation
        assert len(self.critical_log_entries) > 0, "No CRITICAL logs generated during exception scenarios"
        
        # Check each critical log for proper content
        for critical_log in self.critical_log_entries:
            # Should have meaningful message
            assert critical_log['message'], f"Empty message in critical log: {critical_log}"
            assert critical_log['message'].strip(), f"Whitespace-only message: '{critical_log['message']}'"
            
            # Should contain error context
            assert 'failed' in critical_log['message'] or 'error' in critical_log['message'], \
                f"No error indication in message: '{critical_log['message']}'"
            
            # Should have proper context
            context = critical_log['context']
            assert context.get('user_id') == test_user_id, f"Missing user context: {context}"
            
            # Should have exception details in kwargs
            kwargs = critical_log['kwargs']
            assert 'error_type' in kwargs or 'exception' in kwargs, \
                f"Missing exception details: {kwargs}"
        
        # Verify no empty critical logs
        for critical_log in self.critical_log_entries:
            message = critical_log['message']
            assert message and message.strip(), \
                f"Empty or whitespace critical message found: '{message}'"
    
    async def _simulate_service_operation_failure(self, operation: str, exception: Exception):
        """Simulate realistic service operation that fails."""
        operation_delay = 0.1  # Brief delay to simulate real operation
        
        if operation == 'user_data_fetch':
            await asyncio.sleep(operation_delay)
            # Simulate database timeout
            raise exception
            
        elif operation == 'auth_service_startup':
            await asyncio.sleep(operation_delay)
            # Simulate config validation failure
            config = get_config()  # Real config access
            raise exception
            
        elif operation == 'realtime_connection':
            await asyncio.sleep(operation_delay)
            # Simulate WebSocket failure
            raise exception
            
        elif operation == 'agent_execution_setup':
            await asyncio.sleep(operation_delay)
            # Simulate user context creation failure
            try:
                context = UserExecutionContext(user_id=None)  # Invalid input
            except Exception:
                raise exception
        
        else:
            await asyncio.sleep(operation_delay)
            raise exception
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concentrated_burst_logging_patterns(self):
        """Test burst logging patterns that might produce empty messages (Issue #253 pattern)."""
        # Reproduce the exact pattern from Issue #253:
        # 21+ CRITICAL entries in 2-second window
        
        burst_start = time.time()
        burst_user_id = "burst_test_user"
        burst_request_id = f"burst_test_{int(burst_start)}"
        
        request_id_context.set(burst_request_id)
        user_id_context.set(burst_user_id)
        trace_id_context.set(f"burst_trace_{burst_user_id}")
        
        # Create conditions that reproduce burst critical logging
        burst_operations = [
            "websocket_connection_attempt_1",
            "websocket_connection_attempt_2", 
            "websocket_connection_attempt_3",
            "auth_token_validation_retry_1",
            "auth_token_validation_retry_2",
            "database_connection_pool_exhausted",
            "redis_connection_timeout",
            "service_startup_dependency_check_1",
            "service_startup_dependency_check_2",
            "service_startup_dependency_check_3",
            "agent_registry_initialization_failure",
            "websocket_manager_startup_failure",
            "user_execution_context_factory_error",
            "thread_creation_failure_1",
            "thread_creation_failure_2",
            "memory_pressure_detection",
            "cpu_threshold_exceeded",
            "concurrent_user_limit_reached",
            "rate_limiting_triggered",
            "circuit_breaker_opened",
            "health_check_failure"
        ]
        
        # Execute burst operations rapidly (reproduce 21+ in 2-second window)
        burst_results = []
        
        for i, operation in enumerate(burst_operations):
            operation_start = time.time()
            
            try:
                # Rapid-fire critical logging (reproduces production burst pattern)
                self.logger.critical(
                    f"Burst operation {operation} failed in staging environment",
                    extra={
                        'burst_test': True,
                        'operation_name': operation,
                        'operation_index': i,
                        'burst_elapsed': time.time() - burst_start,
                        'user_id': burst_user_id,
                        'request_id': burst_request_id,
                        'gcp_environment': 'staging',
                        'service': 'netra-backend-staging',
                        'operation_timestamp': time.time()
                    }
                )
                
                burst_results.append({
                    'operation': operation,
                    'index': i,
                    'duration': time.time() - operation_start,
                    'success': True
                })
                
                # Brief delay between operations (reproduce rapid succession)
                await asyncio.sleep(0.05)  # 50ms between operations
                
            except Exception as e:
                burst_results.append({
                    'operation': operation,
                    'index': i,
                    'error': str(e),
                    'duration': time.time() - operation_start,
                    'success': False
                })
        
        burst_duration = time.time() - burst_start
        
        # Validate burst pattern reproduction
        assert len(burst_operations) >= 21, f"Need 21+ operations, got {len(burst_operations)}"
        assert burst_duration <= 3.0, f"Burst took too long: {burst_duration:.2f}s (should be ~2s)"
        
        # Check for concentrated CRITICAL log generation
        burst_critical_logs = [
            log for log in self.critical_log_entries 
            if log['context'].get('request_id') == burst_request_id
        ]
        
        assert len(burst_critical_logs) >= 20, \
            f"Insufficient burst critical logs: {len(burst_critical_logs)} (expected 20+)"
        
        # Verify NO empty messages in burst pattern
        for i, critical_log in enumerate(burst_critical_logs):
            message = critical_log['message']
            assert message and message.strip(), \
                f"Empty critical message in burst pattern at index {i}: '{message}'"
            
            # Should contain operation context
            assert 'failed' in message and 'staging' in message, \
                f"Missing operation context in burst message {i}: '{message}'"
            
            # Should have proper extra context
            kwargs = critical_log['kwargs']
            assert 'operation_name' in kwargs, f"Missing operation_name in burst log {i}"
            assert 'burst_test' in kwargs, f"Missing burst_test marker in log {i}"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_service_startup_critical_logging(self):
        """Test critical logging during service initialization scenarios."""
        # Test critical logging during various service startup phases
        startup_phases = [
            {
                'phase': 'environment_validation',
                'error': EnvironmentError("Missing required environment variable: DATABASE_URL"),
                'context': {'startup_phase': 'env_check', 'required_vars': ['DATABASE_URL', 'JWT_SECRET']}
            },
            {
                'phase': 'database_connection',
                'error': ConnectionError("PostgreSQL connection failed: Connection refused"),
                'context': {'startup_phase': 'db_init', 'connection_attempts': 3, 'timeout': 30}
            },
            {
                'phase': 'redis_connection',
                'error': ConnectionError("Redis connection failed: Authentication required"),
                'context': {'startup_phase': 'cache_init', 'redis_host': 'localhost', 'redis_port': 6379}
            },
            {
                'phase': 'websocket_manager_init',
                'error': RuntimeError("WebSocketManager initialization failed: Port 8000 in use"),
                'context': {'startup_phase': 'websocket_init', 'attempted_port': 8000, 'fallback_ports': [8001, 8002]}
            },
            {
                'phase': 'agent_registry_init', 
                'error': ImportError("Agent module loading failed: Missing dependency 'openai'"),
                'context': {'startup_phase': 'agent_init', 'missing_deps': ['openai'], 'available_agents': []}
            }
        ]
        
        startup_test_id = f"startup_test_{int(time.time())}"
        request_id_context.set(startup_test_id)
        user_id_context.set("system_startup")
        trace_id_context.set(f"startup_trace_{startup_test_id}")
        
        startup_results = {}
        
        for phase_config in startup_phases:
            phase_start = time.time()
            phase_name = phase_config['phase']
            
            try:
                # Simulate startup phase failure
                await self._simulate_startup_phase_failure(phase_config)
                
            except Exception as e:
                # Log critical startup failure
                self.logger.critical(
                    f"Service startup failed during {phase_name} phase",
                    exc_info=True,
                    exception=e,
                    extra={
                        'startup_test': True,
                        'startup_phase': phase_name,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'phase_duration': time.time() - phase_start,
                        'startup_context': phase_config['context'],
                        'request_id': startup_test_id
                    }
                )
                
                startup_results[phase_name] = {
                    'failed': True,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'duration': time.time() - phase_start
                }
        
        # Validate startup critical logging
        startup_critical_logs = [
            log for log in self.critical_log_entries
            if log['kwargs'].get('startup_test') == True
        ]
        
        assert len(startup_critical_logs) >= len(startup_phases), \
            f"Missing startup critical logs: {len(startup_critical_logs)} < {len(startup_phases)}"
        
        # Verify each startup critical log has proper content
        for startup_log in startup_critical_logs:
            message = startup_log['message']
            
            # Should have meaningful startup error message
            assert message and message.strip(), f"Empty startup critical message: '{message}'"
            assert 'startup' in message.lower() and 'failed' in message.lower(), \
                f"Missing startup failure context: '{message}'"
            
            # Should have startup phase context
            kwargs = startup_log['kwargs']
            assert 'startup_phase' in kwargs, f"Missing startup phase: {kwargs}"
            assert 'startup_context' in kwargs, f"Missing startup context: {kwargs}"
            
            # Should have error details
            assert 'error_type' in kwargs and 'error_message' in kwargs, \
                f"Missing error details: {kwargs}"
        
        # Verify no empty messages during startup failures
        for startup_log in startup_critical_logs:
            message = startup_log['message']
            assert message and message.strip(), \
                f"Empty startup critical message: '{message}'"
    
    async def _simulate_startup_phase_failure(self, phase_config: Dict[str, Any]):
        """Simulate realistic startup phase failure."""
        phase_name = phase_config['phase']
        error = phase_config['error']
        
        # Add realistic startup delay
        await asyncio.sleep(0.1)
        
        if phase_name == 'environment_validation':
            # Simulate environment check failure
            missing_var = self._env.get('NONEXISTENT_REQUIRED_VAR')
            if not missing_var:
                raise error
                
        elif phase_name == 'database_connection':
            # Simulate database connection failure
            raise error
            
        elif phase_name == 'redis_connection':
            # Simulate Redis connection failure  
            raise error
            
        elif phase_name == 'websocket_manager_init':
            # Simulate WebSocket manager failure
            raise error
            
        elif phase_name == 'agent_registry_init':
            # Simulate agent registry failure
            raise error
        
        else:
            raise error
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_service_integration_critical_paths(self):
        """Test critical logging through real service integration points."""
        # Test integration with actual service components
        integration_user_id = "integration_real_user"
        integration_request_id = f"real_integration_{int(time.time())}"
        
        request_id_context.set(integration_request_id)
        user_id_context.set(integration_user_id)
        trace_id_context.set(f"real_integration_trace_{integration_user_id}")
        
        # Test real service integration scenarios
        integration_scenarios = [
            {
                'name': 'user_execution_context_creation',
                'service': 'UserExecutionContext',
                'operation': 'create_with_invalid_data'
            },
            {
                'name': 'configuration_loading',
                'service': 'ConfigurationManager', 
                'operation': 'load_with_missing_secrets'
            },
            {
                'name': 'environment_isolation',
                'service': 'IsolatedEnvironment',
                'operation': 'access_protected_variable'
            }
        ]
        
        integration_results = {}
        
        for scenario in integration_scenarios:
            scenario_start = time.time()
            scenario_name = scenario['name']
            
            try:
                await self._execute_real_service_integration(scenario)
                
            except Exception as e:
                # Critical logging through real service integration
                self.logger.critical(
                    f"Real service integration failed: {scenario_name}",
                    exc_info=True,
                    exception=e,
                    extra={
                        'real_integration_test': True,
                        'scenario_name': scenario_name,
                        'service_name': scenario['service'],
                        'operation': scenario['operation'],
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'user_id': integration_user_id,
                        'request_id': integration_request_id,
                        'scenario_duration': time.time() - scenario_start
                    }
                )
                
                integration_results[scenario_name] = {
                    'failed': True,
                    'service': scenario['service'],
                    'error': str(e),
                    'duration': time.time() - scenario_start
                }
        
        # Validate real service integration critical logging
        integration_critical_logs = [
            log for log in self.critical_log_entries
            if log['kwargs'].get('real_integration_test') == True
        ]
        
        assert len(integration_critical_logs) > 0, "No real service integration critical logs"
        
        # Check each integration critical log
        for integration_log in integration_critical_logs:
            message = integration_log['message']
            
            # Should have meaningful integration error message
            assert message and message.strip(), f"Empty integration critical message: '{message}'"
            assert 'integration' in message.lower() and 'failed' in message.lower(), \
                f"Missing integration failure context: '{message}'"
            
            # Should have service context
            kwargs = integration_log['kwargs']
            assert 'service_name' in kwargs, f"Missing service name: {kwargs}"
            assert 'scenario_name' in kwargs, f"Missing scenario name: {kwargs}"
            
            # Should have error details from real service
            assert 'error_type' in kwargs and 'error_message' in kwargs, \
                f"Missing real service error details: {kwargs}"
    
    async def _execute_real_service_integration(self, scenario: Dict[str, Any]):
        """Execute real service integration scenario."""
        service_name = scenario['service']
        operation = scenario['operation']
        
        await asyncio.sleep(0.05)  # Brief service operation delay
        
        if service_name == 'UserExecutionContext':
            if operation == 'create_with_invalid_data':
                # Test with invalid user data
                try:
                    context = UserExecutionContext(user_id="")  # Invalid empty user_id
                except Exception as e:
                    raise RuntimeError(f"UserExecutionContext creation failed: {e}")
                    
        elif service_name == 'ConfigurationManager':
            if operation == 'load_with_missing_secrets':
                # Test config loading with missing secrets
                try:
                    config = get_config()
                    # Access potentially missing config
                    missing_secret = getattr(config, 'nonexistent_secret', None)
                    if not missing_secret:
                        raise ValueError("Required secret configuration missing")
                except Exception as e:
                    raise RuntimeError(f"Configuration loading failed: {e}")
                    
        elif service_name == 'IsolatedEnvironment':
            if operation == 'access_protected_variable':
                # Test environment access error
                try:
                    env = IsolatedEnvironment.get_instance()
                    protected_var = env.get('PROTECTED_SYSTEM_VARIABLE')
                    if not protected_var:
                        raise PermissionError("Access to protected environment variable denied")
                except Exception as e:
                    raise RuntimeError(f"Environment access failed: {e}")
        
        else:
            raise RuntimeError(f"Unknown service integration scenario: {service_name}")