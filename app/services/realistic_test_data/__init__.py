"""Realistic Test Data Service Module

Generates production-like test data for comprehensive testing.
This module addresses gaps identified in test realism analysis and provides
realistic patterns for LLM responses, logs, workloads, and performance scenarios.
"""

from .models import RealisticDataPatterns, ConfigManager
from .llm_response_generator import LLMResponseGenerator
from .log_generator import LogGenerator
from .workload_simulator import WorkloadSimulator
from .performance_simulator import PerformanceSimulator


class RealisticTestDataService:
    """Service for generating realistic test data that mimics production patterns"""
    
    def __init__(self):
        """Initialize the realistic test data service"""
        self.config_manager = ConfigManager()
        self.llm_generator = LLMResponseGenerator(self.config_manager)
        self.log_generator = LogGenerator(self.config_manager)
        self.workload_simulator = WorkloadSimulator()
        self.performance_simulator = PerformanceSimulator()
    
    def generate_realistic_llm_response(self, *args, **kwargs):
        """Generate a realistic LLM response with production-like characteristics"""
        return self.llm_generator.generate_realistic_llm_response(*args, **kwargs)
    
    def generate_realistic_log_data(self, *args, **kwargs):
        """Generate realistic log data with specific patterns"""
        return self.log_generator.generate_realistic_log_data(*args, **kwargs)
    
    def generate_workload_simulation(self, *args, **kwargs):
        """Generate realistic workload simulation data"""
        return self.workload_simulator.generate_workload_simulation(*args, **kwargs)
    
    def simulate_performance_degradation(self, *args, **kwargs):
        """Simulate performance degradation over time"""
        return self.performance_simulator.simulate_performance_degradation(*args, **kwargs)
    
    def simulate_bottleneck_analysis(self, *args, **kwargs):
        """Simulate bottleneck analysis across services"""
        return self.performance_simulator.simulate_bottleneck_analysis(*args, **kwargs)


__all__ = [
    "RealisticTestDataService",
    "RealisticDataPatterns",
    "ConfigManager",
    "LLMResponseGenerator",
    "LogGenerator",
    "WorkloadSimulator",
    "PerformanceSimulator"
]