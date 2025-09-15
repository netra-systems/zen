"""
Performance Testing Package for Agent Orchestration System

This package provides comprehensive performance testing capabilities for the
multi-agent orchestration system, including:

- Individual agent execution benchmarks
- Multi-agent pipeline performance aggregation
- Memory and resource utilization tracking
- Token consumption and cost analysis
- Load testing and scalability validation
- Performance degradation detection

Business Value:
- Ensures SLA compliance for Enterprise customers
- Prevents performance-related churn
- Validates scalability for growth scenarios
- Provides cost optimization insights
"""

__version__ = "1.0.0"
__author__ = "Netra AI Platform Team"

# Performance test categories for pytest markers
PERFORMANCE_TEST_CATEGORIES = {
    "performance": "All performance tests",
    "benchmarks": "Performance benchmark tests",
    "load": "Load testing scenarios", 
    "memory": "Memory usage tests",
    "scalability": "Scalability validation tests",
    "cost": "Cost analysis tests"
}

# Default test configuration
DEFAULT_PERFORMANCE_CONFIG = {
    "concurrent_pipelines": 5,
    "test_duration_seconds": 30,
    "memory_threshold_mb": 1024,
    "response_time_threshold_ms": 5000,
    "success_rate_threshold": 0.8
}
