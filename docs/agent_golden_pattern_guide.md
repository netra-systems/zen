# Agent Golden Pattern Guide

## Business Value Justification (BVJ)
- **Segment**: Platform/Internal
- **Business Goal**: Development Velocity & Platform Stability
- **Value Impact**: +25% reduction in agent development time, 90% reduction in SSOT violations
- **Strategic Impact**: Enables consistent agent architecture across platform, reduces technical debt

## Executive Summary

The TriageSubAgent establishes the **golden pattern** for all Netra agents using the enhanced BaseAgent infrastructure. This pattern eliminates SSOT violations, provides standardized infrastructure, and enables clean separation of business logic from infrastructure concerns.

## Core Principles

### 1. Single Source of Truth (SSOT) Enforcement
- **BaseAgent contains ALL infrastructure**: WebSocket events, reliability management, execution patterns, health monitoring
- **Agents contain ONLY business logic**: Domain-specific processing, validation, and operations
- **No infrastructure duplication**: Never implement WebSocket handlers, retry logic, or execution engines in sub-agents

### 2. Clean Inheritance Pattern
```python
from netra_backend.app.agents.base_agent import BaseSubAgent

class YourAgent(BaseSubAgent):
    def __init__(self):
        super().__init__(
            name="YourAgent",
            description="Clear business purpose",
            enable_reliability=True,      # Gets circuit breaker + retry
            enable_execution_engine=True, # Gets modern execution patterns
            enable_caching=True,          # Optional caching infrastructure
        )
        # Initialize ONLY business logic components
```

### 3. Infrastructure Access via SSOT Properties
```python
# Access infrastructure through BaseAgent properties
self.reliability_manager  # Modern reliability patterns
self.execution_engine     # Modern execution engine
self.execution_monitor    # Health and performance monitoring
self.timing_collector     # Execution timing analytics
```

## TriageSubAgent Golden Pattern Analysis

### File Structure (178 lines total)
```
netra_backend/app/agents/triage_sub_agent.py
├── Imports (30 lines)
├── Business Logic Only (148 lines)
│   ├── Initialization with BaseAgent (10 lines)
│   ├── Validation Methods (25 lines)
│   ├── Core Business Logic (40 lines)
│   ├── Legacy Compatibility (20 lines)
│   └── Helper Methods (53 lines)
└── Zero Infrastructure Code (0 lines)
```

### What Belongs in Sub-Agents vs BaseAgent

#### ✅ In Sub-Agents (Business Logic Only)
```python
# Domain-specific validation
async def validate_preconditions(self, context: ExecutionContext) -> bool:
    if not context.state.user_request:
        return False
    validation = self.triage_core.validator.validate_request(context.state.user_request)
    return validation.is_valid

# Core business operations
async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
    await self.emit_thinking("Starting triage analysis...")
    triage_result = await self._get_or_compute_triage_result(context.state, context.run_id, time.time())
    return self._finalize_triage_result(context.state, context.run_id, context.stream_updates, triage_result)

# Domain-specific helper methods
def _validate_request(self, request: str):
    return self.triage_core.validator.validate_request(request)
```

#### ❌ In BaseAgent (Infrastructure Only)
```python
# WebSocket event emission (lines 272-314)
async def emit_thinking(self, thought: str, step_number: Optional[int] = None)
async def emit_tool_executing(self, tool_name: str, parameters: Optional[Dict] = None)
async def emit_agent_completed(self, result: Optional[Dict] = None)

# Reliability management (lines 322-401)
def _init_reliability_infrastructure(self)
async def execute_with_reliability(self, operation, operation_name, fallback=None)

# Execution patterns (lines 403-442)
async def execute_modern(self, state, run_id, stream_updates)
async def send_status_update(self, context, status, message)

# Health monitoring (lines 455-495)
def get_health_status(self) -> Dict[str, Any]
def get_circuit_breaker_status(self) -> Dict[str, Any]
```

## Implementation Checklist

### Phase 1: Clean Inheritance Setup
```python
class YourAgent(BaseSubAgent):
    def __init__(self):
        super().__init__(
            name="YourAgent",
            description="Business purpose description",
            enable_reliability=True,
            enable_execution_engine=True,
            enable_caching=False,  # Only if needed
        )
        # Initialize ONLY business logic components
        self.your_core = YourCore()
        self.your_processor = YourProcessor()
```

### Phase 2: Implement Required Abstract Methods
```python
async def validate_preconditions(self, context: ExecutionContext) -> bool:
    """Validate execution preconditions - domain specific"""
    # Your validation logic here
    return True

async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
    """Execute core business logic with WebSocket events"""
    await self.emit_thinking("Starting analysis...")
    
    # Your business logic here
    result = await self.your_processor.process(context.state)
    
    await self.emit_progress("Analysis completed", is_complete=True)
    return result
```

### Phase 3: Use Inherited Infrastructure
```python
# Use reliability patterns
async def _execute_with_retry(self, operation, operation_name):
    return await self.execute_with_reliability(
        operation, operation_name,
        fallback=self._fallback_operation
    )

# Use modern execution (automatic via execute() method)
# Use WebSocket events (available via emit_* methods)
# Use health monitoring (available via get_health_status())
```

## WebSocket Events Pattern

### Required Events for Chat Value
```python
async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
    # 1. agent_started - handled by orchestrator
    
    # 2. agent_thinking - show reasoning
    await self.emit_thinking("Analyzing user request and determining category...")
    
    # 3. tool_executing/tool_completed - show tool usage
    await self.emit_tool_executing("data_extractor", {"method": "nlp"})
    result = await self.extract_data()
    await self.emit_tool_completed("data_extractor", {"entities": len(result)})
    
    # 4. agent_completed - handled by orchestrator
    
    # 5. Progress updates throughout
    await self.emit_progress("Finalizing analysis...", is_complete=False)
    await self.emit_progress("Analysis completed successfully", is_complete=True)
    
    return result
```

