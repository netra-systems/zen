# Team 1: Data SubAgent SSOT Consolidation Prompt

## COPY THIS ENTIRE PROMPT:

You are a Data Architecture Expert implementing SSOT consolidation for the Data SubAgent module.

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
4. SPEC/learnings/ssot_consolidation_20250825.xml
5. Data SubAgent section in DEFINITION_OF_DONE_CHECKLIST.md
6. METADATA_STORAGE_MIGRATION_AUDIT.md (metadata patterns)
7. SPEC/learnings/agent_execution_order_fix_20250904.xml

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Consolidate 30+ files in data_sub_agent/ into ONE UnifiedDataAgent class
2. Identify and preserve the canonical ExecutionEngine (likely execution_engine_consolidated.py)
3. Implement factory pattern for user isolation per USER_CONTEXT_ARCHITECTURE
4. Migrate ALL metadata operations to BaseAgent SSOT methods
5. Ensure Data agent executes AFTER Triage but BEFORE Optimization

TARGET IMPLEMENTATION:
```python
# Location: netra_backend/app/agents/data/unified_data_agent.py
class UnifiedDataAgentFactory:
    """Factory for creating isolated data agents per request"""
    def create_for_context(self, user_context: UserExecutionContext):
        return UnifiedDataAgent(
            context=user_context,
            isolation_strategy=IsolationStrategy.PER_REQUEST
        )

class UnifiedDataAgent(BaseAgent):
    """SSOT for ALL data operations - maintains isolation"""
    def __init__(self, context: UserExecutionContext):
        super().__init__()
        self.context = context
        self.strategies = self._load_strategies()
    
    def process_data(self, context: UserExecutionContext, data: Any):
        # Use SSOT metadata methods
        self.store_metadata_result(context, 'result', data)
        self.append_metadata_list(context, 'data_points', data_point)
```

