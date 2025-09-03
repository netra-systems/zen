# LIFE OR DEATH CRITICAL: SSOT Remediation Multi-Agent Plan
**Date:** 2025-09-02  
**Mission:** Eliminate 847 SSOT violations threatening spacecraft systems  
**Business Impact:** $4.452M annual revenue at risk  
**Deadline:** 7 days for Phase 1 Critical violations  

## 🔴 PROMPT 1: WebSocket Manager SSOT Crisis Resolution

**LIFE OR DEATH CRITICAL: ACTION:**
PHASE 1 CRITICAL: WebSocket Manager Consolidation - 89+ duplicate implementations causing user data leakage

FOR EACH sub task:
1) Verify current system state - don't trust the report blindly
2) Use multi-agent coordination (5-8 specialized agents) 
3) Create comprehensive test suite BEFORE changes
4) Document MRO analysis for inheritance patterns

### CRITICAL MISSION:
Consolidate 89+ WebSocket Manager implementations to single SSOT. Current duplicates are causing concurrent user failures and data leakage between sessions.

### SUB-TASKS TO COMPLETE:

1. **WebSocket Manager Discovery & Analysis**
   - Scan entire codebase for ALL WebSocket manager implementations
   - Document inheritance hierarchy and MRO for each
   - Map usage patterns across 312+ references
   - Identify which implementation is the TRUE canonical SSOT
   - Create dependency graph of all consumers
   - Analyze test mock patterns (67+ mock implementations)

2. **Canonical SSOT Selection & Enhancement**
   - Verify `netra_backend/app/websocket_core/manager.py` as canonical
   - Merge necessary features from duplicate implementations:
     * ModernWebSocketManager capabilities
     * WebSocketScalingManager scaling features
     * WebSocketHeartbeatManager heartbeat logic
     * WebSocketQualityManager quality metrics
   - Ensure factory-based isolation pattern
   - Add comprehensive user context isolation

3. **Systematic Duplicate Elimination**
   - Remove `ModernWebSocketManager` from `modern_websocket_abstraction.py`
   - Remove `WebSocketScalingManager` from `scaling_manager.py`
   - Remove `WebSocketHeartbeatManager` from `heartbeat_manager.py`
   - Remove `WebSocketQualityManager` from `quality_manager.py`
   - Remove `WebSocketDashboardConfigManager` from monitoring
   - Update ALL imports to canonical implementation
   - Preserve git history with detailed commit messages

4. **Test Infrastructure Consolidation**
   - Replace 67+ MockWebSocketManager implementations
   - Create single test fixture in test_framework
   - Update all test imports and patterns
   - Ensure test isolation and repeatability
   - Add stress tests for 50+ concurrent connections

### AGENTS TO SPAWN:
- **SSOT Discovery Agent**: Map all duplicates with grep/ast analysis
- **MRO Analysis Agent**: Document inheritance and method resolution
- **Consolidation Agent**: Merge features into canonical implementation
- **Migration Agent**: Update all 312+ references systematically
- **Test Refactoring Agent**: Consolidate test mocks
- **Validation Agent**: Verify user isolation integrity
- **Performance Agent**: Benchmark before/after metrics
- **Documentation Agent**: Update architecture specs

### VALIDATION REQUIREMENTS:
- Zero duplicate WebSocketManager classes
- All 312+ references using canonical implementation
- 100+ tests passing with new structure
- User isolation verified with 25+ concurrent sessions
- Memory usage reduced by 30%
- WebSocket event flow validated end-to-end

### FAILURE RECOVERY:
- If canonical selection wrong, pivot to most feature-complete
- Create adapter pattern if breaking changes unavoidable
- Maintain backward compatibility wrapper temporarily
- Document all breaking changes in BREAKING_CHANGES.md

---

## 🟡 PROMPT 2: Environment Access Violation Elimination

**LIFE OR DEATH CRITICAL: ACTION:**
PHASE 1 CRITICAL: Replace 371+ direct os.environ calls - $4.452M revenue risk

FOR EACH sub task:
1) Scan for ALL os.environ patterns including getenv, setdefault
2) Coordinate with configuration architecture team
3) Test in all environments (local, test, staging)
4) Verify no configuration drift

### CRITICAL MISSION:
Eliminate ALL 371+ direct os.environ access violations. Each violation represents $12K MRR loss risk from configuration inconsistencies.

### SUB-TASKS TO COMPLETE:

1. **Comprehensive Environment Access Audit**
   - Find ALL os.environ access patterns:
     * os.environ.get()
     * os.environ[]
     * os.getenv()
     * os.environ.setdefault()
     * patch.dict(os.environ) in tests
   - Map to service boundaries
   - Identify bootstrap/startup exceptions
   - Document legitimate test usage

