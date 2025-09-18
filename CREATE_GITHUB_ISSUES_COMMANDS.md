# GitHub Issue Creation Commands for Issue #1184 Decomposition

**Date**: 2025-01-16
**Purpose**: Decompose complex issue #1184 into manageable sub-issues

## Commands to Execute

### 1. Emergency Production Hotfix (P0 Critical)
```bash
gh issue create \
  --title "HOTFIX: Production WebSocket async/await pattern violations" \
  --body-file "issues/hotfix_websocket_async_patterns.md" \
  --label "bug,priority:critical,websocket,golden-path"
```

### 2. WebSocket Factory Simplification (P1 High)
```bash
gh issue create \
  --title "ENHANCEMENT: WebSocket Factory Pattern Simplification" \
  --body-file "issues/websocket_factory_simplification.md" \
  --label "enhancement,priority:high,websocket,architecture,ssot"
```

### 3. Test-Production Alignment (P1 High)
```bash
gh issue create \
  --title "IMPROVEMENT: Test-Production Alignment for Async/Await Patterns" \
  --body-file "issues/test_production_alignment.md" \
  --label "testing,priority:high,websocket,quality-assurance,async-patterns"
```

### 4. Documentation and Monitoring (P2 Medium)
```bash
gh issue create \
  --title "IMPROVEMENT: Documentation and Monitoring for WebSocket Infrastructure" \
  --body-file "issues/documentation_monitoring_improvements.md" \
  --label "documentation,monitoring,priority:medium,websocket,operational-excellence"
```

## Close Original Issue

After creating the new issues, close the original issue #1184 with a summary comment:

```bash
gh issue close 1184 --comment "$(cat <<'EOF'
# Issue #1184 Decomposition Complete

This complex issue has been analyzed and decomposed into **4 focused, actionable sub-issues** for better tracking and execution.

## Analysis Summary

**Core Problem**: Production async/await pattern violations continue despite documented resolution.
**Root Cause**: Disconnect between test validation and production reality.
**Business Impact**: Golden Path user flow interruption ($500K+ ARR).

## New Issues Created

1. **Production Hotfix** (P0 Critical): Immediate async/await pattern fixes
2. **Factory Simplification** (P1 High): Long-term architectural improvement
3. **Test-Production Alignment** (P1 High): Prevent future misalignment
4. **Documentation & Monitoring** (P2 Medium): Operational excellence

## Master Plan

See complete analysis and implementation strategy in:
- `ISSUE_UNTANGLE_1184_20250116_analysis.md`
- `MASTER_PLAN_1184_20250116.md`

## Next Steps

1. Execute production hotfix for immediate stability
2. Implement test-production alignment validation
3. Simplify factory patterns for long-term maintainability
4. Enhance documentation and monitoring

The original issue scope was too broad for single-issue tracking. These focused sub-issues enable parallel execution and clear progress tracking.

**Status**: Decomposed into actionable work items
**Ownership**: Distributed across specialized teams
**Timeline**: 2-4 weeks for complete resolution
EOF
)"
```

## Verification Commands

After creating issues, verify they were created correctly:

```bash
# List recently created issues
gh issue list --author @me --limit 5

# Check specific issue details
gh issue view <issue_number>

# Verify labels were applied correctly
gh issue list --label "websocket" --state open
```

## Notes

- All issue files are ready in the `issues/` directory
- Each issue has detailed acceptance criteria and implementation plans
- Issues are prioritized for both parallel and sequential execution
- Links back to parent issue #1184 and master plan documentation maintained

Execute these commands in sequence to complete the issue decomposition process.