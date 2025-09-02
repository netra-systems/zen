# Agent Migration Checklist

## Business Value Justification (BVJ)
- **Segment**: Platform/Internal
- **Business Goal**: Development Velocity & Risk Reduction
- **Value Impact**: Systematic SSOT compliance, reduced migration errors
- **Strategic Impact**: Ensures all agents follow golden pattern consistently

## Pre-Migration Assessment

### 1. Analyze Current Agent Structure
- [ ] **Map current inheritance hierarchy** using `inspect.getmro()` or code review
- [ ] **Identify infrastructure code** (WebSocket handlers, retry logic, execution engines)
- [ ] **List business logic methods** that should be preserved
- [ ] **Document current dependencies** and external integrations
- [ ] **Check for SSOT violations** against existing patterns

### 2. Create MRO Analysis Report
```bash
python -c "
import inspect
from your.agent.module import YourAgent
print('Current MRO:', inspect.getmro(YourAgent))
"
```
- [ ] **Document method resolution paths** for key methods
- [ ] **Identify potential conflicts** with BaseAgent methods
- [ ] **Save MRO report** to `reports/mro_analysis_[agent_name]_[date].md`

### 3. Dependency Impact Analysis
- [ ] **Find all consumers** of the agent being migrated
- [ ] **Document interface changes** that will affect consumers
- [ ] **Identify breaking changes** and required adaptations
- [ ] **Plan backward compatibility** if needed

## Migration Process

### Phase 1: Infrastructure Removal

#### 1.1 Remove Duplicate Infrastructure
- [ ] **Delete WebSocket handlers**
  ```python
  # Remove methods like:
  async def send_websocket_update(self, ...)
  async def emit_agent_started(self, ...)
  async def notify_completion(self, ...)
  ```

- [ ] **Delete retry/reliability logic**
  ```python
  # Remove methods like:
  async def retry_operation(self, ...)
  async def execute_with_circuit_breaker(self, ...)
  def get_health_status(self, ...)
  ```

- [ ] **Delete execution engines**
  ```python
  # Remove methods like:
  async def execute_with_monitoring(self, ...)
  def setup_execution_context(self, ...)
  class CustomExecutionEngine(...)
  ```

- [ ] **Delete state management** (if duplicated)
  ```python
  # Remove if duplicating BaseAgent functionality:
  def set_state(self, ...)
  def get_state(self, ...)
  def validate_transition(self, ...)
  ```

#### 1.2 Remove Mixins (If Present)
- [ ] **Remove mixin imports**
  ```python
  # Remove lines like:
  from .mixins import AgentCommunicationMixin
  from .mixins import AgentLifecycleMixin
  ```

- [ ] **Remove mixin inheritance**
  ```python
  # Change from:
  class YourAgent(BaseSubAgent, AgentCommunicationMixin):
  # To:
  class YourAgent(BaseSubAgent):
  ```

### Phase 2: BaseAgent Integration

#### 2.1 Update Class Declaration
- [ ] **Change inheritance to BaseSubAgent only**
  ```python
  from netra_backend.app.agents.base_agent import BaseSubAgent
  
  class YourAgent(BaseSubAgent):
  ```

#### 2.2 Update Constructor
- [ ] **Call super().__init__ with infrastructure flags**
  ```python
  def __init__(self):
      super().__init__(
          name="YourAgent",
          description="Clear business purpose description",
          enable_reliability=True,      # Circuit breaker + retry
          enable_execution_engine=True, # Modern execution patterns
          enable_caching=False,         # Only if needed
      )
      # Initialize ONLY business logic components
      self.your_core = YourCore()
      self.your_processor = YourProcessor()
  ```

- [ ] **Remove infrastructure initialization**
  ```python
  # Remove lines like:
  self.websocket_handler = WebSocketHandler()
  self.retry_manager = RetryManager()
  self.circuit_breaker = CircuitBreaker()
  ```

### Phase 3: Implement Abstract Methods

#### 3.1 Add Required Methods
- [ ] **Implement validate_preconditions()**
  ```python
  async def validate_preconditions(self, context: ExecutionContext) -> bool:
      """Validate execution preconditions - domain specific"""
      if not context.state.user_request:
          self.logger.warning(f"No user request for {context.run_id}")
          return False
      # Add your domain-specific validation
      return True
  ```

- [ ] **Implement execute_core_logic()**
  ```python
  async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
      """Execute core business logic with WebSocket events"""
      await self.emit_thinking("Starting analysis...")
      
      # Your business logic here
      result = await self.your_processor.process(context.state)
      
      await self.emit_progress("Analysis completed", is_complete=True)
      return result
  ```

#### 3.2 Add WebSocket Events
- [ ] **Add thinking events** for reasoning visibility
  ```python
  await self.emit_thinking("Analyzing user request...")
  ```

- [ ] **Add progress events** for status updates
  ```python
  await self.emit_progress("Processing data...", is_complete=False)
  await self.emit_progress("Analysis completed", is_complete=True)
  ```

- [ ] **Add tool events** for transparency
  ```python
  await self.emit_tool_executing("data_processor", {"method": "nlp"})
  result = await self.process_data()
  await self.emit_tool_completed("data_processor", {"entities": len(result)})
  ```

### Phase 4: Update Business Logic

#### 4.1 Use Inherited Infrastructure
- [ ] **Replace custom retry with execute_with_reliability()**
  ```python
  # Change from:
  await self.retry_operation(operation, max_retries=3)
  # To:
  await self.execute_with_reliability(operation, "operation_name")
  ```

- [ ] **Replace custom WebSocket with inherited methods**
  ```python
  # Change from:
  await self.websocket_handler.send_update(message)
  # To:
  await self.emit_thinking(message)
  ```

