# Agent Golden Pattern Quick Reference

## TL;DR - The Golden Rule
**All agents inherit from BaseSubAgent. Agents contain ONLY business logic. Infrastructure is inherited.**

```python
from netra_backend.app.agents.base_agent import BaseSubAgent

class YourAgent(BaseSubAgent):
    def __init__(self):
        super().__init__(
            name="YourAgent",
            description="Business purpose",
            enable_reliability=True,      # Circuit breaker + retry
            enable_execution_engine=True, # Modern execution patterns
            enable_caching=True,          # Optional caching
        )
        # Initialize ONLY business logic
        
    async def validate_preconditions(self, context) -> bool:
        # Your validation logic
        return True
        
    async def execute_core_logic(self, context) -> Dict[str, Any]:
        await self.emit_thinking("Starting analysis...")
        # Your business logic
        await self.emit_progress("Completed", is_complete=True)
        return result
```

## BaseAgent Features Available

### WebSocket Events (For Chat Experience)
```python
await self.emit_thinking("Reasoning step...")                    # Show AI thinking
await self.emit_progress("Processing...", is_complete=False)     # Status updates  
await self.emit_progress("Done!", is_complete=True)              # Final status
await self.emit_tool_executing("data_processor", params)        # Tool transparency
await self.emit_tool_completed("data_processor", result)        # Tool results
await self.emit_error("Error occurred", "ValidationError")      # Error reporting
```

### Reliability Patterns
```python
# Automatic retry with circuit breaker
await self.execute_with_reliability(
    operation=lambda: your_operation(),
    operation_name="your_operation",
    fallback=lambda: fallback_operation()  # Optional
)

# Health monitoring
health = self.get_health_status()                 # Comprehensive health
circuit = self.get_circuit_breaker_status()       # Circuit breaker status
```

### Execution Infrastructure
```python
# Modern execution (automatic via execute_core_logic)
# Legacy compatibility via execute() method
# Timing and performance monitoring (automatic)
# State management and lifecycle (automatic)
```

### Configuration Options
```python
super().__init__(
    name="AgentName",                    # Required: Agent identifier
    description="Purpose",               # Required: Business description
    enable_reliability=True,             # Circuit breaker + retry patterns
    enable_execution_engine=True,        # Modern execution infrastructure  
    enable_caching=True,                 # Redis caching (optional)
    llm_manager=None,                    # Auto-created if None
    tool_dispatcher=None,                # Auto-created if None
    redis_manager=None,                  # Auto-created if None
)
```

## Required Methods

### Must Implement
```python
async def validate_preconditions(self, context: ExecutionContext) -> bool:
    """Check if agent can execute - domain specific validation"""
    # Validate inputs, check prerequisites
    return True

async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
    """Core business logic with WebSocket events"""
    await self.emit_thinking("Step 1: Analysis")
    # Your processing logic
    await self.emit_progress("Step completed")
    return {"result": "success"}
```

### Optional Overrides
```python
async def execute(self, state, run_id, stream_updates):
    """Legacy compatibility - usually delegates to execute_core_logic"""

async def shutdown(self):
    """Custom cleanup - call super().shutdown() first"""

def get_health_status(self):
    """Extend health reporting - call super().get_health_status() first"""
```

## Common Patterns

### Basic Agent Structure
```python
class DataAgent(BaseSubAgent):
    def __init__(self):
        super().__init__(
            name="DataAgent",
            description="Processes data requests",
            enable_reliability=True,
            enable_execution_engine=True,
        )
        self.processor = DataProcessor()  # Business logic only
        
    async def validate_preconditions(self, context) -> bool:
        return bool(context.state.data_request)
        
    async def execute_core_logic(self, context) -> Dict[str, Any]:
        await self.emit_thinking("Analyzing data request...")
        
        # Business logic with progress updates
        await self.emit_progress("Extracting entities...")
        entities = self.processor.extract_entities(context.state.data_request)
        
        await self.emit_progress("Processing analysis...")  
        result = self.processor.analyze(entities)
        
        await self.emit_progress("Analysis complete", is_complete=True)
        return result
```

### Legacy Compatibility Pattern
```python
async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool):
    """Legacy execute method for backward compatibility"""
    await self.execute_with_reliability(
        lambda: self._execute_main(state, run_id, stream_updates),
        "execute_main",
        fallback=lambda: self._execute_fallback(state, run_id, stream_updates)
    )
    
async def _execute_main(self, state, run_id, stream_updates):
    """Delegate to modern execute_core_logic"""
    context = ExecutionContext(
        run_id=run_id,
        agent_name=self.name,
        state=state,
        stream_updates=stream_updates,
        # ... other context fields
    )
    return await self.execute_core_logic(context)
```

