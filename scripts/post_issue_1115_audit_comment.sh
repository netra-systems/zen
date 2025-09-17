#!/bin/bash

# GitHub Issue #1115 Audit Results Comment Posting Script
# Agent Session: 20250915-224118

echo "Posting audit results comment to Issue #1115..."

# Post the audit comment
gh issue comment 1115 --body "$(cat issue_1115_audit_results_comment.md)"

if [ $? -eq 0 ]; then
    echo "✅ Successfully posted audit results comment to Issue #1115"

    # Check current issue status
    echo "Checking current issue status..."
    gh issue view 1115 --json state,closedAt,labels

    # Add agent session label if not present
    echo "Adding agent session labels..."
    gh issue edit 1115 --add-label "audit-complete" --add-label "ssot-validated" --add-label "agent-session-20250915-224118"

else
    echo "❌ Failed to post comment to Issue #1115"
    exit 1
fi

echo "Issue #1115 audit complete - no reopening needed based on technical validation"