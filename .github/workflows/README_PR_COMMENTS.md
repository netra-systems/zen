# GitHub Actions PR Comment Management

## Problem
Multiple GitHub Actions workflows were creating separate PR comments, causing comment spam and making it difficult to track the overall status of PR checks.

## Solution
We've implemented two reusable GitHub Actions to consolidate PR comments:

### 1. Individual Workflow Comments: `pr-comment`
Located at `.github/actions/pr-comment/action.yml`

This action allows workflows to create or update a single comment with a unique identifier.

**Usage:**
```yaml
- name: Post Status
  uses: ./.github/actions/pr-comment
  with:
    comment-identifier: 'unique-workflow-id'
    comment-body: |
      Your markdown content here
```

### 2. Consolidated Status Comment: `consolidated-pr-status`
Located at `.github/actions/consolidated-pr-status/action.yml`

This action maintains a single consolidated status comment that shows the status of all workflows.

**Usage:**
```yaml
- name: Update Consolidated Status
  uses: ./.github/actions/consolidated-pr-status
  with:
    workflow-name: 'Test Runner'
    status: 'success'  # or 'failure', 'skipped', 'running'
    details: 'All tests passed'
```

## Migration Status

### ✅ Completed
- Created reusable PR comment action
- Created consolidated status action  
- Updated `unified-test-runner.yml` to use the new action
- Updated `mission-critical-tests.yml` to use the new action
- Added migration notices to workflows needing updates

### 🔧 Workflows Requiring Updates
The following workflows still need to be updated to use the new comment system:
- `e2e-tests.yml` (creates 2 separate comments)
- `deploy-staging.yml`
- `database-regression-tests.yml`
- `cleanup.yml`
- `ci-orchestrator.yml`
- `ci-max-parallel.yml`
- `ci-fail-fast.yml`
- `ci-balanced.yml`
- `agent-startup-e2e-tests.yml`

## Benefits
1. **Reduced Noise**: Single updateable comment per workflow instead of multiple comments
2. **Better Overview**: Consolidated status comment shows all workflow statuses at a glance
3. **Cleaner PR Interface**: Less scrolling, easier to find relevant information
4. **Consistent Updates**: Comments are updated in place rather than creating new ones

## Implementation Notes
- Comments use HTML comments as identifiers to find and update existing comments
- The consolidated status stores workflow data in base64-encoded JSON within the comment
- Comment posting failures don't fail the workflow (graceful degradation)
- Works with both individual workflow updates and consolidated status tracking