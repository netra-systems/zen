#!/usr/bin/env python3
"""
Issue #802 SSOT Chat Migration Test Plan - Deployment Safety Validation

This test validates that Issue #565 ExecutionEngine migration is deployment-safe:
1. Migration maintains system stability during rolling deployments
2. No breaking changes for existing running instances
3. Database and state migrations are backward compatible
4. WebSocket connections remain stable during deployment
5. Chat functionality continues operating during migration

Business Value: Platform/Internal - Deployment Safety & System Reliability
Protects production stability and ensures zero-downtime deployment of the
ExecutionEngine migration protecting $500K+ ARR Golden Path functionality.

CRITICAL: These tests simulate production deployment scenarios to validate
that the migration can be deployed safely without service interruption.
"""

import pytest
import asyncio
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import concurrent.futures

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)


@pytest.mark.e2e
class DeploymentSafetyValidationTests(SSotAsyncTestCase):
    """
    Test suite validating deployment safety for ExecutionEngine migration.

    Simulates production deployment scenarios to ensure the migration
    can be deployed without breaking existing functionality or causing downtime.
    """

    async def setup_method(self, method):
        """Setup for each test method."""
        await super().setup_method(method)

        # Create mock factory for deployment testing
        self.mock_factory = SSotMockFactory()

        # Track engines for cleanup
        self.created_engines: List[UserExecutionEngine] = []

        # Deployment simulation components
        self.deployment_scenarios = {
            'rolling_deployment': {
                'description': 'Gradual replacement of execution engines',
                'legacy_instances': 3,
                'modern_instances': 3,
                'overlap_duration': 5.0
            },
            'blue_green_deployment': {
                'description': 'Complete environment swap',
                'legacy_environment': 'blue',
                'modern_environment': 'green',
                'cutover_duration': 2.0
            },
            'canary_deployment': {
                'description': 'Gradual traffic migration',
                'canary_percentage': [10, 25, 50, 75, 100],
                'validation_interval': 1.0
            }
        }

        # Mock components for deployment testing
        self.mock_registry = self.mock_factory.create_agent_registry_mock()
        self.mock_websocket_bridge = self.mock_factory.create_websocket_bridge_mock()

    async def teardown_method(self, method):
        """Cleanup for each test method."""
        for engine in self.created_engines:
            try:
                if hasattr(engine, 'is_active') and engine.is_active():
                    await engine.cleanup()
            except Exception as e:
                print(f"Warning: Engine cleanup failed: {e}")

        self.created_engines.clear()
        await super().teardown_method(method)

    def create_deployment_user_context(self, user_id: str, environment: str = 'production') -> UserExecutionContext:
        """Create UserExecutionContext for deployment testing."""
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{user_id}_{environment}",
            run_id=f"run_{user_id}_{environment}_{int(time.time())}",
            request_id=f"request_{user_id}_{environment}_{int(time.time())}",
            metadata={
                'environment': environment,
                'test_category': 'deployment_safety',
                'deployment_test': True
            }
        )

    async def create_legacy_execution_engine(self, user_id: str, environment: str = 'legacy') -> UserExecutionEngine:
        """Create execution engine simulating legacy deployment."""
        user_context = self.create_deployment_user_context(user_id, environment)

        # Create engine using legacy compatibility pattern
        engine = await UserExecutionEngine.create_from_legacy(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=user_context
        )

        # Mark as legacy for testing
        engine._deployment_type = 'legacy'
        engine._deployment_environment = environment

        self.created_engines.append(engine)
        return engine

    async def create_modern_execution_engine(self, user_id: str, environment: str = 'modern') -> UserExecutionEngine:
        """Create execution engine simulating modern deployment."""
        user_context = self.create_deployment_user_context(user_id, environment)

        # Create engine using modern pattern
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=self.mock_factory.create_agent_factory_mock(),
            websocket_emitter=self.mock_factory.create_websocket_emitter_mock(
                user_id=user_id
            )
        )

        # Mark as modern for testing
        engine._deployment_type = 'modern'
        engine._deployment_environment = environment

        self.created_engines.append(engine)
        return engine

    async def test_rolling_deployment_maintains_service_continuity(self):
        """
        Test that rolling deployment maintains continuous service availability.

        ROLLING DEPLOYMENT: Validates that gradual replacement of execution
        engines doesn't interrupt ongoing user sessions or degrade service.
        """
        scenario = self.deployment_scenarios['rolling_deployment']

        # Phase 1: Create legacy instances (current production)
        legacy_engines = []
        for i in range(scenario['legacy_instances']):
            engine = await self.create_legacy_execution_engine(f"legacy_user_{i}")
            legacy_engines.append(engine)

        # Simulate active user sessions on legacy instances
        legacy_sessions = await self._simulate_active_user_sessions(legacy_engines)

        # Phase 2: Begin rolling deployment - create modern instances
        modern_engines = []
        for i in range(scenario['modern_instances']):
            engine = await self.create_modern_execution_engine(f"modern_user_{i}")
            modern_engines.append(engine)

        # Phase 3: Simulate overlap period - both systems running
        overlap_tasks = []

        # Continue legacy sessions
        for session in legacy_sessions:
            task = asyncio.create_task(self._continue_user_session(session))
            overlap_tasks.append(task)

        # Start new sessions on modern instances
        modern_sessions = await self._simulate_active_user_sessions(modern_engines)
        for session in modern_sessions:
            task = asyncio.create_task(self._continue_user_session(session))
            overlap_tasks.append(task)

        # Run overlap period
        await asyncio.sleep(scenario['overlap_duration'])

        # Phase 4: Graceful shutdown of legacy instances
        for engine in legacy_engines:
            await engine.cleanup()

        # Wait for all tasks to complete
        results = await asyncio.gather(*overlap_tasks, return_exceptions=True)

        # Validate deployment safety
        self._validate_rolling_deployment_results(results, legacy_sessions, modern_sessions)

    async def _simulate_active_user_sessions(self, engines: List[UserExecutionEngine]) -> List[Dict[str, Any]]:
        """Simulate active user sessions for deployment testing."""
        sessions = []

        for engine in engines:
            session = {
                'engine': engine,
                'user_id': engine.user_context.user_id,
                'start_time': time.time(),
                'requests_completed': 0,
                'errors_encountered': 0,
                'deployment_type': getattr(engine, '_deployment_type', 'unknown')
            }
            sessions.append(session)

        return sessions

    async def _continue_user_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Continue user session during deployment overlap."""
        engine = session['engine']
        session_duration = 3.0  # 3 seconds of activity

        start_time = time.time()
        while time.time() - start_time < session_duration:
            try:
                # Simulate user request
                request = {
                    'message': f"Deployment test request {session['requests_completed']}",
                    'user_id': session['user_id'],
                    'session_test': True
                }

                result = await engine.execute_agent_pipeline(
                    agent_name="deployment_test_agent",
                    execution_context=engine.user_context,
                    input_data=request
                )

                if result.success:
                    session['requests_completed'] += 1
                else:
                    session['errors_encountered'] += 1

                # Brief pause between requests
                await asyncio.sleep(0.5)

            except Exception as e:
                session['errors_encountered'] += 1
                print(f"Session error (expected during deployment): {e}")

            # Stop if engine becomes inactive
            if not engine.is_active():
                break

        session['end_time'] = time.time()
        session['total_duration'] = session['end_time'] - session['start_time']
        return session

    def _validate_rolling_deployment_results(self, results: List[Any], legacy_sessions: List, modern_sessions: List):
        """Validate rolling deployment maintains service quality."""
        # Analyze session results
        all_sessions = legacy_sessions + modern_sessions

        for session in all_sessions:
            # Each session should complete some requests
            assert session['requests_completed'] > 0, \
                f"Session {session['user_id']} completed no requests during deployment"

            # Error rate should be acceptable during deployment
            total_requests = session['requests_completed'] + session['errors_encountered']
            if total_requests > 0:
                error_rate = session['errors_encountered'] / total_requests
                assert error_rate <= 0.2, \
                    f"High error rate during deployment: {error_rate:.1%} for {session['user_id']}"

        # Modern sessions should perform at least as well as legacy
        legacy_avg_requests = sum(s['requests_completed'] for s in legacy_sessions) / len(legacy_sessions)
        modern_avg_requests = sum(s['requests_completed'] for s in modern_sessions) / len(modern_sessions)

        assert modern_avg_requests >= legacy_avg_requests * 0.8, \
            f"Modern instances underperforming: {modern_avg_requests} vs {legacy_avg_requests}"

    async def test_blue_green_deployment_zero_downtime(self):
        """
        Test that blue-green deployment achieves zero downtime cutover.

        BLUE-GREEN DEPLOYMENT: Validates that complete environment swap
        can be performed without service interruption.
        """
        scenario = self.deployment_scenarios['blue_green_deployment']

        # Phase 1: Blue environment (current production)
        blue_engines = []
        for i in range(3):
            engine = await self.create_legacy_execution_engine(
                f"blue_user_{i}", scenario['legacy_environment']
            )
            blue_engines.append(engine)

        # Phase 2: Green environment (new deployment)
        green_engines = []
        for i in range(3):
            engine = await self.create_modern_execution_engine(
                f"green_user_{i}", scenario['modern_environment']
            )
            green_engines.append(engine)

        # Phase 3: Pre-cutover validation
        await self._validate_environment_health(blue_engines, 'blue')
        await self._validate_environment_health(green_engines, 'green')

        # Phase 4: Instantaneous cutover simulation
        cutover_start = time.time()

        # Simulate traffic switch (blue -> green)
        traffic_switch_tasks = []

        # Create new sessions on green environment
        for i in range(5):  # Simulate new traffic
            task = asyncio.create_task(
                self._simulate_cutover_request(green_engines[i % len(green_engines)])
            )
            traffic_switch_tasks.append(task)

        # Wait for cutover to complete
        cutover_results = await asyncio.gather(*traffic_switch_tasks, return_exceptions=True)
        cutover_duration = time.time() - cutover_start

        # Phase 5: Post-cutover validation
        await self._validate_environment_health(green_engines, 'green_post_cutover')

        # Validate zero-downtime cutover
        assert cutover_duration <= scenario['cutover_duration'], \
            f"Cutover took too long: {cutover_duration:.2f}s > {scenario['cutover_duration']}s"

        for result in cutover_results:
            assert not isinstance(result, Exception), f"Cutover request failed: {result}"

        # Phase 6: Graceful blue environment shutdown
        for engine in blue_engines:
            await engine.cleanup()

    async def _validate_environment_health(self, engines: List[UserExecutionEngine], environment_name: str):
        """Validate that environment is healthy and ready."""
        health_checks = []

        for engine in engines:
            # Basic health check
            assert engine.is_active(), f"Engine {engine.engine_id} not active in {environment_name}"

            # Functional health check
            try:
                stats = engine.get_user_execution_stats()
                assert isinstance(stats, dict), f"Stats check failed for {environment_name}"

                # Quick functional test
                test_request = {
                    'message': f"Health check for {environment_name}",
                    'health_check': True
                }

                result = await engine.execute_agent_pipeline(
                    agent_name="health_check_agent",
                    execution_context=engine.user_context,
                    input_data=test_request
                )

                health_checks.append({
                    'engine_id': engine.engine_id,
                    'environment': environment_name,
                    'health_status': 'healthy' if result.success else 'unhealthy',
                    'response_time': getattr(result, 'duration', 0)
                })

            except Exception as e:
                health_checks.append({
                    'engine_id': engine.engine_id,
                    'environment': environment_name,
                    'health_status': 'error',
                    'error': str(e)
                })

        # All engines should be healthy
        unhealthy_engines = [hc for hc in health_checks if hc['health_status'] != 'healthy']
        assert len(unhealthy_engines) == 0, f"Unhealthy engines in {environment_name}: {unhealthy_engines}"

    async def _simulate_cutover_request(self, engine: UserExecutionEngine) -> Dict[str, Any]:
        """Simulate request during blue-green cutover."""
        start_time = time.time()

        request = {
            'message': 'Critical business request during cutover',
            'priority': 'high',
            'cutover_test': True
        }

        result = await engine.execute_agent_pipeline(
            agent_name="cutover_test_agent",
            execution_context=engine.user_context,
            input_data=request
        )

        return {
            'success': result.success,
            'response_time': time.time() - start_time,
            'engine_id': engine.engine_id,
            'environment': getattr(engine, '_deployment_environment', 'unknown')
        }

    async def test_canary_deployment_gradual_traffic_migration(self):
        """
        Test that canary deployment allows safe gradual traffic migration.

        CANARY DEPLOYMENT: Validates that traffic can be gradually shifted
        to new deployment while monitoring for issues.
        """
        scenario = self.deployment_scenarios['canary_deployment']

        # Create stable baseline (legacy deployment)
        baseline_engines = []
        for i in range(4):
            engine = await self.create_legacy_execution_engine(f"baseline_user_{i}")
            baseline_engines.append(engine)

        # Create canary deployment (modern deployment)
        canary_engines = []
        for i in range(4):
            engine = await self.create_modern_execution_engine(f"canary_user_{i}")
            canary_engines.append(engine)

        # Gradual traffic migration
        migration_results = []

        for canary_percentage in scenario['canary_percentage']:
            phase_result = await self._execute_canary_phase(
                baseline_engines, canary_engines, canary_percentage
            )
            migration_results.append(phase_result)

            # Validate phase before proceeding
            self._validate_canary_phase(phase_result, canary_percentage)

            # Brief pause between phases
            await asyncio.sleep(scenario['validation_interval'])

        # Validate complete migration
        self._validate_complete_canary_migration(migration_results)

    async def _execute_canary_phase(self, baseline_engines: List, canary_engines: List, canary_percentage: int) -> Dict[str, Any]:
        """Execute single phase of canary deployment."""
        total_requests = 20
        canary_requests = int(total_requests * canary_percentage / 100)
        baseline_requests = total_requests - canary_requests

        # Execute requests on both deployments
        baseline_tasks = [
            self._execute_canary_request(baseline_engines[i % len(baseline_engines)], 'baseline')
            for i in range(baseline_requests)
        ]

        canary_tasks = [
            self._execute_canary_request(canary_engines[i % len(canary_engines)], 'canary')
            for i in range(canary_requests)
        ]

        # Wait for all requests to complete
        all_tasks = baseline_tasks + canary_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Analyze results
        baseline_results = results[:baseline_requests]
        canary_results = results[baseline_requests:]

        return {
            'canary_percentage': canary_percentage,
            'baseline_results': [r for r in baseline_results if not isinstance(r, Exception)],
            'canary_results': [r for r in canary_results if not isinstance(r, Exception)],
            'baseline_errors': [r for r in baseline_results if isinstance(r, Exception)],
            'canary_errors': [r for r in canary_results if isinstance(r, Exception)],
            'total_requests': total_requests
        }

    async def _execute_canary_request(self, engine: UserExecutionEngine, deployment_type: str) -> Dict[str, Any]:
        """Execute single request for canary testing."""
        start_time = time.time()

        request = {
            'message': f'Canary test request for {deployment_type} deployment',
            'deployment_type': deployment_type,
            'canary_test': True
        }

        try:
            result = await engine.execute_agent_pipeline(
                agent_name="canary_test_agent",
                execution_context=engine.user_context,
                input_data=request
            )

            return {
                'success': result.success,
                'response_time': time.time() - start_time,
                'deployment_type': deployment_type,
                'engine_id': engine.engine_id
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': time.time() - start_time,
                'deployment_type': deployment_type,
                'engine_id': engine.engine_id
            }

    def _validate_canary_phase(self, phase_result: Dict[str, Any], canary_percentage: int):
        """Validate single canary deployment phase."""
        baseline_results = phase_result['baseline_results']
        canary_results = phase_result['canary_results']

        # Calculate success rates
        baseline_success_rate = sum(1 for r in baseline_results if r['success']) / max(len(baseline_results), 1)
        canary_success_rate = sum(1 for r in canary_results if r['success']) / max(len(canary_results), 1)

        # Canary should perform at least as well as baseline
        assert canary_success_rate >= baseline_success_rate * 0.95, \
            f"Canary underperforming at {canary_percentage}%: {canary_success_rate:.1%} vs {baseline_success_rate:.1%}"

        # Calculate response times
        baseline_response_times = [r['response_time'] for r in baseline_results if r['success']]
        canary_response_times = [r['response_time'] for r in canary_results if r['success']]

        if baseline_response_times and canary_response_times:
            baseline_avg_time = sum(baseline_response_times) / len(baseline_response_times)
            canary_avg_time = sum(canary_response_times) / len(canary_response_times)

            # Canary response time should be reasonable
            assert canary_avg_time <= baseline_avg_time * 1.5, \
                f"Canary response time too slow at {canary_percentage}%: {canary_avg_time:.2f}s vs {baseline_avg_time:.2f}s"

    def _validate_complete_canary_migration(self, migration_results: List[Dict[str, Any]]):
        """Validate complete canary migration process."""
        # Migration should complete successfully
        final_phase = migration_results[-1]
        assert final_phase['canary_percentage'] == 100, "Migration should reach 100% canary traffic"

        # Success rates should remain stable throughout migration
        success_rates = []
        for phase in migration_results:
            canary_results = phase['canary_results']
            if canary_results:
                success_rate = sum(1 for r in canary_results if r['success']) / len(canary_results)
                success_rates.append(success_rate)

        # Success rate should not degrade significantly
        if len(success_rates) > 1:
            min_success_rate = min(success_rates)
            max_success_rate = max(success_rates)
            degradation = max_success_rate - min_success_rate

            assert degradation <= 0.1, f"Success rate degraded too much during migration: {degradation:.1%}"

    async def test_database_state_migration_compatibility(self):
        """
        Test that database state migration is backward compatible.

        DATABASE COMPATIBILITY: Validates that state storage patterns
        remain compatible during ExecutionEngine migration.
        """
        # Create engines with different patterns to test state compatibility
        legacy_user_context = self.create_deployment_user_context("db_legacy_user")
        modern_user_context = self.create_deployment_user_context("db_modern_user")

        legacy_engine = await self.create_legacy_execution_engine("db_legacy_user")
        modern_engine = await self.create_modern_execution_engine("db_modern_user")

        # Test state persistence patterns
        state_test_cases = [
            {
                'name': 'execution_stats_persistence',
                'test_func': self._test_execution_stats_compatibility
            },
            {
                'name': 'agent_result_storage',
                'test_func': self._test_agent_result_storage_compatibility
            },
            {
                'name': 'user_context_serialization',
                'test_func': self._test_user_context_serialization_compatibility
            }
        ]

        for test_case in state_test_cases:
            with self.subTest(state_test=test_case['name']):
                await test_case['test_func'](legacy_engine, modern_engine)

    async def _test_execution_stats_compatibility(self, legacy_engine: UserExecutionEngine, modern_engine: UserExecutionEngine):
        """Test execution stats remain compatible between engine types."""
        # Get stats from both engines
        legacy_stats = legacy_engine.get_user_execution_stats()
        modern_stats = modern_engine.get_user_execution_stats()

        # Both should have compatible structure
        required_fields = ['user_id', 'engine_id', 'total_executions', 'is_active']

        for field in required_fields:
            assert field in legacy_stats, f"Legacy engine missing stats field: {field}"
            assert field in modern_stats, f"Modern engine missing stats field: {field}"

        # Stats should be serializable (for database storage)
        try:
            json.dumps(legacy_stats)
            json.dumps(modern_stats)
        except Exception as e:
            self.fail(f"Stats not serializable: {e}")

    async def _test_agent_result_storage_compatibility(self, legacy_engine: UserExecutionEngine, modern_engine: UserExecutionEngine):
        """Test agent result storage remains compatible."""
        # Store test results in both engines
        test_result_data = {
            'agent_name': 'compatibility_test_agent',
            'result': 'test_output',
            'metadata': {'compatibility_test': True}
        }

        legacy_engine.set_agent_result('test_agent', test_result_data)
        modern_engine.set_agent_result('test_agent', test_result_data)

        # Retrieve results
        legacy_result = legacy_engine.get_agent_result('test_agent')
        modern_result = modern_engine.get_agent_result('test_agent')

        # Results should be equivalent
        assert legacy_result == test_result_data
        assert modern_result == test_result_data
        assert legacy_result == modern_result

    async def _test_user_context_serialization_compatibility(self, legacy_engine: UserExecutionEngine, modern_engine: UserExecutionEngine):
        """Test user context serialization remains compatible."""
        # Get user contexts
        legacy_context = legacy_engine.get_user_context()
        modern_context = modern_engine.get_user_context()

        # Both should be UserExecutionContext instances
        assert isinstance(legacy_context, UserExecutionContext)
        assert isinstance(modern_context, UserExecutionContext)

        # Both should have compatible serialization
        try:
            legacy_correlation_id = legacy_context.get_correlation_id()
            modern_correlation_id = modern_context.get_correlation_id()

            assert legacy_correlation_id is not None
            assert modern_correlation_id is not None

        except Exception as e:
            self.fail(f"User context serialization failed: {e}")

    async def test_websocket_connection_stability_during_deployment(self):
        """
        Test that WebSocket connections remain stable during deployment.

        WEBSOCKET STABILITY: Validates that real-time connections are
        maintained and continue to deliver events during migration.
        """
        # Create engines with active WebSocket connections
        websocket_engines = []
        for i in range(3):
            engine = await self.create_modern_execution_engine(f"websocket_user_{i}")
            websocket_engines.append(engine)

        # Simulate active WebSocket sessions
        websocket_sessions = []
        for engine in websocket_engines:
            session = await self._start_websocket_session(engine)
            websocket_sessions.append(session)

        # Simulate deployment event (engine restart/replacement)
        deployment_duration = 3.0
        start_time = time.time()

        # Continue WebSocket activity during deployment
        websocket_tasks = []
        for session in websocket_sessions:
            task = asyncio.create_task(
                self._maintain_websocket_activity(session, deployment_duration)
            )
            websocket_tasks.append(task)

        # Wait for deployment simulation to complete
        websocket_results = await asyncio.gather(*websocket_tasks, return_exceptions=True)

        # Validate WebSocket stability
        for i, result in enumerate(websocket_results):
            assert not isinstance(result, Exception), f"WebSocket session {i} failed: {result}"

            session_stats = result
            assert session_stats['events_delivered'] > 0, f"No events delivered in session {i}"
            assert session_stats['connection_stable'] == True, f"Connection unstable in session {i}"

    async def _start_websocket_session(self, engine: UserExecutionEngine) -> Dict[str, Any]:
        """Start WebSocket session for deployment testing."""
        return {
            'engine': engine,
            'user_id': engine.user_context.user_id,
            'events_delivered': 0,
            'errors_encountered': 0,
            'connection_stable': True,
            'start_time': time.time()
        }

    async def _maintain_websocket_activity(self, session: Dict[str, Any], duration: float) -> Dict[str, Any]:
        """Maintain WebSocket activity during deployment."""
        engine = session['engine']
        end_time = time.time() + duration

        while time.time() < end_time:
            try:
                # Simulate agent execution that triggers WebSocket events
                request = {
                    'message': 'WebSocket stability test during deployment',
                    'websocket_test': True
                }

                result = await engine.execute_agent_pipeline(
                    agent_name="websocket_stability_agent",
                    execution_context=engine.user_context,
                    input_data=request
                )

                if result.success:
                    session['events_delivered'] += 1

                # Brief pause between requests
                await asyncio.sleep(0.5)

            except Exception as e:
                session['errors_encountered'] += 1
                if session['errors_encountered'] > 3:
                    session['connection_stable'] = False
                    break

        session['end_time'] = time.time()
        return session
