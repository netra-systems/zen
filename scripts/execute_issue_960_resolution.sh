#!/bin/bash

# Execute Issue #960 Resolution - WebSocket SSOT Consolidation
# Date: 2025-09-16
# Purpose: Close contaminated issue #960 and create focused atomic issues
# Based on: ISSUE_UNTANGLE_960_20250916_claude.md and MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md

set -e

echo "=== Executing Issue #960 Resolution Plan ==="
echo "Purpose: Close contaminated issue and create focused WebSocket SSOT issues"
echo "Date: $(date)"
echo ""

# Store issue numbers as variables for cross-referencing
declare -A NEW_ISSUES

echo "Step 1: Creating Issue #1 - WebSocket Manager SSOT Architecture Audit"
NEW_ISSUE_1=$(gh issue create \
  --title "WebSocket Manager SSOT Architecture Audit - Map All 11 Implementations" \
  --label "ssot,websocket,architecture,audit,P1" \
  --body "$(cat <<'EOF'
## Problem Statement
The codebase currently has **11 duplicate WebSocket Manager implementations**, violating SSOT principles and creating reliability risks for chat functionality (90% of platform value).

## Background
As identified in Issue #960, we have multiple WebSocket Manager implementations causing:
- SSOT principle violations
- Inconsistent behavior across services
- Maintenance burden for updates
- Risk to chat functionality reliability

## Scope
Conduct comprehensive audit of all WebSocket Manager implementations to establish foundation for SSOT remediation.

## Tasks
- [ ] Inventory all 11 WebSocket Manager implementations with file paths
- [ ] Map dependencies and usage patterns for each implementation
- [ ] Create mermaid diagram of current fragmented architecture
- [ ] Design mermaid diagram of target SSOT architecture
- [ ] Analyze implementations to identify most complete/stable candidate
- [ ] Document selection criteria and rationale
- [ ] Assess migration risks and dependencies

## Success Criteria
- [ ] Complete inventory documented in `docs/websocket_architecture_audit.md`
- [ ] Current and target architecture diagrams created
- [ ] Canonical implementation selected with documented rationale
- [ ] Migration risk assessment completed
- [ ] Updated `SSOT_IMPORT_REGISTRY.md` with findings

## Deliverables
1. `docs/websocket_architecture_audit.md` with complete inventory
2. Mermaid diagram of current architecture
3. Mermaid diagram of target SSOT architecture
4. Recommendation for canonical implementation
5. Risk assessment and migration plan

## Definition of Done
- [ ] All WebSocket Manager implementations catalogued
- [ ] Architecture diagrams approved by team
- [ ] Canonical implementation selection documented
- [ ] Risk assessment completed and reviewed
- [ ] Foundation established for next phase

## Estimated Effort
3-5 days

## Links
- **Closes:** Part of #960 (WebSocket SSOT fragmentation)
- **Blocks:** WebSocket Manager SSOT Implementation Selection
- **Epic:** WebSocket SSOT Remediation

## Business Impact
Protects chat functionality (90% of platform value) by establishing foundation for reliable WebSocket management.

---
*Part of Issue #960 resolution plan - see `MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md`*
EOF
)")

NEW_ISSUES[1]=$NEW_ISSUE_1
echo "Created Issue #$NEW_ISSUE_1"

