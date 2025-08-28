# Timing Integration Examples

## Quick Start

### 1. Basic Agent Timing

```python
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector, TimingCategory
from netra_backend.app.agents.base.timing_decorators import time_operation, timed_agent

@timed_agent  # Automatically times all methods
class OptimizedTriageAgent(BaseSubAgent):
    
    @time_operation(category=TimingCategory.LLM)
    async def process_with_llm(self, prompt: str):
        """This method is automatically timed."""
        response = await self.llm_client.complete(prompt)
        return response
    
    @time_operation("data_validation", TimingCategory.VALIDATION)
    async def validate_input(self, data: dict):
        """Custom operation name and category."""
        # Validation logic
        pass
    
    async def execute(self, state: DeepAgentState):
        """Main execution - timing tracked hierarchically."""
        # Start execution timing
        self.timing_collector.start_execution(state.correlation_id)
        
        try:
            # These will be tracked as nested operations
            validated = await self.validate_input(state.data)
            result = await self.process_with_llm(validated)
            
            return result
        finally:
            # Complete execution and get timing tree
            timing_tree = self.timing_collector.complete_execution()
            
            # Log performance summary
            logger.info(f"Execution completed in {timing_tree.get_total_duration_ms():.2f}ms")
```

### 2. Manual Timing for Complex Operations

```python
from netra_backend.app.agents.base.timing_decorators import TimingContext

class DataAnalysisAgent(BaseSubAgent):
    
    async def analyze_dataset(self, dataset_id: str):
        """Complex multi-step analysis with manual timing."""
        
        # Time data fetching
        async with TimingContext(
            self.timing_collector,
            "fetch_dataset",
            TimingCategory.DATABASE
        ) as timer:
            data = await self.db.fetch_dataset(dataset_id)
            timer.metadata["row_count"] = len(data)
        
        # Time processing with nested operations
        with self.timing_collector.time_operation(
            "process_dataset",
            TimingCategory.PROCESSING
        ):
            # Nested timing for sub-operations
            with self.timing_collector.time_operation("normalize_data"):
                normalized = self.normalize(data)
            
            with self.timing_collector.time_operation("calculate_metrics"):
                metrics = self.calculate_metrics(normalized)
        
        return metrics
```

### 3. Supervisor Pipeline Timing

```python
from netra_backend.app.agents.base.timing_decorators import time_step

class ModernSupervisorAgent:
    
    def __init__(self):
        self.timing_collector = ExecutionTimingCollector("supervisor")
        self.timing_aggregator = TimingAggregator()
    
    @time_step("agent_selection")
    async def select_agent(self, query: str) -> str:
        """Select appropriate agent for query."""
        # Selection logic
        return agent_name
    
    @time_step("agent_execution")  
    async def execute_agent(self, agent_name: str, state: DeepAgentState):
        """Execute selected agent."""
        agent = self.registry.get_agent(agent_name)
        return await agent.execute(state)
    
    async def process_request(self, request: dict):
        """Process request with full timing."""
        # Start execution timing
        tree = self.timing_collector.start_execution(request["correlation_id"])
        
        try:
            # Pipeline steps are automatically timed
            agent_name = await self.select_agent(request["query"])
            result = await self.execute_agent(agent_name, request["state"])
            
            return result
        finally:
            # Complete and analyze timing
            timing_tree = self.timing_collector.complete_execution()
            self.timing_aggregator.add_timing_tree(timing_tree)
            
            # Generate report periodically
            if len(self.timing_aggregator.timing_trees) >= 100:
                report = self.timing_aggregator.generate_optimization_report()
                await self.send_performance_report(report)
```

## Rollup Reporting

### Generate Performance Reports

```python
from netra_backend.app.agents.base.timing_aggregator import TimingAggregator

async def generate_daily_performance_report():
    """Generate daily performance optimization report."""
    
    aggregator = TimingAggregator()
    
    # Collect timing trees from all agents
    for agent in agent_registry.get_all_agents():
        if hasattr(agent, 'timing_collector'):
            for tree in agent.timing_collector.completed_trees:
                aggregator.add_timing_tree(tree)
    
    # Generate comprehensive report
    report = aggregator.generate_optimization_report()
    
    # Log key metrics
    logger.info(f"Performance Report Generated:")
    logger.info(f"  Total Executions: {report.total_executions}")
    logger.info(f"  Average Duration: {report.avg_duration_ms:.2f}ms")
    logger.info(f"  Optimization Potential: {report.optimization_potential_ms:.2f}ms")
    
    # Log top bottlenecks
    logger.info("Top Bottlenecks:")
    for bottleneck in report.bottlenecks[:5]:
        logger.info(f"  - {bottleneck.operation}: {bottleneck.avg_duration_ms:.2f}ms")
        logger.info(f"    Impact: {bottleneck.impact_percentage:.1f}%")
        logger.info(f"    Recommendation: {bottleneck.recommendation}")
    
    # Export full report
    json_report = aggregator.export_report_json(report)
    await save_report_to_storage(json_report)
    
    # Send to monitoring dashboard
    await send_to_grafana(report)
```

