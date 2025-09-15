# Agents Unit Test Coverage Improvement Plan

**Agent Session:** agent-session-2025-09-13-1957
**Date:** 2025-09-13
**Current Coverage:** 7.13% (1,744/24,446 lines)
**GitHub Issue:** #872

## Executive Summary

The agents area has critical coverage gaps that pose risks to our $500K+ ARR dependency on agent functionality. While 276 test files exist, many have import issues preventing execution. This plan outlines a systematic approach to achieve 35% coverage over 6-8 weeks.

## Current State Analysis

### Coverage Statistics
- **Total Agent Source Files:** 250 Python files
- **Total Lines of Code:** 24,446 lines in agents directory
- **Current Coverage:** 7.13% (from working base_agent_initialization tests)
- **Working Tests:** ~180 tests (estimated from functional test suites)
- **Broken Tests:** 14+ test files with DeepAgentState import errors

### Critical Gaps
1. **0% Coverage Modules (117+ files):** Most agent modules have no test coverage
2. **Infrastructure Modules:** All supervisor/* modules uncovered (critical for Golden Path)
3. **Core Modules:** base_agent.py at only 28.66% despite being 2,661 lines
4. **Import Issues:** DeepAgentState migration broke 14+ test files

## Phase 1: Foundation Fixes (Target: 15% coverage)
**Timeline:** 1-2 weeks
**Priority:** P0 - Blocking

### 1.1 Import Error Resolution (Critical)
**Problem:** 14 test files failing with DeepAgentState import errors
```
ImportError: cannot import name 'DeepAgentState' from 'netra_backend.app.agents.state'
```

**Solution:** Update imports to SSOT location:
```python
# OLD (broken):
from netra_backend.app.agents.state import DeepAgentState

# NEW (correct):
from netra_backend.app.schemas.agent_models import DeepAgentState
```

**Affected Files:**
- test_agent_lifecycle_core.py
- test_corpus_admin_unit.py
- test_llm_agent_advanced_integration.py
- test_llm_agent_integration_core.py
- test_llm_agent_integration_fixtures.py
- test_supervisor_consolidated_core.py
- test_supervisor_routing.py
- test_supply_researcher_agent_core.py
- test_synthetic_data_unit.py
- test_tool_dispatcher_advanced_operations.py
- 4 additional test files with similar issues

### 1.2 High-Impact Core Module Coverage

#### base_agent.py (Priority 1)
- **Current:** 28.66% (763/2,661 lines covered)
- **Target:** 60% coverage
- **Focus Areas:**
  - Factory pattern validation
  - User context isolation
  - WebSocket integration
  - Error handling and recovery
  - Lifecycle management
- **Tests Needed:** 15-20 additional unit tests
- **Business Impact:** Core agent functionality protection

#### registry.py (Priority 2)
- **Current:** 0% coverage (185 lines)
- **Target:** 40% coverage
- **Focus Areas:**
  - Agent registration and discovery
  - SSOT compliance validation
  - Lifecycle state management
  - Error handling
- **Tests Needed:** 8-12 new unit tests
- **Business Impact:** Agent routing and discovery protection

#### agent_communication.py (Priority 3)
- **Current:** 0% coverage (129 lines)
- **Target:** 30% coverage
- **Focus Areas:**
  - Inter-agent message routing
  - Communication protocols
  - Error propagation
- **Tests Needed:** 6-10 new unit tests
- **Business Impact:** Multi-agent workflow protection

## Phase 2: Infrastructure Coverage (Target: 25% coverage)
**Timeline:** 2-3 weeks
**Priority:** P1 - High

### 2.1 Supervisor Module Suite (Critical Infrastructure)
All supervisor/* modules currently have 0% coverage, representing critical Golden Path infrastructure.

#### user_execution_engine.py (Priority 1)
- **Current:** 13.72% (87/634 lines covered)
- **Target:** 50% coverage
- **Focus:** User isolation, execution context, factory patterns
- **Business Impact:** Multi-user safety and performance

#### agent_execution_core.py (Priority 2)
- **Current:** 10.37% (34/328 lines covered)
- **Target:** 45% coverage
- **Focus:** Core execution logic, error handling, state management

#### execution_engine_factory.py (Priority 3)
- **Current:** 15.38% (44/286 lines covered)
- **Target:** 40% coverage
- **Focus:** Factory pattern validation, instance creation, cleanup

### 2.2 Tool Integration Coverage
Critical for tool execution and WebSocket event delivery.

#### unified_tool_execution.py
- **Current:** 10.78% (51/473 lines covered)
- **Target:** 45% coverage
- **Tests Needed:** Tool execution validation, error handling, WebSocket integration

#### tool_executor_factory.py
- **Current:** 0% coverage (163 lines)
- **Target:** 30% coverage
- **Tests Needed:** Factory pattern validation, tool lifecycle management

## Phase 3: Specialized Agent Coverage (Target: 35% coverage)
**Timeline:** 3-4 weeks
**Priority:** P2 - Medium

### 3.1 Domain Expert Modules (15 modules, all 0% coverage)
- **base_expert.py:** 65 lines → Target 25% coverage
- **business_expert.py:** 30 lines → Target 20% coverage
- **engineering_expert.py:** 30 lines → Target 20% coverage
- **finance_expert.py:** 27 lines → Target 20% coverage

### 3.2 Synthetic Data Pipeline (20+ modules, all 0% coverage)
- **core.py:** 232 lines → Target 30% coverage
- **approval_flow.py:** 53 lines → Target 25% coverage
- **generation_workflow.py:** 58 lines → Target 25% coverage

### 3.3 GitHub Analyzer Suite (25+ modules, all 0% coverage)
- **agent.py:** 181 lines → Target 20% coverage
- **scanner_core.py:** 206 lines → Target 15% coverage
- **pattern_matcher.py:** 66 lines → Target 20% coverage

## Implementation Strategy

### Development Approach
1. **Fix First:** Resolve all import errors before new test development
2. **High ROI Focus:** Prioritize modules with highest business impact
3. **Factory Pattern Emphasis:** Ensure user isolation and multi-user safety
4. **Real Services:** No mocks in integration-style unit tests
5. **WebSocket Validation:** Ensure event delivery in all agent tests

### Test Infrastructure Requirements
- **Base Test Classes:** Use existing SSOT BaseTestCase
- **Mock Management:** Leverage SSOT MockFactory for consistency
- **Environment:** Use IsolatedEnvironment for configuration access
- **Coverage Tools:** pytest-cov with HTML reporting
- **CI Integration:** Coverage reporting in all pull requests

### Success Metrics
- **Coverage Progression:** 7.13% → 15% → 25% → 35% over 6-8 weeks
- **Test Count Growth:** ~180 → 400+ functional unit tests
- **Import Error Resolution:** 0 test collection failures due to imports
- **Golden Path Protection:** Complete supervisor module coverage
- **Business Value:** $500K+ ARR agent functionality comprehensive coverage

### Risk Mitigation
- **Incremental Approach:** Phase-based implementation reduces integration risk
- **Continuous Validation:** Weekly coverage reports and trend analysis
- **Import Management:** Central tracking of SSOT migration impacts
- **Performance Monitoring:** Test execution time optimization
- **Documentation:** Comprehensive test documentation and examples

## Next Steps

1. **Immediate (Week 1):** Fix all DeepAgentState import errors
2. **Short-term (Weeks 1-2):** Achieve 15% coverage with core module focus
3. **Medium-term (Weeks 3-4):** Infrastructure coverage to 25%
4. **Long-term (Weeks 5-8):** Specialized agent coverage to 35%

**Champion Required:** Dedicated developer for 6-8 weeks to execute this plan systematically.

---

*Generated by agent-session-2025-09-13-1957 | GitHub Issue #872*