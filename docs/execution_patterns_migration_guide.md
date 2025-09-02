# Execution Patterns Migration Guide

## Overview

This guide explains how to migrate agents from custom execution patterns to the standardized BaseExecutionEngine with strategy pattern support. The BaseExecutionEngine serves as the single source of truth (SSOT) for all agent execution workflows.

## Business Value

- **Eliminates 40+ duplicate execution patterns** across agents
- **Standardizes WebSocket event emission** for consistent chat experience
- **Provides strategy pattern support** for different execution needs
- **Enables extension hooks** for agent-specific logic
- **Improves maintainability** through consistent patterns

## Strategy Pattern Support

### Available Strategies

1. **SEQUENTIAL**: Execute phases one after another
2. **PIPELINE**: Execute phases with dependency resolution and data flow
3. **PARALLEL**: Execute phases concurrently where dependencies allow

### Strategy Selection Guide

| Use Case | Strategy | Example |
|----------|----------|---------|
| Simple linear workflow | SEQUENTIAL | Basic data processing |
| Complex multi-phase with dependencies | PIPELINE | GitHub analysis (scan → config → map) |
| Independent operations | PARALLEL | Multiple API calls |

## Migration Steps

### Step 1: Add Imports

```python
from netra_backend.app.agents.base.executor import (
    BaseExecutionEngine, ExecutionStrategy, ExecutionWorkflowBuilder,
    LambdaExecutionPhase, AgentMethodExecutionPhase
)
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
```

### Step 2: Initialize Execution Engine

Add to your agent's `__init__` or initialization method:

```python
def _init_execution_engine(self) -> None:
    """Initialize BaseExecutionEngine with phases."""
    # Create execution phases
    phase_1 = AgentMethodExecutionPhase("phase_name", self, "method_name")
    phase_2 = AgentMethodExecutionPhase("phase_name_2", self, "method_name_2", ["phase_name"])
    
    # Build execution engine
    self.execution_engine = ExecutionWorkflowBuilder() \
        .add_phases([phase_1, phase_2]) \
        .set_strategy(ExecutionStrategy.PIPELINE) \
        .add_pre_execution_hook(self._pre_execution_hook) \
        .add_post_execution_hook(self._post_execution_hook) \
        .build()
```

### Step 3: Create Phase Methods

Replace your existing workflow methods with phase wrapper methods:

```python
async def _execute_phase_1_method(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 1: Description - method wrapper."""
    # Access context data
    run_id = context.run_id
    state = context.state
    
    # Access previous phase results
    if previous_results:
        previous_data = previous_results.get("previous_phase_name", {})
    
    # Execute phase logic
    result = await self._do_phase_work(context, previous_data)
    
    # Return phase results
    return {"phase_result": result}
```

### Step 4: Update Main Execute Method

Replace your main execute method:

```python
async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
    """Execute using BaseExecutionEngine."""
    try:
        # Create execution context
        execution_context = ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            thread_id=getattr(state, 'chat_thread_id', None),
            user_id=getattr(state, 'user_id', None),
            correlation_id=run_id
        )
        
        # Execute using BaseExecutionEngine
        result = await self.execution_engine.execute_phases(execution_context)
        
        if not result.success:
            raise Exception(result.error)
            
    except Exception as e:
        # Handle errors
        await self._handle_execution_error(e, state, run_id, stream_updates)
        raise
```

### Step 5: Add Hook Methods

Create pre and post execution hooks:

```python
async def _pre_execution_hook(self, context: ExecutionContext) -> None:
    """Pre-execution hook for setup."""
    logger.info(f"Starting {self.name} for run_id: {context.run_id}")
    # Add any setup logic here

async def _post_execution_hook(self, context: ExecutionContext, phase_results: Dict[str, Any]) -> None:
    """Post-execution hook for cleanup."""
    logger.info(f"{self.name} completed for run_id: {context.run_id}")
    # Extract results and update state
    if "final_phase" in phase_results:
        context.state.agent_result = phase_results["final_phase"]
```

## Phase Types

### AgentMethodExecutionPhase

For calling existing agent methods:

```python
phase = AgentMethodExecutionPhase("phase_name", self, "method_name", dependencies=["dep1"])
```

### LambdaExecutionPhase

For inline functions:

```python
async def custom_logic(context, previous_results):
    return {"result": "value"}

phase = LambdaExecutionPhase("phase_name", custom_logic, dependencies=["dep1"])
```

## WebSocket Integration

The BaseExecutionEngine automatically handles WebSocket events for each phase:

- **Phase Start**: `tool_executing` event with phase name
- **Phase Complete**: `tool_completed` event with phase results
- **Phase Error**: `agent_error` event with error details

### Ensuring WebSocket Events

Make sure your ExecutionContext has a websocket_manager:

```python
# The execution context should have websocket access through the agent
# WebSocket events are automatically sent for each phase execution
```

## Migration Examples

### Example 1: GitHubAnalyzerService (Pipeline Strategy)

**Before**:
```python
async def execute(self, state, context):
    repo_path = await self._execute_phase_1(repo_url, state)
    ai_patterns = await self._execute_phase_2(repo_path, state)
    configs = await self._execute_phase_3(repo_path, state)
    llm_map, tool_map = await self._execute_phase_4(ai_patterns, state)
    result_map = await self._execute_phase_5(repo_url, ai_patterns, configs, llm_map, tool_map, state)
    return self._create_success_result(result_map)
```

