#!/bin/bash

# Issue #1263 Status Update Script
# Updates issue with comprehensive status analysis and adds tracking tags

echo "Updating Issue #1263 with status analysis..."

# Add the comprehensive status update comment
echo "Adding status update comment..."
gh issue comment 1263 --body-file "issue_1263_status_update_comment.md"

# Capture the comment ID (last comment will be the one we just added)
COMMENT_ID=$(gh issue view 1263 --json comments --jq '.comments[-1].id')
echo "Comment ID: $COMMENT_ID"

# Add the required tags
echo "Adding tags to Issue #1263..."
gh issue edit 1263 --add-label "actively-being-worked-on"
gh issue edit 1263 --add-label "agent-session-20250915-125647"

# Verify the tags were added
echo "Current issue labels:"
gh issue view 1263 --json labels --jq '.labels[].name'

echo "Issue #1263 updated successfully!"
echo "Comment ID: $COMMENT_ID"
echo "Status: SUBSTANTIALLY RESOLVED - Continuing to optional monitoring steps"