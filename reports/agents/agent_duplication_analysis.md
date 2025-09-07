# Agent Code Duplication Analysis Report

## Executive Summary

Analysis of 8 agent implementations reveals significant code duplication that should be consolidated into the BaseSubAgent class. The repetitive patterns span initialization, WebSocket notifications, error handling, state management, LLM interaction patterns, and execution infrastructure.

## Analyzed Agents

1. **DataSubAgent** (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\data_sub_agent\agent.py)
2. **TriageSubAgent** (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\triage_sub_agent.py)
3. **ActionsToMeetGoalsSubAgent** (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\actions_to_meet_goals_sub_agent.py)
4. **OptimizationsCoreSubAgent** (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\optimizations_core_sub_agent.py)
5. **ReportingSubAgent** (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\reporting_sub_agent.py)
6. **SyntheticDataSubAgent** (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\synthetic_data_sub_agent.py)
7. **ValidationSubAgent** (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\validation_sub_agent.py)
8. **CorpusAdminSubAgent** and **SupplyResearcherSubAgent** are modularized imports only

## Top 8 Critical Code Duplication Patterns

### 1. Modern Execution Infrastructure Setup

**Duplication Severity: HIGH**

**Pattern Found In:**
- DataSubAgent (lines 72-82)
- TriageSubAgent (lines 106-128)
- ActionsToMeetGoalsSubAgent (lines 74-95)
- OptimizationsCoreSubAgent (lines 52-75)
- ReportingSubAgent (lines 51-87)

**Duplicated Code Blocks:**

```python
# Similar pattern across all agents
def _initialize_modern_components(self) -> None:
    """Initialize modern execution components."""
    circuit_config = self._create_circuit_breaker_config()
    retry_config = self._create_retry_config()
    self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
    self.error_handler = ExecutionErrorHandler
    self.monitor = ExecutionMonitor()

def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
    """Create circuit breaker configuration."""
    return CircuitBreakerConfig(
        name=f"{self.name}",
        failure_threshold=3,  # Similar values across agents
        recovery_timeout=30   # Similar values across agents
    )

def _create_retry_config(self) -> RetryConfig:
    """Create retry configuration."""
    return RetryConfig(
        max_retries=2,        # Similar values across agents
        base_delay=1.0,       # Similar values across agents
        max_delay=10.0        # Similar values across agents
    )
```

**Recommendation:** Move entire modern execution infrastructure setup to BaseSubAgent.

### 2. LLM Interaction with Observability Pattern

**Duplication Severity: HIGH**

**Pattern Found In:**
- ActionsToMeetGoalsSubAgent (lines 312-349)
- OptimizationsCoreSubAgent (lines 170-187)
- ReportingSubAgent (lines 164-181)

**Duplicated Code Blocks:**

```python
# Near identical pattern in all agents
async def _execute_llm_with_observability(self, prompt: str, correlation_id: str) -> str:
    """Execute LLM call with full observability."""
    start_llm_heartbeat(correlation_id, f"{self.agent_name}")
    try:
        log_agent_input(f"{self.agent_name}", "LLM", len(prompt), correlation_id)
        return await self._make_llm_request(prompt, correlation_id)
    finally:
        stop_llm_heartbeat(correlation_id)

async def _make_llm_request(self, prompt: str, correlation_id: str) -> str:
    """Make LLM request with error handling."""
    try:
        response = await self.llm_manager.ask_llm(prompt, llm_config_name='specific_config')
        log_agent_output("LLM", f"{self.agent_name}", len(response), "success", correlation_id)
        return response
    except Exception as e:
        log_agent_output("LLM", f"{self.agent_name}", 0, "error", correlation_id)
        raise

def _prepare_llm_request(self, prompt: str, run_id: str) -> str:
    """Prepare LLM request with logging and monitoring setup."""
    correlation_id = generate_llm_correlation_id()
    start_llm_heartbeat(correlation_id, f"{self.agent_name}")
    log_agent_input(f"{self.agent_name}", "LLM", len(prompt), correlation_id)
    return correlation_id
```

**Recommendation:** Create base LLM interaction methods in BaseSubAgent.

### 3. WebSocket Notification Patterns

**Duplication Severity: HIGH**

**Pattern Found In:**
- DataSubAgent (lines 121-124, 156-170, 182-195, 228-240, 767-769)
- TriageSubAgent (lines 157-158, 160-161, 167-168, 171-172, 229-230, 233-234, 237-238, 244-245)
- ReportingSubAgent (lines 105, 120, 134-161)
- ValidationSubAgent (lines 116, 124, 149, 192-205)

**Duplicated Code Blocks:**

