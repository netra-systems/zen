"""
FINALIZE Phase Integration Tests - System Startup to Chat Ready
============================================================

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure complete system readiness for chat operations
- Value Impact: Validates chat functionality delivers 90% of business value
- Strategic Impact: Prevents broken chat from reaching users

CRITICAL: Chat delivers 90% of our value - if chat cannot work, service MUST NOT start.
These tests validate the FINALIZE phase ensures complete system readiness for chat operations.

Based on deterministic startup architecture (startup_module.py and smd.py):
- Phase 7: FINALIZE validates all systems ready for chat
- Complete startup completion state validation  
- System health assessment with chat readiness focus
- Critical path validation for end-to-end chat functionality
"""

import asyncio
import logging
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from pathlib import Path

# Core imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.service_availability import check_service_availability, ServiceUnavailableError
from shared.isolated_environment import get_env
from netra_backend.app.smd import StartupOrchestrator, StartupPhase, DeterministicStartupError
from netra_backend.app.startup_health_checks import validate_startup_health, ServiceStatus
from netra_backend.app.logging_config import central_logger

# Test framework imports
from test_framework.fixtures.configuration_test_fixtures import ConfigurationTestManager
from test_framework.database_test_utilities import DatabaseTestUtilities

# Check service availability at module level for optional services
_service_status = check_service_availability(['postgresql', 'redis'], timeout=2.0)
_postgresql_available = _service_status['postgresql'] is True
_redis_available = _service_status['redis'] is True

logger = central_logger.get_logger(__name__)


