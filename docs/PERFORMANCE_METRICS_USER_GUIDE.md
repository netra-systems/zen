# Performance Metrics and Timing User Guide

## Overview

The Netra Platform Performance Metrics system provides comprehensive timing collection, performance analysis, and metrics aggregation capabilities. This guide explains how to use these features to monitor and optimize agent execution performance.

**Business Value**: 20-30% performance improvement through granular visibility and optimization insights.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Components](#core-components)
3. [Using Timing Collectors](#using-timing-collectors)
4. [Performance Metrics](#performance-metrics)
5. [Metrics Aggregation](#metrics-aggregation)
6. [Integration with Agents](#integration-with-agents)
7. [Analyzing Performance](#analyzing-performance)
8. [Best Practices](#best-practices)
9. [API Reference](#api-reference)
10. [Related Documentation](#related-documentation)

## Quick Start

### Basic Usage

```python
from uuid import uuid4
from netra_backend.app.core.performance_metrics import EnhancedExecutionTimingCollector

# Create a timing collector for your execution
execution_id = uuid4()
collector = EnhancedExecutionTimingCollector(
    execution_id=execution_id,
    agent_name="my_agent"
)

# Track execution phases
collector.start_phase("initialization")
# ... initialization code ...
collector.stop_phase("initialization")

collector.start_phase("tool_execution")
# ... tool execution code ...
collector.stop_phase("tool_execution")

# Record Time to First Token
collector.record_first_token()

# Get performance breakdown
breakdown = collector.get_breakdown()
print(f"Total execution: {breakdown.total_ms}ms")
print(f"Efficiency: {breakdown.calculate_efficiency()}%")
```

## Core Components

### 1. EnhancedExecutionTimingCollector

The main component for collecting detailed timing information during agent execution.

**Key Features:**
- Phase-based timing tracking
- Time to First Token (TTFT) measurement
- Parallel task tracking
- Automatic metric generation

### 2. TimingBreakdown

Provides detailed breakdown of execution timings across different phases.

**Tracked Phases:**
- `initialization_ms` - Setup and configuration time
- `tool_execution_ms` - Tool invocation time
- `llm_processing_ms` - LLM API call time
- `websocket_notification_ms` - Real-time notification overhead
- `database_query_ms` - Database operation time
- `external_api_ms` - External API call time
- `queue_wait_ms` - Queue processing wait time
- `overhead_ms` - Framework overhead

### 3. MetricsAggregator

Aggregates performance metrics across multiple executions for trend analysis.

**Aggregation Windows:**
- MINUTE (60s)
- FIVE_MINUTES (300s)
- HOUR (3600s)
- DAY (86400s)
- WEEK (604800s)

## Using Timing Collectors

### Basic Phase Tracking

```python
from netra_backend.app.core.performance_metrics import EnhancedExecutionTimingCollector
from uuid import uuid4

collector = EnhancedExecutionTimingCollector(
    execution_id=uuid4(),
    agent_name="data_analysis_agent"
)

# Start and stop phases
collector.start_phase("data_loading")
# ... load data ...
duration = collector.stop_phase("data_loading")
print(f"Data loading took {duration}ms")
```

### Nested Phase Tracking

```python
# Phases can be nested for detailed tracking
collector.start_phase("main_processing")
    
    collector.start_phase("preprocessing")
    # ... preprocessing ...
    collector.stop_phase("preprocessing")
    
    collector.start_phase("analysis")
    # ... analysis ...
    collector.stop_phase("analysis")
    
collector.stop_phase("main_processing")
```

### Parallel Task Tracking

```python
# Track parallel operations
import asyncio

async def parallel_operations(collector):
    # Start parallel tasks
    task1 = collector.start_parallel_task("api_call_1")
    task2 = collector.start_parallel_task("api_call_2")
    
    # Execute in parallel
    results = await asyncio.gather(
        api_call_1(),
        api_call_2()
    )
    
    # Stop tracking
    collector.stop_parallel_task("api_call_1")
    collector.stop_parallel_task("api_call_2")
    
    return results
```

### Time to First Token (TTFT)

```python
# Record when the first response token is generated
collector.start_phase("llm_processing")

# When first token arrives from LLM
ttft = collector.record_first_token()
print(f"Time to First Token: {ttft}ms")

# Continue processing...
collector.stop_phase("llm_processing")
```

## Performance Metrics

### Creating Custom Metrics

```python
from netra_backend.app.core.performance_metrics import MetricType

# Add custom performance metrics
collector.add_metric(
    metric_type=MetricType.DATABASE_QUERY,
    value=125.5,  # milliseconds
    metadata={"query": "SELECT * FROM agents", "rows": 42}
)

collector.add_metric(
    metric_type=MetricType.EXTERNAL_API,
    value=850.0,
    metadata={"endpoint": "/api/v1/analyze", "status": 200}
)
```

### Metric Types

Available metric types in `MetricType` enum:
- `TTFT` - Time to first token
- `TOTAL_EXECUTION` - Total execution time
- `QUEUE_WAIT` - Queue waiting time
- `DATABASE_QUERY` - Database query time
- `EXTERNAL_API` - External API call time
- `WEBSOCKET_LATENCY` - WebSocket notification latency
- `INITIALIZATION` - Initialization time
- `TOOL_EXECUTION` - Tool execution time
- `LLM_PROCESSING` - LLM processing time
- `MEMORY_USAGE` - Memory utilization
- `THREAD_POOL_USAGE` - Thread pool utilization

## Metrics Aggregation

### Using the Global Aggregator

```python
from netra_backend.app.monitoring.metrics_aggregator import (
    get_global_aggregator,
    AggregationWindow
)

# Get the global aggregator instance
aggregator = get_global_aggregator()

# Add metrics from your collector
for metric in collector.metrics:
    aggregator.add_metric(metric)

# Add timing breakdown
breakdown = collector.get_breakdown()
aggregator.add_timing_breakdown(breakdown)

# Get aggregated statistics
minute_stats = aggregator.get_aggregated_metrics(
    MetricType.LLM_PROCESSING,
    AggregationWindow.MINUTE
)

print(f"LLM Processing (last minute):")
print(f"  Average: {minute_stats.mean}ms")
print(f"  P95: {minute_stats.p95}ms")
print(f"  P99: {minute_stats.p99}ms")
```

### Performance Summary

```python
# Get comprehensive performance summary
summary = aggregator.get_performance_summary()

print("Current Performance:")
print(f"  Active Metrics: {len(summary['current_metrics'])}")
print(f"  Trends: {summary['trends']}")
print(f"  Resource Utilization: {summary['resource_utilization']}")

# Identify bottlenecks
bottlenecks = aggregator.get_bottlenecks(threshold_percentile=95)
for bottleneck in bottlenecks:
    print(f"Bottleneck: {bottleneck['metric_type']} "
          f"(threshold: {bottleneck['threshold']}ms)")
```

## Integration with Agents

### Supervisor Integration

```python
from netra_backend.app.agents.supervisor.comprehensive_observability import (
    SupervisorObservability
)
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState

# Create observability instance
observability = SupervisorObservability()

# Create execution context
state = DeepAgentState()
context = ExecutionContext(
    run_id=str(uuid4()),
    agent_name="supervisor",
    state=state,
    user_id="user123"
)

# Start workflow with timing
observability.start_workflow_trace(context)

# Track phases
observability.start_phase(context.run_id, "tool_execution")
# ... execute tools ...
observability.stop_phase(context.run_id, "tool_execution")

# Record TTFT
observability.record_first_token(context.run_id)

# Get timing breakdown
breakdown = observability.get_timing_breakdown(context.run_id)

# Complete workflow
result = ExecutionResult(success=True, data={"result": "data"})
observability.complete_workflow_trace(context, result)
```

### Adding to Custom Agents

```python
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.performance_metrics import EnhancedExecutionTimingCollector

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.timing_collector = None
    
    async def execute(self, context: ExecutionContext):
        # Initialize timing for this execution
        self.timing_collector = EnhancedExecutionTimingCollector(
            execution_id=UUID(context.run_id),
            agent_name=self.name
        )
        
        # Track initialization
        self.timing_collector.start_phase("initialization")
        await self._initialize()
        self.timing_collector.stop_phase("initialization")
        
        # Track main execution
        self.timing_collector.start_phase("processing")
        result = await self._process()
        self.timing_collector.stop_phase("processing")
        
        # Get performance metrics
        breakdown = self.timing_collector.get_breakdown()
        self.logger.info(f"Execution completed in {breakdown.total_ms}ms")
        
        return result
```

## Analyzing Performance

### Performance Analyzer

```python
from netra_backend.app.core.performance_metrics import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()

# Analyze timing breakdown
breakdown = collector.get_breakdown()
analysis = analyzer.analyze_timing_breakdown(breakdown)

print(f"Efficiency Score: {analysis['efficiency_score']}%")
print(f"Bottlenecks: {analysis['bottlenecks']}")
print(f"Recommendations: {analysis['recommendations']}")
```

### Anomaly Detection

```python
# Detect performance anomalies
metrics = aggregator.export_metrics(AggregationWindow.HOUR)
anomalies = analyzer.detect_anomalies(metrics)

for anomaly in anomalies:
    print(f"Anomaly detected: {anomaly['metric_type']}")
    print(f"  Value: {anomaly['value']}ms (mean: {anomaly['mean']}ms)")
    print(f"  Z-score: {anomaly['z_score']}")
```

### SLO Compliance

```python
# Define Service Level Objectives
slo_thresholds = {
    "time_to_first_token": 1000,  # 1 second
    "database_query": 100,         # 100ms
    "total_execution": 5000        # 5 seconds
}

# Calculate compliance
compliance = analyzer.calculate_slo_compliance(
    metrics,
    slo_thresholds
)

for metric_type, compliance_percent in compliance.items():
    print(f"{metric_type}: {compliance_percent:.1f}% compliant")
```

## Best Practices

### 1. Phase Granularity

Choose appropriate granularity for phase tracking:
- **Too Fine**: Overhead from tracking exceeds benefit
- **Too Coarse**: Loses valuable performance insights
- **Just Right**: Track major operations and expensive calls

### 2. Metadata Collection

Include relevant metadata for debugging:

```python
collector.start_phase("database_query", metadata={
    "query_type": "SELECT",
    "table": "agents",
    "index_used": True
})
```

### 3. Error Handling

Always stop phases even on errors:

```python
collector.start_phase("risky_operation")
try:
    result = perform_risky_operation()
except Exception as e:
    collector.stop_phase("risky_operation")
    collector.add_metric(
        MetricType.TOTAL_EXECUTION,
        0,
        metadata={"error": str(e)}
    )
    raise
else:
    collector.stop_phase("risky_operation")
```

### 4. Context Managers

Use context managers for automatic phase management:

```python
with collector.measure("database_operation", MetricType.DATABASE_QUERY):
    result = await db.query("SELECT * FROM agents")
```

### 5. Resource Monitoring

Track resource utilization alongside timing:

```python
import psutil

# Record resource metrics
observability.record_resource_metrics(
    cpu_percent=psutil.cpu_percent(),
    memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
    thread_count=threading.active_count()
)
```

## API Reference

### EnhancedExecutionTimingCollector

```python
class EnhancedExecutionTimingCollector:
    def __init__(self, execution_id: UUID, agent_name: str = "unknown")
    def start_phase(self, phase_name: str, metadata: Optional[Dict] = None) -> PhaseTimer
    def stop_phase(self, phase_name: str) -> Optional[float]
    def record_first_token(self) -> float
    def start_parallel_task(self, task_name: str) -> PhaseTimer
    def stop_parallel_task(self, task_name: str) -> Optional[float]
    def add_metric(self, metric_type: MetricType, value: float, metadata: Optional[Dict] = None)
    def get_breakdown(self) -> TimingBreakdown
    def get_summary(self) -> Dict[str, Any]
```

### MetricsAggregator

```python
class MetricsAggregator:
    def __init__(self, retention_hours: int = 24)
    def add_metric(self, metric: PerformanceMetric)
    def add_timing_breakdown(self, breakdown: TimingBreakdown)
    def get_aggregated_metrics(self, metric_type: MetricType, window: AggregationWindow) -> Optional[AggregatedMetrics]
    def get_performance_summary(self) -> Dict[str, Any]
    def get_bottlenecks(self, threshold_percentile: int = 95) -> List[Dict]
    def export_metrics(self, window: AggregationWindow) -> List[Dict]
```

### PerformanceAnalyzer

```python
class PerformanceAnalyzer:
    def analyze_timing_breakdown(self, breakdown: TimingBreakdown) -> Dict[str, Any]
    def detect_anomalies(self, metrics: List[PerformanceMetric]) -> List[Dict]
    def calculate_slo_compliance(self, metrics: List[PerformanceMetric], slo_thresholds: Dict[str, float]) -> Dict[str, float]
```

## Related Documentation

- [Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md) - Understanding agent components
- [User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md) - Factory-based isolation patterns
- [WebSocket Modernization Report](../WEBSOCKET_MODERNIZATION_REPORT.md) - Real-time notification performance
- [Test Architecture Visual Overview](../tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md) - Testing performance metrics
- [Configuration Architecture](./configuration_architecture.md) - Configuration for performance settings
- [Docker Orchestration](./docker_orchestration.md) - Container performance monitoring

## Performance Optimization Tips

### 1. Identify Bottlenecks

Use the aggregator to find performance bottlenecks:

```python
bottlenecks = aggregator.get_bottlenecks(threshold_percentile=90)
```

### 2. Monitor Trends

Track performance over time:

```python
summary = aggregator.get_performance_summary()
if summary['trends']['llm_processing'] == 'degrading':
    # Take action to improve LLM performance
    pass
```

### 3. Set Alerts

Create alerts for performance degradation:

```python
def check_performance_alerts():
    metrics = aggregator.get_aggregated_metrics(
        MetricType.TOTAL_EXECUTION,
        AggregationWindow.FIVE_MINUTES
    )
    
    if metrics and metrics.p95 > 10000:  # 10 seconds
        send_alert("High P95 latency detected")
```

### 4. Optimize Critical Path

Focus optimization on the critical path:

```python
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector

collector = ExecutionTimingCollector(agent_name="my_agent")
# ... execution ...
critical_path = collector.get_critical_path()
for entry in critical_path:
    print(f"{entry.operation}: {entry.duration_ms}ms")
```

## Troubleshooting

### Common Issues

1. **Missing Phases**: Ensure all started phases are stopped
2. **Memory Leaks**: Clear old metrics periodically with `aggregator.clear_old_metrics()`
3. **Clock Skew**: Use consistent time sources (prefer `time.perf_counter()`)
4. **High Overhead**: Reduce tracking granularity in production

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger("netra_backend.app.core.performance_metrics").setLevel(logging.DEBUG)
logging.getLogger("netra_backend.app.monitoring.metrics_aggregator").setLevel(logging.DEBUG)
```

## Conclusion

The Performance Metrics system provides comprehensive visibility into agent execution performance, enabling data-driven optimization decisions. By following this guide and best practices, you can achieve significant performance improvements in your Netra platform deployments.

For questions or issues, please refer to the [main documentation index](./index.md) or contact the platform team.