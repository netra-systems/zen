#!/bin/bash

# Create comprehensive comment on GitHub Issue #1278
# This script creates a comment with Five Whys analysis and current status

gh issue comment 1278 --body-file "C:\GitHub\netra-apex\issue_1278_comment_simple.md"

# Get the comment ID for tracking
gh api repos/:owner/:repo/issues/1278/comments --jq '.[-1].id'

echo "Comment created successfully on Issue #1278"
echo "Comment contains:"
echo "- Five Whys Analysis Results"
echo "- Current Codebase Audit Evidence"
echo "- System Status Assessment"
echo "- Validation Commands & Results"
echo "- Recommended Next Steps"
echo "- Business Impact Summary"