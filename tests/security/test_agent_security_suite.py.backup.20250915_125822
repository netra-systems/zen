"""Comprehensive security test suite for agent execution protection.

This test suite validates all security mechanisms implemented to prevent
agent death, resource exhaustion, and DoS attacks as described in
AGENT_DEATH_AFTER_TRIAGE_BUG_REPORT.md

Test Categories:
1. Timeout enforcement and detection
2. Resource protection (memory, CPU, concurrency)
3. Circuit breaker functionality
4. Error boundary validation
5. Silent failure detection
6. Recovery and cleanup mechanisms
"""
import asyncio
import pytest
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.agents.security import ResourceGuard, ResourceLimits, SecurityManager, SecurityConfig, SystemCircuitBreaker, CircuitBreakerConfig, FailureType
from netra_backend.app.agents.security.security_manager import ExecutionRequest, ExecutionPermission
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

class TestTimeoutEnforcement:
    """Test timeout enforcement and detection mechanisms."""

    @pytest.fixture
    def security_manager(self):
        """Create security manager with short timeouts for testing."""
        config = SecurityConfig(default_timeout_seconds=1.0, max_timeout_seconds=2.0, enable_timeout_protection=True)
        return SecurityManager(config)

    @pytest.mark.asyncio
    async def test_timeout_enforcement_prevents_hanging(self, security_manager):
        """Test that timeouts prevent agents from hanging indefinitely."""
        request = ExecutionRequest(agent_name='test_agent', user_id='test_user', estimated_memory_mb=0)
        permission = await security_manager.validate_execution_request(request)
        assert permission.allowed is True
        assert permission.timeout_seconds == 1.0
        start_time = time.time()
        try:
            async with asyncio.timeout(permission.timeout_seconds):
                await asyncio.sleep(2.0)
            assert False, 'Timeout did not trigger'
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            assert elapsed < 1.5
            await security_manager.record_execution_result(request, permission, False, 'Timeout occurred', elapsed, 0)

    @pytest.mark.asyncio
    async def test_timeout_detection_triggers_circuit_breaker(self, security_manager):
        """Test that repeated timeouts trigger circuit breaker."""
        request = ExecutionRequest(agent_name='timeout_agent', user_id='test_user')
        for i in range(4):
            permission = await security_manager.validate_execution_request(request)
            if i < 3:
                assert permission.allowed is True
            await security_manager.record_execution_result(request, permission, False, 'Execution timeout', 1.0, 0)
        permission = await security_manager.validate_execution_request(request)
        assert permission.allowed is False
        assert 'unavailable' in permission.reason.lower()

    @pytest.mark.asyncio
    async def test_timeout_cleanup_prevents_resource_leaks(self, security_manager):
        """Test that timeouts properly clean up resources."""
        initial_status = await security_manager.get_security_status()
        initial_concurrent = initial_status['manager']['total_requests']
        request = ExecutionRequest(agent_name='cleanup_test', user_id='test_user')
        permission = await security_manager.validate_execution_request(request)
        await security_manager.acquire_execution_resources(request, permission)
        await security_manager.record_execution_result(request, permission, False, 'Timeout', 1.0, 0)
        final_status = await security_manager.get_security_status()
        if 'resource_guard' in final_status:
            resource_status = final_status['resource_guard']
            assert resource_status['current_usage']['concurrent_executions'] == 0

class TestResourceProtection:
    """Test resource protection mechanisms."""

    @pytest.fixture
    def resource_guard(self):
        """Create resource guard with low limits for testing."""
        limits = ResourceLimits(max_memory_mb=100, max_concurrent_per_user=2, max_concurrent_global=5, rate_limit_per_minute=10)
        return ResourceGuard(limits)

    @pytest.mark.asyncio
    async def test_concurrent_execution_limits_enforced(self, resource_guard):
        """Test that concurrent execution limits prevent overload."""
        user_id = 'test_user'
        for i in range(2):
            can_acquire = await resource_guard.acquire_resources(user_id, 0)
            assert can_acquire is True
        validation_error = await resource_guard.validate_resource_request(user_id, 0)
        assert validation_error is not None
        assert 'concurrent execution limit exceeded' in validation_error.lower()

    @pytest.mark.asyncio
    async def test_rate_limiting_prevents_abuse(self, resource_guard):
        """Test that rate limiting prevents request flooding."""
        user_id = 'flood_user'
        for i in range(10):
            validation_error = await resource_guard.validate_resource_request(user_id, 0)
            if i < 9:
                assert validation_error is None
            else:
                assert validation_error is not None
                assert 'rate limit exceeded' in validation_error.lower()

    @pytest.mark.asyncio
    async def test_memory_constraints_prevent_oom(self, resource_guard):
        """Test that memory constraints prevent out-of-memory conditions."""
        user_id = 'memory_user'
        validation_error = await resource_guard.validate_resource_request(user_id, 200)
        assert validation_error is not None
        assert 'insufficient memory' in validation_error.lower()

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_execution_end(self, resource_guard):
        """Test that resources are properly cleaned up."""
        user_id = 'cleanup_user'
        await resource_guard.acquire_resources(user_id, 10)
        status = await resource_guard.get_resource_status()
        assert status['user_stats']['total_concurrent'] > 0
        await resource_guard.release_resources(user_id)
        status = await resource_guard.get_resource_status()
        assert status['user_stats']['total_concurrent'] == 0

