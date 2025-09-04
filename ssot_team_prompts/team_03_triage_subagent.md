# Team 3: Triage SubAgent Consolidation Prompt

## COPY THIS ENTIRE PROMPT:

You are a Triage Architecture Expert implementing SSOT consolidation for the Triage SubAgent module with CRITICAL execution order fixes.

🚨 ULTRA CRITICAL FIRST ACTION - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

MANDATORY READING BEFORE STARTING:
1. CLAUDE.md (entire document, especially sections 2.1, 3.6, 6 AND the recent issues section)
2. USER_CONTEXT_ARCHITECTURE.md (factory patterns)
3. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
4. SPEC/learnings/agent_execution_order_fix_20250904.xml (CRITICAL!)
5. AGENT_EXECUTION_ORDER_REASONING.md
6. Triage section in DEFINITION_OF_DONE_CHECKLIST.md
7. METADATA_STORAGE_MIGRATION_AUDIT.md (metadata patterns)

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Consolidate 28 files in triage_sub_agent/ into ONE UnifiedTriageAgent
2. FIX CRITICAL BUG: Triage MUST execute FIRST (before Data and Optimization)
3. Implement factory pattern for user isolation
4. Migrate ALL metadata operations to BaseAgent SSOT methods (6 violations)
5. Ensure correct execution order: Triage → Data → Optimize → Actions → Report

TARGET IMPLEMENTATION:
```python
# Location: netra_backend/app/agents/triage/unified_triage_agent.py
class UnifiedTriageAgentFactory:
    """Factory for creating isolated triage agents per request"""
    def create_for_context(self, user_context: UserExecutionContext):
        return UnifiedTriageAgent(
            context=user_context,
            isolation_strategy=IsolationStrategy.PER_REQUEST,
            execution_priority=0  # CRITICAL: Must run FIRST
        )

class UnifiedTriageAgent(BaseAgent):
    """SSOT for ALL triage operations - MUST RUN FIRST"""
    EXECUTION_ORDER = 0  # CRITICAL: First in sequence
    
    def __init__(self, context: UserExecutionContext):
        super().__init__()
        self.context = context
        self.priority = 0  # Ensure first execution
    
    def triage_request(self, context: UserExecutionContext, request: Any):
        # CRITICAL: This must happen BEFORE data/optimization
        self.emit_websocket_event('agent_started', {'type': 'triage'})
        
        # Triage logic determines what agents run next
        triage_result = self._perform_triage(request)
        
        # Store using SSOT methods
        self.store_metadata_result(context, 'triage_result', triage_result)
        self.store_metadata_result(context, 'next_agents', triage_result.required_agents)
        
        return triage_result
```

FILES TO CONSOLIDATE:
- All 28 files in triage_sub_agent/
- Any triage utilities in other modules
- Triage configuration and strategies

CRITICAL EXECUTION ORDER FIX:
```python
# WRONG (current bug):
# Optimization runs before Data collection!
order = ['optimize', 'data', 'triage']  

# CORRECT (must implement):
order = ['triage', 'data', 'optimize', 'actions', 'report']
```

CRITICAL REQUIREMENTS:
1. Generate MRO report before refactoring (CLAUDE.md 3.6)
2. FIX EXECUTION ORDER - Triage MUST run first
3. Preserve factory patterns for user isolation
4. Maintain ALL WebSocket critical events
5. Validate against MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
6. Use UnifiedDockerManager for Docker operations
7. Test with real services (mocks forbidden)
8. Extract ALL value from files before deletion
9. Migrate metadata to SSOT methods (6 violations)
10. Verify execution order in supervisor/orchestrator

VALUE PRESERVATION PROCESS (Per File):
1. Run git log - identify triage logic fixes
2. Grep for triage strategies and rules
3. Check for WebSocket event emissions
4. Extract triage algorithms and heuristics
5. Document in extraction_report_[filename].md
6. Migrate triage tests
7. ONLY delete after extraction

