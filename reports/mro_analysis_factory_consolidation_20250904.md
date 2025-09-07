# MRO Analysis: Agent Instance Factory Consolidation
## Date: 2025-09-04
## Author: Factory Consolidation Specialist

## Executive Summary
This report documents the Method Resolution Order (MRO) and class hierarchy analysis for consolidating the duplicate agent instance factory implementations, as mandated by CLAUDE.md Section 3.6.

## Critical SSOT Violations Identified

### 1. Duplicate Factory Implementations
- **Base Factory**: `agent_instance_factory.py` (1072 lines) - KEEP
- **Optimized Factory**: `agent_instance_factory_optimized.py` (574 lines) - DELETE AFTER MERGE

### 2. Duplicate WebSocket Emitter Implementations
- `netra_backend.app.agents.supervisor.agent_instance_factory.UserWebSocketEmitter` (line 48)
- `netra_backend.app.agents.supervisor.agent_instance_factory_optimized.OptimizedUserWebSocketEmitter` (line 52)
- `netra_backend.app.services.websocket_bridge_factory.UserWebSocketEmitter` (line 391)
- `netra_backend.app.services.user_websocket_emitter.UserWebSocketEmitter` (line 27)

## Class Hierarchy Analysis

### Base Factory (`agent_instance_factory.py`)

```
UserWebSocketEmitter (line 48)
├── No inheritance
├── Direct instantiation
└── Methods:
    ├── __init__(user_id, thread_id, run_id, websocket_bridge)
    ├── notify_agent_started(agent_name, context)
    ├── notify_agent_thinking(agent_name, reasoning, step_number, progress_percentage)
    ├── notify_tool_executing(tool_name, parameters)
    ├── notify_tool_completed(tool_name, result, execution_time_ms)
    ├── notify_agent_completed(agent_name, result, execution_time_ms)
    └── cleanup()

AgentInstanceFactory (line 330)
├── No inheritance
├── Singleton pattern (via module-level instance)
└── Methods:
    ├── __init__()
    ├── initialize(agent_registry, agent_class_registry, websocket_bridge, websocket_manager)
    ├── create_user_context(user_id, thread_id, run_id, db_session, websocket_bridge)
    ├── create_agent_instance(agent_name, user_context, **kwargs)
    ├── get_registry_info()
    └── cleanup_user_context(user_context)
```

### Optimized Factory (`agent_instance_factory_optimized.py`)

```
OptimizedUserWebSocketEmitter (line 52)
├── No inheritance
├── Object pooling support
├── __slots__ optimization
└── Methods:
    ├── __init__() - Minimal initialization
    ├── initialize(user_id, thread_id, run_id, websocket_bridge) - Fast reset
    ├── reset() - For object reuse
    ├── notify_agent_started(agent_name, context)
    ├── notify_agent_thinking(agent_name, reasoning, step_number, progress_percentage)
    ├── notify_agent_completed(agent_name, result, execution_time_ms)
    └── cleanup()

WebSocketEmitterPool (line 171)
├── No inheritance
├── Object pool pattern
└── Methods:
    ├── __init__(initial_size=10, max_size=100)
    ├── acquire(user_id, thread_id, run_id, websocket_bridge)
    ├── release(emitter)
    └── get_stats()

OptimizedAgentInstanceFactory (line 224)
├── No inheritance
├── Performance optimizations
└── Methods:
    ├── __init__()
    ├── _lazy_init()
    ├── initialize(agent_registry, agent_class_registry, websocket_bridge, websocket_manager)
    ├── create_user_context(user_id, thread_id, run_id, db_session, websocket_bridge)
    ├── _create_emitter_fast(user_id, thread_id, run_id, websocket_bridge)
    ├── create_agent_instance(agent_name, user_context, **kwargs)
    ├── _get_agent_class_cached(agent_name)
    ├── cleanup_user_context(user_context)
    ├── get_pool_stats()
    └── cleanup()
```

## Performance Optimizations to Preserve

### From Optimized Factory
1. **WebSocket Emitter Pooling**
   - Initial pool size: 10
   - Max pool size: 100
   - Reduces object creation overhead
   - Fast acquire/release operations

2. **Class Caching**
   - LRU cache for agent class lookups
   - Cache size: 128 entries
   - Reduces registry lookup overhead

3. **Lazy Initialization**
   - Infrastructure components loaded on demand
   - Reduces startup time

4. **__slots__ Usage**
   - Memory optimization for emitter instances
   - Reduces attribute access overhead

5. **Metric Sampling**
   - Sample rate: 10% by default
   - Reduces metric collection overhead

## Consumer Analysis