2. **IsolatedEnvironment Implementation**
   - Verify `shared/isolated_environment.py` implementation
   - Add missing environment variables to schema
   - Create service-specific environment configs:
     * BackendEnvironment for netra_backend
     * AuthEnvironment for auth_service
     * FrontendEnvironment for frontend
   - Implement proper defaults and validation
   - Add environment inheritance patterns

3. **Systematic Migration to IsolatedEnvironment**
   - Start with `project_utils.py` (lines 115-117)
   - Fix `logging_config.py` color settings (lines 33-35)
   - Update ALL 371+ violations systematically
   - Preserve environment detection logic
   - Maintain test isolation patterns
   - Update Docker environment mappings

4. **Test Environment Standardization**
   - Replace patch.dict(os.environ) with IsolatedEnvironment mocks
   - Create test environment fixtures
   - Ensure test/prod parity
   - Add environment validation tests
   - Test configuration precedence

### AGENTS TO SPAWN:
- **Environment Scanner Agent**: Find all access patterns
- **Schema Definition Agent**: Define environment contracts
- **Migration Execution Agent**: Replace violations systematically  
- **Service Isolation Agent**: Ensure service independence
- **Test Environment Agent**: Standardize test patterns
- **Validation Agent**: Verify configuration consistency
- **Docker Integration Agent**: Update compose files
- **Compliance Agent**: Ensure zero direct access

### VALIDATION REQUIREMENTS:
- ZERO direct os.environ access (except bootstrap)
- All services using IsolatedEnvironment
- Configuration consistency across environments
- Test suite passing with new patterns
- Environment variables documented
- No configuration drift in staging

### CRITICAL VIOLATIONS TO FIX FIRST:
```python
# project_utils.py lines 115-117
os.environ.get('PYTEST_CURRENT_TEST')  # VIOLATION
os.environ.get('TESTING')  # VIOLATION  
os.environ.get('ENVIRONMENT')  # VIOLATION

# logging_config.py lines 33-35
os.environ['NO_COLOR'] = '1'  # VIOLATION
os.environ['FORCE_COLOR'] = '0'  # VIOLATION
os.environ['PY_COLORS'] = '0'  # VIOLATION
```

---

## 🟢 PROMPT 3: Tool Dispatcher & MCPToolExecutor Deduplication

**LIFE OR DEATH CRITICAL: ACTION:**
PHASE 1 CRITICAL: Fix MCPToolExecutor exact duplicate - Critical SSOT violation

FOR EACH sub task:
1) Understand request-scoped vs singleton patterns
2) Preserve factory-based isolation
3) Maintain backward compatibility
4) Test with real agent executions

### CRITICAL MISSION:
Eliminate 47+ Tool Dispatcher duplicates, especially the CRITICAL exact duplicate of MCPToolExecutor in two files.

### SUB-TASKS TO COMPLETE:

1. **MCPToolExecutor Emergency Deduplication**
   - Compare implementations in:
     * `services/agent_mcp_bridge.py:97`
     * `services/mcp_client_tool_executor.py:21`
   - Determine canonical location (likely mcp_client_tool_executor)
   - Remove duplicate, update all imports
   - Verify MCP bridge functionality intact
   - Test with actual MCP tools

2. **Tool Dispatcher Pattern Analysis**
   - Map relationships between:
     * ToolDispatcher (canonical core)
     * UnifiedToolDispatcher (violation or evolution?)
     * RequestScopedToolDispatcher (new pattern - keep)
     * ToolExecutorFactory (factory pattern - keep)
   - Document which patterns are legitimate
   - Create migration path for violations

3. **Consolidation Strategy Implementation**
   - Keep `ToolDispatcher` as base/abstract
   - Keep `RequestScopedToolDispatcher` for isolation
   - Keep `ToolExecutorFactory` for creation
   - Merge/remove `UnifiedToolDispatcher` features
   - Update all agent implementations
   - Preserve WebSocket event integration

4. **Agent Integration Validation**
   - Test with 20+ agent types
   - Verify tool execution isolation
   - Validate WebSocket notifications
   - Test concurrent agent execution
   - Ensure compensation tracking works

### AGENTS TO SPAWN:
- **Duplicate Hunter Agent**: Find exact duplicates
- **Pattern Analysis Agent**: Understand dispatcher patterns
- **Consolidation Strategy Agent**: Design unified approach
- **Migration Execution Agent**: Implement changes
- **Agent Testing Agent**: Validate with real agents
- **Factory Pattern Agent**: Ensure proper isolation
- **MCP Integration Agent**: Fix MCP tool execution

