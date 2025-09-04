# Team 2: Tool Dispatcher & Admin Tool Consolidation Prompt

## COPY THIS ENTIRE PROMPT:

You are a Tool Architecture Expert implementing SSOT consolidation for Tool Dispatcher and Admin Tool modules.

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
4. TOOL_DISPATCHER_MIGRATION_GUIDE.md (migration from singleton)
5. Tool Dispatcher section in DEFINITION_OF_DONE_CHECKLIST.md
6. METADATA_STORAGE_MIGRATION_AUDIT.md (metadata patterns)
7. SPEC/learnings/websocket_agent_integration_critical.xml

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Consolidate 3+ ToolDispatcher implementations into ONE canonical version
2. Consolidate 24 admin_tool_dispatcher files into ONE UnifiedAdminToolDispatcher
3. Implement request-scoped factory pattern per TOOL_DISPATCHER_MIGRATION_GUIDE
4. Ensure WebSocket notifications for ALL tool executions
5. Migrate metadata operations to BaseAgent SSOT methods

TARGET IMPLEMENTATION:
```python
# Location: netra_backend/app/core/tools/unified_tool_dispatcher.py
class UnifiedToolDispatcherFactory:
    """Factory maintaining tool isolation per user request"""
    def create_for_request(self, request_context: RequestContext):
        dispatcher = UnifiedToolDispatcher(request_context)
        # CRITICAL: Must enhance with WebSocket notifier
        if request_context.websocket_manager:
            dispatcher.set_websocket_manager(request_context.websocket_manager)
        return dispatcher

class UnifiedToolDispatcher:
    """SSOT for ALL tool execution - base class"""
    def execute_tool(self, tool_name: str, params: dict, context: UserExecutionContext):
        # Emit WebSocket event BEFORE execution
        self._emit_tool_executing(tool_name, params)
        result = self._execute_internal(tool_name, params, context)
        # Emit WebSocket event AFTER execution
        self._emit_tool_completed(tool_name, result)
        return result

# Location: netra_backend/app/admin/tools/unified_admin_dispatcher.py
class UnifiedAdminToolDispatcher(UnifiedToolDispatcher):
    """Admin-specific tool dispatcher extending base"""
    pass
```

FILES TO CONSOLIDATE:

Tool Dispatcher Files:
- tool_dispatcher_core.py (likely CANONICAL - keep this one)
- tool_dispatcher_consolidated.py (merge or delete)
- schemas/tool.py (ToolDispatcher interface - merge)
- agents/interfaces.py (tool interfaces - merge)

Admin Tool Files (24 total):
- All files in admin_tool_dispatcher/ folder
- Extract unique admin tools and consolidate

CRITICAL REQUIREMENTS:
1. Generate MRO report before refactoring (CLAUDE.md 3.6)
2. Preserve factory patterns for user isolation
3. Maintain ALL WebSocket critical events for tools
4. Single ToolDispatcher base implementation
5. Validate all named values against MISSION_CRITICAL index
6. Use UnifiedDockerManager for all Docker operations
7. Test with real services (mocks forbidden)
8. Extract ALL value from files before deletion
9. Migrate metadata to SSOT methods (5 violations in admin tools)
10. Follow request-scoped pattern from migration guide

VALUE PRESERVATION PROCESS (Per File):
1. Run git log on file - identify recent tool fixes
2. Grep for error handling in tool execution
3. Check for WebSocket event emissions in tools
4. Extract unique tool implementations
5. Document in extraction_report_[filename].md
6. Migrate tool tests to new location
7. ONLY delete after value extracted

METADATA MIGRATION (CRITICAL):
Replace ALL instances in admin tools:
```python
# WRONG (5 violations found):
context.metadata['tool_result'] = result
context.metadata['tool_errors'].append(error)

# RIGHT:
self.store_metadata_result(context, 'tool_result', result)
self.append_metadata_list(context, 'tool_errors', error)
```

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] Run python tests/unified_test_runner.py --real-services --category tools
- [ ] Create NEW tests for all 24 admin tools
- [ ] Run python tests/mission_critical/test_websocket_agent_events_suite.py
- [ ] Document current tool execution flow

