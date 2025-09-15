"""
Main Concurrency and Isolation Test Suite - E2E Implementation

This file replaces the original test_concurrency_isolation.py that exceeded
size limits. Concurrency and isolation tests are now organized in focused modules.

Business Value Justification (BVJ):
- Segment: Enterprise, Mid-tier customers  
- Business Goal: Platform Scalability, Multi-tenant Security, System Stability
- Value Impact: Enables $100K+ enterprise deals, prevents catastrophic failures
- Strategic/Revenue Impact: Critical for enterprise sales, prevents security breaches

The original file was refactored into focused modules:
- test_concurrent_agent_startup.py - Agent startup isolation
- test_concurrent_authentication.py - Auth race conditions
- test_concurrent_database_pools.py - Database connection management
- test_concurrent_cache_contention.py - Cache contention handling
"""

import asyncio
import logging
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.fixtures.concurrency_scenarios import (
    ConcurrencyScenarioRunner,
    get_load_levels_for_scaling,
)
from tests.e2e.test_helpers.concurrency_base import (
    ConcurrencyTestBase,
    ConcurrencyTestConfig,
    PerformanceAnalyzer,
    StressTestGenerator,
)
from tests.e2e.test_helpers.performance_testing import (
    PerformanceTestOrchestrator,
    ResourceMonitoringHelper,
    StressTestOrchestrator,
    TestResultValidator,
    create_session_result_converter,
)
from tests.e2e.test_helpers.resource_monitoring import ResourceMonitor

logger = logging.getLogger(__name__)


class ConcurrencyIsolationIntegrationTests:
    """Integration tests for concurrency and isolation system"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = ConcurrencyTestConfig()
        self.base = ConcurrencyTestBase(self.config)
        self.scenario_runner = ConcurrencyScenarioRunner(self.config)
        self._setup_orchestrators()
        self.result_validator = TestResultValidator(self.config)
        self.convert_session_result = create_session_result_converter()
    
    def _setup_orchestrators(self):
        """Setup performance and stress test orchestrators"""
        self.performance_orchestrator = PerformanceTestOrchestrator(self.scenario_runner, PerformanceAnalyzer())
        self.stress_orchestrator = StressTestOrchestrator(StressTestGenerator(), self.config)
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(600)
    async def test_100_concurrent_user_isolation(self):
        """Test isolation with 100+ concurrent users"""
        logger.info("Testing 100+ concurrent user isolation")
        user_results = await self._run_user_isolation_test()
        self._validate_isolation_results(user_results)
        logger.info("100+ user isolation validated")
    
    @pytest.mark.asyncio
    async def test_performance_under_concurrent_load(self):
        """Test performance characteristics under concurrent load"""
        logger.info("Testing performance under concurrent load")
        performance_results = await self._run_performance_scaling_test()
        self.performance_analyzer.validate_performance_scaling(performance_results)
        logger.info("Performance under concurrent load validated")
    
    @pytest.mark.asyncio
    async def test_system_resilience_under_stress(self):
        """Test overall system resilience under stress conditions"""
        logger.info("Testing system resilience under stress")
        stress_results, actual_duration = await self._run_stress_resilience_test()
        resilience_score = PerformanceAnalyzer().calculate_resilience_score(stress_results)
        self._validate_resilience_requirements(resilience_score, actual_duration)
        logger.info(f"System resilience validated: {resilience_score:.3f} score")
    
    async def _run_user_isolation_test(self) -> List[Dict[str, Any]]:
        """Run user isolation test with resource monitoring"""
        monitor_helper = ResourceMonitoringHelper(ResourceMonitor)
        await monitor_helper.start_monitoring()
        try:
            return await self._execute_user_isolation_scenario()
        finally:
            await monitor_helper.stop_monitoring()
    
    def _validate_isolation_results(self, user_results: List[Dict[str, Any]]):
        """Validate isolation test results meet requirements"""
        converted_results = [self.convert_session_result(r) for r in user_results]
        self.result_validator.validate_user_session_results(converted_results)
        self.result_validator.validate_no_cross_contamination(converted_results)
    
    
    async def _run_performance_scaling_test(self) -> Dict[int, Any]:
        """Run performance scaling test across load levels"""
        load_levels = get_load_levels_for_scaling()
        return await self.performance_orchestrator.run_load_test_sequence(load_levels)
    
    async def _run_stress_resilience_test(self) -> tuple:
        """Run stress resilience test with multiple stress types"""
        return await self.stress_orchestrator.run_multi_stress_test()
    
    
    def _validate_resilience_requirements(self, resilience_score: float, actual_duration: float):
        """Validate resilience test meets performance requirements"""
        self.result_validator.validate_resilience_score(resilience_score)
        self.result_validator.validate_test_duration(actual_duration)
    
    async def _execute_user_isolation_scenario(self) -> List[Dict[str, Any]]:
        """Execute user isolation scenario with configured parameters"""
        return await self.scenario_runner.run_user_isolation_scenario(
            self.config.max_concurrent_users
        )
    