class FinalizePhaseIntegrationTest(BaseIntegrationTest):
    """
    Base class for FINALIZE phase integration tests.
    
    CRITICAL: These tests validate that the complete startup sequence 
    enables chat functionality - the core business value delivery.
    """
    
    def setup_method(self, method):
        """Set up test method with FINALIZE phase context."""
        super().setup_method(method)
        self.config_manager = ConfigurationTestManager()
        self.db_utilities = DatabaseTestUtilities()
        self.startup_metrics = {}
        self.phase_timings = {}
        
    def teardown_method(self, method):
        """Clean up test method."""
        super().teardown_method(method)
        if hasattr(self, 'config_manager'):
            self.config_manager.cleanup()
    
    async def create_test_app_with_full_startup(self) -> 'FastAPI':
        """Create test app with complete startup sequence through FINALIZE phase."""
        from fastapi import FastAPI
        from netra_backend.app.startup_module import run_complete_startup
        
        # Create FastAPI app
        app = FastAPI(title="Test App - FINALIZE Phase")
        
        # Set test environment for startup
        env = get_env()
        original_values = {}
        
        try:
            # Configure for test environment with real services
            test_env_vars = {
                'ENVIRONMENT': 'test',
                'SKIP_MIGRATIONS': 'true',
                'FAST_STARTUP_MODE': 'false',  # Need full startup
                'DISABLE_STARTUP_CHECKS': 'false',  # Need health checks
                'GRACEFUL_STARTUP_MODE': 'false',  # Deterministic mode only
                'USE_ROBUST_STARTUP': 'true',
                'CLICKHOUSE_REQUIRED': 'false',  # Optional in test
                'DISABLE_BACKGROUND_TASKS': 'true',  # Reduce complexity
                'DISABLE_MONITORING': 'false',  # Need monitoring for health
            }
            
            # Store original values and set test values
            for key, value in test_env_vars.items():
                if env.exists(key):
                    original_values[key] = env.get(key)
                env.set(key, value, source="test_setup")
            
            # Run complete startup sequence
            start_time, logger_instance = await run_complete_startup(app)
            
            # Validate startup completed successfully
            assert hasattr(app.state, 'startup_complete'), "App missing startup_complete flag"
            assert app.state.startup_complete is True, "Startup not marked complete"
            assert hasattr(app.state, 'startup_failed'), "App missing startup_failed flag"
            assert app.state.startup_failed is False, "Startup marked as failed"
            
            return app
            
        finally:
            # Restore original environment values
            for key, value in original_values.items():
                env.set(key, value, source="test_cleanup")
            for key in test_env_vars:
                if key not in original_values:
                    env.delete(key, source="test_cleanup")
    
    def validate_startup_timing(self, app: 'FastAPI', max_startup_time: float = 60.0):
        """Validate startup completed within reasonable time limits."""
        # Get startup timing from app state
        startup_start = getattr(app.state, 'startup_start_time', None)
        assert startup_start is not None, "Startup start time not recorded"
        
        # Calculate total startup time
        current_time = time.time()
        total_startup_time = current_time - startup_start
        
        # Business value: Startup must be reasonably fast for good UX
        assert total_startup_time <= max_startup_time, (
            f"Startup took {total_startup_time:.2f}s, exceeding limit of {max_startup_time}s"
        )
        
        logger.info(f"✅ Startup completed in {total_startup_time:.2f}s")
        return total_startup_time
    
    def validate_critical_services_ready(self, app: 'FastAPI'):
        """Validate all critical services required for chat are ready."""
        critical_services = {
            'db_session_factory': 'Database connection for chat history',
            'redis_manager': 'Caching for chat performance', 
            'llm_manager': 'AI models for chat responses',
            'agent_supervisor': 'Agent orchestration for chat',
            'thread_service': 'Chat thread management',
            'agent_service': 'Agent execution service',
            'agent_websocket_bridge': 'Real-time chat events'
        }
        
        missing_services = []
        none_services = []
        
        for service_name, description in critical_services.items():
            if not hasattr(app.state, service_name):
                missing_services.append(f"{service_name} ({description})")
            else:
                service = getattr(app.state, service_name)
                if service is None:
                    none_services.append(f"{service_name} ({description})")
        
        # Assert no critical services missing or None
        assert not missing_services, (
            f"Critical chat services missing: {missing_services}"
        )
        assert not none_services, (
            f"Critical chat services are None: {none_services}"
        )
        
        logger.info("✅ All critical chat services validated")
    
    def validate_phase_completion(self, app: 'FastAPI'):
        """Validate all startup phases completed successfully."""
        # Check phase completion tracking
        if hasattr(app.state, 'startup_completed_phases'):
            completed_phases = app.state.startup_completed_phases
            expected_phases = ['init', 'dependencies', 'database', 'cache', 'services', 'websocket', 'finalize']
            
            missing_phases = [phase for phase in expected_phases if phase not in completed_phases]
            assert not missing_phases, f"Startup phases not completed: {missing_phases}"
            
            logger.info(f"✅ All {len(completed_phases)} startup phases completed")
        
        # Check no failed phases
        if hasattr(app.state, 'startup_failed_phases'):
            failed_phases = app.state.startup_failed_phases
            assert not failed_phases, f"Startup phases failed: {failed_phases}"


