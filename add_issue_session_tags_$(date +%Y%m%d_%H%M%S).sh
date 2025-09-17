#!/bin/bash

# Issue session tagging for P0 issue processing
# Generated: 2025-09-16
# Current timestamp for session tracking

ISSUE_NUM="1278"
SESSION_ID="agent-session-$(date +%Y%m%d-%H%M%S)"

echo "Adding session tags to Issue #${ISSUE_NUM}..."

# Add required session tags
gh issue edit ${ISSUE_NUM} --add-label "actively-being-worked-on"
gh issue edit ${ISSUE_NUM} --add-label "${SESSION_ID}"
gh issue edit ${ISSUE_NUM} --add-label "p0-critical-processing"

echo "Session tags applied successfully to Issue #${ISSUE_NUM}"
echo "Issue #${ISSUE_NUM} is now tagged for active agent session work."
echo "Session ID: ${SESSION_ID}"