# SSOT Remediation: ReportingSubAgent JSON Handling Migration

**Issue:** [#187 - incomplete-migration-reporting-agent-json-handling](https://github.com/netra-systems/netra-apex/issues/187)
**Created:** 2025-01-09
**Status:** DISCOVERY COMPLETE
**Priority:** CRITICAL - Affects Golden Path

## Problem Summary

ReportingSubAgent bypasses SSOT JSON handling infrastructure, creating inconsistent parsing behavior that affects the golden path (users login → get AI responses).

### Critical Files
- **Violation:** `/netra_backend/app/agents/reporting_sub_agent.py:343-362`
- **SSOT Target:** `/netra_backend/app/core/unified_json_handler.py`

## SSOT Violations Identified

1. **Custom JSON Parsing** (Lines 343-362)
   - Duplicate implementation of JSON parsing logic
   - Different error handling from SSOT patterns
   - Potential for inconsistent behavior

2. **Bypass SSOT Imports** (Lines 17-20)
   - Direct JSON parsing instead of using `LLMResponseParser`
   - Missing integration with unified error handling

3. **Cache Helper Instantiation** (Line 699)
   - `self._cache_helper = CacheHelpers(None)` bypasses proper cache management
   - Creates potential cache inconsistencies

## Golden Path Impact

This violation directly affects user experience when:
- Users request AI-generated reports
- Agents process and return JSON responses
- WebSocket events deliver report results
- Error conditions occur during report generation

## Progress Tracking

### Phase 0: DISCOVERY ✅ COMPLETE
- [x] SSOT audit conducted
- [x] GitHub issue created (#187)
- [x] Progress tracker established

### Phase 1: TEST DISCOVERY & PLANNING 🔄 IN PROGRESS
- [ ] Find existing tests protecting ReportingSubAgent
- [ ] Plan new SSOT compliance tests
- [ ] Identify test gaps for JSON handling
- [ ] Document test execution strategy

### Phase 2: TEST EXECUTION 🔄 PENDING
- [ ] Create failing tests for SSOT compliance
- [ ] Run existing tests to establish baseline
- [ ] Implement new SSOT validation tests

### Phase 3: REMEDIATION PLANNING 🔄 PENDING
- [ ] Plan migration to LLMResponseParser
- [ ] Plan cache helper integration
- [ ] Document breaking change impact

### Phase 4: REMEDIATION EXECUTION 🔄 PENDING
- [ ] Replace custom JSON parsing with SSOT
- [ ] Integrate proper cache management
- [ ] Update imports and dependencies

### Phase 5: VALIDATION 🔄 PENDING
- [ ] All existing tests pass
- [ ] New SSOT tests pass
- [ ] Golden path validation
- [ ] No regression in report functionality

### Phase 6: PR & CLOSURE 🔄 PENDING
- [ ] Create pull request
- [ ] Link to issue #187
- [ ] Code review and merge

## Notes

- **Business Impact:** High - affects primary user workflows
- **Technical Debt:** Medium - manageable migration scope
- **Risk Level:** Low - well-defined SSOT patterns to follow

## Next Steps

1. Spawn subagent for test discovery and planning
2. Focus on non-Docker tests (unit, integration, staging e2e)
3. Ensure backward compatibility during migration

---
*This document tracks progress for SSOT Gardener remediation process*