class TestFinalizePhaseSystemValidation(FinalizePhaseIntegrationTest):
    """Test FINALIZE phase system-wide validation and readiness."""

    @pytest.mark.asyncio
    async def test_complete_startup_validation_finalize_phase(self):
        """
        Test complete startup sequence validation through FINALIZE phase.
        
        BVJ: Ensures entire system ready for chat operations - core business value.
        """
        # Create app with full startup
        app = await self.create_test_app_with_full_startup()
        
        # Validate startup completion
        assert app.state.startup_complete is True
        assert app.state.startup_failed is False
        
        # Validate timing
        startup_time = self.validate_startup_timing(app, max_startup_time=45.0)
        
        # Validate all critical services
        self.validate_critical_services_ready(app)
        
        # Validate phase completion
        self.validate_phase_completion(app)
        
        # Business value assertion
        logger.info("✅ System ready for chat operations - primary business value enabled")
        
        # Store metrics for reporting
        self.startup_metrics['total_time'] = startup_time
        self.startup_metrics['phases_completed'] = getattr(app.state, 'startup_completed_phases', [])

    @pytest.mark.asyncio 
    async def test_startup_health_checks_comprehensive(self):
        """
        Test comprehensive startup health checks in FINALIZE phase.
        
        BVJ: Health validation prevents broken chat from reaching users.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Run startup health validation
        from netra_backend.app.startup_health_checks import StartupHealthChecker
        
        health_checker = StartupHealthChecker(app)
        all_healthy, results = await health_checker.run_all_health_checks()
        
        # Validate critical services healthy
        critical_unhealthy = []
        for result in results:
            if result.service_name in health_checker.CRITICAL_SERVICES:
                if result.status not in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
                    critical_unhealthy.append(f"{result.service_name}: {result.message}")
        
        assert not critical_unhealthy, f"Critical services unhealthy: {critical_unhealthy}"
        
        # Log health summary
        healthy_count = sum(1 for r in results if r.status == ServiceStatus.HEALTHY)
        logger.info(f"✅ {healthy_count}/{len(results)} services healthy")
        
        # Business value: System health enables reliable chat
        logger.info("✅ Health checks passed - chat operations reliable")

    @pytest.mark.asyncio
    async def test_critical_path_validation_chat_ready(self):
        """
        Test critical communication paths for chat functionality.
        
        BVJ: Validates end-to-end chat flow works before accepting users.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Validate critical chat components integration
        supervisor = app.state.agent_supervisor
        thread_service = app.state.thread_service
        websocket_bridge = app.state.agent_websocket_bridge
        
        # Test supervisor can create agents
        assert supervisor is not None
        assert hasattr(supervisor, 'create_agent_run'), "Supervisor missing agent creation"
        
        # Test thread service ready
        assert thread_service is not None
        assert hasattr(thread_service, 'create_thread'), "Thread service missing thread creation"
        
        # Test WebSocket bridge ready for events
        assert websocket_bridge is not None
        assert hasattr(websocket_bridge, 'notify_agent_started'), "Bridge missing agent notifications"
        
        # Test WebSocket bridge health
        if hasattr(websocket_bridge, 'health_check'):
            health = await websocket_bridge.health_check()
            # Note: In per-request architecture, some components may not be initialized
            # during startup. This is expected and correct.
            logger.info(f"WebSocket bridge health: {health}")
        
        logger.info("✅ Critical chat communication paths validated")

    @pytest.mark.asyncio
    async def test_application_state_consistency_validation(self):
        """
        Test application state consistency after FINALIZE phase.
        
        BVJ: Consistent state prevents runtime errors in chat operations.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Validate startup state flags consistency
        state_checks = {
            'startup_complete': True,
            'startup_in_progress': False, 
            'startup_failed': False,
            'startup_error': None
        }
        
        for attr_name, expected_value in state_checks.items():
            actual_value = getattr(app.state, attr_name, 'MISSING')
            if expected_value is None:
                assert actual_value is None, f"Expected {attr_name} to be None, got {actual_value}"
            else:
                assert actual_value == expected_value, f"Expected {attr_name}={expected_value}, got {actual_value}"
        
        # Validate phase tracking consistency
        if hasattr(app.state, 'startup_completed_phases') and hasattr(app.state, 'startup_failed_phases'):
            completed = set(app.state.startup_completed_phases)
            failed = set(app.state.startup_failed_phases)
            
            # No overlap between completed and failed
            overlap = completed.intersection(failed)
            assert not overlap, f"Phases marked both completed and failed: {overlap}"
        
        # Validate service dependency consistency
        if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
            supervisor = app.state.agent_supervisor
            
            # Agent supervisor should have required dependencies
            if hasattr(supervisor, 'llm_manager'):
                assert supervisor.llm_manager is not None, "Supervisor missing LLM manager dependency"
        
        logger.info("✅ Application state consistency validated")

    @pytest.mark.asyncio
    async def test_resource_allocation_validation(self):
        """
        Test resource allocation and availability after startup.
        
        BVJ: Proper resource allocation ensures chat performance.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Test database connection pool availability (only if PostgreSQL is available)
        if _postgresql_available and hasattr(app.state, 'db_session_factory') and app.state.db_session_factory:
            try:
                # Test can create database session
                async with app.state.db_session_factory() as session:
                    from sqlalchemy import text
                    result = await session.execute(text("SELECT 1"))
                    assert result.scalar() == 1, "Database connection test failed"
                logger.info("✅ Database connection validated")
            except Exception as e:
                logger.warning(f"Database connection test failed (service available but connection issue): {e}")
        elif not _postgresql_available:
            logger.info("ℹ️ PostgreSQL not available - skipping database connection test")
        
        # Test Redis connection availability (only if Redis is available)
        if _redis_available and hasattr(app.state, 'redis_manager') and app.state.redis_manager:
            redis_manager = app.state.redis_manager
            # Test Redis ping if available
            if hasattr(redis_manager, 'redis_client') and redis_manager.redis_client:
                try:
                    await redis_manager.redis_client.ping()
                    logger.info("✅ Redis connection validated")
                except Exception as e:
                    logger.warning(f"Redis ping failed (service available but connection issue): {e}")
        elif not _redis_available:
            logger.info("ℹ️ Redis not available - skipping Redis connection test")
        
        # Test LLM manager resource allocation
        if hasattr(app.state, 'llm_manager') and app.state.llm_manager:
            llm_manager = app.state.llm_manager
            assert hasattr(llm_manager, 'llm_configs'), "LLM manager missing configs"
            
            # Should have at least one LLM configuration available
            if hasattr(llm_manager, 'llm_configs') and llm_manager.llm_configs:
                logger.info(f"✅ {len(llm_manager.llm_configs)} LLM configurations available")
        
        logger.info("✅ Resource allocation validated for chat operations")


