# WebSocket v2 Critical Services Migration Guide

## Executive Summary

This document provides a comprehensive guide for migrating critical production services from the deprecated singleton `get_websocket_manager()` pattern to the new factory pattern `create_websocket_manager(user_context)`. This migration is **SECURITY CRITICAL** and addresses multiple vulnerabilities that could lead to user data cross-contamination.

## Business Value Justification (BVJ)

- **Segment:** ALL (Free → Enterprise)
- **Business Goal:** Eliminate critical WebSocket isolation vulnerabilities
- **Value Impact:** Prevents user data cross-contamination and connection hijacking
- **Revenue Impact:** Prevents catastrophic security breaches that could destroy business trust and revenue

## Critical Vulnerabilities Addressed

1. **User Isolation Failures:** Shared state causing data leakage between users
2. **Connection Hijacking:** Potential for user A to receive user B's messages
3. **Race Conditions:** Concurrent operations affecting wrong users
4. **Memory Leaks:** Accumulation of stale connections across users
5. **Silent Failures:** Security violations without error notifications
6. **Broadcast Leakage:** Information intended for one user sent to others

## Migration Script Overview

The migration script `scripts/migrate_websocket_v2_critical_services.py` provides:

- **Automated Analysis:** Identifies all deprecated usage patterns
- **Safe Migration:** Creates backups before any changes
- **Dry-Run Mode:** Preview changes without modification
- **Comprehensive Reporting:** Detailed migration analysis and results
- **User Context Detection:** Identifies available context sources
- **Manual Review Flags:** Marks areas requiring human intervention

## Current State Analysis

Based on the latest validation run:

- **Total Critical Services:** 17 services identified
- **Services Requiring Migration:** 17 (100%)
- **High-Complexity Services:** 16 services (complexity score 5/5)
- **Services with User Context:** 1 service (agent_service_core.py)
- **Manual Review Required:** 16 services need context creation

### Services Requiring Migration

#### High Priority (Core Agent Services)
- `agent_service_core.py` - ✅ Has user context available
- `agent_service_factory.py` - ⚠️ Needs user context injection
- `message_handler_base.py` - ⚠️ Needs context in handle methods
- `message_handler_utils.py` - ⚠️ Utility functions need context parameters
- `thread_service.py` - ⚠️ Service methods need context
- `generation_job_manager.py` - ⚠️ Job operations need user isolation

#### Quality Management Services
- `websocket/quality_manager.py` - ⚠️ Central quality coordinator
- `websocket/quality_message_router.py` - ⚠️ Message routing needs isolation
- `websocket/quality_validation_handler.py` - ⚠️ Validation per user
- `websocket/quality_report_handler.py` - ⚠️ User-specific reports
- `websocket/quality_metrics_handler.py` - ⚠️ Per-user metrics
- `websocket/quality_alert_handler.py` - ⚠️ Targeted alerts

#### Infrastructure Services
- `websocket/message_handler.py` - ⚠️ Core message handling
- `websocket/message_queue.py` - ⚠️ Message queuing system
- `corpus/clickhouse_operations.py` - ⚠️ Data operations need user context
- `memory_startup_integration.py` - ⚠️ Startup integration
- `websocket_event_router.py` - ⚠️ Event routing system

## Migration Process

### Phase 1: Preparation and Analysis

```bash
# 1. Validate current state
python scripts/migrate_websocket_v2_critical_services.py --validate-only

# 2. Perform dry-run to see changes
python scripts/migrate_websocket_v2_critical_services.py --dry-run --verbose

# 3. Review the generated migration report
# Check: backups/websocket_v2_migration_TIMESTAMP/migration_report_TIMESTAMP.md
```

### Phase 2: Automated Migration

```bash
# Perform the actual migration (creates backups automatically)
python scripts/migrate_websocket_v2_critical_services.py --force

# Verify results
python scripts/migrate_websocket_v2_critical_services.py --validate-only
```

### Phase 3: Manual Review and Context Creation

After automated migration, **CRITICAL MANUAL STEPS** are required:

#### 1. Services Without User Context (16 services)

For services marked with `# MANUAL REVIEW REQUIRED`, you must:

**A. Add User Context Parameters to Functions/Methods:**
```python
# BEFORE (vulnerable)
async def process_message(message: Dict[str, Any]) -> None:
    websocket_manager = get_websocket_manager()  # DEPRECATED
    
# AFTER (secure)
async def process_message(message: Dict[str, Any], user_context: UserExecutionContext) -> None:
    websocket_manager = create_websocket_manager(user_context)  # SECURE
```

**B. Update Service Constructors to Accept Context:**
```python
# BEFORE (vulnerable)
class QualityManager:
    def __init__(self):
        self.websocket_manager = get_websocket_manager()  # SHARED STATE
        
# AFTER (secure) 
class QualityManager:
    def __init__(self, user_context: UserExecutionContext):
        self.user_context = user_context
        self.websocket_manager = create_websocket_manager(user_context)  # ISOLATED
```

**C. Context Propagation in Message Handlers:**
```python
# BEFORE (vulnerable)
async def handle_quality_request(self, message: Dict) -> None:
    manager = get_websocket_manager()  # CROSS-USER CONTAMINATION RISK
    
# AFTER (secure)
async def handle_quality_request(self, message: Dict, user_context: UserExecutionContext) -> None:
    manager = create_websocket_manager(user_context)  # USER-ISOLATED
```

#### 2. Context Creation Patterns