### Real-time Monitoring Integration

```python
from netra_backend.app.agents.base.timing_collector import ExecutionTimingTree

async def send_timing_metrics_to_websocket(
    tree: ExecutionTimingTree,
    websocket_manager: WebSocketManager
):
    """Send real-time timing metrics via WebSocket."""
    
    metrics = {
        "type": "execution_timing",
        "agent": tree.agent_name,
        "correlation_id": tree.correlation_id,
        "total_duration_ms": tree.get_total_duration_ms(),
        "critical_path": [
            {
                "operation": entry.operation,
                "duration_ms": entry.duration_ms,
                "category": entry.category.value
            }
            for entry in tree.get_critical_path()
        ],
        "category_breakdown": {}
    }
    
    # Calculate category breakdown
    for entry in tree.entries.values():
        if entry.is_complete:
            category = entry.category.value
            if category not in metrics["category_breakdown"]:
                metrics["category_breakdown"][category] = 0
            metrics["category_breakdown"][category] += entry.duration_ms or 0
    
    # Send to connected clients
    await websocket_manager.broadcast_metric(metrics)
```

## Configuration

### Enable Timing in Environment

```python
# settings.py
TIMING_CONFIG = {
    "enabled": os.getenv("ENABLE_TIMING", "true").lower() == "true",
    "sampling_rate": float(os.getenv("TIMING_SAMPLING_RATE", "1.0")),
    "slow_operation_threshold_ms": int(os.getenv("SLOW_OP_THRESHOLD_MS", "1000")),
    "report_interval_minutes": int(os.getenv("TIMING_REPORT_INTERVAL", "60")),
    "persist_to_database": os.getenv("PERSIST_TIMING", "true").lower() == "true"
}
```

### Conditional Timing Based on Environment

```python
from netra_backend.app.config import TIMING_CONFIG

class ConditionallyTimedAgent(BaseSubAgent):
    
    def __init__(self):
        super().__init__()
        # Only create collector if timing is enabled
        if TIMING_CONFIG["enabled"]:
            self.timing_collector = ExecutionTimingCollector(self.name)
        else:
            self.timing_collector = None
    
    async def execute(self, state):
        if self.timing_collector:
            self.timing_collector.start_execution(state.correlation_id)
        
        try:
            # Execute logic
            result = await self._process(state)
            return result
        finally:
            if self.timing_collector:
                self.timing_collector.complete_execution()
```

## Best Practices

### 1. Hierarchical Timing
- Use nested timing contexts for complex operations
- Keep parent-child relationships clear
- Don't create too many levels (3-4 max)

### 2. Category Selection
- Use appropriate categories for accurate aggregation
- Auto-detection works well for standard patterns
- Override when the operation doesn't match naming convention

### 3. Metadata Collection
- Include relevant context (user_id, request_type, etc.)
- Avoid sensitive data in metadata
- Keep metadata lightweight

### 4. Performance Impact
- Timing adds ~0.1-0.5ms overhead per operation
- Use sampling in production if needed
- Disable for performance-critical paths

### 5. Report Generation
- Generate reports during low-traffic periods
- Archive historical reports for trend analysis
- Set up alerts for performance degradation

## Testing

```python
import pytest
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector

@pytest.mark.asyncio
async def test_agent_timing():
    """Test timing integration."""
    
    agent = OptimizedTriageAgent()
    
    # Execute with timing
    result = await agent.execute(test_state)
    
    # Verify timing was collected
    assert len(agent.timing_collector.completed_trees) == 1
    
    tree = agent.timing_collector.completed_trees[0]
    assert tree.get_total_duration_ms() > 0
    
    # Check for expected operations
    operations = [e.operation for e in tree.entries.values()]
    assert "process_with_llm" in operations
    assert "validate_input" in operations
    
    # Verify hierarchical structure
    assert tree.root_id in tree.entries
    assert len(tree.children[tree.root_id]) > 0
```