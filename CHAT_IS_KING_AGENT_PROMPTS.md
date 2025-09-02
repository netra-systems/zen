# LIFE OR DEATH CRITICAL: Chat is King WebSocket Agent Prompts

## 🔴 PROMPT 1: Critical Infrastructure Fixes

**LIFE OR DEATH CRITICAL: ACTION:**
BATCH 1: Critical Infrastructure Fixes from CHAT_IS_KING_REMEDIATION_PLAN.md

FOR EACH sub task in item:
1) Don't believe the report fully - check latest system and think about it yourself
2) Use multi-agent (3-7 best most relevant agents) to complete actual work
3) Failing tests and test suite must be complete, comprehensive, and difficult

### CRITICAL MISSION:
Fix the fixture scope architecture crisis that's blocking ALL WebSocket tests. The session-scoped `real_services_manager` is causing 175+ test failures.

### SUB-TASKS TO COMPLETE:
1. **Fixture Scope Architecture Emergency Fix**
   - Investigate `tests/mission_critical/conftest.py` line 48-56
   - Verify the actual error: session scope accessing function scope
   - Create compatibility wrapper OR refactor to function scope
   - Test with at least 10 different test files to ensure fix works
   - DO NOT trust that changing scope is simple - check all dependencies

2. **Missing Test Framework Module Creation**
   - Search entire codebase for `TestContext` references
   - Determine what TestContext SHOULD do based on usage patterns
   - Create `test_framework/test_context.py` with WebSocket utilities
   - Include context isolation, user simulation, event tracking
   - Write 5+ unit tests for TestContext itself

3. **Syntax Error Elimination**
   - Fix `test_websocket_simple.py` line 41 continuation character
   - Scan ALL test files for similar syntax issues
   - Create pre-commit hook to prevent future syntax errors
   - Validate with Python AST parser

### AGENTS TO SPAWN:
- **Test Infrastructure Agent**: Fix pytest fixtures and scopes
- **Module Recovery Agent**: Reconstruct missing test_framework
- **Syntax Validation Agent**: Fix and prevent syntax errors
- **Integration Testing Agent**: Validate fixes across suite
- **Dependency Analysis Agent**: Map all fixture dependencies

### VALIDATION REQUIREMENTS:
- Run 50+ tests successfully with new fixture architecture
- All imports must resolve without errors
- Zero syntax errors in entire test suite
- Create regression test to prevent scope mismatch

---

## 🟡 PROMPT 2: WebSocket Event Suite Restoration

**LIFE OR DEATH CRITICAL: ACTION:**
BATCH 2: WebSocket Event Suite Restoration from CHAT_IS_KING_REMEDIATION_PLAN.md

FOR EACH sub task in item:
1) Don't believe the report fully - check latest system and think about it yourself
2) Use multi-agent (3-7 best most relevant agents) to complete actual work
3) Failing tests and test suite must be complete, comprehensive, and difficult

### CRITICAL MISSION:
Restore the 21 core WebSocket event tests that validate our "Chat is King" business value delivery. These tests MUST verify all 5 required events.

### SUB-TASKS TO COMPLETE:
1. **Core WebSocket Event Test Restoration**
   - Analyze `test_websocket_agent_events_suite.py` actual implementation
   - Don't trust the "21 tests" count - verify each test method
   - Fix ALL unit tests (TestUnitWebSocketComponents class)
   - Fix ALL integration tests (TestIntegrationWebSocketFlow class)
   - Fix ALL E2E tests (TestE2EWebSocketChatFlow class)
   - Add 10+ edge case tests not currently covered

2. **Critical E2E WebSocket Function Recovery**
   - Find where `enhance_tool_dispatcher_with_notifications` was moved
   - Check git history for function removal/renaming
   - Update imports to current SSOT implementation
   - If function deleted, recreate with proper WebSocket integration
   - Create fallback mechanism if enhancement fails

3. **Five Event Validation Framework**
   - Build comprehensive validator for required events:
     * agent_started (with timestamp and context)
     * agent_thinking (with reasoning details)
     * tool_executing (with tool name and parameters)
     * tool_completed (with results and duration)
     * agent_completed (with final status and summary)
   - Create event sequence validator
   - Add timing analysis between events
   - Build event replay mechanism for debugging