- [ ] **Use inherited health monitoring**
  ```python
  # Available automatically:
  health_status = self.get_health_status()
  circuit_status = self.get_circuit_breaker_status()
  ```

#### 4.2 Preserve Business Logic Methods
- [ ] **Keep domain-specific validation methods**
- [ ] **Keep business processing methods** 
- [ ] **Keep helper methods** that contain business logic
- [ ] **Update method signatures** if needed for new patterns

### Phase 5: Backward Compatibility

#### 5.1 Legacy Method Support
- [ ] **Add legacy execute() method if needed**
  ```python
  async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
      """Legacy execute method for backward compatibility"""
      await self.execute_with_reliability(
          lambda: self._execute_main(state, run_id, stream_updates),
          "execute_main",
          fallback=lambda: self._execute_fallback(state, run_id, stream_updates)
      )
  ```

- [ ] **Map legacy parameters** to new ExecutionContext
- [ ] **Ensure interface compatibility** with existing consumers

## Post-Migration Validation

### 1. Code Quality Checks
- [ ] **Run static analysis** to check for unused imports
- [ ] **Verify no infrastructure duplication** remains
- [ ] **Check method resolution order** is clean
- [ ] **Validate SSOT compliance** with BaseAgent patterns

### 2. Testing Requirements

#### 2.1 Unit Tests
- [ ] **Test business logic methods** in isolation
- [ ] **Mock BaseAgent infrastructure** if needed
- [ ] **Test validation methods** with various inputs
- [ ] **Test helper methods** preserve functionality

#### 2.2 Integration Tests
- [ ] **Test with real BaseAgent infrastructure**
- [ ] **Verify WebSocket event emission** works correctly
- [ ] **Test reliability patterns** under failure conditions
- [ ] **Test health monitoring** integration

#### 2.3 E2E Tests
- [ ] **Test complete agent execution flow**
- [ ] **Verify chat experience** with real WebSocket connections
- [ ] **Test fallback scenarios** and error handling
- [ ] **Test consumer integration** if agent has dependents

### 3. Performance Validation
- [ ] **Compare execution times** before and after migration
- [ ] **Monitor memory usage** for any regressions
- [ ] **Test under load** to verify reliability patterns work
- [ ] **Validate circuit breaker** triggers appropriately

## Common Migration Issues

### Issue 1: Method Name Conflicts
**Problem**: Agent method conflicts with BaseAgent method
```python
# Conflict example:
class YourAgent(BaseSubAgent):
    async def emit_thinking(self, message):  # Conflicts with BaseAgent
        # Custom implementation
```

**Solution**: Rename conflicting methods
```python
class YourAgent(BaseSubAgent):
    async def _internal_thinking(self, message):  # Renamed
        # Custom implementation
```

### Issue 2: Missing WebSocket Context
**Problem**: WebSocket events not working
```python
await self.emit_thinking("test")  # No output
```

**Solution**: Ensure WebSocket bridge is set by orchestrator
```python
# This is handled by the execution engine, but verify:
self.set_websocket_bridge(bridge, run_id)
```

### Issue 3: Reliability Not Working
**Problem**: Circuit breaker not triggering
```python
await self.execute_with_reliability(operation, "test")  # No circuit breaker
```

**Solution**: Ensure reliability is enabled in constructor
```python
super().__init__(
    name="YourAgent",
    enable_reliability=True,  # Must be True
)
```

### Issue 4: Legacy Consumers Breaking
**Problem**: Existing code calling old interface
```python
agent = YourAgent()
await agent.old_method(params)  # Method removed
```

**Solution**: Add backward compatibility wrapper
```python
async def old_method(self, params):
    """Backward compatibility wrapper"""
    context = self._build_context_from_legacy_params(params)
    return await self.execute_core_logic(context)
```

## Migration Validation Commands

```bash
# Check for infrastructure duplication
grep -r "emit_thinking\|emit_progress" your_agent_file.py

# Check for proper inheritance
python -c "
from your.agent import YourAgent
import inspect
print('MRO:', inspect.getmro(YourAgent))
print('BaseSubAgent in MRO:', any('BaseSubAgent' in str(cls) for cls in inspect.getmro(YourAgent)))
"

# Run tests
python tests/unified_test_runner.py --category unit --file test_your_agent.py
python tests/unified_test_runner.py --category integration --file test_your_agent_integration.py

# Check health status
python -c "
from your.agent import YourAgent
agent = YourAgent()
print(agent.get_health_status())
"
```

## Success Criteria

- [ ] **Zero infrastructure code** in agent file (WebSocket, retry, execution)
- [ ] **Clean MRO hierarchy** with only BaseSubAgent as parent
- [ ] **All tests passing** (unit, integration, E2E)
- [ ] **WebSocket events working** in chat experience
- [ ] **Reliability patterns active** (circuit breaker, retry)
- [ ] **Performance maintained** or improved
- [ ] **Backward compatibility** if required by consumers
- [ ] **Code size reduced** by 60-80% through infrastructure removal

## Rollback Plan

If migration fails, rollback steps:

1. **Revert to previous version** from git
2. **Document failure reasons** in migration report
3. **Create targeted fix plan** for specific issues
4. **Re-attempt migration** with lessons learned

## Related Documentation

- [Golden Pattern Guide](agent_golden_pattern_guide.md)
- [Architecture Decision Record](adr/agent_ssot_consolidation.md)
- [BaseAgent API Reference](../SPEC/base_agent_api.xml)
- [SSOT Consolidation Learnings](../SPEC/learnings/ssot_consolidation_20250825.xml)

---

*This checklist ensures systematic, risk-free migration to the golden pattern while maintaining business value and system stability.*