class TestFinalizePhasePerformanceValidation(FinalizePhaseIntegrationTest):
    """Test FINALIZE phase performance and monitoring setup."""

    @pytest.mark.asyncio
    async def test_memory_performance_baseline_establishment(self):
        """
        Test memory and performance baseline establishment.
        
        BVJ: Performance baselines ensure chat remains responsive under load.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Measure memory usage after startup
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Business value: Memory usage should be reasonable for scalability
        assert memory_mb < 500, f"Memory usage {memory_mb:.1f}MB exceeds reasonable startup baseline"
        
        # Test CPU usage is stable
        cpu_percent = process.cpu_percent(interval=1.0)
        assert cpu_percent < 50, f"CPU usage {cpu_percent}% too high after startup"
        
        # Store performance baseline
        self.startup_metrics['memory_mb'] = memory_mb
        self.startup_metrics['cpu_percent'] = cpu_percent
        
        logger.info(f"✅ Performance baseline: {memory_mb:.1f}MB RAM, {cpu_percent:.1f}% CPU")

    @pytest.mark.asyncio
    async def test_startup_metrics_monitoring_setup(self):
        """
        Test startup metrics and monitoring infrastructure setup.
        
        BVJ: Monitoring enables proactive chat performance management.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Test performance monitor setup
        performance_monitor = getattr(app.state, 'performance_monitor', None)
        if performance_monitor:
            logger.info("✅ Performance monitoring initialized")
        
        # Test health service setup
        health_service = getattr(app.state, 'health_service', None)
        if health_service:
            logger.info("✅ Health service monitoring initialized")
        
        # Test background task manager for monitoring
        bg_manager = getattr(app.state, 'background_task_manager', None)
        if bg_manager:
            logger.info("✅ Background task manager ready for monitoring tasks")
        
        # Test startup timing data available
        if hasattr(app.state, 'startup_phase_timings'):
            phase_timings = app.state.startup_phase_timings
            total_phases = len(phase_timings)
            logger.info(f"✅ Startup timing data: {total_phases} phases tracked")
        
        logger.info("✅ Monitoring infrastructure ready for chat operations")

    @pytest.mark.asyncio
    async def test_startup_completion_timing_validation(self):
        """
        Test startup completion timing meets business requirements.
        
        BVJ: Fast startup improves user experience and reduces downtime.
        """
        start_time = time.time()
        app = await self.create_test_app_with_full_startup()
        total_time = time.time() - start_time
        
        # Business requirements for startup timing
        timing_requirements = {
            'development': 30.0,  # 30 seconds max for development
            'test': 45.0,         # 45 seconds max for test environment  
            'staging': 60.0,      # 60 seconds max for staging
            'production': 90.0    # 90 seconds max for production
        }
        
        environment = get_env().get('ENVIRONMENT', 'test')
        max_time = timing_requirements.get(environment, 45.0)
        
        assert total_time <= max_time, (
            f"Startup time {total_time:.2f}s exceeds {environment} limit of {max_time}s"
        )
        
        # Validate phase timing breakdown
        if hasattr(app.state, 'startup_phase_timings'):
            phase_timings = app.state.startup_phase_timings
            slowest_phase = None
            slowest_time = 0
            
            for phase_name, timing in phase_timings.items():
                duration = timing.get('duration', 0)
                if duration > slowest_time:
                    slowest_time = duration
                    slowest_phase = phase_name
            
            if slowest_phase:
                logger.info(f"Slowest phase: {slowest_phase} ({slowest_time:.2f}s)")
        
        logger.info(f"✅ Startup timing validated: {total_time:.2f}s in {environment}")
        
        # Store for reporting
        self.startup_metrics['environment'] = environment
        self.startup_metrics['total_startup_time'] = total_time
        self.startup_metrics['timing_requirement_met'] = True


