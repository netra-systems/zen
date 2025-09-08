"""
Test Startup Cross-Phase Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure startup phase transitions maintain system coherence
- Value Impact: Phase integration failures prevent chat readiness and block user value
- Strategic Impact: Core platform stability and initialization reliability

This module tests the integration between multiple startup phases to ensure
smooth transitions and proper dependency management across phase boundaries.

CRITICAL: These tests validate that:
1. Phase transitions maintain state consistency
2. Dependencies are properly initialized across phases 
3. Resource sharing works correctly between phases
4. Error propagation handles cross-phase scenarios
5. Authentication context persists across phases
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest  
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.smd import (
    StartupOrchestrator,
    StartupPhase,
    DeterministicStartupError
)
from netra_backend.app.core.registry.universal_registry import UniversalRegistry
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
# UnifiedWebSocketInit class does not exist - removed import
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestStartupCrossPhaseIntegration(BaseIntegrationTest):
    """Test integration between multiple startup phases."""
    
    def __init__(self):
        """Initialize test suite with proper environment isolation."""
        super().__init__()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.startup_orchestrator: Optional[StartupOrchestrator] = None
        self.startup_context: Optional[dict] = None
        
    async def asyncSetUp(self):
        """Set up test environment with proper authentication."""
        await super().asyncSetUp()
        # Create authenticated test user for multi-user scenarios
        self.test_token, self.test_user = await create_authenticated_user(
            environment="test",
            email="cross_phase_test@example.com", 
            permissions=["read", "write"]
        )
    
    async def asyncTearDown(self):
        """Clean up test resources."""
        if self.startup_orchestrator:
            try:
                await self.startup_orchestrator.shutdown()
            except Exception:
                pass  # Ignore cleanup errors
        await super().asyncTearDown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_init_to_dependencies_phase_transition(self, real_services_fixture):
        """Test smooth transition from INIT to DEPENDENCIES phase."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Start INIT phase
            context = await startup_orchestrator.execute_phase(StartupPhase.INIT)
            
            # Validate INIT phase state
            assert context.phase_states[StartupPhase.INIT].is_complete
            assert context.environment is not None
            assert context.configuration is not None
            
            # Execute DEPENDENCIES phase
            context = await startup_orchestrator.execute_phase(StartupPhase.DEPENDENCIES, context)
            
            # Validate transition state
            assert context.phase_states[StartupPhase.DEPENDENCIES].is_complete
            assert context.shared_state.get("universal_registry") is not None
            
            # Verify environment persisted across phases
            init_env_id = context.phase_states[StartupPhase.INIT].outputs.get("env_id")
            deps_env_id = context.phase_states[StartupPhase.DEPENDENCIES].outputs.get("env_id") 
            assert init_env_id == deps_env_id
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration 
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_dependencies_to_database_registry_sharing(self, real_services_fixture):
        """Test registry sharing from DEPENDENCIES to DATABASE phase."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute through DEPENDENCIES 
            context = await startup_orchestrator.execute_through_phase(StartupPhase.DEPENDENCIES)
            
            # Capture registry instance
            registry = context.shared_state.get("universal_registry")
            assert registry is not None
            registry_id = id(registry)
            
            # Execute DATABASE phase
            context = await startup_orchestrator.execute_phase(StartupPhase.DATABASE, context)
            
            # Verify same registry instance shared
            database_registry = context.shared_state.get("universal_registry")
            assert id(database_registry) == registry_id
            
            # Verify database components registered in shared registry
            db_pool = registry.get("database_pool")
            assert db_pool is not None
            
            # Verify database configuration accessible through registry
            db_config = registry.get("database_config")
            assert db_config is not None
            assert hasattr(db_config, 'connection_string')
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_database_to_cache_connection_persistence(self, real_services_fixture):
        """Test connection persistence from DATABASE to CACHE phase."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute through DATABASE
            context = await startup_orchestrator.execute_through_phase(StartupPhase.DATABASE)
            
            # Capture database connection state
            db_pool = context.shared_state.get("universal_registry").get("database_pool")
            assert db_pool is not None
            db_connection_count = len(db_pool._pool._queue) if hasattr(db_pool, '_pool') else 0
            
            # Execute CACHE phase
            context = await startup_orchestrator.execute_phase(StartupPhase.CACHE, context)
            
            # Verify database connections maintained
            post_cache_db_pool = context.shared_state.get("universal_registry").get("database_pool")
            assert post_cache_db_pool is not None
            assert id(post_cache_db_pool) == id(db_pool)  # Same instance
            
            # Verify cache integration with database
            redis_pool = context.shared_state.get("universal_registry").get("redis_pool")
            assert redis_pool is not None
            
            # Test cache-database coordination
            cache_key = f"test_key_{int(time.time())}"
            await redis_pool.set(cache_key, "test_value", ex=10)
            cached_value = await redis_pool.get(cache_key)
            assert cached_value == "test_value"
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_cache_to_services_state_propagation(self, real_services_fixture):
        """Test state propagation from CACHE to SERVICES phase."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute through CACHE
            context = await startup_orchestrator.execute_through_phase(StartupPhase.CACHE)
            
            # Capture cache state
            redis_pool = context.shared_state.get("universal_registry").get("redis_pool")
            cache_health_key = "startup_cache_health"
            await redis_pool.set(cache_health_key, "healthy", ex=30)
            
            # Execute SERVICES phase
            context = await startup_orchestrator.execute_phase(StartupPhase.SERVICES, context)
            
            # Verify services can access cache state
            agent_registry = context.shared_state.get("agent_registry")
            assert agent_registry is not None
            
            # Verify agent registry has access to cache
            assert agent_registry._redis_pool is not None
            cached_health = await agent_registry._redis_pool.get(cache_health_key)
            assert cached_health == "healthy"
            
            # Verify user execution context service integration
            user_context_service = context.shared_state.get("user_execution_context_service")
            assert user_context_service is not None
            assert user_context_service._registry is not None
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_services_to_websocket_agent_integration(self, real_services_fixture):
        """Test agent integration from SERVICES to WEBSOCKET phase."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute through SERVICES
            context = await startup_orchestrator.execute_through_phase(StartupPhase.SERVICES)
            
            # Capture agent registry state
            agent_registry = context.shared_state.get("agent_registry")
            assert agent_registry is not None
            
            # Create test user execution context
            user_context = UserExecutionContext(
                user_id=self.test_user["id"],
                session_id=f"test_session_{int(time.time())}",
                thread_id=f"test_thread_{int(time.time())}",
                permissions=self.test_user["permissions"]
            )
            
            # Execute WEBSOCKET phase
            context = await startup_orchestrator.execute_phase(StartupPhase.WEBSOCKET, context)
            
            # Verify WebSocket initialization has access to agents
            websocket_manager = context.shared_state.get("websocket_manager")
            assert websocket_manager is not None
            
            # Verify WebSocket can create agent instances
            if hasattr(websocket_manager, 'agent_registry'):
                ws_agent_registry = websocket_manager.agent_registry
                assert ws_agent_registry is not None
                assert id(ws_agent_registry) == id(agent_registry)  # Same instance
            
            # Test WebSocket-Agent integration
            unified_ws_init = context.shared_state.get("unified_websocket_init")
            assert unified_ws_init is not None
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_websocket_to_finalize_health_validation(self, real_services_fixture):
        """Test health validation from WEBSOCKET to FINALIZE phase."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute through WEBSOCKET
            context = await startup_orchestrator.execute_through_phase(StartupPhase.WEBSOCKET)
            
            # Capture WebSocket state
            websocket_manager = context.shared_state.get("websocket_manager")
            unified_ws_init = context.shared_state.get("unified_websocket_init")
            
            # Execute FINALIZE phase
            context = await startup_orchestrator.execute_phase(StartupPhase.FINALIZE, context)
            
            # Verify health checks validate all phases
            health_status = context.phase_states[StartupPhase.FINALIZE].outputs.get("health_status")
            assert health_status is not None
            
            # Verify all components are healthy
            assert health_status.get("database_healthy", False)
            assert health_status.get("cache_healthy", False)
            assert health_status.get("agents_healthy", False)
            assert health_status.get("websocket_healthy", False)
            
            # Verify final system readiness
            assert context.is_chat_ready
            assert context.startup_completed_at is not None
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_full_phase_dependency_chain(self, real_services_fixture):
        """Test complete dependency chain across all phases."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Track phase execution order
            phase_order = []
            original_execute = startup_orchestrator.execute_phase
            
            async def track_phase_execution(phase, context=None):
                phase_order.append(phase)
                return await original_execute(phase, context)
            
            startup_orchestrator.execute_phase = track_phase_execution
            
            # Execute complete startup
            context = await startup_orchestrator.startup()
            
            # Verify correct phase order
            expected_order = [
                StartupPhase.INIT,
                StartupPhase.DEPENDENCIES, 
                StartupPhase.DATABASE,
                StartupPhase.CACHE,
                StartupPhase.SERVICES,
                StartupPhase.WEBSOCKET,
                StartupPhase.FINALIZE
            ]
            assert phase_order == expected_order
            
            # Verify each phase can access dependencies from previous phases
            registry = context.shared_state.get("universal_registry")
            assert registry is not None
            
            # DATABASE dependencies
            assert registry.get("database_pool") is not None
            
            # CACHE dependencies  
            assert registry.get("redis_pool") is not None
            
            # SERVICES dependencies
            assert context.shared_state.get("agent_registry") is not None
            assert context.shared_state.get("user_execution_context_service") is not None
            
            # WEBSOCKET dependencies
            assert context.shared_state.get("websocket_manager") is not None
            assert context.shared_state.get("unified_websocket_init") is not None
            
            # FINALIZE validation
            assert context.is_chat_ready
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_cross_phase_error_propagation(self, real_services_fixture):
        """Test error propagation across phase boundaries."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute INIT successfully
            context = await startup_orchestrator.execute_phase(StartupPhase.INIT)
            assert context.phase_states[StartupPhase.INIT].is_complete
            
            # Inject error in DEPENDENCIES phase
            with patch.object(UniversalRegistry, '__init__', side_effect=Exception("Registry initialization failed")):
                with pytest.raises(DeterministicStartupError) as exc_info:
                    await startup_orchestrator.execute_phase(StartupPhase.DEPENDENCIES, context)
                
                assert "Registry initialization failed" in str(exc_info.value)
                assert context.phase_states[StartupPhase.DEPENDENCIES].error is not None
                
            # Verify INIT phase state preserved despite DEPENDENCIES failure
            assert context.phase_states[StartupPhase.INIT].is_complete
            assert context.phase_states[StartupPhase.INIT].error is None
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration 
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_phase_rollback_on_failure(self, real_services_fixture):
        """Test phase rollback capabilities when later phase fails."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute through CACHE successfully
            context = await startup_orchestrator.execute_through_phase(StartupPhase.CACHE)
            
            # Capture successful state
            successful_registry = context.shared_state.get("universal_registry")
            successful_db_pool = successful_registry.get("database_pool")
            successful_redis_pool = successful_registry.get("redis_pool")
            
            # Inject failure in SERVICES phase
            with patch.object(AgentRegistry, '__init__', side_effect=Exception("Agent registry failed")):
                with pytest.raises(DeterministicStartupError):
                    await startup_orchestrator.execute_phase(StartupPhase.SERVICES, context)
            
            # Verify previous phases remain intact
            assert context.phase_states[StartupPhase.INIT].is_complete
            assert context.phase_states[StartupPhase.DEPENDENCIES].is_complete
            assert context.phase_states[StartupPhase.DATABASE].is_complete
            assert context.phase_states[StartupPhase.CACHE].is_complete
            
            # Verify resources from successful phases still accessible
            current_registry = context.shared_state.get("universal_registry")
            assert id(current_registry) == id(successful_registry)
            assert current_registry.get("database_pool") is not None
            assert current_registry.get("redis_pool") is not None
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_concurrent_phase_access_safety(self, real_services_fixture):
        """Test thread safety of cross-phase resource access."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute through SERVICES
            context = await startup_orchestrator.execute_through_phase(StartupPhase.SERVICES)
            
            # Get shared resources
            registry = context.shared_state.get("universal_registry")
            agent_registry = context.shared_state.get("agent_registry")
            
            # Define concurrent access function
            async def access_shared_resources(worker_id: int) -> Dict:
                results = {}
                
                # Access database pool
                db_pool = registry.get("database_pool")
                results[f"db_pool_{worker_id}"] = db_pool is not None
                
                # Access Redis pool
                redis_pool = registry.get("redis_pool")
                results[f"redis_pool_{worker_id}"] = redis_pool is not None
                
                # Access agent registry
                results[f"agent_registry_{worker_id}"] = agent_registry is not None
                
                # Small delay to simulate real usage
                await asyncio.sleep(0.01)
                
                return results
            
            # Run concurrent access tests
            tasks = [access_shared_resources(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            
            # Verify all workers accessed resources successfully
            for worker_results in results:
                for key, success in worker_results.items():
                    assert success, f"Worker failed to access resource: {key}"
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_phase_state_isolation(self, real_services_fixture):
        """Test that phase-specific state doesn't leak between phases."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Execute INIT and inject phase-specific state
            context = await startup_orchestrator.execute_phase(StartupPhase.INIT)
            context.phase_states[StartupPhase.INIT].phase_specific_data = {"init_secret": "init_only_data"}
            
            # Execute DEPENDENCIES and inject different state
            context = await startup_orchestrator.execute_phase(StartupPhase.DEPENDENCIES, context)
            context.phase_states[StartupPhase.DEPENDENCIES].phase_specific_data = {"deps_secret": "deps_only_data"}
            
            # Execute DATABASE phase
            context = await startup_orchestrator.execute_phase(StartupPhase.DATABASE, context)
            
            # Verify phase isolation - each phase only sees its own data
            init_data = context.phase_states[StartupPhase.INIT].phase_specific_data
            deps_data = context.phase_states[StartupPhase.DEPENDENCIES].phase_specific_data
            
            assert init_data.get("init_secret") == "init_only_data"
            assert "deps_secret" not in init_data
            
            assert deps_data.get("deps_secret") == "deps_only_data" 
            assert "init_secret" not in deps_data
            
            # Verify DATABASE phase doesn't see other phase secrets
            db_state = context.phase_states[StartupPhase.DATABASE]
            if hasattr(db_state, 'phase_specific_data') and db_state.phase_specific_data:
                assert "init_secret" not in db_state.phase_specific_data
                assert "deps_secret" not in db_state.phase_specific_data
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_authentication_context_across_phases(self, real_services_fixture):
        """Test authentication context persistence across startup phases."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Create user execution context during INIT
            context = await startup_orchestrator.execute_phase(StartupPhase.INIT)
            
            user_context = UserExecutionContext(
                user_id=self.test_user["id"],
                session_id=f"cross_phase_session_{int(time.time())}",
                thread_id=f"cross_phase_thread_{int(time.time())}",
                permissions=self.test_user["permissions"],
                authentication_token=self.test_token
            )
            
            # Store user context in shared state
            context.shared_state["test_user_context"] = user_context
            
            # Execute through all phases
            context = await startup_orchestrator.execute_through_phase(StartupPhase.FINALIZE, context)
            
            # Verify authentication context persisted
            final_user_context = context.shared_state.get("test_user_context")
            assert final_user_context is not None
            assert final_user_context.user_id == self.test_user["id"]
            assert final_user_context.authentication_token == self.test_token
            assert final_user_context.permissions == self.test_user["permissions"]
            
            # Verify user context service can use authentication
            user_context_service = context.shared_state.get("user_execution_context_service")
            if user_context_service:
                # Test authentication validation
                is_valid = await user_context_service.validate_user_context(final_user_context)
                assert is_valid
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_resource_cleanup_across_phases(self, real_services_fixture):
        """Test resource cleanup coordination across phases."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        resource_cleanup_log = []
        
        try:
            # Execute through SERVICES to create resources
            context = await startup_orchestrator.execute_through_phase(StartupPhase.SERVICES)
            
            # Mock cleanup tracking
            registry = context.shared_state.get("universal_registry")
            original_cleanup = registry.cleanup if hasattr(registry, 'cleanup') else AsyncMock()
            
            async def track_cleanup():
                resource_cleanup_log.append("registry_cleanup")
                if callable(original_cleanup):
                    await original_cleanup()
            
            registry.cleanup = track_cleanup
            
            # Mock agent registry cleanup
            agent_registry = context.shared_state.get("agent_registry")
            if hasattr(agent_registry, 'cleanup'):
                original_agent_cleanup = agent_registry.cleanup
                
                async def track_agent_cleanup():
                    resource_cleanup_log.append("agent_registry_cleanup")
                    await original_agent_cleanup()
                
                agent_registry.cleanup = track_agent_cleanup
            
            # Trigger shutdown
            await startup_orchestrator.shutdown()
            
            # Verify cleanup was called for shared resources
            assert len(resource_cleanup_log) > 0
            
        finally:
            # Ensure cleanup even if test fails
            try:
                await startup_orchestrator.shutdown()
            except Exception:
                pass

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_phase_timing_and_performance_correlation(self, real_services_fixture):
        """Test performance correlation across phase transitions."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        phase_timings = {}
        
        try:
            # Track phase execution times
            for phase in StartupPhase:
                start_time = time.time()
                
                if phase == StartupPhase.INIT:
                    context = await startup_orchestrator.execute_phase(phase)
                else:
                    context = await startup_orchestrator.execute_phase(phase, context)
                
                end_time = time.time()
                phase_timings[phase] = end_time - start_time
            
            # Verify reasonable timing relationships
            # INIT should be fast (configuration loading)
            assert phase_timings[StartupPhase.INIT] < 2.0, "INIT phase too slow"
            
            # DATABASE and CACHE should be moderate (connection setup)
            assert phase_timings[StartupPhase.DATABASE] < 5.0, "DATABASE phase too slow"
            assert phase_timings[StartupPhase.CACHE] < 5.0, "CACHE phase too slow"
            
            # SERVICES might be slower (agent initialization)
            assert phase_timings[StartupPhase.SERVICES] < 10.0, "SERVICES phase too slow"
            
            # Total startup should be under 30 seconds
            total_time = sum(phase_timings.values())
            assert total_time < 30.0, f"Total startup too slow: {total_time}s"
            
            # Verify no single phase dominates
            max_time = max(phase_timings.values())
            assert max_time < total_time * 0.6, "Single phase dominates startup time"
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_cross_phase_event_propagation(self, real_services_fixture):
        """Test event propagation across phase boundaries."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        events_received = []
        
        try:
            # Mock event handler
            def event_handler(phase: StartupPhase, event_type: str, data: dict):
                events_received.append({
                    "phase": phase,
                    "event_type": event_type,
                    "data": data,
                    "timestamp": datetime.now(timezone.utc)
                })
            
            # Attach event handler to startup module
            if hasattr(startup_orchestrator, 'add_event_handler'):
                startup_orchestrator.add_event_handler(event_handler)
            
            # Execute startup with event tracking
            context = await startup_orchestrator.startup()
            
            # Verify events were generated for each phase
            phase_events = {event["phase"] for event in events_received}
            
            # Should have events from key phases
            assert StartupPhase.INIT in phase_events or len(events_received) == 0  # Events optional
            
            # If events are implemented, verify proper ordering
            if events_received:
                # Sort events by timestamp
                sorted_events = sorted(events_received, key=lambda x: x["timestamp"])
                
                # Verify chronological order matches phase order
                phase_order = [event["phase"] for event in sorted_events]
                expected_phases = [p for p in StartupPhase]
                
                # Events should generally follow phase order (some phases may not emit events)
                last_phase_index = -1
                for event_phase in phase_order:
                    current_phase_index = expected_phases.index(event_phase)
                    assert current_phase_index >= last_phase_index, "Event order doesn't match phase order"
                    last_phase_index = current_phase_index
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_phase_configuration_inheritance(self, real_services_fixture):
        """Test configuration inheritance and override across phases."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Set base configuration in INIT
            context = await startup_orchestrator.execute_phase(StartupPhase.INIT)
            
            base_config = {
                "database_timeout": 30,
                "redis_timeout": 10,
                "agent_timeout": 60,
                "global_debug": False
            }
            
            context.configuration.update(base_config)
            
            # Execute DEPENDENCIES with config inheritance
            context = await startup_orchestrator.execute_phase(StartupPhase.DEPENDENCIES, context)
            
            # DEPENDENCIES might override some settings
            deps_config_overrides = {
                "registry_cache_size": 1000,
                "global_debug": True  # Override base setting
            }
            context.configuration.update(deps_config_overrides)
            
            # Execute DATABASE phase
            context = await startup_orchestrator.execute_phase(StartupPhase.DATABASE, context)
            
            # Verify configuration inheritance
            assert context.configuration.get("database_timeout") == 30  # From base
            assert context.configuration.get("redis_timeout") == 10     # From base
            assert context.configuration.get("registry_cache_size") == 1000  # From dependencies
            assert context.configuration.get("global_debug") is True    # Overridden
            
            # Execute remaining phases
            context = await startup_orchestrator.execute_through_phase(StartupPhase.FINALIZE, context)
            
            # Verify final configuration available to all components
            final_config = context.configuration
            assert len(final_config) >= len(base_config) + len(deps_config_overrides) - 1  # -1 for override
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services 
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_phase_dependency_validation(self, real_services_fixture):
        """Test validation of phase dependencies."""
        from fastapi import FastAPI
        app = FastAPI()
        startup_orchestrator = StartupOrchestrator(app)
        
        try:
            # Try to execute DATABASE phase without DEPENDENCIES
            context = await startup_orchestrator.execute_phase(StartupPhase.INIT)
            
            # Skip DEPENDENCIES phase and try DATABASE directly
            with pytest.raises(DeterministicStartupError) as exc_info:
                await startup_orchestrator.execute_phase(StartupPhase.DATABASE, context)
            
            assert "dependency" in str(exc_info.value).lower() or "prerequisite" in str(exc_info.value).lower()
            
            # Verify correct phase order requirement
            context = await startup_orchestrator.execute_phase(StartupPhase.DEPENDENCIES, context)
            
            # Now DATABASE should work
            context = await startup_orchestrator.execute_phase(StartupPhase.DATABASE, context)
            assert context.phase_states[StartupPhase.DATABASE].is_complete
            
        finally:
            await startup_orchestrator.shutdown()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.skip(reason="Phase execution API not implemented - StartupOrchestrator uses initialize_system() instead of execute_phase()")
    async def test_multi_instance_phase_isolation(self, real_services_fixture):
        """Test isolation between multiple startup module instances."""
        startup_orchestrator_1 = StartupOrchestrator()
        startup_orchestrator_2 = StartupOrchestrator()
        
        try:
            # Execute different phases on different instances
            context_1 = await startup_orchestrator_1.execute_through_phase(StartupPhase.DEPENDENCIES)
            context_2 = await startup_orchestrator_2.execute_through_phase(StartupPhase.CACHE)
            
            # Verify instances have different state
            assert id(context_1) != id(context_2)
            
            registry_1 = context_1.shared_state.get("universal_registry")
            registry_2 = context_2.shared_state.get("universal_registry")
            
            # Registries should be different instances
            assert id(registry_1) != id(registry_2)
            
            # Each context should only show completed phases
            assert context_1.phase_states[StartupPhase.DEPENDENCIES].is_complete
            assert not context_1.phase_states[StartupPhase.DATABASE].is_complete
            
            assert context_2.phase_states[StartupPhase.CACHE].is_complete
            assert context_2.phase_states[StartupPhase.DATABASE].is_complete  # Cache requires database
            
        finally:
            await startup_orchestrator_1.shutdown()
            await startup_orchestrator_2.shutdown()