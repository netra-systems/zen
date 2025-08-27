# Agent Execution Timing Architecture

## Current State Analysis

### Existing Time Tracking Mechanisms
1. **ExecutionContext** (`base/execution_context.py`)
   - Tracks `start_time` and `end_time` 
   - Provides `duration` property
   - Limited to single execution scope

2. **ExecutionMonitor** (`base/monitoring.py`)
   - Collects execution metrics (time, tokens, queries)
   - Maintains performance stats per agent
   - Calculates averages and p95 percentiles
   - Missing: Step-level granularity

3. **SupervisorPipelineLogger** (`supervisor/flow_logger.py`)
   - Logs flow start/completion times
   - Tracks agent execution durations
   - TODOs with timestamps
   - Missing: Aggregated rollup reporting

4. **ExecutionEngine** (`supervisor/execution_engine.py`)
   - Basic timing with `time.time()`
   - No structured step timing

### Identified Gaps
1. **No unified timing collection** - Each component tracks time independently
2. **No step-level granularity** - Can't identify slow operations within agents
3. **No rollup reporting** - Can't see aggregate time by operation type
4. **No persistence** - Timing data not stored for historical analysis
5. **No visualization** - No dashboards or reports for optimization insights

## Proposed Architecture

### Core Components

#### 1. ExecutionTimingCollector
Central service for collecting all timing data with hierarchical structure:

```python
@dataclass
class TimingEntry:
    """Single timing measurement."""
    operation: str          # e.g., "triage_agent.llm_call"
    category: str           # e.g., "llm", "database", "processing"
    start_time: float
    end_time: Optional[float]
    duration_ms: Optional[float]
    metadata: Dict[str, Any]   # agent_name, step_name, etc.
    parent_id: Optional[str]   # For hierarchical tracking
    
@dataclass
class ExecutionTimingTree:
    """Hierarchical execution timing structure."""
    root_id: str               # Top-level execution ID
    entries: Dict[str, TimingEntry]
    children: Dict[str, List[str]]  # parent_id -> child_ids
```

#### 2. StepTimingDecorator
Automatic timing collection for agent methods:

```python
@timing_step("llm_call", category="llm")
async def process_with_llm(self, prompt: str):
    # Automatically timed and reported
    pass
```

#### 3. TimingAggregator
Rollup reporting and analysis:

```python
class TimingAggregator:
    def aggregate_by_category(entries: List[TimingEntry]) -> Dict[str, AggregateStats]
    def aggregate_by_agent(entries: List[TimingEntry]) -> Dict[str, AggregateStats]
    def identify_bottlenecks(tree: ExecutionTimingTree) -> List[Bottleneck]
    def generate_optimization_report() -> OptimizationReport
```

#### 4. TimingPersistence
Store timing data for historical analysis:

```python
class TimingPersistence:
    async def store_execution_timing(tree: ExecutionTimingTree)
    async def query_historical_timings(filters: TimingFilters) -> List[ExecutionTimingTree]
    async def get_trend_analysis(operation: str, days: int) -> TrendData
```

### Integration Points

#### Agent Base Classes
```python
class BaseSubAgent:
    def __init__(self):
        self.timing_collector = ExecutionTimingCollector()
    
    @contextmanager
    def time_step(self, step_name: str, category: str):
        """Context manager for timing steps."""
        entry = self.timing_collector.start_timing(step_name, category)
        try:
            yield
        finally:
            self.timing_collector.end_timing(entry)
```

#### Supervisor Integration
```python
class SupervisorAgent:
    async def execute_pipeline(self):
        with self.timing_collector.time_execution("pipeline"):
            for step in steps:
                with self.timing_collector.time_step(f"step_{step.name}"):
                    await self.execute_step(step)
```

### Reporting Structure

#### Real-time Metrics
- WebSocket events for live timing updates
- Current execution tree visualization
- Running bottleneck detection

#### Rollup Reports
1. **Execution Summary**
   - Total time by category (LLM, DB, Processing)
   - Time distribution across agents
   - Critical path analysis

2. **Optimization Opportunities**
   - Top 10 slowest operations
   - Operations exceeding SLA thresholds
   - Redundant operation detection

3. **Historical Trends**
   - Performance degradation alerts
   - Capacity planning metrics
   - Success rate vs execution time correlation

### Implementation Phases

#### Phase 1: Core Infrastructure (Week 1)
- [ ] Create ExecutionTimingCollector
- [ ] Implement TimingEntry and ExecutionTimingTree
- [ ] Add basic timing decorators
- [ ] Integrate with ExecutionContext

#### Phase 2: Agent Integration (Week 2)
- [ ] Update BaseSubAgent with timing support
- [ ] Add step-level timing to critical agents
- [ ] Implement timing context managers
- [ ] Create timing middleware

#### Phase 3: Aggregation & Reporting (Week 3)
- [ ] Build TimingAggregator
- [ ] Create rollup report generators
- [ ] Implement bottleneck detection
- [ ] Add WebSocket timing events

#### Phase 4: Persistence & Analytics (Week 4)
- [ ] Implement TimingPersistence with PostgreSQL
- [ ] Create historical trend analysis
- [ ] Build optimization recommendation engine
- [ ] Deploy monitoring dashboards

### Optimization Targets

Based on initial analysis, focus timing on:
1. **LLM Calls** - Typically 60-80% of execution time
2. **Database Queries** - Can spike with complex aggregations
3. **Inter-agent Communication** - Network overhead
4. **JSON Parsing/Validation** - CPU-intensive operations
5. **Cache Misses** - Redundant computations

### Success Metrics
- **Visibility**: 100% of agent operations have timing data
- **Granularity**: Can identify operations taking >100ms
- **Actionability**: Weekly report identifies top 5 optimization opportunities
- **Impact**: 20% reduction in p95 execution time after optimizations

### Configuration
```yaml
timing:
  enabled: true
  sampling_rate: 1.0  # Sample all executions initially
  persistence:
    enabled: true
    retention_days: 30
  thresholds:
    slow_operation_ms: 1000
    critical_operation_ms: 5000
  reporting:
    realtime: true
    rollup_interval_minutes: 5
```