**After**:
```python
def _init_execution_engine(self) -> None:
    phase_1 = AgentMethodExecutionPhase("repository_access", self, "_execute_phase_1_method")
    phase_2 = AgentMethodExecutionPhase("pattern_scanning", self, "_execute_phase_2_method", ["repository_access"])
    phase_3 = AgentMethodExecutionPhase("config_extraction", self, "_execute_phase_3_method", ["repository_access"])
    phase_4 = AgentMethodExecutionPhase("mapping_generation", self, "_execute_phase_4_method", ["pattern_scanning"])
    phase_5 = AgentMethodExecutionPhase("final_map_creation", self, "_execute_phase_5_method", ["config_extraction", "mapping_generation"])
    
    self.execution_engine = ExecutionWorkflowBuilder() \
        .add_phases([phase_1, phase_2, phase_3, phase_4, phase_5]) \
        .set_strategy(ExecutionStrategy.PIPELINE) \
        .build()

async def execute(self, state, context):
    execution_context = ExecutionContext(...)
    result = await self.execution_engine.execute_phases(execution_context)
    return self._create_success_result(result.result.get("final_map_creation", {}).get("result_map", {}))
```

### Example 2: SupplyResearcherAgent (Sequential Strategy)

**Before**:
```python
async def execute(self, state, run_id, stream_updates):
    request = state.user_request
    parsed_request = await self._parse_request(request)
    research_session = await self._create_research_session(parsed_request, state)
    research_result = await self._conduct_research(parsed_request, research_session)
    result = await self._process_results(research_result, parsed_request, research_session)
    state.supply_research_result = result
```

**After**:
```python
def _init_execution_engine(self) -> None:
    phase_1 = AgentMethodExecutionPhase("request_parsing", self, "_execute_parsing_phase")
    phase_2 = AgentMethodExecutionPhase("research_session_creation", self, "_execute_session_creation_phase", ["request_parsing"])
    phase_3 = AgentMethodExecutionPhase("research_execution", self, "_execute_research_phase", ["research_session_creation"])
    phase_4 = AgentMethodExecutionPhase("results_processing", self, "_execute_processing_phase", ["research_execution"])
    
    self.execution_engine = ExecutionWorkflowBuilder() \
        .add_phases([phase_1, phase_2, phase_3, phase_4]) \
        .set_strategy(ExecutionStrategy.SEQUENTIAL) \
        .build()
```

## Best Practices

### 1. Phase Naming
- Use descriptive names that reflect the phase purpose
- Follow snake_case convention
- Keep names under 30 characters

### 2. Dependency Management
- Only specify necessary dependencies
- Avoid circular dependencies
- Use pipeline strategy when phases have data dependencies

### 3. Error Handling
- Let phases raise exceptions for errors
- BaseExecutionEngine handles error propagation
- Use try/catch in main execute method for agent-specific error handling

### 4. State Management
- Access agent state via `context.state`
- Update final state in post-execution hook
- Don't modify state directly in phases unless necessary

### 5. WebSocket Events
- WebSocket events are automatically handled
- Additional custom events can be sent in phase methods
- Always ensure WebSocket manager is available in context

## Extension Hooks

### Pre-execution Hooks
```python
def add_custom_setup(context):
    # Custom setup logic
    pass

engine.add_pre_execution_hook(add_custom_setup)
```

### Post-execution Hooks
```python
def add_custom_cleanup(context, results):
    # Custom cleanup logic
    pass

engine.add_post_execution_hook(add_custom_cleanup)
```

## Testing Strategy

### Unit Testing Phases
```python
async def test_phase_execution():
    agent = YourAgent()
    context = ExecutionContext(...)
    previous_results = {}
    
    result = await agent._execute_phase_1_method(context, previous_results)
    
    assert result["expected_key"] == "expected_value"
```

### Integration Testing
```python
async def test_full_execution():
    agent = YourAgent()
    state = DeepAgentState()
    
    await agent.execute(state, "test_run_id", False)
    
    assert state.agent_result is not None
```

## Validation Checklist

When migrating an agent, ensure:

- [ ] All imports added correctly
- [ ] Execution engine initialized in constructor
- [ ] Phase methods created with correct signatures
- [ ] Main execute method updated to use execution engine
- [ ] Pre and post execution hooks implemented
- [ ] WebSocket events tested
- [ ] Legacy methods preserved for backward compatibility
- [ ] Unit tests updated for new patterns
- [ ] Integration tests passing

## Troubleshooting

### Common Issues

1. **Missing Dependencies**: Ensure phase dependencies are correctly specified
2. **WebSocket Events Not Firing**: Check that ExecutionContext has websocket access
3. **State Not Updated**: Verify post-execution hook updates state correctly
4. **Performance Issues**: Consider using PARALLEL strategy for independent phases

### Debugging

Enable debug logging to see phase execution flow:

```python
import logging
logging.getLogger('netra_backend.app.agents.base.executor').setLevel(logging.DEBUG)
```

## Migration Timeline

The migration should be done incrementally:

1. **Week 1**: Migrate GitHubAnalyzerService (completed)
2. **Week 2**: Migrate SupplyResearcherAgent (completed)
3. **Week 3**: Migrate remaining high-priority agents
4. **Week 4**: Validation and performance testing

## Support

For questions or issues during migration:

1. Check this guide first
2. Review existing migrated agents as examples
3. Test changes thoroughly before deployment
4. Update relevant documentation