```python
# WebSocket thinking notifications (almost identical across agents)
await self.emit_thinking("Starting [agent specific] analysis...")
await self.emit_thinking("Analyzing [specific task] and preparing [specific process]...")
await self.emit_thinking("Processing and formatting results...")

# WebSocket tool execution patterns
await self.emit_tool_executing("database_query") # DataSubAgent line 157
await self.emit_tool_executing(f"validation_tool_{rule}") # ValidationSubAgent line 195

# WebSocket completion patterns
await self.emit_progress("[Task] completed successfully", is_complete=True)
await self.emit_tool_completed("tool_name", result)

# Status update patterns with similar structures
async def send_status_update(self, context: ExecutionContext, status: str, message: str) -> None:
    """Send status update via WebSocket."""
    if context.stream_updates:
        await self._process_and_send_status_update(context.run_id, status, message)
```

**Recommendation:** Create standardized WebSocket notification helpers in BaseSubAgent.

### 4. Agent Communication Logging Pattern

**Duplication Severity: MEDIUM**

**Pattern Found In:**
- ActionsToMeetGoalsSubAgent (lines 207-213, 240-245)
- OptimizationsCoreSubAgent (lines 113, 129)
- ReportingSubAgent (lines 102, 128)

**Duplicated Code Blocks:**

```python
# Agent communication start logging (identical pattern)
log_agent_communication("Supervisor", f"{self.agent_name}", run_id, "execute_request")

# Agent communication completion logging (identical pattern)
log_agent_communication(f"{self.agent_name}", "Supervisor", run_id, "execute_response")
```

**Recommendation:** Create base logging wrapper methods in BaseSubAgent.

### 5. Health Status and Monitoring Pattern

**Duplication Severity: MEDIUM**

**Pattern Found In:**
- TriageSubAgent (lines 272-307)
- ActionsToMeetGoalsSubAgent (lines 419-434)
- OptimizationsCoreSubAgent (lines 236-247)
- ReportingSubAgent (lines 271-287)

**Duplicated Code Blocks:**

```python
# Health status pattern (very similar structure)
def get_health_status(self) -> Dict[str, Any]:
    """Get comprehensive agent health status."""
    return {
        "agent_name": self.agent_name,
        "reliability": self.reliability_manager.get_health_status(),
        "monitoring": self.monitor.get_health_status(),
        "error_handler": "available"  # or more complex logic
    }

def get_circuit_breaker_status(self) -> Dict[str, Any]:
    """Get circuit breaker status."""
    return self.reliability_manager.circuit_breaker.get_status()

def get_performance_metrics(self) -> dict:
    """Get performance metrics."""
    return self.monitor.get_agent_metrics(self.name)
```

**Recommendation:** Create base health monitoring methods in BaseSubAgent.

### 6. Execution Context Creation Pattern

**Duplication Severity: MEDIUM**

**Pattern Found In:**
- DataSubAgent (lines 142-151)
- ActionsToMeetGoalsSubAgent (lines 214-222)
- ReportingSubAgent (lines 342-352)

**Duplicated Code Blocks:**

```python
# Execution context creation (near identical)
def _create_execution_context(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> ExecutionContext:
    """Create execution context for modern patterns."""
    return ExecutionContext(
        run_id=run_id,
        agent_name=self.name,  # or self.agent_name
        state=state,
        stream_updates=stream_updates,
        # Various metadata fields with similar patterns
    )
```

**Recommendation:** Create base execution context factory in BaseSubAgent.

### 7. Fallback Result Creation Pattern

**Duplication Severity: MEDIUM**

**Pattern Found In:**
- OptimizationsCoreSubAgent (lines 212-234)
- ReportingSubAgent (lines 237-269)

**Duplicated Code Blocks:**

```python
# Fallback result creation (similar structure)
def _create_default_fallback_result(self) -> Dict[str, Any]:
    """Create default fallback result."""
    return {
        "status": "fallback_used",
        "recommendations": self._get_default_recommendations(),
        "confidence_score": 0.5,  # Similar fallback values
        "metadata": self._get_fallback_metadata()
    }

def _get_fallback_metadata(self) -> Dict[str, Any]:
    """Get fallback metadata dictionary."""
    return {
        "fallback_used": True,
        "reason": "Primary [operation] failed"
    }
```

**Recommendation:** Create base fallback result patterns in BaseSubAgent.

### 8. Error Handling and Result Creation Pattern

**Duplication Severity: MEDIUM**

**Pattern Found In:**
- ValidationSubAgent (lines 259-271)
- ActionsToMeetGoalsSubAgent (lines 247-255)

**Duplicated Code Blocks:**

```python
# Error result creation (similar patterns)
def _create_error_result(self, error_message: str, start_time: float) -> TypedAgentResult:
    """Create standardized error result."""
    execution_time = (time.time() - start_time) * 1000
    
    return TypedAgentResult(
        success=False,
        result={
            "error": error_message,
            "execution_time_ms": execution_time,
            "status": "failed"  # Similar error structures
        },
        execution_time_ms=execution_time
    )
```

