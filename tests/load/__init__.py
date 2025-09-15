"""Production Load Tests for Concurrent Agent Persistence

This package contains comprehensive production-grade load tests that validate
the platform's ability to handle enterprise-scale concurrent agent workloads
with production performance requirements.

Test Categories:
- Baseline concurrent agent execution (100+ agents)
- Mixed read/write workload patterns
- State size scalability testing
- Sustained load simulation (24-hour patterns)
- Burst traffic and spike handling
- Resource exhaustion scenarios
- Performance SLA compliance validation
- Failure recovery under load

Business Value:
- Validates $50K+ MRR Enterprise workload capabilities
- Ensures 99.9% uptime SLA compliance
- Prevents performance-related customer churn
- Validates enterprise scalability claims

Usage:
    pytest tests/load/ -m load -v --asyncio-mode=auto

Requirements:
- Real Redis, PostgreSQL, and ClickHouse connections
- Sufficient system resources for load testing
- Production-like environment configuration
"""

# Test markers for pytest
load_tests = [
    "test_100_concurrent_agents_baseline",
    "test_mixed_workload_read_write_patterns", 
    "test_state_size_scalability",
    "test_sustained_load_24_hours_simulation",
    "test_burst_traffic_handling",
    "test_redis_connection_pool_exhaustion",
    "test_postgres_checkpoint_under_load",
    "test_memory_usage_under_load",
    "test_latency_sla_compliance",
    "test_failure_recovery_under_load"
]

__all__ = ["load_tests"]
