# GitHub Commands for Issue #1278 Critical Update

## Option 1: Update Existing Issue #1278 (Preferred)

### Add Critical Status Comment
```bash
gh issue comment 1278 --body-file "C:\netra-apex\issue_1278_critical_update_20250915_185527.md"
```

### Update Labels
```bash
gh issue edit 1278 --add-label "P0-critical"
gh issue edit 1278 --add-label "infrastructure"
gh issue edit 1278 --add-label "regression"
gh issue edit 1278 --add-label "actively-being-worked-on"
gh issue edit 1278 --add-label "staging-outage"
```

### View Current Status
```bash
gh issue view 1278
```

## Option 2: Create New Issue (If #1278 is closed/irrelevant)

### Create New Critical Issue
```bash
gh issue create \
  --title "CRITICAL: Staging Environment Complete Outage - HTTP 503/500 Errors Blocking Golden Path User Flow" \
  --body-file "C:\netra-apex\issue_1278_critical_update_20250915_185527.md" \
  --label "P0-critical,infrastructure,staging-outage,database-connectivity,regression" \
  --assignee "@me"
```

## Verification Commands

### Check Issue Status
```bash
gh issue view 1278 --json state,title,labels,assignees,url
```

### List Recent Issues
```bash
gh issue list --limit 10 --state all --label "P0-critical"
```

## Expected Outcomes

### If Issue #1278 Exists and is Open:
- Comment will be added with comprehensive status update
- Labels will be updated to reflect critical priority
- Issue remains tracked under #1278

### If Issue #1278 is Closed or Doesn't Exist:
- New issue will be created with all relevant details
- Will receive new issue number for tracking
- Original #1278 can be referenced in new issue if relevant

## File References
- **Update Content**: `C:\netra-apex\issue_1278_critical_update_20250915_185527.md`
- **Evidence Files**: Multiple comprehensive analysis files referenced in update
- **Technical Context**: Database connectivity regression analysis included

## Post-Action Steps
1. Note the issue number (either #1278 or new number)
2. Note the comment ID from the response
3. Verify labels were applied correctly
4. Share issue URL for team visibility

---
**Created**: 2025-09-15T18:55:27 PST
**Purpose**: GitHub issue management for critical staging outage