# Unified User Value System (UVS) - Master Orchestration Prompt

## CRITICAL: READ THIS FIRST

This is the master orchestration for implementing the Unified User Value System (UVS) that guarantees meaningful value delivery to every user. The system ensures that ReportingSubAgent (the final user value deliverer) NEVER crashes and ALWAYS provides actionable insights through intelligent failure recovery and data_helper fallback routing.

## Business Value Justification (BVJ)

**Segment:** All (Free, Early, Mid, Enterprise)
**Business Goal:** Customer Experience & Retention  
**Value Impact:** 100% user value guarantee, zero-crash delivery
**Revenue Impact:** +30% retention through reliable AI-powered user value

## Team Structure & Parallel Execution

### Phase 1: Analysis & Design (Parallel)
- **Team A**: PM Agent - Requirements & BVJ refinement
- **Team B**: Design Agent - Architecture & API contracts  
- **Team C**: QA Agent - Test strategy & failure scenarios

### Phase 2: Core Implementation (Sequential with Parallel Components)
- **Team D**: Unified User Value Implementation (ReportingSubAgent)
- **Team E**: Value Preservation Checkpoint System  
- **Team F**: Intelligent Value Completion Fallback

### Phase 3: Recovery & Adaptation (Parallel)
- **Team G**: Workflow Adaptation Implementation
- **Team H**: Monitoring & Alerting Setup
- **Team I**: Performance Optimization

## Critical Context Files (MANDATORY READING)

ALL AGENTS MUST READ:
1. `CLAUDE.md` - Sections 2.1 (Architecture), 3.6 (Refactoring), 6 (WebSocket)
2. `reporting_crash_audit_and_plan.md` - Complete crash analysis
3. `USER_CONTEXT_ARCHITECTURE.md` - Factory patterns for isolation
4. `MISSION_CRITICAL_NAMED_VALUES_INDEX.xml` - Critical values
5. `DEFINITION_OF_DONE_CHECKLIST.md` - Reporting module section

## Success Criteria

1. **Zero Hard Crashes**: User value delivery (ReportingSubAgent) MUST NOT crash
2. **100% Value Guarantee**: Every request delivers meaningful user value
3. **Automatic Fallback**: Failed value generation triggers data_helper automatically
4. **<5 Second Recovery**: From failure to value delivery
5. **Backward Compatible**: Existing workflows continue functioning

## Delegation Instructions

### For Principal Engineer:

1. **Spawn Team A, B, C simultaneously** for Phase 1
2. **Wait for Phase 1 completion** (all three teams)
3. **Spawn Team D, E, F** for Phase 2 core implementation
4. **Monitor progress** via checkpoint reports
5. **Spawn Team G, H, I** for Phase 3 recovery features
6. **Integrate all outputs** into final implementation

### Critical Coordination Points:

1. **API Contracts** (Team B) → Implementation Teams (D, E, F)
2. **Test Scenarios** (Team C) → All implementation teams
3. **Checkpoint Format** (Team E) → Value Delivery (Team D) & Recovery (Team G)
4. **Failure Detection** (Team D) → Fallback Routing (Team F)

## Firewall Technique Requirements

When delegating to agents, provide ONLY:
- Specific task scope
- Required interfaces (not implementations)
- Input/output contracts
- Test acceptance criteria

DO NOT provide:
- Full codebase context
- Unrelated module implementations  
- Global state information

## Progress Tracking

Each team MUST produce:
1. **Checkpoint Report** every 2 hours
2. **Completion Report** with artifacts
3. **Integration Notes** for handoffs
4. **Test Results** for their component

## Risk Mitigation

1. **No Breaking Changes**: All modifications MUST be backward compatible
2. **Incremental Deployment**: Each phase independently deployable
3. **Feature Flags**: New behavior behind configuration toggles
4. **Rollback Plan**: Each change reversible within 5 minutes

## Final Integration Checklist

- [ ] All WebSocket events preserved (agent_started, thinking, tool_executing, completed)
- [ ] Factory patterns maintained for user isolation
- [ ] Real service tests passing (no mocks)
- [ ] Performance benchmarks met (<100ms overhead)
- [ ] Documentation updated
- [ ] Monitoring configured
- [ ] Rollback tested

## Execution Command

```bash
# Start parallel execution
python scripts/spawn_uvs_teams.py --phase 1 --parallel

# Monitor progress
python scripts/monitor_team_progress.py --project uvs

# Run integration tests
python tests/mission_critical/test_uvs_suite.py --real-services
```

## CRITICAL REMINDERS

1. **Multi-user System**: Consider concurrent execution at all times
2. **Race Conditions**: Plan for async/WebSocket concurrency
3. **95% First**: Handle common cases before edge cases
4. **Delete vs Fix**: Remove ugly tests rather than add complexity
5. **Business Value**: Always tie back to user value delivery

Start with Team A, B, C prompts in parallel for maximum efficiency.