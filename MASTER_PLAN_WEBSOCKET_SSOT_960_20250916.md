# Master Plan: WebSocket Manager SSOT Consolidation
**Date:** 2025-09-16
**Original Issue:** #960
**Plan Author:** Claude

## Executive Summary

Issue #960 has become contaminated with infrastructure noise, automated alerts, and multiple failed attempts. The core problem remains valid: **11 duplicate WebSocket Manager implementations violating SSOT principles**. This master plan provides a clean, focused approach to resolve this architectural debt.

### Key Decision: Close #960 and Create Focused Issues

Rather than continue with the contaminated #960, we will:
1. Close #960 with clear documentation
2. Create 5 new atomic, focused issues
3. Execute a phased consolidation plan
4. Validate success with compliance monitoring

## The Core Problem

- **11 duplicate WebSocket Manager implementations** exist in production
- Each implementation has slight variations causing inconsistent behavior
- Multiple import paths create runtime fragmentation
- This violates SSOT principles and risks chat functionality (90% of business value)

## New Issue Structure

### Issue #[NEW-1]: WebSocket Manager SSOT Audit & Inventory

```markdown
### Title
WebSocket Manager SSOT Audit - Map All 11 Implementations

### Description
Conduct comprehensive audit of all WebSocket Manager implementations to establish baseline for SSOT consolidation.

### Background
As identified in #960, we have 11 duplicate WebSocket Manager implementations violating SSOT principles. Before consolidation, we need a complete inventory.

### Scope
- [ ] Identify all WebSocket Manager class definitions
- [ ] Map all import paths and usage patterns
- [ ] Document implementation differences
- [ ] Identify consumer services and dependencies
- [ ] Create comparison matrix of features/behaviors

### Success Criteria
- Complete inventory spreadsheet with all 11 implementations
- Dependency graph showing all consumers
- Feature comparison matrix
- Risk assessment for each implementation

### Deliverables
1. `docs/websocket_audit_results.md` with complete inventory
2. Mermaid diagram of current architecture
3. Recommendation for canonical implementation

### Links
- Closes part of #960
- Blocks: WebSocket SSOT Implementation (#[NEW-2])

### Labels
`ssot`, `websocket`, `architecture`, `audit`

### Estimate
2 days
```

### Issue #[NEW-2]: WebSocket Manager Canonical Implementation

```markdown
### Title
Implement Canonical WebSocket Manager with Factory Pattern

### Description
Create the single canonical WebSocket Manager implementation following SSOT principles.

### Background
Following audit (#[NEW-1]), implement the selected canonical WebSocket Manager with proper factory pattern for multi-user isolation.

### Scope
- [ ] Implement canonical manager in `/netra_backend/app/websocket_core/websocket_manager.py`
- [ ] Add factory pattern for user isolation
- [ ] Implement manager registry to prevent duplicates
- [ ] Add runtime SSOT validation
- [ ] Create comprehensive unit tests

### Technical Requirements
```python
# Canonical location ONLY
/netra_backend/app/websocket_core/websocket_manager.py

# Factory pattern
class WebSocketManagerFactory:
    """Ensures single instance per user context"""

# Registry pattern
class WebSocketManagerRegistry:
    """Prevents duplicate instantiation"""
```

### Success Criteria
- Single canonical implementation exists
- Factory pattern ensures user isolation
- Registry prevents duplicate instances
- All tests pass
- No runtime SSOT violations

### Links
- Depends on: #[NEW-1] (audit results)
- Closes part of #960
- Blocks: #[NEW-3] (migration)

### Labels
`ssot`, `websocket`, `implementation`, `golden-path`

### Estimate
3 days
```

### Issue #[NEW-3]: WebSocket Consumer Migration Sprint

```markdown
### Title
Migrate All Services to Canonical WebSocket Manager

### Description
Update all 11+ consumer services to use the canonical WebSocket Manager implementation.

### Background
With canonical implementation ready (#[NEW-2]), migrate all consumers to use single SSOT implementation.

### Migration Checklist
- [ ] Backend routes migration
- [ ] Agent system integration
- [ ] Tool execution engine
- [ ] Event notification system
- [ ] Test framework updates
- [ ] Frontend WebSocket client
- [ ] Admin dashboard
- [ ] Monitoring systems
- [ ] Docker configurations
- [ ] CI/CD pipelines
- [ ] Development scripts

### Migration Process
1. Update import statements
2. Verify factory pattern usage
3. Test each service
4. Remove legacy implementation
5. Validate no regression

### Success Criteria
- All imports use canonical path
- Zero references to legacy implementations
- All services tested and working
- 10+ duplicate files deleted
- Git history shows clean removal

### Links
- Depends on: #[NEW-2] (canonical implementation)
- Closes part of #960

### Labels
`ssot`, `websocket`, `migration`, `cleanup`

### Estimate
5 days
```

### Issue #[NEW-4]: WebSocket SSOT Compliance Monitoring

```markdown
### Title
Implement WebSocket SSOT Compliance Tests & Monitoring

### Description
Create comprehensive testing and monitoring to prevent WebSocket SSOT violations.

### Background
To prevent regression, we need automated validation and monitoring of SSOT compliance.

### Scope
- [ ] SSOT compliance test suite
- [ ] Runtime validation checks
- [ ] Import path verification
- [ ] CI/CD integration
- [ ] Production monitoring alerts
- [ ] Compliance dashboard

### Test Implementation
```python
# tests/mission_critical/test_websocket_ssot_compliance.py
class TestWebSocketSSOTCompliance:
    def test_single_implementation(self):
        """Verify only one WebSocket Manager exists"""

    def test_canonical_imports(self):
        """Verify all imports use canonical path"""

    def test_no_duplicate_instances(self):
        """Verify registry prevents duplicates"""
