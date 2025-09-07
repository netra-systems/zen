# E2E Test Fix Implementation Plan
Generated: 2025-09-06

## 🎯 Mission
Get all E2E tests passing with full Docker integration and real service connections.

## 📊 Current State Assessment

### ✅ What's Working
- Docker environment configured and running (6 services healthy)
- Native ARM64 architecture on Mac confirmed
- Import errors fixed in test files
- Test collection working without errors

### ❌ What Needs Fixing
1. Missing method implementations in test infrastructure
2. Service connectivity issues (tests falling back to offline mode)
3. Long-running WebSocket tests need completion
4. OAuth configuration warnings (non-critical but should fix)

## 📋 Implementation Plan

### Phase 1: Fix Infrastructure Methods (Priority: CRITICAL)
**Timeline: 1-2 hours**

#### Task 1.1: Implement TenantAgentManager.create_tenant_agents
- **File**: `/tests/e2e/resource_isolation/suite/tenant_agent_manager.py`
- **Action**: Add missing `create_tenant_agents` method
- **Implementation**:
  ```python
  async def create_tenant_agents(self, count: int = 3):
      # Create specified number of tenant agents
      # Track resource usage per tenant
      # Return list of TenantAgent instances
  ```
- **Multi-Agent Team**:
  - Analyzer: Study existing manager pattern
  - Implementer: Write the method
  - Validator: Test with CPU isolation tests

#### Task 1.2: Fix Service Verification
- **Issue**: "Service verification failed: All connection attempts failed"
- **Root Cause**: Tests trying wrong ports or missing auth
- **Fix**:
  - Update service URLs to use Docker ports (8002, 8083, etc.)
  - Ensure test auth tokens are configured
  - Add retry logic with exponential backoff

### Phase 2: Service Connectivity (Priority: HIGH)
**Timeline: 1 hour**

#### Task 2.1: Configure Test Environment URLs
- **Action**: Set correct Docker service URLs
- **Environment Variables**:
  ```bash
  BACKEND_URL=http://localhost:8002
  AUTH_SERVICE_URL=http://localhost:8083
  FRONTEND_URL=http://localhost:3002
  DATABASE_URL=postgresql://...@localhost:5435/...
  REDIS_URL=redis://localhost:6382
  ```

#### Task 2.2: Add Service Health Checks
- **Implementation**: Pre-test service verification
- **Components**:
  - Backend health endpoint check
  - Auth service availability
  - Database connectivity
  - Redis ping test

### Phase 3: Complete WebSocket Tests (Priority: HIGH)
**Timeline: 30 minutes**

#### Task 3.1: Monitor Running WebSocket Tests
- Check `websocket_test_results.log`
- Identify any stuck tests or timeouts
- Document event delivery metrics

#### Task 3.2: Fix Any WebSocket Issues
- Ensure all 5 required events fire:
  - agent_started
  - agent_thinking  
  - tool_executing
  - tool_completed
  - agent_completed

### Phase 4: Run Full Test Suite (Priority: MEDIUM)
**Timeline: 2-3 hours**

#### Task 4.1: Execute Test Categories
```bash
# Run in order of importance
1. Mission Critical WebSocket Tests
2. Auth Flow Tests  
3. Chat UI Flow Tests
4. Agent Isolation Tests
5. Performance Tests
6. Data Pipeline Tests
```

#### Task 4.2: Document Failures
For each failure:
- Test name and location
- Error message and stack trace
- Root cause analysis
- Fix strategy

### Phase 5: Fix Failing Tests (Priority: HIGH)
**Timeline: 3-4 hours**

#### Task 5.1: Spawn Multi-Agent Teams per Failure
For each failing test:

**Team Structure**:
1. **Root Cause Analyst**
   - Examine error logs
   - Identify missing dependencies
   - Determine fix approach

2. **Implementation Agent**
   - Apply fixes following SSOT
   - Update test fixtures
   - Fix implementation bugs

3. **Validation Agent**
   - Run fixed test
   - Verify no regressions
   - Check related tests

4. **Integration Agent**
   - Ensure system-wide compatibility
   - Update documentation
   - Commit fixes

### Phase 6: Optimization & Coverage (Priority: LOW)
**Timeline: 1 hour**

