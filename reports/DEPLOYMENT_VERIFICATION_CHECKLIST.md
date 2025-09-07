# Deployment Verification Checklist

## 🚨 CRITICAL: Pre-Deployment Verification

This checklist MUST be completed before ANY deployment to staging or production environments.

**Last Updated:** 2025-09-01  
**Critical Systems:** Deterministic Startup, WebSocket Events, Health Monitoring

---

## 1. Startup Sequence Validation ✅

### Required Tests
- [ ] **Smoke Tests Pass** (`< 30 seconds`)
  ```bash
  python -m pytest tests/mission_critical/test_startup_wiring_smoke.py -v
  ```
  
- [ ] **Phase Ordering Verified** (7-phase sequence)
  ```bash
  python -m pytest tests/mission_critical/test_deterministic_startup_validation.py::TestDeterministicStartupSequence -v
  ```
  
- [ ] **WebSocket Wiring Confirmed**
  ```bash
  python -m pytest tests/mission_critical/test_deterministic_startup_validation.py::TestWebSocketIntegration -v
  ```

### Startup Phases (Must Execute in Order)
1. **INIT** - Foundation setup and environment validation
2. **DEPENDENCIES** - Core service managers and keys
3. **DATABASE** - Database connections and schema
4. **CACHE** - Redis and caching systems
5. **SERVICES** - Chat Pipeline and critical services
6. **WEBSOCKET** - WebSocket integration and real-time communication
7. **FINALIZE** - Final validation and optional services

### Verification Points
- [ ] `app.state.startup_complete` is `False` during startup
- [ ] `app.state.startup_in_progress` is `True` during startup
- [ ] `app.state.startup_phase` tracks current phase
- [ ] `app.state.startup_complete` is `True` only after ALL phases complete
- [ ] Health endpoints return 503 until startup completes

---

## 2. WebSocket Agent Events (90% of Business Value) ✅

### Mission Critical Events
All of these events MUST be sent during agent execution:

- [ ] **agent_started** - Confirms agent began processing
- [ ] **agent_thinking** - Shows real-time reasoning
- [ ] **tool_executing** - Tool usage transparency
- [ ] **tool_completed** - Tool results delivery
- [ ] **agent_completed** - Final response ready

### Test Command
```bash
python -m pytest tests/mission_critical/test_final_validation.py -v
python -m pytest tests/mission_critical/test_websocket_agent_events_suite.py -v
```

### Critical Integration Points
- [ ] `AgentRegistry.set_websocket_manager()` enhances tool dispatcher
- [ ] `ExecutionEngine` has WebSocketNotifier initialized
- [ ] `EnhancedToolExecutionEngine` wraps tool execution
- [ ] WebSocket bridge is never set to None

---

## 3. Health Endpoint Verification ✅

### Health Check Requirements
- [ ] `/health` endpoint checks `app.state.startup_complete`
- [ ] Returns 503 if startup incomplete
- [ ] Returns 503 if startup failed
- [ ] Returns 200 only when fully operational
- [ ] Includes startup phase in response during startup

### Test Commands
```bash
# Manual health check
curl http://localhost:8000/health

# During startup (should return 503)
curl -i http://localhost:8000/health
# Expected: HTTP/1.1 503 Service Unavailable
# Body: {"status": "unhealthy", "message": "Startup in progress", "startup_in_progress": true}

# After startup (should return 200)
curl -i http://localhost:8000/health
# Expected: HTTP/1.1 200 OK
# Body: {"status": "healthy", ...}
```

---

## 4. Integration Test Suite ✅

### Required Test Suites
- [ ] **Unit Tests** (Fast, isolated)
  ```bash
  python tests/unified_test_runner.py --category unit
  ```

- [ ] **Integration Tests** (With mocked services)
  ```bash
  python tests/unified_test_runner.py --category integration
  ```

