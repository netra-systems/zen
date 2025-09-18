# Dependency Management Specification

**Purpose:** Standard approach for managing issue dependencies, blocking relationships, and execution sequencing in Netra Apex development.

**Created:** 2025-09-15
**Last Updated:** 2025-09-15
**Version:** 1.0

## Overview

This specification defines how to identify, track, and manage dependencies between GitHub issues to prevent wheel-spinning, ensure proper execution sequencing, and maintain development velocity.

## Label System

### Blocking Labels
- **`infrastructure-blocker`** (color: `cc0000`) - Infrastructure issues blocking multiple features
- **`blocks-golden-path`** (color: `ff0000`) - Issues that block Golden Path functionality

### Dependency Labels
- **`depends-on-XXXX`** (color: gradient `ffcccc` → `fff0ee`) - Blocked by specific issue number
- **`sequential-dependency`** (color: `ffa500`) - Must complete in sequence with other issues

### Examples:
- `depends-on-1264` - Blocked by Cloud SQL misconfiguration issue #1264
- `depends-on-1171` - Blocked by WebSocket race condition issue #1171
- `depends-on-1184` - Blocked by WebSocket infrastructure integration issue #1184
- `depends-on-1201` - Blocked by production deployment validation issue #1201

## Issue Cross-Linking Standard

### 1. Dependency Comments Template
Add to each issue with dependencies:

```markdown
## 🔗 DEPENDENCY LINKS & BLOCKING ISSUES

**PARENT ISSUE:** #XXXX (if part of larger plan)

### Dependencies (Must Complete Before This Issue):
- **#XXXX** (Description) - DEPENDENCY
- **#XXXX** (Description) - DEPENDENCY

### Current Blockers:
- **#XXXX** (Description) - **CRITICAL BLOCKER**
  - Why it blocks this issue
  - Impact description

### Blocks These Issues:
- **#XXXX** (Description)
- **#XXXX** (Description)

### Resolution Sequence Required:
1. Fix #XXXX (description) ← **IMMEDIATE**
2. Resolve #XXXX (description) ← **NEXT**
3. **THEN** proceed with this issue

**STATUS:** ⛔ BLOCKED / ✅ READY / 🔄 IN PROGRESS
```

### 2. Master Plan Coordination
For complex multi-issue initiatives:

```markdown
## 📋 EXECUTION SEQUENCE & STATUS

### CRITICAL PATH (Sequential - Must Complete in Order):
1. **#XXXX** (Description)
   - Status: ⛔ BLOCKED / ✅ READY / 🔄 IN PROGRESS
   - Action: What needs to be done
   - Timeline: Estimated time

### PARALLEL WORK (Can Proceed Independently):
- #XXXX (Description) ✅ Can proceed
- #XXXX (Description) ✅ Can proceed

### CONSOLIDATED ISSUES:
- ✅ **#XXXX CLOSED** (reason)

**TOTAL ESTIMATED TIME:** X hours after blockers resolved
**CURRENT BLOCKER:** Primary blocking issue
```

## Dependency Analysis Process

### 1. For Each P0 Issue:
1. **Search for Related Issues**
   - Use GitHub search with relevant keywords
   - Check labels for related functionality
   - Review recent issues in same domain

2. **Identify Blocking Relationships**
   - Infrastructure dependencies (databases, services, deployment)
   - Code dependencies (shared components, APIs, interfaces)
   - Sequential workflows (auth → validation → deployment)

3. **Determine Consolidation Opportunities**
   - Issues with same root cause → merge/close duplicates
   - Related work that should be coordinated → cross-link
   - Sequential work that could be batched → combine

4. **Apply Labels and Cross-Links**
   - Add dependency labels to blocked issues
   - Add blocking labels to blocker issues
   - Add cross-reference comments to all related issues

### 2. Dependency Tree Mapping
Create visual dependency trees in master coordination issues:

```
Issue A (Primary Blocker)
  ├── CAUSES Issue B (direct impact)
  ├── BLOCKS Issue C (cannot proceed until A is fixed)
  │   └── BLOCKS Issue D (depends on C)
  └── RELATED TO Issue E (same domain, potential consolidation)
```

