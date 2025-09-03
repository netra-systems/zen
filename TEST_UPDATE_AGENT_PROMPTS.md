# LIFE OR DEATH: Test Update Agent Team Prompts
**Mission Critical Date:** 2025-09-02  
**Parallel Execution:** 5 Teams Working Simultaneously

---

## 🔴 TEAM ALPHA: WebSocket Warriors
### ULTRA CRITICAL MISSION: Fix 25 WebSocket & Chat Infrastructure Tests

**LIFE OR DEATH CRITICAL ACTION:**
You are TEAM ALPHA. The platform's entire chat value delivery depends on your success. Without functioning WebSocket tests, users receive ZERO value.

### YOUR 25 CRITICAL TESTS TO UPDATE:
```
1. test_websocket_agent_events_suite.py
2. test_websocket_bridge_critical_flows.py
3. test_websocket_comprehensive_validation.py
4. test_websocket_chat_bulletproof.py
5. test_websocket_event_reliability_comprehensive.py
6. test_websocket_multi_agent_integration_20250902.py
7. test_websocket_reliability_focused.py
8. test_chat_initialization.py
9. test_websocket_bridge_lifecycle_comprehensive.py
10. test_websocket_bridge_edge_cases_20250902.py
11. test_websocket_bridge_thread_resolution.py
12. test_websocket_bridge_isolation.py
13. test_websocket_simple.py
14. test_websocket_direct.py
15. test_websocket_e2e_proof.py
16. test_websocket_events_refresh_validation.py
17. test_websocket_json_agent_events.py
18. test_websocket_subagent_events.py
19. test_enhanced_tool_execution_websocket_events.py
20. test_missing_websocket_events.py
21. test_typing_indicator_robustness_suite.py
22. test_websocket_load_minimal.py
23. test_websocket_context_refactor.py
24. test_websocket_initialization_order.py
25. test_websocket_startup_dependencies.py
```

### CRITICAL SUB-TASKS:

#### 1. IMMEDIATE INFRASTRUCTURE FIXES
- **Fix fixture scope crisis** in `tests/mission_critical/conftest.py`
- **Create missing TestContext** module at `test_framework/test_context.py`
- **Fix syntax errors** in test_websocket_simple.py line 41
- **Update all imports** to current SSOT implementations

#### 2. WEBSOCKET EVENT VALIDATION
For EACH test file:
- Verify ALL 5 required events are tested:
  * `agent_started` - With user context and timestamp
  * `agent_thinking` - With reasoning details
  * `tool_executing` - With tool name and parameters
  * `tool_completed` - With results and duration
  * `agent_completed` - With final status
- Add event sequence validation
- Test event ordering and timing
- Verify no events are dropped

#### 3. COMPREHENSIVE TEST ENHANCEMENT
For EACH test:
- Add minimum 15 test cases covering:
  * Happy path scenarios (5 tests)
  * Edge cases (5 tests)
  * Error conditions (5 tests)
- Test with 10+ concurrent connections
- Validate message latency < 100ms
- Test reconnection within 3 seconds
- Add chaos testing (random disconnects)

### SUB-AGENTS TO SPAWN:
1. **WebSocket Protocol Specialist** - Deep dive into event structure
2. **Event Flow Tracer** - Map event paths through system
3. **Performance Validator** - Benchmark latency and throughput
4. **Chaos Engineer** - Test failure scenarios
5. **Integration Tester** - Validate end-to-end flows

### VALIDATION REQUIREMENTS:
✅ All 25 tests passing with REAL WebSocket connections  
✅ Each test validates actual event content AND sequence  
✅ Support 25+ concurrent WebSocket sessions  
✅ < 50ms message latency P99  
✅ Zero message drops under normal load  
✅ Automatic reconnection working  

### CRITICAL NOTES:
- **NEVER use mocks** - Real WebSocket connections ONLY
- **Test the actual bridge** not abstractions
- **Verify user isolation** between sessions
- **Document all event flows** in test comments

---

## 🟡 TEAM BRAVO: Golden Guardians
### CRITICAL MISSION: Enforce 20 Agent Golden Pattern Compliance Tests

**LIFE OR DEATH CRITICAL ACTION:**
You are TEAM BRAVO. Agent reliability determines whether users get consistent, valuable AI responses. Your tests ensure every agent follows the golden pattern.

