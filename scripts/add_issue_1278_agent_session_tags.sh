#!/bin/bash
# Add agent session tracking tags to Issue #1278
# Agent Session: 20250916_032825

echo "Adding agent session tracking tags to Issue #1278..."

# Add the required tags to Issue #1278
gh issue edit 1278 --add-label "actively-being-worked-on" --add-label "agent-session-20250916_032825"

echo "Successfully added agent session tags to Issue #1278:"
echo "- actively-being-worked-on"
echo "- agent-session-20250916_032825"

# Show current status
echo ""
echo "Current labels on Issue #1278:"
gh issue view 1278 --json labels -q '.labels[].name'

echo ""
echo "Issue #1278 agent session tagging complete!"