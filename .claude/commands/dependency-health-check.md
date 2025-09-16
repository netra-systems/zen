# Dependency Health Check Command

Check health of dependency chains and identify bottlenecks across all GitHub issues.

## Usage
- `/dependency-health-check` - Check all issues with dependency labels
- `/dependency-health-check P0` - Check P0 issue dependency health
- `/dependency-health-check golden-path` - Check Golden Path dependency health
- `/dependency-health-check report` - Generate comprehensive dependency health report

## What This Command Does

1. **Scan Dependency Labels**
   - Find all issues with `depends-on-XXXX` labels
   - Find all issues with `blocks-XXXX` labels
   - Map complete dependency network

2. **Identify Dependency Issues**
   - Broken dependency chains (referenced issues don't exist)
   - Circular dependencies (A depends on B, B depends on A)
   - Long-blocking issues (issues blocking work for extended periods)
   - Orphaned dependencies (depends on closed/resolved issues)

3. **Analyze Bottlenecks**
   - Issues blocking multiple other issues
   - Critical path bottlenecks affecting timelines
   - Resource constraints affecting dependency resolution

4. **Health Assessment**
   - Dependency chain completeness
   - Average resolution time for blocking issues
   - Number of issues waiting on dependencies
   - Critical path health metrics

5. **Generate Recommendations**
   - Priority order for resolving blockers
   - Opportunities for parallel work
   - Dependency chain optimization suggestions
   - Resource allocation recommendations

## Health Metrics

### Healthy Dependency Chain
- ✅ All dependencies clearly labeled and cross-linked
- ✅ Blocking issues have clear resolution plans
- ✅ No circular dependencies
- ✅ Critical path is well-defined and progressing

### Unhealthy Dependency Chain
- ❌ Broken links or missing dependency labels
- ❌ Long-blocking issues without progress
- ❌ Circular dependencies preventing progress
- ❌ Multiple critical paths competing for resources

## Expected Output

- **Dependency Health Score** (0-100%)
- **Bottleneck Analysis** (top blocking issues)
- **Broken Chain Report** (issues needing attention)
- **Resolution Priority List** (optimal order for fixing blockers)
- **Health Trend Analysis** (improving/degrading over time)

## Report Structure

```markdown
# Dependency Health Report

## Overall Health Score: XX%

### Critical Blockers (Top Priority):
- #XXXX: Blocking N issues for Y days
- #XXXX: Infrastructure blocker affecting critical path

### Broken Dependencies:
- #XXXX: References non-existent issue #YYYY
- #XXXX: Circular dependency with #YYYY

### Long-Standing Blockers:
- #XXXX: Blocking for X days without progress
- #XXXX: Needs resource assignment

### Recommendations:
1. Fix #XXXX immediately (unblocks N issues)
2. Resolve circular dependency between #XXXX and #YYYY
3. Assign resources to #XXXX (critical path impact)
```

## Integration

- Works with `dependency-analysis` to maintain healthy relationships
- Supports `critical-path-planning` with bottleneck identification
- Integrates with `priority-triage` for resource allocation
- Uses DEPENDENCY_MANAGEMENT_SPEC.md for health criteria

## Automation

Can be run:
- Weekly as part of development process health checks
- Before major releases to ensure dependency readiness
- When new P0 issues are created to check impact
- During sprint planning to identify dependency risks