- [ ] **E2E Tests** (With real services)
  ```bash
  python tests/unified_test_runner.py --category e2e --real-services
  ```

- [ ] **Mission Critical Tests**
  ```bash
  python -m pytest tests/mission_critical/ -v
  ```

### Docker Service Health
- [ ] PostgreSQL running on port 5434 (test) or 5432 (dev)
- [ ] Redis running on port 6381 (test) or 6379 (dev)
- [ ] Backend service healthy on port 8000
- [ ] Auth service healthy on port 8081

---

## 5. Performance Benchmarks ✅

### Startup Performance
- [ ] Complete startup in < 30 seconds
- [ ] Each phase completes in < 10 seconds
- [ ] No phase timeouts or hangs

### WebSocket Performance
- [ ] Event delivery < 100ms latency
- [ ] Can handle 100+ events/second
- [ ] No event loss under load

### Health Check Performance
- [ ] Response time < 50ms when healthy
- [ ] Response time < 100ms during startup

---

## 6. Error Scenarios ✅

### Startup Failure Handling
- [ ] Database connection failure stops startup
- [ ] Redis connection failure stops startup
- [ ] Missing required environment variables stop startup
- [ ] Health endpoint reports failure correctly

### WebSocket Failure Handling
- [ ] Graceful degradation if WebSocket unavailable
- [ ] Error events sent on tool failures
- [ ] Connection recovery after disconnect

---

## 7. Configuration Validation ✅

### Environment Variables
- [ ] All required vars set for target environment
- [ ] No hardcoded secrets in code
- [ ] JWT secrets properly configured
- [ ] Database URLs correct for environment

### Service Dependencies
- [ ] Auth service reachable
- [ ] Database migrations complete
- [ ] Redis cache initialized
- [ ] LLM service configured

---

## 8. Deployment Steps ✅

### Pre-Deployment
1. [ ] Run all test suites locally
2. [ ] Verify Docker images build successfully
3. [ ] Check CI/CD pipeline green
4. [ ] Review recent commits for breaking changes

### Deployment
1. [ ] Deploy to staging first
2. [ ] Run health checks on staging
3. [ ] Test WebSocket events on staging
4. [ ] Monitor logs for errors
5. [ ] Run smoke tests on staging

### Post-Deployment
1. [ ] Monitor health endpoints
2. [ ] Check WebSocket event flow
3. [ ] Verify chat functionality
4. [ ] Monitor error rates
5. [ ] Check performance metrics

---

## 9. Rollback Plan ✅

### Triggers for Rollback
- [ ] Health checks failing for > 5 minutes
- [ ] WebSocket events not flowing
- [ ] Chat functionality broken
- [ ] Error rate > 5%
- [ ] Startup failures

### Rollback Steps
1. Revert to previous deployment
2. Verify health restored
3. Investigate root cause
4. Fix issues in development
5. Re-run full test suite

---

## 10. Sign-Off ✅

### Required Approvals
- [ ] Engineering Lead approval
- [ ] QA verification complete
- [ ] Product Owner sign-off
- [ ] DevOps ready for deployment

### Final Checks
- [ ] All checklist items completed
- [ ] No known critical issues
- [ ] Monitoring dashboards ready
- [ ] On-call engineer notified
- [ ] Rollback plan confirmed

---

## Emergency Contacts

- **Engineering Lead:** [Contact Info]
- **DevOps On-Call:** [Contact Info]
- **Product Owner:** [Contact Info]
- **Security Team:** [Contact Info]

## References

- [Startup Architecture](netra_backend/app/startup_module_deterministic.py)
- [WebSocket Integration](SPEC/learnings/websocket_agent_integration_critical.xml)
- [Health Endpoints](netra_backend/app/routes/health.py)
- [CI/CD Workflows](.github/workflows/)
- [Test Documentation](tests/README.md)

---

**⚠️ REMEMBER:** Chat functionality delivers 90% of business value. If chat is broken, deployment MUST be blocked.