FILES TO CONSOLIDATE:
- data_sub_agent/*.py (all 30+ files)
- data_sub_agent/execution_engine.py (merge with canonical)
- Any data processing utilities scattered in other modules

CRITICAL REQUIREMENTS:
1. Generate MRO report before refactoring (CLAUDE.md 3.6)
2. Preserve factory patterns for user isolation
3. Maintain ALL WebSocket critical events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
4. Follow correct agent execution order (Triage → Data → Optimize → Actions → Report)
5. Validate all named values against MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
6. Use UnifiedDockerManager for all Docker operations
7. Test with real services (mocks forbidden)
8. Extract ALL value from files before deletion
9. Migrate metadata to SSOT methods (NO direct assignments)
10. CONTINUOUSLY AUDIT for breaking changes

VALUE PRESERVATION PROCESS (Per File):
1. Run git log on file - identify recent fixes
2. Grep for error handling patterns
3. Check for WebSocket event emissions
4. Extract unique algorithms/validations
5. Document in extraction_report_[filename].md
6. Migrate tests to new location
7. ONLY delete after value extracted

METADATA MIGRATION (CRITICAL):
Replace ALL instances of:
```python
# WRONG:
context.metadata['key'] = value
context.metadata['results'] = result.model_dump()
context.metadata['list'].append(item)

# RIGHT:
self.store_metadata_result(context, 'key', value)
self.store_metadata_result(context, 'results', result)
self.append_metadata_list(context, 'list', item)
```

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] Run python tests/unified_test_runner.py --real-services --category data
- [ ] Create NEW tests for current data processing functionality
- [ ] Run python tests/mission_critical/test_websocket_agent_events_suite.py
- [ ] Document current WebSocket event flow for data operations

Stage 2 - During consolidation:
- [ ] After EACH file change, run related tests
- [ ] Create unit tests for extracted data algorithms
- [ ] Test WebSocket events continuously
- [ ] Verify factory isolation with multi-user data processing tests

Stage 3 - Post-consolidation:
- [ ] Full regression: python tests/unified_test_runner.py --real-services
- [ ] Performance benchmarks for data operations (no regression)
- [ ] Load test with 10+ concurrent users processing data
- [ ] WebSocket event integrity verification
- [ ] Memory usage comparison for large datasets

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] Import statements in ALL files importing from data_sub_agent/
- [ ] Supervisor agent references to data processing
- [ ] Factory registration in AgentRegistry
- [ ] Configuration loading for data strategies
- [ ] Environment variable access patterns
- [ ] WebSocket event registrations for data events
- [ ] Tool dispatcher registrations for data tools
- [ ] Agent execution order configuration
- [ ] Database migrations if data schemas changed
- [ ] API endpoint registrations for data endpoints
- [ ] Frontend API calls for data operations

DETAILED REPORTING REQUIREMENTS:
Create reports/team_01_data_subagent_[timestamp].md with:

## Consolidation Report - Team 1: Data SubAgent
### Phase 1: Analysis
- Files analyzed: [30+ files in data_sub_agent/]
- Duplicates found: [list ExecutionEngine duplicates]
- Critical logic identified: [data strategies, algorithms]
- Recent fixes extracted: [list with commit hashes]
- Metadata violations found: [count and locations]

### Phase 2: Implementation  
- SSOT location chosen: netra_backend/app/agents/data/unified_data_agent.py
- Factory pattern implementation: [show UnifiedDataAgentFactory code]
- Configuration strategy: [strategy-based approach]
- Migration approach: [step by step consolidation plan]
- ExecutionEngine consolidation: [which one kept and why]

### Phase 3: Validation
- Tests created: [unit, integration, e2e counts]
- Tests passing: [percentage before/after]
- Performance impact: [data processing benchmarks]
- Memory impact: [before/after for 1000 data points]
- WebSocket events verified: [all 5 critical events working]
- Multi-user data processing: [10 users tested]

### Phase 4: Cleanup
- Files deleted: [30+ files from data_sub_agent/]
- Imports updated: [count across codebase]
- Documentation updated: [GOLDEN_AGENT_INDEX.md, etc]
- Learnings captured: [data consolidation patterns]

### Evidence of Correctness:
- Screenshot/log of test results
- WebSocket event capture showing data processing events
- Performance benchmark results for data operations
- Multi-user test results showing isolation
- Memory usage graphs for large datasets
- Execution order proof (Triage → Data → Optimize)

VALIDATION CHECKLIST:
- [ ] MRO report generated and saved for data inheritance
- [ ] Factory pattern preserved/implemented for data agents
- [ ] WebSocket events maintained (run test_websocket_agent_events_suite.py)
- [ ] All imports updated to absolute
- [ ] Named values validated against MISSION_CRITICAL index
- [ ] Tests passing with --real-services
- [ ] Value extracted from all deleted data files
- [ ] Extraction reports created for each data file
- [ ] Metadata migrated to SSOT methods (8 violations fixed)
- [ ] Zero direct metadata assignments remain
- [ ] Legacy data files deleted ONLY after extraction
- [ ] Compliance with CLAUDE.md verified
- [ ] Breaking changes audited and fixed
- [ ] Performance benchmarks show no regression
- [ ] Multi-user isolation verified for data processing
- [ ] Detailed report created with evidence
- [ ] ExecutionEngine duplicates resolved

SUCCESS CRITERIA:
- Single UnifiedDataAgent implementation
- Single ExecutionEngine (3 duplicates removed)
- Zero data processing functionality loss
- All mission-critical tests passing
- Factory isolation for data operations maintained
- Chat value delivery preserved for data insights
- Metadata SSOT complete (8 violations fixed)
- No performance regression in data processing
- Multi-user data support intact
- Complete audit trail with evidence
- Correct execution order (Data AFTER Triage)

PRIORITY: P0 ULTRA CRITICAL
TIME ALLOCATION: 20 hours
EXPECTED REDUCTION: 30+ files → 1 unified implementation