### Base Factory Consumers (31 files)
**Critical Consumers:**
- `netra_backend.app.dependencies.py` - Request dependency injection
- `netra_backend.app.agents.supervisor.agent_registry.py` - Agent registration
- `netra_backend.app.agents.supervisor.execution_engine.py` - Execution orchestration
- `netra_backend.app.agents.supervisor.execution_engine_factory.py` - Engine creation

**Test Consumers:**
- 15+ test files rely on base factory
- Mission critical tests use base factory

### Optimized Factory Consumers (2 files)
- `scripts.load_test_isolation.py` - Load testing only
- `tests.performance.test_isolation_performance.py` - Performance testing only

## Breaking Changes Risk Assessment

### High Risk Areas
1. **WebSocket Emitter Interface Changes**
   - Must maintain exact method signatures
   - Event notification flow must remain identical
   - Thread/user isolation must be preserved

2. **Factory Initialization**
   - Must support both eager and lazy initialization
   - Registry references must remain compatible

### Low Risk Areas
1. **Internal Optimizations**
   - Pooling is transparent to consumers
   - Caching is transparent to consumers
   - Can be toggled via configuration

## Migration Strategy

### Phase 1: Create Configuration Architecture
```python
@dataclass
class FactoryPerformanceConfig:
    enable_emitter_pooling: bool = True
    pool_initial_size: int = 20
    pool_max_size: int = 200
    enable_class_caching: bool = True
    cache_size: int = 128
    enable_metrics: bool = True
    metrics_sample_rate: float = 0.1
```

### Phase 2: Merge Optimizations
1. Add pooling as configurable feature
2. Add caching as configurable feature
3. Preserve all public interfaces
4. Support both initialization modes

### Phase 3: Consolidate WebSocket Emitters
1. Create single `services/websocket_emitter.py`
2. Support pooling via configuration
3. Maintain backward compatibility

### Phase 4: Update All Imports
1. Update 31 base factory imports
2. Update 2 optimized factory imports
3. Update 4+ WebSocket emitter imports

## Validation Requirements

1. **Performance Benchmarks**
   - Agent creation: <10ms
   - Context creation: <5ms
   - Cleanup: <2ms
   - Support 100+ concurrent users

2. **Functional Tests**
   - All 5 WebSocket events working
   - User isolation preserved
   - No memory leaks from pooling
   - Mission critical tests passing

## Rollback Plan

1. Keep backups of original files
2. Feature flag for gradual rollout:
   ```python
   USE_CONSOLIDATED_FACTORY = os.getenv('USE_CONSOLIDATED_FACTORY', 'true')
   ```
3. Performance monitoring during rollout
4. Immediate rollback if regression detected

## Next Steps

1. ✅ Complete MRO analysis
2. ⏳ Extract performance optimizations
3. ⏳ Design unified configuration
4. ⏳ Implement consolidation
5. ⏳ Create comprehensive tests
6. ⏳ Migrate all imports
7. ⏳ Delete optimized factory
8. ⏳ Update documentation

## Appendix: Method Signature Compatibility

### Critical Methods to Preserve
```python
# UserWebSocketEmitter interface
async def notify_agent_started(agent_name: str, context: Optional[Dict[str, Any]] = None) -> bool
async def notify_agent_thinking(agent_name: str, reasoning: str, step_number: Optional[int] = None, progress_percentage: Optional[float] = None) -> bool
async def notify_tool_executing(tool_name: str, parameters: Optional[Dict[str, Any]] = None) -> bool
async def notify_tool_completed(tool_name: str, result: Optional[Any] = None, execution_time_ms: Optional[float] = None) -> bool
async def notify_agent_completed(agent_name: str, result: Optional[Dict[str, Any]] = None, execution_time_ms: Optional[float] = None) -> bool

# AgentInstanceFactory interface
def initialize(agent_registry: AgentRegistry, agent_class_registry: AgentClassRegistry, websocket_bridge: AgentWebSocketBridge, websocket_manager: WebSocketManager) -> None
async def create_user_context(user_id: str, thread_id: str, run_id: str, db_session: AsyncSession, websocket_bridge: Optional[AgentWebSocketBridge] = None) -> UserExecutionContext
async def create_agent_instance(agent_name: str, user_context: UserExecutionContext, **kwargs) -> BaseAgent
async def cleanup_user_context(user_context: UserExecutionContext) -> None
```

## Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Performance regression | Low | High | Benchmark before/after |
| WebSocket event loss | Low | Critical | Mission critical tests |
| Memory leak from pooling | Medium | High | Cleanup monitoring |
| Import migration errors | Medium | Medium | Automated search/replace |
| Test failures | High | Low | Run full test suite |

## Conclusion

The consolidation is feasible with proper configuration architecture. All optimizations can be preserved while eliminating duplicate code. The main risk is in WebSocket emitter consolidation, which requires careful testing of all 5 critical events.