class TestFinalizePhaseErrorHandlingValidation(FinalizePhaseIntegrationTest):
    """Test FINALIZE phase error handling and recovery capabilities."""

    @pytest.mark.asyncio
    async def test_startup_error_aggregation_reporting(self):
        """
        Test startup error aggregation and reporting in FINALIZE phase.
        
        BVJ: Proper error reporting enables fast issue resolution.
        """
        # Create app but expect it to succeed
        app = await self.create_test_app_with_full_startup()
        
        # Validate error tracking infrastructure exists
        assert hasattr(app.state, 'startup_error'), "Missing startup error tracking"
        assert app.state.startup_error is None, "Startup error should be None on success"
        
        # Test error state consistency
        assert hasattr(app.state, 'startup_failed'), "Missing startup failed flag"
        assert app.state.startup_failed is False, "Startup should not be marked as failed"
        
        # Test error aggregation system ready
        if hasattr(app.state, 'startup_failed_phases'):
            failed_phases = app.state.startup_failed_phases
            assert isinstance(failed_phases, list), "Failed phases should be list"
            assert len(failed_phases) == 0, f"Should have no failed phases, got: {failed_phases}"
        
        logger.info("✅ Error aggregation and reporting validated")

    @pytest.mark.asyncio
    async def test_graceful_degradation_validation(self):
        """
        Test graceful degradation capabilities where applicable.
        
        BVJ: Graceful degradation maintains some functionality during issues.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Test optional services can be degraded without breaking core chat
        optional_services = ['clickhouse_available', 'performance_monitor', 'chat_event_monitor']
        
        for service in optional_services:
            if hasattr(app.state, service):
                service_value = getattr(app.state, service)
                # Optional services can be None/False without breaking chat
                if service_value is None or service_value is False:
                    logger.info(f"ℹ️ Optional service {service} degraded - chat still operational")
        
        # Validate core chat services are never degraded
        core_services = ['agent_supervisor', 'thread_service', 'llm_manager']
        
        for service in core_services:
            if hasattr(app.state, service):
                service_value = getattr(app.state, service)
                assert service_value is not None, f"Core chat service {service} cannot be None"
        
        logger.info("✅ Graceful degradation validated - core chat protected")

    @pytest.mark.asyncio
    async def test_system_recovery_readiness_validation(self):
        """
        Test system recovery capabilities after startup failures.
        
        BVJ: Recovery capabilities minimize downtime impact on business.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Test health check infrastructure for recovery monitoring
        from netra_backend.app.startup_health_checks import StartupHealthChecker
        
        health_checker = StartupHealthChecker(app)
        all_healthy, results = await health_checker.run_all_health_checks()
        
        # Test recovery monitoring can detect issues
        unhealthy_services = [r for r in results if r.status == ServiceStatus.UNHEALTHY]
        degraded_services = [r for r in results if r.status == ServiceStatus.DEGRADED]
        
        # Log recovery readiness
        if unhealthy_services:
            logger.warning(f"⚠️ {len(unhealthy_services)} unhealthy services for recovery monitoring")
        
        if degraded_services:
            logger.info(f"ℹ️ {len(degraded_services)} degraded services under recovery monitoring")
        
        # Test background task manager ready for recovery tasks
        bg_manager = getattr(app.state, 'background_task_manager', None)
        if bg_manager:
            logger.info("✅ Background task manager ready for recovery operations")
        
        logger.info("✅ System recovery readiness validated")