**Extract Context from WebSocket Connections:**
```python
# In WebSocket route handlers
async def websocket_endpoint(websocket: WebSocket):
    user_context = UserExecutionContext(
        user_id=await get_user_id_from_token(websocket),
        thread_id=websocket.headers.get("thread-id"),
        run_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        websocket_connection_id=websocket.client.host + str(websocket.client.port)
    )
```

**Context from HTTP Requests:**
```python
# In API endpoints
async def api_endpoint(request: Request, user_id: str):
    user_context = UserExecutionContext(
        user_id=user_id,
        thread_id=request.headers.get("thread-id", str(uuid.uuid4())),
        run_id=str(uuid.uuid4()),
        request_id=request.headers.get("request-id", str(uuid.uuid4()))
    )
```

## Testing Strategy

### Automated Testing
```bash
# Run WebSocket isolation tests
python tests/mission_critical/test_websocket_agent_events_suite.py

# Run full integration tests with real services
python tests/unified_test_runner.py --real-services --category integration

# Run end-to-end tests
python tests/unified_test_runner.py --category e2e
```

### Manual Testing Checklist

- [ ] **Multi-User Isolation Test:** Verify user A cannot see user B's messages
- [ ] **Connection Lifecycle Test:** Verify proper cleanup when connections close
- [ ] **Error Boundary Test:** Verify failures don't affect other users
- [ ] **Performance Test:** Verify no performance degradation under load
- [ ] **Memory Leak Test:** Verify no memory accumulation over time

## Critical Success Criteria

### Security Requirements (MUST PASS)
- [ ] **Zero Cross-User Message Leakage:** No messages sent to wrong users
- [ ] **Complete Context Isolation:** Each manager instance serves only one user
- [ ] **Proper Connection Cleanup:** No stale connections accumulate
- [ ] **Error Isolation:** User errors don't affect other users
- [ ] **Audit Trail:** All WebSocket operations are traceable to specific users

### Performance Requirements
- [ ] **Response Time:** < 100ms for WebSocket message handling
- [ ] **Memory Usage:** No memory leaks under normal operation
- [ ] **Concurrent Users:** Support 50+ concurrent users without degradation
- [ ] **Connection Scaling:** Handle user connection spikes gracefully

## Rollback Plan

If critical issues are discovered after migration:

### Immediate Rollback (< 5 minutes)
```bash
# 1. Stop services
docker-compose down

# 2. Restore from backups
cp -r backups/websocket_v2_migration_TIMESTAMP/* ./

# 3. Restart services
docker-compose up -d

# 4. Verify rollback success
python tests/smoke_tests.py
```

### Gradual Rollback (per service)
```bash
# Restore individual service files
cp backups/websocket_v2_migration_TIMESTAMP/netra_backend/app/services/SERVICE_NAME.py \
   netra_backend/app/services/SERVICE_NAME.py
   
# Restart specific services
docker-compose restart backend
```

## Monitoring and Alerts

### Key Metrics to Monitor
- **User Isolation Violations:** Zero tolerance
- **WebSocket Connection Errors:** < 1% error rate
- **Message Delivery Failures:** < 0.1% failure rate
- **Memory Usage:** Monitor for leaks
- **Response Times:** Alert if > 200ms

### Critical Alerts
- **SECURITY VIOLATION:** Cross-user message delivery
- **PERFORMANCE DEGRADATION:** Response times > 500ms
- **MEMORY LEAK:** Continuous memory growth
- **CONNECTION OVERFLOW:** Too many stale connections

## Post-Migration Verification

### Phase 1: Immediate Verification (0-24 hours)
- [ ] All services start without errors
- [ ] WebSocket connections establish successfully
- [ ] Message delivery works for single users
- [ ] No obvious cross-user contamination
- [ ] Performance within expected ranges

### Phase 2: Extended Verification (1-7 days)
- [ ] Multi-user concurrent usage testing
- [ ] Memory usage remains stable
- [ ] No user isolation violations detected
- [ ] Error rates within normal ranges
- [ ] User experience remains positive

### Phase 3: Full Production Validation (1-4 weeks)
- [ ] Performance under full production load
- [ ] Long-term memory stability
- [ ] User satisfaction maintained
- [ ] Zero security incidents
- [ ] Monitoring dashboards healthy

## Troubleshooting Common Issues

### Issue: "UserExecutionContext cannot be None"
**Cause:** Service called without proper context
**Solution:** Ensure all service methods receive user_context parameter

### Issue: "Resource limits exceeded for user"
**Cause:** Too many WebSocket managers per user
**Solution:** Review connection cleanup logic, increase limits if needed

### Issue: "Connection user_id mismatch"
**Cause:** Context inconsistency
**Solution:** Verify user_context creation matches connection user

### Issue: Performance degradation
**Cause:** Creating too many manager instances
**Solution:** Implement connection pooling or manager reuse patterns

## Additional Resources

- **WebSocket Factory Documentation:** `/netra_backend/app/websocket_core/websocket_manager_factory.py`
- **User Context Documentation:** `/netra_backend/app/models/user_execution_context.py`
- **Architecture Guide:** `/USER_CONTEXT_ARCHITECTURE.md`
- **Test Suite:** `/tests/mission_critical/test_websocket_agent_events_suite.py`

## Contact and Support

For migration questions or issues:
- **Technical Issues:** Check logs in `/logs/websocket_migration_TIMESTAMP.log`
- **Security Concerns:** Immediately review security audit logs
- **Performance Issues:** Use monitoring dashboards and profiling tools
- **Rollback Needs:** Follow rollback plan above, document reasons

---

**⚠️ CRITICAL REMINDER:** This migration addresses serious security vulnerabilities. Do not skip manual review steps or testing phases. User data security depends on proper implementation of the factory pattern with complete user isolation.