# UserContext Migration Roadmap

## Executive Summary
This roadmap outlines the complete migration path from global singleton patterns to UserContext-based isolation across the Netra Apex platform.

## Current State (2025-01-03)

### ✅ Phase 1: Core Tool System (COMPLETED)
- [x] Created UserContextToolFactory for per-user tool systems
- [x] Modified UnifiedToolDispatcher to accept existing registries
- [x] Updated SupervisorAgent to use UserContext-based tools
- [x] Removed global tool registry creation from startup (smd.py)
- [x] Documentation complete

### 🚧 Phase 2: Agent Infrastructure (IN PROGRESS)
Current focus areas with existing warnings in logs:

#### 2.1 AgentRegistry Migration
**Status**: Has migration helpers, marked DEPRECATED
**Actions Required**:
1. Update all code using `AgentRegistry.get()` to use `AgentInstanceFactory`
2. Migrate agent registration from startup to lazy instantiation
3. Remove global WebSocket bridge setting

#### 2.2 ExecutionEngine Factory Adoption
**Status**: ExecutionEngineFactory exists, needs wider adoption
**Actions Required**:
1. Update all ExecutionEngine creation to use factory
2. Remove direct ExecutionEngine instantiation
3. Ensure UserContext propagation

## Detailed Migration Plan

### Phase 2: Agent Infrastructure (Q1 2025)

#### Week 1: AgentRegistry Deprecation
```python
# BEFORE (Global):
agent = agent_registry.get("triage")

# AFTER (Per-request):
factory = get_agent_instance_factory()
agent = await factory.create_agent_instance("triage", context)
```

**Files to Update**:
- [ ] `netra_backend/app/services/agent_service_core.py`
- [ ] `netra_backend/app/api/endpoints/agent_endpoints.py`
- [ ] All test files using AgentRegistry

#### Week 2: ExecutionEngine Migration
```python
# BEFORE (Direct creation):
engine = ExecutionEngine(registry, bridge, None)

# AFTER (Factory):
factory = get_execution_engine_factory()
engine = await factory.create_for_user(context)
```

**Files to Update**:
- [ ] `netra_backend/app/agents/supervisor_consolidated.py`
- [ ] `netra_backend/app/services/agent_service_core.py`

### Phase 3: WebSocket Isolation (Q1 2025)

#### Week 3: WebSocket Manager Factory
Create factory for WebSocket managers to ensure channel isolation:

```python
class WebSocketManagerFactory:
    async def create_for_user(self, context: UserExecutionContext):
        return UserWebSocketManager(
            user_id=context.user_id,
            thread_id=context.thread_id
        )
```

**New Files**:
- [ ] `netra_backend/app/websocket_core/websocket_manager_factory.py`
- [ ] `netra_backend/app/websocket_core/user_websocket_manager.py`

### Phase 4: Database Connection Isolation (Q2 2025)

#### Week 4-5: Per-User Connection Pooling
Implement connection limits per user:

```python
class UserDatabasePoolFactory:
    def get_pool_for_user(self, user_id: str):
        return self._pools.setdefault(
            user_id, 
            create_pool(max_connections=5)
        )
```

### Phase 5: Testing & Validation (Q2 2025)

#### Week 6: Comprehensive Testing
- [ ] Create concurrent user test suite
- [ ] Load test with 100+ concurrent users
- [ ] Memory leak testing
- [ ] Resource cleanup validation

## Migration Checklist

### Code Changes
- [ ] Remove all global singleton usage
- [ ] Update all agent instantiation
- [ ] Migrate all ExecutionEngine creation
- [ ] Update WebSocket manager usage
- [ ] Add UserContext to all API endpoints

### Testing Requirements
- [ ] Unit tests for all factories
- [ ] Integration tests for user isolation
- [ ] Performance tests with concurrent users
- [ ] Memory/resource leak tests
- [ ] E2E tests with multiple users

### Documentation Updates
- [ ] Update API documentation
- [ ] Create migration guides for each component
- [ ] Update architectural diagrams
- [ ] Add troubleshooting guides

## Success Criteria

### Technical Metrics
- Zero global state warnings in logs
- Support for 10+ concurrent users without issues
- < 100ms overhead from factory patterns
- Zero shared state between user requests

### Business Metrics
- No increase in error rates
- Maintain current response times
- Support multi-tenant deployment
- Enable horizontal scaling

## Risk Mitigation

### Identified Risks
1. **Performance Impact**: Factory overhead
   - Mitigation: Object pooling, lazy initialization
   
2. **Backward Compatibility**: Breaking existing integrations
   - Mitigation: Adapter patterns, gradual migration
   
3. **Testing Coverage**: Missing edge cases
   - Mitigation: Comprehensive test suite, staged rollout

## Timeline

### Q1 2025
- Week 1-2: Agent Infrastructure (Phase 2)
- Week 3: WebSocket Isolation (Phase 3)
- Week 4: Testing & Stabilization

### Q2 2025
- Week 1-2: Database Isolation (Phase 4)
- Week 3-4: Performance Optimization
- Week 5-6: Final Testing & Validation (Phase 5)

## Rollback Plan

Each phase can be independently rolled back:
1. Feature flags for factory usage
2. Parallel running of old/new patterns
3. Gradual migration with monitoring
4. Automated rollback on error threshold

## Next Steps

1. **Immediate** (Today):
   - Review and approve roadmap
   - Set up tracking dashboard
   - Begin Phase 2 implementation

2. **This Week**:
   - Complete AgentRegistry migration
   - Start ExecutionEngine factory adoption
   - Create test harness for concurrent users

3. **This Month**:
   - Complete Phase 2 and 3
   - Performance testing
   - Documentation updates

## Dependencies

### Technical Dependencies
- Python 3.11+ (for better async performance)
- Redis 7.0+ (for better connection pooling)
- PostgreSQL 14+ (for better concurrency)

### Team Dependencies
- Code review from architecture team
- Performance testing from QA team
- Deployment support from DevOps

## Monitoring & Observability

### Key Metrics to Track
- Factory creation time (p50, p95, p99)
- Memory usage per user context
- Active contexts count
- Resource cleanup success rate
- Global state warning frequency

### Dashboards Required
- User isolation metrics
- Factory performance
- Resource utilization
- Error rates by component

---

**Document Status**: DRAFT - Pending Review
**Author**: Architecture Team
**Date**: 2025-01-03
**Review By**: 2025-01-10