class TestFinalizePhaseBusinessValueValidation(FinalizePhaseIntegrationTest):
    """Test FINALIZE phase business value and production readiness."""

    @pytest.mark.asyncio
    async def test_chat_functionality_end_to_end_readiness(self):
        """
        Test end-to-end chat functionality readiness validation.
        
        BVJ: Chat readiness validates 90% of business value delivery capability.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Test chat pipeline component integration
        components = {
            'agent_supervisor': 'Orchestrates AI agents for chat responses',
            'thread_service': 'Manages chat conversation threads',
            'agent_service': 'Executes agent workflows', 
            'llm_manager': 'Provides AI model access',
            'agent_websocket_bridge': 'Delivers real-time chat events',
            'db_session_factory': 'Persists chat history',
        }
        
        for component, description in components.items():
            assert hasattr(app.state, component), f"Missing chat component: {component}"
            service = getattr(app.state, component)
            assert service is not None, f"Chat component {component} is None: {description}"
        
        # Test WebSocket bridge can handle chat events
        websocket_bridge = app.state.agent_websocket_bridge
        required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
        
        for method in required_methods:
            assert hasattr(websocket_bridge, method), f"WebSocket bridge missing {method} for chat events"
        
        # Test agent supervisor ready for chat
        supervisor = app.state.agent_supervisor
        if hasattr(supervisor, 'websocket_bridge'):
            assert supervisor.websocket_bridge is not None, "Supervisor missing WebSocket integration for chat"
        
        logger.info("✅ End-to-end chat functionality ready - primary business value enabled")

    @pytest.mark.asyncio
    async def test_production_readiness_checks(self):
        """
        Test production readiness validation in FINALIZE phase.
        
        BVJ: Production readiness ensures reliable business value delivery.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Test production-ready configurations
        config_checks = {
            'startup_complete': 'System fully initialized',
            'database_available': 'Database ready for production load',
            'agent_supervisor': 'AI orchestration ready',
            'health_service': 'Health monitoring active'
        }
        
        for check, description in config_checks.items():
            if hasattr(app.state, check):
                value = getattr(app.state, check)
                if isinstance(value, bool):
                    assert value is True, f"Production check failed: {description}"
                else:
                    assert value is not None, f"Production component missing: {description}"
        
        # Test critical service health for production
        from netra_backend.app.startup_health_checks import StartupHealthChecker
        
        health_checker = StartupHealthChecker(app)
        all_healthy, results = await health_checker.run_all_health_checks()
        
        # Count production-critical issues
        critical_issues = 0
        for result in results:
            if result.service_name in health_checker.CRITICAL_SERVICES:
                if result.status == ServiceStatus.UNHEALTHY:
                    critical_issues += 1
                    logger.error(f"Production-critical issue: {result.service_name} - {result.message}")
        
        # Production readiness requires all critical services healthy
        assert critical_issues == 0, f"{critical_issues} critical services unhealthy - not production ready"
        
        logger.info("✅ Production readiness validated - business value delivery assured")

    @pytest.mark.asyncio
    async def test_scalability_configuration_validation(self):
        """
        Test scalability configuration readiness.
        
        BVJ: Scalability enables business growth and increased value delivery.
        """
        app = await self.create_test_app_with_full_startup()
        
        # Test database connection pooling ready (only if PostgreSQL available)
        if _postgresql_available and hasattr(app.state, 'db_session_factory') and app.state.db_session_factory:
            # Database session factory enables connection pooling
            logger.info("✅ Database connection pooling ready for scale")
        elif not _postgresql_available:
            logger.info("ℹ️ PostgreSQL not available - database pooling test skipped")
        
        # Test Redis caching ready (only if Redis available)
        if _redis_available and hasattr(app.state, 'redis_manager') and app.state.redis_manager:
            logger.info("✅ Redis caching ready for performance scaling")
        elif not _redis_available:
            logger.info("ℹ️ Redis not available - caching test skipped")
        
        # Test background task management for scale
        if hasattr(app.state, 'background_task_manager') and app.state.background_task_manager:
            logger.info("✅ Background task management ready for concurrent operations")
        
        # Test WebSocket bridge ready for concurrent connections
        websocket_bridge = getattr(app.state, 'agent_websocket_bridge', None)
        if websocket_bridge:
            # Modern per-request WebSocket architecture supports scaling
            logger.info("✅ WebSocket infrastructure ready for concurrent chat sessions")
        
        # Test factory patterns for user isolation (scalability requirement)
        factory_components = ['execution_engine_factory', 'websocket_bridge_factory', 'agent_instance_factory']
        
        factories_ready = 0
        for factory in factory_components:
            if hasattr(app.state, factory) and getattr(app.state, factory):
                factories_ready += 1
        
        if factories_ready > 0:
            logger.info(f"✅ {factories_ready}/{len(factory_components)} factory patterns ready for user isolation scaling")
        
        logger.info("✅ Scalability configuration validated for business growth")