```

### Monitoring Setup
- GCP alert for SSOT violations
- Daily compliance reports
- Pre-deployment validation

### Success Criteria
- Test suite detects any SSOT violation
- CI/CD blocks deployments with violations
- Monitoring alerts on runtime violations
- Zero false positives

### Links
- Depends on: #[NEW-3] (migration complete)
- Closes monitoring aspect of #960

### Labels
`ssot`, `websocket`, `testing`, `monitoring`, `compliance`

### Estimate
3 days
```

### Issue #[NEW-5]: WebSocket Architecture Documentation

```markdown
### Title
Document WebSocket SSOT Architecture & Patterns

### Description
Create comprehensive documentation to prevent future SSOT violations.

### Background
Clear documentation ensures team understanding and prevents reintroduction of duplicate implementations.

### Deliverables
- [ ] Architecture decision record (ADR)
- [ ] Mermaid diagrams (current vs target)
- [ ] Developer guide for WebSocket usage
- [ ] Migration playbook for future changes
- [ ] SSOT principles documentation
- [ ] Code review checklist

### Documentation Structure
```
docs/websocket/
├── architecture.md (ADR with diagrams)
├── developer_guide.md (How to use WebSocket)
├── ssot_principles.md (Why and how)
├── migration_guide.md (For future changes)
└── code_review_checklist.md
```

### Success Criteria
- Complete documentation package
- Mermaid diagrams clear and accurate
- Team review and approval
- Integrated into onboarding
- Added to CLAUDE.md directives

### Links
- Depends on: #[NEW-3] (final architecture)
- Fully closes #960 documentation debt

### Labels
`documentation`, `ssot`, `websocket`, `architecture`

### Estimate
2 days
```

## Execution Timeline

### Phase 1: Foundation (Days 1-5)
- **Day 1-2:** Execute #[NEW-1] (Audit)
- **Day 3-5:** Execute #[NEW-2] (Canonical Implementation)

### Phase 2: Migration (Days 6-10)
- **Day 6-10:** Execute #[NEW-3] (Consumer Migration)

### Phase 3: Hardening (Days 11-15)
- **Day 11-13:** Execute #[NEW-4] (Compliance Monitoring)
- **Day 14-15:** Execute #[NEW-5] (Documentation)

## Success Metrics

### Technical Metrics
- **Before:** 11 duplicate implementations, multiple import paths
- **After:** 1 canonical implementation, single import path
- **Validation:** 100% SSOT compliance score
- **Cleanup:** 10+ files deleted, ~2000 lines removed

### Business Metrics
- **Reliability:** Zero WebSocket-related chat failures
- **Velocity:** 50% faster WebSocket feature development
- **Quality:** No SSOT architectural debt
- **Monitoring:** Real-time compliance validation

## Risk Mitigation

### Risk 1: Production Impact
- **Mitigation:** Phased rollout with feature flags
- **Rollback:** Keep legacy code until validation complete

### Risk 2: Missing Consumers
- **Mitigation:** Comprehensive audit in #[NEW-1]
- **Validation:** Runtime monitoring for legacy usage

### Risk 3: Behavior Differences
- **Mitigation:** Feature comparison matrix
- **Testing:** Comprehensive E2E validation

## Closing Issue #960

### Close Message for #960
```markdown
Closing this issue in favor of focused, atomic issues for WebSocket SSOT consolidation.

After thorough analysis, this issue has accumulated too much noise from:
- Infrastructure alerts mixing with code issues
- Multiple overlapping attempts (#885, #1182)
- Scope creep beyond original problem

The core problem remains valid and critical: 11 duplicate WebSocket Manager implementations violating SSOT principles.

### New Focused Issues Created:
- #[NEW-1] WebSocket Manager Audit & Inventory
- #[NEW-2] Canonical WebSocket Implementation
- #[NEW-3] Consumer Migration Sprint
- #[NEW-4] SSOT Compliance Monitoring
- #[NEW-5] Architecture Documentation

These atomic issues provide clear scope, dependencies, and success criteria without the contamination of #960's history.

See Master Plan: `MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md`
```

## Next Steps

### Immediate Actions (Today)
1. [ ] Review and approve this master plan
2. [ ] Create the 5 new issues in GitHub
3. [ ] Close #960 with reference to new issues
4. [ ] Assign team members to #[NEW-1]

### This Week
1. [ ] Complete WebSocket audit (#[NEW-1])
2. [ ] Begin canonical implementation (#[NEW-2])
3. [ ] Prepare migration checklist

### Success Checkpoint (Day 15)
- [ ] All 5 issues complete
- [ ] SSOT compliance achieved
- [ ] Monitoring active
- [ ] Documentation published
- [ ] Team trained on patterns

## Conclusion

This master plan transforms a contaminated, complex issue into 5 focused, executable tasks. By closing #960 and starting fresh, we:

1. **Eliminate noise** from infrastructure and history
2. **Provide clarity** with atomic, well-scoped issues
3. **Ensure completion** with clear dependencies
4. **Prevent regression** with monitoring and documentation
5. **Protect business value** by securing chat functionality

The phased approach ensures system stability while achieving complete SSOT compliance for WebSocket management.