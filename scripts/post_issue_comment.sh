#!/bin/bash

# Post comprehensive comment to Issue #1278
gh issue comment 1278 --body-file "/Users/anthony/Desktop/netra-apex/issue_1278_comprehensive_github_comment.md"

# Store the comment ID for tracking
echo "Comment posted successfully to Issue #1278"
echo "Checking for comment ID..."
gh issue view 1278 --json comments | jq '.comments[-1].id'