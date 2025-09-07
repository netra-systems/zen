# Parallel SSOT Remediation Agent Prompts

**Mission:** Execute parallel SSOT consolidation across 8 specialized agents to eliminate all duplicate implementations within 5 days.

**Critical Context:** Each agent MUST read `CLAUDE.md` and `SSOT_VIOLATION_REPORT_CURRENT_STATE.md` before starting.

---

## Agent 1: Execution Engine Auditor
**Priority:** P0 - CRITICAL  
**Timeline:** Day 1  
**Dependencies:** None

### Mission
You are the Execution Engine Auditor. Your mission is to perform deep analysis of all ExecutionEngine implementations and create a definitive consolidation plan.

### Specific Tasks
1. **Analyze ALL ExecutionEngine implementations:**
   ```
   - netra_backend/app/agents/execution_engine_consolidated.py
   - netra_backend/app/agents/supervisor/execution_engine.py
   - netra_backend/app/agents/data_sub_agent/execution_engine.py
   ```

2. **Create detailed comparison matrix:**
   - List all methods in each implementation
   - Identify unique features per implementation
   - Document parameter differences
   - Note WebSocket integration patterns
   - Analyze error handling approaches

3. **Determine canonical implementation:**
   - Recommend which file should be the SSOT
   - Document why (feature completeness, test coverage, usage)
   - List features to migrate from other implementations

4. **Generate MRO (Method Resolution Order) report:**
   - Use `inspect.getmro()` on all classes
   - Document inheritance hierarchies
   - Identify potential conflicts

5. **Output:** Create `EXECUTION_ENGINE_AUDIT_REPORT.md` with:
   - Feature comparison matrix
   - Canonical recommendation with justification
   - Migration checklist
   - Risk assessment
   - Test coverage analysis

### Success Criteria
- [ ] All three implementations analyzed
- [ ] Clear canonical choice with data-driven justification
- [ ] Complete feature inventory
- [ ] MRO conflicts identified
- [ ] Migration plan created

---

## Agent 2: Execution Engine Consolidator
**Priority:** P0 - CRITICAL  
**Timeline:** Day 1-2  
**Dependencies:** Agent 1 output

### Mission
You are the Execution Engine Consolidator. Using Agent 1's audit report, merge all ExecutionEngine implementations into a single canonical SSOT.

### Specific Tasks
1. **Read Agent 1's audit report**

2. **Implement consolidation:**
   - Start with canonical implementation
   - Add missing features from other implementations
   - Use configuration flags for variant behaviors:
   ```python
   class ExecutionEngineConfig:
       enable_caching: bool = True
       enable_metrics: bool = True
       websocket_mode: str = "enhanced"  # or "basic"
   ```

3. **Preserve all functionality:**
   - Ensure no features are lost
   - Maintain backward compatibility
   - Add deprecation warnings where needed

4. **Update imports system-wide:**
   - Find all imports of old implementations
   - Update to use consolidated version
   - Remove old import statements

5. **Delete duplicate files:**
   - Remove non-canonical implementations
   - Clean up any related utility files

6. **Output:** 
   - Consolidated `execution_engine.py`
   - `EXECUTION_ENGINE_CONSOLIDATION_COMPLETE.md` report
   - List of all files modified

### Success Criteria
- [ ] Single ExecutionEngine implementation
- [ ] All tests passing
- [ ] No functionality lost
- [ ] All imports updated
- [ ] Old files removed

---

## Agent 3: Factory Pattern Unifier
**Priority:** P0  
**Timeline:** Day 2  
**Dependencies:** None (can run parallel)

### Mission
You are the Factory Pattern Unifier. Consolidate all factory implementations into single, configurable factories.

### Specific Tasks
1. **Analyze factory duplicates:**
   ```
   - execution_engine_factory.py
   - execution_factory.py
   - Review factory_performance_config.py usage
   ```

2. **Create unified factory:**
   ```python
   class UnifiedExecutionEngineFactory:
       def __init__(self, config: FactoryConfig):
           self.config = config
           
       def create_engine(self, engine_type: str) -> ExecutionEngine:
           # Single method with configuration-based behavior
   ```

3. **Migrate RequestScopedExecutorFactory:**
   - Ensure it uses unified factory
   - Remove any duplicate factory logic

4. **Update all factory consumers:**
   - Find all factory instantiations
   - Update to use unified factory
   - Test each consumer

5. **Output:**
   - Single `execution_factory.py`
   - `FACTORY_UNIFICATION_COMPLETE.md` report
   - Consumer migration log

### Success Criteria
- [ ] Single factory implementation per type
- [ ] Configuration-driven behavior
- [ ] All consumers updated
- [ ] Tests passing
- [ ] Performance unchanged or improved