class TestCircuitBreakerFunctionality:
    """Test circuit breaker failure detection and recovery."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker with low thresholds for testing."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1, success_threshold=1)
        return SystemCircuitBreaker(config)

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test that circuit breaker opens after repeated failures."""
        agent_name = 'failing_agent'
        can_execute, fallback = await circuit_breaker.can_execute_agent(agent_name)
        assert can_execute is True
        assert fallback is None
        for i in range(2):
            await circuit_breaker.record_execution_result(agent_name, False, FailureType.EXCEPTION, f'Error {i}', 'user1')
        can_execute, fallback = await circuit_breaker.can_execute_agent(agent_name)
        assert can_execute is False

    @pytest.mark.asyncio
    async def test_circuit_provides_fallback_agents(self, circuit_breaker):
        """Test that circuit breaker provides fallback agents."""
        await circuit_breaker.add_fallback_agent('data', 'triage')
        for i in range(2):
            await circuit_breaker.record_execution_result('data', False, FailureType.TIMEOUT, 'Timeout', 'user1')
        can_execute, fallback = await circuit_breaker.can_execute_agent('data')
        assert fallback == 'triage'

    @pytest.mark.asyncio
    async def test_circuit_recovery_after_success(self, circuit_breaker):
        """Test that circuit breaker recovers after successful executions."""
        agent_name = 'recovery_agent'
        for i in range(2):
            await circuit_breaker.record_execution_result(agent_name, False, FailureType.EXCEPTION, 'Error', 'user1')
        await asyncio.sleep(1.1)
        can_execute, _ = await circuit_breaker.can_execute_agent(agent_name)
        assert can_execute is True
        await circuit_breaker.record_execution_result(agent_name, True, None, '', 'user1')
        status = await circuit_breaker.get_system_status()
        agent_status = status['agents'][agent_name]
        assert agent_status['state'] == 'closed'

class TestErrorBoundaryValidation:
    """Test error boundaries that prevent silent failures."""

    @pytest.fixture
    def execution_engine(self):
        """Create execution engine for testing."""
        return UnifiedToolExecutionEngine()

    @pytest.mark.asyncio
    async def test_silent_failure_detection(self, execution_engine):
        """Test that silent failures (None results) are detected."""

        class SilentFailureTool:

            def arun(self, kwargs):
                return None
        tool = SilentFailureTool()
        kwargs = {}
        with pytest.raises(ValueError) as exc_info:
            await execution_engine._run_tool_by_interface_safe(tool, kwargs)
        assert 'returned no result' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_placeholder_result_detection(self, execution_engine):
        """Test detection of placeholder results that indicate failure."""

        class PlaceholderTool:

            def arun(self, kwargs):
                return '...'
        tool = PlaceholderTool()
        kwargs = {}
        with pytest.raises(ValueError) as exc_info:
            await execution_engine._run_tool_by_interface_safe(tool, kwargs)
        assert 'failed silently' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exception_propagation(self, execution_engine):
        """Test that exceptions are properly propagated, not silenced."""

        class ExceptionTool:

            def arun(self, kwargs):
                raise RuntimeError('Tool error')
        tool = ExceptionTool()
        kwargs = {}
        with pytest.raises(RuntimeError) as exc_info:
            await execution_engine._run_tool_by_interface_safe(tool, kwargs)
        assert 'Tool error' in str(exc_info.value)

