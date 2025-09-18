"""
E2E Tests for Issue #1278 - SMD Phase 3 Cascade Failure Reproduction

These tests reproduce the exact Issue #1278 failure scenario in real GCP staging environment
to validate that the Issue #1263 fix was incomplete for deeper infrastructure constraints.

Expected Result: Tests should FAIL initially, reproducing exact Issue #1278 symptoms
"""

import asyncio
import pytest
import time
from typing import Dict, List
from fastapi import FastAPI
from test_framework.base_e2e_test import BaseE2ETest

class TestIssue1278SmdCascadeFailure(BaseE2ETest):
    """E2E tests reproducing Issue #1278 SMD cascade failure in real GCP environment."""
    
    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    @pytest.mark.issue_1278_reproduction
    async def test_smd_phase3_failure_under_cloud_sql_load(self):
        """
        Reproduce SMD Phase 3 failure under real Cloud SQL capacity pressure.
        
        This test intentionally creates load conditions that expose the infrastructure
        constraints Issue #1263 fix didn't address.
        
        Expected: TEST FAILURE - Reproducing exact Issue #1278 startup failure
        """
        # Create multiple FastAPI applications to simulate concurrent startup load
        # This reproduces the conditions that cause Issue #1278 in production
        
        apps = []
        failure_count = 0
        successful_startups = 0
        startup_times = []
        
        async def attempt_app_startup(app_index: int) -> Dict:
            """Attempt application startup and measure timing."""
            app = FastAPI()
            start_time = time.time()
            
            try:
                from netra_backend.app.smd import StartupOrchestrator
                orchestrator = StartupOrchestrator(app)
                
                # Phase 1 & 2 should succeed
                await orchestrator._phase1_foundation()
                await orchestrator._phase2_core_services()
                
                # Phase 3 is where Issue #1278 manifests under load
                await orchestrator._phase3_database_setup()
                
                startup_time = time.time() - start_time
                return {
                    "app_index": app_index,
                    "status": "success", 
                    "startup_time": startup_time,
                    "phase3_status": "completed"
                }
                
            except Exception as e:
                startup_time = time.time() - start_time
                return {
                    "app_index": app_index,
                    "status": "failed",
                    "startup_time": startup_time,
                    "error": str(e),
                    "phase3_status": "failed"
                }
        
        # Create concurrent startup attempts to stress Cloud SQL
        concurrent_startups = 5  # Simulate multiple service instances starting
        tasks = []
        
        for i in range(concurrent_startups):
            task = asyncio.create_task(attempt_app_startup(i))
            tasks.append(task)
        
        # Wait for all startup attempts
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for Issue #1278 patterns
        for result in results:
            if isinstance(result, dict):
                startup_times.append(result["startup_time"])
                if result["status"] == "failed":
                    failure_count += 1
                    # Check if this matches Issue #1278 error pattern
                    if "timeout" in result.get("error", "").lower():
                        pytest.fail(
                            f"Issue #1278 reproduced: App {result['app_index']} failed with timeout "
                            f"after {result['startup_time']:.1f}s: {result['error']}"
                        )
                else:
                    successful_startups += 1
        
        # Check for Issue #1278 indicators
        failure_rate = failure_count / len(results)
        avg_startup_time = sum(startup_times) / len(startup_times) if startup_times else 0
        
        # CRITICAL TEST: High failure rate or slow startup indicates Issue #1278 conditions
        if failure_rate > 0.2:  # >20% failure rate
            pytest.fail(
                f"Issue #1278 cascade failure reproduced: "
                f"{failure_rate:.1%} failure rate ({failure_count}/{len(results)}) "
                f"with average startup time {avg_startup_time:.1f}s"
            )
        
        if avg_startup_time > 30.0:  # Slower than reasonable startup
            pytest.fail(
                f"Issue #1278 slow startup pattern: "
                f"Average startup time {avg_startup_time:.1f}s indicates infrastructure constraints"
            )
    
    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_fastapi_lifespan_error_context_loss(self):
        """
        Test FastAPI lifespan error context preservation during SMD failures.
        
        Expected: TEST FAILURE - Error context lost during startup failures
        """
        from netra_backend.app.core.lifespan_manager import lifespan
        from netra_backend.app.smd import DeterministicStartupError
        
        app = FastAPI()
        error_context_preserved = False
        original_error_message = None
        
        # Simulate the exact Issue #1278 scenario
        try:
            async with lifespan(app):
                # This should trigger the exact failure path from Issue #1278
                pass
        except DeterministicStartupError as e:
            original_error_message = str(e)
            # Check if error context is preserved
            if "Phase 3" in original_error_message or "database" in original_error_message.lower():
                error_context_preserved = True
        except Exception as e:
            original_error_message = str(e)
        
        # Verify app state contains error information
        startup_error = getattr(app.state, 'startup_error', None)
        startup_failed = getattr(app.state, 'startup_failed', False)
        
        if not error_context_preserved:
            pytest.fail(
                f"Issue #1278 error context loss: "
                f"FastAPI lifespan error context not preserved. "
                f"Original error: {original_error_message}, "
                f"App state error: {startup_error}, "
                f"App state failed: {startup_failed}"
            )
    
    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_container_exit_code_3_reproduction(self):
        """
        Reproduce the container exit code 3 behavior from Issue #1278.
        
        Expected: TEST FAILURE - Container exit behavior indicates startup failure
        """
        # This test simulates the container behavior that produces exit code 3
        # when SMD Phase 3 fails
        
        startup_failed = False
        exit_code = 0
        
        try:
            app = FastAPI()
            from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError
            
            orchestrator = StartupOrchestrator(app)
            await orchestrator.initialize_system()
            
        except DeterministicStartupError:
            startup_failed = True
            exit_code = 3  # The exit code from Issue #1278 logs
        except Exception:
            startup_failed = True
            exit_code = 1  # Generic failure
        
        if startup_failed and exit_code == 3:
            pytest.fail(
                f"Issue #1278 container exit code 3 reproduced: "
                f"SMD startup failure resulted in exit code {exit_code}, "
                f"indicating cascading failure pattern identical to Issue #1278"
            )

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_smd_phase_timing_cascade_failure(self):
        """
        Test SMD phase timing cascade failure under infrastructure pressure.
        
        Expected: TEST FAILURE - Phase timing cascades cause total startup failure
        """
        from netra_backend.app.smd import StartupOrchestrator, StartupPhase
        from fastapi import FastAPI
        
        app = FastAPI()
        orchestrator = StartupOrchestrator(app)
        
        phase_timings = {}
        total_startup_time = 0
        failed_phases = []
        
        try:
            # Track timing for each phase to identify cascade patterns
            start_time = time.time()
            
            # Phase 1: Should complete quickly
            phase1_start = time.time()
            await orchestrator._phase1_foundation()
            phase_timings['phase1'] = time.time() - phase1_start
            
            # Phase 2: Should complete reasonably
            phase2_start = time.time()
            await orchestrator._phase2_core_services()
            phase_timings['phase2'] = time.time() - phase2_start
            
            # Phase 3: This is where Issue #1278 manifests
            phase3_start = time.time()
            await orchestrator._phase3_database_setup()
            phase_timings['phase3'] = time.time() - phase3_start
            
            total_startup_time = time.time() - start_time
            
        except Exception as e:
            total_startup_time = time.time() - start_time
            current_phase = getattr(orchestrator, 'current_phase', None)
            if current_phase:
                failed_phases.append(current_phase.value)
        
        # Analyze timing patterns for Issue #1278 cascade indicators
        phase3_time = phase_timings.get('phase3', 0)
        
        # CRITICAL TEST: Long Phase 3 time indicates infrastructure constraints
        if phase3_time > 20.0:  # Issue #1278 manifests with >20s Phase 3 time
            pytest.fail(
                f"Issue #1278 SMD Phase 3 cascade failure reproduced: "
                f"Phase 3 took {phase3_time:.1f}s (>{20.0}s threshold), "
                f"total startup time {total_startup_time:.1f}s, "
                f"failed phases: {failed_phases}"
            )

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_deterministic_startup_graceful_degradation_failure(self):
        """
        Test deterministic startup graceful degradation failure patterns.
        
        Expected: TEST FAILURE - Deterministic startup doesn't gracefully degrade
        """
        from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError
        from fastapi import FastAPI
        
        app = FastAPI()
        orchestrator = StartupOrchestrator(app)
        
        degraded_startup_attempted = False
        deterministic_failure_occurred = False
        
        try:
            # Attempt full deterministic startup
            await orchestrator.initialize_system()
            
        except DeterministicStartupError as e:
            deterministic_failure_occurred = True
            error_message = str(e)
            
            # Check if startup attempted graceful degradation
            if hasattr(app.state, 'startup_degraded_mode'):
                degraded_startup_attempted = True
        
        # CRITICAL TEST: Deterministic startup should not allow degraded mode
        # Issue #1278 occurs because there's no graceful degradation for infrastructure constraints
        if deterministic_failure_occurred and not degraded_startup_attempted:
            pytest.fail(
                f"Issue #1278 deterministic startup rigidity: "
                f"Deterministic startup failed without graceful degradation option, "
                f"causing complete service unavailability instead of partial functionality"
            )