### YOUR 20 CRITICAL TESTS TO UPDATE:
```
26. test_supervisor_golden_compliance_quick.py
27. test_data_sub_agent_golden_ssot.py
28. test_actions_agent_golden_compliance.py
29. test_reporting_agent_golden.py
30. test_optimizations_agent_golden.py
31. test_summary_extractor_golden.py
32. test_tool_discovery_golden.py
33. test_goals_triage_golden.py
34. test_actions_to_meet_goals_golden.py
35. test_agent_resilience_patterns.py
36. test_baseagent_edge_cases_comprehensive.py
37. test_baseagent_inheritance_violations.py
38. test_agent_type_safety_comprehensive.py
39. test_agent_communication_undefined_attributes.py
40. test_agent_death_fix_complete.py
41. test_agent_manager_lifecycle_events.py
42. test_inheritance_architecture_violations.py
43. test_datahelper_golden_alignment.py
44. test_datahelper_websocket_integration.py
45. test_circuit_breaker_comprehensive.py
```

### CRITICAL SUB-TASKS:

#### 1. BASEAGENT COMPLIANCE VERIFICATION
For EACH agent test:
- Verify proper BaseAgent inheritance
- Check `_execute_core()` implementation
- Validate WebSocket event emission
- Test error handling patterns
- Verify resilience mechanisms

#### 2. GOLDEN PATTERN ENFORCEMENT
- Test Method Resolution Order (MRO)
- Validate no method shadowing
- Check SSOT compliance (one implementation per concept)
- Verify proper async/await patterns
- Test context isolation

#### 3. COMPREHENSIVE AGENT TESTING
For EACH test file:
- Add 20+ test cases covering:
  * Initialization scenarios (5 tests)
  * Execution patterns (5 tests)
  * Error recovery (5 tests)
  * Resource cleanup (5 tests)
- Test agent death detection
- Validate lifecycle events
- Test compensation calculation
- Verify tool execution

### SUB-AGENTS TO SPAWN:
1. **Inheritance Analyzer** - Verify MRO and inheritance chains
2. **Pattern Validator** - Check golden pattern compliance
3. **Resilience Tester** - Test error recovery
4. **Lifecycle Manager** - Validate agent lifecycle
5. **Integration Specialist** - Test agent coordination

### VALIDATION REQUIREMENTS:
✅ All 20 tests passing with real agent instances  
✅ 100% BaseAgent compliance verified  
✅ All WebSocket events properly emitted  
✅ Error recovery working in < 5 seconds  
✅ No memory leaks detected  
✅ Proper resource cleanup verified  

### CRITICAL NOTES:
- **Follow docs/GOLDEN_AGENT_INDEX.md** religiously
- **Test actual agent execution** not mocks
- **Verify WebSocket integration** for every agent
- **Document compliance violations** clearly

---

## 🟢 TEAM CHARLIE: SSOT Sentinels
### CRITICAL MISSION: Eliminate 20 SSOT Violations & Ensure Data Isolation

**LIFE OR DEATH CRITICAL ACTION:**
You are TEAM CHARLIE. Data integrity equals trustworthy AI responses. Your tests prevent duplicate implementations and ensure complete user isolation.

### YOUR 20 CRITICAL TESTS TO UPDATE:
```
46. test_no_ssot_violations.py
47. test_ssot_compliance_suite.py
48. test_ssot_framework_validation.py
49. test_ssot_integration.py
50. test_ssot_orchestration_consolidation.py
51. test_ssot_regression_prevention.py
52. test_ssot_backward_compatibility.py
53. test_data_layer_isolation.py
54. test_data_isolation_simple.py
55. test_concurrent_user_isolation.py
56. test_database_session_isolation.py
57. test_agent_registry_isolation.py
58. test_isolated_environment_compliance.py
59. test_json_ssot_consolidation.py
60. test_reporting_agent_ssot_violations.py
61. test_triage_agent_ssot_compliance.py
62. test_data_sub_agent_ssot_compliance.py
63. test_reliability_consolidation_ssot.py
64. test_error_handling_ssot_consistency.py
65. test_mock_policy_violations.py
```

### CRITICAL SUB-TASKS:

#### 1. SSOT VIOLATION DETECTION
For EACH test:
- Scan for duplicate implementations
- Verify single source per concept
- Check for hidden duplicates in:
  * Configuration management
  * Error handling
  * WebSocket management
  * Database connections
  * Environment access

#### 2. USER ISOLATION VERIFICATION
- Test 10+ concurrent users
- Verify no data leakage between users
- Check session isolation
- Validate context separation
- Test resource isolation

#### 3. COMPREHENSIVE ISOLATION TESTING
For EACH test file:
- Add 15+ isolation tests:
  * User context isolation (5 tests)
  * Database session isolation (5 tests)
  * WebSocket channel isolation (5 tests)
- Test with malicious inputs
- Verify security boundaries
- Test race conditions