class TestHealthCheckCapability:
    """Test health check capability detection."""

    @pytest.mark.asyncio
    async def test_health_check_detects_processing_capability(self):
        """Test that health checks verify actual processing capability."""
        execution_engine = UnifiedToolExecutionEngine()
        health_status = await execution_engine.health_check()
        assert 'can_process_agents' in health_status
        assert health_status['can_process_agents'] is True
        assert 'processing_capability_verified' in health_status

    @pytest.mark.asyncio
    async def test_health_check_detects_stuck_executions(self):
        """Test that health checks detect stuck executions."""
        execution_engine = UnifiedToolExecutionEngine()
        execution_id = 'stuck_test'
        execution_engine._active_executions[execution_id] = {'tool_name': 'stuck_tool', 'start_time': time.time() - 120, 'user_id': 'test_user'}
        health_status = await execution_engine.health_check()
        assert 'stuck executions detected' in str(health_status.get('issues', []))

class TestEmergencyRecovery:
    """Test emergency recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_emergency_shutdown_cleans_all_resources(self):
        """Test that emergency shutdown properly cleans all resources."""
        config = SecurityConfig()
        security_manager = SecurityManager(config)
        request = ExecutionRequest('test_agent', 'user1')
        permission = await security_manager.validate_execution_request(request)
        await security_manager.acquire_execution_resources(request, permission)
        shutdown_stats = await security_manager.emergency_shutdown('test')
        assert 'timestamp' in shutdown_stats
        assert shutdown_stats['reason'] == 'test'
        status = await security_manager.get_security_status()
        assert status['manager']['emergency_shutdowns'] > 0

    @pytest.mark.asyncio
    async def test_user_specific_cleanup(self):
        """Test cleanup of resources for specific users."""
        execution_engine = UnifiedToolExecutionEngine()
        user_id = 'stuck_user'
        execution_id = 'stuck_execution'
        execution_engine._active_executions[execution_id] = {'tool_name': 'stuck_tool', 'start_time': time.time() - 200, 'user_id': user_id}
        execution_engine._user_execution_counts[user_id] = 1
        cleanup_count = await execution_engine.force_cleanup_user_executions(user_id)
        assert cleanup_count > 0
        assert user_id not in execution_engine._user_execution_counts
        assert execution_id not in execution_engine._active_executions

class TestSecurityIntegration:
    """Test integration of all security components."""

    @pytest.mark.asyncio
    async def test_end_to_end_security_protection(self):
        """Test complete security protection flow."""
        config = SecurityConfig(max_concurrent_per_user=1, rate_limit_per_minute=5, default_timeout_seconds=1.0, failure_threshold=2)
        security_manager = SecurityManager(config)
        user_id = 'e2e_user'
        request1 = ExecutionRequest('test_agent', user_id)
        permission1 = await security_manager.validate_execution_request(request1)
        assert permission1.allowed is True
        await security_manager.acquire_execution_resources(request1, permission1)
        request2 = ExecutionRequest('test_agent', user_id)
        permission2 = await security_manager.validate_execution_request(request2)
        assert permission2.allowed is False
        assert 'concurrent' in permission2.reason.lower()
        await security_manager.record_execution_result(request1, permission1, True, '', 0.5, 0)
        request3 = ExecutionRequest('test_agent', user_id)
        permission3 = await security_manager.validate_execution_request(request3)
        assert permission3.allowed is True

    @pytest.mark.asyncio
    async def test_security_metrics_collection(self):
        """Test that security metrics are properly collected."""
        security_manager = SecurityManager()
        request = ExecutionRequest('metrics_agent', 'metrics_user')
        permission = await security_manager.validate_execution_request(request)
        if permission.allowed:
            await security_manager.acquire_execution_resources(request, permission)
            await security_manager.record_execution_result(request, permission, True, '', 1.0, 0)
        metrics = await security_manager.get_security_metrics()
        assert 'timestamp' in metrics
        assert 'requests_per_second' in metrics
        assert 'block_rate_percent' in metrics
        assert 'components' in metrics

    @pytest.mark.asyncio
    async def test_security_status_reporting(self):
        """Test comprehensive security status reporting."""
        security_manager = SecurityManager()
        status = await security_manager.get_security_status()
        assert 'manager' in status
        assert 'config' in status
        manager_stats = status['manager']
        assert 'total_requests' in manager_stats
        assert 'blocked_requests' in manager_stats
        assert 'security_violations' in manager_stats
        config = status['config']
        assert 'resource_protection_enabled' in config
        assert 'circuit_breaker_enabled' in config
        assert 'timeout_protection_enabled' in config
pytestmark = [pytest.mark.security, pytest.mark.asyncio]
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')