#!/bin/bash

# Add session tags to GitHub Issue #914
# Session: agent-session-2025-09-15-163618

echo "Adding session tags to GitHub Issue #914..."

# Add the session tags
gh issue edit 914 --add-label "actively-being-worked-on"
gh issue edit 914 --add-label "agent-session-2025-09-15-163618"

echo "Session tags added successfully to Issue #914"

# Verify the labels were added
echo "Current labels on Issue #914:"
gh issue view 914 --json labels --jq '.labels[].name'