#### Task 6.1: Performance Optimization
- Parallelize independent tests
- Optimize Docker resource allocation
- Cache test data where appropriate

#### Task 6.2: Coverage Metrics
- Generate test coverage report
- Identify untested code paths
- Document coverage percentages

## 🚀 Execution Strategy

### Immediate Actions (Next 30 mins)
1. Implement `create_tenant_agents` method
2. Fix service URL configuration
3. Check WebSocket test progress

### Short Term (Next 2 hours)
1. Get CPU isolation test passing
2. Complete service connectivity fixes
3. Run auth flow tests

### Medium Term (Next 4 hours)
1. Fix all identified test failures
2. Run complete E2E suite
3. Document results

### Long Term (Next Day)
1. Achieve 100% E2E test pass rate
2. Add missing test coverage
3. Setup CI/CD integration

## 🎪 Multi-Agent Team Deployment

### Team Alpha: Infrastructure
- Focus: TenantAgentManager, service connectivity
- Agents: 2 implementation, 1 validation

### Team Beta: WebSocket
- Focus: Event delivery, real-time messaging
- Agents: 1 monitor, 1 fixer, 1 validator

### Team Gamma: Test Fixes
- Focus: Individual test failures
- Agents: 4-agent teams per failure

## 📈 Success Metrics

### Must Have (P0)
- [ ] All import errors resolved ✅
- [ ] Docker services running ✅
- [ ] TenantAgentManager.create_tenant_agents implemented
- [ ] Service connectivity working
- [ ] 5 core WebSocket events validated

### Should Have (P1)
- [ ] 80%+ E2E tests passing
- [ ] Auth flow tests working
- [ ] Chat UI tests functional

### Nice to Have (P2)
- [ ] 95%+ test pass rate
- [ ] Performance benchmarks met
- [ ] Full test coverage report

## 🛠️ Tools & Commands

### Test Execution
```bash
# Run specific test
python -m pytest tests/e2e/[test_file] -xvs

# Run with Docker
python tests/unified_test_runner.py --category e2e --real-services

# Mission critical tests
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### Docker Management
```bash
# Check services
docker-compose -f docker-compose.alpine-test.yml ps

# View logs
docker-compose -f docker-compose.alpine-test.yml logs -f [service]

# Restart service
docker-compose -f docker-compose.alpine-test.yml restart [service]
```

### Debugging
```bash
# Check connectivity
curl http://localhost:8002/health
curl http://localhost:8083/health

# Database connection
psql -h localhost -p 5435 -U postgres

# Redis connection  
redis-cli -p 6382 ping
```

## 🚨 Risk Mitigation

### Potential Blockers
1. **OAuth Configuration**: May need real credentials
   - Mitigation: Use test/mock OAuth provider
   
2. **Service Dependencies**: External API calls
   - Mitigation: Mock external services in test mode
   
3. **Resource Constraints**: Docker memory/CPU limits
   - Mitigation: Optimize container resources

4. **Flaky Tests**: Timing-dependent failures
   - Mitigation: Add proper waits and retries

## 📝 Documentation Requirements

### Update After Completion
1. E2E_TEST_STATUS_REPORT.md - Final results
2. TEST_CREATION_GUIDE.md - Lessons learned
3. DEFINITION_OF_DONE_CHECKLIST.md - E2E test requirements
4. Individual test docstrings - Implementation notes

## 🎯 Definition of Done

- [ ] All E2E tests can be collected without import errors
- [ ] Docker services verified healthy before each test
- [ ] Service connectivity confirmed with health checks
- [ ] TenantAgentManager fully implemented
- [ ] WebSocket events test passing
- [ ] At least 80% of E2E tests passing
- [ ] All failures documented with fix plans
- [ ] Test execution time < 10 minutes
- [ ] Coverage report generated
- [ ] Documentation updated

## 🚦 Go/No-Go Criteria

**GO Criteria** (Ready for production):
- All P0 items complete
- No critical test failures
- WebSocket events working
- Auth flow functional

**NO-GO Criteria** (Needs more work):
- Any import errors remain
- Docker services unhealthy
- Core WebSocket events failing
- Auth completely broken

---

## Next Step: Start Phase 1
Begin with implementing `TenantAgentManager.create_tenant_agents` method to unblock CPU isolation tests.