### AGENTS TO SPAWN:
- **WebSocket Protocol Agent**: Deep dive into event structure
- **Event Flow Agent**: Trace event paths through system
- **SSOT Compliance Agent**: Ensure single source of truth
- **Test Coverage Agent**: Identify missing test scenarios
- **Performance Testing Agent**: Validate event latency
- **Error Recovery Agent**: Test failure scenarios
- **Integration Validation Agent**: End-to-end verification

### VALIDATION REQUIREMENTS:
- All 21+ tests must pass with real WebSocket connections
- Each test must validate actual event content, not just presence
- Events must flow in correct sequence with proper timing
- Stress test with 100+ events per second
- Zero event drops under normal load

---

## 🟢 PROMPT 3: Chat System Integration Tests

**LIFE OR DEATH CRITICAL: ACTION:**
BATCH 3: Chat System Integration Tests from CHAT_IS_KING_REMEDIATION_PLAN.md

FOR EACH sub task in item:
1) Don't believe the report fully - check latest system and think about it yourself
2) Use multi-agent (3-7 best most relevant agents) to complete actual work
3) Failing tests and test suite must be complete, comprehensive, and difficult

### CRITICAL MISSION:
Fix 154+ WebSocket bridge tests that ensure chat messages flow correctly. The bridge is the heart of user value delivery.

### SUB-TASKS TO COMPLETE:
1. **Chat Initialization Test Recovery**
   - Fix TestContext import in `test_chat_initialization.py`
   - Verify chat session creation with unique IDs
   - Test user context isolation (10+ concurrent users)
   - Validate JWT token flow through chat init
   - Add byzantine fault tolerance tests

2. **WebSocket Bridge Test Marathon**
   - Fix ALL 154 tests across 10 bridge test files
   - Don't assume fixture fix solves everything - verify each
   - Test bridge singleton pattern under concurrency
   - Validate thread resolution with 50+ threads
   - Test message ordering guarantees
   - Add chaos engineering tests (random disconnects)

3. **Simple WebSocket Foundation Tests**
   - Fix syntax in `test_websocket_simple.py`
   - Create baseline connection tests
   - Test message routing with 20+ route patterns
   - Validate error handling for 15+ error types
   - Build reconnection logic tests

### AGENTS TO SPAWN:
- **Bridge Architecture Agent**: Understand bridge pattern
- **Concurrency Testing Agent**: Multi-user scenarios
- **Message Flow Agent**: Trace message paths
- **Session Management Agent**: User context isolation
- **Fault Injection Agent**: Chaos testing
- **Performance Baseline Agent**: Establish metrics

### VALIDATION REQUIREMENTS:
- 154+ bridge tests passing
- Support 25+ concurrent chat sessions
- Zero message drops under normal operation
- < 50ms message latency P99
- Automatic reconnection within 3 seconds

---

## 🔵 PROMPT 4: User Journey Validation

**LIFE OR DEATH CRITICAL: ACTION:**
BATCH 4: User Journey Validation from CHAT_IS_KING_REMEDIATION_PLAN.md

FOR EACH sub task in item:
1) Don't believe the report fully - check latest system and think about it yourself
2) Use multi-agent (3-7 best most relevant agents) to complete actual work
3) Failing tests and test suite must be complete, comprehensive, and difficult

### CRITICAL MISSION:
Validate complete user journeys from signup to receiving AI-powered insights through chat. This proves business value delivery.

### SUB-TASKS TO COMPLETE:
1. **Complete User Journey Test Suite**
   - Fix and enhance `test_complete_user_journey.py`
   - Test signup → login → chat → agent execution → results
   - Include OAuth, email, and social login paths
   - Test 10+ different user personas
   - Add journey timing benchmarks

2. **Message Flow Comprehensive Testing**
   - Validate message flow through entire stack
   - Test message transformations at each layer
   - Verify message persistence and recovery
   - Test 20+ message types and formats
   - Add message corruption detection