---

## Agent 4: WebSocket Manager Consolidator
**Priority:** P1  
**Timeline:** Day 3  
**Dependencies:** Agents 1-2 completion preferred

### Mission
You are the WebSocket Manager Consolidator. Establish a single WebSocketManager as the SSOT for all WebSocket operations.

### Specific Tasks
1. **Audit WebSocket implementations:**
   ```
   - websocket_core/manager.py
   - agents/base/interface.py
   - core/interfaces_websocket.py
   - Check for UnifiedWebSocketManager usage
   ```

2. **Define canonical WebSocketManager:**
   - Choose `websocket_core/manager.py` as likely SSOT
   - Extract clean interfaces
   - Ensure thread-safety and user isolation

3. **Consolidate event handling:**
   ```python
   class WebSocketEventType(Enum):
       AGENT_STARTED = "agent_started"
       AGENT_THINKING = "agent_thinking"
       TOOL_EXECUTING = "tool_executing"
       TOOL_COMPLETED = "tool_completed"
       AGENT_COMPLETED = "agent_completed"
   ```

4. **Update all agents:**
   - Ensure all agents use canonical manager
   - Verify event emission patterns
   - Test with real WebSocket connections

5. **Run mission-critical tests:**
   ```bash
   python tests/mission_critical/test_websocket_agent_events_suite.py
   ```

6. **Output:**
   - Consolidated WebSocketManager
   - `WEBSOCKET_CONSOLIDATION_COMPLETE.md`
   - Event flow documentation

### Success Criteria
- [ ] Single WebSocketManager implementation
- [ ] All events properly emitted
- [ ] Mission-critical tests passing
- [ ] No event loss or duplication
- [ ] Clean interface separation

---

## Agent 5: Tool Dispatcher Unifier
**Priority:** P1  
**Timeline:** Day 3-4  
**Dependencies:** None (can run parallel)

### Mission
You are the Tool Dispatcher Unifier. Create a single, canonical ToolDispatcher implementation.

### Specific Tasks
1. **Analyze tool dispatcher variants:**
   ```
   - tool_dispatcher_core.py
   - tool_dispatcher_consolidated.py (if exists)
   - EnhancedToolDispatcher variations
   ```

2. **Choose canonical implementation:**
   - Likely `tool_dispatcher_core.py`
   - Document decision rationale

3. **Merge unique features:**
   - WebSocket notifications
   - Error handling enhancements
   - Metrics collection
   - Tool result caching

4. **Create clean interfaces:**
   ```python
   class IToolDispatcher(Protocol):
       async def dispatch(self, tool_name: str, params: Dict) -> ToolResult:
           ...
   ```

5. **Update all tool execution paths:**
   - Find all tool dispatcher usage
   - Update to canonical implementation
   - Verify tool execution flow

6. **Output:**
   - Single `tool_dispatcher.py`
   - `TOOL_DISPATCHER_UNIFICATION_COMPLETE.md`
   - Interface documentation

### Success Criteria
- [ ] Single ToolDispatcher implementation
- [ ] All tool types supported
- [ ] WebSocket integration working
- [ ] Error handling comprehensive
- [ ] Performance maintained

---

## Agent 6: Emitter Pool Optimizer
**Priority:** P2  
**Timeline:** Day 4  
**Dependencies:** Agent 4 completion

### Mission
You are the Emitter Pool Optimizer. Consolidate WebSocket emitter implementations and optimize pooling.

### Specific Tasks
1. **Analyze emitter implementations:**
   ```
   - UserWebSocketEmitter in agent_instance_factory.py
   - websocket_emitter_pool.py
   - Any OptimizedEmitter references
   ```

2. **Consolidate into single pattern:**
   - Decide: pooled vs non-pooled as configuration
   - Implement in agent_instance_factory.py
   - Remove separate pool file if redundant

3. **Optimize performance:**
   ```python
   class EmitterConfig:
       enable_pooling: bool = True
       pool_size: int = 100
       reuse_connections: bool = True
   ```

4. **Memory management:**
   - Implement proper cleanup
   - Add memory limits
   - Monitor for leaks

5. **Output:**
   - Optimized emitter in factory
   - `EMITTER_OPTIMIZATION_COMPLETE.md`
   - Performance benchmarks

### Success Criteria
- [ ] Single emitter implementation
- [ ] Configurable pooling
- [ ] No memory leaks
- [ ] Performance improved
- [ ] Clean resource management

---

## Agent 7: Compliance Automation Builder
**Priority:** P1  
**Timeline:** Day 4-5  
**Dependencies:** None (can run parallel)