Stage 2 - During consolidation:
- [ ] After EACH tool migration, run its tests
- [ ] Create unit tests for tool dispatcher factory
- [ ] Test WebSocket events for tool_executing/tool_completed
- [ ] Verify request-scoped isolation with concurrent tool calls

Stage 3 - Post-consolidation:
- [ ] Full regression: python tests/unified_test_runner.py --real-services
- [ ] Performance benchmarks for tool execution
- [ ] Load test with 10+ users executing tools concurrently
- [ ] WebSocket event verification for all tools
- [ ] Memory usage comparison

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] Import statements for tool_dispatcher across codebase
- [ ] Admin tool imports (24 files worth of imports!)
- [ ] Tool registration in AgentRegistry
- [ ] Tool dispatcher factory initialization
- [ ] WebSocket manager injection points
- [ ] Tool execution call sites
- [ ] API endpoints using tools
- [ ] Frontend tool invocation paths
- [ ] Tool configuration loading
- [ ] Error handling for tool failures

DETAILED REPORTING REQUIREMENTS:
Create reports/team_02_tool_dispatcher_[timestamp].md with:

## Consolidation Report - Team 2: Tool Dispatcher
### Phase 1: Analysis
- Files analyzed: 3 ToolDispatcher + 24 admin files
- Duplicates found: [list all ToolDispatcher variants]
- Critical tools identified: [list all 24 admin tools]
- Recent fixes extracted: [tool-related commits]
- Metadata violations: 5 in admin_tool_dispatcher/

### Phase 2: Implementation  
- SSOT location: netra_backend/app/core/tools/unified_tool_dispatcher.py
- Admin location: netra_backend/app/admin/tools/unified_admin_dispatcher.py
- Factory pattern: Request-scoped per migration guide
- Tool registry approach: [how tools are registered]
- WebSocket integration: [how events are emitted]

### Phase 3: Validation
- Tests created: [count for each tool]
- Tests passing: [percentage]
- Tool execution performance: [benchmarks]
- Concurrent execution: [10 users tested]
- WebSocket events: [tool_executing, tool_completed verified]

### Phase 4: Cleanup
- Files deleted: 24 admin + 2 duplicate dispatchers
- Imports updated: [count]
- Documentation: TOOL_DISPATCHER_MIGRATION_GUIDE updated
- Learnings: Request-scoped patterns documented

### Evidence of Correctness:
- Test results showing all tools working
- WebSocket capture of tool events
- Performance comparison (before/after)
- Multi-user tool execution logs
- Memory usage for tool pool
- Request isolation proof

VALIDATION CHECKLIST:
- [ ] MRO report for ToolDispatcher hierarchy
- [ ] Factory pattern implemented (request-scoped)
- [ ] WebSocket events for ALL tool executions
- [ ] Absolute imports throughout
- [ ] Named values validated
- [ ] Tests with --real-services passing
- [ ] Value extracted from 24 admin files
- [ ] Extraction reports created
- [ ] Metadata SSOT (5 violations fixed)
- [ ] Zero direct metadata assignments
- [ ] Legacy files deleted after extraction
- [ ] CLAUDE.md compliance verified
- [ ] Breaking changes fixed
- [ ] No performance regression
- [ ] Multi-user isolation working
- [ ] Complete documentation

SUCCESS CRITERIA:
- Single UnifiedToolDispatcher base class
- Single UnifiedAdminToolDispatcher extending base
- All 24 admin tools consolidated and working
- Zero tool functionality loss
- Request-scoped isolation verified
- WebSocket events for all tools
- Metadata violations fixed (5 → 0)
- Performance maintained or improved
- Multi-user tool execution working
- Complete migration from singleton pattern

PRIORITY: P0 CRITICAL
TIME ALLOCATION: 22 hours
EXPECTED REDUCTION: 27+ files → 2 unified implementations