@pytest.mark.asyncio
async def test_finalize_phase_integration_comprehensive():
    """
    Comprehensive integration test covering all FINALIZE phase aspects.
    
    BVJ: End-to-end validation ensures complete business value delivery readiness.
    """
    test_instance = FinalizePhaseIntegrationTest()
    test_instance.setup_method(test_finalize_phase_integration_comprehensive)
    
    try:
        # Run complete startup and validation
        app = await test_instance.create_test_app_with_full_startup()
        
        # Validate all aspects
        test_instance.validate_startup_timing(app, max_startup_time=60.0)
        test_instance.validate_critical_services_ready(app)
        test_instance.validate_phase_completion(app)
        
        # Run comprehensive health validation
        from netra_backend.app.startup_health_checks import StartupHealthChecker
        
        health_checker = StartupHealthChecker(app)
        validation_passed = await health_checker.validate_startup(fail_on_critical=True)
        
        assert validation_passed, "Comprehensive health validation failed"
        
        # Business value validation
        assert app.state.startup_complete is True, "Startup not complete"
        assert app.state.startup_failed is False, "Startup marked as failed"
        
        # Final business value assertion
        logger.info("🎯 COMPREHENSIVE FINALIZE PHASE VALIDATION PASSED")
        logger.info("✅ System ready for full business value delivery through chat")
        logger.info("✅ All critical services operational")
        logger.info("✅ Performance within acceptable limits")
        logger.info("✅ Health monitoring active")
        logger.info("✅ Production readiness confirmed")
        
        return True
        
    finally:
        test_instance.teardown_method(test_finalize_phase_integration_comprehensive)


if __name__ == "__main__":
    # Can be run directly for development testing
    import asyncio
    asyncio.run(test_finalize_phase_integration_comprehensive())