### Mission
You are the Compliance Automation Builder. Create automated tools to prevent future SSOT violations.

### Specific Tasks
1. **Enhance compliance checker:**
   ```python
   # scripts/check_ssot_compliance.py
   def detect_duplicate_classes():
       # Find all class definitions
       # Group by class name
       # Report duplicates
   ```

2. **Create pre-commit hooks:**
   ```yaml
   # .pre-commit-config.yaml
   - repo: local
     hooks:
     - id: ssot-check
       name: SSOT Compliance Check
       entry: python scripts/check_ssot_compliance.py
       language: python
       files: \.py$
   ```

3. **Build CI/CD integration:**
   - Add to GitHub Actions
   - Fail builds on violations
   - Generate reports

4. **Create violation scanner:**
   ```python
   # scripts/scan_ssot_violations.py
   class SSOTViolationScanner:
       def scan_codebase(self) -> List[Violation]:
           # Comprehensive scanning logic
   ```

5. **Documentation generator:**
   - Auto-generate SSOT map
   - Update string literals index
   - Create dependency graphs

6. **Output:**
   - Automated compliance tools
   - `COMPLIANCE_AUTOMATION_COMPLETE.md`
   - CI/CD configuration

### Success Criteria
- [ ] Automated violation detection
- [ ] Pre-commit hooks working
- [ ] CI/CD integration complete
- [ ] Documentation auto-generated
- [ ] Zero false positives

---

## Agent 8: Integration Test Orchestrator
**Priority:** P0  
**Timeline:** Day 5  
**Dependencies:** All other agents

### Mission
You are the Integration Test Orchestrator. Ensure all consolidations work together seamlessly.

### Specific Tasks
1. **Run comprehensive test suite:**
   ```bash
   python tests/unified_test_runner.py --real-services --real-llm
   ```

2. **Test WebSocket event flow:**
   ```bash
   python tests/mission_critical/test_websocket_agent_events_suite.py
   ```

3. **Validate agent workflows:**
   - Test each agent type
   - Verify tool execution
   - Check WebSocket events
   - Validate error handling

4. **Performance testing:**
   - Benchmark before/after
   - Memory usage analysis
   - Concurrent user testing
   - Resource leak detection

5. **Create rollback plan:**
   - Document all changes
   - Create rollback scripts
   - Test rollback procedure

6. **Update documentation:**
   - Update all specs
   - Create migration guide
   - Document new patterns

7. **Output:**
   - `INTEGRATION_TEST_REPORT.md`
   - Performance comparison
   - Rollback procedures
   - Updated documentation

### Success Criteria
- [ ] All tests passing
- [ ] No performance regression
- [ ] WebSocket events working
- [ ] Memory usage stable
- [ ] Documentation complete

---

## Coordination Protocol

### Daily Sync Points
- **Start of Day:** Read previous agents' outputs
- **Mid-Day:** Update progress in report
- **End of Day:** Commit working changes

### Communication
- Use `SSOT_REMEDIATION_PROGRESS.md` for status updates
- Flag blockers immediately
- Share discoveries in `SPEC/learnings/`

### Conflict Resolution
- If conflicts arise, document in `SSOT_CONFLICTS.md`
- Escalate to Principal Engineer role
- Prioritize business value

### Testing Strategy
- Test after each consolidation
- Run integration tests frequently
- Use real services, not mocks
- Validate with actual WebSocket connections

### Success Metrics
- Zero duplicate implementations
- All tests passing
- No performance degradation
- Complete documentation
- Automated compliance checking

---

## Launch Command

```bash
# Launch all agents in parallel
# Each agent should be run in a separate context/session

# Audit agents (can start immediately)
python -m netra_agent "Execute Agent 1: Execution Engine Auditor prompt"
python -m netra_agent "Execute Agent 3: Factory Pattern Unifier prompt"
python -m netra_agent "Execute Agent 7: Compliance Automation Builder prompt"

# Consolidation agents (start after audits)
python -m netra_agent "Execute Agent 2: Execution Engine Consolidator prompt"
python -m netra_agent "Execute Agent 4: WebSocket Manager Consolidator prompt"
python -m netra_agent "Execute Agent 5: Tool Dispatcher Unifier prompt"

# Optimization agent (start after consolidations)
python -m netra_agent "Execute Agent 6: Emitter Pool Optimizer prompt"

# Final validation (start after all complete)
python -m netra_agent "Execute Agent 8: Integration Test Orchestrator prompt"
```

---

**Remember:** ULTRA THINK DEEPLY. This consolidation is critical for platform stability and business value. Each violation fixed reduces maintenance burden and improves system reliability.