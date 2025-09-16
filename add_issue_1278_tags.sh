#!/bin/bash
# Add required tracking tags to Issue #1278
# Session: agent-session-20250915-131500

echo "Adding tracking tags to Issue #1278..."

# Add the required tags to Issue #1278
gh issue edit 1278 --add-label "actively-being-worked-on,agent-session-20250915-131500"

echo "Successfully added tags to Issue #1278:"
echo "- actively-being-worked-on"
echo "- agent-session-20250915-131500"

# Verify the tags were added
echo ""
echo "Current labels on Issue #1278:"
gh issue view 1278 --json labels --jq '.labels[]|.name'