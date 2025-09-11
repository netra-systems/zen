# SSOT-dual-systems-unified-id-manager-conflict

**GitHub Issue**: [#301](https://github.com/netra-systems/netra-apex/issues/301)  
**Status**: In Progress - Discovery Complete  
**Priority**: P0 CRITICAL - Golden Path Blocker  
**Business Impact**: $500K+ ARR at risk from WebSocket failures

## Issue Summary

Dual ID management systems (UnifiedIDManager vs UnifiedIdGenerator) creating severe SSOT violations that impact Golden Path functionality and system stability.

## Key Findings from SSOT Audit

### Critical Violations Identified

1. **Dual SSOT Systems (P0 CRITICAL)**
   - `netra_backend/app/core/unified_id_manager.py` (821 lines) - Primary SSOT
   - `shared/id_generation/unified_id_generator.py` (590 lines) - Competing SSOT
   - 265+ files use UnifiedIdGenerator vs 29+ files use UnifiedIDManager

2. **WebSocket Resource Cleanup Failures (P0 CRITICAL)**
   - ID pattern mismatches: `thread_{operation}_{counter}_{random}` vs `run_{thread_id}_{timestamp}_{uuid}`
   - Causing WebSocket 1011 errors and memory leaks
   - Direct Golden Path impact

3. **Cross-Service Import Conflicts (P0 CRITICAL)**
   - Auth service uses UnifiedIdGenerator exclusively
   - netra_backend uses UnifiedIDManager for core functionality
   - Authentication context mismatches possible

4. **Custom ID Generators (P1 HIGH)**
   - `transaction_stats.py:83` - Custom transaction ID generation
   - `connection_id_manager.py:344` - Environment-specific ID generation
   - Multiple alert ID generators

## Remediation Plan

### Phase 1: IMMEDIATE (Golden Path Blockers)
- [ ] Standardize WebSocket ID generation patterns
- [ ] Fix thread_id/run_id consistency 
- [ ] Resolve cross-service import conflicts
- [ ] Create compatibility layer for migration

### Phase 2: HIGH PRIORITY (System Stability)
- [ ] Eliminate custom ID generators
- [ ] Ensure service boundary compliance
- [ ] Validate cross-service ID compatibility

### Phase 3: MEDIUM PRIORITY (Test Infrastructure)
- [ ] Replace direct UUID usage in tests
- [ ] Standardize test ID generation patterns

## Test Plan Status
- [ ] Discover existing tests protecting ID management
- [ ] Plan new SSOT validation tests  
- [ ] Execute test plan for new SSOT tests
- [ ] Run test fix loop until all pass

## Progress Log

### 2025-09-10 - Discovery Complete
- ✅ Comprehensive SSOT audit completed
- ✅ GitHub issue #301 created
- ✅ Local progress tracker established
- 🔄 Next: Test discovery and planning

## Notes
- Recommend keeping UnifiedIDManager as primary SSOT (more comprehensive features)
- Need backward compatibility during migration
- Monitor Golden Path WebSocket functionality throughout remediation