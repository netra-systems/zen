#!/bin/bash
# Add required tracking tags to Issue #1278
# Agent Session: 20250916-085636

echo "Adding tracking tags to Issue #1278..."

# Add the required tags to Issue #1278
gh issue edit 1278 --add-label "actively-being-worked-on" --add-label "agent-session-20250916-085636"

echo "Successfully added tags to Issue #1278:"
echo "- actively-being-worked-on"
echo "- agent-session-20250916-085636"

# Show current status
echo ""
echo "Current labels on Issue #1278:"
gh issue view 1278 --json labels -q '.labels[].name'

echo ""
echo "Issue #1278 tagging complete!"