### Error Handling Pattern
```python
async def execute_core_logic(self, context) -> Dict[str, Any]:
    try:
        await self.emit_thinking("Starting processing...")
        result = await self.process_data(context.state)
        await self.emit_progress("Processing complete", is_complete=True)
        return result
    except ValidationError as e:
        await self.emit_error(f"Validation failed: {e}", "ValidationError")
        return {"error": "validation_failed", "message": str(e)}
    except Exception as e:
        await self.emit_error(f"Processing failed: {e}", "ProcessingError")
        raise  # Let reliability patterns handle retry
```

## What NOT to Do

### ❌ Don't Duplicate Infrastructure
```python
# DON'T: Implement WebSocket handlers
async def send_websocket_update(self, message):
    # This duplicates BaseAgent functionality
    
# DON'T: Implement retry logic  
async def retry_operation(self, op, retries=3):
    # This duplicates BaseAgent functionality
    
# DON'T: Implement health monitoring
def get_health_status(self):
    # This duplicates BaseAgent functionality
```

### ❌ Don't Use Multiple Inheritance
```python
# DON'T: Mix inheritance patterns
class BadAgent(BaseSubAgent, SomeMixin, AnotherMixin):
    # Leads to MRO conflicts
```

### ❌ Don't Bypass Infrastructure
```python
# DON'T: Direct infrastructure access
from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge

async def execute_core_logic(self, context):
    bridge = await get_agent_websocket_bridge()  # WRONG!
    # Use self.emit_thinking() instead
```

## Testing Quick Start

### Unit Test Template
```python
import pytest
from your_agent import YourAgent

@pytest.mark.asyncio
async def test_agent_validation():
    agent = YourAgent()
    context = ExecutionContext(
        state=mock_state,
        run_id="test-123"
    )
    
    # Test business logic only
    assert await agent.validate_preconditions(context) == True
    
@pytest.mark.asyncio  
async def test_agent_execution():
    agent = YourAgent()
    context = ExecutionContext(
        state=mock_state_with_data,
        run_id="test-123"
    )
    
    result = await agent.execute_core_logic(context)
    assert result["status"] == "success"
```

### Integration Test Template
```python
@pytest.mark.asyncio
async def test_agent_with_infrastructure():
    # Test with real BaseAgent infrastructure
    agent = YourAgent()
    
    # Mock WebSocket bridge
    mock_bridge = Mock()
    agent.set_websocket_bridge(mock_bridge, "test-run-123")
    
    result = await agent.execute_modern(mock_state, "test-run-123", True)
    
    # Verify WebSocket events were called
    assert mock_bridge.notify_agent_thinking.called
    assert result.success == True
```

## File Size Guidelines

- **Target Size**: 150-200 lines for typical agent
- **TriageSubAgent**: 178 lines (golden standard)
- **If >300 lines**: Consider splitting business logic into separate modules
- **Infrastructure code**: Should be 0 lines (inherited from BaseAgent)

## Performance Tips

- Use `enable_caching=True` for expensive operations
- Implement efficient `validate_preconditions()` to fail fast
- Use appropriate WebSocket event frequency (don't spam)
- Monitor health status for performance issues

## Debugging Commands

```bash
# Check agent health
python -c "
from your.agent import YourAgent
agent = YourAgent()
print(agent.get_health_status())
"

# Check MRO (Method Resolution Order)
python -c "
import inspect
from your.agent import YourAgent
print('MRO:', inspect.getmro(YourAgent))
"

# Test WebSocket events
python -c "
from your.agent import YourAgent
agent = YourAgent()
print('WebSocket available:', agent.has_websocket_context())
"
```

## Getting Help

1. **Golden Pattern Guide**: [docs/agent_golden_pattern_guide.md](agent_golden_pattern_guide.md)
2. **Migration Checklist**: [docs/agent_migration_checklist.md](agent_migration_checklist.md)
3. **Architecture Decision**: [docs/adr/agent_ssot_consolidation.md](adr/agent_ssot_consolidation.md)
4. **BaseAgent Source**: `netra_backend/app/agents/base_agent.py`
5. **Golden Example**: `netra_backend/app/agents/triage_sub_agent.py`

---

*Keep this guide handy when developing agents. Remember: Business logic only, everything else is inherited!*