**Recommendation:** Create standardized error result factory in BaseSubAgent.

## Detailed Duplication Analysis by Agent

### DataSubAgent
- **Lines 72-82:** Modern execution engine setup
- **Lines 121-124:** WebSocket thinking notifications
- **Lines 156-170:** Tool execution notifications with error handling
- **Lines 182-240:** Analysis method with WebSocket progress updates
- **Lines 767-769:** Thinking notification helper

### TriageSubAgent  
- **Lines 106-128:** Modern reliability manager creation
- **Lines 157-172:** WebSocket event emissions during execution
- **Lines 272-307:** Health status monitoring methods
- **Lines 310-331:** WebSocket bridge update methods

### ActionsToMeetGoalsSubAgent
- **Lines 74-95:** Modern execution infrastructure setup
- **Lines 207-245:** Agent communication logging wrapper
- **Lines 312-349:** LLM interaction with full observability
- **Lines 419-434:** Health monitoring methods

### OptimizationsCoreSubAgent
- **Lines 52-75:** Modern component initialization
- **Lines 113-129:** Agent communication logging
- **Lines 170-187:** LLM execution with observability
- **Lines 212-234:** Fallback result creation

### ReportingSubAgent
- **Lines 51-87:** Modern execution components setup
- **Lines 102-128:** Agent communication and WebSocket notifications
- **Lines 164-181:** LLM request handling with observability
- **Lines 237-269:** Fallback operation patterns

### ValidationSubAgent
- **Lines 116-149:** WebSocket event emission during execution
- **Lines 192-205:** Tool execution with progress notifications
- **Lines 259-271:** Error result creation

## Recommendations for BaseSubAgent Enhancement

### 1. Modern Execution Infrastructure (High Priority)
Move the entire modern execution setup to BaseSubAgent:
```python
def _setup_modern_execution_infrastructure(
    self, 
    circuit_failure_threshold: int = 3,
    circuit_recovery_timeout: int = 30,
    retry_max_retries: int = 2,
    retry_base_delay: float = 1.0,
    retry_max_delay: float = 10.0
) -> None:
    """Setup modern execution infrastructure with configurable parameters."""
    # Consolidated initialization logic
```

### 2. LLM Interaction Base Methods (High Priority)
Add standardized LLM interaction methods:
```python
async def execute_llm_with_observability(
    self, 
    prompt: str, 
    llm_config_name: str,
    correlation_id: Optional[str] = None
) -> str:
    """Execute LLM call with full observability tracking."""
    # Consolidated LLM interaction pattern
```

### 3. WebSocket Notification Helpers (High Priority)
Create specialized WebSocket helper methods:
```python
async def emit_analysis_progress(self, stage: str, details: str) -> None:
    """Emit standardized analysis progress with stage information."""
    
async def emit_processing_started(self, process_name: str) -> None:
    """Emit standardized processing start notification."""
```

### 4. Health and Monitoring Base Methods (Medium Priority)
Add standardized health monitoring:
```python
def get_comprehensive_health_status(self) -> Dict[str, Any]:
    """Get standardized health status across all components."""
    
def get_execution_metrics(self) -> Dict[str, Any]:
    """Get standardized execution metrics."""
```

### 5. Communication Logging Wrapper (Medium Priority)
Add base communication logging:
```python
async def execute_with_communication_logging(
    self, 
    state: DeepAgentState, 
    run_id: str, 
    stream_updates: bool,
    main_executor: Callable
) -> None:
    """Execute with standardized communication logging."""
```

### 6. Base Error and Fallback Patterns (Medium Priority)
Create standardized error handling:
```python
def create_standardized_error_result(
    self, 
    error_message: str, 
    start_time: float,
    error_type: str = "execution_error"
) -> TypedAgentResult:
    """Create standardized error result."""
```

## Impact Assessment

### Code Reduction Potential
- **Estimated lines saved:** 800-1000 lines across all agents
- **Duplication reduction:** ~40-50% reduction in repetitive patterns
- **Maintenance improvement:** Single source of truth for common patterns

### Risk Assessment
- **Low Risk:** WebSocket notification helpers, communication logging
- **Medium Risk:** Health monitoring consolidation, error handling patterns  
- **High Risk:** Modern execution infrastructure changes (requires careful testing)

## Implementation Priority

1. **Phase 1 (High Priority):** Modern execution infrastructure, LLM interaction patterns
2. **Phase 2 (Medium Priority):** WebSocket notification helpers, health monitoring
3. **Phase 3 (Low Priority):** Communication logging, error handling standardization

## Conclusion

The analysis reveals substantial code duplication across agent implementations, with modern execution infrastructure setup and LLM interaction patterns being the most critical areas for consolidation. Moving these patterns to BaseSubAgent will significantly reduce code duplication, improve maintainability, and ensure consistent behavior across all agents.