echo ""
echo "Step 2: Creating Issue #2 - WebSocket Manager SSOT Implementation"
NEW_ISSUE_2=$(gh issue create \
  --title "Implement Canonical WebSocket Manager with Factory Pattern" \
  --label "ssot,websocket,implementation,golden-path,P1" \
  --body "$(cat <<EOF
## Problem Statement
Need to establish single canonical WebSocket Manager implementation that handles all use cases from 11 duplicate implementations.

## Background
Following audit (Issue #${NEW_ISSUES[1]}), implement the selected canonical WebSocket Manager with proper factory pattern for multi-user isolation.

## Scope
Enhance selected canonical implementation to serve as single source of truth for all WebSocket management.

## Technical Requirements
\`\`\`python
# Canonical location ONLY
/netra_backend/app/websocket_core/websocket_manager.py

# Factory pattern for user isolation
class WebSocketManagerFactory:
    \"\"\"Ensures single instance per user context\"\"\"

# Registry pattern to prevent duplicates
class WebSocketManagerRegistry:
    \"\"\"Prevents duplicate instantiation\"\"\"
\`\`\`

## Tasks
- [ ] Analyze canonical implementation identified in Issue #${NEW_ISSUES[1]}
- [ ] Consolidate features from all 11 implementations
- [ ] Implement factory pattern to prevent duplicate instantiation
- [ ] Create comprehensive interface contract
- [ ] Ensure backward compatibility during transition
- [ ] Add runtime validation for SSOT compliance
- [ ] Create comprehensive unit tests

## Success Criteria
- [ ] Single enhanced WebSocket Manager with all required features
- [ ] Factory pattern prevents duplicate instantiation
- [ ] Interface contract documented for all consumers
- [ ] Backward compatibility maintained
- [ ] Runtime SSOT validation implemented
- [ ] All tests pass
- [ ] No runtime SSOT violations

## Definition of Done
- [ ] Canonical WebSocket Manager implementation complete
- [ ] Factory pattern tested and validated
- [ ] Interface documentation approved
- [ ] Migration guide created for next phase
- [ ] All existing functionality preserved

## Estimated Effort
5-7 days

## Links
- **Depends on:** Issue #${NEW_ISSUES[1]} (audit results)
- **Closes:** Part of #960 (implementation)
- **Blocks:** WebSocket Consumer Migration
- **Epic:** WebSocket SSOT Remediation

## Business Impact
Establishes reliable foundation for chat functionality through SSOT WebSocket management.

---
*Part of Issue #960 resolution plan - see \`MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md\`*
EOF
)")

NEW_ISSUES[2]=$NEW_ISSUE_2
echo "Created Issue #$NEW_ISSUE_2"

echo ""
echo "Step 3: Creating Issue #3 - WebSocket Consumer Migration Sprint"
NEW_ISSUE_3=$(gh issue create \
  --title "Migrate All Services to Canonical WebSocket Manager" \
  --label "ssot,websocket,migration,cleanup,P1" \
  --body "$(cat <<EOF
## Problem Statement
Migrate all services and components to use the canonical WebSocket Manager implementation and remove all duplicate implementations.

## Background
With canonical implementation ready (Issue #${NEW_ISSUES[2]}), migrate all consumers to use single SSOT implementation.

## Scope
Complete migration of all WebSocket Manager consumers to SSOT implementation.

## Migration Checklist
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

## Migration Process
1. Update import statements to canonical path
2. Verify factory pattern usage
3. Test each service individually
4. Remove legacy implementation
5. Validate no regression

## Tasks
- [ ] Update all service imports to use canonical implementation
- [ ] Migrate all consumers following migration guide from Issue #${NEW_ISSUES[2]}
- [ ] Remove all 10 duplicate WebSocket Manager implementations
- [ ] Update import statements throughout codebase
- [ ] Validate no functionality regression
- [ ] Update SSOT compliance metrics

## Success Criteria
- [ ] All services use canonical WebSocket Manager only
- [ ] All duplicate implementations removed from codebase
- [ ] No WebSocket functionality regression
- [ ] SSOT compliance score improved significantly
- [ ] All tests pass with single implementation
- [ ] Zero references to legacy implementations
- [ ] 10+ duplicate files deleted
- [ ] Git history shows clean removal

## Definition of Done
- [ ] All consumers migrated successfully
- [ ] Duplicate files removed from repository
- [ ] Import registry updated
- [ ] Full test suite passes
- [ ] SSOT compliance validated

## Estimated Effort
4-6 days

## Links
- **Depends on:** Issue #${NEW_ISSUES[2]} (canonical implementation)
- **Closes:** Part of #960 (migration)
- **Blocks:** WebSocket SSOT Compliance Validation
- **Epic:** WebSocket SSOT Remediation

## Business Impact
Eliminates fragmentation risk and ensures reliable chat functionality through unified WebSocket management.

---
*Part of Issue #960 resolution plan - see \`MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md\`*
EOF
)")

NEW_ISSUES[3]=$NEW_ISSUE_3
echo "Created Issue #$NEW_ISSUE_3"

echo ""
echo "Step 4: Creating Issue #4 - WebSocket SSOT Compliance Monitoring"
NEW_ISSUE_4=$(gh issue create \
  --title "Implement WebSocket SSOT Compliance Tests & Monitoring" \
  --label "ssot,websocket,testing,monitoring,compliance,P1" \
  --body "$(cat <<EOF
## Problem Statement
Ensure SSOT compliance for WebSocket components and prevent future violations through testing and monitoring.

## Background
To prevent regression after migration (Issue #${NEW_ISSUES[3]}), we need automated validation and monitoring of SSOT compliance.

## Scope
Create comprehensive validation and monitoring for WebSocket SSOT compliance.

## Test Implementation
\`\`\`python
# tests/mission_critical/test_websocket_ssot_compliance.py
class TestWebSocketSSOTCompliance:
    def test_single_implementation(self):
        \"\"\"Verify only one WebSocket Manager exists\"\"\"

    def test_canonical_imports(self):
        \"\"\"Verify all imports use canonical path\"\"\"

    def test_no_duplicate_instances(self):
        \"\"\"Verify registry prevents duplicates\"\"\"
\`\`\`

## Tasks
- [ ] Create test suite for WebSocket SSOT compliance
- [ ] Implement runtime validation to prevent duplicate instantiation
- [ ] Add monitoring and alerting for SSOT violations
- [ ] Run all mission-critical WebSocket tests
- [ ] Validate 100% SSOT compliance score
- [ ] Create regression prevention mechanisms
- [ ] Add CI/CD integration for compliance checks
- [ ] Create compliance dashboard

## Monitoring Setup
- [ ] GCP alert for SSOT violations
- [ ] Daily compliance reports
- [ ] Pre-deployment validation
- [ ] Runtime duplicate detection

## Success Criteria
- [ ] Comprehensive test suite validates single WebSocket Manager
- [ ] Runtime checks prevent duplicate instantiation
- [ ] Monitoring alerts on any SSOT violations
- [ ] All WebSocket tests pass
- [ ] 100% SSOT compliance for WebSocket components
- [ ] CI/CD blocks deployments with violations
- [ ] Zero false positives in monitoring

## Definition of Done
- [ ] Test suite created and passing
- [ ] Runtime validation implemented
- [ ] Monitoring and alerting configured
- [ ] Compliance score reaches 100%
- [ ] Regression prevention validated

## Estimated Effort
3-4 days

## Links
- **Depends on:** Issue #${NEW_ISSUES[3]} (migration complete)
- **Closes:** Monitoring aspect of #960
- **Blocks:** WebSocket SSOT Documentation
- **Epic:** WebSocket SSOT Remediation

## Business Impact
Ensures long-term reliability of chat functionality by preventing SSOT violations.

---
*Part of Issue #960 resolution plan - see \`MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md\`*
EOF
)"
)

NEW_ISSUES[4]=$NEW_ISSUE_4
echo "Created Issue #$NEW_ISSUE_4"

echo ""
echo "Step 5: Creating Issue #5 - WebSocket Architecture Documentation"
NEW_ISSUE_5=$(gh issue create \
  --title "Document WebSocket SSOT Architecture & Patterns" \
  --label "documentation,ssot,websocket,architecture,P2" \
  --body "$(cat <<EOF
## Problem Statement
Document the new WebSocket SSOT architecture and train team to prevent future violations.

## Background
Clear documentation ensures team understanding and prevents reintroduction of duplicate implementations after remediation (Issue #${NEW_ISSUES[4]}).

## Scope
Create comprehensive documentation and training materials for WebSocket SSOT architecture.

## Documentation Structure
\`\`\`
docs/websocket/
├── architecture.md (ADR with diagrams)
├── developer_guide.md (How to use WebSocket)
├── ssot_principles.md (Why and how)
├── migration_guide.md (For future changes)
└── code_review_checklist.md
\`\`\`

## Tasks
- [ ] Create complete WebSocket architecture documentation
- [ ] Update development guidelines to prevent future violations
- [ ] Create training materials for development team
- [ ] Document lessons learned in SPEC/learnings/
- [ ] Update coding standards and review checklists
- [ ] Create Architecture Decision Record (ADR)
- [ ] Update CLAUDE.md directives

## Deliverables
- [ ] Architecture decision record (ADR) with Mermaid diagrams
- [ ] Developer guide for WebSocket usage
- [ ] SSOT principles documentation
- [ ] Migration playbook for future changes
- [ ] Code review checklist
- [ ] Team training materials

## Success Criteria
- [ ] Complete WebSocket architecture documentation
- [ ] Updated development guidelines
- [ ] Team training completed
- [ ] Lessons learned documented
- [ ] Prevention mechanisms in place
- [ ] Team review and approval
- [ ] Integrated into onboarding

## Definition of Done
- [ ] Documentation reviewed and approved
- [ ] Team training completed
- [ ] Guidelines integrated into development process
- [ ] Learning documentation in SPEC/learnings/
- [ ] WebSocket SSOT remediation fully complete

## Estimated Effort
2-3 days

## Links
- **Depends on:** Issue #${NEW_ISSUES[4]} (final architecture)
- **Fully closes:** #960 documentation debt
- **Epic:** WebSocket SSOT Remediation

## Business Impact
Prevents future SSOT violations that could impact chat functionality reliability.

---
*Part of Issue #960 resolution plan - see \`MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md\`*
EOF
)"
)

NEW_ISSUES[5]=$NEW_ISSUE_5
echo "Created Issue #$NEW_ISSUE_5"

echo ""
echo "Step 6: Updating Issue #960 with cross-references"

# Update Issue #960 with references to new issues
gh issue comment 960 --body "$(cat <<EOF
## Issue Resolution Update - Decomposition Complete

This issue has been decomposed into focused, atomic issues for better execution:

### New Issues Created:
- **Issue #${NEW_ISSUES[1]}:** WebSocket Manager SSOT Architecture Audit - Map All 11 Implementations
- **Issue #${NEW_ISSUES[2]}:** Implement Canonical WebSocket Manager with Factory Pattern
- **Issue #${NEW_ISSUES[3]}:** Migrate All Services to Canonical WebSocket Manager
- **Issue #${NEW_ISSUES[4]}:** Implement WebSocket SSOT Compliance Tests & Monitoring
- **Issue #${NEW_ISSUES[5]}:** Document WebSocket SSOT Architecture & Patterns

### Master Plan
Complete implementation strategy documented in:
- \`MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md\`
- \`WEBSOCKET_MANAGER_SSOT_MASTER_PLAN.md\`
- \`ISSUE_UNTANGLE_960_20250916_claude.md\`

### Why This Approach?
Issue #960 became contaminated with:
- Infrastructure alerts mixing with code issues
- Multiple overlapping attempts (#885, #1182)
- Scope creep beyond original problem
- Automated noise obscuring human insights

The focused issues provide clear scope, dependencies, and success criteria without the historical contamination.

### Next Steps
1. Begin with Issue #${NEW_ISSUES[1]} (Architecture Audit)
2. Follow dependency chain through all 5 issues
3. Target completion in 4 weeks with phased approach

This approach protects chat functionality (90% of business value) while achieving complete SSOT compliance.
EOF
)"

echo "Updated Issue #960 with cross-references to new issues"

echo ""
echo "Step 7: Closing Issue #960 with comprehensive summary"

gh issue close 960 --comment "$(cat <<'EOF'
## Issue #960 Closure - Resolved Through Focused Decomposition

After thorough analysis, this issue has been resolved through architectural decomposition into focused, atomic issues.

### Root Cause Analysis
- **Core Problem:** 11 duplicate WebSocket Manager implementations violating SSOT principles
- **Business Impact:** Risk to chat functionality (90% of platform value)
- **Why Previous Attempts Failed:** Scope creep, infrastructure noise, contaminated issue history

### Resolution Strategy
Rather than continue with this contaminated issue, we have:

1. **Created Focused Issues:** 5 atomic issues with clear scope and dependencies
2. **Eliminated Noise:** Separated code issues from infrastructure alerts
3. **Established Clear Path:** Phased approach with specific success criteria
4. **Protected Business Value:** Ensures chat functionality reliability

### Master Plan References
- `MASTER_PLAN_WEBSOCKET_SSOT_960_20250916.md` - Complete implementation strategy
- `WEBSOCKET_MANAGER_SSOT_MASTER_PLAN.md` - Detailed technical plan
- `ISSUE_UNTANGLE_960_20250916_claude.md` - Analysis and recommendations

### Implementation Timeline
- **Phase 1 (Weeks 1-2):** Architecture audit and canonical implementation
- **Phase 2 (Week 3):** Consumer migration and cleanup
- **Phase 3 (Week 4):** Validation, monitoring, and documentation

### Success Metrics
- **Technical:** 100% SSOT compliance for WebSocket components
- **Business:** Zero WebSocket-related chat failures
- **Quality:** 10+ duplicate files removed, comprehensive test coverage

### Business Impact
This resolution protects our primary value delivery channel (chat functionality) by ensuring reliable, maintainable WebSocket management through SSOT compliance.

The focused approach ensures successful execution without the scope creep and confusion that prevented previous resolution attempts.

**Issue #960 is now closed. Implementation continues through the focused issue chain above.**
EOF
)"

echo "Successfully closed Issue #960"

echo ""
echo "=== Issue #960 Resolution Complete ==="
echo ""
echo "Summary of Actions:"
echo "✅ Created Issue #${NEW_ISSUES[1]}: WebSocket Manager SSOT Architecture Audit"
echo "✅ Created Issue #${NEW_ISSUES[2]}: Implement Canonical WebSocket Manager"
echo "✅ Created Issue #${NEW_ISSUES[3]}: Migrate All Services to Canonical WebSocket Manager"
echo "✅ Created Issue #${NEW_ISSUES[4]}: Implement WebSocket SSOT Compliance Tests & Monitoring"
echo "✅ Created Issue #${NEW_ISSUES[5]}: Document WebSocket SSOT Architecture & Patterns"
echo "✅ Updated Issue #960 with cross-references"
echo "✅ Closed Issue #960 with comprehensive closure comment"
echo ""
echo "Next Steps:"
echo "1. Begin Issue #${NEW_ISSUES[1]} (Architecture Audit)"
echo "2. Follow dependency chain: ${NEW_ISSUES[1]} → ${NEW_ISSUES[2]} → ${NEW_ISSUES[3]} → ${NEW_ISSUES[4]} → ${NEW_ISSUES[5]}"
echo "3. Target completion: 4 weeks with phased approach"
echo ""
echo "Business Impact: Protects chat functionality (90% of platform value) through SSOT compliance"
echo ""
echo "Resolution complete - focused execution can now begin!"