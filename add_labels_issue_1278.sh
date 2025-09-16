#!/bin/bash
# Script to add tracking labels to Issue #1278
# Agent Session: 20250916

echo "Adding tracking labels to Issue #1278..."

# Add the required labels to Issue #1278
gh issue edit 1278 --add-label "actively-being-worked-on,agent-session-20250916"

echo "Successfully added labels to Issue #1278:"
echo "- actively-being-worked-on"
echo "- agent-session-20250916"

# Verify the labels were added
echo ""
echo "Current labels on Issue #1278:"
gh issue view 1278 --json labels --jq '.labels[]|.name'

echo ""
echo "Issue #1278 labeling complete!"