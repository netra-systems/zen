# Redis SSOT Violations - Immediate Action Plan

**Status:** CRITICAL - 47 Redis violations causing WebSocket 1011 failures
**Impact:** 0% WebSocket success rate in staging, blocking $500K+ ARR chat functionality
**Created:** 2025-09-15

## Critical Summary

✅ **SSOT Infrastructure:** Ready - `redis_manager` singleton exists
❌ **Current State:** 47 files with direct `RedisManager()` instantiation violations
🔥 **Business Impact:** WebSocket failures preventing all chat functionality

## Immediate Actions Required

### Step 1: Execute Priority 1 Remediation (IMMEDIATE)

```bash
# Test current state
python tests/mission_critical/test_redis_ssot_factory_validation.py

# Execute Priority 1 fixes (dry run first)
python scripts/redis_ssot_remediation_priority1.py --dry-run

# Apply Priority 1 fixes
python scripts/redis_ssot_remediation_priority1.py

# Validate WebSocket functionality
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### Step 2: Immediate Validation

```bash
# Test Redis singleton behavior
python -c "
from netra_backend.app.redis_manager import redis_manager as r1
from netra_backend.app.redis_manager import redis_manager as r2
print(f'Same instance: {id(r1) == id(r2)}')
print(f'Instance ID: {id(r1)}')
"

# Test WebSocket startup
python tests/integration/test_websocket_startup_integration.py
```

### Step 3: Deploy to Staging

```bash
# Deploy with Redis fixes
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Test Golden Path
python tests/e2e/staging/test_golden_path_validation_staging_current.py

# Monitor WebSocket health
curl https://staging.netrasystems.ai/health
```

## Priority 1 Files (WebSocket Core)

These files require **immediate** fixes to restore chat functionality:

1. **WebSocket Manager Integration**
   - `netra_backend/app/websocket_core/manager.py`
   - `netra_backend/app/routes/websocket.py`
   - `netra_backend/app/websocket_core/auth.py`

2. **Agent Execution Components**
   - `netra_backend/app/agents/registry.py`
   - `netra_backend/app/agents/supervisor/execution_engine.py`

3. **Service Initialization**
   - `netra_backend/app/core/startup_validation.py`
   - `netra_backend/app/startup_module.py`

## Migration Pattern

### BEFORE (Causing WebSocket failures):
```python
# Direct instantiation - VIOLATION
redis_manager = RedisManager()
self.redis = RedisManager()
```

### AFTER (SSOT compliant):
```python
# Use singleton - COMPLIANT
from netra_backend.app.redis_manager import redis_manager
self.redis = redis_manager
```

## Expected Results

### Immediate (Within 1 hour):
- [ ] WebSocket success rate > 0%
- [ ] Redis connection pool consolidation
- [ ] No WebSocket 1011 errors

### Short-term (Within 4 hours):
- [ ] WebSocket success rate > 90%
- [ ] All Priority 1 violations fixed
- [ ] Golden Path chat functionality restored

### Long-term (Within 24 hours):
- [ ] All 47 violations fixed
- [ ] Memory usage reduced by 75%
- [ ] 95%+ WebSocket reliability achieved

## Risk Mitigation

### Backup Strategy
- All files automatically backed up before changes
- Git commit after each priority level
- Rollback command available if needed

### Validation at Each Step
1. **Factory Pattern Test:** Confirms singleton behavior
2. **WebSocket Test:** Validates chat functionality
3. **Integration Test:** Confirms no regressions
4. **Staging Test:** End-to-end validation

### Rollback if Needed
```bash
# If something breaks, rollback specific files
git checkout HEAD~1 -- netra_backend/app/websocket_core/
python tests/mission_critical/test_websocket_agent_events_suite.py
```

## Success Metrics

### Technical Metrics
- Redis singleton instances: 47 → 1
- WebSocket success rate: 0% → 95%+
- Memory usage: 75% reduction target
- Connection pool: Single stable pool

### Business Metrics
- Chat functionality: Restored
- User experience: No WebSocket errors
- Revenue impact: $500K+ ARR protected
- System reliability: Enterprise-grade

## File-by-File Priority Breakdown

### Priority 1 (8 files) - Core WebSocket
- WebSocket core components
- Agent registry integration
- Service startup validation

### Priority 2 (12 files) - Agent Execution
- Execution engines
- State persistence
- Tool dispatchers

### Priority 3 (15 files) - Service Infrastructure
- Configuration management
- Health monitoring
- Background services

### Priority 4 (12 files) - Test Infrastructure
- Test fixtures
- Mock implementations
- Integration tests

## Immediate Next Commands

```bash
# 1. Quick validation of current state
python -c "from netra_backend.app.redis_manager import redis_manager; print(f'SSOT ready: {hasattr(redis_manager, \"get_client\")}')"

# 2. Execute Priority 1 remediation
python scripts/redis_ssot_remediation_priority1.py --dry-run
python scripts/redis_ssot_remediation_priority1.py

# 3. Test WebSocket functionality
python tests/mission_critical/test_websocket_agent_events_suite.py

# 4. Deploy to staging if tests pass
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

## Critical Business Context

**This remediation directly addresses:**
- Issue #1278: WebSocket 1011 failures
- Golden Path chat functionality blocking
- $500K+ ARR revenue protection
- User experience degradation

**Success enables:**
- Immediate chat functionality restoration
- Elimination of WebSocket reliability issues
- Foundation for scalable multi-user architecture
- Platform stability for customer retention

---

**NEXT ACTION:** Execute `python scripts/redis_ssot_remediation_priority1.py --dry-run` to begin immediate remediation of WebSocket-critical violations.