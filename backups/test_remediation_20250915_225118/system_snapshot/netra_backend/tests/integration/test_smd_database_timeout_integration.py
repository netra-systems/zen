"""
Integration Tests for SMD Database Timeout - Issue #1278 Real Database Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Integration & Database Reliability
- Business Goal: Validate real database connection timeout behavior under load
- Value Impact: Prevent staging deployment failures due to database timeout cascades
- Strategic Impact: Integration-level validation of timeout handling worth $500K+ ARR impact

Testing Strategy:
- Test with real database connection delays (without mocking)
- Test lifespan_manager error handling with real components
- Test startup failure recovery scenarios
- Validate container behavior under real timeout conditions

Expected Result: Tests should FAIL initially, reproducing Issue #1278 database timeout integration issues
"""

import pytest
import asyncio
import os
import time
from fastapi import FastAPI

# Import test framework
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper

# Import SMD components  
from netra_backend.app.smd import (
    StartupOrchestrator,
    StartupPhase,
    DeterministicStartupError
)
from netra_backend.app.core.lifespan_manager import lifespan


class TestSMDDatabaseTimeoutIntegration(BaseIntegrationTest):
    """Integration tests for SMD database timeout scenarios using real components."""
    
    def setup_method(self):
        """Set up isolated test environment for each test."""
        super().setup_method()
        self.isolated_helper = IsolatedTestHelper()
        
    def teardown_method(self):
        """Clean up isolated environment after each test."""
        self.isolated_helper.cleanup_all()
        super().teardown_method()

    @pytest.mark.integration
    @pytest.mark.database_timeout
    @pytest.mark.timeout_reproduction
    def test_real_database_connection_delay_timeout(self):
        """
        Test real database connection with artificial delay to trigger timeout.
        
        Expected: TEST FAILURE - Real database timeout not handled properly
        """
        app = FastAPI()
        
        with self.isolated_helper.create_isolated_context("database_timeout_test") as context:
            # Configure environment for database timeout testing
            context.env.set("ENVIRONMENT", "staging", source="test")
            context.env.set("DATABASE_URL", "postgresql://test:test@localhost:5434/timeout_test_db", source="test")
            context.env.set("GRACEFUL_STARTUP_MODE", "false", source="test")  # Force strict mode
            
            # Set artificially low timeout to trigger failure
            context.env.set("DATABASE_TIMEOUT_OVERRIDE", "2.0", source="test")  # 2 second timeout
            
            orchestrator = StartupOrchestrator(app)
            
            # This should fail with real database timeout under artificial constraint
            with pytest.raises(DeterministicStartupError) as exc_info:
                asyncio.run(orchestrator._phase3_database_setup())
            
            error_message = str(exc_info.value)
            timeout_indicators = ["timeout", "database", "2.0"]
            
            has_timeout_indicators = any(indicator in error_message.lower() for indicator in timeout_indicators)
            if not has_timeout_indicators:
                pytest.fail(
                    f"Issue #1278 real database timeout not reproduced. "
                    f"Expected timeout indicators {timeout_indicators} in error: {error_message}"
                )

    @pytest.mark.integration
    @pytest.mark.database_timeout
    @pytest.mark.timeout_reproduction
    @pytest.mark.asyncio
    async def test_lifespan_manager_database_timeout_handling(self):
        """
        Test lifespan_manager error handling with real database timeout.
        
        Expected: TEST FAILURE - Lifespan manager doesn't handle database timeouts correctly
        """
        app = FastAPI()
        
        with self.isolated_helper.create_isolated_context("lifespan_timeout_test") as context:
            # Configure for timeout scenario
            context.env.set("ENVIRONMENT", "staging", source="test")
            context.env.set("DATABASE_URL", "postgresql://timeout:timeout@nonexistent:5432/timeout_db", source="test")
            context.env.set("DATABASE_INITIALIZATION_TIMEOUT", "5.0", source="test")
            
            # Test lifespan manager behavior during database timeout
            async def test_lifespan_timeout():
                async with lifespan(app):
                    pass  # Should never reach here due to database timeout
            
            # This should raise DeterministicStartupError from lifespan manager
            with pytest.raises(DeterministicStartupError) as exc_info:
                await test_lifespan_timeout()
            
            # Verify lifespan manager preserved the database timeout error
            error_message = str(exc_info.value)
            lifespan_timeout_indicators = ["database", "timeout", "deterministic"]
            
            has_lifespan_indicators = any(indicator in error_message.lower() for indicator in lifespan_timeout_indicators)
            if not has_lifespan_indicators:
                pytest.fail(
                    f"Issue #1278 lifespan timeout handling gap: "
                    f"Lifespan manager didn't preserve database timeout context. "
                    f"Error: {error_message}"
                )

    @pytest.mark.integration
    @pytest.mark.database_timeout
    @pytest.mark.timeout_reproduction
    def test_startup_failure_recovery_behavior(self):
        """
        Test startup failure recovery behavior with real components.
        
        Expected: TEST FAILURE - Recovery behavior not working correctly
        """
        app = FastAPI()
        
        with self.isolated_helper.create_isolated_context("recovery_test") as context:
            context.env.set("ENVIRONMENT", "staging", source="test")
            # Use invalid database URL to trigger connection failure
            context.env.set("DATABASE_URL", "postgresql://invalid:invalid@localhost:9999/nonexistent", source="test")
            
            orchestrator = StartupOrchestrator(app)
            
            # First attempt should fail
            with pytest.raises(DeterministicStartupError):
                asyncio.run(orchestrator.initialize_system())
            
            # Check failure state is properly recorded
            assert orchestrator.app.state.startup_failed is True
            assert len(orchestrator.failed_phases) > 0
            
            # Verify app state reflects the failure
            startup_error = getattr(orchestrator.app.state, 'startup_error', None)
            if not startup_error or "database" not in startup_error.lower():
                pytest.fail(
                    f"Issue #1278 recovery state gap: "
                    f"Startup failure state not properly recorded. "
                    f"Startup error: {startup_error}"
                )

    @pytest.mark.integration
    @pytest.mark.database_timeout
    @pytest.mark.timeout_reproduction
    def test_database_manager_real_timeout_integration(self):
        """
        Test DatabaseManager real timeout behavior with integration components.
        
        Expected: TEST FAILURE - DatabaseManager integration timeout not handled
        """
        app = FastAPI()
        
        with self.isolated_helper.create_isolated_context("db_manager_timeout") as context:
            context.env.set("ENVIRONMENT", "staging", source="test")
            # Configure very short timeout to trigger failure
            context.env.set("DATABASE_INITIALIZATION_TIMEOUT", "1.0", source="test")
            context.env.set("DATABASE_URL", "postgresql://slow:slow@localhost:5434/slow_db", source="test")
            
            orchestrator = StartupOrchestrator(app)
            
            # Measure timeout behavior
            start_time = time.time()
            
            with pytest.raises(DeterministicStartupError) as exc_info:
                asyncio.run(orchestrator._phase3_database_setup())
            
            elapsed_time = time.time() - start_time
            
            # Verify timeout occurred within expected timeframe (1-3 seconds)
            if elapsed_time > 5.0:
                pytest.fail(
                    f"Issue #1278 timeout behavior gap: "
                    f"Database timeout took {elapsed_time:.2f}s, expected ~1-3s timeout"
                )
            
            # Verify error includes timeout information
            error_message = str(exc_info.value)
            if "timeout" not in error_message.lower():
                pytest.fail(
                    f"Issue #1278 timeout error preservation gap: "
                    f"Timeout error not preserved in DeterministicStartupError: {error_message}"
                )

    @pytest.mark.integration
    @pytest.mark.database_timeout
    @pytest.mark.timeout_reproduction
    async def test_container_environment_timeout_behavior(self):
        """
        Test container environment timeout behavior with real environment constraints.
        
        Expected: TEST FAILURE - Container environment constraints not properly handled
        """
        app = FastAPI()
        
        with self.isolated_helper.create_isolated_context("container_timeout") as context:
            # Simulate container environment variables
            context.env.set("ENVIRONMENT", "staging", source="container")
            context.env.set("CLOUD_PLATFORM", "CLOUD_RUN", source="container")
            context.env.set("DATABASE_URL", "postgresql://container:test@cloud-sql:5432/staging", source="container")
            
            # Set container-like timeout constraints
            context.env.set("CONTAINER_STARTUP_TIMEOUT", "30", source="container")
            context.env.set("DATABASE_INITIALIZATION_TIMEOUT", "20.0", source="container")
            
            orchestrator = StartupOrchestrator(app)
            
            # Test startup under container constraints
            start_time = time.time()
            
            try:
                await asyncio.wait_for(
                    orchestrator.initialize_system(),
                    timeout=25.0  # Container timeout constraint
                )
                # If we get here, the test should check if startup actually succeeded
                if not orchestrator.app.state.startup_complete:
                    pytest.fail(
                        f"Issue #1278 container startup gap: "
                        f"Startup completed but state not marked as complete"
                    )
            except (DeterministicStartupError, asyncio.TimeoutError) as e:
                elapsed_time = time.time() - start_time
                
                # This is expected - but check timing behavior
                if elapsed_time > 30.0:
                    pytest.fail(
                        f"Issue #1278 container timeout constraint violation: "
                        f"Startup took {elapsed_time:.2f}s, exceeded container limit of 30s"
                    )
                
                # Verify error context preserves container environment information
                error_message = str(e)
                container_indicators = ["staging", "timeout", "container"]
                
                has_container_context = any(indicator in error_message.lower() for indicator in container_indicators)
                if not has_container_context:
                    pytest.fail(
                        f"Issue #1278 container context gap: "
                        f"Container environment context not preserved in error. "
                        f"Error: {error_message}"
                    )

    @pytest.mark.integration
    @pytest.mark.database_timeout
    @pytest.mark.timeout_reproduction
    async def test_phase_transition_timing_under_timeout(self):
        """
        Test phase transition timing behavior under database timeout conditions.
        
        Expected: TEST FAILURE - Phase timing not tracked correctly during timeouts
        """
        app = FastAPI()
        
        with self.isolated_helper.create_isolated_context("phase_timing_test") as context:
            context.env.set("ENVIRONMENT", "staging", source="test")
            context.env.set("DATABASE_URL", "postgresql://timing:test@localhost:9999/timing_test", source="test")
            
            orchestrator = StartupOrchestrator(app)
            
            # Start phase tracking
            orchestrator._set_current_phase(StartupPhase.INIT)
            orchestrator._set_current_phase(StartupPhase.DEPENDENCIES) 
            orchestrator._set_current_phase(StartupPhase.DATABASE)
            
            start_time = time.time()
            
            try:
                await orchestrator._phase3_database_setup()
            except DeterministicStartupError:
                # Expected failure - check timing tracking
                pass
            
            elapsed_time = time.time() - start_time
            
            # Check phase timing tracking
            database_timing = orchestrator.phase_timings.get(StartupPhase.DATABASE, {})
            if not database_timing:
                pytest.fail(
                    f"Issue #1278 phase timing gap: "
                    f"Database phase timing not tracked during timeout failure"
                )
            
            # Check timing accuracy
            tracked_duration = database_timing.get('duration', 0.0)
            timing_tolerance = 2.0  # 2 second tolerance
            
            if abs(tracked_duration - elapsed_time) > timing_tolerance:
                pytest.fail(
                    f"Issue #1278 timing accuracy gap: "
                    f"Tracked duration {tracked_duration:.2f}s vs actual {elapsed_time:.2f}s "
                    f"exceeds tolerance of {timing_tolerance}s"
                )

    @pytest.mark.integration
    @pytest.mark.database_timeout
    @pytest.mark.timeout_reproduction 
    async def test_app_state_consistency_during_timeout_failure(self):
        """
        Test app state consistency during timeout failure scenarios.
        
        Expected: TEST FAILURE - App state not consistently updated during failures
        """
        app = FastAPI()
        
        with self.isolated_helper.create_isolated_context("state_consistency_test") as context:
            context.env.set("ENVIRONMENT", "staging", source="test")
            context.env.set("DATABASE_URL", "postgresql://state:test@localhost:9999/state_test", source="test")
            
            orchestrator = StartupOrchestrator(app)
            
            # Check initial state
            assert orchestrator.app.state.startup_in_progress is True
            assert orchestrator.app.state.startup_complete is False
            assert orchestrator.app.state.startup_failed is False
            
            # Trigger failure
            try:
                await orchestrator.initialize_system()
            except DeterministicStartupError:
                # Expected failure - check state consistency
                pass
            
            # Verify final state consistency
            final_state_checks = [
                (orchestrator.app.state.startup_in_progress, True, "startup_in_progress should remain True during failure"),
                (orchestrator.app.state.startup_complete, False, "startup_complete should be False after failure"),
                (orchestrator.app.state.startup_failed, True, "startup_failed should be True after failure")
            ]
            
            for actual, expected, description in final_state_checks:
                if actual != expected:
                    pytest.fail(
                        f"Issue #1278 state consistency gap: {description}. "
                        f"Expected {expected}, got {actual}"
                    )
            
            # Check error preservation
            startup_error = getattr(orchestrator.app.state, 'startup_error', None)
            if not startup_error:
                pytest.fail(
                    f"Issue #1278 error preservation gap: "
                    f"Startup error not preserved in app.state after failure"
                )

    @pytest.mark.integration
    @pytest.mark.database_timeout  
    @pytest.mark.timeout_reproduction
    async def test_cleanup_behavior_after_database_timeout(self):
        """
        Test cleanup behavior after database timeout failure.
        
        Expected: TEST FAILURE - Cleanup not properly executed after timeout
        """
        app = FastAPI()
        
        with self.isolated_helper.create_isolated_context("cleanup_test") as context:
            context.env.set("ENVIRONMENT", "staging", source="test")
            context.env.set("DATABASE_URL", "postgresql://cleanup:test@localhost:9999/cleanup_test", source="test")
            
            orchestrator = StartupOrchestrator(app)
            
            # Set some app state that should be cleaned up
            app.state.test_resource = "should_be_cleaned"
            app.state.database_available = True
            
            # Trigger failure and check cleanup
            try:
                await orchestrator.initialize_system()
            except DeterministicStartupError:
                # Expected failure
                pass
            
            # Check if appropriate cleanup occurred
            # Note: This test might need to be adapted based on actual cleanup implementation
            if hasattr(app.state, 'database_available') and app.state.database_available is True:
                pytest.fail(
                    f"Issue #1278 cleanup gap: "
                    f"Database availability flag not reset after timeout failure"
                )
            
            # Verify thread cleanup manager behavior (if in production mode)
            if orchestrator.thread_cleanup_manager:
                # Check if cleanup manager is still functioning
                cleanup_status = orchestrator.thread_cleanup_manager.get_status()
                if cleanup_status.get('has_leaked_threads', False):
                    pytest.fail(
                        f"Issue #1278 thread cleanup gap: "
                        f"Thread leaks detected after database timeout failure: {cleanup_status}"
                    )