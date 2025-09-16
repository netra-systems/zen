"""
Performance Testing Utilities

Provides specialized utilities for performance testing with concurrency.
Follows SPEC/testing.xml requirements (8-line function limit, real dependencies).

Business Value Justification (BVJ):
- Segment: Enterprise, Mid-tier customers  
- Business Goal: Platform Scalability, Performance SLA Compliance
- Value Impact: Enables $100K+ enterprise deals, prevents performance degradation
- Strategic/Revenue Impact: Critical for enterprise sales, prevents SLA breaches
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    """Result of a load test execution"""
    load_level: int
    success: bool
    duration: float
    error_message: str = None


class PerformanceTestOrchestrator:
    """Orchestrates performance testing scenarios"""
    
    def __init__(self, scenario_runner, performance_analyzer):
        self.scenario_runner = scenario_runner
        self.performance_analyzer = performance_analyzer
    
    async def test_run_load_test_sequence(self, load_levels: List[int]) -> Dict[int, Any]:
        """Run performance tests across multiple load levels"""
        performance_results = {}
        
        for load in load_levels:
            result = await self._execute_single_load_test(load)
            performance_results[load] = result
        
        return performance_results
    
    async def _execute_single_load_test(self, load: int):
        """Execute performance test at single load level"""
        logger.info(f"Testing load level: {load} concurrent users")
        perf_result = await self.scenario_runner.run_performance_scenario(load)
        await asyncio.sleep(5.0)  # Allow system to stabilize
        return perf_result


class StressTestOrchestrator:
    """Orchestrates stress testing scenarios"""
    
    def __init__(self, stress_generator, config):
        self.stress_generator = stress_generator
        self.config = config
    
    async def run_multi_stress_test(self) -> Tuple[List[Any], float]:
        """Run multiple types of stress tests concurrently"""
        duration = self.config.stress_test_duration
        stress_tasks = self._create_stress_task_list(duration // 3)
        
        start_time = time.time()
        stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        actual_duration = time.time() - start_time
        
        return stress_results, actual_duration
    
    def _create_stress_task_list(self, duration: int) -> List:
        """Create list of stress testing tasks"""
        return [
            self.stress_generator.generate_user_bursts(duration),
            self.stress_generator.generate_database_stress(duration),
            self.stress_generator.generate_cache_stress(duration)
        ]


class ResourceMonitoringHelper:
    """Helper for resource monitoring during tests"""
    
    def __init__(self, monitor_class):
        self.monitor_class = monitor_class
        self.monitor = None
    
    async def start_monitoring(self):
        """Start resource monitoring with standard configuration"""
        self.monitor = self.monitor_class(interval_seconds=2.0)
        await self.monitor.start()
    
    async def stop_monitoring(self):
        """Stop resource monitoring and return statistics"""
        if self.monitor:
            stats = await self.monitor.stop()
            self.monitor = None
            return stats
        return None


class TestResultValidator:
    """Validates test results against requirements"""
    
    def __init__(self, config):
        self.config = config
    
    def validate_resilience_score(self, score: float, min_threshold: float = 0.8):
        """Validate system resilience score meets minimum threshold"""
        assert score >= min_threshold, f"System resilience too low: {score:.3f}"
    
    def validate_test_duration(self, actual_duration: float, max_multiplier: float = 1.2):
        """Validate test completed within acceptable time"""
        max_duration = self.config.stress_test_duration * max_multiplier
        assert actual_duration <= max_duration, f"Test took too long: {actual_duration:.1f}s"
    
    def validate_user_session_results(self, results: List[Any], min_success_rate: float = 0.95):
        """Validate user session results meet success rate requirements"""
        if not results:
            return
        
        successful = sum(1 for r in results if getattr(r, 'success', False))
        success_rate = successful / len(results)
        assert success_rate >= min_success_rate, f"Success rate too low: {success_rate:.3f}"
    
    def validate_no_cross_contamination(self, results: List[Any]):
        """Validate no cross-user contamination occurred"""
        contaminated = sum(1 for r in results if getattr(r, 'cross_contamination', False))
        assert contaminated == 0, f"Cross-contamination detected: {contaminated} instances"


def create_session_result_converter():
    """Factory function for session result converter"""
    from tests.e2e.test_helpers.concurrency_base import UserSessionResult
    
    def convert_dict_to_session_result(result_dict: Dict[str, Any]) -> UserSessionResult:
        """Convert dictionary to UserSessionResult object"""
        return UserSessionResult(
            user_id=result_dict.get("user_id", 0),
            success=result_dict.get("success", False),
            session_time=result_dict.get("session_time", 0.0),
            cross_contamination=result_dict.get("cross_contamination", False),
            actions_completed=result_dict.get("actions_completed", 0),
            error=result_dict.get("error")
        )
    
    return convert_dict_to_session_result
