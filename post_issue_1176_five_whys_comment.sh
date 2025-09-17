#!/bin/bash

# Script to post Issue #1176 Five Whys Analysis comment to GitHub
# Run with: bash post_issue_1176_five_whys_comment.sh

echo "Posting Issue #1176 Five Whys Analysis Status Update..."

# Post the comment
gh issue comment 1176 --repo netra-systems/netra-apex --body-file github_issue_1176_five_whys_status_update.md

# Add/update labels
echo "Updating issue labels..."
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "actively-being-worked-on"
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "P0-critical"
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "recursive-manifestation"
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "documentation-reality-disconnect"
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "infrastructure-truth-validation"
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "unit-test-failures"
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "integration-test-failures"
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "e2e-test-failures"
gh issue edit 1176 --repo netra-systems/netra-apex --add-label "false-green-ci-status"

echo "Issue #1176 updated with Five Whys analysis and appropriate labels."
echo "Comment posted successfully!"