### WebSocket Event Guidelines
- **Use emit_thinking()** for reasoning visibility
- **Use emit_progress()** for partial results and status
- **Use emit_tool_executing/completed()** for transparency
- **Never implement custom WebSocket handlers** - use inherited methods

## Anti-Patterns to Avoid

### ❌ Infrastructure Duplication
```python
# DON'T: Duplicate WebSocket handling
class BadAgent(BaseSubAgent):
    async def send_websocket_update(self, message):
        # This duplicates BaseAgent functionality
        pass
    
    async def retry_operation(self, op):
        # This duplicates BaseAgent reliability
        pass
```

### ❌ Multiple Inheritance Complexity
```python
# DON'T: Mix multiple inheritance patterns
class BadAgent(BaseSubAgent, SomeMixin, AnotherMixin):
    # Leads to MRO conflicts and SSOT violations
    pass
```

### ❌ Direct Infrastructure Access
```python
# DON'T: Bypass BaseAgent infrastructure
from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge

class BadAgent(BaseSubAgent):
    async def execute_core_logic(self, context):
        bridge = await get_agent_websocket_bridge()  # Wrong!
        # Use self.emit_thinking() instead
```

## Code Examples

### TriageSubAgent Key Patterns

#### 1. Clean Initialization (Lines 41-51)
```python
def __init__(self):
    super().__init__(
        name="TriageSubAgent", 
        description="Enhanced triage agent using BaseAgent infrastructure",
        enable_reliability=True,      # Get circuit breaker + retry
        enable_execution_engine=True, # Get modern execution patterns
        enable_caching=True,
    )   
    self.triage_core = TriageCore(self.redis_manager)  # Business logic only
    self.processor = TriageProcessor(self.triage_core, self.llm_manager)
```

#### 2. Validation Pattern (Lines 54-63)
```python
async def validate_preconditions(self, context: ExecutionContext) -> bool:
    """Validate execution preconditions for triage."""
    if not context.state.user_request:
        self.logger.warning(f"No user request provided for triage in run_id: {context.run_id}")
        return False
    validation = self.triage_core.validator.validate_request(context.state.user_request)
    if not validation.is_valid:
        self._set_validation_error_result(context.state, context.run_id, validation)
        return False
    return True
```

#### 3. Business Logic with Events (Lines 70-92)
```python
async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
    """Execute core triage logic with modern patterns and WebSocket events."""
    start_time = time.time()
    
    # WebSocket events for user visibility
    await self.emit_thinking("Starting triage analysis for user request")
    await self.emit_thinking("Analyzing user request and determining category...")
    
    await self._send_processing_update(context.run_id, context.stream_updates)
    
    # Business logic with progress updates
    await self.emit_progress("Extracting entities and determining intent...")
    triage_result = await self._get_or_compute_triage_result(context.state, context.run_id, start_time)
    
    await self.emit_progress("Finalizing triage results and recommendations...")
    result = await self._finalize_triage_result(context.state, context.run_id, context.stream_updates, triage_result)
    
    # Completion event
    await self.emit_progress("Triage analysis completed successfully", is_complete=True)
    
    return result
```

#### 4. Legacy Compatibility (Lines 121-128)
```python
async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
    """Execute the enhanced triage logic - uses BaseAgent's reliability infrastructure"""
    await self.execute_with_reliability(
        lambda: self._execute_triage_main(state, run_id, stream_updates),
        "execute_triage",
        fallback=lambda: self._execute_triage_fallback(state, run_id, stream_updates)
    )
```

## Testing Requirements

### Unit Tests
- Test business logic methods only
- Mock BaseAgent infrastructure if needed
- Focus on domain-specific validation and processing

### Integration Tests
- Test with real BaseAgent infrastructure
- Verify WebSocket event emission
- Test reliability patterns under failure conditions

### E2E Tests
- Test complete agent execution flow
- Verify chat experience with real WebSocket connections
- Test fallback scenarios and error handling

## Migration Guide Quick Reference

1. **Remove Infrastructure**: Delete WebSocket handlers, retry logic, execution engines
2. **Inherit BaseAgent**: Change to `class Agent(BaseSubAgent)`
3. **Initialize Infrastructure**: Call `super().__init__()` with required flags
4. **Implement Abstracts**: Add `validate_preconditions()` and `execute_core_logic()`
5. **Add WebSocket Events**: Use `emit_thinking()`, `emit_progress()`, etc.
6. **Update Tests**: Test business logic, rely on BaseAgent for infrastructure

## Success Metrics

- **Code Reduction**: 60-80% reduction in agent code size
- **SSOT Compliance**: Zero infrastructure duplication
- **Development Speed**: 25% faster agent development
- **Chat Experience**: Real-time WebSocket events for all agents
- **Reliability**: Consistent error handling and circuit breaker patterns

## Related Documentation

- [Agent Migration Checklist](agent_migration_checklist.md)
- [Architecture Decision Record](adr/agent_ssot_consolidation.md)
- [BaseAgent API Reference](../SPEC/base_agent_api.xml)
- [WebSocket Integration Guide](../SPEC/learnings/websocket_agent_integration_critical.xml)

---

*This golden pattern ensures all future agents follow SSOT principles while maximizing business value delivery through consistent, reliable infrastructure.*