### SUB-AGENTS TO SPAWN:
1. **SSOT Scanner** - Find all duplicates
2. **Isolation Validator** - Test user separation
3. **Security Auditor** - Check boundaries
4. **Concurrency Tester** - Test race conditions
5. **Data Integrity Specialist** - Verify data consistency

### VALIDATION REQUIREMENTS:
✅ Zero SSOT violations detected  
✅ Complete user isolation verified  
✅ No data leakage under load  
✅ All mocks eliminated  
✅ Single implementation per concept  
✅ Thread-safe operations verified  

### CRITICAL NOTES:
- **Reference SPEC/type_safety.xml** for rules
- **Check SPEC/mega_class_exceptions.xml** for allowed exceptions
- **Verify IsolatedEnvironment usage** everywhere
- **Document every SSOT violation found**

---

## 🔵 TEAM DELTA: Docker Defenders
### CRITICAL MISSION: Guarantee 20 Infrastructure & Docker Tests

**LIFE OR DEATH CRITICAL ACTION:**
You are TEAM DELTA. Platform stability equals 99.99% uptime. Your tests ensure infrastructure never fails under production load.

### YOUR 20 CRITICAL TESTS TO UPDATE:
```
66. test_docker_stability_suite.py
67. test_docker_stability_comprehensive.py
68. test_docker_lifecycle_management.py
69. test_docker_lifecycle_critical.py
70. test_docker_full_integration.py
71. test_docker_edge_cases.py
72. test_docker_performance.py
73. test_docker_rate_limiter_integration.py
74. test_docker_ssot_compliance.py
75. test_docker_unified_fixes_validation.py
76. test_docker_compliance_audit.py
77. test_docker_credential_configuration.py
78. test_orchestration_system_suite.py
79. test_orchestration_integration.py
80. test_orchestration_edge_cases.py
81. test_orchestration_performance.py
82. test_deterministic_startup_validation.py
83. test_startup_validation.py
84. test_service_factory_websocket_bug.py
85. test_fixture_cleanup_verification.py
```

### CRITICAL SUB-TASKS:

#### 1. DOCKER ORCHESTRATION VALIDATION
For EACH test:
- Verify UnifiedDockerManager usage
- Test automatic conflict resolution
- Validate health checks
- Test dynamic port allocation
- Verify Alpine container support

#### 2. STABILITY UNDER LOAD
- Test with 100+ containers
- Simulate Docker daemon crashes
- Test rate limit handling
- Verify automatic recovery
- Test rolling updates

#### 3. COMPREHENSIVE INFRASTRUCTURE TESTING
For EACH test file:
- Add 20+ infrastructure tests:
  * Service startup (5 tests)
  * Health monitoring (5 tests)
  * Failure recovery (5 tests)
  * Performance benchmarks (5 tests)
- Test cross-platform compatibility
- Verify resource limits
- Test cleanup procedures

### SUB-AGENTS TO SPAWN:
1. **Docker Orchestrator** - Manage containers
2. **Health Monitor** - Track service health
3. **Performance Profiler** - Benchmark operations
4. **Chaos Injector** - Test failures
5. **Resource Manager** - Monitor usage

### VALIDATION REQUIREMENTS:
✅ All services start in < 30 seconds  
✅ Automatic recovery from crashes  
✅ Zero port conflicts  
✅ Health checks working  
✅ < 500MB memory per container  
✅ 99.99% uptime over 24 hours  

### CRITICAL NOTES:
- **Use docs/docker_orchestration.md** as reference
- **Test with Alpine containers** for speed
- **Never use --force flags** in Docker
- **Document all infrastructure issues**

---

## ⚪ TEAM ECHO: Experience Engineers
### CRITICAL MISSION: Validate 15 Authentication & User Journey Tests

**LIFE OR DEATH CRITICAL ACTION:**
You are TEAM ECHO. User access equals revenue. Your tests ensure complete user journeys from signup to receiving AI value.

### YOUR 15 CRITICAL TESTS TO UPDATE:
```
86. test_staging_auth_cross_service_validation.py
87. test_auth_state_consistency.py
88. test_jwt_secret_hard_requirements.py
89. test_jwt_secret_synchronization_simple.py
90. test_jwt_sync_ascii.py
91. test_pre_post_deployment_jwt_verification.py
92. test_backend_login_endpoint_fix.py
93. test_staging_endpoints_direct.py
94. test_staging_websocket_agent_events.py
95. test_token_refresh_active_chat.py
96. test_presence_detection_critical.py
97. test_chat_responsiveness_under_load.py
98. test_memory_leak_prevention_comprehensive.py
99. test_tool_progress_bulletproof.py
100. test_comprehensive_compliance_validation.py
```

### CRITICAL SUB-TASKS:

#### 1. AUTHENTICATION FLOW VALIDATION
For EACH auth test:
- Test complete signup → login → chat flow
- Verify JWT token generation
- Test token refresh during active chat
- Validate cross-service authentication
- Test OAuth and social logins

#### 2. USER JOURNEY TESTING
- Test 10+ user personas
- Validate first-time user experience
- Test power user workflows
- Verify billing integration
- Test compensation calculation

#### 3. COMPREHENSIVE EXPERIENCE TESTING
For EACH test file:
- Add 25+ experience tests:
  * Authentication flows (10 tests)
  * User journeys (10 tests)
  * Performance under load (5 tests)
- Test with 50+ concurrent users
- Verify < 30 second journeys
- Test memory leak prevention

### SUB-AGENTS TO SPAWN:
1. **Auth Specialist** - JWT and authentication
2. **Journey Mapper** - User flow validation
3. **Load Tester** - Performance validation
4. **Memory Profiler** - Leak detection
5. **UX Validator** - Experience quality

### VALIDATION REQUIREMENTS:
✅ Complete journeys < 30 seconds  
✅ JWT tokens properly synchronized  
✅ 50+ concurrent users supported  
✅ No memory leaks detected  
✅ Token refresh working seamlessly  
✅ All user personas validated  

### CRITICAL NOTES:
- **Test with real auth service** not mocks
- **Validate actual user journeys** end-to-end
- **Check staging environment** compatibility
- **Document all UX issues** found

---

## 🚨 COORDINATION PROTOCOL

### CRITICAL EXECUTION RULES:
1. **ALL TEAMS START SIMULTANEOUSLY** - Maximum parallelization
2. **NEVER trust existing code** - Verify everything yourself
3. **COORDINATE via reports** - Share discoveries every 30 minutes
4. **USE REAL SERVICES ONLY** - Mocks are FORBIDDEN
5. **DOCUMENT everything** - Update SPEC files continuously

### INTER-TEAM DEPENDENCIES:
- **ALPHA → ALL**: WebSocket infrastructure must work for other tests
- **BRAVO → CHARLIE**: Agent patterns affect SSOT compliance
- **DELTA → ALL**: Docker must be stable for all testing
- **CHARLIE → ECHO**: Data isolation affects user journeys
- **ECHO → ALPHA**: Auth affects WebSocket connections

### PROGRESS SYNCHRONIZATION:
```
Every 30 minutes:
1. Each team creates progress report
2. Share blocking issues immediately
3. Coordinate on shared dependencies
4. Update master tracking document
5. Adjust priorities if needed
```

### FAILURE RECOVERY:
If ANY team encounters blockers:
1. **Immediately notify all teams**
2. **Reassign resources if critical**
3. **Document workaround strategies**
4. **Update contingency plans**
5. **Continue with parallel work**

---

## 📊 SUCCESS METRICS

### PER-TEAM REQUIREMENTS:
- **ALPHA**: 25/25 WebSocket tests passing
- **BRAVO**: 20/20 Agent tests passing
- **CHARLIE**: 20/20 SSOT tests passing
- **DELTA**: 20/20 Docker tests passing
- **ECHO**: 15/15 Journey tests passing

### OVERALL REQUIREMENTS:
✅ 100/100 critical tests passing  
✅ < 100ms latency P99  
✅ 50+ concurrent users  
✅ Zero SSOT violations  
✅ 99.99% reliability  
✅ Complete journeys working  

### QUALITY STANDARDS:
- Each test: 15+ test cases minimum
- Each test: Real services only
- Each test: Performance benchmarks
- Each test: Error scenarios covered
- Each test: Documentation complete

---

## 🎯 FINAL REMINDERS

### THE MISSION IS LIFE OR DEATH:
- **Our spacecraft depends on this platform**
- **User value delivery is NON-NEGOTIABLE**
- **Chat is King - it delivers 90% of value**
- **Tests protect revenue generation**
- **Quality over speed, but both required**

### SPAWN YOUR SUB-AGENTS NOW:
Each team should immediately spawn 5-7 specialized sub-agents to divide the work. Use the Task tool with specific, focused prompts for maximum efficiency.

### TIME IS CRITICAL:
- **Hour 1**: Fix blocking issues
- **Hours 2-6**: Parallel test updates
- **Hour 7**: Integration testing
- **Hour 8**: Documentation

---

**TEAMS ALPHA, BRAVO, CHARLIE, DELTA, ECHO:**
**YOUR MISSION BEGINS NOW.**
**FAILURE IS NOT AN OPTION.**
**THE PLATFORM'S SURVIVAL DEPENDS ON YOUR SUCCESS.**

**EXECUTE WITH PRECISION. COORDINATE WITH PURPOSE. SUCCEED AT ALL COSTS.**