## Claude Command Integration

### Recommended `.claude/commands` Updates

#### 1. Create `dependency-analysis` Command
```markdown
# .claude/commands/dependency-analysis.md

Analyze dependencies for a specific issue or set of issues.

Usage: `/dependency-analysis <issue-number>` or `/dependency-analysis P0`

This command will:
1. Search for related issues by keywords and labels
2. Identify blocking relationships and dependencies
3. Recommend consolidation opportunities
4. Generate dependency tree visualization
5. Apply appropriate labels and cross-links
6. Create execution sequence recommendations

Always check for infrastructure blockers, code dependencies, and sequential workflow requirements.
```

#### 2. Create `issue-consolidation` Command
```markdown
# .claude/commands/issue-consolidation.md

Consolidate duplicate or related issues to reduce tracking fragmentation.

Usage: `/issue-consolidation <primary-issue> <duplicate-issue>`

This command will:
1. Analyze if issues have same root cause
2. Merge relevant information into primary issue
3. Add consolidation comments with cross-references
4. Close duplicate issue with appropriate reason
5. Update all related issues with new references
6. Transfer labels and relationships as needed
```

#### 3. Create `critical-path-planning` Command
```markdown
# .claude/commands/critical-path-planning.md

Create execution plan for complex multi-issue initiatives.

Usage: `/critical-path-planning <master-issue>`

This command will:
1. Identify all related issues in the initiative
2. Analyze dependencies and blocking relationships
3. Create sequential execution order
4. Identify parallel work opportunities
5. Estimate timelines and resource requirements
6. Generate master coordination plan
7. Apply proper labels and cross-links
```

#### 4. Update `priority-triage` Command
Add dependency checking to existing priority triage:

```markdown
# .claude/commands/priority-triage.md (UPDATE)

// Add to existing command:

### Dependency Analysis:
- Check for blocking infrastructure issues
- Identify prerequisite work that must complete first
- Look for opportunities to batch related work
- Apply dependency labels: depends-on-XXXX, blocks-XXXX
- Cross-link related issues with dependency comments
```

#### 5. Create `dependency-health-check` Command
```markdown
# .claude/commands/dependency-health-check.md

Check health of dependency chains and identify bottlenecks.

Usage: `/dependency-health-check` or `/dependency-health-check P0`

This command will:
1. Scan all issues with dependency labels
2. Identify broken dependency chains
3. Find circular dependencies
4. Highlight long-blocking issues
5. Recommend resolution priorities
6. Generate dependency health report
```

## Best Practices

### Do:
- ✅ Always search for related issues before creating new ones
- ✅ Apply dependency labels immediately when relationships are identified
- ✅ Add cross-reference comments explaining blocking relationships
- ✅ Close duplicate issues with proper consolidation comments
- ✅ Update dependency chains when issues are resolved
- ✅ Create master coordination issues for complex initiatives

### Don't:
- ❌ Create issues without checking for existing related work
- ❌ Start work on issues that have unresolved blockers
- ❌ Mix multiple root causes in a single issue
- ❌ Leave dependency relationships undocumented
- ❌ Work on issues out of dependency order
- ❌ Create circular dependencies

## Implementation Checklist

When implementing dependency management:

- [ ] Create all required labels in repository
- [ ] Apply labels to existing P0 issues
- [ ] Add cross-reference comments to related issues
- [ ] Create master coordination issues for complex work
- [ ] Update Claude commands to respect dependencies
- [ ] Train team on dependency management process
- [ ] Regular dependency health checks (weekly)

## Success Metrics

- **Reduced Wheel-Spinning:** Issues don't start until blockers are resolved
- **Clear Execution Order:** Teams know what to work on next
- **Efficient Resource Use:** Parallel work identified and utilized
- **Faster Resolution:** Dependencies don't cause unexpected delays
- **Better Visibility:** Management can see true project status

---

**Note:** This specification should be updated as dependency management practices evolve and new patterns are discovered.