3. **Agent Pipeline End-to-End**
   - Test complete agent execution pipeline
   - Verify supervisor → agent → tool → result flow
   - Test agent compensation calculation
   - Validate billing event generation
   - Test 15+ agent types in pipeline

### AGENTS TO SPAWN:
- **User Journey Agent**: Map all user paths
- **Message Protocol Agent**: Validate message specs
- **Pipeline Orchestration Agent**: Test agent coordination
- **Business Logic Agent**: Verify value delivery
- **Metrics Collection Agent**: Gather journey metrics
- **UX Validation Agent**: Test user experience

### VALIDATION REQUIREMENTS:
- Complete journeys < 30 seconds end-to-end
- All message types handled correctly
- Agent pipeline 99.9% reliability
- Accurate billing/compensation
- Positive user experience metrics

---

## ⚪ PROMPT 5: Performance & Reliability

**LIFE OR DEATH CRITICAL: ACTION:**
BATCH 5: Performance & Reliability from CHAT_IS_KING_REMEDIATION_PLAN.md

FOR EACH sub task in item:
1) Don't believe the report fully - check latest system and think about it yourself
2) Use multi-agent (3-7 best most relevant agents) to complete actual work
3) Failing tests and test suite must be complete, comprehensive, and difficult

### CRITICAL MISSION:
Ensure system can handle production load with 10+ concurrent users without degradation. This is critical for business scalability.

### SUB-TASKS TO COMPLETE:
1. **Stress Testing Infrastructure**
   - Fix rapid refresh stress tests
   - Test with 50+ concurrent WebSocket connections
   - Simulate 1000+ messages per second
   - Test connection pool exhaustion
   - Add thundering herd tests

2. **Memory & Resource Management**
   - Fix memory leak detection tests
   - Monitor memory growth over 1 hour
   - Test circuit breaker activation
   - Validate retry logic with exponential backoff
   - Test resource cleanup on crash

3. **Docker Service Orchestration**
   - Ensure all Docker services start reliably
   - Test service discovery and registration
   - Validate health checks and auto-recovery
   - Test rolling updates without downtime
   - Add container resource limit tests

### AGENTS TO SPAWN:
- **Load Testing Agent**: Generate realistic load
- **Memory Profiling Agent**: Detect leaks
- **Reliability Engineering Agent**: Fault tolerance
- **Docker Orchestration Agent**: Service management
- **Monitoring Agent**: Metrics and alerting
- **Chaos Engineering Agent**: Failure injection
- **Performance Tuning Agent**: Optimization

### VALIDATION REQUIREMENTS:
- Handle 100+ concurrent users
- < 100MB memory growth per hour
- 99.99% uptime over 24 hours
- < 5 second recovery from failures
- Zero data loss during crashes

---

## EXECUTION COORDINATION

### CRITICAL RULES FOR ALL AGENTS:
1. **NEVER trust existing code** - Verify everything yourself
2. **ALWAYS write comprehensive tests** - Minimum 10 tests per feature
3. **COORDINATE with other agents** - Share discoveries via reports
4. **DOCUMENT all changes** - Update SPEC files and learnings
5. **VALIDATE with real services** - NO MOCKS ALLOWED

### PARALLEL EXECUTION STRATEGY:
- **Hour 1-2**: PROMPT 1 (Infrastructure) - MUST complete first
- **Hour 3-5**: PROMPTS 2 & 3 in parallel (WebSocket + Chat)
- **Hour 6-7**: PROMPTS 4 & 5 in parallel (Journey + Performance)
- **Hour 8**: Final integration and validation

### SUCCESS CRITERIA:
✅ ALL 5 WebSocket events working
✅ 200+ tests passing
✅ 10+ concurrent users supported
✅ < 100ms message latency
✅ Zero message drops
✅ Complete user journeys functional
✅ System stable under load

### FAILURE CONTINGENCY:
If any batch fails:
1. Stop all parallel work
2. Focus all agents on failed batch
3. Create detailed failure analysis
4. Implement workaround if blocker found
5. Document in SPEC/learnings

---

**REMEMBER: This is LIFE OR DEATH for the platform. Chat is King. User value delivery depends on these tests working. COMPLETE THE MISSION.**