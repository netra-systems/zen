# SSOT-AgentState-DuplicateDeepAgentStateDefinitions

**Priority**: P0 - CRITICAL (Blocking Golden Path)
**Issue Type**: SSOT Violation - Agent State Management
**Status**: ISSUE CREATED
**Created**: 2025-09-13
**GitHub Issue**: https://github.com/netra-systems/netra-apex/issues/871

## Problem Statement

**CRITICAL SSOT VIOLATION**: Duplicate DeepAgentState class definitions causing Golden Path failures and user data isolation risks.

### Primary Conflict
- **DEPRECATED**: `netra_backend/app/agents/state.py:164` - Marked for removal but still widely used
- **SSOT SOURCE**: `netra_backend/app/schemas/agent_models.py:119` - "Unified Deep Agent State - single source of truth"

### Business Impact on Golden Path
- **User Isolation Risk**: Deprecated version creates data leakage risks between users
- **Runtime Errors**: Agents fail with "'DeepAgentState' object has no attribute 'thread_id'"
- **Schema Fragmentation**: Different system parts use different DeepAgentState definitions
- **Security Risk**: Deprecated version warns "USER DATA AT RISK: This pattern may cause data leakage between users"

## Files Using DEPRECATED Version (20+ files to migrate)
- `netra_backend/app/agents/artifact_validator.py:16`
- `netra_backend/app/agents/agent_lifecycle.py:12`
- `netra_backend/app/agents/data_sub_agent/__init__.py:10`
- `netra_backend/app/agents/github_analyzer/agent.py:31`
- `netra_backend/app/agents/corpus_admin/agent.py:20`
- Plus 15+ more files requiring migration

## Files Using CORRECT SSOT Version
- `netra_backend/app/schemas/agent_models.py:119` (Authoritative source)
- `netra_backend/app/agents/synthetic_data_sub_agent.py:21`

## Secondary SSOT Violations Discovered
1. **ExecutionEngineFactory duplication** (P1)
2. **AgentRegistry duplication** (P1)

## Test Discovery Status ✅ COMPLETE
- [x] **Existing Tests Found**: 161 test files requiring SSOT import updates
- [x] **Test Categories**: Unit (16), Integration (16), Mission Critical validation
- [x] **Execution Strategy**: No Docker - unit/integration/staging GCP only
- [x] **Test Plan**: 32 new tests (8 failing + 8 unit + 16 integration)

### Test Execution Strategy (No Docker Requirements)
- **Unit Tests**: `python tests/unified_test_runner.py --category unit --test-pattern "*deepagentstate*"`
- **Integration**: `python tests/unified_test_runner.py --category integration --test-pattern "*agent_state_ssot*" --env staging`
- **Mission Critical**: `python tests/mission_critical/test_websocket_agent_events_suite.py`

### Test Implementation Priority
1. **Phase 1**: 8 failing tests proving SSOT violation exists
2. **Phase 2**: 8 unit tests validating SSOT DeepAgentState
3. **Phase 3**: 16 integration/security tests
4. **Phase 4**: Update 161 existing tests to use SSOT imports

## Remediation Plan Status
- [ ] Migration strategy for 20+ files using deprecated version
- [ ] Test validation for SSOT compliance
- [ ] Runtime verification of Golden Path functionality

## Progress Log
- **2025-09-13**: Initial discovery via SSOT Gardener audit
- **2025-09-13**: Test discovery complete - 161 existing tests + 32 new tests planned