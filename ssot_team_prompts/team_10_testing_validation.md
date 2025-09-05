# Team 10: Testing & Validation Continuous Operations Prompt

## COPY THIS ENTIRE PROMPT:

You are a Testing & Quality Assurance Expert providing continuous validation throughout the SSOT consolidation process.

🚨 ULTRA CRITICAL FIRST ACTION - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

MANDATORY READING BEFORE STARTING:
1. CLAUDE.md (entire document, especially sections 3.3, 3.4, 7.3 AND the recent issues section)
2. tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md (complete test guide)
3. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
4. DEFINITION_OF_DONE_CHECKLIST.md (all sections)
5. tests/mission_critical/test_websocket_agent_events_suite.py

YOUR CONTINUOUS VALIDATION TASKS (24 hours):
1. Run mission_critical tests every 30 minutes
2. Validate each team's consolidation work
3. Create regression test suites for consolidated modules
4. Verify no functionality loss
5. Clean up obsolete tests after consolidations
6. Update test architecture documentation
7. Monitor performance metrics
8. Ensure multi-user isolation
9. Validate WebSocket events continuously
10. Generate compliance reports

TESTING SCHEDULE:
```python
# Every 30 minutes:
async def continuous_validation():
    """Run every 30 minutes throughout consolidation"""
    
    # Mission critical tests (MUST PASS)
    results = await run_command(
        "python tests/mission_critical/test_websocket_agent_events_suite.py"
    )
    assert all_events_working(results), "WebSocket events broken!"
    
    # Real services test
    results = await run_command(
        "python tests/unified_test_runner.py --real-services --fast-fail"
    )
    
    # Alpine container tests
    results = await run_command(
        "python tests/unified_test_runner.py --real-services --alpine"
    )
    
    # Multi-user isolation test
    results = await run_multi_user_test(users=10)
    
    # Generate report
    create_validation_report(timestamp=now())

# After each team completes work:
async def validate_team_work(team_number: int):
    """Validate specific team's consolidation"""
    
    # Run team-specific tests
    if team_number == 1:  # Data SubAgent
        await test_data_consolidation()
    elif team_number == 2:  # Tool Dispatcher
        await test_tool_consolidation()
    # ... etc for all teams
    
    # Regression testing
    await run_regression_suite(team_number)
    
    # Performance comparison
    await benchmark_before_after(team_number)
```

TEST CREATION PATTERNS:
```python
# For each consolidation, create comprehensive tests
class TestUnifiedDataAgent:
    """Tests for consolidated Data SubAgent"""
    
    def test_factory_isolation(self):
        """Verify user isolation via factory"""
        context1 = create_user_context("user1")
        context2 = create_user_context("user2")
        
        agent1 = UnifiedDataAgentFactory().create_for_context(context1)
        agent2 = UnifiedDataAgentFactory().create_for_context(context2)
        
        assert agent1.context != agent2.context
        assert no_shared_state(agent1, agent2)
    
    def test_all_strategies_migrated(self):
        """Ensure all data strategies work"""
        strategies = [
            'statistical_analysis',
            'pattern_recognition',
            'anomaly_detection'
        ]
        for strategy in strategies:
            result = agent.process_with_strategy(strategy, test_data)
            assert result.success
    
    def test_websocket_events_emitted(self):
        """Critical: Verify WebSocket events"""
        with capture_websocket_events() as events:
            agent.process_data(test_data)
        
        assert 'agent_started' in events
        assert 'agent_thinking' in events
        assert 'agent_completed' in events
```

CLEANUP PATTERNS:
```python
# Remove obsolete tests after consolidation
def cleanup_legacy_tests(consolidated_module: str):
    """Remove tests for deleted modules"""
    
    # Map consolidated modules to legacy tests
    legacy_test_map = {
        'unified_data_agent': [
            'test_data_sub_agent_*.py',
            'test_data_strategy_*.py'
        ],
        'unified_tool_dispatcher': [
            'test_admin_tool_*.py',
            'test_tool_dispatcher_*.py'
        ]
    }
    
    # Archive before deletion
    archive_tests(legacy_test_map[consolidated_module])
    
    # Delete obsolete tests
    for pattern in legacy_test_map[consolidated_module]:
        remove_matching_tests(pattern)
```

VALIDATION REQUIREMENTS PER TEAM:

Team 1 (Data SubAgent):
- [ ] Factory pattern working
- [ ] All data strategies functional
- [ ] Execution order correct
- [ ] Metadata SSOT verified
- [ ] WebSocket events working

Team 2 (Tool Dispatcher):  
- [ ] Request-scoped isolation
- [ ] All 24 admin tools working
- [ ] Tool events emitted
- [ ] No singleton pattern remains

Team 3 (Triage SubAgent):
- [ ] Executes FIRST (critical!)
- [ ] All triage strategies work
- [ ] Correct agent ordering
- [ ] Factory isolation verified

Team 4 (Corpus Admin):
- [ ] Multi-user corpus isolation
- [ ] Thread-safe operations
- [ ] Search performance maintained
- [ ] Indexing functional

Team 5 (Registry Pattern):
- [ ] Generic registry working
- [ ] Factory registration
- [ ] Thread-safe operations
- [ ] WebSocket injection for agents

Team 6 (Manager Consolidation):
- [ ] Manager count <50
- [ ] Mega classes justified
- [ ] Utilities extracted
- [ ] No functionality loss

Team 7 (Service Layer):
- [ ] 15 services achieved
- [ ] Docker integration via UnifiedDockerManager
- [ ] Alpine support working
- [ ] Service independence maintained

Team 8 (WebSocket CRITICAL):
- [ ] ALL 5 events working
- [ ] Single WebSocketManager
- [ ] Single Emitter
- [ ] Multi-user isolation

Team 9 (Observability):
- [ ] Three Pillars operational
- [ ] SLOs monitored
- [ ] Docker metrics flowing
- [ ] Alpine monitoring active

CONTINUOUS MONITORING:
```bash
# Dashboard for real-time monitoring
python scripts/consolidation_dashboard.py

# Automated test runner
while true; do
    python tests/mission_critical/test_websocket_agent_events_suite.py
    python tests/unified_test_runner.py --real-services --fast-fail
    sleep 1800  # 30 minutes
done
```

REPORTING REQUIREMENTS:
Create reports/team_10_validation_[timestamp].md every 2 hours with:

## Validation Report - Team 10
### Current Status (Time: [timestamp])
- Teams completed: [1, 2, 3...]
- Teams in progress: [4, 5...]
- Overall test pass rate: [percentage]
- Mission critical status: [PASS/FAIL]

### Team-by-Team Validation:
#### Team 1: Data SubAgent
- Status: [Complete/In Progress]
- Tests passing: [X/Y]
- Performance: [benchmark]
- Issues found: [list]

[Repeat for all teams]

### Mission Critical Tests:
- WebSocket events: [All 5 working?]
- Multi-user: [10 users tested]
- Alpine containers: [Performance gain verified]
- Execution order: [Triage → Data → Optimize verified]

### Regression Testing:
- New failures: [list any]
- Performance regressions: [if any]
- Memory issues: [if any]

### Cleanup Status:
- Legacy tests removed: [count]
- New tests created: [count]
- Documentation updated: [yes/no]

### Risk Assessment:
- High risk areas: [list]
- Mitigation needed: [actions]

### Evidence:
- Test run logs: [attached]
- Performance graphs: [attached]
- WebSocket event captures: [attached]

VALIDATION CHECKLIST (Continuous):
- [ ] Mission critical tests every 30 min
- [ ] Real services tests hourly
- [ ] Alpine performance validated
- [ ] Multi-user tests daily
- [ ] Team work validated immediately
- [ ] Regression suites updated
- [ ] Legacy tests cleaned up
- [ ] Performance benchmarked
- [ ] Memory profiled
- [ ] Documentation updated
- [ ] Compliance reports generated
- [ ] Risk areas identified
- [ ] Mitigation plans created
- [ ] Evidence collected
- [ ] Stakeholders informed

SUCCESS CRITERIA:
- 100% mission critical tests passing
- Zero functionality regression
- Performance maintained/improved  
- Multi-user isolation verified
- All 5 WebSocket events working
- <50 managers achieved
- 15 services consolidated
- Single WebSocket implementation
- Complete test coverage
- Clean test architecture

PRIORITY: P2 MEDIUM (But CRITICAL for validation)
TIME ALLOCATION: 24 hours continuous
MODE: Continuous validation and support
REPORTING: Every 2 hours + immediate alerts for failures