### VALIDATION REQUIREMENTS:
- ZERO duplicate MCPToolExecutor classes
- Clear dispatcher hierarchy documented
- All agents using correct dispatcher
- Tool execution isolation verified
- WebSocket events flowing correctly
- MCP tools working end-to-end

### BREAKING CHANGE MITIGATION:
- Create compatibility imports if needed
- Add deprecation warnings
- Document migration in TOOL_DISPATCHER_MIGRATION_GUIDE.md
- Provide adapter pattern for legacy code

---

## 🔵 PROMPT 4: Agent Registry Factory Pattern Implementation

**LIFE OR DEATH CRITICAL: ACTION:**
PHASE 2 HIGH: Convert 67+ Agent Registry duplicates to factory pattern

FOR EACH sub task:
1) Understand singleton vs factory patterns
2) Analyze user isolation requirements
3) Test with concurrent users
4) Verify state isolation

### CRITICAL MISSION:
Transform Agent Registry from singleton pattern (causing user state sharing) to factory-based isolation pattern.

### SUB-TASKS TO COMPLETE:

1. **Registry Pattern Architecture Analysis**
   - Study current AgentRegistry in `supervisor/agent_registry.py`
   - Map 312+ references across codebase
   - Identify singleton usage patterns
   - Document state sharing vulnerabilities
   - Design factory-based alternative

2. **Factory Pattern Implementation**
   - Create AgentRegistryFactory class
   - Implement per-request registry creation
   - Add user context isolation
   - Maintain registry lifecycle management
   - Ensure proper cleanup

3. **Systematic Singleton Elimination**
   - Remove all `agent_registry_singleton` references
   - Update initialization patterns
   - Fix dependency injection
   - Update all 312+ usage points
   - Maintain backward compatibility

4. **Concurrent User Validation**
   - Test with 50+ concurrent users
   - Verify complete state isolation
   - Test registry cleanup
   - Validate memory usage
   - Ensure no state leakage

### AGENTS TO SPAWN:
- **Pattern Analysis Agent**: Understand current singleton usage
- **Factory Design Agent**: Design new factory pattern
- **State Isolation Agent**: Ensure user separation
- **Migration Planning Agent**: Plan 312+ reference updates
- **Concurrent Testing Agent**: Validate isolation
- **Memory Profiling Agent**: Check for leaks
- **Integration Agent**: Update dependent systems

### VALIDATION REQUIREMENTS:
- Zero singleton registry instances
- Complete user state isolation
- All 312+ references updated
- 50+ concurrent users supported
- No memory leaks detected
- Agent execution isolated per user

---

## ⚪ PROMPT 5: Session Management & Configuration Unification

**LIFE OR DEATH CRITICAL: ACTION:**
PHASE 2-3: Consolidate 156+ session and 117+ configuration duplicates

FOR EACH sub task:
1) Map all duplicate patterns
2) Identify service boundaries
3) Respect microservice independence
4) Create unified patterns

### CRITICAL MISSION:
Unify session management (156+ duplicates) and configuration patterns (117+ duplicates) while maintaining service independence.

### SUB-TASKS TO COMPLETE:

1. **Session Management Consolidation**
   - Map all DatabaseSession patterns
   - Identify SessionManager duplicates
   - Design unified session architecture
   - Implement in `netra_backend/app/database/`
   - Create session lifecycle management
   - Add connection pool monitoring

2. **Configuration Architecture Standardization**
   - Map 89+ Config classes
   - Identify configuration loading patterns
   - Consolidate to IsolatedEnvironment
   - Create service-specific configs
   - Implement configuration validation
   - Add configuration versioning

3. **Service Independence Preservation**
   - Maintain service boundaries
   - Allow shared libraries pattern
   - Document acceptable duplicates
   - Create service contracts
   - Implement health checks

4. **Cross-Service Testing**
   - Test configuration consistency
   - Validate session isolation
   - Test service communication
   - Verify error propagation
   - Test configuration reload

### AGENTS TO SPAWN:
- **Session Analysis Agent**: Map session patterns
- **Configuration Mapping Agent**: Document config patterns
- **Unification Design Agent**: Create consolidated architecture
- **Service Boundary Agent**: Maintain independence
- **Migration Agent**: Execute consolidation
- **Testing Agent**: Validate changes
- **Documentation Agent**: Update specs

### VALIDATION REQUIREMENTS:
- Unified session management pattern
- Consistent configuration loading
- Service independence maintained
- Zero connection leaks
- Configuration drift eliminated
- All services healthy

---

## 🟣 PROMPT 6: Test Infrastructure SSOT Compliance

