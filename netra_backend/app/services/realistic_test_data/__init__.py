"""Realistic Test Data Service Module

Generates production-like test data for comprehensive testing.
This module addresses gaps identified in test realism analysis and provides
realistic patterns for LLM responses, logs, workloads, and performance scenarios.
"""

from typing import Dict, List, Any, Optional

from netra_backend.app.models import RealisticDataPatterns, RealisticTestDataConfigManager
from netra_backend.app.llm_response_generator import LLMResponseGenerator
from netra_backend.app.log_generator import LogGenerator
from netra_backend.app.workload_simulator import WorkloadSimulator
from netra_backend.app.performance_simulator import PerformanceSimulator


class RealisticTestDataService:
    """Service for generating realistic test data that mimics production patterns"""
    
    def __init__(self):
        """Initialize the realistic test data service"""
        self.config_manager = RealisticTestDataConfigManager()
        self.llm_generator = LLMResponseGenerator(self.config_manager)
        self.log_generator = LogGenerator(self.config_manager)
        self.workload_simulator = WorkloadSimulator()
        self.performance_simulator = PerformanceSimulator()
    
    def generate_realistic_llm_response(
        self,
        model: str = "gpt-4",
        prompt_tokens: Optional[int] = None,
        include_errors: bool = True
    ) -> Dict[str, Any]:
        """Generate a realistic LLM response with production-like characteristics"""
        return self.llm_generator.generate_realistic_llm_response(model, prompt_tokens, include_errors)
    
    def generate_realistic_log_data(
        self,
        pattern: str = "normal_operation",
        duration_hours: int = 24,
        volume: int = 10000
    ) -> List[Dict[str, Any]]:
        """Generate realistic log data with specific patterns"""
        return self.log_generator.generate_realistic_log_data(pattern, duration_hours, volume)
    
    def generate_workload_simulation(
        self,
        workload_type: str = "ecommerce",
        duration_days: int = 7,
        include_seasonality: bool = True
    ) -> Dict[str, Any]:
        """Generate realistic workload simulation data"""
        return self.workload_simulator.generate_workload_simulation(workload_type, duration_days, include_seasonality)
    
    def simulate_performance_degradation(
        self,
        base_metrics: Dict[str, float],
        scenario: str = "cascading_failure",
        duration_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Simulate performance degradation over time"""
        return self.performance_simulator.simulate_performance_degradation(base_metrics, scenario, duration_minutes)
    
    def simulate_bottleneck_analysis(self, service_metrics: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Simulate bottleneck analysis across services"""
        return self.performance_simulator.simulate_bottleneck_analysis(service_metrics)


__all__ = [
    "RealisticTestDataService",
    "RealisticDataPatterns",
    "RealisticTestDataConfigManager",
    "LLMResponseGenerator",
    "LogGenerator",
    "WorkloadSimulator",
    "PerformanceSimulator"
]