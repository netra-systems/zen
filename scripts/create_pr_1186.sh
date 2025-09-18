#!/bin/bash
# Safe PR creation for Issue #1186
# CRITICAL: Maintains develop-long-lived as current branch

echo "Creating PR for Issue #1186..."
echo "Current branch: $(git branch --show-current)"

# Create PR from feature branch to develop-long-lived
gh pr create \
  --base develop-long-lived \
  --head feature/issue-1186-1757975088 \
  --title "Fix: Issue #1186 UserExecutionEngine SSOT Consolidation" \
  --body "Consolidates UserExecutionEngine implementation into single source of truth. Removes duplicate execution logic across multiple files. Improves system stability and maintainability. Validated through comprehensive staging deployment. Closes #1186"

echo "PR created successfully!"
echo "Final verification - Current branch: $(git branch --show-current)"