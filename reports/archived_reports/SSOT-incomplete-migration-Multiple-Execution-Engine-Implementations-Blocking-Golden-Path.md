# SSOT-incomplete-migration-Multiple Execution Engine Implementations Blocking Golden Path

**GitHub Issue**: [#859](https://github.com/netra-systems/netra-apex/issues/859)
**Priority**: P0 (Critical/blocking)
**Created**: 2025-01-13
**Status**: Step 0 Complete - SSOT Audit Complete

## Problem Summary

**CRITICAL SSOT Violation**: Multiple execution engine classes violating Single Source of Truth principle, causing WebSocket user isolation failures and security vulnerabilities that directly block the Golden Path.

## Files Involved

### SSOT Implementation (TARGET)
- `/netra_backend/app/agents/supervisor/user_execution_engine.py:239` - **UserExecutionEngine** (SSOT target)

### DEPRECATED/LEGACY (TO REMOVE)
- `/netra_backend/app/agents/supervisor/execution_engine.py` - DEPRECATED but still used
- `/netra_backend/app/agents/execution_engine_legacy_adapter.py:42` - SupervisorExecutionEngineAdapter
- `/netra_backend/app/agents/execution_engine_legacy_adapter.py:164` - ConsolidatedExecutionEngineWrapper
- `/netra_backend/app/agents/execution_engine_unified_factory.py:41` - UnifiedExecutionEngineFactory
- `/netra_backend/app/agents/base/executor.py:266` - BaseExecutionEngine

## Golden Path Impact (BLOCKING CRITICAL)

- **USER ISOLATION FAILURES**: WebSocket messages delivered to wrong users
- **SECURITY RISK**: Race conditions in concurrent user scenarios
- **MEMORY LEAKS**: Legacy engines persist state between user sessions
- **$500K+ ARR AT RISK**: Chat functionality reliability compromised

## Remediation Plan

### Success Criteria
- [ ] Single `UserExecutionEngine` as SSOT for all agent execution
- [ ] Remove all legacy adapters and deprecated engines
- [ ] Update 100+ references to use single engine
- [ ] Zero WebSocket user isolation failures in testing

### Effort Estimate
**HIGH** (3-5 days) - Requires careful migration of all execution patterns

## Process Progress

- [x] **Step 0: SSOT Audit Complete** - Identified critical execution engine SSOT violation
- [x] **Step 1: Discover and Plan Tests Complete** - 22 existing tests found, 6-8 new tests planned
- [ ] Step 2: Execute Test Plan (20% new SSOT tests)
- [ ] Step 3: Plan Remediation
- [ ] Step 4: Execute Remediation
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR and Closure

## Test Discovery Status

**Status**: COMPLETE ✅
- **Existing tests found**: 22 test files, 169 mission critical tests protecting execution engine functionality
- **Test coverage**: EXCELLENT - UserExecutionEngine has comprehensive coverage for WebSocket integration, user isolation, concurrent execution
- **Gap analysis**: Missing SSOT violation reproduction tests and multi-engine failure scenarios

### 🏆 Existing Test Coverage (Strong Foundation)
- **UserExecutionEngine Core**: 8 focused test files with 85%+ coverage
- **WebSocket Integration**: Comprehensive event delivery and bridge testing
- **User Isolation**: 15+ tests validating concurrent user scenarios
- **Memory Management**: Multi-user execution and cleanup validation
- **Mission Critical**: 169 tests protecting $500K+ ARR Golden Path functionality

### 🎯 New Test Plan (20% Effort - 6-8 Test Files)

#### FAILING Tests (Prove SSOT Violation):
1. `test_issue_859_multiple_engine_user_isolation_violations.py` - WebSocket messages to wrong users
2. `test_issue_859_memory_leaks_legacy_engines.py` - Persistent state between users
3. `test_issue_859_race_conditions_concurrent_users.py` - Race conditions in multi-engine scenarios

#### SUCCESS Tests (Validate Remediation):
4. `test_issue_859_single_engine_user_isolation_success.py` - Single UserExecutionEngine isolation
5. `test_issue_859_memory_cleanup_validation.py` - Clean memory management
6. `test_issue_859_websocket_routing_consistency.py` - Consistent WebSocket event delivery

#### Integration Tests:
7. `test_issue_859_golden_path_single_engine_integration.py` - End-to-end with single engine
8. `test_issue_859_concurrent_users_performance_validation.py` - 10+ concurrent users

### 📊 Test Execution Strategy
- **Unit Tests**: `python tests/unified_test_runner.py --category unit --pattern issue_859`
- **Integration**: `python tests/unified_test_runner.py --category integration --pattern issue_859 --real-services`
- **E2E Staging**: `python tests/unified_test_runner.py --category e2e --pattern issue_859 --env staging`

## Remediation Status

**Status**: Not Started
- Migration strategy: TBD
- Breaking changes assessment: TBD
- Rollback plan: TBD

## Notes

This is the #1 most critical SSOT violation in the agent system identified during the audit. Must be resolved before other agent SSOT issues to prevent cascading failures.