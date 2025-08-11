# Coverage Analysis Report - August 11, 2025

## Executive Summary

**Backend Coverage: 20.39%** (2,901 covered / 14,225 total lines)
- Missing lines: 11,324
- Target: 97% (per SPEC/testing.xml)
- Gap: 76.61%

## Top 20 Testing Issues to Fix

### Test Collection Errors (Fix First)
1. **test_super_e2e.py** - IndentationError on line 128
2. **test_system_startup.py** - ImportError: TestingConfig not found

### Files with Zero Coverage (Critical Services)
3. **app/services/quality_gate_service.py** - 370 lines uncovered
4. **app/services/quality_monitoring_service.py** - 325 lines uncovered  
5. **app/core/async_utils.py** - 273 lines uncovered
6. **app/core/fallback_handler.py** - 258 lines uncovered
7. **app/core/schema_sync.py** - 258 lines uncovered
8. **app/startup_checks.py** - 228 lines uncovered
9. **app/agents/supply_researcher_sub_agent.py** - 213 lines uncovered
10. **app/core/resource_manager.py** - 209 lines uncovered
11. **app/core/type_validation.py** - 194 lines uncovered
12. **app/services/mcp_service.py** - 192 lines uncovered

### Files with Low Coverage (High Impact)
13. **app/agents/data_sub_agent.py** - 16.1% coverage (344 lines missing)
14. **app/services/generation_service.py** - 16.5% coverage (192 lines missing)
15. **app/agents/triage_sub_agent.py** - 30.1% coverage (218 lines missing)
16. **app/services/synthetic_data_service.py** - 25.0% coverage (168 lines missing)
17. **app/ws_manager.py** - 26.2% coverage (166 lines missing)

### Other Critical Components
18. **app/services/supply_research_scheduler.py** - 191 lines uncovered
19. **app/services/supply_research_service.py** - 189 lines uncovered
20. **app/services/tool_permission_service.py** - 175 lines uncovered

## Fix Priority Order

1. Fix test collection errors first (prevents all tests from running)
2. Add tests for critical zero-coverage services (quality, monitoring, startup)
3. Improve coverage for core utilities (async, fallback, resource management)
4. Enhance agent testing (data, triage, supply researcher)
5. Complete service layer testing (generation, MCP, synthetic data)

## Notes
- Backend test runner properly integrates coverage reporting
- Frontend coverage reporting is also integrated
- Coverage reports saved to: reports/coverage/ and reports/frontend-coverage/
- Test reports saved to: test_reports/ with timestamps