**LIFE OR DEATH CRITICAL: ACTION:**
PHASE 3: Standardize test infrastructure and eliminate mock duplicates

FOR EACH sub task:
1) Create canonical test patterns
2) Eliminate mock proliferation
3) Standardize fixtures
4) Document test architecture

### CRITICAL MISSION:
Create single source of truth for test infrastructure, eliminating 156+ mock duplicates.

### SUB-TASKS TO COMPLETE:

1. **Test Mock Consolidation**
   - Find all 67+ MockWebSocketManager variants
   - Create canonical mocks in test_framework
   - Standardize mock behavior
   - Update all test imports
   - Remove duplicate mocks

2. **Fixture Standardization**
   - Create canonical fixtures
   - Standardize scope patterns
   - Fix session/function scope issues
   - Create fixture inheritance
   - Document fixture usage

3. **Test Pattern Documentation**
   - Document approved test patterns
   - Create test architecture guide
   - Define mock vs real service rules
   - Establish test categories
   - Create test templates

4. **Test Suite Validation**
   - Run all 500+ tests
   - Verify no flaky tests
   - Ensure proper isolation
   - Test parallel execution
   - Validate coverage

### AGENTS TO SPAWN:
- **Mock Discovery Agent**: Find all mock patterns
- **Fixture Analysis Agent**: Map fixture usage
- **Standardization Agent**: Create canonical patterns
- **Migration Agent**: Update all tests
- **Validation Agent**: Ensure test quality
- **Documentation Agent**: Create test guide

### VALIDATION REQUIREMENTS:
- Single mock implementation per component
- Standardized fixture patterns
- All tests passing
- Parallel execution working
- Test isolation verified
- Documentation complete

---

## EXECUTION COORDINATION & MONITORING

### CRITICAL EXECUTION ORDER:
1. **Day 1-2**: PROMPT 1 (WebSocket) + PROMPT 2 (Environment) in parallel
2. **Day 3**: PROMPT 3 (Tool Dispatcher) - Depends on 1 & 2
3. **Day 4-5**: PROMPT 4 (Agent Registry) + PROMPT 5 (Session/Config) 
4. **Day 6**: PROMPT 6 (Test Infrastructure)
5. **Day 7**: Integration validation and cleanup

### AGENT COORDINATION RULES:
1. **Share discoveries** via reports in `reports/ssot_remediation/`
2. **Update progress** in MASTER_WIP_STATUS.md hourly
3. **Document violations** fixed in SSOT_COMPLIANCE_LOG.md
4. **Create learnings** for each major fix
5. **Test continuously** with real services

### SUCCESS METRICS:
✅ 89+ WebSocket duplicates eliminated  
✅ 371+ environment violations fixed  
✅ Zero MCPToolExecutor duplicates  
✅ Agent Registry factory pattern implemented  
✅ Session/Config patterns unified  
✅ Test infrastructure standardized  
✅ All mission-critical tests passing  
✅ User isolation verified with 50+ users  

### VALIDATION CHECKPOINTS:
- **Hour 4**: WebSocket canonical selected
- **Hour 8**: Environment migration started
- **Day 1 End**: 50% of critical violations fixed
- **Day 3 End**: All Phase 1 complete
- **Day 5 End**: Phase 2 complete
- **Day 7**: Full system validation

### FAILURE CONTINGENCY:
If any prompt blocked:
1. **Escalate** to architecture team
2. **Document** blocker in BLOCKERS.md
3. **Pivot** to next priority
4. **Create** workaround if possible
5. **Update** timeline and communicate

### COMPLIANCE TRACKING:
Run every 2 hours:
```bash
python scripts/scan_ssot_violations.py --output reports/ssot_progress.json
python scripts/check_architecture_compliance.py
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### FINAL VALIDATION:
After all prompts complete:
1. Run full test suite with real services
2. Verify zero SSOT violations remain
3. Test with 100+ concurrent users
4. Validate staging environment
5. Create final compliance report

---

## REMEMBER: SPACECRAFT MISSION CRITICAL

**Our lives depend on eliminating these 847 SSOT violations.**

Each violation is a potential mission failure point. The $4.452M revenue risk is just the beginning - the real risk is total system failure under load.

**WORK SYSTEMATICALLY. TEST EVERYTHING. DOCUMENT THOROUGHLY.**

**Mission Success Criteria:**
- ZERO SSOT violations in production code
- Complete user isolation verified
- All systems passing mission-critical tests
- Platform ready for 100+ concurrent users
- Documentation complete and accurate

**COMPLETE THE MISSION. THERE IS NO ALTERNATIVE.**