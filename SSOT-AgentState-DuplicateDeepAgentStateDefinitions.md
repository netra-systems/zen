# SSOT-AgentState-DuplicateDeepAgentStateDefinitions

**Priority**: P0 - CRITICAL (Blocking Golden Path)
**Issue Type**: SSOT Violation - Agent State Management
**Status**: DISCOVERED
**Created**: 2025-09-13

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

## Test Discovery Status
- [ ] Existing tests protecting DeepAgentState functionality
- [ ] Integration tests validating agent state consistency
- [ ] User isolation tests for multi-user scenarios

## Remediation Plan Status
- [ ] Migration strategy for 20+ files using deprecated version
- [ ] Test validation for SSOT compliance
- [ ] Runtime verification of Golden Path functionality

## Progress Log
- **2025-09-13**: Initial discovery via SSOT Gardener audit