METADATA MIGRATION (CRITICAL):
Fix 6 violations in triage files:
```python
# WRONG (6 violations found):
context.metadata['triage_score'] = score
context.metadata['agent_queue'].append(agent)
context.metadata['priority'] = high

# RIGHT:
self.store_metadata_result(context, 'triage_score', score)
self.append_metadata_list(context, 'agent_queue', agent)
self.store_metadata_result(context, 'priority', high)
```

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] Document CURRENT execution order (likely wrong)
- [ ] Run python tests/unified_test_runner.py --real-services --category triage
- [ ] Create tests proving triage runs FIRST
- [ ] Run python tests/mission_critical/test_websocket_agent_events_suite.py
- [ ] Capture execution order logs

Stage 2 - During consolidation:
- [ ] Test execution order after EACH change
- [ ] Verify triage → data → optimize sequence
- [ ] Create unit tests for triage strategies
- [ ] Test WebSocket events continuously
- [ ] Multi-user triage isolation tests

Stage 3 - Post-consolidation:
- [ ] Full regression with correct order
- [ ] Performance benchmarks for triage
- [ ] Load test with 10+ concurrent triages
- [ ] Execution order verification logs
- [ ] Memory usage comparison

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] Supervisor agent execution order configuration
- [ ] Orchestrator agent sequencing
- [ ] Import statements for triage_sub_agent/
- [ ] Factory registration in AgentRegistry
- [ ] Triage strategy configuration
- [ ] WebSocket event order (triage first!)
- [ ] API endpoints calling triage
- [ ] Frontend expectations of execution order
- [ ] Test assertions about agent order
- [ ] Documentation about workflow

DETAILED REPORTING REQUIREMENTS:
Create reports/team_03_triage_subagent_[timestamp].md with:

## Consolidation Report - Team 3: Triage SubAgent
### Phase 1: Analysis
- Files analyzed: 28 in triage_sub_agent/
- Execution order bug: CONFIRMED (optimize before data)
- Critical triage logic: [list strategies]
- Recent fixes: [commits related to triage]
- Metadata violations: 6 found

### Phase 2: Implementation  
- SSOT location: netra_backend/app/agents/triage/unified_triage_agent.py
- Execution order fix: Triage set to priority 0
- Factory implementation: Per-request isolation
- Triage strategies: [consolidated approach]
- Supervisor integration: [order configuration]

### Phase 3: Validation
- Execution order tests: [proof triage runs first]
- Tests created: [unit, integration counts]
- Tests passing: [percentage]
- Performance: [triage decision time]
- WebSocket events: [correct order verified]

### Phase 4: Cleanup
- Files deleted: 28 from triage_sub_agent/
- Imports updated: [count]
- Execution order documented
- Learnings: Order criticality captured

### Evidence of Correctness:
- Execution logs showing: Triage → Data → Optimize
- Test results with correct order
- WebSocket events in correct sequence
- Multi-user triage working
- Performance benchmarks
- Memory usage stable

VALIDATION CHECKLIST:
- [ ] MRO report for triage hierarchy
- [ ] EXECUTION ORDER FIXED (Triage first!)
- [ ] Factory pattern implemented
- [ ] WebSocket events maintained
- [ ] Absolute imports used
- [ ] Named values validated
- [ ] Tests passing with --real-services
- [ ] Value extracted from 28 files
- [ ] Extraction reports complete
- [ ] Metadata SSOT (6 violations fixed)
- [ ] Zero direct metadata assignments
- [ ] Legacy files deleted
- [ ] CLAUDE.md compliance
- [ ] Breaking changes fixed
- [ ] No performance regression
- [ ] Multi-user isolation verified
- [ ] Execution order documented

SUCCESS CRITERIA:
- Single UnifiedTriageAgent implementation
- TRIAGE RUNS FIRST (critical bug fixed)
- Correct order: Triage → Data → Optimize → Actions → Report
- Zero triage functionality loss
- Factory isolation maintained
- WebSocket events in correct order
- Metadata violations fixed (6 → 0)
- Performance maintained
- Multi-user triage working
- Complete execution order documentation

PRIORITY: P0 CRITICAL (Execution order bug is breaking system)
TIME ALLOCATION: 22 hours
EXPECTED REDUCTION: 28 files → 1 unified implementation
CRITICAL FIX: Execution order (Triage MUST run first)